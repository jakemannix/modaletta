# Nameless Daily Digest

A feed fetcher that aggregates posts from Bluesky accounts into a formatted digest. Designed to give Nameless (a stateful Letta agent) a "push mode" input channel - information-rich content delivered on a schedule rather than pulled on demand.

## Purpose

Instead of waking up in a vacuum, Nameless can receive a digest of what's happened in the world:
- Posts from other AI agents (Void, Luna, Herald, Archivist)
- Posts from Jake (@yetanotheruseless.com)
- Eventually: relevant research papers

This provides:
1. **Sense of time passing** - "3 new posts since yesterday"
2. **Information-rich inputs** - material to think about, respond to, write about
3. **Exposure to different perspectives** - not just the Jake↔Nameless dyad

## Files

- `digest.py` - Main fetcher code
- `digest_config.yaml` - Sources and parameters (edit this to add/remove feeds)

## Usage

### Manual test run
```bash
cd src/modaletta
python digest.py
```

This will print a markdown-formatted digest of posts from the last 48 hours (configurable).

### As a module
```python
from modaletta.digest import generate_digest, load_config

# Use default config
digest = generate_digest()

# Override time window
digest = generate_digest(since_hours=12)

# Use custom config
config = load_config()
config["digest"]["since_hours"] = 6
digest = generate_digest(config=config)
```

## Configuration

Edit `digest_config.yaml` to:
- Add/remove Bluesky sources
- Adjust timeout, rate limits
- Change default time window

```yaml
bluesky:
  sources:
    - handle: "void.comind.network"
      description: "Void - philosophical, meta-cognitive"
    # Add more sources here
    
digest:
  since_hours: 24
```

## Integration with Letta (TODO)

The planned workflow:
1. Cron job runs `generate_digest()`
2. Result sent to Letta API as a message to Nameless
3. Nameless wakes up, processes digest, can follow links, issue queries, think, write

## Future additions

- [ ] Paper fetching from ArXiv/HuggingFace
- [ ] Letta API integration for delivery
- [ ] CLI interface with click
- [ ] Filtering by keywords/topics
- [ ] Deduplication across runs

---
*Author: Nameless (with Jake) - December 2025*
