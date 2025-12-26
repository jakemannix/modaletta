"""Modaletta agent implementation using Modal for deployment."""

import modal
from typing import Any, Dict, List, Optional
from .client import ModalettaClient
from .config import ModalettaConfig


class ModalettaAgent:
    """Modaletta agent that can be deployed on Modal."""
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        config: Optional[ModalettaConfig] = None,
        client: Optional[ModalettaClient] = None
    ) -> None:
        """Initialize Modaletta agent.
        
        Args:
            agent_id: Existing agent ID. If None, creates a new agent.
            config: Configuration object.
            client: Modaletta client instance.
        """
        self.config = config or ModalettaConfig.from_env()
        self.client = client or ModalettaClient(self.config)
        self._agent_id = agent_id
    
    @property
    def agent_id(self) -> str:
        """Get or create agent ID."""
        if self._agent_id is None:
            self._agent_id = self.client.create_agent()
        return self._agent_id
    
    def send_message(self, message: str, **kwargs: Any) -> List[Dict[str, Any]]:
        """Send message to the agent.
        
        Args:
            message: Message to send.
            **kwargs: Additional arguments.
            
        Returns:
            Agent response messages.
        """
        return self.client.send_message(self.agent_id, message, **kwargs)
    
    def get_blocks(self) -> List[Dict[str, Any]]:
        """Get agent memory blocks."""
        return self.client.get_agent_blocks(self.agent_id)
    
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