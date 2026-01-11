#!/usr/bin/env python3
"""Validate syntax of all Python files in the server directory."""

import py_compile
import sys
from pathlib import Path


def validate_file(file_path: Path) -> bool:
    """Validate syntax of a single Python file."""
    try:
        py_compile.compile(str(file_path), doraise=True)
        return True
    except py_compile.PyCompileError as e:
        print(f"✗ {file_path}: {e}")
        return False
    except Exception as e:
        print(f"✗ {file_path}: {e}")
        return False


def main():
    """Validate all Python files."""
    server_dir = Path(__file__).parent / "server"

    if not server_dir.exists():
        print(f"✗ Server directory not found: {server_dir}")
        sys.exit(1)

    python_files = list(server_dir.rglob("*.py"))

    print(f"Validating {len(python_files)} Python files...")
    print()

    failed = []
    for py_file in sorted(python_files):
        if not validate_file(py_file):
            failed.append(py_file)

    print()
    if failed:
        print(f"✗ {len(failed)} file(s) failed validation:")
        for f in failed:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print(f"✓ All {len(python_files)} files passed syntax validation!")
        sys.exit(0)


if __name__ == "__main__":
    main()
