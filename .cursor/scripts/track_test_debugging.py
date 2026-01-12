#!/usr/bin/env python3
"""
Analyze test results and update tracking documents.

This script:
- Parses JSON test reports
- Extracts failure details
- Updates scratchpad with new issues
- Generates summary for AGENTS.md update
- Tracks issue resolution over time
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / ".cursor" / "test_results"
SCRATCHPAD = PROJECT_ROOT / ".cursor" / "scratchpad.md"


def load_latest_results() -> dict[str, Any] | None:
    """Load the latest test results."""
    latest_file = RESULTS_DIR / "latest.json"
    if not latest_file.exists():
        return None

    try:
        with latest_file.open() as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def update_scratchpad(results: dict[str, Any], issues_summary: dict[str, Any]):
    """Update scratchpad with test run information."""
    if not SCRATCHPAD.exists():
        print(f"Warning: Scratchpad not found at {SCRATCHPAD}")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    summary = results["summary"]
    coverage = results.get("coverage", {})

    # Determine status
    errors = summary.get("error", summary.get("errors", 0))
    if summary["failed"] == 0 and errors == 0:
        status = "PASSED"
    elif summary["passed"] > 0:
        status = "PARTIAL"
    else:
        status = "FAILED"

    # Build test run entry
    entry = f"""
### [{timestamp}] - Test Run #{len(issues_summary.get("runs", [])) + 1}
- **Status**: {status}
- **Tests Run**: {summary["passed"]}/{summary["total"]} passed
- **Coverage**: {coverage.get("percent", 0)}%
- **Duration**: {results["duration"]}s
- **Issues Found**: {len(results.get("failures", []))} failures, {errors} errors
- **Notes**:
"""

    # Add failure details if any
    if results.get("failures"):
        entry += "  - Failures:\n"
        for i, failure in enumerate(results["failures"][:5], 1):  # Limit to 5
            nodeid = failure.get("nodeid", "unknown")
            entry += f"    {i}. {nodeid}\n"
        if len(results["failures"]) > 5:
            entry += f"    ... and {len(results['failures']) - 5} more\n"

    # Add issue tracking summary
    if issues_summary.get("new"):
        entry += f"  - New issues: {len(issues_summary['new'])}\n"
    if issues_summary.get("updated"):
        entry += f"  - Updated issues: {len(issues_summary['updated'])}\n"

    entry += "\n---\n"

    # Read existing scratchpad
    with SCRATCHPAD.open() as f:
        content = f.read()

    # Find the "Test Run History" section and insert after it
    if "## Test Run History" in content:
        # Insert after the header
        insert_pos = content.find("## Test Run History") + len("## Test Run History")
        # Find the next section or end of file
        next_section = content.find("\n## ", insert_pos)
        if next_section == -1:
            next_section = len(content)

        # Insert the new entry
        new_content = content[:next_section] + "\n" + entry + content[next_section:]
    else:
        # Append to end if section doesn't exist
        new_content = content + "\n## Test Run History\n" + entry

    # Write back
    with SCRATCHPAD.open("w") as f:
        f.write(new_content)

    print(f"✓ Updated scratchpad: {SCRATCHPAD}")


def generate_agents_summary(results: dict[str, Any], issues_summary: dict[str, Any]) -> str:
    """Generate summary markdown for AGENTS.md update."""
    summary = results["summary"]
    coverage = results.get("coverage", {})

    # Get test file status from parsed results
    # We'll need to parse the pytest report to get per-file stats
    # For now, use summary data

    md = f"""## Testing Status

**Last Updated**: {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Test Coverage**: {coverage.get("percent", 0)}%
**Total Tests**: {summary["total"]}
**Passing**: {summary["passed"]}
**Failing**: {summary["failed"]}
**Errors**: {summary["errors"]}
**Skipped**: {summary["skipped"]}
**Success Rate**: {summary.get("success_rate", 0)}%

### Test Files
- `test_tools.py`: Status TBD (run tests to update)
- `test_linear_agent.py`: Status TBD (run tests to update)
- `test_orchestrator_nodes.py`: Status TBD (run tests to update)
- `test_storm_workflow.py`: Status TBD (run tests to update)
- `test_graph_enhanced.py`: Status TBD (run tests to update)
- `test_state_models.py`: Status TBD (run tests to update)

### Known Issues
"""

    if issues_summary.get("open_issues"):
        for issue_id in issues_summary["open_issues"][:5]:  # Limit to 5
            md += f"- {issue_id}: See scratchpad for details\n"
    else:
        md += "- None\n"

    md += "\n### Recent Test Run\n"
    md += f"- **Date**: {results.get('timestamp', 'N/A')}\n"
    md += f"- **Duration**: {results['duration']}s\n"
    md += f"- **Result**: {summary['passed']}/{summary['total']} passed\n"

    return md


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Track test debugging and update documentation")
    parser.add_argument(
        "--results",
        type=str,
        default=str(RESULTS_DIR / "latest.json"),
        help="Path to test results JSON file",
    )
    parser.add_argument(
        "--update-scratchpad",
        action="store_true",
        help="Update scratchpad with test run information",
    )
    parser.add_argument(
        "--generate-agents-summary", action="store_true", help="Generate summary for AGENTS.md"
    )
    parser.add_argument("--add-issues", action="store_true", help="Add issues from test failures")

    args = parser.parse_args()

    # Load results
    results_file = Path(args.results)
    if not results_file.exists():
        print(f"Error: Results file not found: {results_file}", file=sys.stderr)
        sys.exit(1)

    with results_file.open() as f:
        results = json.load(f)

    # Add issues if requested
    issues_summary = {"new": [], "updated": [], "open_issues": []}
    if args.add_issues:
        # Import and use track_issues
        sys.path.insert(0, str(Path(__file__).parent))
        try:
            from track_issues import add_issues_from_failures

            issues_result = add_issues_from_failures(results.get("failures", []))
            issues_summary["new"] = issues_result["new"]
            issues_summary["updated"] = issues_result["updated"]

            # Get open issues
            from track_issues import list_issues

            open_issues = list_issues("open")
            issues_summary["open_issues"] = [i["id"] for i in open_issues]
        except ImportError:
            print("Warning: Could not import track_issues module")

    # Update scratchpad
    if args.update_scratchpad:
        update_scratchpad(results, issues_summary)

    # Generate AGENTS.md summary
    if args.generate_agents_summary:
        summary = generate_agents_summary(results, issues_summary)
        print("\n" + "=" * 80)
        print("AGENTS.md UPDATE SUMMARY")
        print("=" * 80)
        print(summary)
        print("\nCopy the above section to update AGENTS.md")

    # Print summary
    summary = results["summary"]
    print("\nTest Summary:")
    print(f"  Total: {summary['total']}")
    print(f"  Passed: {summary['passed']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Errors: {summary['errors']}")

    if issues_summary.get("new"):
        print(f"\n  New Issues: {len(issues_summary['new'])}")
    if issues_summary.get("updated"):
        print(f"  Updated Issues: {len(issues_summary['updated'])}")


if __name__ == "__main__":
    main()
