#!/usr/bin/env python3
"""
start_services.py

This script starts the Supabase stack first, waits for it to initialize, and then starts
the local AI stack. Both stacks use the same Docker Compose project name ("localai")
so they appear together in Docker Desktop.
"""

import os
import subprocess
import shutil
import time
import argparse
import platform
import sys
import json
import base64


def run_command(cmd, cwd=None):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def load_env_file(env_path=".env"):
    """Load environment variables from .env file."""
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
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
        with open(docker_config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            auths = config.get("auths", {})
            # Check if dhi.io is in the auths
            return "dhi.io" in auths or "https://dhi.io" in auths
    except (json.JSONDecodeError, KeyError, IOError):
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
    password = env_vars.get("DOCKER_HUB_PASSWORD") or env_vars.get("DOCKER_HUB_TOKEN") or os.environ.get("DOCKER_HUB_PASSWORD") or os.environ.get("DOCKER_HUB_TOKEN")
    
    if not username:
        print("Warning: DOCKER_HUB_USERNAME not found in .env file or environment variables.")
        print("Skipping dhi.io authentication. You may need to manually run: docker login dhi.io")
        print("Or set DOCKER_HUB_USERNAME and DOCKER_HUB_PASSWORD/DOCKER_HUB_TOKEN in your .env file.")
        return False
    
    if not password:
        print("Warning: DOCKER_HUB_PASSWORD or DOCKER_HUB_TOKEN not found in .env file or environment variables.")
        print("Skipping dhi.io authentication. You may need to manually run: docker login dhi.io")
        print("Or set DOCKER_HUB_PASSWORD/DOCKER_HUB_TOKEN in your .env file.")
        print("For better security, use a Personal Access Token (PAT) instead of password.")
        print("Create a PAT at: https://hub.docker.com/settings/security")
        return False
    
    # Perform non-interactive login
    print("Authenticating to dhi.io registry...")
    try:
        # Use subprocess with stdin to securely pass password
        cmd = [
            "docker", "login", "dhi.io",
            "--username", username,
            "--password-stdin"
        ]
        
        # Pass password via stdin to avoid shell history and command line exposure
        result = subprocess.run(
            cmd,
            input=password,
            capture_output=True,
            text=True,
            check=False
        )
        
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
        print("Error: Docker command not found. Please ensure Docker is installed and in your PATH.")
        return False
    except Exception as e:
        print(f"Error during dhi.io authentication: {e}")
        print("You may need to manually run: docker login dhi.io")
        return False


def clone_supabase_repo():
    """Clone the Supabase repository using sparse checkout if not already present."""
    if not os.path.exists("supabase"):
        print("Cloning the Supabase repository...")
        run_command(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                "https://github.com/supabase/supabase.git",
            ]
        )
        os.chdir("supabase")
        run_command(["git", "sparse-checkout", "init", "--cone"])
        run_command(["git", "sparse-checkout", "set", "docker"])
        run_command(["git", "checkout", "master"])
        os.chdir("..")
    else:
        print("Supabase repository already exists, updating...")
        os.chdir("supabase")
        run_command(["git", "pull"])
        os.chdir("..")


def prepare_supabase_env():
    """Copy .env to .env in supabase/docker."""
    env_path = os.path.join("supabase", "docker", ".env")
    env_example_path = os.path.join(".env")
    print("Copying .env in root to .env in supabase/docker...")
    shutil.copyfile(env_example_path, env_path)


def stop_existing_containers(profile=None):
    print(
        "Stopping and removing existing containers for the unified project 'localai'..."
    )
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml", "down"])
    run_command(cmd)


def pull_docker_images(profile=None, environment=None):
    """Pull latest versions of all Docker images before starting services."""
    print("Pulling latest Docker images for all services...")

    # Pull Supabase images
    print("Pulling Supabase images...")
    cmd = [
        "docker",
        "compose",
        "-p",
        "localai",
        "-f",
        "supabase/docker/docker-compose.yml",
    ]
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.supabase.yml"])
    cmd.extend(["pull"])
    try:
        run_command(cmd)
    except subprocess.CalledProcessError:
        print("Warning: Some Supabase images may not have been updated.")

    # Pull local AI images
    print("Pulling local AI service images...")
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml"])
    if environment and environment == "private":
        cmd.extend(["-f", "docker-compose.override.private.yml"])
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.yml"])
    cmd.extend(["pull"])
    try:
        run_command(cmd)
    except subprocess.CalledProcessError:
        print("Warning: Some local AI images may not have been updated.")

    print("Image pull complete!")


def start_infisical(environment=None):
    """Start the Infisical service."""
    print("Starting Infisical service...")
    cmd = ["docker", "compose", "-p", "localai", "-f", "docker-compose.yml"]
    if environment and environment == "private":
        cmd.extend(["-f", "docker-compose.override.private.yml"])
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.yml"])
    cmd.extend(["up", "-d", "infisical"])
    run_command(cmd)


def wait_for_infisical(max_retries=30, retry_interval=2):
    """Wait for Infisical to become ready by checking its health endpoint."""
    print("Waiting for Infisical to become ready...")

    for i in range(max_retries):
        try:
            # Try to check health endpoint via docker exec using wget
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    "infisical",
                    "wget",
                    "--no-verbose",
                    "--tries=1",
                    "--spider",
                    "http://localhost:8080/api/health",
                ],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                print("Infisical is ready!")
                return True
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            pass
        except Exception as e:
            print(f"Error checking Infisical health: {e}")

        if i < max_retries - 1:
            print(
                f"Infisical not ready yet, waiting {retry_interval}s... ({i+1}/{max_retries})"
            )
            time.sleep(retry_interval)

    print("Warning: Infisical did not become ready within the expected time.")
    print("You may need to check the Infisical container logs manually.")
    return False


def start_supabase(environment=None):
    """Start the Supabase services (using its compose file)."""
    print("Starting Supabase services...")
    cmd = [
        "docker",
        "compose",
        "-p",
        "localai",
        "-f",
        "supabase/docker/docker-compose.yml",
    ]
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.supabase.yml"])
    cmd.extend(["up", "-d"])
    run_command(cmd)


def export_infisical_secrets(env_file_path=".env.infisical"):
    """Export secrets from Infisical to a temporary .env file."""
    print("Exporting secrets from Infisical...")

    # Check if Infisical CLI is available
    try:
        result = subprocess.run(
            ["infisical", "--version"], capture_output=True, timeout=5, check=False
        )
        if result.returncode != 0:
            print("Warning: Infisical CLI not found or not working.")
            print("Skipping Infisical secret export. Services will use .env file only.")
            return None
    except FileNotFoundError:
        print("Warning: Infisical CLI not installed.")
        print("Install it from: https://infisical.com/docs/cli/overview")
        print("Skipping Infisical secret export. Services will use .env file only.")
        return None
    except Exception as e:
        print(f"Warning: Error checking Infisical CLI: {e}")
        print("Skipping Infisical secret export. Services will use .env file only.")
        return None

    # Try to export secrets
    try:
        cmd = [
            "infisical",
            "export",
            "--format=dotenv",
            f"--output-file={env_file_path}",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            if os.path.exists(env_file_path) and os.path.getsize(env_file_path) > 0:
                print(f"Successfully exported Infisical secrets to {env_file_path}")
                return env_file_path
            else:
                print(
                    "Warning: Infisical export completed but file is empty or missing."
                )
                print(
                    "Make sure you're authenticated and have secrets configured in Infisical."
                )
                return None
        else:
            print(f"Warning: Infisical export failed: {result.stderr}")
            print("You may need to authenticate first: infisical login")
            print("Skipping Infisical secret export. Services will use .env file only.")
            return None
    except Exception as e:
        print(f"Warning: Error exporting Infisical secrets: {e}")
        print("Skipping Infisical secret export. Services will use .env file only.")
        return None


def start_local_ai(profile=None, environment=None, use_infisical=False):
    """Start the local AI services (using its compose file)."""
    print("Starting local AI services...")
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml"])
    if environment and environment == "private":
        cmd.extend(["-f", "docker-compose.override.private.yml"])
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.yml"])

    # If using Infisical, try to export secrets and use them
    if use_infisical:
        infisical_env_file = export_infisical_secrets()
        if infisical_env_file:
            cmd.extend(["--env-file", infisical_env_file])
            print(f"Using Infisical secrets from {infisical_env_file}")
        else:
            print("Falling back to .env file for secrets")

    cmd.extend(["up", "-d"])
    run_command(cmd)


def generate_searxng_secret_key():
    """Generate a secret key for SearXNG based on the current platform."""
    print("Checking SearXNG settings...")

    # Define paths for SearXNG settings files
    settings_path = os.path.join("searxng", "settings.yml")
    settings_base_path = os.path.join("searxng", "settings-base.yml")

    # Check if settings-base.yml exists
    if not os.path.exists(settings_base_path):
        print(f"Warning: SearXNG base settings file not found at {settings_base_path}")
        return

    # Check if settings.yml exists, if not create it from settings-base.yml
    if not os.path.exists(settings_path):
        print(f"SearXNG settings.yml not found. Creating from {settings_base_path}...")
        try:
            shutil.copyfile(settings_base_path, settings_path)
            print(f"Created {settings_path} from {settings_base_path}")
        except Exception as e:
            print(f"Error creating settings.yml: {e}")
            return
    else:
        print(f"SearXNG settings.yml already exists at {settings_path}")

    print("Generating SearXNG secret key...")

    # Detect the platform and run the appropriate command
    system = platform.system()

    try:
        if system == "Windows":
            print(
                "Detected Windows platform, using PowerShell to generate secret key..."
            )
            # PowerShell command to generate a random key and replace in the settings file
            ps_command = [
                "powershell",
                "-Command",
                "$randomBytes = New-Object byte[] 32; "
                + "(New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($randomBytes); "
                + '$secretKey = -join ($randomBytes | ForEach-Object { "{0:x2}" -f $_ }); '
                + "(Get-Content searxng/settings.yml) -replace 'ultrasecretkey', $secretKey | Set-Content searxng/settings.yml",
            ]
            subprocess.run(ps_command, check=True)

        elif system == "Darwin":  # macOS
            print(
                "Detected macOS platform, using sed command with empty string parameter..."
            )
            # macOS sed command requires an empty string for the -i parameter
            openssl_cmd = ["openssl", "rand", "-hex", "32"]
            random_key = subprocess.check_output(openssl_cmd).decode("utf-8").strip()
            sed_cmd = [
                "sed",
                "-i",
                "",
                f"s|ultrasecretkey|{random_key}|g",
                settings_path,
            ]
            subprocess.run(sed_cmd, check=True)

        else:  # Linux and other Unix-like systems
            print("Detected Linux/Unix platform, using standard sed command...")
            # Standard sed command for Linux
            openssl_cmd = ["openssl", "rand", "-hex", "32"]
            random_key = subprocess.check_output(openssl_cmd).decode("utf-8").strip()
            sed_cmd = ["sed", "-i", f"s|ultrasecretkey|{random_key}|g", settings_path]
            subprocess.run(sed_cmd, check=True)

        print("SearXNG secret key generated successfully.")

    except Exception as e:
        print(f"Error generating SearXNG secret key: {e}")
        print("You may need to manually generate the secret key using the commands:")
        print(
            '  - Linux: sed -i "s|ultrasecretkey|$(openssl rand -hex 32)|g" searxng/settings.yml'
        )
        print(
            "  - macOS: sed -i '' \"s|ultrasecretkey|$(openssl rand -hex 32)|g\" searxng/settings.yml"
        )
        print("  - Windows (PowerShell):")
        print("    $randomBytes = New-Object byte[] 32")
        print(
            "    (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($randomBytes)"
        )
        print(
            '    $secretKey = -join ($randomBytes | ForEach-Object { "{0:x2}" -f $_ })'
        )
        print(
            "    (Get-Content searxng/settings.yml) -replace 'ultrasecretkey', $secretKey | Set-Content searxng/settings.yml"
        )


def check_and_fix_docker_compose_for_searxng():
    """Check and modify docker-compose.yml for SearXNG first run."""
    docker_compose_path = "docker-compose.yml"
    if not os.path.exists(docker_compose_path):
        print(f"Warning: Docker Compose file not found at {docker_compose_path}")
        return

    try:
        # Read the docker-compose.yml file
        with open(docker_compose_path, "r") as file:
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
                container_name = next(
                    container for container in searxng_containers if container
                )
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
                    print(
                        "Found uwsgi.ini inside the SearXNG container - not first run"
                    )
                    is_first_run = False
                else:
                    print(
                        "uwsgi.ini not found inside the SearXNG container - first run"
                    )
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
                "Note: After the first run completes successfully, you should re-add 'cap_drop: - ALL' to docker-compose.yml for security reasons."
            )
        elif (
            not is_first_run
            and "# cap_drop: - ALL  # Temporarily commented out for first run"
            in content
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
        print(f"Error checking/modifying docker-compose.yml for SearXNG: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Start the local AI and Supabase services."
    )
    parser.add_argument(
        "--profile",
        choices=["cpu", "gpu-nvidia", "gpu-amd", "none"],
        default="cpu",
        help="Profile to use for Docker Compose (default: cpu)",
    )
    parser.add_argument(
        "--environment",
        choices=["private", "public"],
        default="private",
        help="Environment to use for Docker Compose (default: private)",
    )
    parser.add_argument(
        "--use-infisical",
        action="store_true",
        default=True,
        help="Use Infisical for secret management (default: True)",
    )
    parser.add_argument(
        "--skip-infisical",
        action="store_true",
        help="Skip Infisical startup and use .env files directly",
    )
    parser.add_argument(
        "--skip-dhi-auth",
        action="store_true",
        help="Skip dhi.io registry authentication",
    )
    args = parser.parse_args()

    # If skip-infisical is set, disable use-infisical
    if args.skip_infisical:
        args.use_infisical = False

    clone_supabase_repo()
    prepare_supabase_env()

    # Generate SearXNG secret key and check docker-compose.yml
    generate_searxng_secret_key()
    check_and_fix_docker_compose_for_searxng()

    # Authenticate to dhi.io registry before pulling images
    authenticate_dhi_registry(skip_auth=args.skip_dhi_auth)

    stop_existing_containers(args.profile)

    # Pull latest Docker images before starting services
    pull_docker_images(args.profile, args.environment)

    # Start Infisical first (if enabled) - it needs postgres and redis
    if args.use_infisical:
        print("Infisical integration enabled.")
        # Note: Infisical depends on postgres and redis, which are started with Supabase
        # So we start Supabase first, then Infisical, then wait for it
        start_supabase(args.environment)

        # Give postgres and redis time to be ready
        print("Waiting for postgres and redis to be ready...")
        time.sleep(10)

        # Start Infisical
        start_infisical(args.environment)

        # Wait for Infisical to be ready
        wait_for_infisical()
    else:
        print("Infisical integration disabled. Using .env files directly.")
        # Start Supabase first
        start_supabase(args.environment)

        # Give Supabase some time to initialize
        print("Waiting for Supabase to initialize...")
        time.sleep(10)

    # Then start the local AI services
    start_local_ai(args.profile, args.environment, args.use_infisical)


if __name__ == "__main__":
    main()
