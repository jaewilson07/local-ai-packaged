#!/usr/bin/env python3
"""
Setup Infisical Project: local-aipackaged
This script helps set up a new Infisical project for the local-ai-packaged repository
"""

import os
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

PROJECT_NAME = "local-aipackaged"
INFISICAL_URL = os.getenv("INFISICAL_SITE_URL", "http://localhost:8010")


def check_infisical_cli():
    """Check if Infisical CLI is installed."""
    try:
        result = subprocess.run(
            ["infisical", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        version = result.stdout.strip().split("\n")[0]
        print(f"✅ Infisical CLI found: {version}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Infisical CLI not found")
        print("   Install it: python3 utils/setup/install_clis.py")
        return False


def check_infisical_accessibility():
    """Check if Infisical is accessible."""
    print("🔍 Checking Infisical accessibility...")
    try:
        health_url = f"{INFISICAL_URL}/api/health"
        with urlopen(health_url, timeout=5) as response:
            if response.status == 200:
                print(f"✅ Infisical is accessible at {INFISICAL_URL}")
                return True
    except (URLError, OSError, ValueError):
        pass

    print(f"⚠️  Infisical not accessible at {INFISICAL_URL}")
    print("   Make sure Infisical is running:")
    print("     docker ps | grep infisical")
    print("   Or check if it's on a different port/URL")
    response = input("Continue anyway? (y/n) ")
    return response.lower() in ("y", "yes")


def print_setup_steps():
    """Print setup instructions."""
    print("")
    print("📋 Setup Steps:")
    print("")
    print("1. Access Infisical UI:")
    print(f"   Open: {INFISICAL_URL}/admin/signup")
    print(f"   (Or {INFISICAL_URL} if already signed up)")
    print("")
    print("2. Create Organization (if needed):")
    print("   - Click 'Create Organization'")
    print("   - Name it (e.g., 'DataCrew' or 'Personal')")
    print("")
    print("3. Create Project:")
    print("   - Click 'Create Project'")
    print(f"   - Name: {PROJECT_NAME}")
    print("   - Select or create environments:")
    print("     * development (for local dev)")
    print("     * production (for production)")
    print("")
    input("Press Enter when you've created the project in the UI...")


def authenticate_cli():
    """Authenticate Infisical CLI."""
    print("")
    print("4. Authenticate CLI:")
    print("   This will open a browser for authentication...")
    subprocess.run(
        ["infisical", "login", f"--host={INFISICAL_URL}"],
        check=True,
    )


def initialize_project():
    """Initialize Infisical project in current directory."""
    print("")
    print("5. Initialize project in this directory:")
    print("   This will create .infisical.json config file...")
    # Get the repository root directory
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    subprocess.run(["infisical", "init"], cwd=repo_root, check=True)


def main():
    """Main setup flow."""
    print("=" * 60)
    print(f"Infisical Project Setup: {PROJECT_NAME}")
    print("=" * 60)
    print("")

    # Check CLI installation
    if not check_infisical_cli():
        sys.exit(1)

    print("")

    # Check accessibility
    if not check_infisical_accessibility():
        sys.exit(1)

    # Print setup steps
    print_setup_steps()

    # Authenticate CLI
    authenticate_cli()

    # Initialize project
    initialize_project()

    # Final instructions
    print("")
    print("✅ Project setup complete!")
    print("")
    print("Next steps:")
    print("1. Add secrets to Infisical (via UI or CLI)")
    print("2. Test secret export: infisical export --format=dotenv")
    print("3. Use with start_services.py: python start_services.py --use-infisical")
    print("")
    print("For more info, see: 00-infrastructure/docs/infisical/setup.md")


if __name__ == "__main__":
    main()
