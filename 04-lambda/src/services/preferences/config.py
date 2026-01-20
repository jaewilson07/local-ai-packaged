"""Configuration constants for the preferences system."""

from enum import Enum


class PreferenceCategories(str, Enum):
    """Available preference categories."""

    GOOGLE_DRIVE = "google_drive"
    LLM = "llm"
    EMBEDDINGS = "embeddings"
    UI = "ui"
    CRAWL = "crawl"
    RAG = "rag"
    WORKFLOWS = "workflows"
    NOTIFICATIONS = "notifications"
    IMMICH = "immich"
    DISCORD = "discord"


class PreferenceKeys:
    """Strongly-typed preference key constants."""

    # Google Drive
    GOOGLE_DRIVE_DEFAULT_FOLDER_ID = "google_drive.default_folder_id"
    GOOGLE_DRIVE_SEARCH_SCOPE = "google_drive.search_scope"
    GOOGLE_DRIVE_PAGE_SIZE = "google_drive.page_size"

    # LLM
    LLM_DEFAULT_MODEL = "llm.default_model"
    LLM_TEMPERATURE = "llm.temperature"
    LLM_MAX_TOKENS = "llm.max_tokens"
    LLM_PROVIDER = "llm.provider"

    # Embeddings
    EMBEDDINGS_MODEL = "embeddings.model"
    EMBEDDINGS_PROVIDER = "embeddings.provider"

    # UI
    UI_THEME = "ui.theme"
    UI_ITEMS_PER_PAGE = "ui.items_per_page"
    UI_DEFAULT_VIEW = "ui.default_view"

    # Crawl
    CRAWL_MAX_DEPTH = "crawl.max_depth"
    CRAWL_MAX_PAGES = "crawl.max_pages"
    CRAWL_TIMEOUT = "crawl.timeout"

    # RAG
    RAG_SEARCH_MODE = "rag.search_mode"
    RAG_TOP_K = "rag.top_k"
    RAG_USE_RERANK = "rag.use_rerank"

    # Workflows
    WORKFLOWS_AUTO_SAVE = "workflows.auto_save"

    # Notifications
    NOTIFICATIONS_EMAIL_ENABLED = "notifications.email_enabled"
    NOTIFICATIONS_DISCORD_ENABLED = "notifications.discord_enabled"

    # Immich
    IMMICH_AUTO_BACKUP = "immich.auto_backup"
    IMMICH_BACKUP_FOLDER = "immich.backup_folder"

    # Discord (see discord_service.py for full Discord preference keys)
    DISCORD_ENABLED_CAPABILITIES = "discord.enabled_capabilities"
    DISCORD_CHAT_MODE = "discord.chat_mode"
    DISCORD_PERSONALITY_ID = "discord.personality_id"
    DISCORD_RAG_COLLECTION = "discord.rag_collection"
    DISCORD_NOTIFICATIONS_ENABLED = "discord.notifications_enabled"


# System-wide fallback defaults (used when DB is unavailable)
FALLBACK_DEFAULTS = {
    PreferenceKeys.GOOGLE_DRIVE_DEFAULT_FOLDER_ID: "root",
    PreferenceKeys.GOOGLE_DRIVE_SEARCH_SCOPE: "my_drive",
    PreferenceKeys.GOOGLE_DRIVE_PAGE_SIZE: 10,
    PreferenceKeys.LLM_DEFAULT_MODEL: "llama3.2",
    PreferenceKeys.LLM_TEMPERATURE: 0.7,
    PreferenceKeys.LLM_MAX_TOKENS: 2048,
    PreferenceKeys.LLM_PROVIDER: "ollama",
    PreferenceKeys.EMBEDDINGS_MODEL: "qwen3-embedding:4b",
    PreferenceKeys.EMBEDDINGS_PROVIDER: "ollama",
    PreferenceKeys.UI_THEME: "dark",
    PreferenceKeys.UI_ITEMS_PER_PAGE: 50,
    PreferenceKeys.UI_DEFAULT_VIEW: "grid",
    PreferenceKeys.CRAWL_MAX_DEPTH: 3,
    PreferenceKeys.CRAWL_MAX_PAGES: 100,
    PreferenceKeys.CRAWL_TIMEOUT: 30,
    PreferenceKeys.RAG_SEARCH_MODE: "hybrid",
    PreferenceKeys.RAG_TOP_K: 10,
    PreferenceKeys.RAG_USE_RERANK: True,
    PreferenceKeys.WORKFLOWS_AUTO_SAVE: True,
    PreferenceKeys.NOTIFICATIONS_EMAIL_ENABLED: True,
    PreferenceKeys.NOTIFICATIONS_DISCORD_ENABLED: False,
    PreferenceKeys.IMMICH_AUTO_BACKUP: False,
    PreferenceKeys.IMMICH_BACKUP_FOLDER: "/backups",
    # Discord fallbacks
    PreferenceKeys.DISCORD_ENABLED_CAPABILITIES: ["echo"],
    PreferenceKeys.DISCORD_CHAT_MODE: "echo",
    PreferenceKeys.DISCORD_PERSONALITY_ID: None,
    PreferenceKeys.DISCORD_RAG_COLLECTION: "documents",
    PreferenceKeys.DISCORD_NOTIFICATIONS_ENABLED: True,
}
