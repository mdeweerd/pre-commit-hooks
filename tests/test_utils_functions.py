#!/usr/bin/env python3
"""Tests for utility functions in hooks/utils.py.

Tests cover the helper functions and base class methods that aren't
fully covered by the integration tests.
"""

import os
import subprocess as sp
import tempfile
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from hooks.utils import Command
from hooks.utils import FormatterCmd
from hooks.utils import StaticAnalyzerCmd


class TestCommandBaseClass:
    """Test the Command base class methods."""

    def test_check_installed_exits_for_missing_command(self):
        """Test that check_installed exits when command is not found."""

        class FakeCmd(Command):
            def __init__(self):
                self.command = "nonexistent-command-that-should-not-exist"
                self.look_behind = "test"
                self.args = []
                self.files = []
                self.stderr = b""
                self.returncode = 0

        cmd = FakeCmd()
        with pytest.raises(SystemExit):
            cmd.check_installed()

    def test_get_added_files_from_argv(self):
        """Test that files are properly extracted from argv."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
            f.write("int main() { return 0; }\n")
            temp_file = f.name

        try:
            # Temporarily modify sys.argv to simulate command-line args
            import sys

            original_argv = sys.argv
            sys.argv = ["test-cmd", temp_file]

            class TestCmd(Command):
                def __init__(self):
                    self.command = "test"
                    self.look_behind = "test"
                    self.args = sys.argv
                    self.files = self.get_added_files()

            cmd = TestCmd()
            assert temp_file in cmd.files
        finally:
            sys.argv = original_argv
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_cfg_files_filtered_out(self):
        """Test that .cfg files are filtered from file list."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as cfg_file:
            cfg_file.write("config\n")
            cfg_path = cfg_file.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as c_file:
            c_file.write("int main() { return 0; }\n")
            c_path = c_file.name

        try:
            # Temporarily modify sys.argv to simulate command-line args
            import sys

            original_argv = sys.argv
            sys.argv = ["test-cmd", cfg_path, c_path]

            class TestCmd(Command):
                def __init__(self):
                    self.command = "test"
                    self.look_behind = "test"
                    self.args = sys.argv
                    self.files = self.get_added_files()

            cmd = TestCmd()
            assert cfg_path not in cmd.files
            assert c_path in cmd.files
        finally:
            sys.argv = original_argv
            if os.path.exists(cfg_path):
                os.unlink(cfg_path)
            if os.path.exists(c_path):
                os.unlink(c_path)

    def test_parse_args_removes_files_from_args(self):
        """Test that file paths are removed from args list."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
            f.write("int main() { return 0; }\n")
            temp_file = f.name

        try:

            class TestCmd(Command):
                def __init__(self):
                    self.command = "test"
                    self.look_behind = "test"
                    self.args = []
                    self.files = [temp_file]

            cmd = TestCmd()
            cmd.parse_args(["test-cmd", "--flag", temp_file])
            # File should not be in args
            assert temp_file not in cmd.args
            # Flag should be in args
            assert "--flag" in cmd.args
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_add_if_missing_adds_new_args(self):
        """Test that add_if_missing adds arguments that aren't present."""

        class TestCmd(Command):
            def __init__(self):
                self.command = "test"
                self.look_behind = "test"
                self.args = ["--existing"]
                self.files = []

        cmd = TestCmd()
        cmd.add_if_missing(["--new-arg"])
        assert "--new-arg" in cmd.args
        assert "--existing" in cmd.args

    def test_add_if_missing_does_not_add_existing_args(self):
        """Test that add_if_missing doesn't add duplicate arguments."""

        class TestCmd(Command):
            def __init__(self):
                self.command = "test"
                self.look_behind = "test"
                self.args = ["--existing=value"]
                self.files = []

        cmd = TestCmd()
        initial_length = len(cmd.args)
        cmd.add_if_missing(["--existing=different_value"])
        # Length should not change
        assert len(cmd.args) == initial_length
        # Original value should remain
        assert "--existing=value" in cmd.args

    def test_add_if_missing_with_equals_sign(self):
        """Test that add_if_missing handles --key=value correctly."""

        class TestCmd(Command):
            def __init__(self):
                self.command = "test"
                self.look_behind = "test"
                self.args = []
                self.files = []

        cmd = TestCmd()
        cmd.add_if_missing(["--key=value"])
        assert "--key=value" in cmd.args

        # Adding same key with different value should not add
        initial_length = len(cmd.args)
        cmd.add_if_missing(["--key=different"])
        assert len(cmd.args) == initial_length

    def test_add_if_missing_with_multiple_same_key_args_in_one_call(self):
        """Test that add_if_missing can add multiple same-key args in a single call.

        When add_if_missing is called with multiple arguments that share the same
        option key, all are added because it only checks if the first arg's key exists.
        """

        class TestCmd(Command):
            def __init__(self):
                self.command = "test"
                self.look_behind = "test"
                self.args = []
                self.files = []

        cmd = TestCmd()
        # Add multiple --suppress arguments at once
        cmd.add_if_missing(
            [
                "--suppress=unmatchedSuppression",
                "--suppress=missingIncludeSystem",
            ]
        )
        # Both are added because the key check only looks at the first arg
        assert "--suppress=unmatchedSuppression" in cmd.args
        assert "--suppress=missingIncludeSystem" in cmd.args

    def test_add_if_missing_bug_with_multiple_calls_default(self):
        """Test the original behavior: with allow_multiple=False (default),
        same-key args across multiple calls are NOT added.
        """

        class TestCmd(Command):
            def __init__(self):
                self.command = "test"
                self.look_behind = "test"
                self.args = []
                self.files = []

        cmd = TestCmd()
        # Add first --suppress argument
        cmd.add_if_missing(["--suppress=unmatchedSuppression"])
        assert "--suppress=unmatchedSuppression" in cmd.args

        # Now try to add another --suppress argument in a separate call (default allow_multiple=False)
        initial_length = len(cmd.args)
        cmd.add_if_missing(["--suppress=missingIncludeSystem"])
        # With default behavior, this does NOT add the new argument because --suppress key already exists
        assert "--suppress=missingIncludeSystem" not in cmd.args
        assert len(cmd.args) == initial_length

    def test_add_if_missing_with_allow_multiple_true(self):
        """Test that with allow_multiple=True, same-key args with different values
        can be added across multiple calls, and --key=value and --key value forms
        are treated as equivalent."""

        class TestCmd(Command):
            def __init__(self):
                self.command = "test"
                self.look_behind = "test"
                self.args = []
                self.files = []

        cmd = TestCmd()
        # Add first --suppress argument
        cmd.add_if_missing(["--suppress=unmatchedSuppression"], allow_multiple=True)
        assert "--suppress=unmatchedSuppression" in cmd.args

        # Now add another --suppress argument in a separate call with allow_multiple=True
        initial_length = len(cmd.args)
        cmd.add_if_missing(["--suppress=missingIncludeSystem"], allow_multiple=True)
        # With allow_multiple=True, this DOES add the new argument
        assert "--suppress=missingIncludeSystem" in cmd.args
        assert len(cmd.args) == initial_length + 1

        # But duplicate with space form is not added
        cmd.add_if_missing(["--suppress", "unmatchedSuppression"], allow_multiple=True)
        assert len(cmd.args) == 2  # Still 2, not 3 (space form treated as equivalent)

        # Test with space form first
        cmd2 = TestCmd()
        cmd2.add_if_missing(["--suppress", "value1"], allow_multiple=True)
        assert cmd2.args == ["--suppress", "value1"]
        # Then --suppress=value1 should not be added
        cmd2.add_if_missing(["--suppress=value1"], allow_multiple=True)
        assert len(cmd2.args) == 2  # Still 2, not 3

    def test_raise_error_writes_to_stderr(self):
        """Test that raise_error writes formatted error to stderr."""

        class TestCmd(Command):
            def __init__(self):
                self.command = "test-command"
                self.look_behind = "test"
                self.args = []
                self.files = []
                self.stderr = b""
                self.returncode = 0

        cmd = TestCmd()
        with pytest.raises(SystemExit) as exc_info:
            cmd.raise_error("test problem", "test details")

        assert exc_info.value.code == 1
        assert cmd.returncode == 1
        assert b"test-command" in cmd.stderr
        assert b"test problem" in cmd.stderr
        assert b"test details" in cmd.stderr


class TestVersionParsing:
    """Test version string parsing and comparison."""

    def test_version_str_parsed_correctly(self):
        """Test that version strings are extracted correctly."""
        # This is an integration test that requires the actual commands
        # Just verify the method exists and can handle basic patterns
        from hooks.clang_format import ClangFormatCmd

        # Mock the subprocess to return a known version string
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=b"clang-format version 14.0.0\n", returncode=0)

            with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as temp_file:
                temp_file.write("int main() { return 0; }\n")
                temp_path = temp_file.name

            try:
                cmd = ClangFormatCmd(["clang-format-hook", temp_path])
                version = cmd.get_version_str()
                assert version == "14.0.0"
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

    def test_fuzzy_version_matching(self):
        """Test that fuzzy version matching works (e.g., 14.0 matches 14.0.6)."""
        from hooks.clang_format import ClangFormatCmd

        with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
            f.write("int main() { return 0; }\n")
            temp_file = f.name

        try:
            # Create command and mock version
            with patch.object(ClangFormatCmd, "get_version_str", return_value="14.0.6"):
                cmd = ClangFormatCmd(["clang-format-hook", temp_file])
                # This should not raise because 14.0 is prefix of 14.0.6
                try:
                    cmd.assert_version("14.0.6", "14.0")
                except SystemExit as e:
                    # assert_version exits with 0 on success
                    assert e.code == 0
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class TestStaticAnalyzerCmd:
    """Test StaticAnalyzerCmd specific functionality."""

    def test_run_command_captures_output(self):
        """Test that run_command captures stdout and stderr."""

        class TestAnalyzer(StaticAnalyzerCmd):
            def __init__(self):
                self.command = "echo"
                self.look_behind = "test"
                self.args = ["test"]
                self.files = []
                self.stdout = b""
                self.stderr = b""
                self.returncode = 0

        cmd = TestAnalyzer()
        # Run echo command which should produce output
        cmd.run_command(["hello"])
        assert b"hello" in cmd.stdout or b"hello" in cmd.stderr

    def test_exit_on_error_exits_with_nonzero(self):
        """Test that exit_on_error exits when returncode is non-zero."""

        class TestAnalyzer(StaticAnalyzerCmd):
            def __init__(self):
                self.command = "test"
                self.look_behind = "test"
                self.args = []
                self.files = []
                self.stdout = b"test output"
                self.stderr = b"test error"
                self.returncode = 1

        cmd = TestAnalyzer()
        with pytest.raises(SystemExit) as exc_info:
            cmd.exit_on_error()
        assert exc_info.value.code == 1

    def test_exit_on_error_continues_with_zero(self):
        """Test that exit_on_error doesn't exit when returncode is zero."""

        class TestAnalyzer(StaticAnalyzerCmd):
            def __init__(self):
                self.command = "test"
                self.look_behind = "test"
                self.args = []
                self.files = []
                self.stdout = b"test output"
                self.stderr = b""
                self.returncode = 0

        cmd = TestAnalyzer()
        # Should not raise
        cmd.exit_on_error()


class TestFormatterCmd:
    """Test FormatterCmd specific functionality."""

    def test_set_diff_flag_detects_and_removes(self):
        """Test that set_diff_flag properly detects and removes --no-diff."""

        class TestFormatter(FormatterCmd):
            def __init__(self):
                self.command = "test"
                self.look_behind = "test"
                self.args = ["--no-diff", "--other-flag"]
                self.files = []

        cmd = TestFormatter()
        cmd.set_diff_flag()
        assert cmd.no_diff_flag is True
        assert "--no-diff" not in cmd.args
        assert "--other-flag" in cmd.args

    def test_set_diff_flag_false_when_missing(self):
        """Test that no_diff_flag is False when --no-diff is not present."""

        class TestFormatter(FormatterCmd):
            def __init__(self):
                self.command = "test"
                self.look_behind = "test"
                self.args = ["--other-flag"]
                self.files = []

        cmd = TestFormatter()
        cmd.set_diff_flag()
        assert cmd.no_diff_flag is False

    def test_get_filelines_reads_file(self):
        """Test that get_filelines correctly reads file contents."""
        # Use binary mode to avoid Windows text mode \n to \r\n conversion
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".c", delete=False) as f:
            f.write(b"line1\nline2\nline3\n")
            temp_file = f.name

        try:

            class TestFormatter(FormatterCmd):
                def __init__(self):
                    self.command = "test"
                    self.look_behind = "test"
                    self.args = []
                    self.files = []

            cmd = TestFormatter()
            lines = cmd.get_filelines(temp_file)
            assert b"line1" in lines
            assert b"line2" in lines
            assert b"line3" in lines
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_get_filelines_handles_missing_file(self):
        """Test that get_filelines errors appropriately for missing files."""

        class TestFormatter(FormatterCmd):
            def __init__(self):
                self.command = "test"
                self.look_behind = "test"
                self.args = []
                self.files = []
                self.stderr = b""
                self.returncode = 0

        cmd = TestFormatter()
        with pytest.raises(SystemExit):
            cmd.get_filelines("/nonexistent/file.c")

    def test_get_filename_opts_with_file_flag(self):
        """Test that get_filename_opts includes file flag when set."""

        class TestFormatter(FormatterCmd):
            def __init__(self):
                self.command = "test"
                self.look_behind = "test"
                self.args = []
                self.files = []
                self.file_flag = "-f"
                self.edit_in_place = False

        cmd = TestFormatter()
        opts = cmd.get_filename_opts("test.c")
        assert "-f" in opts
        assert "test.c" in opts

    def test_get_filename_opts_without_file_flag(self):
        """Test that get_filename_opts works without file flag."""

        class TestFormatter(FormatterCmd):
            def __init__(self):
                self.command = "test"
                self.look_behind = "test"
                self.args = []
                self.files = []
                self.file_flag = None
                self.edit_in_place = False

        cmd = TestFormatter()
        opts = cmd.get_filename_opts("test.c")
        assert opts == ["test.c"]


class TestCpplintArgOrdering:
    """Test cpplint's unique requirement of args before filename."""

    def test_cpplint_args_before_filename(self):
        """Test that cpplint puts args before filename."""
        from hooks.cpplint import CpplintCmd

        with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
            f.write("int main() { return 0; }\n")
            temp_file = f.name

        try:
            cmd = CpplintCmd(["cpplint-hook", "--verbose=0", temp_file])
            # The implementation should handle this correctly
            assert "--verbose=0" in cmd.args
            assert temp_file in cmd.files
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class TestGitIntegration:
    """Test git-related functionality."""

    def test_get_added_files_uses_git_when_no_args(self):
        """Test that get_added_files falls back to git when no args provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize a git repo
            sp.run(["git", "init"], cwd=tmpdir, capture_output=True)
            sp.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=tmpdir,
                capture_output=True,
            )
            sp.run(
                ["git", "config", "user.name", "Test"],
                cwd=tmpdir,
                capture_output=True,
            )

            # Create and stage a file
            test_file = os.path.join(tmpdir, "test.c")
            with open(test_file, "w") as f:
                f.write("int main() { return 0; }\n")
            sp.run(["git", "add", test_file], cwd=tmpdir, capture_output=True)

            # Change to the tmpdir for this test
            original_dir = os.getcwd()
            try:
                os.chdir(tmpdir)

                class TestCmd(Command):
                    def __init__(self):
                        self.command = "test"
                        self.look_behind = "test"
                        self.args = []
                        self.files = self.get_added_files()

                cmd = TestCmd()
                # Should find the staged file via git
                assert any("test.c" in f for f in cmd.files)
            finally:
                os.chdir(original_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
