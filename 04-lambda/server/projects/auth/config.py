"""Configuration for auth project."""

from server.config import settings as global_settings


class AuthConfig:
    """Auth project-specific configuration."""
    
    # Cloudflare Access
    cloudflare_auth_domain: str = global_settings.cloudflare_auth_domain
    cloudflare_aud_tag: str = global_settings.cloudflare_aud_tag
    
    # Supabase
    supabase_db_url: str = global_settings.supabase_db_url
    supabase_service_key: str = global_settings.supabase_service_key
    
    # Neo4j (from global)
    neo4j_uri: str = global_settings.neo4j_uri
    neo4j_user: str = global_settings.neo4j_user
    neo4j_password: str = global_settings.neo4j_password
    neo4j_database: str = global_settings.neo4j_database
    
    # MinIO
    minio_endpoint: str = global_settings.minio_endpoint
    minio_access_key: str = global_settings.minio_access_key
    minio_secret_key: str = global_settings.minio_secret_key


config = AuthConfig()
