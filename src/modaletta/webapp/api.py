"""Modaletta Web Chat API - FastAPI endpoints served via Modal."""

import logging
import time
from pathlib import Path
from typing import Any

import modal
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Configure logging to show in Modal logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("modaletta.webapp")

# Modal app configuration
app = modal.App("modaletta-webapp")

# Build image with dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    [
        "letta-client",
        "pydantic>=2.0.0",
        "python-dotenv",
        "fastapi",
        "pyjwt>=2.0.0",  # For JWT token handling
        "httpx>=0.24.0",  # For OAuth HTTP requests
        "pyyaml>=6.0",  # For authorized users YAML config
    ]
)

# Add modaletta source code to the container
image = image.add_local_python_source("modaletta")

# Add frontend assets to container
frontend_path = Path(__file__).parent / "frontend"
image = image.add_local_dir(frontend_path, remote_path="/assets")

# Add authorized users config if it exists
authorized_users_path = Path(__file__).parent / "authorized_users.yaml"
_has_authorized_users_file = authorized_users_path.exists()
if _has_authorized_users_file:
    image = image.add_local_file(
        authorized_users_path, 
        remote_path="/app/authorized_users.yaml"
    )


# Request/Response models
class UserMetadata(BaseModel):
    """Context metadata from the client (device, time, etc). User info comes from JWT."""
    
    local_time: str | None = None
    local_date: str | None = None
    timezone: str | None = None
    device_type: str | None = None
    platform: str | None = None
    language: str | None = None


class SendMessageRequest(BaseModel):
    """Request body for sending a message to an agent."""

    agent_id: str
    message: str
    role: str = "user"
    project_id: str | None = None
    metadata: UserMetadata | None = None
    include_debug: bool = False  # Include tool calls, reasoning, etc.


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    messages: list[dict[str, Any]]
    include_debug: bool = False  # Whether debug messages should be shown


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


# =============================================================================
# Authentication Setup (Optional - only enabled if OAuth credentials are set)
# =============================================================================

def is_auth_enabled() -> bool:
    """Check if OAuth authentication is configured."""
    import os
    return bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET"))


def setup_auth_routes(app: FastAPI) -> None:
    """Set up authentication routes. Routes are always registered but may return errors if not configured."""
    from modaletta.webapp.auth import create_auth_router
    auth_router = create_auth_router()
    app.include_router(auth_router)
    if is_auth_enabled():
        logger.info("OAuth authentication enabled")
    else:
        logger.info("OAuth routes registered but credentials not configured")


def setup_auth_middleware(app: FastAPI) -> None:
    """Set up middleware to protect routes when auth is enabled."""
    if not is_auth_enabled():
        return
    
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import RedirectResponse, JSONResponse
    from modaletta.webapp.auth import get_token_from_request, decode_jwt_token, OAuthConfig
    from modaletta.webapp.authorization import get_authorization_provider, configure_authorization_from_env
    
    # Configure authorization on startup
    configure_authorization_from_env()
    
    # Routes that don't require authentication
    PUBLIC_PATHS = {
        "/auth/login",
        "/auth/callback", 
        "/auth/logout",
        "/auth/status",
        "/api/health",
    }
    
    class AuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            path = request.url.path
            
            # Allow public paths
            if path in PUBLIC_PATHS or path.startswith("/auth/"):
                return await call_next(request)
            
            # Allow login page
            if path == "/login.html":
                return await call_next(request)
            
            # Allow unauthorized page (so users can see it after failed auth)
            if path == "/unauthorized.html":
                return await call_next(request)
            
            # Check authentication
            token = get_token_from_request(request)
            if token:
                try:
                    config = OAuthConfig.from_env()
                    token_data = decode_jwt_token(token, config)
                    if token_data:
                        # Valid token - now check authorization
                        auth_provider = get_authorization_provider()
                        if auth_provider.is_authorized(token_data.email):
                            # Authorized - allow request
                            return await call_next(request)
                        else:
                            # Authenticated but not authorized
                            logger.warning(f"Unauthorized access attempt by {token_data.email}")
                            if path.startswith("/api/"):
                                return JSONResponse(
                                    {"detail": "User is not authorized to access this application"},
                                    status_code=403
                                )
                            else:
                                # Redirect to unauthorized page
                                from urllib.parse import quote
                                return RedirectResponse(url=f"/unauthorized.html?email={quote(token_data.email, safe='')}")
                except Exception as e:
                    logger.error(f"Auth middleware error: {e}")
            
            # Not authenticated - redirect to login page for browser requests, 401 for API
            if path.startswith("/api/"):
                return JSONResponse(
                    {"detail": "Authentication required"},
                    status_code=401
                )
            else:
                return RedirectResponse(url="/login.html")
    
    app.add_middleware(AuthMiddleware)
    logger.info("Auth middleware enabled - routes are protected")


# Set up auth routes and middleware
# Always register auth routes (they handle missing credentials gracefully)
# Middleware is only set up if credentials are present
from modaletta.webapp.auth import create_auth_router
_auth_router = create_auth_router()
web_app.include_router(_auth_router)
logger.info("Auth routes registered")


# =============================================================================
# API Endpoints
# =============================================================================

@web_app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "auth_enabled": str(is_auth_enabled())}


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

    logger.info(f"list_agents called with project_id={project_id}")
    start_time = time.time()

    try:
        config = ModalettaConfig.from_env()
        logger.info(f"Config loaded: server_url={config.letta_server_url}, api_key={'*' * 8 if config.letta_api_key else 'None'}")

        client = ModalettaClient(config, project_id=project_id)
        logger.info("ModalettaClient created, calling list_agents...")

        agents = client.list_agents()
        elapsed = time.time() - start_time
        logger.info(f"list_agents returned {len(agents)} agents in {elapsed:.2f}s")

        # Return simplified agent info
        result = [
            {
                "id": agent.get("id"),
                "name": agent.get("name"),
                "created_at": agent.get("created_at"),
            }
            for agent in agents
        ]
        logger.info(f"Returning agents: {[a['name'] for a in result]}")
        return result

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"list_agents failed after {elapsed:.2f}s: {type(e).__name__}: {e}")
        raise


def format_message_with_user_and_context(
    message: str,
    user_email: str | None,
    user_name: str | None,
    metadata: UserMetadata | None
) -> str:
    """Format a message with user (from JWT) and context (from client) as JSON.
    
    User info comes from the server-side JWT token (secure).
    Context info comes from the client (device, time, etc).
    """
    import json
    
    enriched: dict[str, Any] = {"message": message}
    
    # Add user info from JWT token (server-verified)
    if user_email or user_name:
        enriched["user"] = {}
        if user_email:
            enriched["user"]["email"] = user_email
        if user_name:
            enriched["user"]["name"] = user_name
    
    # Add context from client metadata
    if metadata:
        context = {}
        if metadata.local_time:
            context["local_time"] = metadata.local_time
        if metadata.local_date:
            context["local_date"] = metadata.local_date
        if metadata.timezone:
            context["timezone"] = metadata.timezone
        if metadata.device_type:
            context["device_type"] = metadata.device_type
        if metadata.platform:
            context["platform"] = metadata.platform
        if metadata.language:
            context["language"] = metadata.language
        if context:
            enriched["context"] = context
    
    return json.dumps(enriched)


@web_app.post("/api/chat")
async def send_message(request: SendMessageRequest, http_request: Request) -> ChatResponse:
    """Send a message to an agent and return the response."""
    from modaletta.client import ModalettaClient
    from modaletta.config import ModalettaConfig
    from modaletta.webapp.auth import get_token_from_request, decode_jwt_token, OAuthConfig

    logger.info(f"send_message called: agent_id={request.agent_id}, project_id={request.project_id}, message_len={len(request.message)}")
    start_time = time.time()

    try:
        config = ModalettaConfig.from_env()
        client = ModalettaClient(config, project_id=request.project_id)
        
        # Extract user info from JWT token (server-side, secure)
        user_email = None
        user_name = None
        token = get_token_from_request(http_request)
        if token:
            try:
                oauth_config = OAuthConfig.from_env()
                token_data = decode_jwt_token(token, oauth_config)
                if token_data:
                    user_email = token_data.email
                    user_name = token_data.name
                    logger.info(f"User from token: {user_email}")
            except Exception as e:
                logger.warning(f"Could not decode token: {e}")
        
        # Format message with user (from token) and context (from client)
        formatted_message = format_message_with_user_and_context(
            message=request.message,
            user_email=user_email,
            user_name=user_name,
            metadata=request.metadata
        )
        logger.info(f"Formatted message: {formatted_message[:200]}...")
        logger.info(f"Sending enriched message to agent {request.agent_id}...")

        messages = client.send_message(
            agent_id=request.agent_id,
            message=formatted_message,
            role=request.role,
        )
        elapsed = time.time() - start_time
        logger.info(f"send_message returned {len(messages)} messages in {elapsed:.2f}s")

        # Log message types for debugging
        msg_types = [m.get("message_type", "unknown") for m in messages]
        logger.info(f"Message types: {msg_types}")

        return ChatResponse(messages=messages, include_debug=request.include_debug)

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"send_message failed after {elapsed:.2f}s: {type(e).__name__}: {e}")
        raise


class MessageHistoryResponse(BaseModel):
    """Response for message history endpoint."""
    
    messages: list[dict[str, Any]]
    has_more: bool
    oldest_id: str | None = None


@web_app.get("/api/agents/{agent_id}/messages")
async def get_message_history(
    agent_id: str,
    limit: int = 10,
    before: str | None = None,
    project_id: str | None = None,
) -> MessageHistoryResponse:
    """Get message history for an agent with pagination.
    
    Args:
        agent_id: The agent ID.
        limit: Maximum number of messages to return (default 10).
        before: Message ID cursor - return messages older than this ID.
        project_id: Optional project ID for multi-project setups.
    
    Returns:
        MessageHistoryResponse with messages, pagination info.
    """
    from modaletta.client import ModalettaClient
    from modaletta.config import ModalettaConfig

    logger.info(f"get_message_history called: agent_id={agent_id}, limit={limit}, before={before}")
    start_time = time.time()

    try:
        config = ModalettaConfig.from_env()
        client = ModalettaClient(config, project_id=project_id)

        # Request one extra to determine if there are more messages
        messages = client.get_messages(
            agent_id=agent_id,
            limit=limit + 1,
            before=before,
            order="desc",  # Newest first
        )
        
        # Debug: log what we got from Letta
        logger.info(f"Letta returned {len(messages)} messages")
        for i, msg in enumerate(messages[:3]):  # Log first 3
            logger.info(f"  Message {i}: type={msg.get('message_type')}, id={msg.get('id')}")
        
        # Check if there are more messages
        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]  # Trim to requested limit
        
        # Get the oldest message ID for pagination
        oldest_id = messages[-1].get("id") if messages else None
        
        elapsed = time.time() - start_time
        logger.info(f"get_message_history returned {len(messages)} messages in {elapsed:.2f}s")
        
        return MessageHistoryResponse(
            messages=messages,
            has_more=has_more,
            oldest_id=oldest_id,
        )

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"get_message_history failed after {elapsed:.2f}s: {type(e).__name__}: {e}")
        raise


@web_app.get("/api/agents/{agent_id}/memory")
async def get_agent_memory(agent_id: str, project_id: str | None = None) -> dict[str, Any]:
    """Get agent memory state."""
    from modaletta.client import ModalettaClient
    from modaletta.config import ModalettaConfig

    logger.info(f"get_agent_memory called: agent_id={agent_id}, project_id={project_id}")
    start_time = time.time()

    try:
        config = ModalettaConfig.from_env()
        client = ModalettaClient(config, project_id=project_id)

        memory = client.get_agent_memory(agent_id)
        elapsed = time.time() - start_time
        num_blocks = len(memory.get("memory_blocks", []))
        logger.info(f"get_agent_memory returned {num_blocks} blocks in {elapsed:.2f}s")
        return memory

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"get_agent_memory failed after {elapsed:.2f}s: {type(e).__name__}: {e}")
        raise


_middleware_initialized = False

# Modal function that serves the ASGI app
@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("letta-credentials"),
        modal.Secret.from_name("oauth-credentials"),
    ],
)
@modal.asgi_app()
def webapp() -> FastAPI:
    """Serve the web application."""
    global _middleware_initialized
    
    # Initialize auth middleware (only once, after Modal injects secrets)
    if not _middleware_initialized:
        setup_auth_middleware(web_app)
        _middleware_initialized = True
        logger.info("Auth middleware initialized")
    
    # Mount static files at root (must be done after API routes)
    web_app.mount("/", StaticFiles(directory="/assets", html=True), name="static")
    return web_app
