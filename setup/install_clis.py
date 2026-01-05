#!/usr/bin/env python3
"""
Install required CLI tools for the AI Homelab project.
Installs: Infisical CLI, Google Cloud CLI, and Cloudflared CLI.
"""

import subprocess
import shutil
import sys

def run_command(command, check=True, shell=False):
    """
    Runs a shell command and returns True on success, False on failure.
    Prints output to stderr/stdout.
    """
    print(f"Running command: {' '.join(command) if isinstance(command, list) else command}")
    try:
        if shell:
            result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
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
        print(f"Command not found: {command[0] if isinstance(command, list) else command.split(' ')[0]}", file=sys.stderr)
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
    if not run_command("curl -1sLf 'https://artifacts-cli.infisical.com/setup.deb.sh' | sudo -E bash", shell=True):
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
    if not run_command("echo \"deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main\" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list", shell=True):
        return False
    if not run_command(["sudo", "apt-get", "install", "-y", "apt-transport-https", "ca-certificates", "gnupg"]):
        return False
    if not run_command("curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -", shell=True):
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
        cloudflared_version = subprocess.run(["cloudflared", "--version"], capture_output=True, text=True)
        if cloudflared_version.returncode == 0:
            print(f"  Version: {cloudflared_version.stdout.strip()}")
        return True

    print("Installing Cloudflared CLI...")
    print("Note: This requires sudo privileges. You may be prompted for your password.")
    import platform
    
    # Detect architecture
    arch = platform.machine()
    if arch == "x86_64":
        arch = "amd64"
    elif arch == "aarch64" or arch == "arm64":
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
    if not run_command(f"sudo sh -c 'chmod +x {temp_path} && mv {temp_path} {install_path}'", shell=True):
        print("\nInstallation failed. You can install manually with:", file=sys.stderr)
        print(f"  sudo chmod +x {temp_path}", file=sys.stderr)
        print(f"  sudo mv {temp_path} {install_path}", file=sys.stderr)
        return False
    
    print("Cloudflared CLI installed successfully.")
    # Verify installation
    if is_tool_installed("cloudflared"):
        cloudflared_version = subprocess.run(["cloudflared", "--version"], capture_output=True, text=True)
        if cloudflared_version.returncode == 0:
            print(f"  Version: {cloudflared_version.stdout.strip()}")
    return True

def main():
    print("Starting CLI installations...")
    if not install_infisical_cli():
        print("Failed to install Infisical CLI.", file=sys.stderr)
        sys.exit(1)
    if not install_gcloud_cli():
        print("Failed to install Google Cloud CLI (gcloud).", file=sys.stderr)
        sys.exit(1)
    if not install_cloudflared_cli():
        print("Failed to install Cloudflared CLI.", file=sys.stderr)
        sys.exit(1)
    print("All specified CLIs installed successfully.")

if __name__ == "__main__":
    main()
