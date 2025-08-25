"""Tests for Modaletta client."""

from unittest.mock import Mock, patch
import pytest
from modaletta.client import ModalettaClient
from modaletta.config import ModalettaConfig


@pytest.fixture
def mock_config() -> ModalettaConfig:
    """Mock configuration for testing."""
    return ModalettaConfig(
        letta_server_url="http://test:8000",
        letta_api_key="test-key"
    )


@pytest.fixture
def mock_letta_client() -> Mock:
    """Mock Letta client."""
    return Mock()


def test_client_initialization(mock_config: ModalettaConfig) -> None:
    """Test client initialization."""
    client = ModalettaClient(mock_config)
    assert client.config == mock_config
    assert client._letta_client is None


@patch("modaletta.client.Letta")
def test_letta_client_property(
    mock_letta_class: Mock,
    mock_config: ModalettaConfig,
    mock_letta_client: Mock
) -> None:
    """Test Letta client property."""
    mock_letta_class.return_value = mock_letta_client
    
    client = ModalettaClient(mock_config)
    letta_client = client.letta_client
    
    assert letta_client == mock_letta_client
    mock_letta_class.assert_called_once_with(
        base_url="http://test:8000",
        token="test-key"
    )


@patch("modaletta.client.Letta")
def test_list_agents(
    mock_letta_class: Mock,
    mock_config: ModalettaConfig,
    mock_letta_client: Mock
) -> None:
    """Test listing agents."""
    mock_agent = Mock()
    mock_agent.model_dump.return_value = {"id": "test-id", "name": "test-agent"}
    mock_letta_client.list_agents.return_value = [mock_agent]
    mock_letta_class.return_value = mock_letta_client
    
    client = ModalettaClient(mock_config)
    agents = client.list_agents()
    
    assert len(agents) == 1
    assert agents[0]["id"] == "test-id"
    assert agents[0]["name"] == "test-agent"