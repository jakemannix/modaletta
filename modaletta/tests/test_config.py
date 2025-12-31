"""Tests for Modaletta configuration."""

import os
from unittest.mock import patch
from modaletta.config import ModalettaConfig


def test_default_config() -> None:
    """Test default configuration values."""
    config = ModalettaConfig()
    
    assert config.letta_server_url == "http://localhost:8283"
    assert config.letta_api_key is None
    assert config.modal_token_id is None
    assert config.modal_token_secret is None
    assert config.agent_name == "modaletta-agent"
    assert config.memory_capacity == 2000
    assert config.llm_model == "openai/gpt-4.1"
    assert config.embedding_model == "openai/text-embedding-3-small"
    assert config.temperature == 0.7
    assert config.tools == []


def test_config_from_env() -> None:
    """Test configuration from environment variables."""
    env_vars = {
        "LETTA_SERVER_URL": "http://test:8000",
        "LETTA_API_KEY": "test-key",
        "MODAL_TOKEN_ID": "test-id",
        "MODAL_TOKEN_SECRET": "test-secret",
        "MODALETTA_AGENT_NAME": "test-agent",
        "MODALETTA_MEMORY_CAPACITY": "4000",
        "MODALETTA_LLM_MODEL": "openai/gpt-3.5-turbo",
        "MODALETTA_EMBEDDING_MODEL": "openai/text-embedding-ada-002",
        "MODALETTA_TEMPERATURE": "0.5",
        "MODALETTA_TOOLS": "web_search,run_code"
    }
    
    with patch.dict(os.environ, env_vars):
        config = ModalettaConfig.from_env()
        
        assert config.letta_server_url == "http://test:8000"
        assert config.letta_api_key == "test-key"
        assert config.modal_token_id == "test-id"
        assert config.modal_token_secret == "test-secret"
        assert config.agent_name == "test-agent"
        assert config.memory_capacity == 4000
        assert config.llm_model == "openai/gpt-3.5-turbo"
        assert config.embedding_model == "openai/text-embedding-ada-002"
        assert config.temperature == 0.5
        assert config.tools == ["web_search", "run_code"]


def test_config_to_dict() -> None:
    """Test configuration conversion to dictionary."""
    config = ModalettaConfig(
        letta_server_url="http://test:8000",
        letta_api_key="test-key",
        agent_name="test-agent",
        tools=["web_search"]
    )
    
    config_dict = config.to_dict()
    
    assert isinstance(config_dict, dict)
    assert config_dict["letta_server_url"] == "http://test:8000"
    assert config_dict["letta_api_key"] == "test-key"
    assert config_dict["agent_name"] == "test-agent"
    assert config_dict["tools"] == ["web_search"]


def test_tools_parsing() -> None:
    """Test tools parsing from environment."""
    # Test empty string
    with patch.dict(os.environ, {"MODALETTA_TOOLS": ""}):
        config = ModalettaConfig.from_env()
        assert config.tools == []
    
    # Test single tool
    with patch.dict(os.environ, {"MODALETTA_TOOLS": "web_search"}):
        config = ModalettaConfig.from_env()
        assert config.tools == ["web_search"]
    
    # Test multiple tools with spaces
    with patch.dict(os.environ, {"MODALETTA_TOOLS": "web_search, run_code, custom_tool"}):
        config = ModalettaConfig.from_env()
        assert config.tools == ["web_search", "run_code", "custom_tool"]