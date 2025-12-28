"""Modaletta client for interacting with Letta agents."""

from typing import Any, Optional

from letta_client import Letta

from .config import ModalettaConfig


class ModalettaClient:
    """Client for managing Modaletta agents with Letta backend."""

    def __init__(
        self,
        config: Optional[ModalettaConfig] = None,
        project_id: Optional[str] = None,
    ) -> None:
        """Initialize the Modaletta client.

        Args:
            config: Configuration object. If None, loads from environment.
            project_id: Letta project ID. If None, uses default project.
        """
        self.config = config or ModalettaConfig.from_env()
        self.project_id = project_id
        self._letta_client: Optional[Letta] = None

    @property
    def letta_client(self) -> Letta:
        """Get or create Letta client."""
        if self._letta_client is None:
            self._letta_client = Letta(
                base_url=self.config.letta_server_url,
                api_key=self.config.letta_api_key,
                project_id=self.project_id,
            )
        return self._letta_client

    def list_agents(self) -> list[dict[str, Any]]:
        """List all agents in the current project."""
        agents = self.letta_client.agents.list(project_id=self.project_id)
        return [agent.model_dump() for agent in agents]

    def create_agent(
        self,
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Create a new agent.

        Args:
            name: Agent name. Uses config default if not provided.
            **kwargs: Additional arguments for agent creation.

        Returns:
            Agent ID.
        """
        agent_name = name or self.config.agent_name
        agent = self.letta_client.agents.create(name=agent_name, **kwargs)
        return agent.id

    def get_agent(self, agent_id: str) -> dict[str, Any]:
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
        role: str = "user",
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
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
            **kwargs,
        )
        return [msg.model_dump() for msg in response.messages]

    def get_agent_memory(self, agent_id: str) -> dict[str, Any]:
        """Get agent memory state.

        Args:
            agent_id: Agent ID.

        Returns:
            Agent memory information.
        """
        # Memory is accessed via the agent's blocks
        agent = self.letta_client.agents.retrieve(agent_id)
        return {"memory_blocks": [b.model_dump() for b in agent.memory.blocks]}

    def update_agent_memory(
        self,
        agent_id: str,
        memory_updates: dict[str, Any],
    ) -> None:
        """Update agent memory.

        Args:
            agent_id: Agent ID.
            memory_updates: Memory updates to apply.
        """
        # Update memory blocks
        for block_label, value in memory_updates.items():
            self.letta_client.agents.blocks.update(
                agent_id=agent_id,
                block_label=block_label,
                value=value,
            )
