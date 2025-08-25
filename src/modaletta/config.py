"""Configuration management for Modaletta."""

import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class ModalettaConfig(BaseModel):
    """Configuration for Modaletta agents."""
    
    # Letta configuration
    letta_server_url: str = Field(default="http://localhost:8283", description="Letta server URL")
    letta_api_key: Optional[str] = Field(default=None, description="Letta API key")
    
    # Modal configuration  
    modal_token_id: Optional[str] = Field(default=None, description="Modal token ID")
    modal_token_secret: Optional[str] = Field(default=None, description="Modal token secret")
    
    # Agent configuration
    agent_name: str = Field(default="modaletta-agent", description="Default agent name")
    memory_capacity: int = Field(default=2000, description="Agent memory capacity in tokens")
    
    # LLM configuration
    llm_model: str = Field(default="gpt-4", description="LLM model to use")
    temperature: float = Field(default=0.7, description="LLM temperature")
    
    @classmethod
    def from_env(cls) -> "ModalettaConfig":
        """Create configuration from environment variables."""
        return cls(
            letta_server_url=os.getenv("LETTA_SERVER_URL", "http://localhost:8283"),
            letta_api_key=os.getenv("LETTA_API_KEY"),
            modal_token_id=os.getenv("MODAL_TOKEN_ID"),
            modal_token_secret=os.getenv("MODAL_TOKEN_SECRET"),
            agent_name=os.getenv("MODALETTA_AGENT_NAME", "modaletta-agent"),
            memory_capacity=int(os.getenv("MODALETTA_MEMORY_CAPACITY", "2000")),
            llm_model=os.getenv("MODALETTA_LLM_MODEL", "gpt-4"),
            temperature=float(os.getenv("MODALETTA_TEMPERATURE", "0.7")),
        )
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return self.model_dump()