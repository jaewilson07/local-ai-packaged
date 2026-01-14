# External Services Samples

Sample scripts demonstrating integration with external services (Google Drive, Google Calendar, etc.).

## Google Drive Samples

### Prerequisites

Set up Google OAuth credentials in your `.env` file:

```bash
# Option 1: JSON format (recommended)
GDOC_CLIENT='{"installed":{"client_id":"...","client_secret":"..."}}'
GDOC_TOKEN='{"token":"...","refresh_token":"...","token_uri":"..."}'

# Option 2: Separate values
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REFRESH_TOKEN=your_refresh_token
```

### Available Samples

#### Simple Search
Search Google Drive and list results:
```bash
python sample/external/google_drive_simple_search.py
```

#### Search and Download Tabs
Search for documents and download all tabs with organized file structure:
```bash
python sample/external/google_drive_search_and_download_tabs.py
```

This will:
1. Search Google Drive for "copilot agent plan"
2. Find all Google Docs matching the query
3. Export each tab to `EXPORTS/gdrive/<doc_id>_<doc_title>/<tab_name>.md`
4. Create a `_metadata.md` file with document information

### File Organization

Downloaded documents are organized as:
```
EXPORTS/gdrive/
├── <doc_id>_<doc_slug>/
│   ├── _metadata.md              # Document metadata and tab index
│   ├── 00_<tab_title>.md         # First tab content
│   ├── 01_<tab_title>.md         # Second tab content
│   └── ...
└── <another_doc_id>_<doc_slug>/
    └── ...
```

### Utilities

The samples use text utilities from `src/shared/text_utils.py`:

- `clean_filename()` - Sanitize strings for safe filenames
- `slugify()` - Convert text to URL-safe slugs
- `safe_path_join()` - Safely join path components

## Service Architecture

The Google Drive service uses composition-based architecture:

```python
from services.external.google_drive import GoogleDriveService

service = GoogleDriveService()

# Search operations
results = service.search_files(query="...", top_n=10)
doc_ids = service.search_document_ids(query="...")

# Export operations
content = service.export_as_markdown(doc_id)
tabs = service.export_tabs(doc_id)

# Download operations
binary_data = service.download_file(file_id)
```

### Inner Class Access

For direct access to composed functionality:

```python
# Direct search access
results = service.api.Search.search(query="...", top_n=10)
folder_id = service.api.Search.resolve_folder("Folder Name")

# Direct export access
markdown = service.api.Export.export_as_markdown(doc_id)
binary = service.api.Export.download_file(file_id)
```

## Error Handling

The service raises specific exceptions:

```python
from services.external.google_drive.classes import (
    GoogleDriveException,
    GoogleDriveAuthError,
    GoogleDriveNotFoundError,
    GoogleDriveExportError,
    GoogleDriveSearchError
)

try:
    results = service.search_files(query="...")
except GoogleDriveAuthError as e:
    print(f"Authentication failed: {e}")
except GoogleDriveSearchError as e:
    print(f"Search failed: {e}")
```

## See Also

- [Google Drive Service Documentation](../../04-lambda/src/services/external/google_drive/README.md)
- [Google Drive Class Documentation](../../04-lambda/src/services/external/google_drive/classes/)
- [Text Utils Documentation](../../04-lambda/src/shared/text_utils.py)
