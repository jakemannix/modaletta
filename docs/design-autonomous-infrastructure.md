# Design: Autonomous Agent Infrastructure

This document covers three interconnected features for running Letta agents autonomously on Modal.

## Overview

Modaletta creates a **bidirectional integration** between Modal and Letta Cloud:

```
                    ┌──────────────────────────────────────┐
                    │           Modal Platform             │
                    │                                      │
     User ─────────▶│  Web Chat UI    Scheduled Wakeups   │
                    │  (FastAPI)      (Cron jobs)         │
                    │                                      │
                    │        Persistent Volumes            │
                    │   /data  /artifacts  /cache          │
                    │                                      │
                    │        MCP Tool Servers              │◀─── (see design-mcp-tools.md)
                    └───────────────┬──────────────────────┘
                                    │
                    ┌───────────────┴──────────────────────┐
                    │                                      │
                    ▼                                      │
          Modal → Letta                          Letta → Modal
          (this doc)                             (MCP tools doc)
                    │                                      │
                    │                                      ▲
                    ▼                                      │
                    ┌──────────────────────────────────────┐
                    │           Letta Cloud                │
                    │                                      │
                    │   Agent Memory  ◀──▶  LLM Reasoning  │
                    │                                      │
                    │   Tool Execution ─────────────────────┘
                    │   (calls Modal MCP servers)
                    └──────────────────────────────────────┘
```

**Modal → Letta (this document):**
- Web chat UI receives user messages, forwards to Letta agents
- Cron jobs wake agents up for autonomous processing

**Letta → Modal (see `design-mcp-tools.md`):**
- Agents call Modal-hosted MCP servers for filesystem, web, code execution

---

## Feature 1: Scheduled Agent Wakeups

### Problem

Agents currently only respond to human messages. For autonomous operation, agents need to:
- Wake up periodically to check for work
- Process background tasks (emails, notifications, data syncs)
- Maintain state without human intervention

### Design

```python
# src/modaletta/scheduled.py

import modal
from datetime import datetime
from typing import Optional
from .client import ModalettaClient
from .config import ModalettaConfig

app = modal.App("modaletta-scheduled")

volume = modal.Volume.from_name("modaletta-data", create_if_missing=True)

@app.function(
    schedule=modal.Cron("*/15 * * * *"),  # Every 15 minutes
    volumes={"/data": volume},
    secrets=[modal.Secret.from_name("letta-credentials")],
)
def agent_wakeup() -> None:
    """Periodic agent wakeup for autonomous processing."""
    config = ModalettaConfig.from_env()
    client = ModalettaClient(config)

    # Load agent roster from volume
    agents = load_agent_roster("/data/agents.json")

    for agent_config in agents:
        if not agent_config.get("autonomous_enabled"):
            continue

        agent_id = agent_config["agent_id"]
        wakeup_prompt = agent_config.get("wakeup_prompt", DEFAULT_WAKEUP_PROMPT)

        # Send wakeup message
        response = client.send_message(
            agent_id,
            wakeup_prompt,
            role="system"
        )

        # Log activity to volume
        log_wakeup(agent_id, response, "/data/logs/")

        volume.commit()


DEFAULT_WAKEUP_PROMPT = """
[AUTONOMOUS WAKEUP - {timestamp}]

You are waking up for your periodic autonomous check. Review your memory and tasks:
1. Check if you have any pending tasks or reminders
2. Review any data sources you're monitoring
3. Take any necessary actions
4. Update your memory with what you've done

If you have nothing to do, simply acknowledge and wait for the next wakeup.
"""
```

### Agent Roster Schema

```json
{
  "agents": [
    {
      "agent_id": "agent-1add5bc4-...",
      "name": "research-assistant",
      "autonomous_enabled": true,
      "wakeup_schedule": "*/15 * * * *",
      "wakeup_prompt": "Check for new papers on arxiv matching your research interests.",
      "data_sources": ["arxiv", "email"],
      "max_actions_per_wakeup": 5
    }
  ]
}
```

### Wakeup Flow

1. Modal cron triggers `agent_wakeup()`
2. Load agent roster from persistent volume
3. For each autonomous agent:
   - Send system message with wakeup prompt
   - Agent reviews memory, takes actions via tools
   - Response logged to volume
4. Commit volume changes

---

## Feature 2: Persistent Storage

### Problem

Agents need durable storage for:
- Documents and artifacts they create
- Embeddings for retrieval
- Logs and audit trails
- Configuration that persists across function invocations

### Design

```python
# src/modaletta/storage.py

import modal
from pathlib import Path
from typing import Optional
import json

# Create named volumes
data_volume = modal.Volume.from_name("modaletta-data", create_if_missing=True)
artifacts_volume = modal.Volume.from_name("modaletta-artifacts", create_if_missing=True)

app = modal.App("modaletta-storage")


@app.cls(volumes={"/data": data_volume, "/artifacts": artifacts_volume})
class AgentStorage:
    """Persistent storage interface for agents."""

    @modal.method()
    def save_document(self, agent_id: str, doc_name: str, content: bytes) -> str:
        """Save a document to agent's artifact storage."""
        path = Path(f"/artifacts/{agent_id}/{doc_name}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        artifacts_volume.commit()
        return str(path)

    @modal.method()
    def load_document(self, agent_id: str, doc_name: str) -> Optional[bytes]:
        """Load a document from agent's artifact storage."""
        path = Path(f"/artifacts/{agent_id}/{doc_name}")
        if path.exists():
            return path.read_bytes()
        return None

    @modal.method()
    def list_documents(self, agent_id: str) -> list[str]:
        """List all documents for an agent."""
        path = Path(f"/artifacts/{agent_id}")
        if not path.exists():
            return []
        return [f.name for f in path.iterdir() if f.is_file()]

    @modal.method()
    def append_log(self, agent_id: str, entry: dict) -> None:
        """Append to agent's activity log."""
        log_path = Path(f"/data/logs/{agent_id}.jsonl")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        data_volume.commit()
```

### Volume Structure

```
/data/                          # Configuration and logs
├── agents.json                 # Agent roster
├── logs/
│   ├── agent-xxx.jsonl        # Per-agent activity logs
│   └── agent-yyy.jsonl
└── config/
    └── global.json            # Global settings

/artifacts/                     # Agent-created content
├── agent-xxx/
│   ├── report-2024-01.pdf
│   ├── notes.md
│   └── embeddings.pkl
└── agent-yyy/
    └── ...
```

---

## Feature 3: Web Chat UI

### Problem

The Letta ADE is an admin/development interface. Users need a clean chat UI that:
- Connects to specific agents
- Streams responses in real-time
- Doesn't expose admin functionality
- Can be embedded or standalone

### Design

```python
# src/modaletta/web.py

import modal
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import json

from .client import ModalettaClient
from .config import ModalettaConfig

app = modal.App("modaletta-web")
web_app = FastAPI(title="Modaletta Chat")

# Serve static files for chat UI
# web_app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatMessage(BaseModel):
    agent_id: str
    message: str
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    messages: list[dict]
    agent_id: str


@web_app.get("/")
async def index() -> HTMLResponse:
    """Serve chat UI."""
    return HTMLResponse(CHAT_HTML)


@web_app.post("/chat", response_model=ChatResponse)
async def chat(msg: ChatMessage) -> ChatResponse:
    """Send message and get response."""
    config = ModalettaConfig.from_env()
    client = ModalettaClient(config)

    response = client.send_message(msg.agent_id, msg.message)

    return ChatResponse(messages=response, agent_id=msg.agent_id)


@web_app.websocket("/stream/{agent_id}")
async def stream_chat(websocket: WebSocket, agent_id: str) -> None:
    """WebSocket for streaming chat."""
    await websocket.accept()
    config = ModalettaConfig.from_env()
    client = ModalettaClient(config)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            # TODO: Use streaming API when available
            response = client.send_message(agent_id, msg["message"])

            for m in response:
                await websocket.send_json(m)

    except Exception:
        await websocket.close()


@web_app.get("/agents")
async def list_agents() -> list[dict]:
    """List available agents (filtered for chat access)."""
    config = ModalettaConfig.from_env()
    client = ModalettaClient(config)

    agents = client.list_agents()
    # Filter to only show chat-enabled agents
    return [
        {"id": a["id"], "name": a["name"]}
        for a in agents
        if not a.get("hidden", False)
    ]


@app.function(
    secrets=[modal.Secret.from_name("letta-credentials")],
)
@modal.asgi_app()
def serve() -> FastAPI:
    """Serve the web chat UI."""
    return web_app


# Minimal embedded chat HTML
CHAT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Modaletta Chat</title>
    <style>
        body { font-family: system-ui; max-width: 800px; margin: 0 auto; padding: 20px; }
        #messages { height: 400px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; }
        .user { color: blue; }
        .assistant { color: green; }
        .reasoning { color: gray; font-style: italic; }
        #input-area { display: flex; gap: 10px; }
        #message-input { flex: 1; padding: 10px; }
        button { padding: 10px 20px; }
    </style>
</head>
<body>
    <h1>Modaletta Chat</h1>
    <select id="agent-select"></select>
    <div id="messages"></div>
    <div id="input-area">
        <input type="text" id="message-input" placeholder="Type a message..." />
        <button onclick="sendMessage()">Send</button>
    </div>
    <script>
        let currentAgent = null;

        async function loadAgents() {
            const res = await fetch('/agents');
            const agents = await res.json();
            const select = document.getElementById('agent-select');
            agents.forEach(a => {
                const opt = document.createElement('option');
                opt.value = a.id;
                opt.textContent = a.name;
                select.appendChild(opt);
            });
            if (agents.length > 0) currentAgent = agents[0].id;
            select.onchange = (e) => currentAgent = e.target.value;
        }

        async function sendMessage() {
            const input = document.getElementById('message-input');
            const msg = input.value.trim();
            if (!msg || !currentAgent) return;

            appendMessage('user', msg);
            input.value = '';

            const res = await fetch('/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({agent_id: currentAgent, message: msg})
            });
            const data = await res.json();

            data.messages.forEach(m => {
                if (m.message_type === 'assistant_message') {
                    appendMessage('assistant', m.content);
                } else if (m.message_type === 'reasoning_message') {
                    appendMessage('reasoning', m.reasoning);
                }
            });
        }

        function appendMessage(type, text) {
            const div = document.createElement('div');
            div.className = type;
            div.textContent = `${type}: ${text}`;
            document.getElementById('messages').appendChild(div);
            div.scrollIntoView();
        }

        document.getElementById('message-input').onkeypress = (e) => {
            if (e.key === 'Enter') sendMessage();
        };

        loadAgents();
    </script>
</body>
</html>
"""
```

### Deployment

```bash
# Deploy to Modal
modal deploy src/modaletta/web.py

# Returns URL like: https://username--modaletta-web-serve.modal.run
```

---

## Integration Points

These three features work together:

1. **Scheduled wakeups** read/write to **persistent volumes**
2. **Web chat UI** can display agent artifacts from **volumes**
3. **Logs** from all interactions stored in **volumes** for audit
4. All three connect to **Letta Cloud** for agent reasoning

## Next Steps

1. Implement `scheduled.py` with basic wakeup loop
2. Create Modal secrets for Letta credentials
3. Test with a single autonomous agent
4. Build out storage layer
5. Deploy minimal chat UI
6. Add authentication to chat UI
