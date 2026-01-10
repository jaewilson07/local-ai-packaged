# Cursor Instructions

Instructions and commands for Cursor IDE workflows.

## generate_agent.md

Instructions for generating hierarchical AGENTS.md structure for the codebase.

### Quick Start

**In Cursor Chat:**
```
@.cursor/instructions/generate_agent.md

Generate the hierarchical AGENTS.md structure following the instructions in the referenced file.
```

**Or use the helper script:**
```bash
python .cursor/scripts/generate_agents.py
```

## Converting Instructions to Commands

### Method 1: Direct @ Reference (Recommended)

The simplest way is to reference the instruction file directly in Cursor:

1. Open Cursor's chat
2. Type: `@.cursor/instructions/generate_agent.md`
3. Add your prompt: "Generate the hierarchical AGENTS.md structure following the instructions"

### Method 2: Using the Helper Script

The `generate_agents.py` script prepares structured prompts:

```bash
# Show what would be generated
python .cursor/scripts/generate_agents.py --dry-run

# Get prompts to use in Cursor
python .cursor/scripts/generate_agents.py
```

Then copy the output prompts and use them in Cursor with `@.cursor/instructions/generate_agent.md` referenced.

### Method 3: Using Composer

For complex multi-step tasks:

1. Open Composer (Cmd/Ctrl + I)
2. Reference: `@.cursor/instructions/generate_agent.md`
3. Use the full prompt from the instructions file

## Cursor Version Information

**Current Version**: `2.3.29` (stable build)

**Note**: As of January 2026, Cursor's nightly builds are no longer maintained. The development team releases stable builds every 1-2 weeks with experimental features available via **Settings > Beta**.

To check your version:
```bash
cursor --version
```

## Custom Commands in Cursor

Cursor doesn't have a built-in `.cursor/commands` directory system like VS Code. However, you can:

1. **Use @ references**: Reference files directly in chat (`@filename`)
2. **Create Python scripts**: Executable scripts in `.cursor/scripts/`
3. **Use Composer**: Multi-step AI workflows
4. **Use AGENTS.md**: Project-level agent instructions (already in use)

## File Structure

```
.cursor/
├── instructions/          # Instruction files for AI agents
│   ├── generate_agent.md  # AGENTS.md generation instructions
│   └── agent_design.md    # Pydantic AI agent design patterns
├── scripts/               # Executable helper scripts
│   ├── generate_agents.py # Helper for generate_agent.md
│   └── README.md          # Script documentation
└── PRDS/                  # Product requirements documents
```
