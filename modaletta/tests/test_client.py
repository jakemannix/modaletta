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
        letta_api_key="test-key",
        llm_model="openai/gpt-4.1",
        embedding_model="openai/text-embedding-3-small",
        tools=["web_search"]
    )


@pytest.fixture
def mock_letta_client() -> Mock:
    """Mock Letta client with nested agents/messages/memory structure."""
    mock_client = Mock()
    mock_client.agents = Mock()
    mock_client.agents.list = Mock()
    mock_client.agents.create = Mock()
    mock_client.agents.get = Mock()
    mock_client.agents.delete = Mock()
    mock_client.agents.messages = Mock()
    mock_client.agents.messages.create = Mock()
    mock_client.agents.messages.create_stream = Mock()
    mock_client.agents.memory = Mock()
    mock_client.agents.memory.get = Mock()
    mock_client.agents.memory.update = Mock()
    return mock_client


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
        api_key="test-key"
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
    mock_letta_client.agents.list.return_value = [mock_agent]
    mock_letta_class.return_value = mock_letta_client
    
    client = ModalettaClient(mock_config)
    agents = client.list_agents()
    
    assert len(agents) == 1
    assert agents[0]["id"] == "test-id"
    assert agents[0]["name"] == "test-agent"


@patch("modaletta.client.Letta")
def test_create_agent(
    mock_letta_class: Mock,
    mock_config: ModalettaConfig,
    mock_letta_client: Mock
) -> None:
    """Test creating an agent."""
    mock_agent = Mock()
    mock_agent.id = "test-agent-id"
    mock_letta_client.agents.create.return_value = mock_agent
    mock_letta_class.return_value = mock_letta_client
    
    client = ModalettaClient(mock_config)
    agent_id = client.create_agent(
        name="test-agent",
        persona="I am a test assistant",
        human="The user is a developer"
    )
    
    assert agent_id == "test-agent-id"
    mock_letta_client.agents.create.assert_called_once()
    call_kwargs = mock_letta_client.agents.create.call_args[1]
    assert call_kwargs["name"] == "test-agent"
    assert call_kwargs["model"] == "openai/gpt-4.1"
    assert call_kwargs["embedding"] == "openai/text-embedding-3-small"
    assert call_kwargs["tools"] == ["web_search"]
    assert len(call_kwargs["memory_blocks"]) == 2


@patch("modaletta.client.Letta")
def test_send_message(
    mock_letta_class: Mock,
    mock_config: ModalettaConfig,
    mock_letta_client: Mock
) -> None:
    """Test sending a message."""
    mock_msg = Mock()
    mock_msg.model_dump.return_value = {
        "message_type": "assistant_message",
        "content": "Hello!"
    }
    mock_response = Mock()
    mock_response.messages = [mock_msg]
    mock_letta_client.agents.messages.create.return_value = mock_response
    mock_letta_class.return_value = mock_letta_client
    
    client = ModalettaClient(mock_config)
    response = client.send_message("test-agent-id", "Hi there!")
    
    assert len(response) == 1
    assert response[0]["message_type"] == "assistant_message"
    assert response[0]["content"] == "Hello!"
    mock_letta_client.agents.messages.create.assert_called_once_with(
        agent_id="test-agent-id",
        messages=[{"role": "user", "content": "Hi there!"}]
    )


@patch("modaletta.client.Letta")
def test_get_agent_memory(
    mock_letta_class: Mock,
    mock_config: ModalettaConfig,
    mock_letta_client: Mock
) -> None:
    """Test getting agent memory."""
    mock_memory = Mock()
    mock_memory.model_dump.return_value = {
        "human": {"value": "Test user"},
        "persona": {"value": "Test assistant"}
    }
    mock_letta_client.agents.memory.get.return_value = mock_memory
    mock_letta_class.return_value = mock_letta_client
    
    client = ModalettaClient(mock_config)
    memory = client.get_agent_memory("test-agent-id")
    
    assert "human" in memory
    assert "persona" in memory
    mock_letta_client.agents.memory.get.assert_called_once_with("test-agent-id")
