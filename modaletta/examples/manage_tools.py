"""Helper script to manage Letta custom tools."""

import sys
from modaletta import ModalettaClient


def list_tools():
    """List all custom tools."""
    client = ModalettaClient()
    tools = client.letta_client.tools.list()
    
    if not tools:
        print("No tools found.")
        return
    
    print(f"\nFound {len(tools)} tool(s):\n")
    for tool in tools:
        print(f"  • {tool.name}")
        print(f"    ID: {tool.id}")
        if hasattr(tool, 'description') and tool.description:
            print(f"    Description: {tool.description}")
        print()


def delete_tool(tool_name):
    """Delete a tool by name."""
    client = ModalettaClient()
    tools = client.letta_client.tools.list()
    
    tool = next((t for t in tools if t.name == tool_name), None)
    
    if tool:
        print(f"Found tool: {tool.name} (ID: {tool.id})")
        confirm = input("Delete this tool? [y/N]: ")
        if confirm.lower() == 'y':
            client.letta_client.tools.delete(tool.id)
            print("✓ Tool deleted")
        else:
            print("Cancelled")
    else:
        print(f"Tool '{tool_name}' not found")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python manage_tools.py list")
        print("  python manage_tools.py delete <tool_name>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        list_tools()
    elif command == "delete":
        if len(sys.argv) < 3:
            print("Error: Please specify tool name to delete")
            sys.exit(1)
        delete_tool(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()

