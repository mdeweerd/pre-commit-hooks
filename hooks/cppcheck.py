#!/usr/bin/env python3
"""Wrapper script for cppcheck."""

import os
import shutil
import sys
import tempfile
from typing import List

from hooks.utils import StaticAnalyzerCmd


class CppcheckCmd(StaticAnalyzerCmd):
    """Class for the cppcheck command."""

    command = "cppcheck"
    lookbehind = "Cppcheck "

    def __init__(self, args: List[str]):
        super().__init__(self.command, self.lookbehind, args)
        self.parse_args(args)
        self.cppcheck_build_dir = None

        # quiet for stdout purposes
        self.add_if_missing(["-q"])
        # make cppcheck behave as expected for pre-commit
        self.add_if_missing(["--error-exitcode=1"])
        # Enable all of the checks
        self.add_if_missing(["--enable=warning,performance,portability,information,style,missingInclude"])
        # Per https://github.com/pocc/pre-commit-hooks/pull/30, suppress messages
        self.add_if_missing(
            [
                "--suppress=unmatchedSuppression",
                "--suppress=missingIncludeSystem",
            ],
            allow_multiple=True,
        )
        self.set_j_value()

    def cleanup_build_dir(self):
        """Remove the temporary build directory if it exists."""
        if self.cppcheck_build_dir is not None and os.path.exists(self.cppcheck_build_dir):
            try:
                shutil.rmtree(self.cppcheck_build_dir)
            except OSError:
                pass
            self.cppcheck_build_dir = None

    def get_j_value(self):
        """Get number of parallel threads currently set in options"""
        for i, arg in enumerate(self.args):
            if arg == "-j":
                # -j followed by value
                if i + 1 < len(self.args) and not self.args[i + 1].startswith("-"):
                    return self.args[i + 1]
            elif arg.startswith("-j") and len(arg) > 2:
                # -jN format (no = sign, just -j followed by digits)
                return arg[2:]

    def set_j_value(self):
        """
        Set the value of -j option if not already present based on # processors
        """
        if self.get_j_value() is not None:
            return

        # Get number of available processors
        try:
            import multiprocessing

            num_cpus = multiprocessing.cpu_count()
        except (ImportError, NotImplementedError):
            # Fallback if multiprocessing is not available
            num_cpus = 1

        # Only add -j if > 1, otherwise single-threaded is fine
        if num_cpus > 1:
            self.args.extend(["-j", str(num_cpus)])

        return

    def set_create_build_dir_if_needed(self):
        """Set & create cppcheck_build_dir unless it is already set or exists in the arguments."""

        if self.cppcheck_build_dir is not None:
            return

        try:
            j_value_int = int(self.get_j_value())
        except (ValueError, TypeError):
            j_value_int = None

        # Check if --cppcheck-build-dir is present
        has_build_dir = any(arg.startswith("--cppcheck-build-dir") for arg in self.args)
        if not has_build_dir:
            # Create a unique temporary directory for parallel processing
            self.cppcheck_build_dir = tempfile.mkdtemp(prefix="cppcheck_")
            self.add_if_missing([f"--cppcheck-build-dir={self.cppcheck_build_dir}"])

    def run(self):
        """Run cppcheck"""
        if not self.files:
            return

        try:
            self.set_create_build_dir_if_needed()
            self.run_command(self.args + ["--file-list=-"], input_data="\n".join(self.files).encode())
            self.exit_on_error()
        finally:
            # Remove, also when interrupted (CTRL-C)
            self.cleanup_build_dir()


def main(argv: List[str] = sys.argv):
    cmd = CppcheckCmd(argv)
    cmd.run()


if __name__ == "__main__":
    main()
