# Migration Guide: Updated to Modern Letta API

This document outlines the changes made to update Modaletta to use the modern Letta Python SDK.

## Overview

Modaletta has been updated from the old Letta API to the modern, officially supported Letta Python SDK (`letta-client`). This update ensures compatibility with the latest Letta features and follows Letta's recommended best practices.

## What Changed

### 1. Client API Methods

**Before (Old API):**
```python
# Old method names
agents = client.letta_client.list_agents()
agent = client.letta_client.create_agent(name="test")
client.letta_client.delete_agent(agent_id)
response = client.letta_client.send_message(agent_id, message)
memory = client.letta_client.get_agent_memory(agent_id)
```

**After (New API):**
```python
# New nested structure: client.agents.*
agents = client.letta_client.agents.list()
agent = client.letta_client.agents.create(name="test", memory_blocks=[...])
client.letta_client.agents.delete(agent_id)
response = client.letta_client.agents.messages.create(agent_id, messages=[...])
memory = client.letta_client.agents.memory.get(agent_id)
```

### 2. Agent Creation with Memory Blocks

**Before:**
```python
agent = client.create_agent(
    name="my-agent",
    persona="I am helpful",
    human="User is a developer"
)
```

**After:**
```python
agent = client.create_agent(
    name="my-agent",
    memory_blocks=[
        {"label": "persona", "value": "I am helpful"},
        {"label": "human", "value": "User is a developer"}
    ],
    model="openai/gpt-4.1",
    embedding="openai/text-embedding-3-small",
    tools=["web_search", "run_code"]
)
```

### 3. Message Response Format

**Before:**
```python
response = client.send_message(agent_id, "Hello")
for msg in response:
    text = msg.get("text", "")
    role = msg.get("role", "")
```

**After:**
```python
response = client.send_message(agent_id, "Hello")
for msg in response:
    message_type = msg.get("message_type", "")
    if message_type == "assistant_message":
        content = msg.get("content", "")
    elif message_type == "tool_call_message":
        tool_call = msg.get("tool_call", {})
    elif message_type == "tool_return_message":
        tool_return = msg.get("tool_return", "")
```

### 4. Configuration Updates

**New Default Models:**
- `llm_model`: `openai/gpt-4.1` (was `gpt-4`)
- `embedding_model`: `openai/text-embedding-3-small` (new field)
- `tools`: Comma-separated list via `MODALETTA_TOOLS` env var (new field)

### 5. Streaming Support

**New Feature:**
```python
# Stream responses
for chunk in client.send_message_stream(agent_id, "Tell me a story", stream_tokens=True):
    if chunk.get("message_type") == "assistant_message":
        print(chunk.get("content", ""), end="", flush=True)
```

## Updated Files

### Core Files
- **`src/modaletta/client.py`**: Updated all API calls to use modern nested structure
- **`src/modaletta/config.py`**: Added embedding model and tools configuration
- **`src/modaletta/agent.py`**: Added streaming support and better initialization
- **`src/modaletta/cli.py`**: Updated to handle new message types with `--stream` flag

### Tests
- **`tests/test_client.py`**: Updated mocks for nested API structure
- **`tests/test_config.py`**: Added tests for new configuration fields

### Examples
- **`examples/basic_agent.py`**: Updated to use new API patterns
- **`examples/modal_deployment.py`**: Updated message handling

### Documentation
- **`README.md`**: Comprehensive update with modern examples
- **`MIGRATION_GUIDE.md`**: This file

## Key Differences from Raw Letta SDK

While Modaletta now uses the modern Letta SDK, it provides additional benefits:

1. **Simplified Configuration**: Environment-based config with sensible defaults
2. **Convenience Methods**: Higher-level abstractions for common operations
3. **Modal Integration**: Ready-to-use serverless deployment functions
4. **CLI Tools**: Command-line interface for quick operations
5. **Type Hints**: Full type hints for better IDE support

## Environment Variables

New/updated environment variables:

```bash
# Updated defaults
MODALETTA_LLM_MODEL=openai/gpt-4.1  # was gpt-4
MODALETTA_EMBEDDING_MODEL=openai/text-embedding-3-small  # new

# New: Tools configuration
MODALETTA_TOOLS=web_search,run_code  # comma-separated list
```

## Breaking Changes

1. **Response Format**: All message responses now use `message_type` instead of `role`/`text`
2. **Model Names**: Must include provider prefix (e.g., `openai/gpt-4.1` not just `gpt-4`)
3. **Agent Creation**: Memory blocks are now explicitly structured
4. **Memory Methods**: Changed from `get_agent_memory` to nested `agents.memory.get`

## Testing

All tests pass with the new API:
```bash
$ python -m pytest tests/ -v
============================= test session starts ==============================
tests/test_client.py::test_client_initialization PASSED
tests/test_client.py::test_letta_client_property PASSED
tests/test_client.py::test_list_agents PASSED
tests/test_client.py::test_create_agent PASSED
tests/test_client.py::test_send_message PASSED
tests/test_client.py::test_get_agent_memory PASSED
tests/test_config.py::test_default_config PASSED
tests/test_config.py::test_config_from_env PASSED
tests/test_config.py::test_config_to_dict PASSED
tests/test_config.py::test_tools_parsing PASSED
======================== 10 passed in 0.86s ========================
```

## Migration Checklist

If you have existing code using Modaletta, follow these steps:

- [ ] Update environment variables with new defaults
- [ ] Update any custom agent creation code to use `memory_blocks`
- [ ] Update message response parsing to use `message_type` instead of `role`
- [ ] Add provider prefixes to model names (e.g., `openai/`)
- [ ] Test with a Letta server (self-hosted or Letta Cloud)
- [ ] Consider using new streaming features

## Resources

- [Letta Documentation](https://docs.letta.com)
- [Letta Python SDK](https://github.com/letta-ai/letta-python)
- [Letta Cloud](https://app.letta.com)
- [Modal Documentation](https://modal.com/docs)

## Support

For issues or questions:
- [GitHub Issues](https://github.com/jakemannix/modaletta/issues)
- [Letta Discord](https://discord.gg/letta)

