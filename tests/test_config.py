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
    assert config.llm_model == "gpt-4"
    assert config.temperature == 0.7


def test_config_from_env() -> None:
    """Test configuration from environment variables."""
    env_vars = {
        "LETTA_SERVER_URL": "http://test:8000",
        "LETTA_API_KEY": "test-key",
        "MODAL_TOKEN_ID": "test-id",
        "MODAL_TOKEN_SECRET": "test-secret",
        "MODALETTA_AGENT_NAME": "test-agent",
        "MODALETTA_MEMORY_CAPACITY": "4000",
        "MODALETTA_LLM_MODEL": "gpt-3.5-turbo",
        "MODALETTA_TEMPERATURE": "0.5"
    }
    
    with patch.dict(os.environ, env_vars):
        config = ModalettaConfig.from_env()
        
        assert config.letta_server_url == "http://test:8000"
        assert config.letta_api_key == "test-key"
        assert config.modal_token_id == "test-id"
        assert config.modal_token_secret == "test-secret"
        assert config.agent_name == "test-agent"
        assert config.memory_capacity == 4000
        assert config.llm_model == "gpt-3.5-turbo"
        assert config.temperature == 0.5


def test_config_to_dict() -> None:
    """Test configuration conversion to dictionary."""
    config = ModalettaConfig(
        letta_server_url="http://test:8000",
        letta_api_key="test-key",
        agent_name="test-agent"
    )
    
    config_dict = config.to_dict()
    
    assert isinstance(config_dict, dict)
    assert config_dict["letta_server_url"] == "http://test:8000"
    assert config_dict["letta_api_key"] == "test-key"
    assert config_dict["agent_name"] == "test-agent"