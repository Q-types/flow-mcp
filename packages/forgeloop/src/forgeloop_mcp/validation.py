"""Validation command execution for ForgeLoop MCP."""

import re
import shlex
import subprocess
import time
from pathlib import Path

from .models import OutputCapture, ValidationRecord, ValidationStatus
from .storage import ForgeLoopStorage


# Allowed commands for validation (security whitelist)
ALLOWED_COMMAND_PREFIXES = {
    # Python
    "pytest", "python", "python3", "pip", "uv", "ruff", "mypy", "black", "isort",
    "flake8", "pylint", "bandit", "safety", "coverage",
    # JavaScript/TypeScript
    "npm", "npx", "yarn", "pnpm", "node", "tsc", "eslint", "prettier", "jest",
    "vitest", "mocha", "playwright", "cypress",
    # Rust
    "cargo", "rustfmt", "clippy",
    # Go
    "go", "gofmt", "golint", "staticcheck",
    # Docker
    "docker", "docker-compose", "podman",
    # General
    "make", "cmake", "bash", "sh", "cat", "ls", "head", "tail", "grep", "wc",
    "curl", "wget",  # For health checks
}


class ValidationError(Exception):
    """Validation execution error."""
    pass


def _is_safe_command(command: str) -> bool:
    """Check if a command is in the allowed list.

    This is a heuristic safety check - it allows commands that start
    with known safe prefixes.
    """
    parts = shlex.split(command)
    if not parts:
        return False
    cmd = parts[0].split("/")[-1]  # Get base command name
    return cmd in ALLOWED_COMMAND_PREFIXES


def _parse_test_output(output: str, command: str) -> tuple[int | None, int | None]:
    """Parse test output to extract pass/fail counts.

    Supports multiple test frameworks:
    - pytest (Python)
    - Jest/Vitest (JavaScript/TypeScript)
    - Cargo test (Rust)
    - go test (Go)
    - Mocha (JavaScript)
    - PHPUnit (PHP)
    - RSpec (Ruby)

    Returns (passed, failed) tuple.
    """
    passed = None
    failed = None

    # pytest style: "X passed, Y failed"
    pytest_match = re.search(r"(\d+) passed", output)
    if pytest_match:
        passed = int(pytest_match.group(1))
    pytest_fail = re.search(r"(\d+) failed", output)
    if pytest_fail:
        failed = int(pytest_fail.group(1))

    # Jest/Vitest style: "Tests: X passed, Y failed"
    jest_match = re.search(r"Tests:\s*(\d+)\s*passed", output)
    if jest_match:
        passed = int(jest_match.group(1))
    jest_fail = re.search(r"Tests:\s*(\d+)\s*failed", output)
    if jest_fail:
        failed = int(jest_fail.group(1))

    # npm test/jest alternative: "Test Suites: X passed"
    if passed is None:
        suite_match = re.search(r"Test Suites:\s*(\d+)\s*passed", output)
        if suite_match:
            passed = int(suite_match.group(1))

    # Cargo test (Rust): "test result: ok. X passed; Y failed"
    if passed is None:
        cargo_match = re.search(r"test result:.*?(\d+)\s*passed;\s*(\d+)\s*failed", output)
        if cargo_match:
            passed = int(cargo_match.group(1))
            failed = int(cargo_match.group(2))

    # Go test: "ok" lines for passed, "FAIL" for failures, or "--- PASS: X" / "--- FAIL: X"
    if passed is None:
        go_pass = len(re.findall(r"--- PASS:", output))
        go_fail = len(re.findall(r"--- FAIL:", output))
        if go_pass > 0 or go_fail > 0:
            passed = go_pass
            failed = go_fail if go_fail > 0 else 0

    # Mocha: "X passing" / "Y failing"
    if passed is None:
        mocha_pass = re.search(r"(\d+)\s*passing", output)
        if mocha_pass:
            passed = int(mocha_pass.group(1))
        mocha_fail = re.search(r"(\d+)\s*failing", output)
        if mocha_fail:
            failed = int(mocha_fail.group(1))

    # PHPUnit: "OK (X tests, Y assertions)" or "FAILURES! Tests: X, Assertions: Y, Failures: Z"
    if passed is None:
        phpunit_ok = re.search(r"OK \((\d+) tests?, \d+ assertions?\)", output)
        if phpunit_ok:
            passed = int(phpunit_ok.group(1))
            failed = 0
        else:
            phpunit_fail = re.search(r"Tests:\s*(\d+).*?Failures:\s*(\d+)", output)
            if phpunit_fail:
                total = int(phpunit_fail.group(1))
                failed = int(phpunit_fail.group(2))
                passed = total - failed if total >= failed else 0

    # RSpec (Ruby): "X examples, Y failures"
    if passed is None:
        rspec_match = re.search(r"(\d+)\s*examples?,\s*(\d+)\s*failures?", output)
        if rspec_match:
            total = int(rspec_match.group(1))
            failed = int(rspec_match.group(2))
            passed = total - failed

    return passed, failed


def _parse_lint_output(output: str, command: str) -> dict[str, int | None]:
    """Parse lint tool output to extract error/warning counts.

    Supports:
    - ruff (Python)
    - eslint (JavaScript/TypeScript)
    - clippy (Rust)
    - golint/staticcheck (Go)
    - pylint (Python)
    - flake8 (Python)

    Returns dict with keys: errors, warnings, fixed (if applicable).
    """
    result: dict[str, int | None] = {"errors": None, "warnings": None, "fixed": None}

    # Ruff: "Found X errors" or "X errors" at end, or count by scanning output
    if "ruff" in command.lower():
        # Ruff summary: "Found X error(s)."
        ruff_errors = re.search(r"Found (\d+) errors?", output)
        if ruff_errors:
            result["errors"] = int(ruff_errors.group(1))
        else:
            # Count individual error lines (file:line:col: code message)
            error_lines = len(re.findall(r"^\S+:\d+:\d+:", output, re.MULTILINE))
            if error_lines > 0:
                result["errors"] = error_lines

        # Ruff fix mode: "Fixed X errors"
        ruff_fixed = re.search(r"Fixed (\d+) errors?", output)
        if ruff_fixed:
            result["fixed"] = int(ruff_fixed.group(1))

    # ESLint: "X problems (Y errors, Z warnings)"
    eslint_match = re.search(r"(\d+) problems?\s*\((\d+) errors?,\s*(\d+) warnings?\)", output)
    if eslint_match:
        result["errors"] = int(eslint_match.group(2))
        result["warnings"] = int(eslint_match.group(3))

    # Clippy (Rust): "warning: X warnings emitted" or "error[E...]:"
    if "clippy" in command.lower() or "cargo" in command.lower():
        clippy_warn = re.search(r"warning:\s*(\d+)\s*warnings?\s*emitted", output)
        if clippy_warn:
            result["warnings"] = int(clippy_warn.group(1))
        clippy_errors = len(re.findall(r"^error\[E\d+\]:", output, re.MULTILINE))
        if clippy_errors > 0:
            result["errors"] = clippy_errors

    # Pylint: "Your code has been rated at X/10"
    # Also extracts counts from "Messages: X warnings, Y errors" or similar
    pylint_msg = re.search(r"(\d+)\s*errors?,\s*(\d+)\s*warnings?", output, re.IGNORECASE)
    if pylint_msg and result["errors"] is None:
        result["errors"] = int(pylint_msg.group(1))
        result["warnings"] = int(pylint_msg.group(2))

    # Flake8: count error lines
    if "flake8" in command.lower() and result["errors"] is None:
        error_lines = len(re.findall(r"^\S+:\d+:\d+:", output, re.MULTILINE))
        if error_lines > 0:
            result["errors"] = error_lines

    # golint/staticcheck: count lines of output (each line is an issue)
    if ("golint" in command.lower() or "staticcheck" in command.lower()) and result["errors"] is None:
        issue_lines = len([line for line in output.strip().split("\n") if line.strip()])
        if issue_lines > 0:
            result["warnings"] = issue_lines  # golint reports as warnings typically

    return result


def _is_lint_command(command: str) -> bool:
    """Check if command is a lint tool."""
    lint_commands = {
        "ruff", "eslint", "clippy", "golint", "staticcheck",
        "pylint", "flake8", "mypy", "pyright", "tsc",
    }
    parts = command.split()
    if not parts:
        return False
    cmd = parts[0].split("/")[-1]
    return cmd in lint_commands or any(lc in command.lower() for lc in lint_commands)


def _summarize_output(output: str, max_lines: int = 20) -> str:
    """Create a summary of command output."""
    lines = output.strip().split("\n")
    if len(lines) <= max_lines:
        return output.strip()

    # Take first few and last few lines
    head = lines[:5]
    tail = lines[-10:]
    return "\n".join(head + [f"\n... ({len(lines) - 15} lines omitted) ...\n"] + tail)


def run_validation_command(
    storage: ForgeLoopStorage,
    command: str,
    working_directory: str,
    phase_id: str | None = None,
    required_pass: bool = False,
    timeout_seconds: int = 300,
    output_capture: OutputCapture = OutputCapture.SUMMARY,
) -> ValidationRecord:
    """Run a validation command and record the result.

    Args:
        storage: ForgeLoop storage instance.
        command: Command to execute.
        working_directory: Working directory for command execution.
        phase_id: Optional phase ID to associate validation with.
        required_pass: If True, treat non-zero exit as error.
        timeout_seconds: Command timeout in seconds.
        output_capture: Output capture mode (summary or full).

    Returns:
        ValidationRecord with execution results.

    Raises:
        ValidationError: If command is not allowed or execution fails.
    """
    # Security check
    if not _is_safe_command(command):
        raise ValidationError(
            f"Command not in allowed list. First word must be one of: "
            f"{', '.join(sorted(ALLOWED_COMMAND_PREFIXES))}"
        )

    work_dir = Path(working_directory).resolve()
    if not work_dir.exists():
        raise ValidationError(f"Working directory does not exist: {work_dir}")

    # Execute command
    start_time = time.time()
    try:
        # Use shlex.split to properly handle arguments
        # This prevents shell injection while still allowing arguments
        args = shlex.split(command)
        result = subprocess.run(
            args,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
        output = stdout + ("\n" + stderr if stderr else "")
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        validation = storage.create_validation(
            phase_id=phase_id,
            command=command,
            status="fail",
            exit_code=-1,
            duration_seconds=duration,
            output_summary=f"Command timed out after {timeout_seconds} seconds",
        )
        return validation
    except FileNotFoundError as e:
        raise ValidationError(f"Command not found: {e}")
    except Exception as e:
        raise ValidationError(f"Command execution failed: {e}")

    duration = time.time() - start_time

    # Determine status
    if exit_code == 0:
        status = ValidationStatus.PASS
    elif required_pass:
        status = ValidationStatus.FAIL
    else:
        # Non-zero but not required to pass - treat as warning
        status = ValidationStatus.WARNING if exit_code != 0 else ValidationStatus.PASS

    # Parse outputs based on command type
    passed, failed = None, None
    errors, warnings, fixed = None, None, None

    if _is_lint_command(command):
        # Parse lint output
        lint_result = _parse_lint_output(output, command)
        errors = lint_result.get("errors")
        warnings = lint_result.get("warnings")
        fixed = lint_result.get("fixed")
    else:
        # Parse test output
        passed, failed = _parse_test_output(output, command)

    # Create summary
    if output_capture == OutputCapture.SUMMARY:
        output_summary = _summarize_output(output)
    else:
        output_summary = output

    # Save full log
    validation_id = f"VAL-{int(time.time() * 1000) % 100000:05d}"
    log_path = storage.save_log(validation_id, output)

    # Create validation record
    validation = storage.create_validation(
        phase_id=phase_id,
        command=command,
        status=status.value,
        exit_code=exit_code,
        duration_seconds=round(duration, 2),
        passed=passed,
        failed=failed,
        errors=errors,
        warnings=warnings,
        fixed=fixed,
        output_summary=output_summary[:2000],  # Limit summary size
        raw_output_path=str(log_path.relative_to(storage.root_path)),
    )

    return validation
