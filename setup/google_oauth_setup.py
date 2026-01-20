#!/usr/bin/env python3
"""Google OAuth Setup Script - One-time authorization flow.

This script performs the OAuth flow to obtain access and refresh tokens
for Google Drive API access. Run this once to get the GDOC_TOKEN value
to add to your .env file.

Usage:
    python setup/google_oauth_setup.py

Requirements:
    - GOOGLE_CLIENT_ID or CLIENT_ID_GOOGLE_LOGIN in .env
    - GOOGLE_CLIENT_SECRET or CLIENT_SECRET_GOOGLE_LOGIN in .env
"""

import json
import os
import sys
import urllib.parse
from pathlib import Path

import requests

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
from dotenv import load_dotenv

load_dotenv(project_root / ".env")


# Scopes for Google Drive access
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
]

# Redirect URI - using public domain
# Change this to match EXACTLY what's in your Google Cloud Console
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://api.datacrew.space/oauth/google/callback")


def get_client_credentials() -> tuple[str, str]:
    """Get OAuth client credentials from environment variables."""
    client_id = os.getenv("GOOGLE_CLIENT_ID") or os.getenv("CLIENT_ID_GOOGLE_LOGIN")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or os.getenv("CLIENT_SECRET_GOOGLE_LOGIN")

    if not client_id or not client_secret:
        print("Error: Missing Google OAuth credentials.")
        print("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")
        print("Or CLIENT_ID_GOOGLE_LOGIN and CLIENT_SECRET_GOOGLE_LOGIN")
        sys.exit(1)

    return client_id, client_secret


def build_auth_url(client_id: str) -> str:
    """Build the Google OAuth authorization URL."""
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    base_url = "https://accounts.google.com/o/oauth2/auth"
    return f"{base_url}?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(code: str, client_id: str, client_secret: str) -> dict:
    """Exchange authorization code for access and refresh tokens."""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    response = requests.post(token_url, data=data)

    if response.status_code != 200:
        print(f"Error exchanging code: {response.status_code}")
        print(response.text)
        sys.exit(1)

    return response.json()


def main():
    """Run OAuth flow and output token for .env file."""
    print("=" * 60)
    print("Google OAuth Setup (Manual Code Flow)")
    print("=" * 60)
    print()
    print("This flow works without localhost redirect URIs.")
    print("You'll copy a code from the browser and paste it here.")
    print()
    print("Requested scopes:")
    for scope in SCOPES:
        print(f"  - {scope}")
    print()

    # Get client credentials
    client_id, client_secret = get_client_credentials()
    print(f"Using client ID: {client_id[:30]}...")
    print(f"Redirect URI: {REDIRECT_URI}")
    print()
    print("NOTE: The redirect URI must match EXACTLY what's in Google Cloud Console")
    print("If you get 'redirect_uri_mismatch', set GOOGLE_REDIRECT_URI in .env")
    print()

    # Build and display auth URL
    auth_url = build_auth_url(client_id)

    print("=" * 60)
    print("STEP 1: Open this URL in your browser")
    print("=" * 60)
    print()
    print(auth_url)
    print()
    print("=" * 60)
    print("STEP 2: Authorize the application")
    print("=" * 60)
    print()
    print("After clicking 'Allow', you'll be redirected to:")
    print(f"  {REDIRECT_URI}?code=XXXXXX...")
    print()
    print("Copy the 'code' parameter from the URL.")
    print("(The page may show an error - that's OK, we just need the code)")
    print()

    # Get code from user
    print("=" * 60)
    print("STEP 3: Paste the authorization code below")
    print("=" * 60)
    print()
    print("Paste either:")
    print("  - Just the code value, OR")
    print("  - The full redirect URL (code will be extracted)")
    print()
    user_input = input("Enter the code or full URL: ").strip()

    if not user_input:
        print("Error: No code provided")
        sys.exit(1)

    # Extract code from URL if full URL was provided
    if user_input.startswith("http"):
        parsed = urllib.parse.urlparse(user_input)
        query_params = urllib.parse.parse_qs(parsed.query)
        if "code" in query_params:
            code = query_params["code"][0]
            print(f"Extracted code from URL: {code[:20]}...")
        else:
            print("Error: Could not find 'code' parameter in URL")
            sys.exit(1)
    else:
        code = user_input

    print()
    print("Exchanging code for tokens...")

    # Exchange code for tokens
    token_response = exchange_code_for_tokens(code, client_id, client_secret)

    # Build token JSON for .env
    token_data = {
        "access_token": token_response.get("access_token"),
        "refresh_token": token_response.get("refresh_token"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": SCOPES,
    }

    if not token_data["refresh_token"]:
        print("\nWarning: No refresh token received.")
        print("This may happen if you've already authorized this app before.")
        print("Try revoking access at: https://myaccount.google.com/permissions")
        print("Then run this script again.")

    token_json = json.dumps(token_data)

    print()
    print("=" * 60)
    print("SUCCESS! OAuth tokens obtained.")
    print("=" * 60)
    print()
    print("Add the following line to your .env file:")
    print()
    print("-" * 60)
    print(f"GDOC_TOKEN='{token_json}'")
    print("-" * 60)
    print()

    # Offer to append to .env automatically
    env_file = project_root / ".env"
    if env_file.exists():
        response = input("Would you like to append this to .env automatically? [y/N]: ")
        if response.lower() in ("y", "yes"):
            # Check if GDOC_TOKEN already exists
            env_content = env_file.read_text()
            if "GDOC_TOKEN=" in env_content:
                print("\nWarning: GDOC_TOKEN already exists in .env")
                overwrite = input("Overwrite existing token? [y/N]: ")
                if overwrite.lower() in ("y", "yes"):
                    # Replace existing line
                    lines = env_content.split("\n")
                    new_lines = []
                    for line in lines:
                        if line.startswith("GDOC_TOKEN="):
                            new_lines.append(f"GDOC_TOKEN='{token_json}'")
                        else:
                            new_lines.append(line)
                    env_file.write_text("\n".join(new_lines))
                    print("\n✅ GDOC_TOKEN updated in .env")
                else:
                    print("\nSkipped. Add the token manually.")
            else:
                # Append to file
                with open(env_file, "a") as f:
                    f.write(
                        "\n# Google Drive OAuth Token (generated by setup/google_oauth_setup.py)\n"
                    )
                    f.write(f"GDOC_TOKEN='{token_json}'\n")
                print("\n✅ GDOC_TOKEN added to .env")
        else:
            print("\nSkipped. Add the token manually to .env")

    print()
    print("You can now use the Google Drive integration!")
    print("Test with: python sample/comfyui/import_lora_from_google_drive.py")


if __name__ == "__main__":
    main()
