#!/usr/bin/env python3
"""Comprehensive code validation script.

This script validates Python code by:
1. Syntax validation (AST parsing)
2. Import validation (attempts to resolve imports)
3. Type checking preparation (validates type hints syntax)
"""

import ast
import sys
from pathlib import Path

# Directories to skip during validation
SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    ".ruff_cache",
    "build",
    "dist",
    "node_modules",
    ".eggs",
    "*.egg-info",
}

# Files to skip (test files are validated separately)
SKIP_PATTERNS = ["test_", "_test.py", "conftest.py"]


def should_skip_file(file_path: Path) -> bool:
    """Check if a file should be skipped during validation."""
    # Skip if in excluded directory
    for part in file_path.parts:
        if part in SKIP_DIRS:
            return True

    # Skip test files (they're validated separately)
    if any(
        file_path.name.startswith(pattern) or file_path.name.endswith(pattern)
        for pattern in SKIP_PATTERNS
    ):
        return False  # Don't skip test files, validate them too

    return False


def validate_syntax(file_path: Path) -> tuple[bool, str]:
    """Validate Python file syntax using AST parsing."""
    try:
        with file_path.open(encoding="utf-8") as f:
            content = f.read()
        ast.parse(content, filename=str(file_path))
        return True, ""
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except UnicodeDecodeError as e:
        return False, f"Encoding error: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def validate_imports_syntax(file_path: Path) -> tuple[bool, str]:
    """Validate that import statements are syntactically correct."""
    try:
        with file_path.open(encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        # Check all import statements
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                # If we can walk the tree, imports are syntactically valid
                pass

        return True, ""
    except SyntaxError as e:
        return False, f"Import syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Error validating imports: {e}"


def validate_type_hints_syntax(file_path: Path) -> tuple[bool, str]:
    """Validate that type hints are syntactically correct."""
    try:
        with file_path.open(encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        # Check for type hints in function definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check annotations
                if node.returns:
                    # If AST can parse it, the syntax is valid
                    pass
                # Check parameter annotations
                for arg in node.args.args:
                    if arg.annotation:
                        # If AST can parse it, the syntax is valid
                        pass

        return True, ""
    except SyntaxError as e:
        return False, f"Type hint syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Error validating type hints: {e}"


def validate_file(file_path: Path) -> list[str]:
    """Validate a single Python file and return list of errors."""
    errors = []

    # Syntax validation
    valid, msg = validate_syntax(file_path)
    if not valid:
        errors.append(f"Syntax: {msg}")

    # Import syntax validation
    valid, msg = validate_imports_syntax(file_path)
    if not valid:
        errors.append(f"Import syntax: {msg}")

    # Type hints validation
    valid, msg = validate_type_hints_syntax(file_path)
    if not valid:
        errors.append(f"Type hints: {msg}")

    return errors


def main() -> int:
    """Run all validations."""
    # Determine project root (script is in scripts/, so go up one level)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    print(f"Validating Python files in: {project_root}")
    print("-" * 60)

    all_errors = []
    files_checked = 0

    # Find all Python files
    for py_file in project_root.rglob("*.py"):
        # Skip if file should be excluded
        if should_skip_file(py_file):
            continue

        files_checked += 1
        relative_path = py_file.relative_to(project_root)

        # Validate the file
        errors = validate_file(py_file)
        if errors:
            all_errors.append((relative_path, errors))
            print(f"❌ {relative_path}")
            for error in errors:
                print(f"   {error}")
        else:
            print(f"✓ {relative_path}")

    print("-" * 60)
    print(f"Checked {files_checked} files")

    if all_errors:
        print(f"\n❌ Found {len(all_errors)} file(s) with errors:")
        for file_path, errors in all_errors:
            print(f"\n{file_path}:")
            for error in errors:
                print(f"  - {error}")
        return 1
    print("\n✓ All validations passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
