#!/usr/bin/env python
"""
Test runner script for Workflow Engine Service tests
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_path=None, verbose=False, coverage=False, markers=None):
    """Run pytest with specified options"""
    cmd = ["pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend([
            "--cov=src",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-fail-under=90"
        ])
    
    if markers:
        cmd.extend(["-m", markers])
    
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("tests/")
    
    # Add color output
    cmd.append("--color=yes")
    
    # Run tests
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Run Workflow Engine Service tests")
    parser.add_argument(
        "test_path",
        nargs="?",
        help="Specific test file or directory to run"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Run with coverage report"
    )
    parser.add_argument(
        "-m", "--markers",
        help="Run tests matching given mark expression"
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run only integration tests"
    )
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run only unit tests"
    )
    
    args = parser.parse_args()
    
    # Handle test type shortcuts
    if args.integration:
        args.markers = "integration"
    elif args.unit:
        args.markers = "not integration"
    
    # Run tests
    exit_code = run_tests(
        test_path=args.test_path,
        verbose=args.verbose,
        coverage=args.coverage,
        markers=args.markers
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()