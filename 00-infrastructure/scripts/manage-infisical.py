#!/usr/bin/env python3
"""
manage-infisical.py

Unified tool for managing Infisical state.
Supports:
1. Infrastructure Reset (Nuclear): Wipes containers and volumes.
2. Data Reset (Surgical): Wipes database tables, optionally preserving users.

Usage:
  python3 manage-infisical.py [command] [options]

Commands:
  reset-infra   Perform a nuclear reset of the infrastructure (delete volumes).
  reset-data    Selectively reset organization data in the database.
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
import time

# --- Shared Utilities ---

def run_command(cmd, check=True, capture_output=False):
    """Run a shell command."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        text=True,
        check=False,
        capture_output=capture_output
    )
    if result.returncode != 0 and check:
        print(f"Error running command: {' '.join(cmd)}")
        if result.stderr:
            print(f"Stderr: {result.stderr}")
        sys.exit(result.returncode)
    return result

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

def check_container_running(container_name):
    """Check if a Docker container is running."""
    result = run_command(
        ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
        check=False,
        capture_output=True
    )
    return container_name in result.stdout

# --- Infrastructure Reset Logic ---

def reset_infrastructure(args):
    print("⚠️  WARNING: This will DELETE ALL DATA in Infisical (Users, Secrets, Org Settings).")
    print("   It will stop the infrastructure stack and wipe the database volumes.")
    
    if not args.yes:
        response = input("Are you sure you want to proceed? (y/N): ")
        if response.lower() != 'y':
            print("Operation cancelled.")
            return

    print("\n1. Stopping Infisical services...")
    # Try stopping via compose first to be polite
    # Assuming we are in 00-infrastructure/scripts/, repo root is ../../../
    repo_root = Path(__file__).resolve().parent.parent.parent
    os.chdir(repo_root)

    run_command(["docker", "compose", "-p", "localai", "-f", "00-infrastructure/docker-compose.yml", "stop", "infisical-backend", "infisical-db", "infisical-redis"], check=False)
    
    # Force remove containers to ensure they release the volumes
    containers_to_remove = ["infisical-backend", "infisical-db", "infisical-redis"]
    print(f"   Force removing containers: {', '.join(containers_to_remove)}...")
    run_command(["docker", "rm", "-f"] + containers_to_remove, check=False)

    print("\n2. Removing Infisical volumes...")
    volumes_to_check = [
        "localai_infisical-pg-data",
        "localai_infisical-redis-data",
        "00-infrastructure_infisical-pg-data",
        "00-infrastructure_infisical-redis-data",
        "infisical-pg-data",
        "infisical-redis-data",
        "infisical_pg_data",
        "infisical_redis_data"
    ]
    
    for vol in volumes_to_check:
        run_command(["docker", "volume", "rm", vol], check=False)

    print("\n3. Restarting Infrastructure Stack...")
    start_script = repo_root / "start_services.py"
    
    if start_script.exists():
        run_command([sys.executable, str(start_script), "--stack", "infrastructure"])
    else:
        print(f"❌ Could not find start_services.py at {start_script}")
        print("   Please restart the infrastructure manually.")

    print("\n✅ Infisical infrastructure reset complete.")
    print("   Navigate to the Infisical URL to create a new admin account.")

# --- Data Reset Logic ---

def execute_sql_command(sql, db_user, db_name, capture_output=True):
    """Execute a SQL command in the Infisical database container."""
    psql_flags = ["-t", "-A"] if capture_output else []
    
    cmd = [
        "docker", "exec", "-i", "infisical-db",
        "psql", "-U", db_user, "-d", db_name
    ] + psql_flags
    
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate(input=sql)
    
    if process.returncode != 0:
        if stderr and not stderr.strip().startswith("NOTICE:"):
            print(f"SQL Error: {stderr}")
        return None
    return stdout.strip() if capture_output else True

def get_all_tables(db_user, db_name):
    sql = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name;"
    result = execute_sql_command(sql, db_user, db_name)
    return [line.strip() for line in result.split('\n') if line.strip()] if result else []

def identify_organization_tables(tables, include_users=False):
    org_tables = []
    user_tables = []
    patterns = [
        'organization', 'project', 'membership', 'secret', 'environment',
        'folder', 'key', 'token', 'integration', 'webhook', 'audit',
        'invite', 'access', 'permission', 'role', 'workspace'
    ]
    user_patterns = ['user', 'identity', 'membership']
    
    for table in tables:
        table_lower = table.lower()
        if any(pattern in table_lower for pattern in user_patterns):
            if not include_users and (table_lower == 'users' or table_lower == 'user'):
                continue
            user_tables.append(table)
        if any(pattern in table_lower for pattern in patterns):
            if not include_users and (table_lower == 'users' or table_lower == 'user'):
                continue
            org_tables.append(table)
    
    if include_users:
        all_tables = sorted(set(user_tables + org_tables))
        if 'users' in all_tables:
            all_tables.remove('users')
            all_tables.append('users')
        return all_tables
    return sorted(org_tables)

def get_table_row_count(table, db_user, db_name):
    sql = f"SELECT COUNT(*) FROM \"{table}\";"
    result = execute_sql_command(sql, db_user, db_name)
    try:
        return int(result.strip()) if result else 0
    except ValueError:
        return 0

def delete_table_data(table, db_user, db_name, dry_run=False):
    if dry_run:
        count = get_table_row_count(table, db_user, db_name)
        print(f"  [DRY RUN] Would delete {count} rows from {table}")
        return True
    
    sql = f'TRUNCATE TABLE "{table}" CASCADE;'
    result = execute_sql_command(sql, db_user, db_name, capture_output=False)
    if result is None:
        sql = f'DELETE FROM "{table}"'
        result = execute_sql_command(sql, db_user, db_name, capture_output=False)
    return result is not None

def create_database_backup(db_user, db_name, db_password, backup_path):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"infisical_backup_{timestamp}.dump"
    container_backup_path = f"/tmp/{backup_file}"
    print(f"\nCreating database backup...")
    
    env = os.environ.copy()
    env['PGPASSWORD'] = db_password
    
    cmd = [
        "docker", "exec", "-e", f"PGPASSWORD={db_password}",
        "infisical-db", "pg_dump", "-U", db_user, "-d", db_name, "-F", "c", "-f", container_backup_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        local_backup_path = backup_path / backup_file
        copy_cmd = ["docker", "cp", f"infisical-db:{container_backup_path}", str(local_backup_path)]
        if run_command(copy_cmd, check=False).returncode == 0:
            run_command(["docker", "exec", "infisical-db", "rm", container_backup_path], check=False)
            print(f"✅ Backup created: {local_backup_path}")
            return True
    print(f"❌ Backup failed: {result.stderr}")
    return False

def flush_redis_cache(dry_run=False):
    if dry_run:
        print("  [DRY RUN] Would flush Redis cache")
        return True
    print("\nFlushing Redis cache...")
    if run_command(["docker", "exec", "infisical-redis", "redis-cli", "FLUSHALL"], check=False).returncode == 0:
        print("✅ Redis cache flushed")
        return True
    return False

def reset_data(args):
    repo_root = Path(__file__).resolve().parent.parent.parent
    os.chdir(repo_root)
    env_vars = load_env_file(".env")
    
    db_user = env_vars.get("INFISICAL_POSTGRES_USER", "postgres")
    db_password = env_vars.get("INFISICAL_POSTGRES_PASSWORD", "")
    db_name = env_vars.get("INFISICAL_POSTGRES_DB", "postgres")
    
    if not db_password:
        print("❌ INFISICAL_POSTGRES_PASSWORD not found in .env file")
        sys.exit(1)
    
    if not check_container_running("infisical-db"):
        print("❌ infisical-db container is not running. Start infrastructure first.")
        sys.exit(1)

    print("=" * 70)
    print("  Infisical Organization Data Reset")
    print("=" * 70)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE")
    
    print("⚠️  WARNING: This will DELETE all organization-related data (Projects, Secrets, etc).")
    if args.include_users:
        print("⚠️  WARNING: User accounts will also be DELETED.")
    else:
        print("✅ User accounts will be PRESERVED.")

    if not args.yes and not args.dry_run:
        response = input("Are you sure you want to proceed? (y/N): ")
        if response.lower() != 'y':
            return

    if args.backup and not args.dry_run:
        backup_dir = repo_root / "backups"
        backup_dir.mkdir(exist_ok=True)
        create_database_backup(db_user, db_name, db_password, backup_dir)

    print("\n1. Discovering schema...")
    all_tables = get_all_tables(db_user, db_name)
    org_tables = identify_organization_tables(all_tables, include_users=args.include_users)
    
    if not org_tables:
        print("⚠️  No organization-related tables found.")
        return

    print(f"   Identified {len(org_tables)} tables.")
    
    if args.dry_run:
        for table in org_tables:
            delete_table_data(table, db_user, db_name, dry_run=True)
        flush_redis_cache(dry_run=True)
        return

    print("\n2. Deleting data...")
    success_count = 0
    for table in org_tables:
        if delete_table_data(table, db_user, db_name):
            print(f"   ✅ Cleared {table}")
            success_count += 1
        else:
            print(f"   ❌ Failed to clear {table}")
    
    if check_container_running("infisical-redis"):
        flush_redis_cache()
    
    print(f"\n✅ Reset complete! Cleared {success_count}/{len(org_tables)} tables.")

# --- Main CLI ---

def main():
    parser = argparse.ArgumentParser(description="Manage Infisical state and data.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: reset-infra
    parser_infra = subparsers.add_parser("reset-infra", help="Nuclear reset of infrastructure (deletes volumes).")
    parser_infra.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    parser_infra.set_defaults(func=reset_infrastructure)

    # Subcommand: reset-data
    parser_data = subparsers.add_parser("reset-data", help="Surgical reset of organization data (preserves users by default).")
    parser_data.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    parser_data.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    parser_data.add_argument("--backup", action="store_true", help="Create DB backup before deletion")
    parser_data.add_argument("--include-users", action="store_true", help="Also delete user accounts")
    parser_data.set_defaults(func=reset_data)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
