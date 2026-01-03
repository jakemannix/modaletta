"""OAuth authentication module for Modaletta webapp.

Provides Google OAuth 2.0 authentication with JWT session tokens.
"""

import os
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

logger = logging.getLogger("modaletta.webapp.auth")

# =============================================================================
# Configuration
# =============================================================================


class OAuthConfig(BaseModel):
    """OAuth configuration loaded from environment variables."""

    google_client_id: str
    google_client_secret: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    redirect_uri: Optional[str] = None  # Auto-detected if not set

    @classmethod
    def from_env(cls) -> "OAuthConfig":
        """Load OAuth configuration from environment variables."""
        google_client_id = os.environ.get("GOOGLE_CLIENT_ID")
        google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        jwt_secret = os.environ.get("JWT_SECRET")

        if not google_client_id:
            raise ValueError("GOOGLE_CLIENT_ID environment variable is required")
        if not google_client_secret:
            raise ValueError("GOOGLE_CLIENT_SECRET environment variable is required")
        if not jwt_secret:
            # Generate a random secret if not provided (not recommended for production)
            logger.warning("JWT_SECRET not set, generating random secret. Sessions won't persist across restarts.")
            jwt_secret = secrets.token_urlsafe(32)

        return cls(
            google_client_id=google_client_id,
            google_client_secret=google_client_secret,
            jwt_secret=jwt_secret,
            jwt_expiration_hours=int(os.environ.get("JWT_EXPIRATION_HOURS", "24")),
            redirect_uri=os.environ.get("OAUTH_REDIRECT_URI"),
        )


# =============================================================================
# JWT Token Handling
# =============================================================================


class UserInfo(BaseModel):
    """Authenticated user information."""

    id: str  # Google user ID
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: bool = False


class TokenData(BaseModel):
    """Data stored in JWT token."""

    sub: str  # Subject (user ID)
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    exp: datetime
    iat: datetime


def create_jwt_token(user_info: UserInfo, config: OAuthConfig) -> str:
    """Create a JWT token for an authenticated user.
    
    Args:
        user_info: Authenticated user information from Google.
        config: OAuth configuration.
        
    Returns:
        Encoded JWT token string.
    """
    # Import here to avoid issues if PyJWT not installed
    import jwt

    now = datetime.now(timezone.utc)
    expiration = now + timedelta(hours=config.jwt_expiration_hours)

    payload = {
        "sub": user_info.id,
        "email": user_info.email,
        "name": user_info.name,
        "picture": user_info.picture,
        "exp": expiration,
        "iat": now,
    }

    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)


def decode_jwt_token(token: str, config: OAuthConfig) -> Optional[TokenData]:
    """Decode and validate a JWT token.
    
    Args:
        token: JWT token string.
        config: OAuth configuration.
        
    Returns:
        TokenData if valid, None if invalid or expired.
    """
    import jwt

    try:
        payload = jwt.decode(
            token,
            config.jwt_secret,
            algorithms=[config.jwt_algorithm],
        )
        return TokenData(
            sub=payload["sub"],
            email=payload["email"],
            name=payload.get("name"),
            picture=payload.get("picture"),
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
        )
    except jwt.ExpiredSignatureError:
        logger.debug("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid JWT token: {e}")
        return None


# =============================================================================
# Google OAuth Flow
# =============================================================================

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def get_google_auth_url(config: OAuthConfig, redirect_uri: str, state: str) -> str:
    """Generate Google OAuth authorization URL.
    
    Args:
        config: OAuth configuration.
        redirect_uri: Callback URL after authentication.
        state: Random state for CSRF protection.
        
    Returns:
        Authorization URL to redirect user to.
    """
    params = {
        "client_id": config.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(
    code: str,
    config: OAuthConfig,
    redirect_uri: str,
) -> dict[str, Any]:
    """Exchange authorization code for access tokens.
    
    Args:
        code: Authorization code from Google callback.
        config: OAuth configuration.
        redirect_uri: Same redirect URI used in authorization request.
        
    Returns:
        Token response containing access_token, id_token, etc.
        
    Raises:
        HTTPException: If token exchange fails.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": config.google_client_id,
                "client_secret": config.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )

        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to exchange authorization code",
            )

        return response.json()


async def get_google_user_info(access_token: str) -> UserInfo:
    """Fetch user information from Google using access token.
    
    Args:
        access_token: Google access token.
        
    Returns:
        UserInfo with user's Google profile data.
        
    Raises:
        HTTPException: If fetching user info fails.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code != 200:
            logger.error(f"Failed to fetch user info: {response.text}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to fetch user information",
            )

        data = response.json()
        return UserInfo(
            id=data["id"],
            email=data["email"],
            name=data.get("name"),
            picture=data.get("picture"),
            email_verified=data.get("verified_email", False),
        )


# =============================================================================
# FastAPI Dependencies
# =============================================================================

# Cookie name for storing JWT token
AUTH_COOKIE_NAME = "modaletta_auth"

# In-memory state storage for CSRF protection
# In production, use Redis or similar
_oauth_states: dict[str, datetime] = {}


def generate_oauth_state() -> str:
    """Generate and store a random OAuth state for CSRF protection."""
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = datetime.now(timezone.utc)
    # Clean up old states (older than 10 minutes)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    expired = [s for s, t in _oauth_states.items() if t < cutoff]
    for s in expired:
        _oauth_states.pop(s, None)
    return state


def validate_oauth_state(state: str) -> bool:
    """Validate and consume an OAuth state."""
    if state in _oauth_states:
        del _oauth_states[state]
        return True
    return False


def get_token_from_request(request: Request) -> Optional[str]:
    """Extract JWT token from request (cookie or Authorization header).
    
    Args:
        request: FastAPI request object.
        
    Returns:
        JWT token string if found, None otherwise.
    """
    # Try cookie first
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if token:
        return token

    # Try Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]

    return None


def get_oauth_config() -> OAuthConfig:
    """Dependency to get OAuth configuration."""
    return OAuthConfig.from_env()


async def get_current_user(
    request: Request,
    config: OAuthConfig = Depends(get_oauth_config),
) -> Optional[UserInfo]:
    """Dependency to get current authenticated user (optional).
    
    Returns None if not authenticated instead of raising an exception.
    """
    token = get_token_from_request(request)
    if not token:
        return None

    token_data = decode_jwt_token(token, config)
    if not token_data:
        return None

    return UserInfo(
        id=token_data.sub,
        email=token_data.email,
        name=token_data.name,
        picture=token_data.picture,
        email_verified=True,  # Assume verified if we have a valid token
    )


async def require_auth(
    request: Request,
    config: OAuthConfig = Depends(get_oauth_config),
) -> UserInfo:
    """Dependency that requires authentication.
    
    Raises HTTPException if not authenticated.
    """
    user = await get_current_user(request, config)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def set_auth_cookie(response: Response, token: str, max_age_hours: int = 24) -> None:
    """Set authentication cookie on response.
    
    Args:
        response: FastAPI response object.
        token: JWT token to store.
        max_age_hours: Cookie expiration in hours.
    """
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=max_age_hours * 3600,
        httponly=True,
        secure=True,  # Only send over HTTPS
        samesite="lax",
    )


def clear_auth_cookie(response: Response) -> None:
    """Clear authentication cookie."""
    response.delete_cookie(key=AUTH_COOKIE_NAME)


# =============================================================================
# Auth Router Factory
# =============================================================================


def create_auth_router():
    """Create FastAPI router with OAuth endpoints.
    
    Returns:
        APIRouter with /auth/* endpoints.
    """
    from fastapi import APIRouter

    router = APIRouter(prefix="/auth", tags=["authentication"])

    @router.get("/login")
    async def login(request: Request, config: OAuthConfig = Depends(get_oauth_config)):
        """Initiate Google OAuth login flow."""
        # Determine redirect URI
        redirect_uri = config.redirect_uri
        if not redirect_uri:
            # Auto-detect from request
            redirect_uri = str(request.url_for("auth_callback"))

        # Generate state for CSRF protection
        state = generate_oauth_state()

        # Store redirect URI in state for callback (simple approach)
        # In production, you might want to store this server-side
        auth_url = get_google_auth_url(config, redirect_uri, state)

        logger.info(f"Redirecting to Google OAuth: {auth_url[:100]}...")
        return RedirectResponse(url=auth_url)

    @router.get("/callback", name="auth_callback")
    async def auth_callback(
        request: Request,
        code: Optional[str] = None,
        state: Optional[str] = None,
        error: Optional[str] = None,
        config: OAuthConfig = Depends(get_oauth_config),
    ):
        """Handle Google OAuth callback."""
        # Check for errors
        if error:
            logger.error(f"OAuth error: {error}")
            from urllib.parse import quote
            return RedirectResponse(url="/?auth_error=" + quote(error, safe=""))

        if not code or not state:
            logger.error("Missing code or state in callback")
            return RedirectResponse(url="/?auth_error=missing_params")

        # Validate state
        if not validate_oauth_state(state):
            logger.error("Invalid OAuth state")
            return RedirectResponse(url="/?auth_error=invalid_state")

        # Determine redirect URI (must match what was used in login)
        redirect_uri = config.redirect_uri
        if not redirect_uri:
            redirect_uri = str(request.url_for("auth_callback"))

        try:
            # Exchange code for tokens
            tokens = await exchange_code_for_tokens(code, config, redirect_uri)

            # Get user info
            user_info = await get_google_user_info(tokens["access_token"])
            logger.info(f"User authenticated: {user_info.email}")

            # Create JWT token
            jwt_token = create_jwt_token(user_info, config)

            # Redirect to home with auth cookie
            response = RedirectResponse(url="/")
            set_auth_cookie(response, jwt_token, config.jwt_expiration_hours)
            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"OAuth callback error: {e}")
            return RedirectResponse(url="/?auth_error=callback_failed")

    @router.get("/logout")
    async def logout():
        """Log out and clear authentication."""
        response = RedirectResponse(url="/")
        clear_auth_cookie(response)
        return response

    @router.get("/me")
    async def get_current_user_info(user: UserInfo = Depends(require_auth)):
        """Get current authenticated user information."""
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
        }

    @router.get("/status")
    async def get_auth_status(user: Optional[UserInfo] = Depends(get_current_user)):
        """Check authentication status."""
        if user:
            return {
                "authenticated": True,
                "user": {
                    "email": user.email,
                    "name": user.name,
                    "picture": user.picture,
                },
            }
        return {"authenticated": False, "user": None}

    return router
