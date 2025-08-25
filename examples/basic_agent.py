"""Basic example of using Modaletta agents."""

import asyncio
from modaletta import ModalettaAgent, ModalettaConfig

async def main() -> None:
    """Run basic agent example."""
    # Create configuration
    config = ModalettaConfig.from_env()
    
    # Create agent
    agent = ModalettaAgent(config=config)
    
    print(f"Created agent: {agent.agent_id}")
    
    # Send some messages
    messages = [
        "Hello, I'm testing the Modaletta agent!",
        "Can you tell me a joke?",
        "What's the weather like?",
        "Thank you for the conversation!"
    ]
    
    for message in messages:
        print(f"\nUser: {message}")
        response = agent.send_message(message)
        
        for msg in response:
            role = msg.get("role", "")
            content = msg.get("text", "")
            print(f"{role.title()}: {content}")
    
    # Get agent memory
    memory = agent.get_memory()
    print(f"\nAgent memory: {memory}")

if __name__ == "__main__":
    asyncio.run(main())