#!/usr/bin/env python3
"""
Script to run all sample files in the project.

This script:
1. Discovers all Python sample files in the sample/ directory
2. Executes each sample file
3. Reports success/failure for each sample
4. Provides a summary at the end

Usage:
    python scripts/run_all_samples.py
    python scripts/run_all_samples.py --verbose
    python scripts/run_all_samples.py --filter calendar
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Sample directory
SAMPLE_DIR = PROJECT_ROOT / "sample"


def find_sample_files(filter_pattern: str = None) -> List[Path]:
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


def run_sample_file(sample_file: Path, verbose: bool = False, timeout: int = 300) -> Tuple[Path, bool, str]:
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
        else:
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
        "--verbose", "-v",
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
        
        sample_file, success, error_msg = run_sample_file(
            sample_file,
            verbose=args.verbose,
            timeout=args.timeout,
        )
        
        results.append((sample_file, success, error_msg))
        
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
    
    print("=" * 80)
    
    if failed == 0:
        print("🎉 All samples passed!")
        sys.exit(0)
    else:
        print("⚠️  Some samples failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
