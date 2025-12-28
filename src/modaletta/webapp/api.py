"""Modaletta Web Chat API - FastAPI endpoints served via Modal."""

from pathlib import Path
from typing import Any

import modal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Modal app configuration
app = modal.App("modaletta-webapp")

# Build image with dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    [
        "letta-client",
        "pydantic>=2.0.0",
        "python-dotenv",
        "fastapi",
    ]
)

# Add modaletta source code to the container
image = image.add_local_python_source("modaletta")

# Add frontend assets to container
frontend_path = Path(__file__).parent / "frontend"
image = image.add_local_dir(frontend_path, remote_path="/assets")


# Request/Response models
class SendMessageRequest(BaseModel):
    """Request body for sending a message to an agent."""

    agent_id: str
    message: str
    role: str = "user"
    project_id: str | None = None


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    messages: list[dict[str, Any]]


# FastAPI app
web_app = FastAPI(title="Modaletta Chat", version="0.1.0")

# CORS for local development
web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@web_app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


class LogEntry(BaseModel):
    """A single log entry."""

    timestamp: str
    category: str
    message: str
    data: dict[str, Any] | None = None


class LogsRequest(BaseModel):
    """Request body for submitting logs."""

    logs: list[LogEntry]
    session_id: str | None = None


# Store logs in memory for this session (Modal containers are ephemeral)
# Also write to a file that can be retrieved
_debug_logs: list[dict[str, Any]] = []


@web_app.post("/api/logs")
async def submit_logs(request: LogsRequest) -> dict[str, str]:
    """Receive debug logs from the frontend."""
    import json
    from datetime import datetime

    # Add to in-memory store
    for log in request.logs:
        _debug_logs.append(log.model_dump())

    # Also write to file
    log_file = "/tmp/voice-debug-logs.jsonl"
    with open(log_file, "a") as f:
        for log in request.logs:
            entry = {
                "received_at": datetime.utcnow().isoformat(),
                "session_id": request.session_id,
                **log.model_dump(),
            }
            f.write(json.dumps(entry) + "\n")

    return {"status": "ok", "count": str(len(request.logs))}


@web_app.get("/api/logs")
async def get_logs() -> list[dict[str, Any]]:
    """Retrieve stored debug logs."""
    return _debug_logs


@web_app.get("/api/logs/file")
async def get_log_file() -> dict[str, Any]:
    """Retrieve logs from file."""
    log_file = "/tmp/voice-debug-logs.jsonl"
    try:
        with open(log_file) as f:
            lines = f.readlines()
        return {"logs": [line.strip() for line in lines], "count": len(lines)}
    except FileNotFoundError:
        return {"logs": [], "count": 0}


@web_app.get("/api/config")
async def get_config() -> dict[str, Any]:
    """Get webapp configuration including default agent and project IDs."""
    import os

    return {
        "default_agent_id": os.environ.get("DEFAULT_AGENT_ID"),
        "default_project_id": os.environ.get("DEFAULT_PROJECT_ID"),
    }


@web_app.get("/api/agents")
async def list_agents(project_id: str | None = None) -> list[dict[str, Any]]:
    """List all available agents."""
    from modaletta.client import ModalettaClient
    from modaletta.config import ModalettaConfig

    config = ModalettaConfig.from_env()
    client = ModalettaClient(config, project_id=project_id)
    agents = client.list_agents()

    # Return simplified agent info
    return [
        {
            "id": agent.get("id"),
            "name": agent.get("name"),
            "created_at": agent.get("created_at"),
        }
        for agent in agents
    ]


@web_app.post("/api/chat")
async def send_message(request: SendMessageRequest) -> ChatResponse:
    """Send a message to an agent and return the response."""
    from modaletta.client import ModalettaClient
    from modaletta.config import ModalettaConfig

    config = ModalettaConfig.from_env()
    client = ModalettaClient(config, project_id=request.project_id)
    messages = client.send_message(
        agent_id=request.agent_id,
        message=request.message,
        role=request.role,
    )
    return ChatResponse(messages=messages)


@web_app.get("/api/agents/{agent_id}/memory")
async def get_agent_memory(agent_id: str, project_id: str | None = None) -> dict[str, Any]:
    """Get agent memory state."""
    from modaletta.client import ModalettaClient
    from modaletta.config import ModalettaConfig

    config = ModalettaConfig.from_env()
    client = ModalettaClient(config, project_id=project_id)
    return client.get_agent_memory(agent_id)


# Modal function that serves the ASGI app
@app.function(
    image=image,
    secrets=[modal.Secret.from_name("letta-credentials")],
)
@modal.asgi_app()
def webapp() -> FastAPI:
    """Serve the web application."""
    # Mount static files at root (must be done after API routes)
    web_app.mount("/", StaticFiles(directory="/assets", html=True), name="static")
    return web_app
