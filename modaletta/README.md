# Modaletta

**✨ Updated for Modern Letta API**: This package now uses the latest Letta Python SDK with proper agent creation, memory blocks, and message handling.

A Python package that integrates [Letta](https://docs.letta.com) (AI agent framework) with [Modal](https://modal.com/docs) (serverless platform) for scalable stateful AI agent deployment.

## Current Status

### ✅ What's New (v0.1.0)
- **Modern Letta API**: Updated to use latest Letta Python SDK
  - Uses `client.agents.create()` with `memory_blocks` parameter
  - Proper message handling with `message_type` field
  - Support for streaming responses
  - Built-in tools support (`web_search`, `run_code`)
- **Improved Configuration**: 
  - Modern model defaults (`openai/gpt-4.1`, `openai/text-embedding-3-small`)
  - Tool configuration support
  - Embedding model configuration
- **Enhanced CLI**: 
  - Streaming support with `--stream` flag
  - Better message type handling and display
- **Updated Tests**: All tests pass with proper mocking of new API structure

### 🧪 Ready to Test
The codebase provides:
- **Letta Integration**: Complete wrapper around modern letta-client API
- **Modal Deployment**: Serverless functions for agent execution on Modal
- **Agent Management**: High-level abstractions for stateful agent operations
- **CLI Commands**: Full command-line interface with streaming support

### 📋 Prerequisites for Testing
- **Letta Server**: Self-hosted or Letta Cloud account with API key
- **OpenAI API Key**: For using default models (or configure other models)
- **Modal Account**: Only needed for serverless deployment features

## Installation

**From Source (Recommended for now)**:

```bash
git clone https://github.com/jakemannix/modaletta.git
cd modaletta/modaletta
```

**Create a virtual environment** (recommended):

```bash
# Standard approach
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Or use uv (modern, faster alternative - install from https://docs.astral.sh/uv/)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

**Install the package**:

```bash
# Standard pip
pip install -e .

# Or with uv (much faster)
uv pip install -e .
```

## Quick Start

1. **Set up environment variables**:

Create a `.env` file in your project root:

```bash
# For Letta Cloud (easiest)
LETTA_SERVER_URL=https://api.letta.com
LETTA_API_KEY=your_letta_api_key_here  # Get from https://app.letta.com/api-keys

# For self-hosted Letta
# LETTA_SERVER_URL=http://localhost:8283
```

2. **Verify basic functionality**:

```bash
modaletta --help
modaletta config-info
```

3. **Create and use an agent**:

```bash
# Create an agent with custom persona
modaletta create-agent \
  --name "my-assistant" \
  --persona "I am a helpful AI assistant specializing in Python development." \
  --human "The user is a Python developer."

# List all agents
modaletta list-agents

# Send a message (use the agent ID from list-agents)
modaletta send-message <agent-id> "Hello! Can you help me debug some Python code?"

# Send with streaming (see response as it's generated)
modaletta send-message --stream <agent-id> "Tell me a story about AI."

# View agent memory
modaletta get-memory <agent-id>
```

## Configuration

Modaletta uses environment variables for configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| `LETTA_SERVER_URL` | Letta server URL (use `https://api.letta.com` for Letta Cloud) | `http://localhost:8283` |
| `LETTA_API_KEY` | Letta API key (required for Letta Cloud) | None |
| `MODAL_TOKEN_ID` | Modal token ID | None |
| `MODAL_TOKEN_SECRET` | Modal token secret | None |
| `MODALETTA_AGENT_NAME` | Default agent name | `modaletta-agent` |
| `MODALETTA_MEMORY_CAPACITY` | Agent memory capacity | `2000` |
| `MODALETTA_LLM_MODEL` | LLM model to use (with provider prefix) | `openai/gpt-4.1` |
| `MODALETTA_EMBEDDING_MODEL` | Embedding model to use | `openai/text-embedding-3-small` |
| `MODALETTA_TEMPERATURE` | LLM temperature | `0.7` |
| `MODALETTA_TOOLS` | Comma-separated list of tools | `` (empty) |

### Example `.env` file

```bash
# For Letta Cloud
LETTA_SERVER_URL=https://api.letta.com
LETTA_API_KEY=your_letta_api_key_here

# For self-hosted Letta
# LETTA_SERVER_URL=http://localhost:8283
# LETTA_API_KEY=  # Optional for self-hosted

# Model configuration
MODALETTA_LLM_MODEL=openai/gpt-4.1
MODALETTA_EMBEDDING_MODEL=openai/text-embedding-3-small
MODALETTA_TOOLS=web_search,run_code

# Optional Modal configuration (only needed for serverless deployment)
# MODAL_TOKEN_ID=your_modal_token_id
# MODAL_TOKEN_SECRET=your_modal_token_secret

# Optional: E2B API key for run_code tool (get free key at https://e2b.dev)
# E2B_API_KEY=your_e2b_api_key
```

**Note**: The `run_code` tool requires an E2B API key for self-hosted servers. It works automatically on Letta Cloud. Get a free key at [e2b.dev](https://e2b.dev).

## Python API

### Quick Start

```python
from modaletta import ModalettaAgent, ModalettaClient, ModalettaConfig

# Configure (loads from environment variables)
config = ModalettaConfig.from_env()
config.tools = ["web_search", "run_code"]  # Add built-in tools

# Option 1: Use the client directly
client = ModalettaClient(config)
agent_id = client.create_agent(
    name="my-assistant",
    persona="I am a helpful AI assistant that specializes in coding and research.",
    human="The user is a Python developer working on AI projects."
)

# Send a message (note: Letta agents are STATEFUL, only send new messages)
response = client.send_message(agent_id, "Hello! Can you help me with Python?")

# Process response with proper message_type handling
for msg in response:
    message_type = msg.get("message_type", "")
    if message_type == "assistant_message":
        print(f"Assistant: {msg.get('content', '')}")
    elif message_type == "tool_call_message":
        tool_call = msg.get("tool_call", {})
        print(f"[Calling tool: {tool_call.get('name', '')}]")
    elif message_type == "tool_return_message":
        print(f"[Tool result: {msg.get('tool_return', '')}]")

# Option 2: Use the agent wrapper (easier)
agent = ModalettaAgent(
    config=config,
    persona="I am a helpful AI assistant.",
    human="The user is a developer."
)

response = agent.send_message("What's 25 * 47? Use run_code to calculate it.")
for msg in response:
    if msg.get("message_type") == "assistant_message":
        print(msg.get("content", ""))

# Streaming example
for chunk in agent.send_message_stream("Tell me a story", stream_tokens=True):
    if chunk.get("message_type") == "assistant_message":
        content = chunk.get("content", "")
        if content:
            print(content, end="", flush=True)
print()  # New line at end

# Get agent memory
memory = agent.get_memory()
print(f"Memory blocks: {list(memory.keys())}")
```

### Key API Concepts

**Stateful Agents**: Letta agents maintain conversation history server-side. Always send only NEW messages, never the full history.

```python
# ✅ CORRECT - Single new message
response = client.send_message(agent_id, "What's the weather?")

# ❌ WRONG - Don't send conversation history
response = client.send_message(agent_id, previous_messages + [new_message])
```

**Message Types**: Responses use `message_type` field to distinguish different message kinds:
- `assistant_message`: Agent's response (has `content` field)
- `reasoning_message`: Agent's internal reasoning (has `reasoning` field)  
- `tool_call_message`: Agent calling a tool (has `tool_call` dict with `name` and `arguments`)
- `tool_return_message`: Tool execution result (has `tool_return` field)
- `usage_statistics`: Token usage information

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

## Architecture

Modaletta provides multiple layers of abstraction:

1. **ModalettaConfig**: Configuration management with environment variable support
2. **ModalettaClient**: Low-level client wrapping the Letta Python SDK with modern API
3. **ModalettaAgent**: High-level agent wrapper for easier usage
4. **Modal Functions**: Serverless deployment functions for running agents on Modal
5. **CLI**: Command-line interface for all agent operations

### Why Modaletta?

While you can use the Letta Python SDK directly, Modaletta provides:

- **Simplified Configuration**: Environment-based config with sensible defaults
- **Modal Integration**: Ready-to-use serverless deployment on Modal
- **Enhanced Typing**: All responses properly typed with message_type handling
- **CLI Tools**: Command-line interface for quick agent operations
- **Best Practices**: Built-in patterns following Letta's latest guidelines

## Migration from Old Letta API

If you have existing code using the old Letta API, here are the key changes:

```python
# OLD API (deprecated)
from letta import create_client
client = create_client()
agent = client.create_agent(name="test")
response = client.user_message(agent_id, "Hello")

# NEW API (Modaletta with modern Letta)
from modaletta import ModalettaClient
client = ModalettaClient()
agent_id = client.create_agent(
    name="test",
    persona="I am a helpful assistant",
    human="The user is a developer"
)
response = client.send_message(agent_id, "Hello")

# Response format changed:
# OLD: response["messages"][0]["text"]
# NEW: response[0]["content"] (if message_type == "assistant_message")
```

## Known Limitations

- **Modal Deployment**: Modal functions have basic testing but need real-world validation
- **Error Handling**: Could be more comprehensive for edge cases
- **Async Support**: Currently synchronous; async support could be added

## Support

- [GitHub Issues](https://github.com/jakemannix/modaletta/issues) - Please report what you actually tried and what failed
- [Letta Documentation](https://docs.letta.com) - For Letta server setup and API details
- [Modal Documentation](https://modal.com/docs) - For Modal deployment and authentication