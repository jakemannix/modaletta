"""Authorization providers for controlling access to the webapp.

This module provides a clean abstraction for authorization that can be
swapped out for different backends (YAML file, database, API, etc.).
"""

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

logger = logging.getLogger("modaletta.webapp.authorization")


class AuthorizationProvider(ABC):
    """Abstract base class for authorization providers.
    
    Implementations of this class determine whether a user is authorized
    to access the application based on their email address.
    """
    
    @abstractmethod
    def is_authorized(self, email: str) -> bool:
        """Check if a user is authorized to access the app.
        
        Args:
            email: The user's email address (from OAuth).
            
        Returns:
            True if the user is authorized, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_authorized_users(self) -> list[str]:
        """Get list of all authorized users.
        
        Returns:
            List of authorized email addresses.
        """
        pass


class AllowAllProvider(AuthorizationProvider):
    """Authorization provider that allows all authenticated users.
    
    Use this when you want authentication but no authorization restrictions.
    """
    
    def is_authorized(self, email: str) -> bool:
        return True
    
    def get_authorized_users(self) -> list[str]:
        return ["*"]


class YAMLAuthorizationProvider(AuthorizationProvider):
    """Authorization provider that loads authorized users from a YAML file.
    
    Expected YAML format:
    ```yaml
    authorized_users:
      - alice@example.com
      - bob@example.com
    ```
    
    Or with additional metadata (ignored for now, but ready for future):
    ```yaml
    authorized_users:
      - email: alice@example.com
        role: admin
      - email: bob@example.com
        role: user
    ```
    """
    
    def __init__(self, yaml_path: str | Path):
        """Initialize the YAML authorization provider.
        
        Args:
            yaml_path: Path to the YAML file containing authorized users.
        """
        self.yaml_path = Path(yaml_path)
        self._authorized_emails: set[str] = set()
        self._load_authorized_users()
    
    def _load_authorized_users(self) -> None:
        """Load authorized users from the YAML file."""
        import yaml
        
        if not self.yaml_path.exists():
            logger.warning(f"Authorization file not found: {self.yaml_path}")
            return
        
        try:
            with open(self.yaml_path) as f:
                data = yaml.safe_load(f)
            
            if not data:
                logger.warning(f"Empty authorization file: {self.yaml_path}")
                return
            
            users = data.get("authorized_users", [])
            
            for user in users:
                if isinstance(user, str):
                    # Simple format: just email string
                    self._authorized_emails.add(user.lower())
                elif isinstance(user, dict) and "email" in user:
                    # Extended format: dict with email key
                    self._authorized_emails.add(user["email"].lower())
            
            logger.info(f"Loaded {len(self._authorized_emails)} authorized users from {self.yaml_path}")
            
        except Exception as e:
            logger.error(f"Failed to load authorization file: {e}")
    
    def is_authorized(self, email: str) -> bool:
        """Check if email is in the authorized users list."""
        return email.lower() in self._authorized_emails
    
    def get_authorized_users(self) -> list[str]:
        """Get list of authorized emails."""
        return sorted(self._authorized_emails)
    
    def reload(self) -> None:
        """Reload the authorized users from the YAML file."""
        self._authorized_emails.clear()
        self._load_authorized_users()


class EnvironmentAuthorizationProvider(AuthorizationProvider):
    """Authorization provider that reads authorized users from environment variable.
    
    Reads from AUTHORIZED_USERS env var as comma-separated email addresses.
    Example: AUTHORIZED_USERS="alice@example.com,bob@example.com"
    """
    
    def __init__(self, env_var: str = "AUTHORIZED_USERS"):
        """Initialize the environment authorization provider.
        
        Args:
            env_var: Name of the environment variable to read from.
        """
        self.env_var = env_var
        self._authorized_emails: set[str] = set()
        self._load_authorized_users()
    
    def _load_authorized_users(self) -> None:
        """Load authorized users from environment variable."""
        value = os.environ.get(self.env_var, "")
        
        if not value:
            logger.warning(f"No authorized users in {self.env_var} environment variable")
            return
        
        for email in value.split(","):
            email = email.strip().lower()
            if email:
                self._authorized_emails.add(email)
        
        logger.info(f"Loaded {len(self._authorized_emails)} authorized users from ${self.env_var}")
    
    def is_authorized(self, email: str) -> bool:
        """Check if email is in the authorized users list."""
        return email.lower() in self._authorized_emails
    
    def get_authorized_users(self) -> list[str]:
        """Get list of authorized emails."""
        return sorted(self._authorized_emails)


# =============================================================================
# Global Authorization Provider
# =============================================================================

_authorization_provider: Optional[AuthorizationProvider] = None


def get_authorization_provider() -> AuthorizationProvider:
    """Get the current authorization provider.
    
    Returns the configured provider, or AllowAllProvider if none configured.
    """
    global _authorization_provider
    if _authorization_provider is None:
        return AllowAllProvider()
    return _authorization_provider


def set_authorization_provider(provider: AuthorizationProvider) -> None:
    """Set the global authorization provider.
    
    Args:
        provider: The authorization provider to use.
    """
    global _authorization_provider
    _authorization_provider = provider
    logger.info(f"Authorization provider set: {type(provider).__name__}")


def configure_authorization_from_env() -> AuthorizationProvider:
    """Configure authorization based on environment variables.
    
    Checks for configuration in this order:
    1. AUTHORIZED_USERS env var (comma-separated emails)
    2. AUTHORIZED_USERS_FILE env var (path to YAML file)
    3. Default path: /app/authorized_users.yaml (Modal container)
    4. Default: AllowAllProvider (no restrictions)
    
    Returns:
        The configured authorization provider.
    """
    # Check for comma-separated list in env var
    if os.environ.get("AUTHORIZED_USERS"):
        provider = EnvironmentAuthorizationProvider("AUTHORIZED_USERS")
        set_authorization_provider(provider)
        return provider
    
    # Check for YAML file path in env var
    yaml_path = os.environ.get("AUTHORIZED_USERS_FILE")
    if yaml_path and Path(yaml_path).exists():
        provider = YAMLAuthorizationProvider(yaml_path)
        set_authorization_provider(provider)
        return provider
    
    # Check default Modal container path
    default_path = Path("/app/authorized_users.yaml")
    if default_path.exists():
        logger.info(f"Found authorized users file at default path: {default_path}")
        provider = YAMLAuthorizationProvider(default_path)
        set_authorization_provider(provider)
        return provider
    
    # Default: allow all authenticated users
    logger.info("No authorization config found - allowing all authenticated users")
    provider = AllowAllProvider()
    set_authorization_provider(provider)
    return provider
