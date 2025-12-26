"""Scheduled agent wakeup for autonomous processing."""

import modal
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Modal app for scheduled tasks
app = modal.App("modaletta-scheduled")

# Persistent volume for agent roster and logs
volume = modal.Volume.from_name("modaletta-data", create_if_missing=True)

# Path to local source
LOCAL_SRC_PATH = Path(__file__).parent.parent.parent  # src/ directory

# Image with dependencies and local source
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install([
        "letta-client==1.6.2",
        "pydantic>=2.0.0",
        "python-dotenv",
    ])
    .env({"PYTHONPATH": "/root/src"})
    .add_local_dir(LOCAL_SRC_PATH, remote_path="/root/src")  # must be last
)

DEFAULT_WAKEUP_PROMPT = """[AUTONOMOUS WAKEUP - {timestamp}]

You are waking up for your periodic autonomous check. Review your memory and consider:
1. Do you have any pending tasks or reminders?
2. Is there anything you should check on or follow up with?
3. Any actions you should take based on your goals?

If you have nothing to do, simply acknowledge this wakeup and wait for the next one.
Respond briefly with what you checked and any actions taken."""


def load_agent_roster(roster_path: str) -> list[dict[str, Any]]:
    """Load agent roster from JSON file."""
    path = Path(roster_path)
    if not path.exists():
        return []
    with open(path) as f:
        data = json.load(f)
    return data.get("agents", [])


def log_wakeup(agent_id: str, response: list[dict], log_dir: str) -> None:
    """Log wakeup activity."""
    log_path = Path(log_dir) / f"{agent_id}.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Extract just the key fields to avoid datetime serialization issues
    messages_summary = []
    for msg in response[:3]:
        msg_type = msg.get("message_type", "unknown")
        summary = {"type": msg_type}
        if msg_type == "assistant_message":
            summary["content"] = msg.get("content", "")[:500]
        elif msg_type == "reasoning_message":
            summary["reasoning"] = msg.get("reasoning", "")[:500]
        messages_summary.append(summary)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "wakeup",
        "response_count": len(response),
        "messages": messages_summary,
    }

    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


@app.function(
    image=image,
    volumes={"/data": volume},
    secrets=[modal.Secret.from_name("letta-credentials")],
    schedule=modal.Cron("*/15 * * * *"),  # Every 15 minutes
)
def agent_wakeup() -> dict[str, Any]:
    """Periodic agent wakeup - runs on schedule."""
    # Import here to avoid issues at module load time
    from modaletta.client import ModalettaClient
    from modaletta.config import ModalettaConfig

    config = ModalettaConfig.from_env()
    client = ModalettaClient(config)

    # Load agent roster
    roster = load_agent_roster("/data/agents.json")

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agents_processed": 0,
        "agents_skipped": 0,
        "errors": [],
    }

    for agent_config in roster:
        agent_id = agent_config.get("agent_id")
        if not agent_id:
            continue

        if not agent_config.get("autonomous_enabled", False):
            results["agents_skipped"] += 1
            continue

        try:
            # Get custom wakeup prompt or use default
            wakeup_prompt = agent_config.get("wakeup_prompt", DEFAULT_WAKEUP_PROMPT)
            prompt = wakeup_prompt.format(
                timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            )

            # Send wakeup message as system
            response = client.send_message(agent_id, prompt, role="system")

            # Log activity
            log_wakeup(agent_id, response, "/data/logs/")

            results["agents_processed"] += 1

        except Exception as e:
            results["errors"].append({
                "agent_id": agent_id,
                "error": str(e)
            })

    # Commit volume changes
    volume.commit()

    print(f"Wakeup complete: {results}")
    return results


@app.function(
    image=image,
    volumes={"/data": volume},
    secrets=[modal.Secret.from_name("letta-credentials")],
)
def agent_wakeup_once(agent_id: str, prompt: str | None = None) -> dict[str, Any]:
    """Manual one-time agent wakeup for testing."""
    from modaletta.client import ModalettaClient
    from modaletta.config import ModalettaConfig

    config = ModalettaConfig.from_env()
    client = ModalettaClient(config)

    wakeup_prompt = prompt or DEFAULT_WAKEUP_PROMPT.format(
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    )

    response = client.send_message(agent_id, wakeup_prompt, role="system")

    log_wakeup(agent_id, response, "/data/logs/")
    volume.commit()

    return {
        "agent_id": agent_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "response": response,
    }


@app.function(
    image=image,
    volumes={"/data": volume},
)
def init_agent_roster(agents: list[dict[str, Any]]) -> str:
    """Initialize or update the agent roster file."""
    roster_path = Path("/data/agents.json")
    roster_path.parent.mkdir(parents=True, exist_ok=True)

    roster = {"agents": agents}

    with open(roster_path, "w") as f:
        json.dump(roster, f, indent=2)

    volume.commit()
    return f"Roster saved with {len(agents)} agents"


@app.function(
    image=image,
    volumes={"/data": volume},
)
def get_wakeup_logs(agent_id: str, limit: int = 10) -> list[dict]:
    """Get recent wakeup logs for an agent."""
    log_path = Path(f"/data/logs/{agent_id}.jsonl")
    if not log_path.exists():
        return []

    logs = []
    with open(log_path) as f:
        for line in f:
            if line.strip():
                logs.append(json.loads(line))

    return logs[-limit:]


@app.local_entrypoint()
def main(
    agent_id: str | None = None,
    init: bool = False,
    logs: bool = False,
    prompt: str | None = None,
):
    """CLI entrypoint for testing wakeups.

    Examples:
        # Test wakeup for a specific agent
        modal run src/modaletta/scheduled/wakeup.py --agent-id agent-xxx

        # Test wakeup with custom prompt
        modal run src/modaletta/scheduled/wakeup.py --agent-id agent-xxx --prompt "Check for new emails"

        # Initialize roster with an agent
        modal run src/modaletta/scheduled/wakeup.py --init --agent-id agent-xxx

        # Initialize with custom wakeup prompt for scheduled runs
        modal run src/modaletta/scheduled/wakeup.py --init --agent-id agent-xxx --prompt "Review daily tasks"

        # View logs for an agent
        modal run src/modaletta/scheduled/wakeup.py --logs --agent-id agent-xxx
    """
    if init and agent_id:
        # Quick init with a single agent
        agent_config = {
            "agent_id": agent_id,
            "autonomous_enabled": True,
        }
        if prompt:
            agent_config["wakeup_prompt"] = prompt
        result = init_agent_roster.remote([agent_config])
        print(result)
    elif logs and agent_id:
        entries = get_wakeup_logs.remote(agent_id)
        for entry in entries:
            print(f"\n--- {entry['timestamp']} ---")
            print(f"Messages: {entry['response_count']}")
            for msg in entry.get("messages", []):
                msg_type = msg.get("type", "unknown")
                if msg_type == "assistant_message":
                    print(f"  Assistant: {msg.get('content', '')[:200]}")
                elif msg_type == "reasoning_message":
                    print(f"  Reasoning: {msg.get('reasoning', '')[:100]}")
    elif agent_id:
        # One-time wakeup
        result = agent_wakeup_once.remote(agent_id, prompt=prompt)
        print(f"\nWakeup sent to {agent_id}")
        print(f"Timestamp: {result['timestamp']}")
        print("\nResponse:")
        for msg in result["response"]:
            msg_type = msg.get("message_type", "unknown")
            if msg_type == "assistant_message":
                print(f"  Assistant: {msg.get('content', '')}")
            elif msg_type == "reasoning_message":
                print(f"  Reasoning: {msg.get('reasoning', '')}")
    else:
        print("Usage:")
        print("  modal run src/modaletta/scheduled/wakeup.py --agent-id <id>")
        print("  modal run src/modaletta/scheduled/wakeup.py --agent-id <id> --prompt 'Custom message'")
        print("  modal run src/modaletta/scheduled/wakeup.py --init --agent-id <id>")
        print("  modal run src/modaletta/scheduled/wakeup.py --init --agent-id <id> --prompt 'Scheduled prompt'")
        print("  modal run src/modaletta/scheduled/wakeup.py --logs --agent-id <id>")
