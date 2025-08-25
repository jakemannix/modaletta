# Modaletta

**⚠️ Early Development Status**: This package is in initial development. See "Current Status" section below for what actually works.

A Python package that aims to integrate [Letta](https://docs.letta.com) (agent framework) with [Modal](https://modal.com/docs) (serverless platform) for scalable AI agent deployment.

## Current Status

### ✅ What Actually Works (Tested)
- **Package Installation**: `pip install -e .` installs successfully
- **Basic Imports**: Core classes can be imported without errors
  ```python
  from modaletta import ModalettaConfig, ModalettaClient, ModalettaAgent
  ```
- **Configuration Management**: Environment-based config loading works
- **CLI Entry Point**: `modaletta --help` command functions
- **Test Suite**: All tests pass with mocked dependencies

### 🚧 What Should Work (Untested)
The codebase purports to provide:
- **Letta Integration**: Wrapper around letta-client for agent lifecycle management
- **Modal Deployment**: Serverless functions for agent execution on Modal
- **Agent Management**: High-level abstractions for agent operations
- **CLI Commands**: Full command-line interface for agent operations

### ❓ What Needs Real Testing
- Actual Letta server connectivity
- Modal deployment functionality  
- Agent creation and messaging
- End-to-end workflows

## Installation

**From Source (Recommended for now)**:

```bash
git clone https://github.com/jakemannix/modaletta.git
cd modaletta
pip install -e .
```

## Quick Start (Theoretical)

**⚠️ These commands are untested and may not work without a running Letta server**

1. **Set up environment variables**:

```bash
cp .env.example .env
# Edit .env with your Letta and Modal credentials
```

2. **Verify basic functionality**:

```bash
# These should work:
modaletta --help
modaletta config-info
```

3. **Intended usage (requires Letta server)**:

```bash
# These require actual Letta server connectivity:
modaletta create-agent --name "my-agent" --persona "You are a helpful assistant"
modaletta list-agents
modaletta send-message <agent-id> "Hello, how are you?"
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

## Python API (Theoretical)

**⚠️ Untested - requires running Letta server**

```python
from modaletta import ModalettaAgent, ModalettaClient, ModalettaConfig

# This works (tested):
config = ModalettaConfig.from_env()
client = ModalettaClient(config)

# These are untested and may fail without Letta server:
agent_id = client.create_agent(name="my-agent")
response = client.send_message(agent_id, "Hello!")
print(response)

# Agent wrapper (also untested):
agent = ModalettaAgent(agent_id=agent_id, config=config)
response = agent.send_message("How are you?")
```

## Modal Deployment (Theoretical)

**⚠️ Completely untested**

The codebase includes Modal deployment functions but these have not been tested:

```python
import modal
from modaletta.agent import app, create_modal_agent, send_message_modal

# Theoretical usage - may not work:
with app.run():
    config_dict = {"letta_server_url": "http://localhost:8283"}
    agent_id = create_modal_agent.remote(config_dict)
    response = send_message_modal.remote(agent_id, "Hello from Modal!", config_dict)
    print(response)
```

## Development

### Tested Commands
```bash
# These work:
pip install -e .[dev]           # Install with dev dependencies
python -m pytest tests/ -v     # Run test suite (passes)
modaletta --help               # CLI help works
```

### Untested Commands
```bash
# These should work but are untested:
ruff check .                   # Linting
ruff format .                  # Code formatting  
mypy .                         # Type checking
```

## Requirements

### Confirmed Working
- Python 3.9+ (tested with 3.12)
- Dependencies install correctly via pip/uv

### Required for Full Functionality (Untested)
- Letta server running (for agent operations)
- Modal account and authentication (for deployment)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

This package is in early development. The most valuable contributions would be:
1. **Testing with real Letta servers**: Verify agent operations actually work
2. **Modal deployment testing**: Test the serverless deployment functions
3. **Integration testing**: End-to-end workflows
4. **Documentation improvements**: Based on actual usage experience

## Current Limitations

- **No integration testing**: Only unit tests with mocks have been run
- **No real server testing**: Letta connectivity is theoretical
- **No deployment testing**: Modal functions are completely untested
- **Limited error handling**: Edge cases likely not covered
- **No performance testing**: Scalability claims are theoretical

## Support

- [GitHub Issues](https://github.com/jakemannix/modaletta/issues) - Please report what you actually tried and what failed
- [Letta Documentation](https://docs.letta.com) - For Letta server setup and API details
- [Modal Documentation](https://modal.com/docs) - For Modal deployment and authentication