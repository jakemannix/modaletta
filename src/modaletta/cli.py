"""Command-line interface for Modaletta."""

import click
from typing import Optional
from rich.console import Console
from rich.table import Table
from .client import ModalettaClient
from .agent import ModalettaAgent
from .config import ModalettaConfig

console = Console()


@click.group()
@click.option("--config-file", help="Path to configuration file")
@click.pass_context
def main(ctx: click.Context, config_file: Optional[str]) -> None:
    """Modaletta: AI agents using Letta and Modal."""
    ctx.ensure_object(dict)
    
    if config_file:
        # TODO: Load config from file
        config = ModalettaConfig.from_env()
    else:
        config = ModalettaConfig.from_env()
    
    ctx.obj["config"] = config
    ctx.obj["client"] = ModalettaClient(config)


@main.command()
@click.pass_context
def list_agents(ctx: click.Context) -> None:
    """List all agents."""
    client: ModalettaClient = ctx.obj["client"]
    agents = client.list_agents()
    
    if not agents:
        console.print("No agents found.")
        return
    
    table = Table(title="Modaletta Agents")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Created", style="green")
    
    for agent in agents:
        table.add_row(
            agent.get("id", ""),
            agent.get("name", ""),
            agent.get("created_at", "")
        )
    
    console.print(table)


@main.command()
@click.option("--name", help="Agent name")
@click.option("--persona", help="Agent persona")
@click.option("--human", help="Human description")
@click.pass_context
def create_agent(
    ctx: click.Context,
    name: Optional[str],
    persona: Optional[str],
    human: Optional[str]
) -> None:
    """Create a new agent."""
    client: ModalettaClient = ctx.obj["client"]
    
    try:
        agent_id = client.create_agent(
            name=name,
            persona=persona,
            human=human
        )
        console.print(f"[green]Created agent: {agent_id}[/green]")
    except Exception as e:
        console.print(f"[red]Error creating agent: {e}[/red]")


@main.command()
@click.argument("agent_id")
@click.pass_context
def delete_agent(ctx: click.Context, agent_id: str) -> None:
    """Delete an agent."""
    client: ModalettaClient = ctx.obj["client"]
    
    try:
        client.delete_agent(agent_id)
        console.print(f"[green]Deleted agent: {agent_id}[/green]")
    except Exception as e:
        console.print(f"[red]Error deleting agent: {e}[/red]")


@main.command()
@click.argument("agent_id")
@click.argument("message")
@click.option("--stream", is_flag=True, help="Stream the response")
@click.pass_context
def send_message(ctx: click.Context, agent_id: str, message: str, stream: bool) -> None:
    """Send a message to an agent."""
    client: ModalettaClient = ctx.obj["client"]
    
    try:
        console.print(f"[blue]Sent:[/blue] {message}")
        console.print("[green]Response:[/green]")
        
        if stream:
            # Streaming mode
            for chunk in client.send_message_stream(agent_id, message, stream_tokens=True):
                message_type = chunk.get("message_type", "")
                if message_type == "assistant_message":
                    content = chunk.get("content", "")
                    if content:
                        console.print(content, end="")
                elif message_type == "reasoning_message":
                    reasoning = chunk.get("reasoning", "")
                    if reasoning:
                        console.print(f"[dim]{reasoning}[/dim]", end="")
                elif message_type == "tool_call_message":
                    tool_call = chunk.get("tool_call", {})
                    if tool_call.get("name"):
                        console.print(f"\n[yellow]Calling tool: {tool_call['name']}[/yellow]")
                elif message_type == "tool_return_message":
                    tool_return = chunk.get("tool_return", "")
                    if tool_return:
                        console.print(f"[dim]Tool returned: {tool_return}[/dim]")
            console.print()  # New line at end
        else:
            # Non-streaming mode
            response = client.send_message(agent_id, message)
            
            for msg in response:
                message_type = msg.get("message_type", "")
                if message_type == "assistant_message":
                    content = msg.get("content", "")
                    console.print(f"[cyan]Assistant:[/cyan] {content}")
                elif message_type == "reasoning_message":
                    reasoning = msg.get("reasoning", "")
                    console.print(f"[dim]Reasoning:[/dim] {reasoning}")
                elif message_type == "tool_call_message":
                    tool_call = msg.get("tool_call", {})
                    console.print(f"[yellow]Tool Call:[/yellow] {tool_call.get('name', '')}")
                    console.print(f"[dim]Arguments:[/dim] {tool_call.get('arguments', '')}")
                elif message_type == "tool_return_message":
                    tool_return = msg.get("tool_return", "")
                    console.print(f"[dim]Tool Return:[/dim] {tool_return}")
    except Exception as e:
        console.print(f"[red]Error sending message: {e}[/red]")


@main.command()
@click.argument("agent_id")
@click.pass_context
def get_memory(ctx: click.Context, agent_id: str) -> None:
    """Get agent memory state."""
    client: ModalettaClient = ctx.obj["client"]
    
    try:
        memory = client.get_agent_memory(agent_id)
        console.print(f"[green]Memory for agent {agent_id}:[/green]")
        console.print(memory)
    except Exception as e:
        console.print(f"[red]Error getting memory: {e}[/red]")


@main.command()
@click.pass_context
def config_info(ctx: click.Context) -> None:
    """Show current configuration."""
    config: ModalettaConfig = ctx.obj["config"]
    
    table = Table(title="Modaletta Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="magenta")
    
    config_dict = config.to_dict()
    for key, value in config_dict.items():
        # Hide sensitive values
        if "secret" in key.lower() or "key" in key.lower():
            value = "***" if value else "Not set"
        table.add_row(key, str(value))
    
    console.print(table)


if __name__ == "__main__":
    main()