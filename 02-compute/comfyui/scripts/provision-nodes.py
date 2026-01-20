#!/usr/bin/env python3
"""
ComfyUI Custom Node Provisioning Script

Reads known_nodes.yml and installs custom node packages to ComfyUI.
This script is idempotent - it skips packages that already exist.

Usage:
    # Install all nodes from known_nodes.yml
    python provision-nodes.py

    # Install specific packages
    python provision-nodes.py --packages comfyui-vrgamedevgirl ComfyUI-GGUF

    # Install nodes required by workflows (from scan-workflows.py output)
    python provision-nodes.py --from-scan

    # Dry run (show what would be installed)
    python provision-nodes.py --dry-run

    # Update existing packages
    python provision-nodes.py --update

Environment Variables:
    COMFYUI_PATH: Path to ComfyUI installation (default: /opt/ComfyUI)
    COMFYUI_VENV_PIP: Path to pip in ComfyUI venv (for Docker environments)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import yaml

# Default paths
SCRIPT_DIR = Path(__file__).resolve().parent
KNOWN_NODES_PATH = SCRIPT_DIR / "known_nodes.yml"

# ComfyUI paths - support both local and Docker environments
DEFAULT_COMFYUI_PATH = Path("/opt/ComfyUI")
LOCAL_COMFYUI_PATH = SCRIPT_DIR.parent / "data" / "basedir" / "ComfyUI"

# Determine ComfyUI path
if os.environ.get("COMFYUI_PATH"):
    COMFYUI_PATH = Path(os.environ["COMFYUI_PATH"])
elif DEFAULT_COMFYUI_PATH.exists():
    COMFYUI_PATH = DEFAULT_COMFYUI_PATH
elif LOCAL_COMFYUI_PATH.exists():
    COMFYUI_PATH = LOCAL_COMFYUI_PATH
else:
    COMFYUI_PATH = DEFAULT_COMFYUI_PATH  # Will fail gracefully if not found

CUSTOM_NODES_DIR = COMFYUI_PATH / "custom_nodes"


def load_known_nodes() -> dict:
    """Load known nodes from YAML file."""
    if not KNOWN_NODES_PATH.exists():
        print(f"Error: {KNOWN_NODES_PATH} not found")
        return {}

    with open(KNOWN_NODES_PATH) as f:
        return yaml.safe_load(f) or {}


def get_installed_packages() -> set[str]:
    """Get list of already installed custom node packages."""
    installed = set()

    if not CUSTOM_NODES_DIR.exists():
        return installed

    for item in CUSTOM_NODES_DIR.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            installed.add(item.name)

    return installed


def pip_install(packages: list[str], dry_run: bool = False) -> bool:
    """Install pip packages using the appropriate pip."""
    if not packages:
        return True

    # Determine which pip to use
    venv_pip = os.environ.get("COMFYUI_VENV_PIP")

    if venv_pip and Path(venv_pip).exists():
        pip_cmd = [venv_pip]
    else:
        # Try to find pip in common locations
        pip_cmd = [sys.executable, "-m", "pip"]

    cmd = pip_cmd + ["install", "--no-cache-dir"] + packages

    if dry_run:
        print(f"    [DRY RUN] Would run: {' '.join(cmd)}")
        return True

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"    Error installing pip packages: {e.stderr}")
        return False


def clone_package(package_name: str, url: str, update: bool = False, dry_run: bool = False) -> bool:
    """Clone a custom node package from Git."""
    target_path = CUSTOM_NODES_DIR / package_name

    if target_path.exists():
        if update:
            if dry_run:
                print(f"    [DRY RUN] Would update: git -C {target_path} pull")
                return True

            print(f"    Updating {package_name}...")
            try:
                subprocess.run(
                    ["git", "-C", str(target_path), "pull"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return True
            except subprocess.CalledProcessError as e:
                print(f"    Error updating {package_name}: {e.stderr}")
                return False
        else:
            print(f"    ✓ {package_name} already installed, skipping...")
            return True

    if dry_run:
        print(f"    [DRY RUN] Would clone: git clone {url} {target_path}")
        return True

    print(f"    Cloning {package_name}...")
    try:
        subprocess.run(
            ["git", "clone", "--recursive", url, str(target_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"    Error cloning {package_name}: {e.stderr}")
        return False


def install_requirements(package_name: str, dry_run: bool = False) -> bool:
    """Install requirements.txt for a package if it exists."""
    target_path = CUSTOM_NODES_DIR / package_name
    requirements_path = target_path / "requirements.txt"

    if not requirements_path.exists():
        return True

    if dry_run:
        print(f"    [DRY RUN] Would install requirements from: {requirements_path}")
        return True

    print(f"    Installing requirements for {package_name}...")

    # Determine which pip to use
    venv_pip = os.environ.get("COMFYUI_VENV_PIP")

    if venv_pip and Path(venv_pip).exists():
        pip_cmd = [venv_pip]
    else:
        pip_cmd = [sys.executable, "-m", "pip"]

    cmd = pip_cmd + ["install", "--no-cache-dir", "-r", str(requirements_path)]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"    Error installing requirements: {e.stderr}")
        return False


def install_package(
    package_name: str,
    package_info: dict,
    update: bool = False,
    dry_run: bool = False,
) -> bool:
    """Install a single custom node package."""
    url = package_info.get("url", "")
    description = package_info.get("description", "")
    pip_packages = package_info.get("pip_packages", [])

    if not url:
        print(f"    ⚠️  No URL for {package_name}, skipping...")
        return False

    print(f"\n📦 {package_name}")
    print(f"   {description}")

    # Clone the repository
    if not clone_package(package_name, url, update=update, dry_run=dry_run):
        return False

    # Install additional pip packages
    if pip_packages:
        print(f"    Installing pip packages: {', '.join(pip_packages)}")
        if not pip_install(pip_packages, dry_run=dry_run):
            return False

    # Install requirements.txt
    if not install_requirements(package_name, dry_run=dry_run):
        return False

    if not dry_run:
        print(f"    ✓ {package_name} installed successfully")

    return True


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Install ComfyUI custom node packages from known_nodes.yml"
    )
    parser.add_argument(
        "--packages",
        nargs="+",
        help="Specific packages to install (default: all known packages)",
    )
    parser.add_argument(
        "--from-scan",
        action="store_true",
        help="Install packages identified by scan-workflows.py",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update existing packages (git pull)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be installed without making changes",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Check ComfyUI path
    if not COMFYUI_PATH.exists():
        print(f"Error: ComfyUI not found at {COMFYUI_PATH}")
        print("Set COMFYUI_PATH environment variable to the correct location")
        return 1

    # Create custom_nodes directory if needed
    if not args.dry_run:
        CUSTOM_NODES_DIR.mkdir(parents=True, exist_ok=True)

    # Load known nodes
    known_nodes = load_known_nodes()
    if not known_nodes:
        print("No known nodes configured")
        return 1

    print("=" * 60)
    print("  ComfyUI Custom Node Provisioning")
    print("=" * 60)
    print(f"\nComfyUI path: {COMFYUI_PATH}")
    print(f"Custom nodes dir: {CUSTOM_NODES_DIR}")

    # Determine which packages to install
    if args.packages:
        # Install specific packages
        packages_to_install = {
            name: info for name, info in known_nodes.items() if name in args.packages
        }

        # Warn about unknown packages
        unknown = set(args.packages) - set(known_nodes.keys())
        if unknown:
            print(f"\n⚠️  Unknown packages (not in known_nodes.yml): {', '.join(unknown)}")

    elif args.from_scan:
        # Run scan-workflows.py to get required packages
        print("\nRunning workflow scan to identify required packages...")
        try:
            scan_result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "scan-workflows.py"),
                    "--source",
                    "local",
                    "--skip-nodes",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            # For now, just install all known nodes when using --from-scan
            # A more sophisticated implementation would parse the scan output
            packages_to_install = known_nodes
            print("Note: Installing all known custom nodes")
        except Exception as e:
            print(f"Error running scan: {e}")
            packages_to_install = known_nodes
    else:
        # Install all known packages
        packages_to_install = known_nodes

    if not packages_to_install:
        print("\nNo packages to install")
        return 0

    # Get already installed packages
    installed = get_installed_packages()

    print(f"\nPackages to process: {len(packages_to_install)}")
    print(f"Already installed: {len(installed)}")

    # Install packages
    success_count = 0
    fail_count = 0
    skip_count = 0

    for package_name, package_info in packages_to_install.items():
        if package_name in installed and not args.update:
            skip_count += 1
            if args.verbose:
                print(f"\n✓ {package_name} already installed, skipping...")
            continue

        if install_package(package_name, package_info, update=args.update, dry_run=args.dry_run):
            success_count += 1
        else:
            fail_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  Installed/Updated: {success_count}")
    print(f"  Skipped (already installed): {skip_count}")
    print(f"  Failed: {fail_count}")

    if args.dry_run:
        print("\n[DRY RUN] No changes were made")

    if fail_count > 0:
        print("\n⚠️  Some packages failed to install. Check the output above.")
        return 1

    print("\n✓ Custom node provisioning complete!")
    print("  Restart ComfyUI and refresh the browser to use new nodes.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
