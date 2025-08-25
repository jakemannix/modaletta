"""Example of deploying Modaletta agents on Modal."""

from modaletta.agent import app, create_modal_agent, send_message_modal, get_agent_memory_modal
from modaletta import ModalettaConfig

def main() -> None:
    """Run Modal deployment example."""
    # Configuration
    config = ModalettaConfig.from_env()
    config_dict = config.to_dict()
    
    # Deploy and run on Modal
    with app.run():
        print("Creating agent on Modal...")
        agent_id = create_modal_agent.remote(config_dict)
        print(f"Created agent: {agent_id}")
        
        # Send messages
        messages = [
            "Hello from Modal!",
            "This is running serverlessly!",
            "Can you process this message?"
        ]
        
        for message in messages:
            print(f"\nSending: {message}")
            response = send_message_modal.remote(agent_id, message, config_dict)
            
            for msg in response:
                role = msg.get("role", "")
                content = msg.get("text", "")
                print(f"{role.title()}: {content}")
        
        # Get memory state
        print("\nGetting agent memory...")
        memory = get_agent_memory_modal.remote(agent_id, config_dict)
        print(f"Memory: {memory}")

if __name__ == "__main__":
    main()