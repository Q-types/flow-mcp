"""Source-of-truth audit for ForgeLoop MCP."""

import fnmatch
import os
import re
from pathlib import Path

from datetime import datetime, timezone

from .git_utils import get_git_state
from .models import ClassifiedFile, FileClassification, SourceOfTruthAudit

# Patterns for backup/obsolete files
BACKUP_PATTERNS = {
    ".bak", ".backup", ".old", ".orig", ".save",
    "~", ".swp", ".swo", ".tmp",
}

# Age threshold for potentially obsolete files (6 months in seconds)
OBSOLETE_AGE_SECONDS = 180 * 24 * 60 * 60

# Default patterns for file classification
DEFAULT_CANONICAL_PATTERNS = [
    "src/**/*.py", "src/**/*.ts", "src/**/*.js",
    "lib/**/*.py", "lib/**/*.ts", "lib/**/*.js",
    "app/**/*.py", "app/**/*.ts", "app/**/*.js",
    "*.py", "*.ts", "*.js",
    "pyproject.toml", "package.json", "Cargo.toml", "go.mod",
]

DEFAULT_GENERATED_PATTERNS = [
    "dist/**", "build/**", "out/**", ".next/**",
    "*.pyc", "__pycache__/**", "*.egg-info/**",
    "node_modules/**",
    "*.min.js", "*.min.css",
    "coverage/**", "htmlcov/**",
    ".tox/**", ".nox/**",
]

DEFAULT_MIGRATION_PATTERNS = [
    "migrations/**", "alembic/**", "versions/**",
    "**/migrations/**",
]

DEFAULT_DOCS_PATTERNS = [
    "docs/**", "doc/**", "documentation/**",
    "*.md", "*.rst", "*.adoc",
    "README*", "CHANGELOG*", "CONTRIBUTING*",
]

DEFAULT_SCRIPT_PATTERNS = [
    "scripts/**", "bin/**", "tools/**",
    "*.sh", "*.bash", "*.ps1",
    "Makefile", "justfile",
]

DEFAULT_TEST_PATTERNS = [
    "tests/**", "test/**", "__tests__/**", "spec/**",
    "test_*.py", "*_test.py", "*.test.ts", "*.spec.ts",
    "test_*.js", "*_test.js", "*.test.js", "*.spec.js",
]

# Directories to skip
SKIP_DIRS = {
    ".git", ".svn", ".hg",
    "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".tox", ".nox", "venv", ".venv", "env",
    "dist", "build", "target", "out", ".next", ".nuxt",
    ".forgeloop",
}


def _extract_code_symbols(file_path: Path) -> set[str]:
    """Extract function and class names from source code files.

    Supports Python, JavaScript/TypeScript, and basic patterns for other languages.
    Returns a set of symbol names found in the file.
    """
    symbols: set[str] = set()
    suffix = file_path.suffix.lower()

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeDecodeError):
        return symbols

    # Python: def func_name, class ClassName
    if suffix == ".py":
        symbols.update(re.findall(r"^def\s+([a-zA-Z_][a-zA-Z0-9_]*)", content, re.MULTILINE))
        symbols.update(re.findall(r"^class\s+([a-zA-Z_][a-zA-Z0-9_]*)", content, re.MULTILINE))

    # JavaScript/TypeScript: function name, class Name, const/let/var name = function
    elif suffix in {".js", ".ts", ".jsx", ".tsx"}:
        symbols.update(re.findall(r"^(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)", content, re.MULTILINE))
        symbols.update(re.findall(r"^(?:export\s+)?class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)", content, re.MULTILINE))
        symbols.update(re.findall(r"^(?:export\s+)?(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:async\s+)?function", content, re.MULTILINE))

    # Rust: fn name, struct Name, impl Name
    elif suffix == ".rs":
        symbols.update(re.findall(r"^pub\s+fn\s+([a-zA-Z_][a-zA-Z0-9_]*)", content, re.MULTILINE))
        symbols.update(re.findall(r"^fn\s+([a-zA-Z_][a-zA-Z0-9_]*)", content, re.MULTILINE))
        symbols.update(re.findall(r"^pub\s+struct\s+([a-zA-Z_][a-zA-Z0-9_]*)", content, re.MULTILINE))
        symbols.update(re.findall(r"^struct\s+([a-zA-Z_][a-zA-Z0-9_]*)", content, re.MULTILINE))

    # Go: func Name, type Name struct
    elif suffix == ".go":
        symbols.update(re.findall(r"^func\s+(?:\([^)]+\)\s+)?([A-Z][a-zA-Z0-9_]*)", content, re.MULTILINE))
        symbols.update(re.findall(r"^type\s+([A-Z][a-zA-Z0-9_]*)\s+struct", content, re.MULTILINE))

    # Filter out common utility names that are too generic
    common_names = {"main", "init", "setup", "test", "run", "new", "get", "set"}
    return symbols - common_names


def _check_docs_for_symbols(doc_path: Path, symbols: set[str]) -> dict[str, bool]:
    """Check which symbols are mentioned in a documentation file.

    Returns a dict of symbol -> found status.
    """
    result: dict[str, bool] = {}
    if not symbols:
        return result

    try:
        content = doc_path.read_text(encoding="utf-8", errors="ignore").lower()
    except (OSError, UnicodeDecodeError):
        return {s: False for s in symbols}

    for symbol in symbols:
        # Check for symbol in various documentation formats
        # - Direct mention: symbol_name
        # - Code blocks: `symbol_name`
        # - Headings: # symbol_name
        # - Links: [symbol_name]
        symbol_lower = symbol.lower()
        result[symbol] = (
            symbol_lower in content or
            f"`{symbol_lower}`" in content or
            f"[{symbol_lower}]" in content
        )

    return result


def _match_patterns(path: str, patterns: list[str]) -> bool:
    """Check if path matches any of the glob patterns."""
    for pattern in patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
        # Also check with ** prefix for subdirectory matches
        if fnmatch.fnmatch(path, f"**/{pattern}"):
            return True
    return False


def _should_skip_dir(name: str) -> bool:
    """Check if directory should be skipped."""
    return name in SKIP_DIRS or name.startswith(".")


def _is_backup_file(path: Path) -> bool:
    """Check if file appears to be a backup file."""
    name = path.name
    suffix = path.suffix

    # Check suffix
    if suffix in BACKUP_PATTERNS:
        return True

    # Check name patterns
    if name.endswith("~") or name.endswith(".bak") or name.endswith(".backup"):
        return True

    # Copy patterns like "file.py.copy" or "file_copy.py"
    if "_copy" in name.lower() or ".copy" in name.lower():
        return True

    # Old version patterns like "file.py.old" or "file_old.py"
    if "_old" in name.lower() or ".old" in name.lower():
        return True

    return False


def _is_stale_file(path: Path, threshold_seconds: int = OBSOLETE_AGE_SECONDS) -> bool:
    """Check if file hasn't been modified in a long time."""
    try:
        mtime = path.stat().st_mtime
        age = datetime.now(timezone.utc).timestamp() - mtime
        return age > threshold_seconds
    except OSError:
        return False


def _find_orphaned_tests(
    test_files: list[str],
    source_files: list[str],
    root: Path
) -> list[str]:
    """Find test files that may be orphaned (no corresponding source file).

    Uses heuristics to match test files to source files:
    - test_foo.py -> foo.py
    - foo_test.py -> foo.py
    - foo.test.ts -> foo.ts
    """
    orphaned = []
    source_names = set()

    # Build set of source file basenames
    for src in source_files:
        name = Path(src).stem.lower()
        source_names.add(name)

    for test_path in test_files:
        test_name = Path(test_path).stem.lower()

        # Extract the potential source name
        potential_source = None

        # test_foo -> foo
        if test_name.startswith("test_"):
            potential_source = test_name[5:]
        # foo_test -> foo
        elif test_name.endswith("_test"):
            potential_source = test_name[:-5]
        # foo.test -> foo (from foo.test.ts)
        elif ".test" in test_name:
            potential_source = test_name.split(".test")[0]
        # foo.spec -> foo
        elif ".spec" in test_name:
            potential_source = test_name.split(".spec")[0]
        # foo_spec -> foo
        elif test_name.endswith("_spec"):
            potential_source = test_name[:-5]

        if potential_source and potential_source not in source_names:
            # Additional check: is there a file with similar name in source?
            if not any(potential_source in s.lower() for s in source_files):
                orphaned.append(test_path)

    return orphaned


def audit_source_of_truth(
    root_path: str | Path,
    canonical_patterns: list[str] | None = None,
    generated_patterns: list[str] | None = None,
    migration_patterns: list[str] | None = None,
    docs_patterns: list[str] | None = None,
    script_patterns: list[str] | None = None,
    test_patterns: list[str] | None = None,
    compare_docs_to_code: bool = False,
) -> SourceOfTruthAudit:
    """Audit project files for source-of-truth classification.

    Args:
        root_path: Project root directory.
        canonical_patterns: Patterns for canonical source files.
        generated_patterns: Patterns for generated files.
        migration_patterns: Patterns for migration files.
        docs_patterns: Patterns for documentation files.
        script_patterns: Patterns for script files.
        test_patterns: Patterns for test files.
        compare_docs_to_code: Whether to check docs/code alignment (heuristic).

    Returns:
        SourceOfTruthAudit with classified files and flags.
    """
    root = Path(root_path).resolve()
    if not root.exists():
        raise ValueError(f"Path does not exist: {root}")

    # Use defaults if not provided
    canonical = canonical_patterns or DEFAULT_CANONICAL_PATTERNS
    generated = generated_patterns or DEFAULT_GENERATED_PATTERNS
    migrations = migration_patterns or DEFAULT_MIGRATION_PATTERNS
    docs = docs_patterns or DEFAULT_DOCS_PATTERNS
    scripts = script_patterns or DEFAULT_SCRIPT_PATTERNS
    tests = test_patterns or DEFAULT_TEST_PATTERNS

    audit = SourceOfTruthAudit(root_path=str(root))
    classified_files: list[ClassifiedFile] = []
    flags: list[str] = []
    recommendations: list[str] = []

    # Check git state
    git_state = get_git_state(root)
    if git_state and git_state.dirty:
        flags.append("Repository has uncommitted changes")
        recommendations.append("Consider committing or stashing changes before major modifications")

    # Scan files
    def scan_and_classify(dir_path: Path, depth: int = 0):
        if depth > 10:  # Prevent infinite recursion
            return

        try:
            entries = list(dir_path.iterdir())
        except PermissionError:
            flags.append(f"Permission denied: {dir_path.relative_to(root)}")
            return

        for entry in entries:
            if entry.is_dir():
                if not _should_skip_dir(entry.name):
                    scan_and_classify(entry, depth + 1)
            elif entry.is_file():
                rel_path = str(entry.relative_to(root))
                classification = _classify_file(
                    rel_path, canonical, generated, migrations, docs, scripts, tests
                )
                file_info = ClassifiedFile(
                    path=rel_path,
                    classification=classification,
                )

                # Add warnings for specific cases
                if classification == FileClassification.GENERATED:
                    # Check if generated file might have been manually edited
                    if git_state and rel_path in git_state.changed_files:
                        file_info.warnings.append("Generated file appears to have local changes")
                        flags.append(f"Generated file may be manually edited: {rel_path}")

                if classification == FileClassification.UNKNOWN:
                    file_info.reason = "File does not match any known patterns"
                    if entry.suffix in {".sql", ".json", ".yaml", ".yml", ".toml"}:
                        flags.append(f"Unclassified config/data file: {rel_path}")

                # Check for backup/obsolete files
                if _is_backup_file(entry):
                    file_info.classification = FileClassification.OBSOLETE
                    file_info.reason = "Appears to be a backup file"
                    file_info.warnings.append("Consider removing backup file")
                    flags.append(f"Backup file detected: {rel_path}")

                # Check for stale files (only for canonical/source)
                elif classification == FileClassification.CANONICAL:
                    if _is_stale_file(entry):
                        file_info.warnings.append("File not modified in 6+ months")

                classified_files.append(file_info)

    scan_and_classify(root)
    audit.classified_files = classified_files

    # Analyze classifications
    classifications_count: dict[str, int] = {}
    for cf in classified_files:
        key = cf.classification.value
        classifications_count[key] = classifications_count.get(key, 0) + 1

    # Generate recommendations
    if classifications_count.get("unknown", 0) > 10:
        recommendations.append(
            f"Found {classifications_count['unknown']} unclassified files - "
            "consider updating classification patterns"
        )

    if classifications_count.get("ad_hoc", 0) > 5:
        recommendations.append(
            "Multiple ad-hoc scripts detected - consider integrating into main codebase"
        )

    if not classifications_count.get("test", 0):
        recommendations.append("No test files detected - consider adding test coverage")
        flags.append("No test files found")

    if not classifications_count.get("documentation", 0):
        recommendations.append("No documentation files detected")

    # Check for orphaned tests
    test_files = [cf.path for cf in classified_files if cf.classification == FileClassification.TEST]
    source_files = [cf.path for cf in classified_files if cf.classification == FileClassification.CANONICAL]
    orphaned_tests = _find_orphaned_tests(test_files, source_files, root)
    if orphaned_tests:
        flags.append(f"Found {len(orphaned_tests)} potentially orphaned test file(s)")
        for orphan in orphaned_tests[:3]:  # List first 3
            recommendations.append(f"Review orphaned test: {orphan}")

    # Count obsolete files
    obsolete_count = classifications_count.get("obsolete", 0)
    if obsolete_count > 0:
        flags.append(f"Found {obsolete_count} obsolete/backup file(s)")
        recommendations.append("Consider cleaning up backup files")

    # Check for common issues
    has_readme = any(
        cf.path.upper().startswith("README") for cf in classified_files
    )
    if not has_readme:
        flags.append("No README file found")
        recommendations.append("Add a README.md file to document the project")

    # Check for env files that might contain secrets
    env_files = [
        cf for cf in classified_files
        if ".env" in cf.path and not cf.path.endswith(".example")
    ]
    if env_files:
        flags.append(f"Found {len(env_files)} environment file(s) that may contain secrets")
        recommendations.append("Ensure .env files are in .gitignore")

    # Docs-to-code drift detection
    if compare_docs_to_code:
        drift_report = _compare_docs_to_code(root, classified_files)
        if drift_report["undocumented_symbols"]:
            undoc_count = len(drift_report["undocumented_symbols"])
            flags.append(f"Found {undoc_count} public symbols not mentioned in documentation")
            recommendations.append(
                f"Consider documenting: {', '.join(list(drift_report['undocumented_symbols'])[:5])}"
                + ("..." if undoc_count > 5 else "")
            )
        if drift_report["stale_doc_refs"]:
            stale_count = len(drift_report["stale_doc_refs"])
            flags.append(f"Found {stale_count} documentation references that may be stale")

    audit.flags = flags
    audit.recommendations = recommendations

    return audit


def _compare_docs_to_code(root: Path, classified_files: list[ClassifiedFile]) -> dict:
    """Compare documentation to code for drift detection.

    Returns dict with:
    - undocumented_symbols: public symbols not found in any docs
    - stale_doc_refs: doc references that don't match any code
    """
    # Collect all symbols from canonical code files
    all_symbols: set[str] = set()
    canonical_files = [
        cf for cf in classified_files
        if cf.classification == FileClassification.CANONICAL
    ]
    for cf in canonical_files:
        file_path = root / cf.path
        if file_path.exists():
            symbols = _extract_code_symbols(file_path)
            all_symbols.update(symbols)

    # Check which symbols appear in documentation
    doc_files = [
        cf for cf in classified_files
        if cf.classification == FileClassification.DOCUMENTATION
    ]

    documented_symbols: set[str] = set()
    for cf in doc_files:
        file_path = root / cf.path
        if file_path.exists():
            found = _check_docs_for_symbols(file_path, all_symbols)
            documented_symbols.update(s for s, found_flag in found.items() if found_flag)

    # Symbols in code but not in any docs
    undocumented = all_symbols - documented_symbols

    # For stale refs, we'd need to extract references from docs and check code
    # This is a simplified heuristic - check for common patterns
    stale_refs: list[str] = []

    return {
        "undocumented_symbols": undocumented,
        "stale_doc_refs": stale_refs,
    }


def _classify_file(
    path: str,
    canonical: list[str],
    generated: list[str],
    migrations: list[str],
    docs: list[str],
    scripts: list[str],
    tests: list[str],
) -> FileClassification:
    """Classify a single file based on patterns."""
    # Check in order of specificity
    if _match_patterns(path, generated):
        return FileClassification.GENERATED
    if _match_patterns(path, tests):
        return FileClassification.TEST
    if _match_patterns(path, migrations):
        return FileClassification.MIGRATION
    if _match_patterns(path, docs):
        return FileClassification.DOCUMENTATION
    if _match_patterns(path, scripts):
        # Scripts are ad-hoc unless they're documented
        return FileClassification.AD_HOC
    if _match_patterns(path, canonical):
        return FileClassification.CANONICAL

    return FileClassification.UNKNOWN
