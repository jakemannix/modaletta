"""Example of deploying Modaletta agents on Modal."""

from modaletta.agent import app, create_modal_agent, send_message_modal, get_agent_memory_modal
from modaletta import ModalettaConfig


def main() -> None:
    """Run Modal deployment example."""
    # Configuration with modern defaults
    config = ModalettaConfig.from_env()
    config.tools = ["web_search"]  # Add web search tool
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
            "Can you search the web for the latest news about AI?"
        ]
        
        for message in messages:
            print(f"\nSending: {message}")
            response = send_message_modal.remote(agent_id, message, config_dict)
            
            # Process response with new message_type format
            for msg in response:
                message_type = msg.get("message_type", "")
                
                if message_type == "assistant_message":
                    content = msg.get("content", "")
                    print(f"Assistant: {content}")
                elif message_type == "tool_call_message":
                    tool_call = msg.get("tool_call", {})
                    print(f"[Tool Call]: {tool_call.get('name', '')}")
                elif message_type == "tool_return_message":
                    tool_return = msg.get("tool_return", "")
                    print(f"[Tool Return]: {tool_return[:200]}...")
        
        # Get memory state
        print("\nGetting agent memory...")
        memory = get_agent_memory_modal.remote(agent_id, config_dict)
        print(f"Memory blocks: {list(memory.keys())}")


if __name__ == "__main__":
    main()