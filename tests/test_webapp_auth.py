"""Comprehensive tests for OAuth authentication module."""

import os
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def oauth_env_vars():
    """Set up OAuth environment variables for testing."""
    env = {
        "GOOGLE_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
        "GOOGLE_CLIENT_SECRET": "test-client-secret",
        "JWT_SECRET": "test-jwt-secret-key-for-testing-only",
        "JWT_EXPIRATION_HOURS": "24",
    }
    with patch.dict(os.environ, env, clear=False):
        yield env


@pytest.fixture
def oauth_config(oauth_env_vars):
    """Create OAuth config for testing."""
    from modaletta.webapp.auth import OAuthConfig
    return OAuthConfig.from_env()


@pytest.fixture
def sample_user_info():
    """Sample authenticated user info."""
    from modaletta.webapp.auth import UserInfo
    return UserInfo(
        id="123456789",
        email="test@example.com",
        name="Test User",
        picture="https://example.com/avatar.jpg",
        email_verified=True,
    )


@pytest.fixture
def app_with_auth(oauth_env_vars):
    """Create FastAPI app with auth routes for testing."""
    from modaletta.webapp.auth import create_auth_router
    
    app = FastAPI()
    router = create_auth_router()
    app.include_router(router)
    return app


@pytest.fixture
def client_with_auth(app_with_auth):
    """Test client with auth routes."""
    return TestClient(app_with_auth)


# =============================================================================
# OAuthConfig Tests
# =============================================================================


class TestOAuthConfig:
    """Tests for OAuthConfig class."""

    def test_from_env_success(self, oauth_env_vars):
        """Test loading config from environment variables."""
        from modaletta.webapp.auth import OAuthConfig
        
        config = OAuthConfig.from_env()
        
        assert config.google_client_id == "test-client-id.apps.googleusercontent.com"
        assert config.google_client_secret == "test-client-secret"
        assert config.jwt_secret == "test-jwt-secret-key-for-testing-only"
        assert config.jwt_expiration_hours == 24
        assert config.jwt_algorithm == "HS256"

    def test_from_env_missing_client_id(self):
        """Test error when GOOGLE_CLIENT_ID is missing."""
        from modaletta.webapp.auth import OAuthConfig
        
        with patch.dict(os.environ, {"GOOGLE_CLIENT_SECRET": "secret"}, clear=True):
            with pytest.raises(ValueError, match="GOOGLE_CLIENT_ID"):
                OAuthConfig.from_env()

    def test_from_env_missing_client_secret(self):
        """Test error when GOOGLE_CLIENT_SECRET is missing."""
        from modaletta.webapp.auth import OAuthConfig
        
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "id"}, clear=True):
            with pytest.raises(ValueError, match="GOOGLE_CLIENT_SECRET"):
                OAuthConfig.from_env()

    def test_from_env_generates_jwt_secret(self, oauth_env_vars):
        """Test that JWT_SECRET is generated if not provided."""
        from modaletta.webapp.auth import OAuthConfig
        
        env_without_jwt = {k: v for k, v in oauth_env_vars.items() if k != "JWT_SECRET"}
        with patch.dict(os.environ, env_without_jwt, clear=True):
            config = OAuthConfig.from_env()
            assert config.jwt_secret is not None
            assert len(config.jwt_secret) > 20  # Generated secret should be substantial


# =============================================================================
# JWT Token Tests
# =============================================================================


class TestJWTTokens:
    """Tests for JWT token creation and validation."""

    def test_create_jwt_token(self, oauth_config, sample_user_info):
        """Test creating a JWT token."""
        from modaletta.webapp.auth import create_jwt_token
        
        token = create_jwt_token(sample_user_info, oauth_config)
        
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are fairly long
        assert token.count('.') == 2  # JWTs have 3 parts separated by dots

    def test_decode_jwt_token_success(self, oauth_config, sample_user_info):
        """Test decoding a valid JWT token."""
        from modaletta.webapp.auth import create_jwt_token, decode_jwt_token
        
        token = create_jwt_token(sample_user_info, oauth_config)
        decoded = decode_jwt_token(token, oauth_config)
        
        assert decoded is not None
        assert decoded.sub == sample_user_info.id
        assert decoded.email == sample_user_info.email
        assert decoded.name == sample_user_info.name
        assert decoded.picture == sample_user_info.picture

    def test_decode_jwt_token_expired(self, oauth_config, sample_user_info):
        """Test that expired tokens are rejected."""
        import jwt
        from modaletta.webapp.auth import decode_jwt_token
        
        # Create an already-expired token
        now = datetime.now(timezone.utc)
        payload = {
            "sub": sample_user_info.id,
            "email": sample_user_info.email,
            "exp": now - timedelta(hours=1),  # Expired 1 hour ago
            "iat": now - timedelta(hours=2),
        }
        expired_token = jwt.encode(payload, oauth_config.jwt_secret, algorithm="HS256")
        
        decoded = decode_jwt_token(expired_token, oauth_config)
        assert decoded is None

    def test_decode_jwt_token_invalid_signature(self, oauth_config, sample_user_info):
        """Test that tokens with invalid signatures are rejected."""
        from modaletta.webapp.auth import create_jwt_token, decode_jwt_token
        
        token = create_jwt_token(sample_user_info, oauth_config)
        
        # Create config with different secret
        other_config = oauth_config.model_copy(update={"jwt_secret": "different-secret"})
        
        decoded = decode_jwt_token(token, other_config)
        assert decoded is None

    def test_decode_jwt_token_malformed(self, oauth_config):
        """Test that malformed tokens are rejected."""
        from modaletta.webapp.auth import decode_jwt_token
        
        assert decode_jwt_token("not-a-jwt", oauth_config) is None
        assert decode_jwt_token("", oauth_config) is None
        assert decode_jwt_token("a.b", oauth_config) is None


# =============================================================================
# Google OAuth URL Tests
# =============================================================================


class TestGoogleOAuthURL:
    """Tests for Google OAuth URL generation."""

    def test_get_google_auth_url(self, oauth_config):
        """Test generating Google OAuth authorization URL."""
        from modaletta.webapp.auth import get_google_auth_url
        
        redirect_uri = "http://localhost:8000/auth/callback"
        state = "test-state-123"
        
        url = get_google_auth_url(oauth_config, redirect_uri, state)
        
        assert "accounts.google.com" in url
        assert "client_id=test-client-id.apps.googleusercontent.com" in url
        assert f"state={state}" in url
        assert "redirect_uri=" in url
        assert "scope=" in url
        assert "openid" in url
        assert "email" in url
        assert "profile" in url


# =============================================================================
# OAuth State Management Tests
# =============================================================================


class TestOAuthStateManagement:
    """Tests for OAuth state generation and validation."""

    def test_generate_oauth_state(self):
        """Test generating OAuth state."""
        from modaletta.webapp.auth import generate_oauth_state
        
        state1 = generate_oauth_state()
        state2 = generate_oauth_state()
        
        # States should be unique
        assert state1 != state2
        # States should be reasonably long
        assert len(state1) > 20

    def test_validate_oauth_state_success(self):
        """Test validating a valid OAuth state."""
        from modaletta.webapp.auth import generate_oauth_state, validate_oauth_state
        
        state = generate_oauth_state()
        
        # First validation should succeed
        assert validate_oauth_state(state) is True
        
        # Second validation should fail (state is consumed)
        assert validate_oauth_state(state) is False

    def test_validate_oauth_state_invalid(self):
        """Test validating an invalid OAuth state."""
        from modaletta.webapp.auth import validate_oauth_state
        
        assert validate_oauth_state("invalid-state") is False
        assert validate_oauth_state("") is False


# =============================================================================
# Token Extraction Tests
# =============================================================================


class TestTokenExtraction:
    """Tests for extracting tokens from requests."""

    def test_get_token_from_cookie(self, app_with_auth):
        """Test extracting token from cookie."""
        from modaletta.webapp.auth import get_token_from_request
        
        # Create a mock request with a cookie
        mock_request = Mock()
        mock_request.cookies = {"modaletta_auth": "test-token-from-cookie"}
        mock_request.headers = {}
        
        token = get_token_from_request(mock_request)
        assert token == "test-token-from-cookie"

    def test_get_token_from_header(self, app_with_auth):
        """Test extracting token from Authorization header."""
        from modaletta.webapp.auth import get_token_from_request
        
        mock_request = Mock()
        mock_request.cookies = {}
        mock_request.headers = {"Authorization": "Bearer test-token-from-header"}
        
        token = get_token_from_request(mock_request)
        assert token == "test-token-from-header"

    def test_get_token_cookie_priority(self, app_with_auth):
        """Test that cookie takes priority over header."""
        from modaletta.webapp.auth import get_token_from_request
        
        mock_request = Mock()
        mock_request.cookies = {"modaletta_auth": "cookie-token"}
        mock_request.headers = {"Authorization": "Bearer header-token"}
        
        token = get_token_from_request(mock_request)
        assert token == "cookie-token"

    def test_get_token_none(self, app_with_auth):
        """Test when no token is present."""
        from modaletta.webapp.auth import get_token_from_request
        
        mock_request = Mock()
        mock_request.cookies = {}
        mock_request.headers = {}
        
        token = get_token_from_request(mock_request)
        assert token is None


# =============================================================================
# Auth Router Endpoint Tests
# =============================================================================


class TestAuthRouterEndpoints:
    """Tests for auth router endpoints."""

    def test_login_redirects_to_google(self, client_with_auth):
        """Test that /auth/login redirects to Google."""
        response = client_with_auth.get("/auth/login", follow_redirects=False)
        
        assert response.status_code == 307  # Temporary redirect
        assert "accounts.google.com" in response.headers["location"]

    def test_logout_clears_cookie(self, client_with_auth):
        """Test that /auth/logout clears the auth cookie."""
        response = client_with_auth.get("/auth/logout", follow_redirects=False)
        
        assert response.status_code == 307
        # Cookie should be cleared (set to expire)
        assert "modaletta_auth" in response.headers.get("set-cookie", "")

    def test_status_unauthenticated(self, client_with_auth):
        """Test /auth/status when not authenticated."""
        response = client_with_auth.get("/auth/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["user"] is None

    def test_status_authenticated(self, client_with_auth, oauth_config, sample_user_info):
        """Test /auth/status when authenticated."""
        from modaletta.webapp.auth import create_jwt_token
        
        token = create_jwt_token(sample_user_info, oauth_config)
        
        response = client_with_auth.get(
            "/auth/status",
            cookies={"modaletta_auth": token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user"]["email"] == sample_user_info.email

    def test_me_requires_auth(self, client_with_auth):
        """Test that /auth/me requires authentication."""
        response = client_with_auth.get("/auth/me")
        
        assert response.status_code == 401

    def test_me_returns_user_info(self, client_with_auth, oauth_config, sample_user_info):
        """Test /auth/me returns user info when authenticated."""
        from modaletta.webapp.auth import create_jwt_token
        
        token = create_jwt_token(sample_user_info, oauth_config)
        
        response = client_with_auth.get(
            "/auth/me",
            cookies={"modaletta_auth": token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_user_info.id
        assert data["email"] == sample_user_info.email
        assert data["name"] == sample_user_info.name

    def test_callback_invalid_state(self, client_with_auth):
        """Test that callback rejects invalid state."""
        response = client_with_auth.get(
            "/auth/callback",
            params={"code": "test-code", "state": "invalid-state"},
            follow_redirects=False
        )
        
        assert response.status_code == 307
        assert "auth_error=invalid_state" in response.headers["location"]

    def test_callback_missing_params(self, client_with_auth):
        """Test that callback requires code and state."""
        response = client_with_auth.get(
            "/auth/callback",
            follow_redirects=False
        )
        
        assert response.status_code == 307
        assert "auth_error=missing_params" in response.headers["location"]

    def test_callback_oauth_error(self, client_with_auth):
        """Test that callback handles OAuth errors."""
        response = client_with_auth.get(
            "/auth/callback",
            params={"error": "access_denied"},
            follow_redirects=False
        )
        
        assert response.status_code == 307
        assert "auth_error=access_denied" in response.headers["location"]


# =============================================================================
# Token Exchange Tests (with mocked HTTP)
# =============================================================================


class TestTokenExchange:
    """Tests for token exchange with Google."""

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_success(self, oauth_config):
        """Test successful token exchange."""
        from modaletta.webapp.auth import exchange_code_for_tokens
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-access-token",
            "id_token": "test-id-token",
            "token_type": "Bearer",
        }
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            
            tokens = await exchange_code_for_tokens(
                "test-code",
                oauth_config,
                "http://localhost/callback"
            )
            
            assert tokens["access_token"] == "test-access-token"

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_failure(self, oauth_config):
        """Test token exchange failure."""
        from fastapi import HTTPException
        from modaletta.webapp.auth import exchange_code_for_tokens
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid code"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            
            with pytest.raises(HTTPException) as exc_info:
                await exchange_code_for_tokens(
                    "invalid-code",
                    oauth_config,
                    "http://localhost/callback"
                )
            
            assert exc_info.value.status_code == 401


# =============================================================================
# Google User Info Tests (with mocked HTTP)
# =============================================================================


class TestGoogleUserInfo:
    """Tests for fetching Google user info."""

    @pytest.mark.asyncio
    async def test_get_google_user_info_success(self):
        """Test successful user info fetch."""
        from modaletta.webapp.auth import get_google_user_info
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123",
            "email": "test@gmail.com",
            "name": "Test User",
            "picture": "https://example.com/pic.jpg",
            "verified_email": True,
        }
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            
            user_info = await get_google_user_info("test-token")
            
            assert user_info.id == "123"
            assert user_info.email == "test@gmail.com"
            assert user_info.email_verified is True

    @pytest.mark.asyncio
    async def test_get_google_user_info_failure(self):
        """Test user info fetch failure."""
        from fastapi import HTTPException
        from modaletta.webapp.auth import get_google_user_info
        
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid token"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            
            with pytest.raises(HTTPException) as exc_info:
                await get_google_user_info("invalid-token")
            
            assert exc_info.value.status_code == 401


# =============================================================================
# Cookie Handling Tests
# =============================================================================


class TestCookieHandling:
    """Tests for auth cookie management."""

    def test_set_auth_cookie(self):
        """Test setting auth cookie on response."""
        from modaletta.webapp.auth import set_auth_cookie
        
        mock_response = Mock()
        set_auth_cookie(mock_response, "test-token", max_age_hours=12)
        
        mock_response.set_cookie.assert_called_once()
        call_kwargs = mock_response.set_cookie.call_args[1]
        
        assert call_kwargs["key"] == "modaletta_auth"
        assert call_kwargs["value"] == "test-token"
        assert call_kwargs["max_age"] == 12 * 3600
        assert call_kwargs["httponly"] is True
        assert call_kwargs["secure"] is True
        assert call_kwargs["samesite"] == "lax"

    def test_clear_auth_cookie(self):
        """Test clearing auth cookie."""
        from modaletta.webapp.auth import clear_auth_cookie
        
        mock_response = Mock()
        clear_auth_cookie(mock_response)
        
        mock_response.delete_cookie.assert_called_once_with(key="modaletta_auth")


# =============================================================================
# Integration Tests
# =============================================================================


class TestAuthIntegration:
    """Integration tests for complete auth flows."""

    def test_full_auth_flow_simulation(self, oauth_config, sample_user_info):
        """Simulate a complete authentication flow."""
        from modaletta.webapp.auth import (
            create_jwt_token,
            decode_jwt_token,
            generate_oauth_state,
            get_google_auth_url,
            validate_oauth_state,
        )
        
        # Step 1: Generate state and auth URL
        state = generate_oauth_state()
        redirect_uri = "http://localhost:8000/auth/callback"
        auth_url = get_google_auth_url(oauth_config, redirect_uri, state)
        
        assert "accounts.google.com" in auth_url
        assert state in auth_url
        
        # Step 2: Validate state (simulating callback)
        assert validate_oauth_state(state) is True
        
        # Step 3: Create JWT for user (simulating after Google token exchange)
        token = create_jwt_token(sample_user_info, oauth_config)
        
        # Step 4: Decode and verify token
        decoded = decode_jwt_token(token, oauth_config)
        assert decoded is not None
        assert decoded.email == sample_user_info.email
        
        # Step 5: Verify token hasn't expired
        assert decoded.exp > datetime.now(timezone.utc)
