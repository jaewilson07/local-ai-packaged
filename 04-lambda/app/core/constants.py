"""Shared constants used across the application."""

from enum import Enum


class DatabaseDefaults:
    """Default database configuration values."""

    MONGODB_DATABASE = "rag_db"
    MONGODB_COLLECTION = "documents"
    NEO4J_DATABASE = "neo4j"
    SUPABASE_TABLE = "documents"
    
    # Connection timeouts
    MONGODB_TIMEOUT_MS = 5000
    NEO4J_TIMEOUT_S = 5
    SUPABASE_TIMEOUT_S = 10
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY_S = 1


class CrawlingDefaults:
    """Default web crawling configuration."""

    # Request configuration
    USER_AGENT = "Mozilla/5.0 (compatible; LocalAI/1.0)"
    REQUEST_TIMEOUT_S = 30
    MAX_REDIRECTS = 5
    
    # Content extraction
    MIN_CONTENT_LENGTH = 100
    MAX_CONTENT_LENGTH = 1_000_000
    
    # Rate limiting
    RATE_LIMIT_DELAY_MS = 1000
    MAX_CONCURRENT_REQUESTS = 5
    
    # Crawling behavior
    MAX_DEPTH = 3
    MAX_PAGES = 100
    RESPECT_ROBOTS_TXT = True
    
    # Content filtering
    EXCLUDED_EXTENSIONS = [".pdf", ".zip", ".exe", ".dmg", ".pkg"]
    EXCLUDED_MIME_TYPES = ["application/pdf", "application/zip", "video/*"]


class EmbeddingDefaults:
    """Default embedding configuration."""

    MODEL = "qwen3-embedding:4b"
    DIMENSION = 2560
    PROVIDER = "ollama"
    BASE_URL = "http://ollama:11434/v1"
    
    # Processing configuration
    BATCH_SIZE = 32
    MAX_TEXT_LENGTH = 8192


class LLMDefaults:
    """Default LLM configuration."""

    PROVIDER = "ollama"
    MODEL = "llama3.2"
    BASE_URL = "http://ollama:11434/v1"
    
    # Generation parameters
    TEMPERATURE = 0.7
    MAX_TOKENS = 2048
    TOP_P = 0.9
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY_S = 1


class ChunkingDefaults:
    """Default text chunking configuration."""

    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    SEPARATOR = "\n\n"
    
    # Semantic chunking
    MIN_CHUNK_SIZE = 100
    MAX_CHUNK_SIZE = 2000


class CacheDefaults:
    """Default caching configuration."""

    TTL_SHORT_S = 300  # 5 minutes
    TTL_MEDIUM_S = 3600  # 1 hour
    TTL_LONG_S = 86400  # 24 hours
    
    # Key prefixes
    PREFIX_USER = "user:"
    PREFIX_SESSION = "session:"
    PREFIX_EMBEDDING = "embedding:"
    PREFIX_LLM = "llm:"


class StorageDefaults:
    """Default storage configuration."""

    # File size limits
    MAX_FILE_SIZE_MB = 100
    MAX_IMAGE_SIZE_MB = 10
    
    # Allowed file types
    ALLOWED_DOCUMENTS = [".txt", ".md", ".pdf", ".docx", ".html"]
    ALLOWED_IMAGES = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    ALLOWED_MEDIA = [".mp3", ".mp4", ".wav", ".mov"]
    
    # Storage paths
    UPLOAD_DIR = "uploads"
    TEMP_DIR = "temp"
    CACHE_DIR = "cache"


class HTTPStatus(int, Enum):
    """Common HTTP status codes."""

    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    
    INTERNAL_SERVER_ERROR = 500
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
