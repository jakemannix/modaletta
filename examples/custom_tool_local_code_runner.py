"""Example of creating a custom local code execution tool for Letta."""

import subprocess
import tempfile
from typing import Optional
from modaletta import ModalettaClient, ModalettaConfig


def run_code_locally(code: str, language: str = "python") -> str:
    """
    Execute code in a local Docker container.
    
    Args:
        code (str): The code to execute
        language (str): Programming language (currently only 'python' supported)
    
    Returns:
        str: The output of the code execution or error message
    """
    import subprocess
    import tempfile
    
    if language != "python":
        return f"Error: Language '{language}' not supported. Only 'python' is currently supported."
    
    try:
        # Create a temporary file with the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        # Run code in Docker container with limited resources
        # Using official Python slim image for security
        result = subprocess.run(
            [
                'docker', 'run', '--rm',
                '--network', 'none',  # No network access
                '--memory', '256m',    # Limit memory
                '--cpus', '0.5',       # Limit CPU
                '--timeout', '30s',    # 30 second timeout
                '-v', f'{temp_file}:/code.py:ro',  # Mount as read-only
                'python:3.11-slim',
                'python', '/code.py'
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Clean up temp file
        subprocess.run(['rm', temp_file], check=False)
        
        # Build detailed response including the code
        output_parts = []
        output_parts.append(f"CODE EXECUTED:\n{code}\n")
        output_parts.append(f"[Exit code: {result.returncode}]")
        
        if result.returncode == 0:
            if result.stdout:
                output_parts.append(f"STDOUT:\n{result.stdout.strip()}")
            else:
                output_parts.append("(No output produced)")
        else:
            output_parts.append(f"STDERR:\n{result.stderr.strip()}")
        
        return "\n".join(output_parts)
            
    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out (30 second limit)"
    except Exception as e:
        return f"Error executing code: {str(e)}"


def main() -> None:
    """Demo of using custom local code execution tool."""
    
    # Initialize client
    config = ModalettaConfig.from_env()
    client = ModalettaClient(config)
    
    # Create or get existing custom tool
    tool_name = "run_code_locally"
    print(f"Setting up tool '{tool_name}'...")
    
    try:
        # Try to create the tool
        tool = client.letta_client.tools.create_from_function(func=run_code_locally)
        print(f"✓ Tool created: {tool.name}")
    except Exception as e:
        if "already exists" in str(e):
            # Tool already exists, get it
            print(f"✓ Tool already exists, using existing tool")
            tool = client.letta_client.tools.get(tool_name)
        else:
            raise
    
    # Create agent with the custom tool
    print("\nCreating agent with custom tool...")
    agent_id = client.create_agent(
        name="local-code-runner",
        persona="I am a helpful coding assistant that can execute Python code locally.",
        human="The user is a developer who wants to test Python code.",
        tools=[tool.name]  # Use our custom tool
    )
    print(f"✓ Agent created: {agent_id}")
    
    # Test the tool
    test_messages = [
        "Can you calculate 123 * 456 using Python code?",
        "Write a Python function to calculate fibonacci(10) and run it.",
        "Create a list of the first 5 prime numbers using Python."
    ]
    
    for message in test_messages:
        print(f"\n{'='*60}")
        print(f"User: {message}")
        print(f"{'='*60}")
        
        response = client.send_message(agent_id, message)
        
        for msg in response:
            message_type = msg.get("message_type", "")
            
            if message_type == "assistant_message":
                content = msg.get("content", "")
                print(f"\n💬 Assistant: {content}")
                
            elif message_type == "tool_call_message":
                tool_call = msg.get("tool_call", {})
                print(f"\n🔧 Calling tool: {tool_call.get('name', '')}")
                
            elif message_type == "tool_return_message":
                tool_return = msg.get("tool_return", "")
                print(f"\n📦 Tool result:\n{tool_return}")
    
    print(f"\n\n✓ Demo complete! Agent ID: {agent_id}")
    print("You can continue chatting with this agent using:")
    print(f"  modaletta send-message {agent_id} \"Your message here\"")


if __name__ == "__main__":
    main()

