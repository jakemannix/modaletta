"""Modaletta client for interacting with Letta agents."""

from typing import Any, Dict, List, Optional
from letta_client import Letta
from .config import ModalettaConfig


class ModalettaClient:
    """Client for managing Modaletta agents with Letta backend."""
    
    def __init__(self, config: Optional[ModalettaConfig] = None) -> None:
        """Initialize the Modaletta client.
        
        Args:
            config: Configuration object. If None, loads from environment.
        """
        self.config = config or ModalettaConfig.from_env()
        self._letta_client: Optional[Letta] = None
    
    @property
    def letta_client(self) -> Letta:
        """Get or create Letta client."""
        if self._letta_client is None:
            self._letta_client = Letta(
                base_url=self.config.letta_server_url,
                token=self.config.letta_api_key
            )
        return self._letta_client
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents."""
        agents = self.letta_client.list_agents()
        return [agent.model_dump() for agent in agents]
    
    def create_agent(
        self,
        name: Optional[str] = None,
        persona: Optional[str] = None,
        human: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """Create a new agent.
        
        Args:
            name: Agent name. Uses config default if not provided.
            persona: Agent persona description.
            human: Human description for the agent.
            **kwargs: Additional arguments for agent creation.
            
        Returns:
            Agent ID.
        """
        agent_name = name or self.config.agent_name
        
        agent = self.letta_client.create_agent(
            name=agent_name,
            persona=persona,
            human=human,
            **kwargs
        )
        return agent.id
    
    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get agent information.
        
        Args:
            agent_id: Agent ID.
            
        Returns:
            Agent information.
        """
        agent = self.letta_client.get_agent(agent_id)
        return agent.model_dump()
    
    def delete_agent(self, agent_id: str) -> None:
        """Delete an agent.
        
        Args:
            agent_id: Agent ID.
        """
        self.letta_client.delete_agent(agent_id)
    
    def send_message(
        self,
        agent_id: str,
        message: str,
        role: str = "user",
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """Send a message to an agent.
        
        Args:
            agent_id: Agent ID.
            message: Message content.
            role: Message role (user, assistant, system).
            **kwargs: Additional arguments.
            
        Returns:
            Agent response messages.
        """
        response = self.letta_client.send_message(
            agent_id=agent_id,
            message=message,
            role=role,
            **kwargs
        )
        return [msg.model_dump() for msg in response.messages]
    
    def get_agent_memory(self, agent_id: str) -> Dict[str, Any]:
        """Get agent memory state.
        
        Args:
            agent_id: Agent ID.
            
        Returns:
            Agent memory information.
        """
        memory = self.letta_client.get_agent_memory(agent_id)
        return memory.model_dump()
    
    def update_agent_memory(
        self,
        agent_id: str,
        memory_updates: Dict[str, Any]
    ) -> None:
        """Update agent memory.
        
        Args:
            agent_id: Agent ID.
            memory_updates: Memory updates to apply.
        """
        self.letta_client.update_agent_memory(agent_id, **memory_updates)