# AI Editor Instructions Overview

This project uses multiple instruction files to guide AI coding assistants.

## GitHub Copilot (VS Code)

GitHub Copilot automatically reads from:

### 1. Repository Instructions
**File**: [`.github/copilot-instructions.md`](../.github/copilot-instructions.md)
- Applied to **all chat requests** in the workspace
- Repository-wide coding standards and patterns

### 2. AGENTS.md Files (Experimental)
**Files**: `AGENTS.md` at root and in subdirectories
- Automatically applies to all chat requests
- Stack-specific and project-specific rules
- See [root AGENTS.md](../AGENTS.md) for the Universal Constitution

### 3. .instructions.md Files (Optional)
**Pattern**: `**/.instructions.md` files with glob patterns
- Conditionally apply based on file type or location
- Not currently used in this project

## Cursor AI

Cursor uses the modern `.cursor/rules/` directory:

### Current Rules
- **[core.md](rules/core.md)** - Core development principles
- **[sample-files.md](rules/sample-files.md)** - Sample directory guidelines  
- **[docker-compose.md](rules/docker-compose.md)** - Docker Compose patterns

### How Cursor Rules Work
- Each rule can specify semantic descriptions
- Supports glob patterns for path-specific rules
- Auto-attach when matching files are referenced
- Can be triggered manually with `@rulename`

## Hierarchy and Precedence

Both editors follow this general hierarchy:
1. **Most specific**: Path-specific rules (Cursor's glob patterns)
2. **Project-level**: `.github/copilot-instructions.md` and `.cursor/rules/`
3. **Universal**: `AGENTS.md` files (source of truth)

## Key Principle

> **When in doubt, refer to `AGENTS.md` as the source of truth.**

All instruction files should align with the patterns and rules established in the AGENTS.md hierarchy.

## Adding New Instructions

### For GitHub Copilot
Edit [`.github/copilot-instructions.md`](../.github/copilot-instructions.md)

### For Cursor
1. Use command palette: `Cmd + Shift + P` > `New Cursor Rule`
2. Or create a new `.md` file in `.cursor/rules/`

### For Both
Update the relevant `AGENTS.md` file and sync changes to both instruction systems.

## Migration Notes

- ✅ Migrated from legacy `.cursorrules` to `.cursor/rules/` directory (January 2026)
- ✅ Created `.github/copilot-instructions.md` for GitHub Copilot
- ✅ Both systems now aligned with `AGENTS.md` hierarchy
