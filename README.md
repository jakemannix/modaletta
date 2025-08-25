# Modaletta

AI agents using [Letta](https://docs.letta.com) and [Modal](https://modal.com/docs) for scalable deployment.

## Features

- **Letta Integration**: Leverage Letta's powerful agent framework for persistent memory and conversation
- **Modal Deployment**: Scale your agents seamlessly with Modal's serverless platform
- **CLI Interface**: Easy-to-use command-line interface for agent management
- **Configuration Management**: Flexible configuration via environment variables or files
- **Type Safety**: Full type annotations and Pydantic models

## Installation

```bash
pip install modaletta
```

Or install from source:

```bash
git clone https://github.com/jakemannix/modaletta.git
cd modaletta
pip install -e .
```

## Quick Start

1. **Set up environment variables**:

```bash
cp .env.example .env
# Edit .env with your Letta and Modal credentials
```

2. **Create an agent**:

```bash
modaletta create-agent --name "my-agent" --persona "You are a helpful assistant"
```

3. **Send a message**:

```bash
modaletta send-message <agent-id> "Hello, how are you?"
```

4. **List agents**:

```bash
modaletta list-agents
```

## Configuration

Modaletta uses environment variables for configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| `LETTA_SERVER_URL` | Letta server URL | `http://localhost:8283` |
| `LETTA_API_KEY` | Letta API key | None |
| `MODAL_TOKEN_ID` | Modal token ID | None |
| `MODAL_TOKEN_SECRET` | Modal token secret | None |
| `MODALETTA_AGENT_NAME` | Default agent name | `modaletta-agent` |
| `MODALETTA_MEMORY_CAPACITY` | Agent memory capacity | `2000` |
| `MODALETTA_LLM_MODEL` | LLM model to use | `gpt-4` |
| `MODALETTA_TEMPERATURE` | LLM temperature | `0.7` |

## Python API

```python
from modaletta import ModalettaAgent, ModalettaClient, ModalettaConfig

# Create a client
config = ModalettaConfig.from_env()
client = ModalettaClient(config)

# Create an agent
agent_id = client.create_agent(name="my-agent")

# Send a message
response = client.send_message(agent_id, "Hello!")
print(response)

# Or use the agent wrapper
agent = ModalettaAgent(agent_id=agent_id, config=config)
response = agent.send_message("How are you?")
```

## Modal Deployment

Deploy agents to Modal for serverless scaling:

```python
import modal
from modaletta.agent import app, create_modal_agent, send_message_modal

# Deploy the app
with app.run():
    # Create an agent on Modal
    config_dict = {"letta_server_url": "http://localhost:8283"}
    agent_id = create_modal_agent.remote(config_dict)
    
    # Send messages
    response = send_message_modal.remote(agent_id, "Hello from Modal!", config_dict)
    print(response)
```

## Development

1. **Install development dependencies**:

```bash
pip install -e .[dev]
```

2. **Run tests**:

```bash
pytest
```

3. **Run linting**:

```bash
ruff check .
ruff format .
```

4. **Type checking**:

```bash
mypy .
```

## Requirements

- Python 3.9+
- Letta server running (for local development)
- Modal account (for deployment)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please read our contributing guidelines and submit pull requests.

## Support

- [GitHub Issues](https://github.com/jakemannix/modaletta/issues)
- [Letta Documentation](https://docs.letta.com)
- [Modal Documentation](https://modal.com/docs)