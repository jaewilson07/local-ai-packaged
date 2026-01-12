#!/usr/bin/env python3
"""
Script to run all pytest tests in the project.

This script:
1. Discovers all test directories (04-lambda/tests, 03-apps/discord-bot/tests, etc.)
2. Runs pytest in each test directory
3. Reports success/failure for each test suite
4. Provides a summary at the end

Usage:
    python scripts/run_all_tests.py
    python scripts/run_all_tests.py --verbose
    python scripts/run_all_tests.py --coverage
    python scripts/run_all_tests.py --filter lambda
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Test directories to run
TEST_DIRS = [
    {
        "name": "Lambda Server",
        "path": PROJECT_ROOT / "04-lambda" / "tests",
        "working_dir": PROJECT_ROOT / "04-lambda",
        "coverage_module": "server",
    },
    {
        "name": "Discord Bot",
        "path": PROJECT_ROOT / "03-apps" / "discord-bot" / "tests",
        "working_dir": PROJECT_ROOT / "03-apps" / "discord-bot",
        "coverage_module": None,  # Discord bot doesn't use coverage in CI
    },
]


def find_test_directories(filter_pattern: str = None) -> list[dict]:
    """
    Find all test directories.

    Args:
        filter_pattern: Optional pattern to filter test directories by name

    Returns:
        List of test directory info dictionaries
    """
    test_dirs = []

    for test_dir_info in TEST_DIRS:
        test_path = test_dir_info["path"]

        # Check if directory exists and has test files
        if not test_path.exists():
            continue

        # Check if there are any test files
        test_files = list(test_path.rglob("test_*.py"))
        if not test_files:
            continue

        # Apply filter if provided
        if filter_pattern:
            if filter_pattern.lower() not in test_dir_info["name"].lower():
                continue

        test_dirs.append(test_dir_info)

    return test_dirs


def run_pytest_tests(
    test_dir_info: dict,
    verbose: bool = False,
    coverage: bool = False,
    test_path: str | None = None,
) -> tuple[dict, bool, str]:
    """
    Run pytest tests for a test directory.

    Args:
        test_dir_info: Test directory info dictionary
        verbose: Whether to show verbose output
        coverage: Whether to run with coverage
        test_path: Optional specific test path to run

    Returns:
        Tuple of (test_dir_info, success, error_message)
    """
    name = test_dir_info["name"]
    test_path_obj = test_dir_info["path"]
    working_dir = test_dir_info["working_dir"]
    coverage_module = test_dir_info.get("coverage_module")

    # Try to use project-specific Python if available
    python_executable = sys.executable
    project_venv_python = working_dir / ".venv" / "bin" / "python"
    if project_venv_python.exists():
        python_executable = str(project_venv_python)

    # Build pytest command
    cmd = [python_executable, "-m", "pytest"]

    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    cmd.extend(["--tb=short"])

    # Add coverage if requested and supported
    if coverage and coverage_module:
        cmd.extend(
            [
                f"--cov={coverage_module}",
                "--cov-report=term",
                "--cov-report=term-missing",
            ]
        )

    # Add test path
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append(str(test_path_obj))

    # Run pytest
    try:
        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=not verbose,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            return (test_dir_info, True, "")
        else:
            # Combine stdout and stderr for better error reporting
            # Pytest outputs failures to stdout, not stderr
            error_parts = []
            if result.stdout:
                # Extract summary or error lines from stdout
                stdout_lines = result.stdout.split("\n")
                # Look for summary line (e.g., "X failed, Y passed")
                summary_lines = [
                    line
                    for line in stdout_lines
                    if "failed" in line.lower()
                    and ("passed" in line.lower() or "error" in line.lower())
                ]
                if summary_lines:
                    error_parts.append(summary_lines[-1])
                # Or get last few lines with errors
                elif any(
                    "error" in line.lower() or "failed" in line.lower() for line in stdout_lines
                ):
                    error_lines = [
                        line
                        for line in stdout_lines[-20:]
                        if any(
                            keyword in line.lower() for keyword in ["error", "failed", "exception"]
                        )
                    ]
                    if error_lines:
                        error_parts.append("\n".join(error_lines[:5]))  # First 5 error lines
            if result.stderr:
                error_parts.append(result.stderr[:300])
            error_msg = (
                "\n".join(error_parts)
                if error_parts
                else f"Tests failed with exit code {result.returncode}"
            )
            return (test_dir_info, False, error_msg)

    except Exception as e:
        error_msg = str(e)
        return (test_dir_info, False, error_msg)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run all pytest tests in the project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--filter",
        type=str,
        default=None,
        help="Filter test directories by pattern (e.g., 'lambda', 'discord')",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose pytest output",
    )
    parser.add_argument(
        "--coverage",
        "-c",
        action="store_true",
        help="Run with coverage reporting (where supported)",
    )
    parser.add_argument(
        "--test-path",
        type=str,
        default=None,
        help="Run specific test path (e.g., 'tests/test_auth/test_auth_service.py')",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue running tests even if one suite fails",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("RUNNING ALL TESTS")
    print("=" * 80)
    print(f"Project root: {PROJECT_ROOT}")
    if args.filter:
        print(f"Filter pattern: {args.filter}")
    if args.coverage:
        print("Coverage: Enabled")
    print()

    # Find all test directories
    test_dirs = find_test_directories(args.filter)

    if not test_dirs:
        print("⚠️  No test directories found")
        if args.filter:
            print(f"   (with filter: {args.filter})")
        sys.exit(0)

    print(f"Found {len(test_dirs)} test directory(ies):")
    for test_dir_info in test_dirs:
        print(f"  - {test_dir_info['name']}: {test_dir_info['path'].relative_to(PROJECT_ROOT)}")
    print()

    # Run tests in each directory
    results = []
    start_time = time.time()

    for i, test_dir_info in enumerate(test_dirs, 1):
        name = test_dir_info["name"]
        print(f"[{i}/{len(test_dirs)}] Running {name} tests...", end=" ", flush=True)

        if args.verbose:
            print()  # New line for verbose output

        result_test_dir_info, success, error_msg = run_pytest_tests(
            test_dir_info,
            verbose=args.verbose,
            coverage=args.coverage,
            test_path=args.test_path,
        )

        results.append((result_test_dir_info, success, error_msg))

        if not args.verbose:
            if success:
                print("✓")
            else:
                print("✗")

        if not success and not args.continue_on_error:
            print(f"\n❌ Test suite failed: {name}")
            if error_msg:
                print(f"   Error: {error_msg}")
            print("\nUse --continue-on-error to continue running remaining test suites")
            sys.exit(1)

    elapsed_time = time.time() - start_time

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed

    print(f"Total test suites: {len(results)}")
    print(f"✓ Passed: {passed}")
    print(f"✗ Failed: {failed}")
    print(f"⏱️  Total time: {elapsed_time:.2f}s")

    if failed > 0:
        print("\nFailed test suites:")
        for test_dir_info, success, error_msg in results:
            if not success:
                print(f"  - {test_dir_info['name']}")
                if error_msg:
                    print(f"    Error: {error_msg[:200]}")

    print("=" * 80)

    if failed == 0:
        print("🎉 All test suites passed!")
        sys.exit(0)
    else:
        print("⚠️  Some test suites failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
