"""Simpler example: Custom tool that runs code with basic subprocess (no Docker)."""

import subprocess
import sys
from modaletta import ModalettaClient, ModalettaConfig


def run_python_simple(code: str) -> str:
    """
    Execute Python code in a subprocess.

    IMPORTANT: Uses subprocess.run() - so end the code with some print(): print(42 * 37)
    
    Args:
        code (str): Python code to execute
    
    Returns:
        str: The output or error message
    """
    import subprocess
    import sys
    
    try:
        # Add print debugging
        result = subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True,
            text=True,
            timeout=10,
            env={'PYTHONUNBUFFERED': '1'}  # Disable buffering
        )
        
        # Build detailed response
        output_parts = []
        output_parts.append(f"CODE EXECUTED:\n{code}\n")
        output_parts.append(f"[Exit code: {result.returncode}]")
        
        if result.stdout:
            output_parts.append(f"STDOUT:\n{result.stdout.strip()}")
        
        if result.stderr:
            output_parts.append(f"STDERR:\n{result.stderr.strip()}")
        
        if not result.stdout and not result.stderr:
            output_parts.append("(No output produced)")
        
        return "\n".join(output_parts)
        
    except subprocess.TimeoutExpired:
        return "Error: Execution timed out (10 seconds)"
    except Exception as e:
        return f"Error: {type(e).__name__}: {str(e)}"


def main() -> None:
    """Demo of simple custom tool."""
    
    config = ModalettaConfig.from_env()
    client = ModalettaClient(config)
    
    # Create or get existing custom tool
    tool_name = "run_python_simple"
    print(f"Setting up tool '{tool_name}'...")
    
    try:
        # Try to create the tool
        tool = client.letta_client.tools.create_from_function(func=run_python_simple)
        print(f"✓ Tool created: {tool.name}")
    except Exception as e:
        if "already exists" in str(e):
            # Tool already exists, get it
            print(f"✓ Tool already exists, using existing tool")
            tool = client.letta_client.tools.get(tool_name)
        else:
            raise
    
    # Create agent with custom tool
    print("Creating agent...")
    agent_id = client.create_agent(
        name="simple-python-runner",
        persona="I am a helpful Python assistant.",
        human="The user wants to run Python code.",
        tools=[tool.name]
    )
    print(f"✓ Agent created: {agent_id}")
    
    # Test it
    print("\n" + "="*60)
    response = client.send_message(
        agent_id, 
        "Calculate 42 * 37 using Python code"
    )
    
    for msg in response:
        if msg.get("message_type") == "assistant_message":
            print(f"Assistant: {msg.get('content', '')}")
        elif msg.get("message_type") == "tool_return_message":
            print(f"Result: {msg.get('tool_return', '')}")


if __name__ == "__main__":
    main()

