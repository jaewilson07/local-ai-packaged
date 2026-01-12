#!/usr/bin/env python3
"""
Script to run Deep Research Agent tests with reporting.

This script:
1. Runs all tests in 04-lambda/tests/test_deep_research/
2. Generates JSON report with timestamps
3. Calculates coverage metrics
4. Outputs formatted results
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
LAMBDA_DIR = PROJECT_ROOT / "04-lambda"
TEST_DIR = LAMBDA_DIR / "tests" / "test_deep_research"
RESULTS_DIR = PROJECT_ROOT / ".cursor" / "test_results"

# Ensure results directory exists
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def run_tests(
    test_file: str | None = None,
    test_case: str | None = None,
    coverage: bool = False,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    Run pytest tests and return results.

    Args:
        test_file: Optional specific test file to run
        test_case: Optional specific test case to run
        coverage: Whether to run with coverage
        verbose: Whether to show verbose output

    Returns:
        Dictionary with test results
    """
    # Use uv run pytest if available, otherwise fall back to sys.executable
    # This ensures we use the correct Python environment with all dependencies
    import shutil

    uv_cmd = shutil.which("uv")

    if uv_cmd:
        cmd = [
            uv_cmd,
            "run",
            "pytest",
            "-v" if verbose else "-q",
            "--tb=short",
            "--json-report",
            "--json-report-file",
            str(RESULTS_DIR / "pytest_report.json"),
        ]
    else:
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-v" if verbose else "-q",
            "--tb=short",
            "--json-report",
            "--json-report-file",
            str(RESULTS_DIR / "pytest_report.json"),
        ]

    # Add coverage if requested
    if coverage:
        cmd.extend(
            [
                "--cov=server.projects.deep_research",
                "--cov-report=json",
                "--cov-report=term",
            ]
        )

    # Add test target
    if test_case:
        # Specific test case: test_file::test_case
        if test_file:
            cmd.append(f"{TEST_DIR / test_file}::{test_case}")
        else:
            cmd.append(f"{TEST_DIR}::{test_case}")
    elif test_file:
        # Specific test file
        cmd.append(str(TEST_DIR / test_file))
    else:
        # All tests
        cmd.append(str(TEST_DIR))

    print(f"\n{'=' * 80}")
    print("RUNNING DEEP RESEARCH TESTS")
    print(f"{'=' * 80}")
    print(f"Command: {' '.join(cmd)}\n")

    start_time = time.time()
    result = subprocess.run(cmd, cwd=LAMBDA_DIR, capture_output=True, text=True, check=False)
    duration = time.time() - start_time

    # Parse JSON report if it exists
    report_data = {}
    report_file = RESULTS_DIR / "pytest_report.json"
    if report_file.exists():
        try:
            with report_file.open() as f:
                report_data = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Could not parse JSON report from {report_file}")

    # Parse coverage if it exists
    coverage_data = {}
    if coverage:
        coverage_file = LAMBDA_DIR / "coverage.json"
        if coverage_file.exists():
            try:
                with coverage_file.open() as f:
                    coverage_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

    # Extract summary from report
    summary = report_data.get("summary", {})
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    skipped = summary.get("skipped", 0)
    errors = summary.get("error", 0)

    # Extract failures
    failures = []
    for test in report_data.get("tests", []):
        if test.get("outcome") == "failed":
            failures.append(
                {
                    "nodeid": test.get("nodeid", ""),
                    "call": test.get("call", {}).get("longrepr", ""),
                    "duration": test.get("call", {}).get("duration", 0),
                }
            )

    # Calculate coverage percentage
    coverage_percent = 0.0
    if coverage_data:
        totals = coverage_data.get("totals", {})
        if totals.get("covered_lines", 0) > 0:
            coverage_percent = (
                totals.get("covered_lines", 0) / totals.get("num_statements", 1)
            ) * 100

    results = {
        "timestamp": datetime.now().isoformat(),
        "duration": round(duration, 2),
        "exit_code": result.returncode,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
            "success_rate": round((passed / total * 100) if total > 0 else 0, 2),
        },
        "coverage": {
            "enabled": coverage,
            "percent": round(coverage_percent, 2),
            "data": coverage_data,
        },
        "failures": failures,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }

    return results


def save_results(results: dict[str, Any]) -> Path:
    """Save test results to JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"deep_research_{timestamp}.json"
    filepath = RESULTS_DIR / filename

    with filepath.open("w") as f:
        json.dump(results, f, indent=2)

    # Also save as latest.json
    latest_file = RESULTS_DIR / "latest.json"
    with latest_file.open("w") as f:
        json.dump(results, f, indent=2)

    return filepath


def print_summary(results: dict[str, Any]):
    """Print formatted test summary."""
    summary = results["summary"]
    coverage = results["coverage"]

    print(f"\n{'=' * 80}")
    print("TEST SUMMARY")
    print(f"{'=' * 80}")
    print(f"Duration: {results['duration']}s")
    print(f"Total Tests: {summary['total']}")
    print(f"  ✓ Passed: {summary['passed']}")
    print(f"  ✗ Failed: {summary['failed']}")
    print(f"  ⊘ Skipped: {summary['skipped']}")
    print(f"  ⚠ Errors: {summary['errors']}")
    print(f"Success Rate: {summary['success_rate']}%")

    if coverage["enabled"]:
        print(f"\nCoverage: {coverage['percent']}%")

    if results["failures"]:
        print(f"\n{'=' * 80}")
        print("FAILURES")
        print(f"{'=' * 80}")
        for i, failure in enumerate(results["failures"], 1):
            print(f"\n{i}. {failure['nodeid']}")
            if failure.get("call"):
                # Print first few lines of error
                error_lines = failure["call"].split("\n")[:5]
                for line in error_lines:
                    print(f"   {line}")

    print(f"\n{'=' * 80}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Deep Research Agent tests with reporting")
    parser.add_argument("--file", type=str, help="Run specific test file (e.g., test_tools.py)")
    parser.add_argument(
        "--case", type=str, help="Run specific test case (e.g., test_search_web_success)"
    )
    parser.add_argument("--coverage", action="store_true", help="Run with coverage reporting")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode (less verbose output)")

    args = parser.parse_args()

    # Run tests
    results = run_tests(
        test_file=args.file, test_case=args.case, coverage=args.coverage, verbose=not args.quiet
    )

    # Save results
    filepath = save_results(results)
    print(f"\nResults saved to: {filepath}")

    # Print summary
    print_summary(results)

    # Exit with appropriate code
    sys.exit(0 if results["summary"]["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
