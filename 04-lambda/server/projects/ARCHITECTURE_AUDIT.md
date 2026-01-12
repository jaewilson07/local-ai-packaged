# Architecture Compliance Audit

This document tracks compliance with the Service vs Capability Architecture PRD.

## Projects Status

### ✅ Fully Compliant
- `n8n_workflow` - Complete implementation with dependencies.py, tools.py, agent.py, REST, MCP
- `mongo_rag` - Complete implementation
- `crawl4ai_rag` - Complete implementation

### ✅ Recently Completed
- `knowledge` - ✅ Now fully compliant with dependencies.py, tools.py, agent.py, REST, MCP
- `blob_storage` - ✅ Now fully compliant with dependencies.py, tools.py, agent.py, REST, MCP

### ⚠️ Partially Compliant (In Progress)
- `comfyui_workflow` - ✅ Has dependencies.py (updated to inherit BaseDependencies), ✅ tools.py (core CRUD), ✅ agent.py (core tools), ⚠️ router.py needs refactoring to use tools.py (36 endpoints - large refactoring task)
- `conversation` - Has agent.py, but missing dependencies.py and tools.py (uses PersonaDeps)
- `calendar` - Has dependencies.py, tools.py, agent.py, but needs verification
- `graphiti_rag` - Has dependencies.py, tools.py, agent.py, but needs verification
- `persona` - Has dependencies.py, tools.py, agent.py, but needs verification
- `discord_characters` - Has dependencies.py, tools.py, agent.py, but needs verification
- `openwebui_export` - Has dependencies.py, tools.py, agent.py, but needs verification
- `openwebui_topics` - Has dependencies.py, tools.py, agent.py, but needs verification
- `deep_research` - Has dependencies.py, tools.py, agent.py, but needs verification

### ❌ Non-Compliant
- `entity_extraction` - Missing dependencies.py, tools.py, agent.py (library project, may not need full structure)
- `google_drive` - Missing dependencies.py, tools.py, agent.py
- `auth` - Special case (infrastructure service, not a capability project)

## Implementation Checklist

### Phase 1: Critical Missing Components
- [ ] Create dependencies.py for entity_extraction
- [ ] Create tools.py for entity_extraction
- [ ] Create agent.py for entity_extraction
- [ ] Create REST API for entity_extraction
- [ ] Add MCP tools for entity_extraction

- [x] Create dependencies.py for knowledge ✅
- [x] Create tools.py for knowledge ✅
- [x] Create agent.py for knowledge ✅
- [x] Update REST API for knowledge ✅
- [x] Update MCP tools for knowledge ✅

- [x] Create dependencies.py for blob_storage ✅
- [x] Create tools.py for blob_storage ✅
- [x] Create agent.py for blob_storage ✅
- [x] Update REST API for blob_storage ✅
- [x] Add MCP tools for blob_storage ✅

- [ ] Create dependencies.py for google_drive
- [ ] Create tools.py for google_drive
- [ ] Create agent.py for google_drive
- [ ] Create REST API for google_drive (if missing)
- [ ] Add MCP tools for google_drive

### Phase 2: Partial Compliance Fixes
- [x] Create tools.py for comfyui_workflow (core CRUD operations) ✅
- [x] Create agent.py for comfyui_workflow (core tools) ✅
- [x] Update dependencies.py to inherit BaseDependencies ✅
- [ ] Refactor comfyui_workflow/router.py to use tools.py (36 endpoints - large task, structure in place)

- [ ] Create dependencies.py for conversation
- [ ] Extract tools.py from conversation/agent.py
- [ ] Refactor conversation/agent.py to use tools.py

### Phase 3: Verification and Standardization
- [ ] Verify all projects follow BaseDependencies pattern
- [ ] Verify all tools.py functions accept RunContext[Dependencies]
- [ ] Verify all REST endpoints use tools.py
- [ ] Verify all MCP tools call REST endpoints
- [ ] Ensure proper error handling across all layers
- [ ] Ensure proper resource cleanup (try/finally)

## Notes

- `auth` project is a special case - it's infrastructure, not a capability project
- Some projects may have legacy patterns that need migration
- All new projects must follow the standard structure from day one
