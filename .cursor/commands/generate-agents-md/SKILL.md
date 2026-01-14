# Task: Analyze this codebase and generate a hierarchical AGENTS.md structure

## Context & Principles

You are going to help me create a **hierarchical AGENTS.md system** for this codebase. This system serves as the "brain" for AI agents (like Cursor's Composer or generic coding agents), ensuring they understand not just the *code*, but the *behavioral standards* and *architecture* of the project.

### Core Principles:
1. **Multi-Editor Support**: These AGENTS.md files serve both GitHub Copilot and Cursor AI. Both editors read AGENTS.md files, making them the universal source of truth for AI-assisted development.
2. **Nearest-wins hierarchy**: Specific rules (sub-folders) override general rules (root).
3. **JIT (Just-In-Time) indexing**: Provide paths and globs so the agent knows *where* to look, rather than dumping all text into context.
4. **Token Efficiency**: Instructions must be concise. Use high-density constraints over verbose prose.
5. **Behavior over Syntax**: The docs must define *how* the agent thinks (reasoning process), not just what code to write.
6. **No Root Directory Proliferation**: Keep root directory clean and organized. Use designated directories for specific purposes.
7. **Composition over Inheritance**: Use composition with inner classes (Capital letters) for service architecture following SOLID principles.
8. **Protocol-First Design**: Define protocols and ABC base classes for type safety and extensibility.

---

## Your Process

### Phase 1: Repository Analysis

First, analyze the codebase structure and provide a **Structured Map** containing:

1. **Repository & Stack**: Type (Monorepo/Polyrepo), Languages, Frameworks, Build System.
2. **Architecture**: Identify the core domains (e.g., `apps/web`, `services/payment`, `packages/ui`).
3. **Testing Strategy**: Frameworks (Vitest/Jest/Playwright) and locations.
4. **Agent "Gotchas"**:
    * Identify "Legacy" vs "Modern" directories.
    * Identify unique patterns that usually confuse AI (e.g., custom state managers, non-standard API wrappers).

---

### Phase 2: Generate Root `AGENTS.md` (The Constitution)

Create a **Root AGENTS.md** (~150-250 lines) that acts as the universal constitution. It must include:

**1. Agent Behavioral Protocols (Crucial)**
Define *how* the agent solves problems:
* **Multi-Editor Context**: "These instructions apply to both GitHub Copilot and Cursor AI editors."
* **Thinking Process**: "Think Step-by-Step. 1. Explore context. 2. Verify previous patterns (DRY). 3. Plan."
* **Safety**: "Never run `rm -rf`, drop tables, or commit secrets without explicit user confirmation."
* **Error Handling**: "No blind retries. If a fix fails, stop, analyze the error log, and propose a new strategy."
* **Drift Check**: "If this document contradicts the active codebase, **trust the codebase** and flag the discrepancy."
* **File Organization**: "Do not create new root-level files or directories. Use designated locations: .github/, .cursor/, docs/, sample/, scripts/, setup/, test/, temp/"

**2. Token Economy & Output**
* "Use `sed` or patch-style replacements for small edits."
* "Do not output unchanged code blocks (use `// ... existing code ...`)."
* "Do not repeat the user's prompt in your response."

**3. Universal Tech Stack & Commands**
* **Package Manager**: (pnpm/npm/bun/uv)
* **Commands**: `build`, `test`, `lint`.
* **Code Style**: "Strict TypeScript", "Functional React", etc.
* **Python Virtual Environments**: Always use `uv` for Python projects (not pip/venv/poetry)

**4. Service Composition Architecture**
* **Composition Pattern**: Use inner classes with Capital letters for service components (`Service.Search`, `Service.Export`)
* **Base Class Hierarchy**: Always use ABC and Protocol when reasonable for type safety and extensibility
* **Parent Reference**: Components access parent service via `self._parent` parameter
* **Configuration Externalization**: Move hardcoded constants to dedicated `config.py` files
* **Exception Hierarchy**: Create service-specific exceptions inheriting from base exception classes
* **SOLID Principles**: Apply Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion

**5. File Organization & Root Directory Standards**
Enforce clean root directory structure with designated locations:
* **`.github/`** - GitHub-specific configs (workflows, Copilot instructions)
* **`.cursor/`** - Cursor-specific configs (rules, commands, plans)
* **`.venv/`** - Python virtual environment (always use `uv`)
* **`/docs`** - Project documentation
* **`/sample`** - User-facing sample code and examples
* **`/scripts`** - Maintenance scripts (agents: do not modify these)
* **`/setup`** - Installation scripts (CLIs, pre-commit hooks, etc.)
* **`/test`** - Test files to validate generated code
* **`/temp`** - Temporary files during code generation (gitignored)
* Project-specific directories follow after these standard locations

**6. JIT Index (The Map)**
A directory map pointing to sub-files:
* `apps/web/` → [Read apps/web/AGENTS.md](apps/web/AGENTS.md)
* `packages/ui/` → [Read packages/ui/AGENTS.md](packages/ui/AGENTS.md)

**7. AI Editor Integration**
* **GitHub Copilot**: Reads AGENTS.md files automatically (experimental feature)
* **Cursor AI**: Reads AGENTS.md files automatically in workspace and subfolders
* **Single Source of Truth**: Keep all behavioral rules in AGENTS.md hierarchy, not in editor-specific config files
* **Supplementary Configs**:
  - `.github/copilot-instructions.md` - Summarized version for Copilot
  - `.cursor/rules/*.md` - Path-specific overrides for Cursor
  - Both should reference AGENTS.md as source of truth

---

### Phase 3: Generate Sub-Folder `AGENTS.md` Files

For EACH major component identified in Phase 1, create a detailed **Sub-AGENTS.md** containing:

**1. Component Identity & Versions**
* **Strict Versioning**: "Next.js 14.1 (App Router)", "React 18", "Node 20".
* **Constraint**: "Do not use `getInitialProps` or `pages/` directory patterns."

**2. Architecture & Patterns (The "Do's and Don'ts")**
* **File Organization**: Where components, hooks, and utils live.
* **Service Composition**: When to use inner classes (`Service.Search`, `Service.Export`) vs separate modules
* **Base Classes**: How to structure ABC and Protocol hierarchies for the domain
* **Code Examples** (Must use real file paths):
    * ✅ **DO**: "Use this pattern for API calls: `src/lib/api.ts`"
    * ❌ **DON'T**: "Avoid `useEffect` for data fetching; use `useQuery`."
    * ✅ **DO**: "Use composition for multi-concern services: `GoogleDrive.Search.search()`"
    * ❌ **DON'T**: "Create monolithic classes with mixed responsibilities"
* **Domain Dictionary**: Define ambiguous terms (e.g., "User" vs "Patient", "Account" vs "Organization").
* **Exception Patterns**: Service-specific exception hierarchies and error handling

**3. Key Files & JIT Search**
* **Touch Points**: "Auth logic is in `src/auth/provider.tsx`".
* **Search Hints**:
    * "Find Components: `rg -n 'export function' src/components`"
    * "Find Routes: `rg -n 'export async function GET' src/app`"

**4. Testing & Validation**
* **Command**: Specific test command for *this* package (e.g., `pnpm --filter web test`).
* **Strategy**: "Unit test logic, E2E test critical flows."
* **Service Testing**: "Test inner classes independently and as composition"

**5. Refactoring Guidance**
* **When to Apply Composition**: Multi-concern services, shared parent functionality, single entry point
* **Migration Strategy**: How to refactor existing monolithic services to composition pattern
* **Examples**: `ComfyUIService` → `ComfyUI.Workflow`, `ComfyUI.Model`, `ComfyUI.Queue`

---

### Phase 4: Output Format

Provide the output in the following order:

1.  **Analysis Summary** (The Map from Phase 1)
2.  **Root AGENTS.md** (Complete file content)
3.  **Sub-Folder AGENTS.md files** (Iterate through each major directory)

Format the files using code blocks with file path headers:

```markdown
---
File: `AGENTS.md` (root)
---
[Content]

---
File: `apps/web/AGENTS.md`
---
[Content]
