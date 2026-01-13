#!/usr/bin/env python3
"""
Generate XKCD-style passphrases for .env file setup.

This script generates secure, memorable passphrases using common words,
following the XKCD password strength methodology.
It automatically updates the .env file with missing passwords.

When Infisical is available, secrets are generated and set in Infisical first,
then synced back to .env as a fallback.
"""

import argparse
import base64
import getpass
import json
import re
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

# EFF Large Word List (simplified - common words)
# Full list available at: https://www.eff.org/files/2016/07/18/eff_large_wordlist.txt
WORD_LIST = [
    # Common nouns
    "apple",
    "book",
    "car",
    "dog",
    "house",
    "tree",
    "water",
    "fire",
    "earth",
    "wind",
    "moon",
    "star",
    "sun",
    "ocean",
    "mountain",
    "river",
    "forest",
    "valley",
    "cloud",
    "bird",
    "fish",
    "cat",
    "horse",
    "cow",
    "sheep",
    "chicken",
    "duck",
    "goose",
    "table",
    "chair",
    "door",
    "window",
    "wall",
    "floor",
    "roof",
    "room",
    "bed",
    "paper",
    "pen",
    "pencil",
    "computer",
    "phone",
    "key",
    "lock",
    "box",
    "bag",
    # Verbs
    "run",
    "walk",
    "jump",
    "fly",
    "swim",
    "dance",
    "sing",
    "play",
    "work",
    "sleep",
    "eat",
    "drink",
    "cook",
    "read",
    "write",
    "draw",
    "paint",
    "build",
    "create",
    "think",
    "learn",
    "teach",
    "help",
    "give",
    "take",
    "make",
    "do",
    "go",
    "come",
    "see",
    "hear",
    "feel",
    "touch",
    "smell",
    "taste",
    "know",
    "understand",
    "remember",
    # Adjectives
    "big",
    "small",
    "hot",
    "cold",
    "fast",
    "slow",
    "high",
    "low",
    "long",
    "short",
    "good",
    "bad",
    "new",
    "old",
    "young",
    "old",
    "happy",
    "sad",
    "angry",
    "calm",
    "bright",
    "dark",
    "light",
    "heavy",
    "soft",
    "hard",
    "smooth",
    "rough",
    "clean",
    "dirty",
    "wet",
    "dry",
    "warm",
    "cool",
    "quiet",
    "loud",
    "sweet",
    "sour",
    "bitter",
    # Additional common words
    "time",
    "day",
    "night",
    "morning",
    "evening",
    "week",
    "month",
    "year",
    "hour",
    "minute",
    "second",
    "today",
    "tomorrow",
    "yesterday",
    "now",
    "then",
    "here",
    "there",
    "up",
    "down",
    "left",
    "right",
    "front",
    "back",
    "inside",
    "outside",
    "near",
    "far",
    "red",
    "blue",
    "green",
    "yellow",
    "orange",
    "purple",
    "pink",
    "brown",
    "black",
    "white",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
]


def generate_passphrase(num_words=4, separator="-"):
    """
    Generate an XKCD-style passphrase.

    Args:
        num_words: Number of words in the passphrase (default: 4)
        separator: Character to separate words (default: "-")

    Returns:
        A passphrase string
    """
    words = [secrets.choice(WORD_LIST) for _ in range(num_words)]
    return separator.join(words)


def generate_hex_string(length=32):
    """
    Generate a random hexadecimal string.

    Args:
        length: Length of hex string in characters (default: 32)

    Returns:
        A hexadecimal string
    """
    return secrets.token_hex(length // 2)


def generate_base64_string(length=32):
    """
    Generate a random base64 string.

    Args:
        length: Length of base64 string in bytes (default: 32)

    Returns:
        A base64-encoded string
    """
    import base64

    return base64.b64encode(secrets.token_bytes(length)).decode("utf-8")


def generate_uuid():
    """Generate a UUID string."""
    import uuid

    return str(uuid.uuid4())


def base64_url_encode(data):
    """
    Base64 URL encode (RFC 4648 Section 5).
    Replaces '+' with '-', '/' with '_', and removes padding '='.
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    encoded = base64.b64encode(data).decode("utf-8")
    return encoded.replace("+", "-").replace("/", "_").rstrip("=")


def generate_supabase_jwt_tokens(jwt_secret=None):
    """
    Generate Supabase JWT tokens (ANON_KEY and SERVICE_ROLE_KEY).

    Args:
        jwt_secret: JWT secret (base64 string). If None, generates a new one.

    Returns:
        tuple: (jwt_secret, anon_key, service_role_key)
    """
    import hashlib
    import hmac

    # Generate JWT secret if not provided (30 bytes base64)
    if jwt_secret is None:
        jwt_secret = base64.b64encode(secrets.token_bytes(30)).decode("utf-8")

    # JWT header
    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(",", ":"))
    header_base64 = base64_url_encode(header_json)

    # Current time and expiration (5 years from now)
    iat = int(time.time())
    exp = iat + (5 * 365 * 24 * 3600)  # 5 years

    # Anon payload
    anon_payload = {"role": "anon", "iss": "supabase", "iat": iat, "exp": exp}
    anon_payload_json = json.dumps(anon_payload, separators=(",", ":"))
    anon_payload_base64 = base64_url_encode(anon_payload_json)

    # Service role payload
    service_role_payload = {"role": "service_role", "iss": "supabase", "iat": iat, "exp": exp}
    service_role_payload_json = json.dumps(service_role_payload, separators=(",", ":"))
    service_role_payload_base64 = base64_url_encode(service_role_payload_json)

    # Create signature for anon key
    anon_signed_content = f"{header_base64}.{anon_payload_base64}"
    anon_signature = hmac.new(
        jwt_secret.encode("utf-8"), anon_signed_content.encode("utf-8"), hashlib.sha256
    ).digest()
    anon_signature_base64 = base64_url_encode(anon_signature)
    anon_key = f"{anon_signed_content}.{anon_signature_base64}"

    # Create signature for service role key
    service_role_signed_content = f"{header_base64}.{service_role_payload_base64}"
    service_role_signature = hmac.new(
        jwt_secret.encode("utf-8"), service_role_signed_content.encode("utf-8"), hashlib.sha256
    ).digest()
    service_role_signature_base64 = base64_url_encode(service_role_signature)
    service_role_key = f"{service_role_signed_content}.{service_role_signature_base64}"

    return jwt_secret, anon_key, service_role_key


def get_env_file_path():
    # Script is at setup/generate-env-passwords.py
    # Need to go up 1 level to reach project root
    return Path(__file__).resolve().parent.parent / ".env"


def get_example_env_file_path():
    # Script is at setup/generate-env-passwords.py
    # Need to go up 1 level to reach project root
    return Path(__file__).resolve().parent.parent / ".env_sample"


# Patterns for variables that should be synced to Infisical (secrets)
SECRET_PATTERNS = [
    r".*_PASSWORD$",  # All passwords
    r".*_SECRET$",  # All secrets
    r".*_KEY$",  # All keys (encryption keys, etc.)
    r".*_TOKEN$",  # All tokens
    r".*_API_KEY$",  # API keys
    r".*_CLIENT_ID$",  # OAuth client IDs
    r".*_CLIENT_SECRET$",  # OAuth client secrets
    r"^DOCKER_HUB_USERNAME$",  # Docker Hub username
    r"^DOCKER_HUB_PASSWORD$",  # Docker Hub password
    r"^DOCKER_HUB_TOKEN$",  # Docker Hub token
    r"^SMTP_.*$",  # SMTP credentials
]

# Patterns for variables that should NOT be synced to Infisical
NON_SECRET_PATTERNS = [
    r".*_HOSTNAME$",  # Hostnames (N8N_HOSTNAME, etc.)
    r".*_PORT$",  # Port numbers
    r".*_URL$",  # URLs (SITE_URL, etc.)
    r".*_SITE_URL$",  # Site URLs
    r"^INFISICAL_HOSTNAME$",  # Infisical hostname config
    r"^INFISICAL_SITE_URL$",  # Infisical site URL config
    r"^INFISICAL_HTTPS_ENABLED$",  # Infisical HTTPS setting
    r"^INFISICAL_POSTGRES_HOST$",  # Infisical DB host (non-secret)
    r"^INFISICAL_POSTGRES_PORT$",  # Infisical DB port (non-secret)
    r"^INFISICAL_POSTGRES_DATABASE$",  # Infisical DB name (non-secret)
    r"^INFISICAL_POSTGRES_USERNAME$",  # Infisical DB user (non-secret)
]


def is_secret_key(key: str) -> bool:
    """Check if a key should be treated as a secret."""
    # Check exclusion patterns first
    for pattern in NON_SECRET_PATTERNS:
        if re.match(pattern, key, re.IGNORECASE):
            return False

    # Check inclusion patterns
    return any(re.match(pattern, key, re.IGNORECASE) for pattern in SECRET_PATTERNS)


def check_infisical_cli() -> bool:
    """Check if Infisical CLI is installed and available."""
    try:
        result = subprocess.run(
            ["infisical", "--version"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except (subprocess.SubprocessError, OSError):
        return False


def check_infisical_auth() -> bool:
    """Check if Infisical CLI is authenticated."""
    try:
        result = subprocess.run(
            ["infisical", "secrets"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        # If authenticated, this should either succeed or show a project error
        # If not authenticated, it will show auth error
        output = (result.stdout or result.stderr or "").lower()
        return not ("authenticate" in output or "login" in output)
    except (subprocess.SubprocessError, OSError):
        return False


def check_infisical_available() -> tuple[bool, str]:
    """
    Check if Infisical is available and authenticated.

    Returns:
        Tuple of (is_available: bool, reason: str)
    """
    if not check_infisical_cli():
        return False, "Infisical CLI not installed"

    if not check_infisical_auth():
        return False, "Infisical CLI not authenticated"

    return True, "Infisical available"


def get_infisical_secrets() -> dict[str, str]:
    """
    Get all secrets from Infisical.

    Returns:
        Dictionary of secret key-value pairs
    """
    secrets_dict = {}

    try:
        # Export secrets from Infisical
        result = subprocess.run(
            ["infisical", "export", "--format=dotenv"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode == 0 and result.stdout:
            # Parse the dotenv format output
            for raw_line in result.stdout.strip().split("\n"):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes if present
                    if (value.startswith('"') and value.endswith('"')) or (
                        value.startswith("'") and value.endswith("'")
                    ):
                        value = value[1:-1]
                    secrets_dict[key] = value

    except Exception as e:
        print(f"Warning: Could not fetch secrets from Infisical: {e}")

    return secrets_dict


def set_infisical_secret(key: str, value: str) -> bool:
    """
    Set a secret in Infisical using CLI.

    Returns:
        True if successful, False otherwise
    """
    try:
        cmd = ["infisical", "secrets", "set", f"{key}={value}"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode == 0:
            return True
        error_msg = result.stderr or result.stdout or "Unknown error"
        print(f"  Warning: Error setting {key} in Infisical: {error_msg.strip()}")
        return False
    except subprocess.TimeoutExpired:
        print(f"  Warning: Timeout setting {key} in Infisical")
        return False
    except Exception as e:
        print(f"  Warning: Exception setting {key} in Infisical: {e}")
        return False


def sync_infisical_to_env(env_path: Path) -> bool:
    """
    Export secrets from Infisical and update .env file.
    Preserves non-secret configuration in .env.

    Returns:
        True if successful, False otherwise
    """
    try:
        # Export from Infisical
        result = subprocess.run(
            ["infisical", "export", "--format=dotenv"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode != 0 or not result.stdout:
            return False

        # Parse Infisical secrets
        infisical_secrets = {}
        for raw_line in result.stdout.strip().split("\n"):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                infisical_secrets[key] = value

        # Read existing .env file
        if not env_path.exists():
            return False

        with env_path.open(encoding="utf-8") as f:
            lines = f.readlines()

        # Update .env file with Infisical secrets
        new_lines = []
        updated_keys = set()

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                new_lines.append(line)
                continue

            if "=" in stripped:
                key, value = stripped.split("=", 1)
                key = key.strip()

                # If this is a secret key and exists in Infisical, update it
                if is_secret_key(key) and key in infisical_secrets:
                    new_lines.append(f"{key}={infisical_secrets[key]}\n")
                    updated_keys.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        # Add any Infisical secrets that aren't in .env yet
        existing_keys = set()
        for line in lines:
            if "=" in line.strip() and not line.strip().startswith("#"):
                key = line.split("=", 1)[0].strip()
                existing_keys.add(key)

        for key, value in infisical_secrets.items():
            if key not in existing_keys and is_secret_key(key):
                new_lines.append(f"{key}={value}\n")
                updated_keys.add(key)

        # Write updated .env file
        with env_path.open("w", encoding="utf-8") as f:
            f.writelines(new_lines)

        if updated_keys:
            print(f"  Synced {len(updated_keys)} secrets from Infisical to .env")

        return True

    except Exception as e:
        print(f"  Warning: Could not sync Infisical to .env: {e}")
        return False


def create_basic_env_template(env_path):
    """Create a basic .env file template with all required keys."""
    template = """############
# N8N Configuration
############
N8N_ENCRYPTION_KEY=
N8N_USER_MANAGEMENT_JWT_SECRET=

############
# Supabase Secrets
############
POSTGRES_PASSWORD=
POSTGRES_HOST=supabase-db
POSTGRES_PORT=5432
POSTGRES_DB=postgres
JWT_SECRET=
JWT_EXPIRY=3600
ANON_KEY=
SERVICE_ROLE_KEY=
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=
SECRET_KEY_BASE=
VAULT_ENC_KEY=
PG_META_CRYPTO_KEY=
LOGFLARE_PUBLIC_ACCESS_TOKEN=
LOGFLARE_PRIVATE_ACCESS_TOKEN=
POOLER_TENANT_ID=
POOLER_DEFAULT_POOL_SIZE=20
POOLER_MAX_CLIENT_CONN=100
POOLER_DB_POOL_SIZE=10
POOLER_PROXY_PORT_TRANSACTION=6543

############
# Supabase Storage (S3 Compatible)
############
SUPABASE_MINIO_ROOT_USER=supa-storage
SUPABASE_MINIO_ROOT_PASSWORD=secret1234

############
# Supabase Configuration
############
# API and Site URLs (update for production with your domain)
API_EXTERNAL_URL=http://localhost:8011
SITE_URL=http://localhost:3000
SUPABASE_PUBLIC_URL=http://localhost:8011

# Kong Gateway Ports
KONG_HTTP_PORT=8011
KONG_HTTPS_PORT=8443

# Studio Configuration
STUDIO_DEFAULT_ORGANIZATION=Default Organization
STUDIO_DEFAULT_PROJECT=Default Project

# PostgREST Configuration
PGRST_DB_SCHEMAS=public,storage,graphql_public

# Auth Configuration (GoTrue)
DISABLE_SIGNUP=false
ENABLE_EMAIL_SIGNUP=true
ENABLE_EMAIL_AUTOCONFIRM=false
ENABLE_ANONYMOUS_USERS=false
ENABLE_PHONE_SIGNUP=false
ENABLE_PHONE_AUTOCONFIRM=false
ADDITIONAL_REDIRECT_URLS=

# SMTP Configuration (Optional - for email sending)
# Leave empty if not using email features
SMTP_ADMIN_EMAIL=
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_SENDER_NAME=Supabase

# Mailer URL Paths
MAILER_URLPATHS_INVITE=/auth/v1/verify
MAILER_URLPATHS_CONFIRMATION=/auth/v1/verify
MAILER_URLPATHS_RECOVERY=/auth/v1/verify
MAILER_URLPATHS_EMAIL_CHANGE=/auth/v1/verify

# Edge Functions Configuration
FUNCTIONS_VERIFY_JWT=true

# Image Proxy Configuration
IMGPROXY_ENABLE_WEBP_DETECTION=true

# OpenAI API Key (Optional - for AI Assistant in Studio)
OPENAI_API_KEY=

############
# Neo4j Secrets
############
NEO4J_AUTH=

############
# MongoDB Secrets
############
MONGODB_ROOT_USERNAME=admin
MONGODB_ROOT_PASSWORD=
MONGODB_DATABASE=admin
MONGODB_EXPRESS_USERNAME=admin
MONGODB_EXPRESS_PASSWORD=

############
# Langfuse credentials
############
CLICKHOUSE_PASSWORD=
MINIO_ROOT_PASSWORD=
LANGFUSE_SALT=
NEXTAUTH_SECRET=
ENCRYPTION_KEY=

############
# Infisical Configuration
############
INFISICAL_ENCRYPTION_KEY=
INFISICAL_AUTH_SECRET=
INFISICAL_HOSTNAME=:8010
INFISICAL_SITE_URL=http://localhost:8010

# Google OAuth/SSO for Infisical (optional)
# Get these from Google Cloud Console: https://console.cloud.google.com/
# GOOGLE_CLIENT_ID=your-google-client-id
# GOOGLE_CLIENT_SECRET=your-google-client-secret

############
# Flowise
############
FLOWISE_PASSWORD=

############
# Docker Hub Credentials
############
DOCKER_HUB_USERNAME=
DOCKER_HUB_PASSWORD=

############
# Cloudflare Tunnel (Optional)
############
CLOUDFLARE_TUNNEL_TOKEN=

############
# Hostname Configuration (Optional)
############
# N8N_HOSTNAME=
# WEBUI_HOSTNAME=
# FLOWISE_HOSTNAME=
# SUPABASE_HOSTNAME=
# OLLAMA_HOSTNAME=
# SEARXNG_HOSTNAME=
# LANGFUSE_HOSTNAME=
# NEO4J_HOSTNAME=
# COMFYUI_HOSTNAME=
# INFISICAL_HOSTNAME=
"""
    env_path_obj = Path(env_path)
    with env_path_obj.open("w") as f:
        f.write(template)
    print(f"Created basic .env template at {env_path}")


def main():
    """Generate passwords for .env file."""
    parser = argparse.ArgumentParser(
        description="Generate XKCD-style passphrases for .env file setup"
    )
    parser.add_argument(
        "--use-infisical",
        action="store_true",
        help="Use Infisical as source of truth (generate → Infisical → .env)",
    )
    parser.add_argument(
        "--no-infisical",
        action="store_true",
        help="Skip Infisical and generate directly in .env file",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("  Environment File Password Generator")
    print("  Using XKCD-style passphrases for security and memorability")
    print("=" * 60)
    print()

    env_path = get_env_file_path()
    example_env_path = get_example_env_file_path()

    # Determine if we should use Infisical
    use_infisical = False
    if args.no_infisical:
        use_infisical = False
        print("Infisical disabled (--no-infisical flag)")
    elif args.use_infisical:
        # Explicitly requested
        is_available, reason = check_infisical_available()
        if is_available:
            use_infisical = True
            print("Using Infisical as source of truth")
        else:
            print(f"Warning: Infisical requested but not available: {reason}")
            print("Falling back to .env generation")
            use_infisical = False
    else:
        # Auto-detect
        is_available, reason = check_infisical_available()
        if is_available:
            use_infisical = True
            print("Infisical detected - using as source of truth")
        else:
            print(f"Infisical not available ({reason}) - generating in .env")
            use_infisical = False

    print()

    if not env_path.exists():
        if example_env_path.exists():
            print("Creating .env from .env_sample...")
            shutil.copy(example_env_path, env_path)
        else:
            print(".env_sample not found. Creating basic .env template...")
            create_basic_env_template(env_path)
            print("Basic template created. Generating passwords...")
    else:
        print(f"Found existing .env file at {env_path}")

    # Configuration
    passphrase_words = 4  # Number of words in passphrases
    hex_length = 32  # Length for hex strings

    # Define generators (excluding JWT_SECRET, ANON_KEY, SERVICE_ROLE_KEY - handled separately)
    generators = {
        "N8N_ENCRYPTION_KEY": (generate_hex_string, {"length": hex_length}),
        "N8N_USER_MANAGEMENT_JWT_SECRET": (generate_hex_string, {"length": hex_length}),
        "POSTGRES_PASSWORD": (generate_passphrase, {"num_words": passphrase_words}),
        "DASHBOARD_PASSWORD": (generate_passphrase, {"num_words": passphrase_words}),
        "SECRET_KEY_BASE": (generate_hex_string, {"length": 64}),
        "VAULT_ENC_KEY": (generate_hex_string, {"length": 32}),
        "PG_META_CRYPTO_KEY": (generate_hex_string, {"length": 32}),
        "LOGFLARE_PUBLIC_ACCESS_TOKEN": (generate_hex_string, {"length": 32}),
        "LOGFLARE_PRIVATE_ACCESS_TOKEN": (generate_hex_string, {"length": 32}),
        "POOLER_TENANT_ID": (generate_uuid, {}),
        "MONGODB_ROOT_PASSWORD": (generate_passphrase, {"num_words": passphrase_words}),
        "MONGODB_EXPRESS_PASSWORD": (generate_passphrase, {"num_words": passphrase_words}),
        "CLICKHOUSE_PASSWORD": (generate_passphrase, {"num_words": passphrase_words}),
        "MINIO_ROOT_PASSWORD": (generate_passphrase, {"num_words": passphrase_words}),
        "LANGFUSE_SALT": (generate_hex_string, {"length": hex_length}),
        "NEXTAUTH_SECRET": (generate_hex_string, {"length": hex_length}),
        "ENCRYPTION_KEY": (
            generate_hex_string,
            {"length": 64},
        ),  # Langfuse requires 256 bits (64 hex chars)
        "INFISICAL_ENCRYPTION_KEY": (generate_hex_string, {"length": 16}),
        "INFISICAL_AUTH_SECRET": (generate_base64_string, {"length": 32}),
        "FLOWISE_PASSWORD": (generate_passphrase, {"num_words": passphrase_words}),
        # Note: IMMICH_ADMIN_API_KEY is not generated here - it must be obtained from Immich admin panel
        # IMMICH_ADMIN_API_KEY is set manually after creating an admin API key in Immich
    }

    # Read existing lines
    try:
        with env_path.open() as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading .env file: {e}", file=sys.stderr)
        sys.exit(1)

    # If file is empty, create basic template
    if not lines or all(
        line.strip() == "" or line.strip().startswith("#") for line in lines if line.strip()
    ):
        print("Warning: .env file appears to be empty or only contains comments.")
        print("Creating basic template...")
        create_basic_env_template(env_path)
        with env_path.open() as f:
            lines = f.readlines()

    # Get existing secrets from Infisical if using it
    infisical_secrets = {}
    if use_infisical:
        print("Fetching existing secrets from Infisical...")
        infisical_secrets = get_infisical_secrets()
        print(f"Found {len(infisical_secrets)} secrets in Infisical")
        print()

    # First pass: Extract existing keys to check what needs to be generated
    existing_jwt_secret = None
    existing_anon_key = None
    existing_service_role_key = None
    existing_keys_dict = {}
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()
            existing_keys_dict[key] = value
            if key == "JWT_SECRET" and value:
                existing_jwt_secret = value
            elif key == "ANON_KEY" and value:
                existing_anon_key = value
            elif key == "SERVICE_ROLE_KEY" and value:
                existing_service_role_key = value

    # If using Infisical, prefer Infisical values over .env values for secrets
    if use_infisical:
        for key, value in infisical_secrets.items():
            if is_secret_key(key):
                existing_keys_dict[key] = value
                if key == "JWT_SECRET" and value:
                    existing_jwt_secret = value
                elif key == "ANON_KEY" and value:
                    existing_anon_key = value
                elif key == "SERVICE_ROLE_KEY" and value:
                    existing_service_role_key = value

    # Only generate JWT tokens if they're missing or are placeholders
    # Check if existing values are placeholders
    jwt_secret_is_placeholder = (
        not existing_jwt_secret
        or "your-" in existing_jwt_secret.lower()
        or "super-secret" in existing_jwt_secret.lower()
        or "placeholder" in existing_jwt_secret.lower()
        or "generate-" in existing_jwt_secret.lower()
    )

    jwt_secret = existing_jwt_secret if not jwt_secret_is_placeholder else None
    anon_key = (
        existing_anon_key
        if existing_anon_key and "your-" not in existing_anon_key.lower()
        else None
    )
    service_role_key = (
        existing_service_role_key
        if existing_service_role_key and "your-" not in existing_service_role_key.lower()
        else None
    )
    jwt_keys_generated = False

    # Check if we need to generate JWT keys
    need_jwt_secret = not jwt_secret
    need_anon_key = not anon_key
    need_service_role_key = not service_role_key

    if need_jwt_secret or need_anon_key or need_service_role_key:
        # Generate JWT_SECRET if not present (base64, 30 bytes for Supabase)
        if not jwt_secret:
            jwt_secret = base64.b64encode(secrets.token_bytes(30)).decode("utf-8")

        # Generate Supabase JWT tokens (only if needed)
        if need_anon_key or need_service_role_key:
            _, anon_key, service_role_key = generate_supabase_jwt_tokens(jwt_secret)
            jwt_keys_generated = True

    new_lines = []
    generated_count = 0
    secrets_to_set_in_infisical = {}  # Track secrets to set in Infisical

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        if "=" in stripped:
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()

            new_value = value
            updated = False

            if key == "JWT_SECRET":
                # Use generated JWT_SECRET if empty or placeholder
                is_placeholder = (
                    not value
                    or "your-" in value.lower()
                    or "super-secret" in value.lower()
                    or "placeholder" in value.lower()
                    or "generate-" in value.lower()
                )
                if is_placeholder:
                    new_value = jwt_secret
                    updated = True
            elif key == "ANON_KEY":
                # Use generated ANON_KEY
                if not value:
                    new_value = anon_key
                    updated = True
            elif key == "SERVICE_ROLE_KEY":
                # Use generated SERVICE_ROLE_KEY
                if not value:
                    new_value = service_role_key
                    updated = True
            elif key in generators:
                # Check if we need to generate this value
                # If using Infisical, check if it exists there first
                needs_generation = False
                if use_infisical:
                    # Check if missing in Infisical
                    if key not in infisical_secrets:
                        needs_generation = True
                    # Also check if .env value is placeholder (might need update)
                    elif not value or "your-" in value.lower() or "placeholder" in value.lower():
                        # Use Infisical value if available
                        if key in infisical_secrets:
                            new_value = infisical_secrets[key]
                            updated = True
                        else:
                            needs_generation = True
                    # Value exists in both, prefer Infisical
                    elif key in infisical_secrets:
                        new_value = infisical_secrets[key]
                        if new_value != value:
                            updated = True
                else:
                    # Not using Infisical, check if value is placeholder
                    is_placeholder = (
                        not value
                        or "your-" in value.lower()
                        or "super-secret-key" in value.lower()
                        or "placeholder" in value.lower()
                        or "generate-" in value.lower()
                        or "example" in value.lower()
                        or value.startswith("#")  # Commented out values
                    )
                    needs_generation = is_placeholder

                if needs_generation:
                    func, kwargs = generators[key]
                    new_value = func(**kwargs)
                    updated = True
            elif key == "NEO4J_AUTH":
                # Special handling for NEO4J_AUTH
                is_placeholder = (
                    not value
                    or value == "neo4j/your_password"
                    or "your-" in value.lower()
                    or "placeholder" in value.lower()
                )
                if is_placeholder:
                    new_value = f"neo4j/{generate_passphrase(passphrase_words)}"
                    updated = True
            elif key == "ENCRYPTION_KEY" and (
                "generate-" in value.lower() or "openssl" in value.lower()
            ):
                # Handle ENCRYPTION_KEY with comment
                func, kwargs = generators.get(key, (generate_hex_string, {"length": 32}))
                new_value = func(**kwargs)
                updated = True
            elif key == "VAULT_ENC_KEY":
                # Handle VAULT_ENC_KEY placeholder
                is_placeholder = (
                    not value or "your-" in value.lower() or "placeholder" in value.lower()
                )
                if is_placeholder:
                    new_value = generate_hex_string(length=32)
                    updated = True
            elif key == "SECRET_KEY_BASE":
                # Handle SECRET_KEY_BASE placeholder (for Realtime/Pooler)
                is_placeholder = (
                    not value or "your-" in value.lower() or "placeholder" in value.lower()
                )
                if is_placeholder:
                    new_value = generate_hex_string(length=64)
                    updated = True
            elif key == "PG_META_CRYPTO_KEY":
                # Handle PG_META_CRYPTO_KEY placeholder
                is_placeholder = (
                    not value or "your-" in value.lower() or "placeholder" in value.lower()
                )
                if is_placeholder:
                    new_value = generate_hex_string(length=32)
                    updated = True
            elif key in ["LOGFLARE_PUBLIC_ACCESS_TOKEN", "LOGFLARE_PRIVATE_ACCESS_TOKEN"]:
                # Handle Logflare tokens
                is_placeholder = (
                    not value or "your-" in value.lower() or "placeholder" in value.lower()
                )
                if is_placeholder:
                    new_value = generate_hex_string(length=32)
                    updated = True

            if updated:
                print(f"Generated value for {key}")
                # If using Infisical and this is a secret, track it for Infisical
                if use_infisical and is_secret_key(key):
                    secrets_to_set_in_infisical[key] = new_value
                new_lines.append(f"{key}={new_value}\n")
                generated_count += 1
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Check for missing keys in the file that need to be added
    existing_keys_set = set(existing_keys_dict.keys())

    # Add missing generators
    for key, (func, kwargs) in generators.items():
        if key not in existing_keys_set:
            # If using Infisical, check if it exists there
            if use_infisical and key in infisical_secrets:
                val = infisical_secrets[key]
                print(f"Using existing Infisical value for {key}")
            else:
                val = func(**kwargs)
                # If using Infisical and this is a secret, track it for Infisical
                if use_infisical and is_secret_key(key):
                    secrets_to_set_in_infisical[key] = val
            new_lines.append(f"{key}={val}\n")
            print(f"Appended missing key {key}")
            generated_count += 1

    # Add missing Supabase JWT keys if not present (only if we generated them)
    if jwt_keys_generated or need_jwt_secret:
        if "JWT_SECRET" not in existing_keys_set:
            if use_infisical:
                secrets_to_set_in_infisical["JWT_SECRET"] = jwt_secret
            new_lines.append(f"JWT_SECRET={jwt_secret}\n")
            print("Appended missing key JWT_SECRET")
            generated_count += 1

        if need_anon_key and "ANON_KEY" not in existing_keys_set:
            if use_infisical:
                secrets_to_set_in_infisical["ANON_KEY"] = anon_key
            new_lines.append(f"ANON_KEY={anon_key}\n")
            print("Appended missing key ANON_KEY")
            generated_count += 1

        if need_service_role_key and "SERVICE_ROLE_KEY" not in existing_keys_set:
            if use_infisical:
                secrets_to_set_in_infisical["SERVICE_ROLE_KEY"] = service_role_key
            new_lines.append(f"SERVICE_ROLE_KEY={service_role_key}\n")
            print("Appended missing key SERVICE_ROLE_KEY")
            generated_count += 1

    # Prompt for Docker Hub credentials if missing
    docker_hub_username = existing_keys_dict.get("DOCKER_HUB_USERNAME", "").strip()
    docker_hub_password = existing_keys_dict.get("DOCKER_HUB_PASSWORD", "").strip()
    docker_hub_token = existing_keys_dict.get("DOCKER_HUB_TOKEN", "").strip()

    docker_creds_added = False
    if not docker_hub_username and not docker_hub_password and not docker_hub_token:
        print()
        print("-" * 60)
        print("Docker Hub Authentication")
        print("-" * 60)
        print("Docker Hub credentials are required to pull images from dhi.io registry.")
        print("You can use either:")
        print("  1. Username + Password/Personal Access Token (PAT)")
        print("  2. Personal Access Token only (DOCKER_HUB_TOKEN)")
        print()

        try:
            response = (
                input("Would you like to add Docker Hub credentials now? (y/N): ").strip().lower()
            )

            if response in ["y", "yes"]:
                use_token_only = input(
                    "Use Personal Access Token only? (y/N): "
                ).strip().lower() in ["y", "yes"]

                if use_token_only:
                    token = getpass.getpass("Enter your Docker Hub Personal Access Token: ").strip()
                    if token:
                        # Update or add DOCKER_HUB_TOKEN in new_lines
                        updated = False
                        for i, line in enumerate(new_lines):
                            if "DOCKER_HUB_TOKEN" in line:
                                new_lines[i] = f"DOCKER_HUB_TOKEN={token}\n"
                                updated = True
                                docker_creds_added = True
                                generated_count += 1
                                print("Added DOCKER_HUB_TOKEN")
                                break

                        if not updated:
                            # Find Docker Hub section or add at end
                            docker_section_idx = -1
                            for i, line in enumerate(new_lines):
                                if "Docker Hub" in line or "DOCKER_HUB" in line:
                                    docker_section_idx = i
                                    break

                            if docker_section_idx >= 0:
                                # Insert after Docker Hub section header
                                insert_idx = docker_section_idx + 1
                                while insert_idx < len(new_lines) and (
                                    new_lines[insert_idx].strip().startswith("#")
                                    or new_lines[insert_idx].strip() == ""
                                ):
                                    insert_idx += 1
                                new_lines.insert(insert_idx, f"DOCKER_HUB_TOKEN={token}\n")
                            else:
                                new_lines.append(f"DOCKER_HUB_TOKEN={token}\n")

                            docker_creds_added = True
                            generated_count += 1
                            print("Added DOCKER_HUB_TOKEN")
                else:
                    username = input("Enter your Docker Hub username: ").strip()
                    if username:
                        password = getpass.getpass(
                            "Enter your Docker Hub password or Personal Access Token: "
                        ).strip()
                        if password:
                            # Update or add credentials
                            username_updated = False
                            password_updated = False

                            for i, line in enumerate(new_lines):
                                if "DOCKER_HUB_USERNAME" in line:
                                    new_lines[i] = f"DOCKER_HUB_USERNAME={username}\n"
                                    username_updated = True
                                elif "DOCKER_HUB_PASSWORD" in line:
                                    new_lines[i] = f"DOCKER_HUB_PASSWORD={password}\n"
                                    password_updated = True

                            if not username_updated or not password_updated:
                                # Find Docker Hub section or add at end
                                docker_section_idx = -1
                                for i, line in enumerate(new_lines):
                                    if "Docker Hub" in line or "DOCKER_HUB" in line:
                                        docker_section_idx = i
                                        break

                                if docker_section_idx >= 0:
                                    insert_idx = docker_section_idx + 1
                                    while insert_idx < len(new_lines) and (
                                        new_lines[insert_idx].strip().startswith("#")
                                        or new_lines[insert_idx].strip() == ""
                                    ):
                                        insert_idx += 1
                                    if not username_updated:
                                        new_lines.insert(
                                            insert_idx, f"DOCKER_HUB_USERNAME={username}\n"
                                        )
                                        insert_idx += 1
                                    if not password_updated:
                                        new_lines.insert(
                                            insert_idx, f"DOCKER_HUB_PASSWORD={password}\n"
                                        )
                                else:
                                    if not username_updated:
                                        new_lines.append(f"DOCKER_HUB_USERNAME={username}\n")
                                    if not password_updated:
                                        new_lines.append(f"DOCKER_HUB_PASSWORD={password}\n")

                            docker_creds_added = True
                            generated_count += 1
                            print("Added Docker Hub credentials")
            else:
                print("Skipping Docker Hub credentials. You can add them manually later.")
                print("  - DOCKER_HUB_USERNAME and DOCKER_HUB_PASSWORD")
                print("  - OR DOCKER_HUB_TOKEN (Personal Access Token)")
        except (KeyboardInterrupt, EOFError):
            print("\nSkipping Docker Hub credentials due to input cancellation.")
            print("You can add them manually later.")

    # If using Infisical, set secrets in Infisical first
    if use_infisical and secrets_to_set_in_infisical:
        print()
        print("=" * 60)
        print("Setting secrets in Infisical...")
        print("=" * 60)

        infisical_success = 0
        infisical_failed = 0

        for key, value in sorted(secrets_to_set_in_infisical.items()):
            print(f"Setting {key} in Infisical...", end=" ", flush=True)
            if set_infisical_secret(key, value):
                print("✓")
                infisical_success += 1
            else:
                print("✗")
                infisical_failed += 1

        print()
        if infisical_failed > 0:
            print(f"Warning: {infisical_failed} secret(s) failed to set in Infisical")
            print("They will still be written to .env file")

        # Sync Infisical back to .env to ensure consistency
        print()
        print("Syncing Infisical secrets back to .env...")
        sync_infisical_to_env(env_path)
        print()

    if generated_count > 0:
        # Create backup
        backup_path = env_path.with_suffix(".env.bak")
        shutil.copy(env_path, backup_path)
        print(f"Backed up original .env to {backup_path}")

        # Write new content (only if not using Infisical, or if Infisical sync didn't update everything)
        if not use_infisical:
            with env_path.open("w") as f:
                f.writelines(new_lines)
            print(f"Updated {generated_count} passwords in .env")
        else:
            # Re-read .env after Infisical sync to preserve any updates
            # But we still need to write non-secret config updates
            with env_path.open(encoding="utf-8") as f:
                current_lines = f.readlines()

            # Merge non-secret updates from new_lines into current .env
            current_keys = {}
            for line in current_lines:
                if "=" in line.strip() and not line.strip().startswith("#"):
                    key = line.split("=", 1)[0].strip()
                    current_keys[key] = line

            # Write merged content
            merged_lines = []
            for line in new_lines:
                stripped = line.strip()
                if stripped and "=" in stripped and not stripped.startswith("#"):
                    key = stripped.split("=", 1)[0].strip()
                    # For non-secrets, use our generated value
                    # For secrets, Infisical sync should have handled it
                    if not is_secret_key(key) or key not in secrets_to_set_in_infisical:
                        merged_lines.append(line)
                else:
                    merged_lines.append(line)

            # Add any current lines that weren't in new_lines (from Infisical sync)
            for line in current_lines:
                stripped = line.strip()
                if stripped and "=" in stripped and not stripped.startswith("#"):
                    key = stripped.split("=", 1)[0].strip()
                    if key not in [
                        l.split("=", 1)[0].strip() for l in merged_lines if "=" in l.strip()
                    ]:
                        merged_lines.append(line)

            with env_path.open("w", encoding="utf-8") as f:
                f.writelines(merged_lines)

            print(f"Updated {generated_count} passwords (set in Infisical, synced to .env)")
    else:
        print("No missing passwords found. .env is up to date.")

    print()
    print("-" * 60)
    print("Summary:")
    print(f"  - Generated {generated_count} password(s) and key(s)")
    if use_infisical:
        print("  - Secrets set in Infisical (source of truth)")
        print("  - .env file synced as fallback")
    if docker_creds_added:
        print("  - Docker Hub credentials added")
    if jwt_keys_generated:
        print("  - Supabase JWT keys (ANON_KEY, SERVICE_ROLE_KEY) generated")
    elif existing_anon_key and existing_service_role_key:
        print("  - Supabase JWT keys already present (not regenerated)")
    print()
    print("Next steps:")
    print("1. Review the .env file")
    if not docker_creds_added:
        print("2. Add your Docker Hub credentials manually if needed")
    if use_infisical:
        print("3. Verify secrets in Infisical UI")
        print("4. Start services: python start_services.py --profile cpu --use-infisical")
    else:
        print("3. Start services: python start_services.py --profile cpu")
    print("-" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGeneration cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
