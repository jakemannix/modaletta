# OAuth Authentication Setup Guide

This guide explains how to set up Google OAuth authentication for the Modaletta webapp.

## Overview

The webapp supports optional Google OAuth authentication. When enabled:
- Users can sign in with their Google account
- A JWT token is stored in an HTTP-only cookie
- Protected endpoints require authentication
- User info (email, name, avatar) is displayed in the UI

When OAuth is not configured, the webapp works without authentication.

## Setup Steps

### 1. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. Navigate to **APIs & Services → Credentials**
4. Click **+ CREATE CREDENTIALS → OAuth client ID**

#### Configure OAuth Consent Screen (if prompted)
- User Type: **External**
- App name: `Modaletta` (or your preferred name)
- User support email: your email
- Developer contact: your email
- Scopes: defaults (email, profile, openid)
- Test users: add your Google email
- Keep in **Testing** mode (don't publish)

#### Create OAuth Client ID
- Application type: **Web application**
- Name: `Modaletta Web`
- Authorized redirect URIs:
  ```
  http://localhost:8000/auth/callback
  https://YOUR-MODAL-APP-URL/auth/callback
  ```
  (Add the Modal URL after first deployment)

5. Copy the **Client ID** and **Client Secret**

### 2. Create Modal Secret

Create a Modal secret named `oauth-credentials` with your OAuth credentials:

```bash
modal secret create oauth-credentials \
  GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com" \
  GOOGLE_CLIENT_SECRET="GOCSPX-your-secret" \
  JWT_SECRET="your-random-secret-key-at-least-32-chars"
```

**Note**: `JWT_SECRET` is optional - if not provided, a random one is generated on each deployment (sessions won't persist across restarts).

### 3. Deploy the Webapp

```bash
modal deploy src/modaletta/webapp/api.py
```

After deployment, note the URL (e.g., `https://your-username--modaletta-webapp-webapp.modal.run`).

### 4. Add Redirect URI to Google

Go back to Google Cloud Console and add the deployed URL to Authorized redirect URIs:
```
https://your-username--modaletta-webapp-webapp.modal.run/auth/callback
```

## Testing

### Run Unit Tests

```bash
uv sync --all-extras
uv run pytest tests/test_webapp_auth.py -v
```

### Test Locally with Modal

```bash
# Serve locally (uses Modal secrets)
modal serve src/modaletta/webapp/api.py

# Open in browser and test:
# 1. Click "Sign in with Google"
# 2. Complete Google OAuth flow
# 3. Verify you're redirected back and see your name/avatar
# 4. Click "Logout" to sign out
```

### Test Auth Endpoints Directly

```bash
# Check auth status (unauthenticated)
curl https://YOUR-APP-URL/auth/status
# Returns: {"authenticated": false, "user": null}

# After logging in via browser, check status with cookie
curl -b "modaletta_auth=YOUR-JWT-TOKEN" https://YOUR-APP-URL/auth/status
# Returns: {"authenticated": true, "user": {...}}

# Get current user info (requires auth)
curl -b "modaletta_auth=YOUR-JWT-TOKEN" https://YOUR-APP-URL/auth/me
# Returns: {"id": "...", "email": "...", "name": "...", "picture": "..."}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth client secret |
| `JWT_SECRET` | No | Secret for signing JWTs (auto-generated if not set) |
| `JWT_EXPIRATION_HOURS` | No | Token expiration in hours (default: 24) |
| `OAUTH_REDIRECT_URI` | No | Override redirect URI (auto-detected if not set) |
| `AUTHORIZED_USERS` | No | Comma-separated list of authorized email addresses |
| `AUTHORIZED_USERS_FILE` | No | Path to YAML file containing authorized users |

## Authorization (Restricting Access)

By default, all authenticated Google users can access the app. To restrict access to specific users:

### Option 1: Environment Variable (simplest)

Add to your Modal secret:
```bash
modal secret create oauth-credentials \
  GOOGLE_CLIENT_ID="..." \
  GOOGLE_CLIENT_SECRET="..." \
  JWT_SECRET="..." \
  AUTHORIZED_USERS="alice@gmail.com,bob@gmail.com"
```

### Option 2: YAML File (more maintainable)

1. Create `authorized_users.yaml`:
```yaml
authorized_users:
  - alice@gmail.com
  - bob@gmail.com
  - charlie@example.com
```

2. Add to Modal image and set env var:
```python
# In api.py, add file to image:
image = image.add_local_file("authorized_users.yaml", "/app/authorized_users.yaml")

# Set AUTHORIZED_USERS_FILE in Modal secret:
AUTHORIZED_USERS_FILE="/app/authorized_users.yaml"
```

### Behavior

- **Authenticated + Authorized**: Access granted
- **Authenticated + Not Authorized**: 403 Forbidden with message
- **Not Authenticated**: Redirect to Google login

### Future Backends

The authorization system uses a clean abstraction (`AuthorizationProvider`) that can be swapped out for:
- Database (SQLite, PostgreSQL)
- Cloud services (Firebase, Auth0)
- API calls to external service
- Role-based access control (RBAC)

See `authorization.py` for implementation details.

## Auth Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | GET | Redirects to Google OAuth |
| `/auth/callback` | GET | Handles OAuth callback, sets JWT cookie |
| `/auth/logout` | GET | Clears auth cookie, redirects to home |
| `/auth/me` | GET | Returns current user info (requires auth) |
| `/auth/status` | GET | Returns auth status (works authenticated or not) |

## Protecting Endpoints

To require authentication for an endpoint:

```python
from modaletta.webapp.auth import require_auth, UserInfo

@app.get("/api/protected")
async def protected_endpoint(user: UserInfo = Depends(require_auth)):
    return {"message": f"Hello, {user.email}!"}
```

To optionally get user info (None if not authenticated):

```python
from modaletta.webapp.auth import get_current_user, UserInfo

@app.get("/api/optional-auth")
async def optional_auth_endpoint(user: UserInfo | None = Depends(get_current_user)):
    if user:
        return {"message": f"Hello, {user.email}!"}
    return {"message": "Hello, anonymous!"}
```

## Troubleshooting

### "OAuth authentication disabled" in logs
- Check that `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set
- Verify the `oauth-credentials` Modal secret exists

### "Invalid OAuth state" error
- OAuth state expired (>10 minutes) - try logging in again
- Multiple login attempts - only one state is valid at a time

### "Failed to exchange authorization code"
- Check that the redirect URI matches exactly in Google Console
- Verify client secret is correct

### JWT token not persisting across restarts
- Set a fixed `JWT_SECRET` in your Modal secret
- Without it, a random secret is generated each deployment

## Security Notes

1. **JWT tokens** are stored in HTTP-only, secure, same-site cookies
2. **OAuth state** is validated to prevent CSRF attacks
3. **Tokens expire** after 24 hours by default
4. Keep OAuth credentials secret - never commit them to git
5. In production, always use HTTPS (Modal provides this automatically)
