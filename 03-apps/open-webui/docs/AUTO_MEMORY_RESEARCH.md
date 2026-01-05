# Auto Memory Extension Research

## Overview

This document contains research findings on the Auto Memory Function Extension by Davixk, which automatically identifies and stores valuable information from chats as memories within Open WebUI.

## Source

- **Repository**: `github.com/Davixk/open-webui-extensions`
- **Extension Name**: Auto Memory Function Extension
- **Author**: Davixk

## Features

Based on research, the Auto Memory extension provides:

1. **Automatic Memory Capture**
   - Automatically identifies and stores valuable information from chats
   - Analyzes conversations to extract key details for future interactions
   - Captures relevant information from user messages

2. **Memory Management**
   - Consolidates similar or overlapping memories to avoid duplication
   - Updates conflicting information with the most recent data
   - Optional saving of assistant responses as memories

3. **Configuration Options**
   - Configurable memory processing parameters
   - OpenAI API URL configuration
   - Model selection
   - API key configuration
   - Related memories count
   - Memory distance threshold

## Evaluation Criteria

### Pros
- ✅ Automatic memory extraction (no manual work)
- ✅ Memory consolidation (prevents duplicates)
- ✅ Conflict resolution (updates with latest data)
- ✅ Configurable parameters
- ✅ Community-maintained extension

### Cons / Limitations
- ❓ Unknown: Topic-based organization support
- ❓ Unknown: Integration with PostgreSQL storage
- ❓ Unknown: RAG export capabilities
- ❓ Unknown: Custom topic classification

## Decision Points

### Option A: Use As-Is
**If**: The extension meets all requirements without modification
**Action**: Install and configure the extension
**Pros**: Quick implementation, community support
**Cons**: May lack topic organization features

### Option B: Extend the Extension
**If**: The extension is close but needs topic-based organization
**Action**: Fork and extend the extension
**Pros**: Builds on existing work, adds needed features
**Cons**: Requires maintenance of fork

### Option C: Build Custom
**If**: The extension doesn't fit our needs or is too different
**Action**: Build custom memory extension
**Pros**: Full control, tailored to our needs
**Cons**: More development time

## Next Steps

1. **Clone and Test**
   ```bash
   git clone https://github.com/Davixk/open-webui-extensions.git
   cd open-webui-extensions
   # Review code structure and functionality
   ```

2. **Evaluate Features**
   - Test automatic memory extraction
   - Check if it supports topic-based organization
   - Verify PostgreSQL storage compatibility
   - Test memory consolidation behavior

3. **Compare with Requirements**
   - Does it support topic classification?
   - Can memories be exported to RAG?
   - Does it integrate with our PostgreSQL setup?
   - Can topics be manually overridden?

4. **Make Decision**
   - Choose Option A, B, or C based on evaluation
   - Document decision and rationale

## Integration Points

If we use or extend this extension, we need to integrate with:

1. **PostgreSQL Storage**
   - Ensure memories are stored in Supabase PostgreSQL
   - May need to modify storage backend

2. **Topic Classification**
   - Add topic classification to memory extraction
   - Integrate with our topic classifier extension

3. **RAG Export**
   - Export memories to MongoDB RAG system
   - Make memories searchable via vector search

## Alternative Approaches

If the Auto Memory extension doesn't fit, we can:

1. **Build Custom Extension**
   - Create Open WebUI function extension
   - Implement memory extraction with topic support
   - Integrate with PostgreSQL and RAG

2. **Use Open WebUI Pipelines**
   - Create pipeline for memory extraction
   - Process conversations through pipeline
   - Store memories in PostgreSQL

3. **Lambda Service Approach**
   - Create Lambda service for memory extraction
   - Poll Open WebUI API for new conversations
   - Process and store memories

## References

- [Open WebUI Extensions Documentation](https://docs.openwebui.com/features/plugin/)
- [Davixk's Auto Memory Extension](https://github.com/Davixk/open-webui-extensions)
- Open WebUI Functions API documentation

