#!/usr/bin/env python3
"""
Track debugging issues over time with resolution status.

This script:
- Creates issue entries from test failures
- Links issues to test cases
- Tracks resolution status (open/in-progress/resolved)
- Generates issue summary for scratchpad
- Detects recurring issues
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / ".cursor" / "test_results"
ISSUES_FILE = RESULTS_DIR / "issues.json"


def load_issues() -> list[dict[str, Any]]:
    """Load existing issues from JSON file."""
    if not ISSUES_FILE.exists():
        return []

    try:
        with ISSUES_FILE.open() as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_issues(issues: list[dict[str, Any]]):
    """Save issues to JSON file."""
    ISSUES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with ISSUES_FILE.open("w") as f:
        json.dump(issues, f, indent=2)


def create_issue(
    test_nodeid: str, error_message: str, test_file: str, first_seen: str | None = None
) -> dict[str, Any]:
    """Create a new issue entry."""
    issue_id = f"DR-TEST-{len(load_issues()) + 1:03d}"
    return {
        "id": issue_id,
        "test_nodeid": test_nodeid,
        "test_file": test_file,
        "error_message": error_message[:500],  # Truncate long messages
        "status": "open",
        "first_seen": first_seen or datetime.now().isoformat(),
        "last_seen": datetime.now().isoformat(),
        "occurrences": 1,
        "resolution": None,
        "resolved_at": None,
        "notes": [],
    }


def find_existing_issue(
    issues: list[dict[str, Any]], test_nodeid: str, error_message: str
) -> dict[str, Any] | None:
    """Find existing issue by test nodeid and error message."""
    # Normalize error message for comparison (first 200 chars)
    error_key = error_message[:200].strip()

    for issue in issues:
        if (
            issue["test_nodeid"] == test_nodeid
            and issue["error_message"][:200].strip() == error_key
        ):
            return issue
    return None


def add_issues_from_failures(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add new issues from test failures."""
    issues = load_issues()
    new_issues = []
    updated_issues = []

    for failure in failures:
        nodeid = failure.get("nodeid", "")
        error = failure.get("error", failure.get("call", ""))
        file = failure.get("file", "")

        # Find existing issue
        existing = find_existing_issue(issues, nodeid, error)

        if existing:
            # Update existing issue
            existing["last_seen"] = datetime.now().isoformat()
            existing["occurrences"] += 1
            updated_issues.append(existing["id"])
        else:
            # Create new issue
            issue = create_issue(nodeid, error, file)
            issues.append(issue)
            new_issues.append(issue["id"])

    save_issues(issues)

    return {"new": new_issues, "updated": updated_issues, "total": len(issues)}


def list_issues(status: str | None = None) -> list[dict[str, Any]]:
    """List issues, optionally filtered by status."""
    issues = load_issues()

    if status:
        issues = [i for i in issues if i["status"] == status]

    return issues


def resolve_issue(issue_id: str, resolution: str):
    """Mark an issue as resolved."""
    issues = load_issues()

    for issue in issues:
        if issue["id"] == issue_id:
            issue["status"] = "resolved"
            issue["resolution"] = resolution
            issue["resolved_at"] = datetime.now().isoformat()
            save_issues(issues)
            return True

    return False


def get_issue_summary() -> dict[str, Any]:
    """Get summary of all issues."""
    issues = load_issues()

    by_status = defaultdict(int)
    by_file = defaultdict(int)
    recurring = []

    for issue in issues:
        by_status[issue["status"]] += 1
        by_file[issue["test_file"]] += 1
        if issue["occurrences"] > 1:
            recurring.append(issue)

    return {
        "total": len(issues),
        "by_status": dict(by_status),
        "by_file": dict(by_file),
        "recurring": len(recurring),
        "recurring_issues": [
            {"id": i["id"], "test": i["test_nodeid"], "occurrences": i["occurrences"]}
            for i in recurring
        ],
    }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Track debugging issues from test failures")
    parser.add_argument("--add", type=str, help="Add issues from test results JSON file")
    parser.add_argument("--list", action="store_true", help="List all issues")
    parser.add_argument(
        "--status",
        type=str,
        choices=["open", "in-progress", "resolved"],
        help="Filter issues by status",
    )
    parser.add_argument("--resolve", type=str, help="Resolve an issue by ID")
    parser.add_argument("--resolution", type=str, help="Resolution note (use with --resolve)")
    parser.add_argument("--summary", action="store_true", help="Show issue summary")

    args = parser.parse_args()

    if args.add:
        # Add issues from test results
        results_file = Path(args.add)
        if not results_file.exists():
            print(f"Error: File not found: {results_file}", file=sys.stderr)
            sys.exit(1)

        with results_file.open() as f:
            results = json.load(f)

        failures = results.get("failures", [])
        result = add_issues_from_failures(failures)

        print(f"Added {len(result['new'])} new issues")
        print(f"Updated {len(result['updated'])} existing issues")
        print(f"Total issues: {result['total']}")

    elif args.resolve:
        if not args.resolution:
            print("Error: --resolution required when resolving an issue", file=sys.stderr)
            sys.exit(1)

        if resolve_issue(args.resolve, args.resolution):
            print(f"Issue {args.resolve} marked as resolved")
        else:
            print(f"Error: Issue {args.resolve} not found", file=sys.stderr)
            sys.exit(1)

    elif args.summary:
        summary = get_issue_summary()
        print("\nIssue Summary:")
        print(f"  Total Issues: {summary['total']}")
        print("  By Status:")
        for status, count in summary["by_status"].items():
            print(f"    {status}: {count}")
        print(f"  Recurring Issues: {summary['recurring']}")
        if summary["recurring_issues"]:
            print("  Recurring Issue Details:")
            for issue in summary["recurring_issues"][:5]:  # Show top 5
                print(f"    {issue['id']}: {issue['test']} ({issue['occurrences']} occurrences)")

    elif args.list:
        issues = list_issues(args.status)
        if not issues:
            print("No issues found")
        else:
            print(f"\nIssues ({len(issues)}):")
            for issue in issues:
                status_icon = {"open": "○", "in-progress": "◐", "resolved": "✓"}.get(
                    issue["status"], "?"
                )
                print(f"\n{status_icon} {issue['id']}: {issue['test_nodeid']}")
                print(f"   Status: {issue['status']}")
                print(f"   Occurrences: {issue['occurrences']}")
                print(f"   Last seen: {issue['last_seen']}")
                if issue["status"] == "resolved":
                    print(f"   Resolved: {issue['resolved_at']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
