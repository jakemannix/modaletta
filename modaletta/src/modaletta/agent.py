"""Modaletta agent implementation using Modal for deployment."""

import modal
from typing import Any, Dict, Iterator, List, Optional
from .client import ModalettaClient
from .config import ModalettaConfig


class ModalettaAgent:
    """Modaletta agent that can be deployed on Modal."""
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        config: Optional[ModalettaConfig] = None,
        client: Optional[ModalettaClient] = None,
        persona: Optional[str] = None,
        human: Optional[str] = None,
        name: Optional[str] = None,
    ) -> None:
        """Initialize Modaletta agent.
        
        Args:
            agent_id: Existing agent ID. If None, creates a new agent.
            config: Configuration object.
            client: Modaletta client instance.
            persona: Agent persona for new agent creation.
            human: Human description for new agent creation.
            name: Agent name for new agent creation.
        """
        self.config = config or ModalettaConfig.from_env()
        self.client = client or ModalettaClient(self.config)
        self._agent_id = agent_id
        self._creation_params = {
            "persona": persona,
            "human": human,
            "name": name,
        }
    
    @property
    def agent_id(self) -> str:
        """Get or create agent ID."""
        if self._agent_id is None:
            # Create agent with stored creation params
            self._agent_id = self.client.create_agent(**self._creation_params)
        return self._agent_id
    
    def send_message(self, message: str, **kwargs: Any) -> List[Dict[str, Any]]:
        """Send message to the agent.
        
        Args:
            message: Message to send.
            **kwargs: Additional arguments.
            
        Returns:
            Agent response messages with message_type field.
        """
        return self.client.send_message(self.agent_id, message, **kwargs)
    
    def send_message_stream(
        self,
        message: str,
        stream_tokens: bool = False,
        **kwargs: Any
    ) -> Iterator[Dict[str, Any]]:
        """Send message to agent with streaming response.
        
        Args:
            message: Message to send.
            stream_tokens: If True, stream individual tokens. If False, stream complete chunks.
            **kwargs: Additional arguments.
            
        Yields:
            Message chunks with message_type field.
        """
        return self.client.send_message_stream(
            self.agent_id,
            message,
            stream_tokens=stream_tokens,
            **kwargs
        )
    
    def get_memory(self) -> Dict[str, Any]:
        """Get agent memory state."""
        return self.client.get_agent_memory(self.agent_id)
    
    def update_memory(self, memory_updates: Dict[str, Any]) -> None:
        """Update agent memory.
        
        Args:
            memory_updates: Memory updates to apply.
        """
        self.client.update_agent_memory(self.agent_id, memory_updates)
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information."""
        return self.client.get_agent(self.agent_id)
    
    def delete(self) -> None:
        """Delete the agent."""
        if self._agent_id:
            self.client.delete_agent(self._agent_id)
            self._agent_id = None


# Modal deployment functions
app = modal.App("modaletta")

image = modal.Image.debian_slim().pip_install([
    "letta-client",
    "pydantic",
    "python-dotenv",
])


@app.function(image=image)
def create_modal_agent(config_dict: Dict[str, Any]) -> str:
    """Create a Modaletta agent on Modal.
    
    Args:
        config_dict: Configuration dictionary.
        
    Returns:
        Agent ID.
    """
    config = ModalettaConfig(**config_dict)
    agent = ModalettaAgent(config=config)
    return agent.agent_id


@app.function(image=image)
def send_message_modal(
    agent_id: str,
    message: str,
    config_dict: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Send message to agent on Modal.
    
    Args:
        agent_id: Agent ID.
        message: Message to send.
        config_dict: Configuration dictionary.
        
    Returns:
        Agent response messages.
    """
    config = ModalettaConfig(**config_dict)
    agent = ModalettaAgent(agent_id=agent_id, config=config)
    return agent.send_message(message)


@app.function(image=image)
def get_agent_memory_modal(
    agent_id: str,
    config_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Get agent memory on Modal.
    
    Args:
        agent_id: Agent ID.
        config_dict: Configuration dictionary.
        
    Returns:
        Agent memory state.
    """
    config = ModalettaConfig(**config_dict)
    agent = ModalettaAgent(agent_id=agent_id, config=config)
    return agent.get_memory()