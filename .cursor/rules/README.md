# Cursor Rules

Modern Cursor uses the `.cursor/rules/` directory for project-specific instructions.

## How Rules Work

Each rule file can specify:
- **Description**: Semantic description of when to apply
- **Glob patterns**: Which files/folders the rule applies to
- **Auto-attach**: Automatically included when matching files are referenced
- **Manual trigger**: Reference with `@rulename` in chat

## Current Rules

- **[core.md](core.md)** - Core development principles (always applied)
- **[sample-files.md](sample-files.md)** - Rules for `sample/` directory
- **[docker-compose.md](docker-compose.md)** - Docker Compose patterns

## Creating New Rules

Use the command palette: `Cmd + Shift + P` > `New Cursor Rule`

Or create a new `.md` file in this directory.

## Migration Note

We migrated from legacy `.cursorrules` (single file) to this modern structure for better organization and path-specific rules.
