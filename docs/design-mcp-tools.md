# Design: MCP Tool Servers on Modal

This document covers running Model Context Protocol (MCP) servers on Modal to provide tools for Letta agents.

## Overview

Modaletta creates a **bidirectional integration** between Modal and Letta Cloud. This document covers the **Letta → Modal** direction: agents calling Modal-hosted tools.

```
                    ┌──────────────────────────────────────┐
                    │           Modal Platform             │
                    │                                      │
     User ─────────▶│  Web Chat UI    Scheduled Wakeups   │───── (see design-autonomous-infrastructure.md)
                    │                                      │
                    │        Persistent Volumes            │
                    │   /data  /artifacts  /cache          │
                    │                                      │
                    │  ┌────────────────────────────────┐  │
                    │  │      MCP Tool Servers          │  │
                    │  │  Filesystem │ Web │ Code Exec  │  │
                    │  └────────────────────────────────┘  │
                    └───────────────▲──────────────────────┘
                                    │
                    ┌───────────────┴──────────────────────┐
                    │                                      │
                    │                              Letta → Modal
          Modal → Letta                            (this doc)
          (other doc)                                      │
                    │                                      │
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

**Letta → Modal (this document):**
- Agents call Modal-hosted MCP servers for filesystem, web fetch, code execution
- Tools run with access to persistent volumes and sandboxed compute

**Modal → Letta (see `design-autonomous-infrastructure.md`):**
- Web chat UI receives user messages, forwards to Letta agents
- Cron jobs wake agents up for autonomous processing

## Why MCP on Modal?

**Problem**: Letta agents need tools that require:
- Filesystem access (but Letta Cloud is stateless)
- Web fetching (rate limits, caching, proxy)
- Code execution (security sandboxing)
- Heavy compute (embeddings, image processing)

**Solution**: Run MCP servers on Modal that:
- Have access to persistent volumes
- Run in isolated containers
- Scale automatically
- Can be called as HTTP endpoints from Letta tools

---

## Architecture

### MCP Server Gateway

A single Modal function acts as a gateway, routing tool calls to appropriate MCP servers:

```python
# src/modaletta/mcp/gateway.py

import modal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any
import importlib

app = modal.App("modaletta-mcp")
gateway = FastAPI(title="Modaletta MCP Gateway")

# Available MCP servers
MCP_SERVERS = {
    "filesystem": "modaletta.mcp.filesystem",
    "web": "modaletta.mcp.web",
    "code": "modaletta.mcp.code",
    "embeddings": "modaletta.mcp.embeddings",
}


class ToolCall(BaseModel):
    server: str           # Which MCP server
    method: str           # Tool method name
    arguments: dict[str, Any]
    agent_id: str         # For scoping/auth


class ToolResult(BaseModel):
    success: bool
    result: Any
    error: str | None = None


@gateway.post("/tools/call", response_model=ToolResult)
async def call_tool(call: ToolCall) -> ToolResult:
    """Route tool call to appropriate MCP server."""
    if call.server not in MCP_SERVERS:
        raise HTTPException(400, f"Unknown server: {call.server}")

    try:
        # Dynamic import of server module
        server_module = importlib.import_module(MCP_SERVERS[call.server])
        handler = getattr(server_module, call.method)

        # Execute tool with agent context
        result = await handler(
            agent_id=call.agent_id,
            **call.arguments
        )

        return ToolResult(success=True, result=result)

    except Exception as e:
        return ToolResult(success=False, result=None, error=str(e))


@gateway.get("/tools/list")
async def list_tools() -> dict:
    """List all available tools across MCP servers."""
    tools = {}
    for server_name, module_path in MCP_SERVERS.items():
        server_module = importlib.import_module(module_path)
        tools[server_name] = server_module.TOOL_DEFINITIONS
    return tools


@app.function(
    secrets=[modal.Secret.from_name("mcp-credentials")],
)
@modal.asgi_app()
def serve_gateway() -> FastAPI:
    return gateway
```

---

## MCP Server Implementations

### 1. Filesystem MCP Server

Access to persistent storage scoped by agent.

```python
# src/modaletta/mcp/filesystem.py

import modal
from pathlib import Path
from typing import Optional
import json

volume = modal.Volume.from_name("modaletta-artifacts", create_if_missing=True)

TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "Read contents of a file from agent's storage",
        "parameters": {
            "path": {"type": "string", "description": "File path relative to agent root"}
        }
    },
    {
        "name": "write_file",
        "description": "Write contents to a file in agent's storage",
        "parameters": {
            "path": {"type": "string", "description": "File path relative to agent root"},
            "content": {"type": "string", "description": "File content to write"}
        }
    },
    {
        "name": "list_files",
        "description": "List files in a directory",
        "parameters": {
            "path": {"type": "string", "description": "Directory path", "default": "/"}
        }
    },
    {
        "name": "delete_file",
        "description": "Delete a file from storage",
        "parameters": {
            "path": {"type": "string", "description": "File path to delete"}
        }
    }
]


def _agent_root(agent_id: str) -> Path:
    """Get agent's scoped root directory."""
    root = Path(f"/artifacts/{agent_id}")
    root.mkdir(parents=True, exist_ok=True)
    return root


async def read_file(agent_id: str, path: str) -> str:
    """Read file contents."""
    full_path = _agent_root(agent_id) / path.lstrip("/")
    if not full_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    # Prevent path traversal
    if not str(full_path.resolve()).startswith(str(_agent_root(agent_id))):
        raise PermissionError("Access denied")
    return full_path.read_text()


async def write_file(agent_id: str, path: str, content: str) -> dict:
    """Write file contents."""
    full_path = _agent_root(agent_id) / path.lstrip("/")
    if not str(full_path.resolve()).startswith(str(_agent_root(agent_id))):
        raise PermissionError("Access denied")
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content)
    volume.commit()
    return {"written": str(full_path), "size": len(content)}


async def list_files(agent_id: str, path: str = "/") -> list[dict]:
    """List directory contents."""
    full_path = _agent_root(agent_id) / path.lstrip("/")
    if not full_path.exists():
        return []
    return [
        {"name": f.name, "is_dir": f.is_dir(), "size": f.stat().st_size if f.is_file() else 0}
        for f in full_path.iterdir()
    ]


async def delete_file(agent_id: str, path: str) -> dict:
    """Delete a file."""
    full_path = _agent_root(agent_id) / path.lstrip("/")
    if not str(full_path.resolve()).startswith(str(_agent_root(agent_id))):
        raise PermissionError("Access denied")
    if full_path.exists():
        full_path.unlink()
        volume.commit()
        return {"deleted": path}
    raise FileNotFoundError(f"File not found: {path}")
```

### 2. Web Fetch MCP Server

HTTP fetching with caching and rate limiting.

```python
# src/modaletta/mcp/web.py

import modal
import httpx
from typing import Optional
from urllib.parse import urlparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta

cache_volume = modal.Volume.from_name("modaletta-cache", create_if_missing=True)

TOOL_DEFINITIONS = [
    {
        "name": "fetch_url",
        "description": "Fetch content from a URL",
        "parameters": {
            "url": {"type": "string", "description": "URL to fetch"},
            "method": {"type": "string", "description": "HTTP method", "default": "GET"},
            "headers": {"type": "object", "description": "Request headers", "default": {}},
        }
    },
    {
        "name": "fetch_json",
        "description": "Fetch JSON from a URL",
        "parameters": {
            "url": {"type": "string", "description": "URL to fetch"}
        }
    },
    {
        "name": "search_web",
        "description": "Search the web using a search engine",
        "parameters": {
            "query": {"type": "string", "description": "Search query"},
            "num_results": {"type": "integer", "description": "Number of results", "default": 5}
        }
    }
]

# Rate limiting per domain
RATE_LIMITS: dict[str, datetime] = {}
MIN_INTERVAL = timedelta(seconds=1)


def _check_rate_limit(url: str) -> None:
    """Simple per-domain rate limiting."""
    domain = urlparse(url).netloc
    last_request = RATE_LIMITS.get(domain)
    if last_request and datetime.now() - last_request < MIN_INTERVAL:
        raise Exception(f"Rate limited: {domain}")
    RATE_LIMITS[domain] = datetime.now()


def _cache_key(url: str, method: str) -> str:
    """Generate cache key."""
    return hashlib.md5(f"{method}:{url}".encode()).hexdigest()


def _get_cached(key: str, max_age_hours: int = 24) -> Optional[dict]:
    """Check cache for response."""
    cache_path = Path(f"/cache/{key}.json")
    if cache_path.exists():
        data = json.loads(cache_path.read_text())
        cached_at = datetime.fromisoformat(data["cached_at"])
        if datetime.now() - cached_at < timedelta(hours=max_age_hours):
            return data["response"]
    return None


def _set_cached(key: str, response: dict) -> None:
    """Store response in cache."""
    cache_path = Path(f"/cache/{key}.json")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({
        "cached_at": datetime.now().isoformat(),
        "response": response
    }))
    cache_volume.commit()


async def fetch_url(
    agent_id: str,
    url: str,
    method: str = "GET",
    headers: dict | None = None
) -> dict:
    """Fetch URL with caching and rate limiting."""
    _check_rate_limit(url)

    cache_key = _cache_key(url, method)
    if method == "GET":
        cached = _get_cached(cache_key)
        if cached:
            return {**cached, "from_cache": True}

    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, headers=headers or {})

        result = {
            "status": response.status_code,
            "headers": dict(response.headers),
            "content": response.text[:50000],  # Limit content size
            "url": str(response.url),
            "from_cache": False
        }

        if method == "GET" and response.status_code == 200:
            _set_cached(cache_key, result)

        return result


async def fetch_json(agent_id: str, url: str) -> dict:
    """Fetch and parse JSON."""
    result = await fetch_url(agent_id, url)
    if result["status"] == 200:
        return {"data": json.loads(result["content"]), "from_cache": result["from_cache"]}
    raise Exception(f"HTTP {result['status']}: {url}")


async def search_web(agent_id: str, query: str, num_results: int = 5) -> list[dict]:
    """Web search using SearXNG or similar."""
    # TODO: Configure search endpoint
    search_url = f"https://searx.example.com/search?q={query}&format=json"
    result = await fetch_json(agent_id, search_url)
    return result["data"].get("results", [])[:num_results]
```

### 3. Code Execution MCP Server

Sandboxed Python/shell execution.

```python
# src/modaletta/mcp/code.py

import modal
from typing import Optional
import subprocess
import tempfile
import os
from pathlib import Path

sandbox_image = modal.Image.debian_slim().pip_install([
    "numpy", "pandas", "requests", "beautifulsoup4"
])

TOOL_DEFINITIONS = [
    {
        "name": "execute_python",
        "description": "Execute Python code in a sandbox",
        "parameters": {
            "code": {"type": "string", "description": "Python code to execute"},
            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30}
        }
    },
    {
        "name": "execute_shell",
        "description": "Execute shell command in a sandbox",
        "parameters": {
            "command": {"type": "string", "description": "Shell command to execute"},
            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30}
        }
    }
]


# Run code in isolated Modal sandbox
@modal.function(image=sandbox_image, timeout=60)
def _run_python_sandbox(code: str, timeout: int) -> dict:
    """Execute Python in Modal sandbox."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()

        try:
            result = subprocess.run(
                ['python', f.name],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd='/tmp',
                env={**os.environ, 'HOME': '/tmp'}
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"error": "Execution timed out", "returncode": -1}
        finally:
            os.unlink(f.name)


@modal.function(image=sandbox_image, timeout=60)
def _run_shell_sandbox(command: str, timeout: int) -> dict:
    """Execute shell command in Modal sandbox."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd='/tmp'
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"error": "Execution timed out", "returncode": -1}


async def execute_python(agent_id: str, code: str, timeout: int = 30) -> dict:
    """Execute Python code."""
    # Basic security check
    forbidden = ['import os', 'import subprocess', 'import sys', '__import__', 'eval', 'exec', 'open(']
    for f in forbidden:
        if f in code:
            return {"error": f"Forbidden: {f}", "returncode": -1}

    return _run_python_sandbox.remote(code, timeout)


async def execute_shell(agent_id: str, command: str, timeout: int = 30) -> dict:
    """Execute shell command."""
    # Very restricted command set
    allowed_prefixes = ['ls', 'cat', 'head', 'tail', 'wc', 'grep', 'echo', 'date', 'pwd']
    if not any(command.strip().startswith(p) for p in allowed_prefixes):
        return {"error": "Command not allowed", "returncode": -1}

    return _run_shell_sandbox.remote(command, timeout)
```

---

## Registering Tools with Letta

To make these tools available to Letta agents, register them as custom tools:

```python
# src/modaletta/tools/register.py

from letta_client import Letta
from letta_client.types import Tool

MCP_GATEWAY_URL = "https://your-modal-app--modaletta-mcp-serve-gateway.modal.run"


def create_mcp_tool(server: str, method: str, description: str, parameters: dict) -> dict:
    """Create a Letta tool definition that calls MCP gateway."""
    return {
        "name": f"mcp_{server}_{method}",
        "description": description,
        "parameters": {
            "type": "object",
            "properties": parameters,
            "required": list(parameters.keys())
        },
        # Tool implementation calls MCP gateway
        "source_code": f'''
import httpx

def mcp_{server}_{method}(agent_state, **kwargs):
    response = httpx.post(
        "{MCP_GATEWAY_URL}/tools/call",
        json={{
            "server": "{server}",
            "method": "{method}",
            "arguments": kwargs,
            "agent_id": agent_state.agent_id
        }}
    )
    result = response.json()
    if result["success"]:
        return result["result"]
    raise Exception(result["error"])
'''
    }


def register_mcp_tools(client: Letta, agent_id: str) -> None:
    """Register all MCP tools with an agent."""
    tools = [
        create_mcp_tool("filesystem", "read_file", "Read a file", {"path": {"type": "string"}}),
        create_mcp_tool("filesystem", "write_file", "Write a file", {"path": {"type": "string"}, "content": {"type": "string"}}),
        create_mcp_tool("web", "fetch_url", "Fetch a URL", {"url": {"type": "string"}}),
        create_mcp_tool("code", "execute_python", "Run Python code", {"code": {"type": "string"}}),
    ]

    for tool in tools:
        client.tools.create(**tool)
        client.agents.tools.attach(agent_id, tool["name"])
```

---

## Security Considerations

1. **Agent scoping**: All file operations scoped to `/artifacts/{agent_id}/`
2. **Path traversal prevention**: Resolve paths and check prefixes
3. **Code sandboxing**: Run in isolated Modal containers
4. **Restricted shell**: Whitelist of allowed commands only
5. **Rate limiting**: Per-domain request throttling
6. **Content limits**: Truncate large responses
7. **No network from sandbox**: Code execution isolated from network

---

## Deployment

```bash
# Create Modal secrets
modal secret create letta-credentials LETTA_API_KEY=xxx
modal secret create mcp-credentials SEARX_URL=xxx

# Create volumes
modal volume create modaletta-artifacts
modal volume create modaletta-cache

# Deploy MCP gateway
modal deploy src/modaletta/mcp/gateway.py

# Note the URL and configure in Letta tools
```

---

## Future MCP Servers

- **embeddings**: Generate embeddings using Modal GPU
- **image**: Image processing (resize, OCR, describe)
- **pdf**: PDF parsing and extraction
- **database**: SQLite/DuckDB queries on volume data
- **git**: Clone and browse repositories
