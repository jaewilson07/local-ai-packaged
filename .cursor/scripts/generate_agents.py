#!/usr/bin/env python3
"""
generate_agents.py

Implements the hierarchical AGENTS.md generation process from generate_agent.md.

This script analyzes the codebase and generates a hierarchical AGENTS.md structure
following the 4-phase process defined in .cursor/instructions/generate_agent.md.

Usage:
    python .cursor/scripts/generate_agents.py [--output-dir OUTPUT_DIR] [--dry-run]

Options:
    --output-dir    Directory to write generated AGENTS.md files (default: project root)
    --dry-run       Analyze and show what would be generated without writing files
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Get project root (parent of .cursor)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INSTRUCTIONS_FILE = PROJECT_ROOT / ".cursor" / "instructions" / "generate_agent.md"


def read_instructions() -> str:
    """Read the generate_agent.md instructions file."""
    if not INSTRUCTIONS_FILE.exists():
        print(f"Error: Instructions file not found: {INSTRUCTIONS_FILE}")
        sys.exit(1)
    return INSTRUCTIONS_FILE.read_text()


def run_cursor_command(prompt: str) -> str:
    """
    Execute a command in Cursor's AI context.

    This function prepares the prompt to be used with Cursor's @ symbol
    to reference the instructions file.
    """
    instructions_ref = "@.cursor/instructions/generate_agent.md"
    full_prompt = f"{instructions_ref}\n\n{prompt}"
    return full_prompt


def phase1_analysis() -> dict:
    """
    Phase 1: Repository Analysis

    Analyzes the codebase structure and returns a structured map.
    """
    print("Phase 1: Analyzing repository structure...")

    # This would typically use codebase_search or similar tools
    # For now, we'll prepare the prompt for Cursor to execute
    analysis_prompt = """
    Analyze this codebase and provide a Structured Map containing:

    1. Repository & Stack: Type (Monorepo/Polyrepo), Languages, Frameworks, Build System.
    2. Architecture: Identify the core domains (e.g., `apps/web`, `services/payment`, `packages/ui`).
    3. Testing Strategy: Frameworks (Vitest/Jest/Playwright) and locations.
    4. Agent "Gotchas":
       - Identify "Legacy" vs "Modern" directories.
       - Identify unique patterns that usually confuse AI (e.g., custom state managers, non-standard API wrappers).

    Format as a structured summary.
    """

    return {"prompt": analysis_prompt, "phase": 1, "description": "Repository Analysis"}


def phase2_root_agents() -> dict:
    """
    Phase 2: Generate Root AGENTS.md

    Creates the universal constitution file.
    """
    print("Phase 2: Generating root AGENTS.md...")

    prompt = """
    Create a Root AGENTS.md (~150-250 lines) that acts as the universal constitution.

    It must include:

    1. Agent Behavioral Protocols (Crucial)
       - Thinking Process: "Think Step-by-Step. 1. Explore context. 2. Verify previous patterns (DRY). 3. Plan."
       - Safety: "Never run `rm -rf`, drop tables, or commit secrets without explicit user confirmation."
       - Error Handling: "No blind retries. If a fix fails, stop, analyze the error log, and propose a new strategy."
       - Drift Check: "If this document contradicts the active codebase, **trust the codebase** and flag the discrepancy."

    2. Token Economy & Output
       - "Use `sed` or patch-style replacements for small edits."
       - "Do not output unchanged code blocks (use `// ... existing code ...`)."
       - "Do not repeat the user's prompt in your response."

    3. Universal Tech Stack & Commands
       - Package Manager: (pnpm/npm/bun)
       - Commands: `build`, `test`, `lint`.
       - Code Style: "Strict TypeScript", "Functional React", etc.

    4. JIT Index (The Map)
       A directory map pointing to sub-files:
       - `apps/web/` → [Read apps/web/AGENTS.md](apps/web/AGENTS.md)
       - `packages/ui/` → [Read packages/ui/AGENTS.md](packages/ui/AGENTS.md)

    Output the complete file content.
    """

    return {
        "prompt": prompt,
        "phase": 2,
        "description": "Root AGENTS.md Generation",
        "output_file": "AGENTS.md",
    }


def phase3_sub_agents(components: list[str]) -> list[dict]:
    """
    Phase 3: Generate Sub-Folder AGENTS.md Files

    For each major component, creates a detailed Sub-AGENTS.md.
    """
    print(f"Phase 3: Generating {len(components)} sub-folder AGENTS.md files...")

    prompts = []

    for component in components:
        prompt = f"""
        For the component: {component}

        Create a detailed Sub-AGENTS.md containing:

        1. Component Identity & Versions
           - Strict Versioning: "Next.js 14.1 (App Router)", "React 18", "Node 20".
           - Constraint: "Do not use `getInitialProps` or `pages/` directory patterns."

        2. Architecture & Patterns (The "Do's and Don'ts")
           - File Organization: Where components, hooks, and utils live.
           - Code Examples (Must use real file paths):
             * ✅ DO: "Use this pattern for API calls: `src/lib/api.ts`"
             * ❌ DON'T: "Avoid `useEffect` for data fetching; use `useQuery`."
           - Domain Dictionary: Define ambiguous terms (e.g., "User" vs "Patient", "Account" vs "Organization").

        3. Key Files & JIT Search
           - Touch Points: "Auth logic is in `src/auth/provider.tsx`".
           - Search Hints:
             * "Find Components: `rg -n 'export function' src/components`"
             * "Find Routes: `rg -n 'export async function GET' src/app`"

        4. Testing & Validation
           - Command: Specific test command for *this* package (e.g., `pnpm --filter web test`).
           - Strategy: "Unit test logic, E2E test critical flows."

        Output the complete file content for {component}/AGENTS.md.
        """

        prompts.append(
            {
                "prompt": prompt,
                "phase": 3,
                "description": f"Sub-AGENTS.md for {component}",
                "output_file": f"{component}/AGENTS.md",
                "component": component,
            }
        )

    return prompts


def phase4_format_output() -> dict:
    """
    Phase 4: Output Format

    Ensures proper formatting of all generated files.
    """
    print("Phase 4: Formatting output...")

    prompt = """
    Format all generated AGENTS.md files using code blocks with file path headers:

    ```markdown
    ---
    File: `AGENTS.md` (root)
    ---
    [Content]

    ---
    File: `apps/web/AGENTS.md`
    ---
    [Content]
    ```

    Ensure all files follow this format.
    """

    return {"prompt": prompt, "phase": 4, "description": "Output Formatting"}


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate hierarchical AGENTS.md structure for the codebase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate all AGENTS.md files
    python .cursor/scripts/generate_agents.py

    # Dry run (show what would be generated)
    python .cursor/scripts/generate_agents.py --dry-run

    # Custom output directory
    python .cursor/scripts/generate_agents.py --output-dir ./docs/agents

Note: This script prepares prompts for Cursor's AI to execute.
      The actual generation should be done in Cursor using the @ symbol
      to reference .cursor/instructions/generate_agent.md
        """,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT,
        help="Directory to write generated AGENTS.md files (default: project root)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze and show what would be generated without writing files",
    )

    args = parser.parse_args()

    # Verify instructions file exists
    if not INSTRUCTIONS_FILE.exists():
        print(f"Error: Instructions file not found: {INSTRUCTIONS_FILE}")
        sys.exit(1)

    print("=" * 70)
    print("AGENTS.md Generator")
    print("=" * 70)
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Instructions: {INSTRUCTIONS_FILE}")
    print(f"Output Directory: {args.output_dir}")
    print(f"Dry Run: {args.dry_run}")
    print("=" * 70)
    print()

    # Read instructions
    instructions = read_instructions()
    print(f"✓ Loaded instructions ({len(instructions)} characters)")
    print()

    # Execute phases
    phases = []

    # Phase 1: Analysis
    phase1 = phase1_analysis()
    phases.append(phase1)

    # Phase 2: Root AGENTS.md
    phase2 = phase2_root_agents()
    phases.append(phase2)

    # Phase 3: Sub-AGENTS.md (would need component detection)
    # For now, we'll prepare the structure
    # In a real implementation, you'd detect components from the codebase
    print("Note: Component detection for Phase 3 would be implemented here")
    print("      For now, you'll need to specify components manually in Cursor")

    # Phase 4: Formatting
    phase4 = phase4_format_output()
    phases.append(phase4)

    # Output instructions for Cursor
    print()
    print("=" * 70)
    print("CURSOR COMMAND INSTRUCTIONS")
    print("=" * 70)
    print()
    print("To execute this in Cursor, use the following command:")
    print()
    print("  @.cursor/instructions/generate_agent.md")
    print()
    print("Then paste the following prompt:")
    print()
    print("-" * 70)

    for phase in phases:
        print(f"\n## Phase {phase['phase']}: {phase['description']}\n")
        print(phase["prompt"])
        if "output_file" in phase:
            print(f"\nOutput file: {phase['output_file']}")

    print("-" * 70)
    print()
    print("=" * 70)
    print("ALTERNATIVE: Use Cursor's Composer")
    print("=" * 70)
    print()
    print("You can also use Cursor's Composer feature:")
    print("1. Open Composer (Cmd/Ctrl + I)")
    print("2. Reference the instructions: @.cursor/instructions/generate_agent.md")
    print("3. Ask: 'Generate the hierarchical AGENTS.md structure following the")
    print("   instructions in the referenced file'")
    print()

    if args.dry_run:
        print("✓ Dry run complete. No files were written.")
    else:
        print("Note: This script prepares prompts for Cursor.")
        print("      Actual file generation should be done in Cursor's AI context.")


if __name__ == "__main__":
    main()
