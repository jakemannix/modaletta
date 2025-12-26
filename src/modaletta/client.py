"""Modaletta client for interacting with Letta agents."""

from typing import Any, Dict, List, Literal, Optional
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
        system: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """Create a new agent.

        Args:
            name: Agent name. Uses config default if not provided.
            system: System prompt for the agent.
            model: LLM model to use. Uses config default if not provided.
            **kwargs: Additional arguments for agent creation.

        Returns:
            Agent ID.
        """
        agent_name = name or self.config.agent_name
        agent_model = model or self.config.llm_model

        agent = self.letta_client.agents.create(
            name=agent_name,
            system=system,
            model=agent_model,
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
        agent = self.letta_client.agents.retrieve(agent_id)
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
        role: Literal["user", "system", "assistant"] = "user",
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
        response = self.letta_client.agents.messages.create(
            agent_id=agent_id,
            messages=[{"role": role, "content": message}],
            **kwargs
        )
        return [m.model_dump() for m in response.messages]

    def get_agent_blocks(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get agent memory blocks.

        Args:
            agent_id: Agent ID.

        Returns:
            List of memory blocks.
        """
        blocks = self.letta_client.agents.blocks.list(agent_id=agent_id)
        return [b.model_dump() for b in blocks]