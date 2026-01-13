#!/usr/bin/env python3
"""
Script to run all sample files in the project.

This script:
1. Discovers all Python sample files in the sample/ directory
2. Executes each sample file
3. Reports success/failure for each sample
4. Provides a summary at the end

Validation:
Samples are validated through multiple mechanisms:

1. **Exit Code Validation**: Each sample should exit with code 0 on success, non-zero on failure.
   - Successful samples return 0
   - Failed samples return 1 (or raise exceptions)

2. **Verification Helpers**: Many samples use verification helpers from `sample/shared/verification_helpers.py`:
   - `verify_search_results()` - Validates search results are returned
   - `verify_rag_data()` - Validates RAG data via API endpoints
   - `verify_calendar_data()` - Validates calendar events via API
   - `verify_neo4j_data()` - Validates Neo4j nodes/relationships via API
   - `verify_mongodb_data()` - Validates MongoDB documents via API
   - `verify_supabase_data()` - Validates Supabase tables via API
   - `verify_storage_data()` - Validates MinIO storage files via API
   - `verify_loras_data()` - Validates ComfyUI LoRA models via API

3. **API Verification**: Samples that create persistent data verify via REST API:
   - Internal network: `http://lambda-server:8000` (no auth required)
   - External network: `https://api.datacrew.space` (requires Cloudflare Access JWT)
   - Verification functions automatically handle authentication

4. **Result Validation**: Samples validate their own results:
   - Check that expected data was created/retrieved
   - Verify data structure and content
   - Ensure minimum expected counts are met

5. **Error Handling**: All samples include:
   - Try/except blocks for graceful error handling
   - Proper cleanup in finally blocks
   - Clear error messages for debugging

Prerequisites:
- Dependencies installed: Run `python setup/install_clis.py` or `cd 04-lambda && uv pip install -e ".[test,samples]"`
- Services running: MongoDB, Neo4j, Ollama, etc. (as needed by samples)
- Environment variables: Configure `.env` or Infisical with required variables
- Authentication: For external API calls, set `CF_ACCESS_JWT` environment variable

Usage:
    python scripts/run_all_samples.py
    python scripts/run_all_samples.py --verbose
    python scripts/run_all_samples.py --filter calendar
    python scripts/run_all_samples.py --timeout 600 --continue-on-error
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Sample directory
SAMPLE_DIR = PROJECT_ROOT / "sample"


def find_sample_files(filter_pattern: str = None) -> list[Path]:
    """
    Find all sample Python files.

    Args:
        filter_pattern: Optional pattern to filter sample files by name/path

    Returns:
        List of sample file paths
    """
    if not SAMPLE_DIR.exists():
        return []

    sample_files = []
    for sample_file in SAMPLE_DIR.rglob("*.py"):
        # Exclude __pycache__ and __init__.py
        if "__pycache__" in str(sample_file) or sample_file.name == "__init__.py":
            continue

        # Apply filter if provided
        if filter_pattern:
            if filter_pattern.lower() not in str(sample_file).lower():
                continue

        sample_files.append(sample_file)

    return sorted(sample_files)


def run_sample_file(
    sample_file: Path, verbose: bool = False, timeout: int = 300
) -> tuple[Path, bool, str]:
    """
    Run a single sample file.

    Args:
        sample_file: Path to the sample file
        verbose: Whether to show verbose output
        timeout: Timeout in seconds (default: 5 minutes)

    Returns:
        Tuple of (sample_file, success, error_message)
    """
    relative_path = sample_file.relative_to(PROJECT_ROOT)

    if verbose:
        print(f"\n{'=' * 80}")
        print(f"Running: {relative_path}")
        print(f"{'=' * 80}")

    try:
        result = subprocess.run(
            [sys.executable, str(sample_file)],
            cwd=sample_file.parent,
            timeout=timeout,
            capture_output=not verbose,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            if verbose:
                print(f"✓ Success: {relative_path}")
            return (sample_file, True, "")
        error_msg = result.stderr[:500] if result.stderr else "Unknown error"
        if verbose:
            print(f"✗ Failed: {relative_path}")
            print(f"  Exit code: {result.returncode}")
            if result.stderr:
                print(f"  Error: {result.stderr[:500]}")
        return (sample_file, False, error_msg)

    except subprocess.TimeoutExpired:
        error_msg = f"Timeout (exceeded {timeout}s)"
        if verbose:
            print(f"✗ Timeout: {relative_path}")
            print(f"  {error_msg}")
        return (sample_file, False, error_msg)

    except Exception as e:
        error_msg = str(e)
        if verbose:
            print(f"✗ Error: {relative_path}")
            print(f"  {error_msg}")
        return (sample_file, False, error_msg)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run all sample files in the project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--filter",
        type=str,
        default=None,
        help="Filter samples by pattern (e.g., 'calendar', 'mongo_rag')",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose output for each sample",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout per sample in seconds (default: 300)",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue running samples even if one fails",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("RUNNING ALL SAMPLES")
    print("=" * 80)
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Sample directory: {SAMPLE_DIR}")
    if args.filter:
        print(f"Filter pattern: {args.filter}")
    print()

    # Check for common missing dependencies
    missing_deps = []
    try:
        import pydantic_ai
    except ImportError:
        missing_deps.append("pydantic-ai")

    try:
        import neo4j
    except ImportError:
        missing_deps.append("neo4j")

    try:
        import requests
    except ImportError:
        missing_deps.append("requests")

    if missing_deps:
        print("⚠️  Warning: Missing dependencies detected:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print()
        print("💡 To install all dependencies, run:")
        print("   python setup/install_clis.py")
        print("   # Or manually:")
        print("   cd 04-lambda && uv pip install -e '.[test,samples]'")
        print()
        print("⚠️  Note: Also ensure required services are running (MongoDB, Neo4j, etc.)")
        print()
    else:
        print("✅ Dependencies check passed")
        print("⚠️  Note: Ensure required services are running (MongoDB, Neo4j, etc.)")
        print()

    # Find all sample files
    sample_files = find_sample_files(args.filter)

    if not sample_files:
        print("⚠️  No sample files found")
        if args.filter:
            print(f"   (with filter: {args.filter})")
        sys.exit(0)

    print(f"Found {len(sample_files)} sample file(s)")
    print()

    # Run each sample
    results = []
    start_time = time.time()

    for i, sample_file in enumerate(sample_files, 1):
        relative_path = sample_file.relative_to(PROJECT_ROOT)
        print(f"[{i}/{len(sample_files)}] {relative_path}...", end=" ", flush=True)

        result_sample_file, success, error_msg = run_sample_file(
            sample_file,
            verbose=args.verbose,
            timeout=args.timeout,
        )

        results.append((result_sample_file, success, error_msg))

        if success:
            print("✓")
        else:
            print("✗")
            if not args.continue_on_error:
                print(f"\n❌ Sample failed: {relative_path}")
                if error_msg:
                    print(f"   Error: {error_msg}")
                print("\nUse --continue-on-error to continue running remaining samples")
                sys.exit(1)

    elapsed_time = time.time() - start_time

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed

    print(f"Total samples: {len(results)}")
    print(f"✓ Passed: {passed}")
    print(f"✗ Failed: {failed}")
    print(f"⏱️  Total time: {elapsed_time:.2f}s")

    if failed > 0:
        print("\nFailed samples:")
        for sample_file, success, error_msg in results:
            if not success:
                relative_path = sample_file.relative_to(PROJECT_ROOT)
                print(f"  - {relative_path}")
                if error_msg:
                    print(f"    Error: {error_msg[:200]}")

        print("\n💡 Common Issues and Solutions:")
        print("   1. Missing dependencies: Run 'cd 04-lambda && uv pip install -e \".[test]\"'")
        print("   2. Services not running: Start required services (MongoDB, Neo4j, etc.)")
        print("   3. Environment variables: Check .env file or Infisical configuration")
        print(
            "   4. Import errors: Ensure Python path is set correctly (samples handle this automatically)"
        )
        print("   5. Network errors: Verify services are accessible at configured URLs")

    print("=" * 80)

    if failed == 0:
        print("🎉 All samples passed!")
        sys.exit(0)
    else:
        print("⚠️  Some samples failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
