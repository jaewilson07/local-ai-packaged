#!/usr/bin/env python3
"""
Install required CLI tools and Python dependencies for the AI Homelab project.
Installs: Infisical CLI, Google Cloud CLI, Cloudflared CLI, pre-commit hooks, and Python dependencies.
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(command, check=True, shell=False):
    """
    Runs a shell command and returns True on success, False on failure.
    Prints output to stderr/stdout.
    """
    print(f"Running command: {' '.join(command) if isinstance(command, list) else command}")
    try:
        if shell:
            result = subprocess.run(
                command, shell=True, check=check, capture_output=True, text=True
            )
        else:
            result = subprocess.run(command, check=check, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}", file=sys.stderr)
        print(f"Stdout: {e.stdout}", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print(
            f"Command not found: {command[0] if isinstance(command, list) else command.split(' ')[0]}",
            file=sys.stderr,
        )
        return False


def is_tool_installed(name):
    """Check whether `name` is on PATH and is an executable file."""
    return shutil.which(name) is not None


def install_infisical_cli():
    if is_tool_installed("infisical"):
        print("Infisical CLI is already installed.")
        return True

    print("Installing Infisical CLI...")
    # Add Infisical apt repository key and then update
    if not run_command(
        "curl -1sLf 'https://artifacts-cli.infisical.com/setup.deb.sh' | sudo -E bash", shell=True
    ):
        return False
    if not run_command(["sudo", "apt-get", "update"]):
        return False
    if not run_command(["sudo", "apt-get", "install", "-y", "infisical"]):
        return False
    print("Infisical CLI installed successfully.")
    return True


def install_gcloud_cli():
    if is_tool_installed("gcloud"):
        print("Google Cloud CLI (gcloud) is already installed.")
        return True

    print("Installing Google Cloud CLI (gcloud)...")
    # Add Google Cloud SDK distribution URI as a package source
    # This block specifically for Debian/Ubuntu
    if not run_command(
        'echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list',
        shell=True,
    ):
        return False
    if not run_command(
        ["sudo", "apt-get", "install", "-y", "apt-transport-https", "ca-certificates", "gnupg"]
    ):
        return False
    if not run_command(
        "curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -",
        shell=True,
    ):
        return False
    if not run_command(["sudo", "apt-get", "update"]):
        return False
    if not run_command(["sudo", "apt-get", "install", "-y", "google-cloud-cli"]):
        return False
    print("Google Cloud CLI (gcloud) installed successfully.")
    return True


def install_cloudflared_cli():
    if is_tool_installed("cloudflared"):
        print("Cloudflared CLI is already installed.")
        cloudflared_version = subprocess.run(
            ["cloudflared", "--version"], capture_output=True, text=True, check=False
        )
        if cloudflared_version.returncode == 0:
            print(f"  Version: {cloudflared_version.stdout.strip()}")
        return True

    print("Installing Cloudflared CLI...")
    print("Note: This requires sudo privileges. You may be prompted for your password.")
    # Detect architecture
    arch = platform.machine()
    if arch == "x86_64":
        arch = "amd64"
    elif arch in {"aarch64", "arm64"}:
        arch = "arm64"
    else:
        print(f"Unsupported architecture: {arch}", file=sys.stderr)
        return False

    # Download and install cloudflared
    download_url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-{arch}"
    install_path = "/usr/local/bin/cloudflared"
    temp_path = "/tmp/cloudflared"

    print(f"Downloading cloudflared for {arch}...")
    if not run_command(f"curl -L {download_url} -o {temp_path}", shell=True):
        return False

    print("Installing cloudflared (requires sudo)...")
    # Use a single sudo command to chmod and move
    if not run_command(
        f"sudo sh -c 'chmod +x {temp_path} && mv {temp_path} {install_path}'", shell=True
    ):
        print("\nInstallation failed. You can install manually with:", file=sys.stderr)
        print(f"  sudo chmod +x {temp_path}", file=sys.stderr)
        print(f"  sudo mv {temp_path} {install_path}", file=sys.stderr)
        return False

    print("Cloudflared CLI installed successfully.")
    # Verify installation
    if is_tool_installed("cloudflared"):
        cloudflared_version = subprocess.run(
            ["cloudflared", "--version"], capture_output=True, text=True, check=False
        )
        if cloudflared_version.returncode == 0:
            print(f"  Version: {cloudflared_version.stdout.strip()}")
    return True


def install_pre_commit():
    """Install pre-commit package and set up git hooks."""
    # Check if pre-commit is already installed
    try:
        result = subprocess.run(
            ["pre-commit", "--version"], capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            print(f"pre-commit is already installed: {result.stdout.strip()}")
            pre_commit_installed = True
        else:
            pre_commit_installed = False
    except FileNotFoundError:
        pre_commit_installed = False

    # Install pre-commit if not installed
    if not pre_commit_installed:
        print("Installing pre-commit...")

        # Try to use uv if available (preferred for this project)
        if shutil.which("uv"):
            print("Using uv to install pre-commit...")
            if not run_command(["uv", "pip", "install", "pre-commit"]):
                # Fallback to pip
                print("uv installation failed, trying pip...")
                if not run_command(
                    [sys.executable, "-m", "pip", "install", "--user", "pre-commit"]
                ):
                    print(
                        "Failed to install pre-commit. You can install it manually with:",
                        file=sys.stderr,
                    )
                    print("  pip install pre-commit", file=sys.stderr)
                    print("  or", file=sys.stderr)
                    print("  uv pip install pre-commit", file=sys.stderr)
                    return False
        # Use pip
        elif not run_command([sys.executable, "-m", "pip", "install", "--user", "pre-commit"]):
            print(
                "Failed to install pre-commit. You can install it manually with:",
                file=sys.stderr,
            )
            print("  pip install pre-commit", file=sys.stderr)
            return False

        print("pre-commit installed successfully.")

    # Check if we're in a git repository
    repo_root = Path(__file__).parent.parent
    if not (repo_root / ".git").exists():
        print("Warning: Not in a git repository. Skipping pre-commit hook installation.")
        print("  To install hooks later, run: pre-commit install")
        return True

    # Check if .pre-commit-config.yaml exists
    pre_commit_config = repo_root / ".pre-commit-config.yaml"
    if not pre_commit_config.exists():
        print("Warning: .pre-commit-config.yaml not found. Skipping hook installation.")
        return True

    # Install git hooks
    print("Installing pre-commit git hooks...")
    os.chdir(repo_root)
    if not run_command(["pre-commit", "install"]):
        print("Warning: Failed to install pre-commit hooks.", file=sys.stderr)
        print("  You can install them manually with: pre-commit install", file=sys.stderr)
        return False

    print("pre-commit hooks installed successfully.")
    print("  Hooks will run automatically on git commit.")
    print("  To run manually: pre-commit run --all-files")
    return True


def install_python_dependencies():
    """Install Python dependencies for samples and tests."""
    repo_root = Path(__file__).parent.parent
    lambda_dir = repo_root / "04-lambda"

    if not lambda_dir.exists():
        print("Warning: 04-lambda directory not found. Skipping Python dependency installation.")
        return True

    print("Installing Python dependencies for samples and tests...")

    # Check if uv is available (preferred)
    if shutil.which("uv"):
        print("Using uv to install dependencies...")
        os.chdir(lambda_dir)
        # Install with test and samples extras (samples includes test deps)
        if not run_command(["uv", "pip", "install", "-e", ".[test,samples]"]):
            print("Warning: Failed to install dependencies with uv.", file=sys.stderr)
            print("  You can install manually with:", file=sys.stderr)
            print("  cd 04-lambda && uv pip install -e '.[test,samples]'", file=sys.stderr)
            return False
    else:
        # Fallback to pip
        print("uv not found, using pip to install dependencies...")
        print("  Note: uv is recommended for this project.")
        os.chdir(lambda_dir)
        if not run_command([sys.executable, "-m", "pip", "install", "-e", ".[test,samples]"]):
            print("Warning: Failed to install dependencies with pip.", file=sys.stderr)
            print("  You can install manually with:", file=sys.stderr)
            print("  cd 04-lambda && pip install -e '.[test,samples]'", file=sys.stderr)
            return False

    print("Python dependencies installed successfully.")
    return True


def main():
    print("Starting CLI and dependency installations...")
    if not install_infisical_cli():
        print("Failed to install Infisical CLI.", file=sys.stderr)
        sys.exit(1)
    if not install_gcloud_cli():
        print("Failed to install Google Cloud CLI (gcloud).", file=sys.stderr)
        sys.exit(1)
    if not install_cloudflared_cli():
        print("Failed to install Cloudflared CLI.", file=sys.stderr)
        sys.exit(1)
    if not install_pre_commit():
        print("Failed to install pre-commit.", file=sys.stderr)
        sys.exit(1)
    if not install_python_dependencies():
        print("Failed to install Python dependencies.", file=sys.stderr)
        sys.exit(1)
    print("All CLI tools and Python dependencies installed successfully.")


if __name__ == "__main__":
    main()
