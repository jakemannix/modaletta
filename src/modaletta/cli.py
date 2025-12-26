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
        created_at = agent.get("created_at", "")
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()
        table.add_row(
            agent.get("id", ""),
            agent.get("name", ""),
            str(created_at)
        )
    
    console.print(table)


@main.command()
@click.option("--name", help="Agent name")
@click.option("--system", help="System prompt for the agent")
@click.option("--model", help="LLM model to use")
@click.pass_context
def create_agent(
    ctx: click.Context,
    name: Optional[str],
    system: Optional[str],
    model: Optional[str]
) -> None:
    """Create a new agent."""
    client: ModalettaClient = ctx.obj["client"]

    try:
        agent_id = client.create_agent(
            name=name,
            system=system,
            model=model
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
@click.pass_context
def send_message(ctx: click.Context, agent_id: str, message: str) -> None:
    """Send a message to an agent."""
    client: ModalettaClient = ctx.obj["client"]

    try:
        response = client.send_message(agent_id, message)
        console.print(f"[blue]Sent:[/blue] {message}")
        console.print("[green]Response:[/green]")

        for msg in response:
            msg_type = msg.get("message_type", "unknown")
            # Handle different message types
            if msg_type == "assistant_message":
                content = msg.get("content", "")
                console.print(f"[yellow]Assistant:[/yellow] {content}")
            elif msg_type == "reasoning_message":
                reasoning = msg.get("reasoning", "")
                console.print(f"[dim]Reasoning:[/dim] {reasoning}")
            elif msg_type == "tool_call_message":
                tool = msg.get("tool_call", {})
                console.print(f"[cyan]Tool call:[/cyan] {tool}")
            elif msg_type == "tool_return_message":
                result = msg.get("tool_return", "")
                console.print(f"[cyan]Tool result:[/cyan] {result}")
    except Exception as e:
        console.print(f"[red]Error sending message: {e}[/red]")


@main.command()
@click.argument("agent_id")
@click.pass_context
def get_memory(ctx: click.Context, agent_id: str) -> None:
    """Get agent memory blocks."""
    client: ModalettaClient = ctx.obj["client"]

    try:
        blocks = client.get_agent_blocks(agent_id)
        console.print(f"[green]Memory blocks for agent {agent_id}:[/green]")
        for block in blocks:
            console.print(f"  [cyan]{block.get('label', 'unknown')}:[/cyan] {block.get('value', '')[:200]}")
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