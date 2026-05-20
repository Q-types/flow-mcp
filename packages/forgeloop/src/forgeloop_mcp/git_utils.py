"""Git utilities for ForgeLoop MCP."""

import subprocess
from pathlib import Path

from .models import GitState


def is_git_repo(path: Path) -> bool:
    """Check if path is inside a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def get_git_state(path: Path) -> GitState | None:
    """Get current git state for a repository."""
    if not is_git_repo(path):
        return None

    state = GitState()

    # Get current branch
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            state.branch = result.stdout.strip()
    except subprocess.SubprocessError:
        pass

    # Get current commit
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            state.commit = result.stdout.strip()[:12]  # Short hash
    except subprocess.SubprocessError:
        pass

    # Check for dirty state and changed files
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
            if lines:
                state.dirty = True
                for line in lines:
                    if len(line) >= 3:
                        status = line[:2]
                        filepath = line[3:].strip()
                        # Handle renamed files
                        if " -> " in filepath:
                            filepath = filepath.split(" -> ")[1]
                        if status[0] in "MADRCU":  # Staged changes
                            state.staged_files.append(filepath)
                        if status[1] in "MADRCU?":  # Unstaged or untracked
                            state.changed_files.append(filepath)
    except subprocess.SubprocessError:
        pass

    return state


def get_recent_commits(path: Path, count: int = 5) -> list[dict]:
    """Get recent commits."""
    commits = []
    if not is_git_repo(path):
        return commits

    try:
        result = subprocess.run(
            ["git", "log", f"-{count}", "--pretty=format:%H|%s|%ai|%an"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                parts = line.split("|", 3)
                if len(parts) == 4:
                    commits.append({
                        "hash": parts[0][:12],
                        "message": parts[1],
                        "date": parts[2],
                        "author": parts[3],
                    })
    except subprocess.SubprocessError:
        pass

    return commits


def get_current_commit_hash(path: Path) -> str | None:
    """Get the current commit hash."""
    if not is_git_repo(path):
        return None

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except subprocess.SubprocessError:
        pass

    return None
