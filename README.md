# Modaletta Project

This repository contains multiple integrations for AI agents powered by [Letta](https://docs.letta.com) and [Modal](https://modal.com/docs).

## Project Structure

The repository is organized into separate directories for each integration:

### `modaletta/` - Core Package
The main Modaletta Python package for building AI agents with Letta and Modal.

- **Documentation**: See [modaletta/README.md](modaletta/README.md) for full details
- **Installation**: `cd modaletta && pip install -e .`
- **Features**: 
  - Letta integration with modern API support
  - Modal serverless deployment
  - CLI tools for agent management
  - Streaming support
  - Built-in tools (web search, code execution)

### `discord/` - Discord Bot Integration
A Discord bot powered by Modaletta agents.

- **Documentation**: See [discord/README.md](discord/README.md) for setup and usage
- **Installation**: `cd discord && pip install -e .`
- **Features**:
  - Discord bot integration
  - Stateful conversations with memory
  - Per-channel agent customization

## Quick Start

### For the Core Modaletta Package

```bash
cd modaletta

# Create virtual environment (recommended)
python -m venv .venv && source .venv/bin/activate

# Install and use
pip install -e .
modaletta --help
```

See [modaletta/README.md](modaletta/README.md) for detailed usage instructions.

### For the Discord Bot

```bash
cd discord

# Create virtual environment (recommended)
python -m venv .venv && source .venv/bin/activate

# Install and run
pip install -e .
python modaletta.py
```

See [discord/README.md](discord/README.md) for configuration details.

**Tip**: For faster installation, consider using [uv](https://docs.astral.sh/uv/) instead of pip.

## Environment Configuration

Both integrations use environment variables for configuration. Create `.env` files in their respective directories:

- `modaletta/.env` - For the core package
- `discord/.env` - For the Discord bot

See the documentation in each directory for specific configuration options.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please see the individual component READMEs for specific contribution guidelines.

## Support

- [GitHub Issues](https://github.com/jakemannix/modaletta/issues)
- [Letta Documentation](https://docs.letta.com)
- [Modal Documentation](https://modal.com/docs)

