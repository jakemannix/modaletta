# Modaletta Discord Bot

A Discord bot integration for [Modaletta](https://github.com/jakemannix/modaletta), allowing you to deploy AI agents powered by [Letta](https://docs.letta.com) directly in your Discord server.

## Features

- 🤖 Discord bot powered by Letta AI agents
- 🧠 Stateful conversations with memory persistence
- 🔧 Access to Letta's tool ecosystem (web search, code execution, etc.)
- 🚀 Easy deployment with minimal configuration

## Prerequisites

- Python 3.9+
- A Discord bot token ([Create a Discord bot](https://discord.com/developers/applications))
- Modaletta setup with Letta API access (Cloud or self-hosted)

## Installation

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone https://github.com/jakemannix/modaletta.git
   cd modaletta
   ```

2. **Install the main Modaletta package**:
   ```bash
   uv sync
   ```

3. **Install Discord bot dependencies**:
   ```bash
   cd discord
   uv venv && uv pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file in the `discord` directory with the following variables:

```
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token

# Modaletta Configuration
LETTA_SERVER_URL=https://api.letta.com  # or http://localhost:8283 for self-hosted
LETTA_API_KEY=your_letta_api_key        # Required for Letta Cloud

# Agent Configuration
MODALETTA_AGENT_NAME=discord-assistant
MODALETTA_LLM_MODEL=openai/gpt-4.1
MODALETTA_EMBEDDING_MODEL=openai/text-embedding-3-small
MODALETTA_TOOLS=web_search,run_code     # Optional tools
MODALETTA_TEMPERATURE=0.7

# Optional: Tool specific configuration
# E2B_API_KEY=your_e2b_api_key          # For code execution
```

## Usage

### Basic Bot

Run the basic bot:

```bash
python modaletta.py
```

This runs a simple Discord bot that connects to your server but doesn't yet respond to messages (implementation required).

### Example Bot

Run the example bot:

```bash
python examples/example_bot.py
```

This runs a minimal example bot that responds to `$hello` commands.

## Implementing Modaletta Agent Responses

To implement the Modaletta agent in the Discord bot, you'll need to modify the `on_message` function in `modaletta.py`:

```python
from modaletta import ModalettaAgent, ModalettaConfig

# Initialize the agent (outside the event handler for persistence)
config = ModalettaConfig.from_env()
agent = ModalettaAgent(
    config=config,
    persona="I am a helpful AI assistant in a Discord server.",
    human="The users are members of a Discord community."
)

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    # Process messages that mention the bot or are direct messages
    if client.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        # Remove the mention from the message
        content = message.content.replace(f'<@{client.user.id}>', '').strip()
        
        # Let the user know we're processing
        async with message.channel.typing():
            # Send message to Modaletta agent
            response_text = ""
            async_response = await asyncio.to_thread(
                agent.send_message, content
            )
            
            # Process the response
            for msg in async_response:
                if msg.get("message_type") == "assistant_message":
                    response_text += msg.get("content", "")
            
            # Split long responses
            if len(response_text) > 2000:
                chunks = [response_text[i:i+1990] for i in range(0, len(response_text), 1990)]
                for chunk in chunks:
                    await message.channel.send(chunk)
            else:
                await message.channel.send(response_text)
```

## Advanced Features

### Per-Channel Agents

You can create different agents for different channels to specialize them:

```python
# Map channels to agent IDs
channel_agents = {}

# Get or create agent for a channel
def get_channel_agent(channel_id):
    if channel_id not in channel_agents:
        config = ModalettaConfig.from_env()
        agent = ModalettaAgent(
            config=config,
            name=f"agent-{channel_id}",
            persona=f"I am an assistant for the #{channel_id} channel."
        )
        channel_agents[channel_id] = agent
    return channel_agents[channel_id]
```

### Command System

Implement a command system for bot management:

```python
@client.event
async def on_message(message):
    if message.author == client.user:
        return
        
    if message.content.startswith('$reset'):
        # Reset the agent for this channel
        channel_id = str(message.channel.id)
        if channel_id in channel_agents:
            del channel_agents[channel_id]
            await message.channel.send("Agent memory has been reset!")
        return
```

## Contributing

Contributions to improve the Discord bot integration are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - see the main [Modaletta repository](https://github.com/jakemannix/modaletta) for details.
