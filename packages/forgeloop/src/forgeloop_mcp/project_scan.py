"""Project scanning utilities for ForgeLoop MCP."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .git_utils import get_git_state
from .models import DetectedFiles, PackageInfo, ProjectStateSnapshot


# File patterns for categorization
SOURCE_PATTERNS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".swift",
    ".kt", ".scala", ".r", ".R", ".jl", ".lua", ".sh", ".bash",
}

TEST_PATTERNS = {
    "test_", "_test.", ".test.", ".spec.", "_spec.",
    "tests/", "test/", "__tests__/", "spec/",
}

DOC_PATTERNS = {
    ".md", ".rst", ".txt", ".adoc",
    "docs/", "doc/", "documentation/",
}

CONFIG_PATTERNS = {
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "tsconfig.json", "webpack.config.js", "vite.config.ts", "vite.config.js",
    "Cargo.toml", "go.mod", "go.sum", "Gemfile", "composer.json",
    ".eslintrc", ".prettierrc", "jest.config", "pytest.ini", "tox.ini",
    "Makefile", "CMakeLists.txt", "Dockerfile", "docker-compose",
    ".env.example", "config.yaml", "config.json", "settings.json",
}

SCRIPT_PATTERNS = {
    "scripts/", "bin/", "tools/",
    ".sh", ".bash", ".zsh", ".ps1",
}

MIGRATION_PATTERNS = {
    "migrations/", "alembic/", "migrate/",
    "_migration.", ".migration.",
}

ENV_PATTERNS = {
    ".env", ".env.local", ".env.development", ".env.production",
    ".envrc", "secrets.yaml", "secrets.json",
}

README_PATTERNS = {
    "README", "readme", "Readme",
}

# Directories to skip
SKIP_DIRS = {
    ".git", ".svn", ".hg",
    "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".tox", ".nox", "venv", ".venv", "env", ".env",
    "dist", "build", "target", "out", ".next", ".nuxt",
    ".eggs", "*.egg-info", ".cache", ".parcel-cache",
    "coverage", "htmlcov", ".coverage",
    ".forgeloop",  # Skip our own directory
}


def _should_skip(name: str) -> bool:
    """Check if a directory should be skipped."""
    return name in SKIP_DIRS or name.startswith(".")


def _is_source_file(path: Path) -> bool:
    """Check if file is a source code file."""
    return path.suffix in SOURCE_PATTERNS


def _is_test_file(path: Path) -> bool:
    """Check if file is a test file."""
    path_str = str(path)
    name = path.name
    for pattern in TEST_PATTERNS:
        if pattern in path_str or name.startswith(pattern.rstrip("/")):
            return True
    return False


def _is_doc_file(path: Path) -> bool:
    """Check if file is a documentation file."""
    path_str = str(path)
    for pattern in DOC_PATTERNS:
        if pattern.startswith("."):
            if path.suffix == pattern:
                return True
        elif pattern in path_str:
            return True
    return False


def _is_config_file(path: Path) -> bool:
    """Check if file is a configuration file."""
    name = path.name
    for pattern in CONFIG_PATTERNS:
        if pattern in name:
            return True
    return False


def _is_script_file(path: Path) -> bool:
    """Check if file is a script."""
    path_str = str(path)
    for pattern in SCRIPT_PATTERNS:
        if pattern.startswith("."):
            if path.suffix == pattern:
                return True
        elif pattern in path_str:
            return True
    return False


def _is_migration_file(path: Path) -> bool:
    """Check if file is a migration."""
    path_str = str(path)
    for pattern in MIGRATION_PATTERNS:
        if pattern in path_str:
            return True
    return False


def _is_env_file(path: Path) -> bool:
    """Check if file is an environment file."""
    name = path.name
    for pattern in ENV_PATTERNS:
        if pattern in name or name.startswith(".env"):
            return True
    return False


def _is_readme_file(path: Path) -> bool:
    """Check if file is a README."""
    name = path.name
    for pattern in README_PATTERNS:
        if name.startswith(pattern):
            return True
    return False


def _extract_package_info(root: Path) -> PackageInfo | None:
    """Extract package information from project config files."""
    # Try package.json (Node.js)
    package_json = root / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            deps = list(data.get("dependencies", {}).keys())
            dev_deps = list(data.get("devDependencies", {}).keys())
            scripts = data.get("scripts", {})

            return PackageInfo(
                name=data.get("name"),
                version=data.get("version"),
                description=data.get("description"),
                package_type="node",
                dependencies=deps[:50],  # Limit to avoid huge lists
                dev_dependencies=dev_deps[:50],
                scripts=dict(list(scripts.items())[:20]),
                entry_point=data.get("main"),
            )
        except (json.JSONDecodeError, OSError):
            pass

    # Try pyproject.toml (Python)
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8")
            # Simple TOML parsing for common fields
            info = PackageInfo(package_type="python")

            # Extract name
            if 'name = "' in content:
                start = content.find('name = "') + 8
                end = content.find('"', start)
                if end > start:
                    info.name = content[start:end]

            # Extract version
            if 'version = "' in content:
                start = content.find('version = "') + 11
                end = content.find('"', start)
                if end > start:
                    info.version = content[start:end]

            # Extract description
            if 'description = "' in content:
                start = content.find('description = "') + 15
                end = content.find('"', start)
                if end > start:
                    info.description = content[start:end]

            # Extract dependencies (simplified)
            if "dependencies" in content:
                deps = []
                lines = content.split("\n")
                in_deps = False
                for line in lines:
                    if "dependencies" in line and "=" in line:
                        in_deps = True
                        continue
                    if in_deps:
                        if line.strip().startswith("]"):
                            break
                        if '"' in line:
                            dep = line.strip().strip('",')
                            if dep and not dep.startswith("#"):
                                # Extract package name (before any version specifier)
                                dep_name = dep.split(">=")[0].split("==")[0].split("<")[0].strip()
                                if dep_name:
                                    deps.append(dep_name)
                info.dependencies = deps[:50]

            return info
        except OSError:
            pass

    # Try Cargo.toml (Rust)
    cargo = root / "Cargo.toml"
    if cargo.exists():
        try:
            content = cargo.read_text(encoding="utf-8")
            info = PackageInfo(package_type="rust")

            if 'name = "' in content:
                start = content.find('name = "') + 8
                end = content.find('"', start)
                if end > start:
                    info.name = content[start:end]

            if 'version = "' in content:
                start = content.find('version = "') + 11
                end = content.find('"', start)
                if end > start:
                    info.version = content[start:end]

            return info
        except OSError:
            pass

    # Try go.mod (Go)
    gomod = root / "go.mod"
    if gomod.exists():
        try:
            content = gomod.read_text(encoding="utf-8")
            info = PackageInfo(package_type="go")

            lines = content.split("\n")
            for line in lines:
                if line.startswith("module "):
                    info.name = line.replace("module ", "").strip()
                    break

            return info
        except OSError:
            pass

    return None


def scan_project(
    root_path: str | Path,
    include_git: bool = True,
    include_file_tree: bool = True,
    include_recent_changes: bool = True,
    include_package_files: bool = True,
    include_test_files: bool = True,
    max_depth: int = 5,
) -> ProjectStateSnapshot:
    """Scan a project directory and return a structured snapshot.

    Args:
        root_path: Project root directory path.
        include_git: Include git state information.
        include_file_tree: Include file categorization.
        include_recent_changes: Include recently modified files.
        include_package_files: Include package/config files.
        include_test_files: Include test files in detection.
        max_depth: Maximum directory depth to scan.

    Returns:
        ProjectStateSnapshot with categorized project information.
    """
    root = Path(root_path).resolve()
    if not root.exists():
        raise ValueError(f"Path does not exist: {root}")
    if not root.is_dir():
        raise ValueError(f"Path is not a directory: {root}")

    snapshot = ProjectStateSnapshot(root_path=str(root))
    warnings = []
    open_questions = []

    # Git state
    if include_git:
        git_state = get_git_state(root)
        snapshot.git = git_state
        if git_state and git_state.dirty:
            warnings.append("Repository has uncommitted changes")

    # Package info extraction
    if include_package_files:
        package_info = _extract_package_info(root)
        snapshot.package_info = package_info

    # File tree scanning
    if include_file_tree:
        detected = DetectedFiles()
        recent_files = []
        now = datetime.now(timezone.utc)

        def scan_dir(dir_path: Path, depth: int = 0):
            if depth > max_depth:
                return

            try:
                entries = list(dir_path.iterdir())
            except PermissionError:
                warnings.append(f"Permission denied: {dir_path}")
                return

            for entry in entries:
                if entry.is_dir():
                    if not _should_skip(entry.name):
                        scan_dir(entry, depth + 1)
                elif entry.is_file():
                    rel_path = str(entry.relative_to(root))

                    # Check for recent modifications
                    if include_recent_changes:
                        try:
                            mtime = datetime.fromtimestamp(
                                entry.stat().st_mtime, tz=timezone.utc
                            )
                            # Files modified in last 24 hours
                            if (now - mtime).total_seconds() < 86400:
                                recent_files.append(rel_path)
                        except OSError:
                            pass

                    # Categorize files
                    if _is_readme_file(entry):
                        detected.readme.append(rel_path)
                    elif _is_env_file(entry):
                        detected.env_files.append(rel_path)
                        warnings.append(f"Environment file detected: {rel_path}")
                    elif _is_test_file(entry) and include_test_files:
                        detected.tests.append(rel_path)
                    elif _is_migration_file(entry):
                        detected.migrations.append(rel_path)
                    elif _is_script_file(entry):
                        detected.scripts.append(rel_path)
                    elif _is_config_file(entry) and include_package_files:
                        detected.config.append(rel_path)
                    elif _is_doc_file(entry):
                        detected.docs.append(rel_path)
                    elif _is_source_file(entry):
                        detected.source.append(rel_path)

        scan_dir(root)
        snapshot.detected_files = detected
        snapshot.recent_files = recent_files[:50]  # Limit recent files

    # Generate open questions
    if not snapshot.detected_files.tests:
        open_questions.append("No test files detected - is testing configured?")
    if not snapshot.detected_files.readme:
        open_questions.append("No README file detected - consider adding documentation")
    if snapshot.detected_files.env_files:
        open_questions.append("Environment files detected - are secrets excluded from git?")

    snapshot.warnings = warnings
    snapshot.open_questions = open_questions

    return snapshot
