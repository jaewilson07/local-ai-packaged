"""Sample script: Search Google Drive and download document tabs.

This script demonstrates:
1. Searching Google Drive for files matching a query
2. Downloading all tabs from Google Docs
3. Organizing exports by document with clean filenames

Usage:
    python sample/external/google_drive_search_and_download_tabs.py

Environment variables required:
- GDOC_CLIENT: OAuth client configuration JSON
- GDOC_TOKEN: Serialized token JSON
OR
- GOOGLE_CLIENT_ID: OAuth client ID
- GOOGLE_CLIENT_SECRET: OAuth client secret
- GOOGLE_REFRESH_TOKEN: OAuth refresh token
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "04-lambda" / "src"))

from services.external.google_drive import GoogleDriveService
from shared.text_utils import clean_filename, slugify


def main():
    """Search Google Drive and download tabs for matching documents."""
    
    # Search query
    search_query = "copilot agent plan"
    export_base = project_root / "EXPORTS" / "gdrive"
    
    print(f"🔍 Searching Google Drive for: '{search_query}'")
    print(f"📁 Export directory: {export_base}\n")
    
    # Initialize Google Drive service
    service = GoogleDriveService()
    
    # Search for files
    results = service.search_files(query=search_query, top_n=20)
    
    print(f"✅ Found {results.total_results} files\n")
    
    if results.total_results == 0:
        print("No files found. Try a different query.")
        return
    
    # Filter for Google Docs (documents with tabs)
    google_docs = [
        f for f in results.files 
        if f.mime_type == "application/vnd.google-apps.document"
    ]
    
    print(f"📄 Found {len(google_docs)} Google Docs\n")
    
    # Process each document
    for idx, doc in enumerate(google_docs, 1):
        print(f"\n{'='*60}")
        print(f"[{idx}/{len(google_docs)}] Processing: {doc.name}")
        print(f"  ID: {doc.id}")
        print(f"  URL: {doc.web_view_link}")
        
        try:
            # Export tabs for this document
            tabs = service.export_tabs(doc.id)
            
            if not tabs:
                print(f"  ⚠️  No tabs found")
                continue
            
            print(f"  ✅ Found {len(tabs)} tabs")
            
            # Create document directory: EXPORTS/gdrive/<id>_<title>/
            doc_title_clean = clean_filename(doc.name, max_length=100)
            doc_slug = slugify(doc.name, max_length=50)
            doc_dir = export_base / f"{doc.id}_{doc_slug}"
            doc_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"  📁 Created: {doc_dir.relative_to(project_root)}")
            
            # Save each tab
            for tab in tabs:
                # Clean tab title for filename
                tab_title_clean = clean_filename(tab.title, max_length=100)
                tab_filename = f"{tab.index:02d}_{tab_title_clean}.md"
                tab_path = doc_dir / tab_filename
                
                # Write tab content
                tab_path.write_text(tab.markdown_content, encoding="utf-8")
                print(f"    ✅ {tab_filename} ({len(tab.markdown_content)} chars)")
            
            # Create a summary file with document metadata
            summary_path = doc_dir / "_metadata.md"
            summary_content = f"""# {doc.name}

**Document ID**: {doc.id}
**Created**: {doc.created_time}
**Modified**: {doc.modified_time}
**URL**: {doc.web_view_link}

## Tabs ({len(tabs)})

"""
            for tab in tabs:
                tab_title_clean = clean_filename(tab.title, max_length=100)
                tab_filename = f"{tab.index:02d}_{tab_title_clean}.md"
                summary_content += f"- [{tab.title}]({tab_filename})"
                if tab.tab_url:
                    summary_content += f" ([View online]({tab.tab_url}))"
                summary_content += "\n"
            
            summary_path.write_text(summary_content, encoding="utf-8")
            print(f"    📝 _metadata.md (document summary)")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue
    
    print(f"\n{'='*60}")
    print(f"\n✨ Export complete! Check: {export_base.relative_to(project_root)}")


if __name__ == "__main__":
    main()
