# Outstanding Work Summary

This document summarizes remaining work to complete the Service vs Capability Architecture implementation.

## ✅ Completed Projects

1. **`knowledge`** - Fully compliant
   - ✅ dependencies.py, tools.py, agent.py
   - ✅ REST API refactored
   - ✅ MCP tools updated
   - ✅ Documentation created

2. **`blob_storage`** - Fully compliant
   - ✅ dependencies.py, tools.py, agent.py
   - ✅ REST API refactored
   - ✅ MCP tools added
   - ✅ Documentation updated

## ⚠️ Partially Completed Projects

### `comfyui_workflow`
**Status**: Structure in place, router needs refactoring

**Completed:**
- ✅ config.py created
- ✅ dependencies.py updated to inherit BaseDependencies
- ✅ tools.py created with core CRUD operations
- ✅ agent.py created with core tools

**Outstanding:**
- ⚠️ **router.py refactoring** - 36 endpoints need to be updated to use tools.py pattern
  - This is a large task but the structure is ready
  - All endpoints currently call services/stores directly
  - Need to refactor to use `create_run_context()` and call tools

**Priority**: Medium (structure is in place, just needs refactoring)

## ❌ Non-Compliant Projects

### `google_drive`
**Status**: Missing all components

**Outstanding:**
- [ ] Create config.py
- [ ] Create dependencies.py (inherit BaseDependencies)
- [ ] Create tools.py (extract capabilities from service)
- [ ] Create agent.py (agent tools)
- [ ] Create/update REST API to use tools
- [ ] Add MCP tools

**Priority**: Medium

### `entity_extraction`
**Status**: May be a library project

**Outstanding:**
- [ ] Determine if this is a capability project or library
- [ ] If capability: Create dependencies.py, tools.py, agent.py
- [ ] If library: Document as infrastructure service

**Priority**: Low (needs clarification)

### `conversation`
**Status**: Has agent.py but missing dependencies.py and tools.py

**Outstanding:**
- [ ] Create dependencies.py (currently uses PersonaDeps)
- [ ] Extract tools.py from agent.py
- [ ] Refactor agent.py to use tools.py

**Priority**: Medium

## 🔍 Verification Needed

These projects claim to have dependencies.py, tools.py, and agent.py but need verification:

- `calendar`
- `graphiti_rag`
- `persona`
- `discord_characters`
- `openwebui_export`
- `openwebui_topics`
- `deep_research`

**Outstanding:**
- [ ] Verify all follow BaseDependencies pattern
- [ ] Verify tools.py functions accept RunContext[Dependencies]
- [ ] Verify REST endpoints use tools.py
- [ ] Verify MCP tools call REST endpoints or tools
- [ ] Ensure proper error handling
- [ ] Ensure proper resource cleanup

**Priority**: Low (verification task)

## 📋 Phase 3: Standardization

**Outstanding:**
- [ ] Verify all projects follow BaseDependencies pattern
- [ ] Verify all tools.py functions accept RunContext[Dependencies]
- [ ] Verify all REST endpoints use tools.py
- [ ] Verify all MCP tools call REST endpoints or tools
- [ ] Ensure proper error handling across all layers
- [ ] Ensure proper resource cleanup (try/finally)
- [ ] Create project templates/documentation for new projects

**Priority**: Low (ongoing maintenance)

## 🎯 Recommended Next Steps

1. **High Priority**: Complete `comfyui_workflow` router refactoring
   - Start with a few endpoints as examples
   - Apply pattern to remaining endpoints
   - Test thoroughly

2. **Medium Priority**: Implement `google_drive` project
   - Follow the established pattern from `knowledge` and `blob_storage`
   - Extract capabilities from existing service

3. **Medium Priority**: Refactor `conversation` project
   - Create proper dependencies.py
   - Extract tools from agent.py

4. **Low Priority**: Verification tasks
   - Systematically verify each project
   - Update documentation as needed

## 📝 Notes

- All new projects should follow the standard structure from day one
- The `auth` project is a special case (infrastructure service, not a capability)
- Some projects may have legacy patterns that need gradual migration
- Focus on critical path projects first, then verification
