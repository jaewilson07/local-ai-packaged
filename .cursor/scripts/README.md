# Cursor Scripts

Utility scripts for Cursor IDE workflows.

## generate_agents.py

Generates hierarchical AGENTS.md structure for the codebase following the process defined in `.cursor/instructions/generate_agent.md`.

### Usage

#### Option 1: Direct Python Execution

```bash
# Generate prompts for Cursor
python .cursor/scripts/generate_agents.py

# Dry run (show what would be generated)
python .cursor/scripts/generate_agents.py --dry-run
```

#### Option 2: Use in Cursor IDE

1. **Using @ Symbol**:
   - In Cursor's chat, type: `@.cursor/instructions/generate_agent.md`
   - Then ask: "Generate the hierarchical AGENTS.md structure following the instructions in the referenced file"

2. **Using Composer**:
   - Open Composer (Cmd/Ctrl + I)
   - Reference: `@.cursor/instructions/generate_agent.md`
   - Prompt: "Generate the hierarchical AGENTS.md structure following the instructions"

3. **Using the Script Output**:
   - Run: `python .cursor/scripts/generate_agents.py`
   - Copy the generated prompts
   - Paste into Cursor's chat with `@.cursor/instructions/generate_agent.md` referenced

### How It Works

The script implements the 4-phase process:

1. **Phase 1: Repository Analysis** - Analyzes codebase structure
2. **Phase 2: Root AGENTS.md** - Generates universal constitution
3. **Phase 3: Sub-Folder AGENTS.md** - Creates component-specific files
4. **Phase 4: Output Formatting** - Ensures proper formatting

### Cursor Version

**Note**: As of 2024, Cursor's nightly builds are no longer maintained. The development team releases stable builds every 1-2 weeks with experimental features available via Settings > Beta.

To check your Cursor version:
```bash
cursor --version
```

Current version: `2.3.29` (stable build)

### Custom Commands in Cursor

Cursor doesn't have a built-in `.cursor/commands` directory system like VS Code. However, you can:

1. **Reference files with @**: Use `@filename` to include files in context
2. **Use Python scripts**: Create executable scripts like this one
3. **Use Composer**: Leverage Cursor's Composer for complex multi-step tasks

### Integration with Cursor

To make this easier to use in Cursor:

1. **Add to PATH** (optional):
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   export PATH="$PATH:/home/jaewilson07/GitHub/local-ai-packaged/.cursor/scripts"
   ```

2. **Create alias** (optional):
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   alias generate-agents="python /home/jaewilson07/GitHub/local-ai-packaged/.cursor/scripts/generate_agents.py"
   ```

3. **Use in Cursor**:
   - Simply reference `@.cursor/instructions/generate_agent.md` in chat
   - Or run the script and use its output as prompts
