#!/usr/bin/env python3
"""
Parse pytest JSON output and extract key metrics.

This script processes pytest JSON reports and extracts:
- Test counts (passed/failed/skipped)
- Coverage data
- Failure details
- Grouped failures by test file
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / ".cursor" / "test_results"


def parse_pytest_json(report_file: Path) -> dict[str, Any]:
    """
    Parse pytest JSON report file.

    Args:
        report_file: Path to pytest JSON report

    Returns:
        Structured dictionary with parsed data
    """
    if not report_file.exists():
        return {"error": f"Report file not found: {report_file}"}

    try:
        with report_file.open() as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse JSON: {e}"}

    summary = data.get("summary", {})
    tests = data.get("tests", [])

    # Group tests by file
    tests_by_file = defaultdict(list)
    for test in tests:
        nodeid = test.get("nodeid", "")
        # Extract file from nodeid (e.g., "test_tools.py::test_search_web_success")
        if "::" in nodeid:
            file_part = nodeid.split("::")[0]
            # Remove directory path, keep just filename
            filename = Path(file_part).name
            tests_by_file[filename].append(test)
        else:
            tests_by_file[nodeid].append(test)

    # Extract failures
    failures = []
    for test in tests:
        if test.get("outcome") == "failed":
            call_data = test.get("call", {})
            failures.append(
                {
                    "nodeid": test.get("nodeid", ""),
                    "file": (
                        Path(test.get("nodeid", "")).name.split("::")[0]
                        if "::" in test.get("nodeid", "")
                        else ""
                    ),
                    "error": call_data.get("longrepr", ""),
                    "duration": call_data.get("duration", 0),
                    "setup": test.get("setup", {}).get("outcome", ""),
                    "teardown": test.get("teardown", {}).get("outcome", ""),
                }
            )

    # Group failures by file
    failures_by_file = defaultdict(list)
    for failure in failures:
        file = failure["file"] or "unknown"
        failures_by_file[file].append(failure)

    # Extract errors (different from failures)
    errors = []
    for test in tests:
        if test.get("outcome") == "error":
            call_data = test.get("call", {})
            errors.append(
                {
                    "nodeid": test.get("nodeid", ""),
                    "file": (
                        Path(test.get("nodeid", "")).name.split("::")[0]
                        if "::" in test.get("nodeid", "")
                        else ""
                    ),
                    "error": call_data.get("longrepr", ""),
                    "duration": call_data.get("duration", 0),
                }
            )

    return {
        "summary": {
            "total": summary.get("total", 0),
            "passed": summary.get("passed", 0),
            "failed": summary.get("failed", 0),
            "skipped": summary.get("skipped", 0),
            "error": summary.get("error", 0),
            "duration": summary.get("duration", 0),
        },
        "tests_by_file": {
            filename: {
                "total": len(file_tests),
                "passed": sum(1 for t in file_tests if t.get("outcome") == "passed"),
                "failed": sum(1 for t in file_tests if t.get("outcome") == "failed"),
                "skipped": sum(1 for t in file_tests if t.get("outcome") == "skipped"),
                "error": sum(1 for t in file_tests if t.get("outcome") == "error"),
            }
            for filename, file_tests in tests_by_file.items()
        },
        "failures": failures,
        "failures_by_file": dict(failures_by_file),
        "errors": errors,
        "raw_data": data,
    }


def parse_coverage_json(coverage_file: Path) -> dict[str, Any]:
    """
    Parse coverage JSON report.

    Args:
        coverage_file: Path to coverage.json file

    Returns:
        Dictionary with coverage metrics
    """
    if not coverage_file.exists():
        return {}

    try:
        with coverage_file.open() as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

    totals = data.get("totals", {})
    files = data.get("files", {})

    # Calculate per-file coverage
    file_coverage = {}
    for filepath, file_data in files.items():
        # Extract just the filename
        filename = Path(filepath).name
        file_totals = file_data.get("summary", {})
        if file_totals.get("num_statements", 0) > 0:
            file_coverage[filename] = {
                "percent": round(
                    (file_totals.get("covered_lines", 0) / file_totals.get("num_statements", 1))
                    * 100,
                    2,
                ),
                "covered_lines": file_totals.get("covered_lines", 0),
                "num_statements": file_totals.get("num_statements", 0),
            }

    return {
        "totals": {
            "percent_covered": (
                round((totals.get("covered_lines", 0) / totals.get("num_statements", 1)) * 100, 2)
                if totals.get("num_statements", 0) > 0
                else 0
            ),
            "covered_lines": totals.get("covered_lines", 0),
            "num_statements": totals.get("num_statements", 0),
            "missing_lines": totals.get("missing_lines", 0),
        },
        "files": file_coverage,
    }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Parse pytest JSON test results")
    parser.add_argument(
        "--report",
        type=str,
        default=str(RESULTS_DIR / "pytest_report.json"),
        help="Path to pytest JSON report file",
    )
    parser.add_argument("--coverage", type=str, help="Path to coverage.json file")
    parser.add_argument("--output", type=str, help="Output file for parsed results (JSON)")

    args = parser.parse_args()

    # Parse pytest report
    report_file = Path(args.report)
    parsed = parse_pytest_json(report_file)

    if "error" in parsed:
        print(f"Error: {parsed['error']}", file=sys.stderr)
        sys.exit(1)

    # Parse coverage if provided
    if args.coverage:
        coverage_file = Path(args.coverage)
        parsed["coverage"] = parse_coverage_json(coverage_file)

    # Output results
    if args.output:
        output_path = Path(args.output)
        with output_path.open("w") as f:
            json.dump(parsed, f, indent=2)
        print(f"Parsed results saved to: {args.output}")
    else:
        # Print summary
        summary = parsed["summary"]
        print("\nTest Summary:")
        print(f"  Total: {summary['total']}")
        print(f"  Passed: {summary['passed']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Skipped: {summary['skipped']}")
        print(f"  Errors: {summary['error']}")

        if parsed.get("coverage"):
            cov = parsed["coverage"]["totals"]
            print(f"\nCoverage: {cov['percent_covered']}%")

        if parsed["failures"]:
            print("\nFailures by file:")
            for file, failures in parsed["failures_by_file"].items():
                print(f"  {file}: {len(failures)} failures")


if __name__ == "__main__":
    main()
