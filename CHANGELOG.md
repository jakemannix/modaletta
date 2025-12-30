# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-10-25

### Added
- Modern Letta Python SDK integration with `agents.create()` API
- Memory blocks support for agent creation
- Streaming response support via `send_message_stream()`
- Built-in tools configuration (`web_search`, `run_code`)
- Embedding model configuration
- CLI streaming support with `--stream` flag
- Comprehensive test coverage
- Enhanced README with API examples
- Discord bot integration skeleton and examples
- Custom tool examples (code runner, tool management)
- Configuration management via environment variables

### Features
- Simplified configuration with environment-based setup and sensible defaults
- Modal integration for serverless deployment
- Enhanced typing with proper message_type handling
- CLI tools for quick agent operations
- Support for multiple message types (assistant, tool_call, tool_return, reasoning)

### Configuration
- Default LLM model: `openai/gpt-4.1`
- Default embedding model: `openai/text-embedding-3-small`
- Tools configured via `MODALETTA_TOOLS` environment variable (comma-separated)
- Full configuration via environment variables (see README.md)
