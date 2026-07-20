#!/usr/bin/env python3
"""Unit tests for cppcheck hook."""

import os
import sys
import tempfile

import pytest

from hooks.cppcheck import CppcheckCmd


class TestCppcheckAddJOption:
    """Test the add_j_option method."""

    def setup_method(self):
        """Create temporary test files."""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test.c")
        with open(self.test_file, "w") as f:
            f.write("int main() { return 0; }\n")

    def teardown_method(self):
        """Clean up temporary files."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_add_j_option_when_provided_with_space(self):
        """Test that -j option is not duplicated when provided as -j 2."""
        sys.argv = ["cppcheck-hook", "-j", "2", self.test_file]
        cmd = CppcheckCmd(sys.argv)
        # Check that only one -j option exists
        j_args = [arg for arg in cmd.args if arg.startswith("-j")]
        assert len(j_args) == 1, f"Expected 1 -j option, found {len(j_args)}: {j_args}"
        assert "-j" in cmd.args, "Expected -j in args"
        assert "2" in cmd.args, "Expected 2 in args"

    def test_add_j_option_when_provided_without_space(self):
        """Test that -j option is not duplicated when provided as -j2."""
        sys.argv = ["cppcheck-hook", "-j2", self.test_file]
        cmd = CppcheckCmd(sys.argv)
        # Check that only one -j option exists
        j_args = [arg for arg in cmd.args if arg.startswith("-j")]
        assert len(j_args) == 1, f"Expected 1 -j option, found {len(j_args)}: {j_args}"
        assert "-j2" in cmd.args, "Expected -j2 in args"

    def test_with_multiple_files(self):
        """Test Multiple files."""
        test_file2 = os.path.join(self.test_dir, "test2.c")
        with open(test_file2, "w") as f:
            f.write("int foo() { return 1; }\n")

        sys.argv = ["cppcheck-hook", self.test_file, test_file2]
        cmd = CppcheckCmd(sys.argv)
        # Check that both files are in cmd.files
        assert len(cmd.files) == 2, f"Expected 2 files, found {len(cmd.files)}"


class TestCppcheckFileList:
    """Test the file list functionality."""

    def setup_method(self):
        """Create temporary test files."""
        self.test_dir = tempfile.mkdtemp()
        self.test_file1 = os.path.join(self.test_dir, "test1.c")
        self.test_file2 = os.path.join(self.test_dir, "test2.c")
        with open(self.test_file1, "w") as f:
            f.write("int main() { return 0; }\n")
        with open(self.test_file2, "w") as f:
            f.write("int foo() { return 1; }\n")

    def teardown_method(self):
        """Clean up temporary files."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_file_list_created(self):
        """Test that a file list is created with all files."""
        sys.argv = ["cppcheck-hook", self.test_file1, self.test_file2]
        cmd = CppcheckCmd(sys.argv)
        # The files should be in cmd.files
        assert len(cmd.files) == 2, f"Expected 2 files, found {len(cmd.files)}"
        assert self.test_file1 in cmd.files, f"Expected {self.test_file1} in files"
        assert self.test_file2 in cmd.files, f"Expected {self.test_file2} in files"

    def test_single_file(self):
        """Test that single file works correctly."""
        sys.argv = ["cppcheck-hook", self.test_file1]
        cmd = CppcheckCmd(sys.argv)
        # The file should be in cmd.files
        assert len(cmd.files) == 1, f"Expected 1 file, found {len(cmd.files)}"
        assert self.test_file1 in cmd.files, f"Expected {self.test_file1} in files"
