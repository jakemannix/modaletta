"""Basic example of using Modaletta agents."""

from modaletta import ModalettaAgent, ModalettaConfig


def main() -> None:
    """Run basic agent example."""
    # Create configuration with tools
    config = ModalettaConfig.from_env()
    config.tools = ["web_search", "run_python_simple"]  # Add built-in tools
    
    # Create agent with custom persona and human info
    agent = ModalettaAgent(config=config)
    
    print(f"Created agent: {agent.agent_id}")
    
    # Send some messages
    messages = [
        "Hello, I'm testing the Modaletta agent!",
        "Can you tell me a joke?",
        "What's the 10th Fibonacci number?",
        "Thank you for the conversation!"
    ]
    
    for message in messages:
        print(f"\nUser: {message}")
        response = agent.send_message(message)
        
        # Process response with new message_type format
        for msg in response:
            message_type = msg.get("message_type", "")
            
            if message_type == "assistant_message":
                content = msg.get("content", "")
                print(f"Assistant: {content}")
            elif message_type == "reasoning_message":
                reasoning = msg.get("reasoning", "")
                print(f"[Reasoning]: {reasoning}")
            elif message_type == "tool_call_message":
                tool_call = msg.get("tool_call", {})
                print(f"[Tool Call]: {tool_call.get('name', '')}")
            elif message_type == "tool_return_message":
                tool_return = msg.get("tool_return", "")
                print(f"[Tool Return]: {tool_return}")
    
    # Get agent memory
    memory = agent.get_memory()
    print(f"\nAgent memory blocks:")
    for label, value in memory.items():
        print(f"  {label}: {value[:100] if value else '(empty)'}...")


if __name__ == "__main__":
    main()