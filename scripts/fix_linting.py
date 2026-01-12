#!/usr/bin/env python3
"""
Script to automatically fix linting issues using ruff and other tools.

This script:
1. Runs ruff with --fix to auto-fix linting issues
2. Runs black to format code
3. Optionally runs pre-commit hooks if configured
4. Provides a summary of fixes applied

Usage:
    python scripts/fix_linting.py
    python scripts/fix_linting.py --check-only  # Check without fixing
    python scripts/fix_linting.py --ruff-only    # Only run ruff
    python scripts/fix_linting.py --black-only   # Only run black
    python scripts/fix_linting.py --path <path>  # Fix specific path
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent


def run_command(
    cmd: list[str],
    cwd: Path | None = None,
    check: bool = False,
    capture_output: bool = True,
) -> tuple[bool, str, str]:
    """
    Run a command and return success status and output.

    Args:
        cmd: Command to run
        cwd: Working directory
        check: Whether to raise on non-zero exit
        capture_output: Whether to capture stdout/stderr

    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            capture_output=capture_output,
            text=True,
            check=check,
        )
        return (
            result.returncode == 0,
            result.stdout or "",
            result.stderr or "",
        )
    except subprocess.CalledProcessError as e:
        return (
            False,
            e.stdout or "",
            e.stderr or "",
        )
    except Exception as e:
        return (False, "", str(e))


def run_ruff_fix(
    path: Path | None = None,
    check_only: bool = False,
) -> tuple[bool, str]:
    """
    Run ruff to fix linting issues.

    Args:
        path: Optional path to fix (defaults to project root)
        check_only: If True, only check without fixing

    Returns:
        Tuple of (success, output)
    """
    cmd = [sys.executable, "-m", "ruff", "check"]

    if not check_only:
        cmd.append("--fix")

    if path:
        cmd.append(str(path))
    else:
        cmd.append(".")

    success, stdout, stderr = run_command(cmd)
    output = stdout + stderr

    return success, output


def run_ruff_format(
    path: Path | None = None,
    check_only: bool = False,
) -> tuple[bool, str]:
    """
    Run ruff format to format code.

    Args:
        path: Optional path to format (defaults to project root)
        check_only: If True, only check without formatting

    Returns:
        Tuple of (success, output)
    """
    cmd = [sys.executable, "-m", "ruff", "format"]

    if check_only:
        cmd.append("--check")

    if path:
        cmd.append(str(path))
    else:
        cmd.append(".")

    success, stdout, stderr = run_command(cmd)
    output = stdout + stderr

    return success, output


def run_black(
    path: Path | None = None,
    check_only: bool = False,
) -> tuple[bool, str]:
    """
    Run black to format code.

    Args:
        path: Optional path to format (defaults to project root)
        check_only: If True, only check without formatting

    Returns:
        Tuple of (success, output)
    """
    cmd = [sys.executable, "-m", "black"]

    if check_only:
        cmd.append("--check")
    else:
        cmd.append("--quiet")

    if path:
        cmd.append(str(path))
    else:
        cmd.append(".")

    success, stdout, stderr = run_command(cmd)
    output = stdout + stderr

    return success, output


def run_precommit(
    check_only: bool = False,
) -> tuple[bool, str]:
    """
    Run pre-commit hooks.

    Args:
        check_only: If True, only check without fixing

    Returns:
        Tuple of (success, output)
    """
    cmd = ["pre-commit", "run"]

    if check_only:
        cmd.append("--check")
    else:
        cmd.append("--all-files")

    success, stdout, stderr = run_command(cmd)
    output = stdout + stderr

    return success, output


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automatically fix linting issues using ruff and other tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Check for issues without fixing them",
    )
    parser.add_argument(
        "--ruff-only",
        action="store_true",
        help="Only run ruff (skip black and pre-commit)",
    )
    parser.add_argument(
        "--black-only",
        action="store_true",
        help="Only run black (skip ruff and pre-commit)",
    )
    parser.add_argument(
        "--no-precommit",
        action="store_true",
        help="Skip pre-commit hooks",
    )
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Fix specific path (file or directory)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose output",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("FIXING LINTING ISSUES")
    print("=" * 80)
    print(f"Project root: {PROJECT_ROOT}")
    if args.path:
        print(f"Target path: {args.path}")
    if args.check_only:
        print("Mode: CHECK ONLY (no fixes will be applied)")
    print()

    path = Path(args.path) if args.path else None
    if path and not path.exists():
        print(f"❌ Error: Path does not exist: {path}")
        sys.exit(1)

    if path and path.is_absolute():
        path = path.relative_to(PROJECT_ROOT)

    results = []
    start_time = time.time()

    # Run ruff check --fix
    if not args.black_only:
        print("Running ruff check...", end=" ", flush=True)
        success, output = run_ruff_fix(path, check_only=args.check_only)
        results.append(("ruff check", success, output))

        if args.verbose:
            print()  # New line for verbose output
            if output:
                print(output)

        if not args.verbose:
            if success:
                print("✓")
            else:
                print("✗")
                if output:
                    print(output[:500])

    # Run ruff format
    if not args.black_only:
        print("Running ruff format...", end=" ", flush=True)
        success, output = run_ruff_format(path, check_only=args.check_only)
        results.append(("ruff format", success, output))

        if args.verbose:
            print()  # New line for verbose output
            if output:
                print(output)

        if not args.verbose:
            if success:
                print("✓")
            else:
                print("✗")
                if output:
                    print(output[:500])

    # Run black
    if not args.ruff_only:
        print("Running black...", end=" ", flush=True)
        success, output = run_black(path, check_only=args.check_only)
        results.append(("black", success, output))

        if args.verbose:
            print()  # New line for verbose output
            if output:
                print(output)

        if not args.verbose:
            if success:
                print("✓")
            else:
                print("✗")
                if output:
                    print(output[:500])

    # Run pre-commit if configured
    if not args.no_precommit and not args.ruff_only and not args.black_only:
        precommit_config = PROJECT_ROOT / ".pre-commit-config.yaml"
        if not precommit_config.exists():
            precommit_config = PROJECT_ROOT / ".pre-commit-config.yml"

        if precommit_config.exists():
            print("Running pre-commit hooks...", end=" ", flush=True)
            success, output = run_precommit(check_only=args.check_only)
            results.append(("pre-commit", success, output))

            if args.verbose:
                print()  # New line for verbose output
                if output:
                    print(output)

            if not args.verbose:
                if success:
                    print("✓")
                else:
                    print("✗")
                    if output:
                        print(output[:500])
        else:
            print("Skipping pre-commit (no config found)")

    elapsed_time = time.time() - start_time

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed

    for tool_name, success, output in results:
        status = "✓" if success else "✗"
        print(f"{status} {tool_name}")
        if not success and output and args.verbose:
            print(f"   {output[:200]}")

    print(f"\n⏱️  Total time: {elapsed_time:.2f}s")
    print("=" * 80)

    if args.check_only:
        if failed == 0:
            print("🎉 No linting issues found!")
            sys.exit(0)
        else:
            print("⚠️  Some linting issues found (use without --check-only to fix)")
            sys.exit(1)
    elif failed == 0:
        print("🎉 All linting fixes applied successfully!")
        sys.exit(0)
    else:
        print("⚠️  Some tools encountered errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
