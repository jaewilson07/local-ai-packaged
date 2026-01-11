#!/usr/bin/env python3
"""
start_services.py

This script manages services using the stack-based architecture:
- 00-infrastructure: cloudflared, caddy, redis
- infisical-standalone: infisical-backend, infisical-db, infisical-redis (standalone directory)
- 01-data: supabase, qdrant, neo4j, mongodb, minio
- 02-compute: ollama, comfyui
- 03-apps: n8n, flowise, open-webui, searxng, langfuse, clickhouse
- 04-lambda: FastAPI server with MCP and REST APIs

Each stack uses its own Docker Compose project name but shares the external network ("ai-network").
Infisical runs from a standalone directory and will be automatically started if not running.
"""

import argparse
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Define stack-to-file mappings
STACK_FILES = {
    "infrastructure": ["00-infrastructure/docker-compose.yml"],
    # Note: infisical is handled separately via standalone directory
    "data": [
        "01-data/supabase/docker-compose.yml",
        "01-data/qdrant/docker-compose.yml",
        "01-data/neo4j/docker-compose.yml",
        "01-data/mongodb/docker-compose.yml",
        "01-data/minio/docker-compose.yml",
    ],
    "compute": ["02-compute/docker-compose.yml"],
    "apps": ["03-apps/docker-compose.yml"],
    "lambda": ["04-lambda/docker-compose.yml"],
}

# Define stack directory mappings
STACK_DIRS = {
    "infrastructure": "00-infrastructure",
    # Note: infisical is in standalone directory, not in this repo
    "data": "01-data",
    "compute": "02-compute",
    "apps": "03-apps",
    "lambda": "04-lambda",
}

# Infisical standalone directory path
INFISICAL_STANDALONE_DIR = "/home/jaewilson07/GitHub/infisical-standalone"

# Define stack-to-project name mappings
STACK_PROJECTS = {
    "infrastructure": "localai-infra",
    "infisical": "localai-infisical",
    "data": "localai-data",
    "compute": "localai-compute",
    "apps": "localai-apps",
    "lambda": "localai-lambda",
}


def run_command(cmd, cwd=None, check=True):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        if result.stdout:
            print("Stdout:", result.stdout)
        if result.stderr:
            print("Stderr:", result.stderr)
        if check:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )
    if result.stdout:
        print(result.stdout)
    return result


def ensure_network_exists(network_name="ai-network"):
    """Ensure the external Docker network exists, creating it if necessary."""
    print(f"Checking for network '{network_name}'...")

    # Check if network exists
    result = subprocess.run(
        ["docker", "network", "inspect", network_name], capture_output=True, text=True, check=False
    )

    if result.returncode == 0:
        print(f"✓ Network '{network_name}' already exists")
        return True

    # Network doesn't exist, create it
    print(f"Network '{network_name}' not found. Creating it...")
    try:
        run_command(["docker", "network", "create", network_name])
        print(f"✓ Network '{network_name}' created successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create network '{network_name}': {e}")
        return False


def load_env_file(env_path=".env"):
    """Load environment variables from .env file."""
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    env_vars[key] = value
    return env_vars


def is_dhi_authenticated():
    """Check if already authenticated to dhi.io registry."""
    docker_config_path = os.path.expanduser("~/.docker/config.json")
    if platform.system() == "Windows":
        docker_config_path = os.path.join(
            os.environ.get("USERPROFILE", ""), ".docker", "config.json"
        )

    if not os.path.exists(docker_config_path):
        return False

    try:
        with open(docker_config_path, encoding="utf-8") as f:
            config = json.load(f)
            auths = config.get("auths", {})
            # Check if dhi.io is in the auths
            return "dhi.io" in auths or "https://dhi.io" in auths
    except (OSError, json.JSONDecodeError, KeyError):
        return False


def authenticate_dhi_registry(skip_auth=False):
    """Authenticate to dhi.io Docker registry using credentials from .env file."""
    if skip_auth:
        print("Skipping dhi.io authentication (--skip-dhi-auth flag set).")
        return True

    # Check if already authenticated
    if is_dhi_authenticated():
        print("Already authenticated to dhi.io registry.")
        return True

    # Load environment variables from .env
    env_vars = load_env_file()

    # Get credentials - support both DOCKER_HUB_PASSWORD and DOCKER_HUB_TOKEN
    username = env_vars.get("DOCKER_HUB_USERNAME") or os.environ.get("DOCKER_HUB_USERNAME")
    password = (
        env_vars.get("DOCKER_HUB_PASSWORD")
        or env_vars.get("DOCKER_HUB_TOKEN")
        or os.environ.get("DOCKER_HUB_PASSWORD")
        or os.environ.get("DOCKER_HUB_TOKEN")
    )

    if not username:
        print("Warning: DOCKER_HUB_USERNAME not found in .env file or environment variables.")
        print("Skipping dhi.io authentication. You may need to manually run: docker login dhi.io")
        print(
            "Or set DOCKER_HUB_USERNAME and DOCKER_HUB_PASSWORD/DOCKER_HUB_TOKEN in your .env file."
        )
        return False

    if not password:
        print(
            "Warning: DOCKER_HUB_PASSWORD or DOCKER_HUB_TOKEN not found in .env file or environment variables."
        )
        print("Skipping dhi.io authentication. You may need to manually run: docker login dhi.io")
        print("Or set DOCKER_HUB_PASSWORD/DOCKER_HUB_TOKEN in your .env file.")
        print("For better security, use a Personal Access Token (PAT) instead of password.")
        print("Create a PAT at: https://hub.docker.com/settings/security")
        return False

    # Perform non-interactive login
    print("Authenticating to dhi.io registry...")
    try:
        # Use subprocess with stdin to securely pass password
        cmd = ["docker", "login", "dhi.io", "--username", username, "--password-stdin"]

        # Pass password via stdin to avoid shell history and command line exposure
        result = subprocess.run(cmd, input=password, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            print("Successfully authenticated to dhi.io registry.")
            return True
        else:
            error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
            print(f"Failed to authenticate to dhi.io registry: {error_msg}")
            print("\nTroubleshooting:")
            print("1. Verify your Docker Hub username and password/token are correct")
            print("2. For better security, use a Personal Access Token (PAT) instead of password")
            print("3. Create a PAT at: https://hub.docker.com/settings/security")
            print("4. Ensure you have a Docker Hub account (free account works)")
            print("5. Try manually running: docker login dhi.io")
            return False
    except FileNotFoundError:
        print(
            "Error: Docker command not found. Please ensure Docker is installed and in your PATH."
        )
        return False
    except Exception as e:
        print(f"Error during dhi.io authentication: {e}")
        print("You may need to manually run: docker login dhi.io")
        return False


def clone_supabase_repo():
    """Initialize and update the Supabase submodule."""
    target_dir = os.path.join("01-data", "supabase", "upstream")

    print(f"Initializing and updating Supabase submodule at {target_dir}...")

    # Initialize submodules if needed
    run_command(["git", "submodule", "update", "--init", "--recursive", target_dir], check=False)

    # Update the submodule to latest
    run_command(["git", "submodule", "update", "--remote", target_dir], check=False)

    # Configure sparse checkout if not already configured
    sparse_checkout_file = os.path.join(target_dir, ".git", "info", "sparse-checkout")
    if not os.path.exists(sparse_checkout_file):
        print("Configuring sparse checkout for Supabase submodule...")
        cwd = os.getcwd()
        os.chdir(target_dir)
        try:
            run_command(["git", "sparse-checkout", "init", "--cone"], check=False)
            run_command(["git", "sparse-checkout", "set", "docker"], check=False)
        finally:
            os.chdir(cwd)


def get_compose_files(stack, environment="private"):
    """Get list of compose files for a specific stack."""
    files = []

    # Determine which stacks to include
    target_stacks = []
    if stack == "all":
        target_stacks = ["infrastructure", "infisical", "data", "compute", "apps", "lambda"]
    elif stack == "infisical":
        # Infisical is handled separately, return empty list
        return []
    elif stack in STACK_FILES:
        target_stacks = [stack]
    else:
        print(f"Warning: Unknown stack '{stack}'")
        return []

    for s in target_stacks:
        if s == "infisical":
            # Skip infisical here, it's handled separately
            continue
        files.extend(STACK_FILES[s])

        # Add overrides for each stack if they exist
        stack_dir = STACK_DIRS.get(s)
        if stack_dir:
            override_file = os.path.join(stack_dir, f"docker-compose.override.{environment}.yml")
            if os.path.exists(override_file):
                files.append(override_file)

    # Filter out non-existent files
    return [f for f in files if os.path.exists(f)]


def get_stack_project_name(stack):
    """Get the Docker Compose project name for a specific stack."""
    if stack == "all":
        # For "all", we'll handle each stack separately
        return None
    return STACK_PROJECTS.get(stack, "localai")


def stop_services(stack="all", environment="private"):
    """Stop services for the specified stack."""
    print(f"Stopping services for stack: {stack}...")

    if stack == "all":
        # Stop each stack individually with its own project name
        for stack_name in STACK_PROJECTS:
            print(f"Stopping {stack_name} stack...")
            stop_single_stack(stack_name, environment)
    else:
        stop_single_stack(stack, environment)

    # Only perform aggressive container cleanup if stopping ALL services
    if stack == "all":
        print("Performing aggressive cleanup of known containers...")
        container_names = [
            "redis",
            "caddy",
            "cloudflared",
            "n8n",
            "flowise",
            "open-webui",
            "searxng",
            "qdrant",
            "neo4j",
            "mongodb",
            "minio",
            "langfuse-worker",
            "langfuse-web",
            "clickhouse",
            "ollama",
            "comfyui",
            "ollama-pull-llama",
            "comfyui-provision",
            "lambda-server",
            "infisical-backend",
            "infisical-db",
            "infisical-redis",
        ]

        for container_name in container_names:
            try:
                # Check if container exists and is running
                check_cmd = [
                    "docker",
                    "ps",
                    "-a",
                    "--filter",
                    f"name=^{container_name}$",
                    "--format",
                    "{{.Names}}",
                ]
                result = subprocess.run(check_cmd, capture_output=True, text=True, check=False)
                if container_name in result.stdout:
                    print(f"Stopping and removing container: {container_name}")
                    try:
                        subprocess.run(
                            ["docker", "stop", container_name],
                            capture_output=True,
                            check=False,
                            timeout=10,
                        )
                        subprocess.run(
                            ["docker", "rm", container_name],
                            capture_output=True,
                            check=False,
                            timeout=10,
                        )
                    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                        # Try force remove if normal remove fails
                        subprocess.run(
                            ["docker", "rm", "-f", container_name],
                            capture_output=True,
                            check=False,
                            timeout=10,
                        )
            except Exception:
                # Continue even if individual container removal fails
                pass


def stop_single_stack(stack, environment="private"):
    """Stop a single stack using its project name."""
    # Handle infisical separately (standalone directory)
    if stack == "infisical":
        manage_infisical_stack(action="stop", environment=environment)
        return

    if stack not in STACK_FILES:
        print(f"Warning: Unknown stack '{stack}'")
        return

    compose_files = get_compose_files(stack, environment)
    if not compose_files:
        print(f"No compose files found for stack '{stack}'")
        return

    project_name = get_stack_project_name(stack)
    cmd = ["docker", "compose", "-p", project_name]
    for file in compose_files:
        cmd.extend(["-f", file])
    cmd.append("down")

    try:
        run_command(cmd)
    except subprocess.CalledProcessError:
        print(f"Warning: Could not stop services for stack {stack} via compose.")


def pull_docker_images(profile=None, environment=None, stack="all"):
    """Pull latest versions of Docker images."""
    print(f"Pulling latest Docker images for stack: {stack}...")

    if stack == "all":
        # Pull images for each stack individually
        for stack_name in STACK_PROJECTS:
            print(f"Pulling images for {stack_name} stack...")
            pull_stack_images(stack_name, profile, environment)
    else:
        pull_stack_images(stack, profile, environment)

    print("Image pull complete!")


def pull_stack_images(stack, profile=None, environment=None):
    """Pull images for a single stack."""
    compose_files = get_compose_files(stack, environment)
    if not compose_files:
        print(f"No compose files found for stack '{stack}'")
        return

    project_name = get_stack_project_name(stack)
    cmd = ["docker", "compose", "-p", project_name]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    for file in compose_files:
        cmd.extend(["-f", file])

    cmd.extend(["pull"])
    try:
        run_command(cmd)
    except subprocess.CalledProcessError:
        print(f"Warning: Some images may not have been updated for stack '{stack}'.")


def manage_services(action="start", stack="all", profile=None, environment=None):
    """Start or stop services using stack-based architecture."""

    if action == "stop":
        stop_services(stack, environment)
        return True

    # Ensure network exists before starting any services
    if not ensure_network_exists("ai-network"):
        print("❌ Failed to ensure network exists. Cannot start services.")
        return False

    if stack == "all":
        # Start each stack individually with its own project name
        success = True
        for stack_name in STACK_PROJECTS:
            print(f"\n=== Starting {stack_name} stack ===")
            if not start_single_stack(stack_name, profile, environment):
                success = False
        return success
    else:
        return start_single_stack(stack, profile, environment)


def manage_infisical_stack(action="start", environment="private"):
    """Manage Infisical services from standalone directory."""
    infisical_dir = INFISICAL_STANDALONE_DIR
    compose_file = os.path.join(infisical_dir, "docker-compose.yml")
    override_file = os.path.join(infisical_dir, f"docker-compose.override.{environment}.yml")

    if not os.path.exists(compose_file):
        print(f"❌ Error: Docker Compose file not found at {compose_file}")
        print(f"   Please ensure Infisical is set up in {infisical_dir}")
        return False

    # Build docker compose command
    # Use "infisical" to match start_infisical.py for consistency
    cmd = ["docker", "compose", "-p", "infisical"]
    cmd.extend(["-f", compose_file])

    if os.path.exists(override_file):
        cmd.extend(["-f", override_file])

    # Try to use .env from local-ai-packaged project, or from infisical-standalone
    current_dir = os.getcwd()
    env_file_paths = [
        os.path.join(current_dir, ".env"),  # Current directory (local-ai-packaged)
        os.path.join(infisical_dir, ".env"),  # Standalone directory
    ]

    env_file_path = None
    for path in env_file_paths:
        if os.path.exists(path):
            env_file_path = os.path.abspath(path)
            break

    if env_file_path:
        cmd.extend(["--env-file", env_file_path])
    else:
        print("⚠️  Warning: No .env file found. Using environment variables from shell.")

    if action == "stop":
        cmd.append("down")
        print("Stopping Infisical services...")
    else:
        cmd.extend(["up", "-d"])
        print("Starting Infisical services...")

    try:
        # Run from the infisical directory
        run_command(cmd, cwd=infisical_dir)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error {action}ing Infisical services: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def start_single_stack(stack, profile=None, environment=None):
    """Start a single stack using its project name."""
    print(f"Starting services for stack: {stack}...")

    # Handle infisical separately (standalone directory)
    if stack == "infisical":
        return manage_infisical_stack(action="start", environment=environment)

    compose_files = get_compose_files(stack, environment)
    if not compose_files:
        print(f"No compose files found for stack '{stack}'")
        return False

    project_name = get_stack_project_name(stack)

    # Build docker compose command
    cmd = ["docker", "compose", "-p", project_name]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    for file in compose_files:
        cmd.extend(["-f", file])

    # Always add .env file for environment variables
    env_file_path = ".env"
    if os.path.exists(env_file_path):
        cmd.extend(["--env-file", env_file_path])

    cmd.extend(["up", "-d"])

    try:
        run_command(cmd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error starting services for stack '{stack}': {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)

        # Provide helpful error messages for common issues
        error_output = (e.stderr or "") + (e.stdout or "")
        if "nvidia" in error_output.lower() or "gpu" in error_output.lower():
            print("\n💡 GPU-related error detected. Common solutions:")
            print("   1. Verify NVIDIA drivers: nvidia-smi")
            print("   2. Check Docker NVIDIA runtime: docker info | grep -i nvidia")
            print("   3. Install nvidia-container-toolkit if missing")
            print("   4. Try CPU mode: python start_services.py --profile cpu")

        if "profile" in error_output.lower() or "unknown profile" in error_output.lower():
            print("\n💡 Profile error detected. Valid profiles are:")
            print("   - cpu (default)")
            print("   - gpu-nvidia (for NVIDIA GPUs)")
            print("   - gpu-amd (for AMD GPUs)")
            print("   - none (no compute services)")

        return False


def check_nvidia_gpu_availability():
    """Check if NVIDIA GPU is available and Docker can access it."""
    print("Checking NVIDIA GPU availability...")

    # Check if nvidia-smi is available on the host
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            gpus = result.stdout.strip().split("\n")
            print(f"✓ Found {len(gpus)} NVIDIA GPU(s) on host:")
            for i, gpu in enumerate(gpus):
                print(f"  GPU {i}: {gpu}")
            return True
        else:
            print("⚠️  nvidia-smi found but no GPUs detected")
            return False
    except FileNotFoundError:
        print("⚠️  nvidia-smi not found. NVIDIA drivers may not be installed.")
        return False
    except subprocess.TimeoutExpired:
        print("⚠️  nvidia-smi command timed out")
        return False
    except Exception as e:
        print(f"⚠️  Error checking NVIDIA GPU: {e}")
        return False


def check_docker_nvidia_runtime():
    """Check if Docker has NVIDIA runtime configured."""
    print("Checking Docker NVIDIA runtime configuration...")

    try:
        # Check if nvidia-container-runtime is available
        result = subprocess.run(
            ["docker", "info", "--format", "{{.Runtimes}}"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            runtimes = result.stdout.strip()
            if "nvidia" in runtimes.lower():
                print("✓ Docker NVIDIA runtime is configured")
                return True
            else:
                print("⚠️  Docker NVIDIA runtime not found in available runtimes")
                print(f"   Available runtimes: {runtimes}")
                print("   You may need to install nvidia-container-toolkit")
                return False
        else:
            print("⚠️  Could not check Docker runtime configuration")
            return False
    except Exception as e:
        print(f"⚠️  Error checking Docker NVIDIA runtime: {e}")
        return False


def validate_gpu_profile(profile):
    """Validate GPU profile and check system requirements."""
    if profile in ["gpu-nvidia", "gpu-amd"]:
        print(f"\n=== Validating {profile} profile ===")

        if profile == "gpu-nvidia":
            gpu_available = check_nvidia_gpu_availability()
            runtime_available = check_docker_nvidia_runtime()

            if not gpu_available:
                print("\n❌ ERROR: NVIDIA GPU not detected on host system")
                print("   Please ensure:")
                print("   1. NVIDIA drivers are installed (check with: nvidia-smi)")
                print("   2. GPU is properly connected and powered")
                return False

            if not runtime_available:
                print("\n❌ ERROR: Docker NVIDIA runtime not configured")
                print("   Please install and configure nvidia-container-toolkit:")
                print(
                    "   https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
                )
                return False

            print("✓ NVIDIA GPU setup validated\n")
            return True

        elif profile == "gpu-amd":
            # Check for AMD GPU devices
            if os.path.exists("/dev/kfd") and os.path.exists("/dev/dri"):
                print("✓ AMD GPU devices found")
                return True
            else:
                print("⚠️  AMD GPU devices not found (/dev/kfd or /dev/dri)")
                print("   Continuing anyway, but GPU acceleration may not work")
                return True  # Don't fail, just warn

    return True


def generate_searxng_secret_key():
    """Generate a secret key for SearXNG based on the current platform."""
    print("Checking SearXNG settings...")

    # Define paths for SearXNG settings files (in 03-apps/searxng/config/)
    settings_path = os.path.join("03-apps", "searxng", "config", "settings.yml")
    settings_base_path = os.path.join("03-apps", "searxng", "config", "settings-base.yml")

    # Check if settings-base.yml exists
    if not os.path.exists(settings_base_path):
        print(f"Warning: SearXNG base settings file not found at {settings_base_path}")
        return

    # Check if settings.yml exists, if not create it from settings-base.yml
    if not os.path.exists(settings_path):
        print(f"SearXNG settings.yml not found. Creating from {settings_base_path}...")
        try:
            shutil.copyfile(settings_base_path, settings_path)
            # Ensure the file is writable by the current user
            os.chmod(settings_path, 0o644)
            print(f"Created {settings_path} from {settings_base_path}")
        except Exception as e:
            print(f"Error creating settings.yml: {e}")
            return
    else:
        print(f"SearXNG settings.yml already exists at {settings_path}")
        # Ensure existing file is writable
        try:
            os.chmod(settings_path, 0o644)
        except (OSError, PermissionError):
            # If we can't change permissions, continue anyway - write will fail with clear error
            pass

    print("Generating SearXNG secret key...")

    try:
        # Use Python's secrets module to generate a cryptographically secure random key
        # This avoids permission issues with sed's temporary files and works consistently
        # across all platforms (Windows, macOS, Linux)
        random_key = secrets.token_hex(32)

        # Read the settings file
        with open(settings_path) as f:
            content = f.read()

        # Check if the placeholder key still exists
        if "ultrasecretkey" not in content:
            print("Secret key already set, skipping...")
            return

        # Replace the placeholder with the generated key
        content = re.sub(r"ultrasecretkey", random_key, content)

        # Write the updated content back to the file
        # Use atomic write: write to a temporary file in the same directory, then rename
        # This ensures the file is either fully written or not changed at all
        temp_path = settings_path + ".tmp"
        try:
            with open(temp_path, "w") as f:
                f.write(content)
            # Atomic rename (works on Unix-like systems and Windows)
            os.replace(temp_path, settings_path)
        except (OSError, PermissionError):
            # If atomic write fails, try direct write as fallback
            if os.path.exists(temp_path):
                os.remove(temp_path)
            # Direct write (may be less safe but works if directory permissions allow)
            with open(settings_path, "w") as f:
                f.write(content)

        print("SearXNG secret key generated successfully.")

    except PermissionError as e:
        print(f"Permission denied when writing to {settings_path}: {e}")
        print("You may need to fix file permissions or run with appropriate privileges.")
        print(f"Try: sudo chown -R $USER:$USER {os.path.dirname(settings_path)}")
    except Exception as e:
        print(f"Error generating SearXNG secret key: {e}")
        print("You may need to manually generate the secret key.")
        print('Run: python3 -c "import secrets; print(secrets.token_hex(32))"')
        print(f"Then edit {settings_path} and replace 'ultrasecretkey' with the generated key.")


# Patterns for variables that should be synced from Infisical (secrets)
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

# Patterns for variables that should NOT be synced from Infisical
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
    except Exception:
        return False


def check_infisical_auth() -> bool:
    """Check if Infisical CLI is authenticated."""
    try:
        result = subprocess.run(
            ["infisical", "secrets"],
            capture_output=True,
            timeout=10,
            check=False,
        )
        # If authenticated, this should either succeed or show a project error
        # If not authenticated, it will show auth error
        output = (result.stdout or result.stderr or "").lower()
        return not ("authenticate" in output or "login" in output)
    except Exception:
        return False


def check_infisical_running() -> bool:
    """
    Check if Infisical containers are running.

    Returns:
        True if all required Infisical containers are running, False otherwise
    """
    required_containers = ["infisical-backend", "infisical-db", "infisical-redis"]
    running_containers = []
    missing_containers = []

    for container_name in required_containers:
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Status}}", container_name],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode == 0:
                status = result.stdout.strip()
                if status == "running":
                    running_containers.append(container_name)
                else:
                    missing_containers.append(f"{container_name} (status: {status})")
            else:
                missing_containers.append(f"{container_name} (not found)")
        except Exception as e:
            missing_containers.append(f"{container_name} (error: {e!s})")

    if len(running_containers) == len(required_containers):
        return True

    # Print detailed error message
    print("\n❌ Error: Infisical services are not running!")
    print(f"   Required containers: {', '.join(required_containers)}")
    if running_containers:
        print(f"   ✓ Running: {', '.join(running_containers)}")
    if missing_containers:
        print(f"   ✗ Missing/stopped: {', '.join(missing_containers)}")
    print("\n   To start Infisical services, run:")
    print("     python start_services.py --stack infisical")
    print("   Or use the dedicated script:")
    print("     python start_infisical.py")

    return False


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
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
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
        return {}

    return secrets_dict


def sync_infisical_to_env(env_path: str = ".env", quiet: bool = False) -> bool:
    """
    Sync secrets from Infisical directly to .env file.
    Preserves non-secret configuration like hostnames, ports, and URLs.

    Args:
        env_path: Path to .env file (default: ".env")
        quiet: If True, suppress output messages

    Returns:
        True if sync was successful or skipped, False on error
    """
    # Check if Infisical CLI is available
    if not check_infisical_cli():
        if not quiet:
            print("Infisical CLI not found - skipping secret sync")
        return True  # Not an error, just skip

    # Check if authenticated
    if not check_infisical_auth():
        if not quiet:
            print("Infisical CLI not authenticated - skipping secret sync")
            print("  To authenticate: infisical login")
        return True  # Not an error, just skip

    # Get secrets from Infisical
    infisical_secrets = get_infisical_secrets()
    if not infisical_secrets:
        if not quiet:
            print("No secrets found in Infisical - skipping sync")
        return True  # Not an error, just skip

    # Filter secrets (only sync secret keys, not config)
    secrets_to_sync = {}
    for key, value in infisical_secrets.items():
        if is_secret_key(key):
            secrets_to_sync[key] = value

    if not secrets_to_sync:
        if not quiet:
            print("No secrets to sync from Infisical")
        return True

    # Read existing .env file
    env_file_path = Path(env_path)
    if not env_file_path.exists():
        if not quiet:
            print(f"Warning: .env file not found at {env_path} - cannot sync")
        return False

    # Parse .env file
    env_vars = {}
    env_lines = []

    with open(env_file_path, encoding="utf-8") as f:
        for line in f:
            env_lines.append(line)
            stripped = line.strip()

            # Skip empty lines and comments
            if not stripped or stripped.startswith("#"):
                continue

            # Parse KEY=VALUE
            if "=" not in stripped:
                continue

            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()

            # Remove quotes if present
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]

            if key:
                env_vars[key] = value

    # Update .env file with Infisical secrets
    updated_count = 0
    added_count = 0
    processed_keys = set()
    new_lines = []

    for line in env_lines:
        stripped = line.strip()

        # Preserve comments and empty lines
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        # Process KEY=VALUE lines
        if "=" in stripped:
            key, value = stripped.split("=", 1)
            key = key.strip()
            processed_keys.add(key)

            # Update if this is a secret from Infisical
            if key in secrets_to_sync:
                new_lines.append(f"{key}={secrets_to_sync[key]}\n")
                updated_count += 1
                if not quiet:
                    print(f"  Updated {key} from Infisical")
            else:
                # Keep original line
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Add new secrets at the end
    for key, value in secrets_to_sync.items():
        if key not in processed_keys:
            new_lines.append(f"{key}={value}\n")
            added_count += 1
            if not quiet:
                print(f"  Added {key} from Infisical")

    # Write updated .env file
    try:
        with open(env_file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        if not quiet and (updated_count > 0 or added_count > 0):
            print(f"✓ Synced {updated_count + added_count} secret(s) from Infisical to .env")

        return True

    except Exception as e:
        print(f"Error: Failed to write .env file: {e}")
        return False


def check_and_fix_docker_compose_for_searxng():
    """Check and modify 03-apps/docker-compose.yml for SearXNG first run."""
    docker_compose_path = "03-apps/docker-compose.yml"
    if not os.path.exists(docker_compose_path):
        print(f"Warning: Docker Compose file not found at {docker_compose_path}")
        return

    try:
        # Read the docker-compose.yml file
        with open(docker_compose_path) as file:
            content = file.read()

        # Default to first run
        is_first_run = True

        # Check if Docker is running and if the SearXNG container exists
        try:
            # Check if the SearXNG container is running
            container_check = subprocess.run(
                ["docker", "ps", "--filter", "name=searxng", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                check=True,
            )
            searxng_containers = container_check.stdout.strip().split("\n")

            # If SearXNG container is running, check inside for uwsgi.ini
            if any(container for container in searxng_containers if container):
                container_name = next(container for container in searxng_containers if container)
                print(f"Found running SearXNG container: {container_name}")

                # Check if uwsgi.ini exists inside the container
                container_check = subprocess.run(
                    [
                        "docker",
                        "exec",
                        container_name,
                        "sh",
                        "-c",
                        "[ -f /etc/searxng/uwsgi.ini ] && echo 'found' || echo 'not_found'",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if "found" in container_check.stdout:
                    print("Found uwsgi.ini inside the SearXNG container - not first run")
                    is_first_run = False
                else:
                    print("uwsgi.ini not found inside the SearXNG container - first run")
                    is_first_run = True
            else:
                print("No running SearXNG container found - assuming first run")
        except Exception as e:
            print(f"Error checking Docker container: {e} - assuming first run")

        if is_first_run and "cap_drop: - ALL" in content:
            print(
                "First run detected for SearXNG. Temporarily removing 'cap_drop: - ALL' directive..."
            )
            # Temporarily comment out the cap_drop line
            modified_content = content.replace(
                "cap_drop: - ALL",
                "# cap_drop: - ALL  # Temporarily commented out for first run",
            )

            # Write the modified content back
            with open(docker_compose_path, "w") as file:
                file.write(modified_content)

            print(
                "Note: After the first run completes successfully, you should re-add 'cap_drop: - ALL' to 03-apps/docker-compose.yml for security reasons."
            )
        elif (
            not is_first_run
            and "# cap_drop: - ALL  # Temporarily commented out for first run" in content
        ):
            print(
                "SearXNG has been initialized. Re-enabling 'cap_drop: - ALL' directive for security..."
            )
            # Uncomment the cap_drop line
            modified_content = content.replace(
                "# cap_drop: - ALL  # Temporarily commented out for first run",
                "cap_drop: - ALL",
            )

            # Write the modified content back
            with open(docker_compose_path, "w") as file:
                file.write(modified_content)

    except Exception as e:
        print(f"Error checking/modifying 03-apps/docker-compose.yml for SearXNG: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Manage local AI and Supabase services.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_services.py --profile gpu-nvidia              # Start all services with NVIDIA GPU
  python start_services.py --action stop                     # Stop all services
  python start_services.py --stack apps                      # Start only apps stack
  python start_services.py --action stop --stack compute     # Stop compute stack
        """,
    )
    parser.add_argument(
        "--action",
        choices=["start", "stop"],
        default="start",
        help="Action to perform: start or stop services (default: start)",
    )
    parser.add_argument(
        "--stack",
        choices=["all", "infrastructure", "infisical", "data", "compute", "apps", "lambda"],
        default="all",
        help="Target stack to operate on (default: all)",
    )
    parser.add_argument(
        "--profile",
        choices=["cpu", "gpu-nvidia", "gpu-amd", "none", "nvidia"],  # Allow "nvidia" as alias
        default="gpu-nvidia",
        help="Profile to use for Docker Compose. Use 'gpu-nvidia' for NVIDIA GPUs, 'cpu' for CPU-only (default: gpu-nvidia)",
    )
    parser.add_argument(
        "--environment",
        choices=["private", "public"],
        default="private",
        help="Environment to use for Docker Compose (default: private)",
    )
    parser.add_argument(
        "--skip-dhi-auth",
        action="store_true",
        help="Skip dhi.io registry authentication",
    )
    args = parser.parse_args()

    # Normalize profile name (handle "nvidia" as alias for "gpu-nvidia")
    if args.profile == "nvidia":
        print("Note: 'nvidia' profile is an alias for 'gpu-nvidia'")
        args.profile = "gpu-nvidia"

    # Stop logic is simpler - just stop services
    if args.action == "stop":
        manage_services(action="stop", stack=args.stack, environment=args.environment)
        return

    # Start logic (includes pre-flight checks)
    clone_supabase_repo()

    # Generate SearXNG secret key and check docker-compose.yml
    generate_searxng_secret_key()
    check_and_fix_docker_compose_for_searxng()

    # Validate GPU profile before proceeding
    if not validate_gpu_profile(args.profile):
        print("\n❌ GPU profile validation failed. Exiting.")
        print("\nTo use CPU-only mode, run:")
        print("  python start_services.py --profile cpu")
        sys.exit(1)

    # Authenticate to dhi.io registry before pulling images
    authenticate_dhi_registry(skip_auth=args.skip_dhi_auth)

    # Pull latest Docker images before starting services
    pull_docker_images(args.profile, args.environment, args.stack)

    # Check if Infisical is running and start it if needed
    # Infrastructure can start without Infisical, but other stacks require it
    if args.stack not in ["infisical", "infrastructure"]:
        print("\n=== Checking Infisical services ===")
        if not check_infisical_running():
            print("\n⚠️  Infisical services are not running. Starting them now...")
            if not manage_infisical_stack(action="start", environment=args.environment):
                print("\n❌ Failed to start Infisical services. Cannot proceed.")
                sys.exit(1)
            # Wait a bit for services to start
            time.sleep(5)
            if not check_infisical_running():
                print("\n❌ Infisical services did not start successfully. Cannot proceed.")
                sys.exit(1)
            print("✓ Infisical services started and running")
        else:
            print("✓ Infisical services are running")
    elif args.stack == "all":
        # When starting all stacks, check Infisical and start if not running
        print("\n=== Checking Infisical services ===")
        if not check_infisical_running():
            print("⚠ Warning: Infisical services are not running.")
            print("   Starting Infisical services now...")
            if not manage_infisical_stack(action="start", environment=args.environment):
                print("⚠ Warning: Failed to start Infisical services. Continuing anyway...")
            else:
                # Wait a bit for services to start
                time.sleep(5)
                if check_infisical_running():
                    print("✓ Infisical services started successfully")
        else:
            print("✓ Infisical services are running")

    # Sync Infisical secrets directly to .env (two-way sync)
    print("\n=== Syncing Infisical secrets to .env ===")
    sync_infisical_to_env(quiet=False)

    # Start services using modular compose files
    success = manage_services(
        action="start", stack=args.stack, profile=args.profile, environment=args.environment
    )

    if not success:
        print("Error: Failed to start services. Check the error messages above.")
        sys.exit(1)

    print(f"Action '{args.action}' on stack '{args.stack}' completed successfully!")


if __name__ == "__main__":
    main()
