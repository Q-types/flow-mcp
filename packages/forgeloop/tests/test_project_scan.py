"""Tests for project scanning."""

import tempfile
from pathlib import Path

import pytest

from forgeloop_mcp.project_scan import scan_project


@pytest.fixture
def sample_project():
    """Create a sample project structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create directories
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "docs").mkdir()

        # Create files
        (root / "src" / "main.py").write_text("print('hello')")
        (root / "tests" / "test_main.py").write_text("def test_main(): pass")
        (root / "README.md").write_text("# Project")
        (root / "pyproject.toml").write_text("[project]\nname = 'test'")

        yield root


class TestProjectScan:
    """Tests for project scanning."""

    def test_scan_basic(self, sample_project):
        """Test basic project scan."""
        snapshot = scan_project(sample_project)

        # Use resolve() to handle symlinks (e.g., /var -> /private/var on macOS)
        assert snapshot.root_path == str(sample_project.resolve())
        assert len(snapshot.detected_files.source) > 0
        assert len(snapshot.detected_files.tests) > 0
        assert len(snapshot.detected_files.readme) > 0

    def test_scan_detects_config(self, sample_project):
        """Test that config files are detected."""
        snapshot = scan_project(sample_project)

        config_files = snapshot.detected_files.config
        assert any("pyproject.toml" in f for f in config_files)

    def test_scan_detects_docs(self, sample_project):
        """Test that documentation is detected."""
        snapshot = scan_project(sample_project)

        readme_files = snapshot.detected_files.readme
        assert any("README" in f for f in readme_files)

    def test_scan_max_depth(self, sample_project):
        """Test max depth limiting."""
        # Create deep structure
        deep = sample_project / "a" / "b" / "c" / "d" / "e" / "f"
        deep.mkdir(parents=True)
        (deep / "deep.py").write_text("# deep file")

        # Scan with low depth
        snapshot = scan_project(sample_project, max_depth=2)

        # Deep file should not be found
        assert not any("deep.py" in f for f in snapshot.detected_files.source)

    def test_scan_without_git(self, sample_project):
        """Test scanning without git."""
        snapshot = scan_project(sample_project, include_git=False)

        assert snapshot.git is None

    def test_scan_nonexistent_path(self):
        """Test scanning nonexistent path raises error."""
        with pytest.raises(ValueError):
            scan_project("/nonexistent/path/xyz")
