#!/usr/bin/env python3
"""
Script to run all tests and sample files for the Lambda server.

This script:
1. Waits for the server to be ready
2. Runs all pytest tests
3. Runs all sample files
4. Reports results
"""

import subprocess
import sys
import time
from pathlib import Path

import httpx

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
LAMBDA_DIR = Path(__file__).parent

# Test directories
TEST_DIRS = [
    LAMBDA_DIR / "tests",
]

# Sample directories
SAMPLE_DIRS = [
    PROJECT_ROOT / "sample",
]

# Server URL
SERVER_URL = "http://localhost:8000"
HEALTH_ENDPOINT = f"{SERVER_URL}/health"


def wait_for_server(max_wait=300, check_interval=5):
    """Wait for the server to be ready."""
    print(f"⏳ Waiting for server at {SERVER_URL}...")
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            response = httpx.get(HEALTH_ENDPOINT, timeout=2)
            if response.status_code == 200:
                print(f"✓ Server is ready! (took {int(time.time() - start_time)}s)")
                return True
        except (httpx.RequestError, httpx.TimeoutException):
            pass

        time.sleep(check_interval)
        print(f"  Still waiting... ({int(time.time() - start_time)}s)")

    print(f"✗ Server did not become ready within {max_wait}s")
    return False


def find_test_files():
    """Find all test files."""
    test_files = []
    for test_dir in TEST_DIRS:
        if test_dir.exists():
            test_files.extend(test_dir.rglob("test_*.py"))
    return sorted(test_files)


def find_sample_files():
    """Find all sample Python files."""
    sample_files = []
    for sample_dir in SAMPLE_DIRS:
        if sample_dir.exists():
            sample_files.extend(sample_dir.rglob("*.py"))
    # Exclude __pycache__ and __init__.py
    sample_files = [
        f for f in sample_files if "__pycache__" not in str(f) and f.name != "__init__.py"
    ]
    return sorted(sample_files)


def run_pytest_tests():
    """Run all pytest tests."""
    print("\n" + "=" * 80)
    print("RUNNING PYTEST TESTS")
    print("=" * 80)

    test_files = find_test_files()
    if not test_files:
        print("⚠️  No test files found")
        return False

    print(f"Found {len(test_files)} test files")

    # Run pytest
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "--tb=short",
        str(LAMBDA_DIR / "tests"),
    ]

    print(f"\nRunning: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=LAMBDA_DIR, check=False)
    return result.returncode == 0


def run_sample_file(sample_file: Path):
    """Run a single sample file."""
    print(f"\n  Running: {sample_file.relative_to(PROJECT_ROOT)}")
    try:
        result = subprocess.run(
            [sys.executable, str(sample_file)],
            cwd=sample_file.parent,
            timeout=300,  # 5 minute timeout per sample
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print("    ✓ Success")
            if result.stdout:
                # Print last few lines of output
                lines = result.stdout.strip().split("\n")
                if len(lines) > 5:
                    print("    Output (last 5 lines):")
                    for line in lines[-5:]:
                        print(f"      {line}")
                else:
                    print(f"    Output: {result.stdout.strip()}")
            return True
        print(f"    ✗ Failed (exit code: {result.returncode})")
        if result.stderr:
            print(f"    Error: {result.stderr[:500]}")
        return False
    except subprocess.TimeoutExpired:
        print("    ✗ Timeout (exceeded 5 minutes)")
        return False
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False


def run_sample_files():
    """Run all sample files."""
    print("\n" + "=" * 80)
    print("RUNNING SAMPLE FILES")
    print("=" * 80)

    sample_files = find_sample_files()
    if not sample_files:
        print("⚠️  No sample files found")
        return False

    print(f"Found {len(sample_files)} sample files")

    results = []
    for sample_file in sample_files:
        success = run_sample_file(sample_file)
        results.append((sample_file, success))

    # Summary
    print("\n" + "=" * 80)
    print("SAMPLE FILES SUMMARY")
    print("=" * 80)
    passed = sum(1 for _, success in results if success)
    failed = len(results) - passed
    print(f"✓ Passed: {passed}")
    print(f"✗ Failed: {failed}")

    if failed > 0:
        print("\nFailed samples:")
        for sample_file, success in results:
            if not success:
                print(f"  - {sample_file.relative_to(PROJECT_ROOT)}")

    return failed == 0


def main():
    """Main entry point."""
    print("=" * 80)
    print("LAMBDA SERVER TEST AND SAMPLE RUNNER")
    print("=" * 80)

    # Wait for server
    if not wait_for_server():
        print("\n✗ Cannot proceed without server")
        sys.exit(1)

    # Run tests
    tests_passed = run_pytest_tests()

    # Run samples
    samples_passed = run_sample_files()

    # Final summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"Tests: {'✓ PASSED' if tests_passed else '✗ FAILED'}")
    print(f"Samples: {'✓ PASSED' if samples_passed else '✗ FAILED'}")

    if tests_passed and samples_passed:
        print("\n🎉 All tests and samples passed!")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests or samples failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
