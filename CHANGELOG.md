# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-10-25

### Added
- Modern Letta Python SDK integration with proper `agents.create()` API
- Memory blocks support for agent creation
- Streaming response support via `send_message_stream()`
- Built-in tools configuration (`web_search`, `run_code`)
- Embedding model configuration
- CLI streaming support with `--stream` flag
- Comprehensive test coverage for new API
- Migration guide documentation
- Enhanced README with modern API examples

### Changed
- **BREAKING**: Updated to use modern Letta API structure (`client.agents.*` instead of flat methods)
- **BREAKING**: Response format now uses `message_type` field instead of `role`/`text`
- **BREAKING**: Model names must include provider prefix (e.g., `openai/gpt-4.1`)
- Updated default LLM model from `gpt-4` to `openai/gpt-4.1`
- Updated all examples to use new API patterns
- Enhanced CLI with better message type handling
- Improved configuration with tools and embedding model support

### Fixed
- Proper handling of different message types (assistant, tool_call, tool_return, reasoning)
- Correct API method calls matching latest Letta SDK
- Configuration parsing for tools from environment variables

### Deprecated
- Old API method names (still work through wrapper but will be removed in future)

## [0.0.1] - 2024-XX-XX

### Added
- Initial release with basic Letta integration
- Modal deployment support
- Basic CLI commands
- Configuration management

