# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Modaletta integrates [Letta](https://docs.letta.com) (an agent framework with persistent memory) with [Modal](https://modal.com/docs) (a serverless compute platform) for scalable AI agent deployment. The project is in early development - see README.md for current status.

## Build & Development Commands

```bash
# Install with dev dependencies
pip install -e .[dev]

# Run tests
python -m pytest tests/ -v
python -m pytest tests/test_config.py::test_default_config -v  # single test

# Linting and formatting
ruff check .
ruff format .

# Type checking
mypy .

# CLI usage
modaletta --help
modaletta config-info
```

## Architecture

### Core Components (`src/modaletta/`)

- **config.py**: `ModalettaConfig` - Pydantic model for environment-based configuration. Loads from env vars via `from_env()` classmethod.

- **client.py**: `ModalettaClient` - Wrapper around `letta-client` that provides agent lifecycle operations (create, delete, list, send_message, memory management). Creates Letta client lazily via property.

- **agent.py**:
  - `ModalettaAgent` - High-level agent abstraction that wraps `ModalettaClient`. Lazy-creates agents on first access to `agent_id` property.
  - Modal deployment functions (`create_modal_agent`, `send_message_modal`, `get_agent_memory_modal`) - These are `@app.function` decorated for Modal serverless execution.

- **cli.py**: Click-based CLI with commands: `list-agents`, `create-agent`, `delete-agent`, `send-message`, `get-memory`, `config-info`.

### Data Flow

1. Configuration loaded from environment → `ModalettaConfig`
2. Config used to create `ModalettaClient` → connects to Letta server
3. `ModalettaAgent` uses client for operations OR
4. Modal functions wrap agent operations for serverless execution

### Key Dependencies

- `letta-client`: Python client for Letta agent framework
- `modal`: Serverless compute platform SDK
- `pydantic`: Configuration validation
- `click` + `rich`: CLI interface

## Environment Variables

See `.env.example` for all variables. Key ones:
- `LETTA_SERVER_URL`: Letta server endpoint (default: `http://localhost:8283`)
- `LETTA_API_KEY`: Letta authentication
- `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET`: Modal authentication

## Scheduled Agent Wakeups

The `src/modaletta/scheduled/wakeup.py` module provides autonomous agent wakeups via Modal cron.

### Setup

1. Create Modal secret with Letta credentials:
   ```bash
   modal secret create letta-credentials \
     LETTA_SERVER_URL="https://api.letta.com/" \
     LETTA_API_KEY="<your-key>"
   ```

2. Initialize the agent roster (tells the cron which agents to wake):
   ```bash
   modal run src/modaletta/scheduled/wakeup.py --init --agent-id <agent-id>
   ```

### Testing

Test a one-time wakeup for a specific agent:
```bash
modal run src/modaletta/scheduled/wakeup.py --agent-id <agent-id>
```

Test with a custom prompt:
```bash
modal run src/modaletta/scheduled/wakeup.py --agent-id <agent-id> --prompt "Check for new emails and summarize"
```

Initialize roster with a custom scheduled prompt:
```bash
modal run src/modaletta/scheduled/wakeup.py --init --agent-id <agent-id> --prompt "Review daily tasks and priorities"
```

View wakeup logs for an agent:
```bash
modal run src/modaletta/scheduled/wakeup.py --logs --agent-id <agent-id>
```

### Deployment

Deploy the scheduled wakeup (runs every 15 minutes):
```bash
modal deploy src/modaletta/scheduled/wakeup.py
```

### How It Works

- Sends a system message to agents asking them to review memory and pending tasks
- Agents respond with status acknowledgment or take actions via tools
- Logs stored in Modal volume at `/data/logs/<agent-id>.jsonl`
- Agent roster stored at `/data/agents.json`

## Design Documents

See `docs/` for architecture plans:
- `design-autonomous-infrastructure.md`: Scheduled wakeups, persistent volumes, web chat UI
- `design-mcp-tools.md`: MCP tool servers on Modal for filesystem, web, code execution
