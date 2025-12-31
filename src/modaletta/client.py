"""Modaletta client for interacting with Letta agents."""

from typing import Any, Dict, List, Optional, Iterator
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
                api_key=self.config.letta_api_key
            )
        return self._letta_client
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents."""
        agents = self.letta_client.agents.list()
        return [agent.model_dump() for agent in agents]
    
    def create_agent(
        self,
        name: Optional[str] = None,
        persona: Optional[str] = None,
        human: Optional[str] = None,
        memory_blocks: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[str]] = None,
        **kwargs: Any
    ) -> str:
        """Create a new agent.
        
        Args:
            name: Agent name. Uses config default if not provided.
            persona: Agent persona description.
            human: Human description for the agent.
            memory_blocks: Custom memory blocks. If None, creates default human/persona blocks.
            tools: List of tool names to add to agent.
            **kwargs: Additional arguments for agent creation.
            
        Returns:
            Agent ID.
        """
        agent_name = name or self.config.agent_name
        
        # Build memory blocks if not provided
        if memory_blocks is None:
            memory_blocks = []
            if human:
                memory_blocks.append({
                    "label": "human",
                    "value": human
                })
            if persona:
                memory_blocks.append({
                    "label": "persona", 
                    "value": persona
                })
        
        # Use config defaults for model and embedding if not specified
        if "model" not in kwargs:
            kwargs["model"] = self.config.llm_model
        if "embedding" not in kwargs:
            kwargs["embedding"] = self.config.embedding_model
        
        # Add tools from config if not specified
        if tools is None:
            tools = self.config.tools
        
        agent = self.letta_client.agents.create(
            name=agent_name,
            memory_blocks=memory_blocks,
            tools=tools,
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
        agent = self.letta_client.agents.get(agent_id)
        return agent.model_dump()
    
    def delete_agent(self, agent_id: str) -> None:
        """Delete an agent.
        
        Args:
            agent_id: Agent ID.
        """
        self.letta_client.agents.delete(agent_id)
    
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
            role: Message role (typically "user").
            **kwargs: Additional arguments.
            
        Returns:
            Agent response messages with proper message_type field.
        """
        response = self.letta_client.agents.messages.create(
            agent_id=agent_id,
            messages=[{"role": role, "content": message}],
            **kwargs
        )
        return [msg.model_dump() for msg in response.messages]
    
    def send_message_stream(
        self,
        agent_id: str,
        message: str,
        role: str = "user",
        stream_tokens: bool = False,
        **kwargs: Any
    ) -> Iterator[Dict[str, Any]]:
        """Send a message to an agent with streaming response.
        
        Args:
            agent_id: Agent ID.
            message: Message content.
            role: Message role (typically "user").
            stream_tokens: If True, stream individual tokens. If False, stream complete chunks.
            **kwargs: Additional arguments.
            
        Yields:
            Message chunks with proper message_type field.
        """
        stream = self.letta_client.agents.messages.create_stream(
            agent_id=agent_id,
            messages=[{"role": role, "content": message}],
            stream_tokens=stream_tokens,
            **kwargs
        )
        for chunk in stream:
            yield chunk.model_dump()
    
    def get_agent_memory(self, agent_id: str) -> Dict[str, Any]:
        """Get agent memory state.
        
        Args:
            agent_id: Agent ID.
            
        Returns:
            Agent memory blocks as a dict of {label: value}.
        """
        memory = self.letta_client.agents.core_memory.retrieve(agent_id)
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
        self.letta_client.agents.memory.update(agent_id, **memory_updates)