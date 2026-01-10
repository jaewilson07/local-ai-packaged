## GitHub Copilot agent skills and tools

This repo now includes a scaffold for custom Copilot agent skills and tools. The goal is to “pass” curated docs to Copilot and expose repo-native tools (scripts/workflows) as callable skills.

> Important: Skill/manifest schemas evolve. Use the latest docs for exact keys and placement:
- VS Code: https://code.visualstudio.com/docs/copilot/customization/agent-skills
- Platform: https://agentskills.io/home

### Layout

```
.copilot/
  skills/           # Skill manifests (one per skill)

.github/
  tools/            # Tool adapters or docs for callable commands (optional)
```

### Skills to define (suggested)

- rag.ingest — Ingest documents using the repo pipeline.
- rag.search — Run hybrid search examples/tests and summarize.
- rag.agent.debug — Run the conversational CLI against a prompt and return trace.

### Example skill manifests (pseudo)

The following are examples. Adjust to the official schema in the docs linked above.

```json
{
  "name": "rag.ingest",
  "description": "Run the ingestion pipeline over ./documents and report stats.",
  "triggers": ["ingest", "reindex", "reingest"],
  "inputs": {
    "directory": {"type": "string", "default": "./documents"},
    "chunkSize": {"type": "number", "default": 1000}
  },
  "entrypoint": {
    "type": "terminal",
    "command": "uv run python -m examples.ingestion.ingest -d ${inputs.directory} --chunk-size ${inputs.chunkSize}"
  },
  "visibility": "workspace"
}
```

```json
{
  "name": "rag.search",
  "description": "Execute hybrid search over Atlas and summarize findings.",
  "inputs": {
    "query": {"type": "string"},
    "k": {"type": "number", "default": 5}
  },
  "entrypoint": {
    "type": "terminal",
    "command": "uv run python -m examples.cli",
    "instructions": "Ask the agent to run a hybrid search for '${inputs.query}' with top ${inputs.k} results and print sources."
  }
}
```

If the platform supports tool-style skills (JSON schema I/O bound to a function), you can wrap repository code directly. For example, expose `semantic_search` and `hybrid_search` from `examples/tools.py` as callable tools.

### Passing docs to Copilot

- Consolidate knowledge in `/docs` and reference it from skill manifests (if supported) or include short inline instructions that point to the files. Suggested anchors:
  - docs/reference/agent-tools.md
  - docs/reference/mongodb-patterns.md
  - docs/reference/docling-ingestion.md
  - docs/architecture/HYBRID_SEARCH_EXPLAINED.md

### Next steps

1) Create concrete manifests under `.copilot/skills/` targeting your workflow.  
2) If using VS Code, note VS Code currently discovers skills under `.github/skills/`. You may duplicate selected skills there for VS Code consumption while keeping `.copilot/skills/` as your canonical location.  
3) Optionally add GitHub Actions to validate skills manifests and run smoke tests.
