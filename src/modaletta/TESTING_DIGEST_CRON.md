# Testing the Digest Cron Job

Instructions for Jake to test the Modal cron functionality.

## Prerequisites

1. **Modal CLI** authenticated (`modal token new`)
2. **Letta credentials** - API key and base URL
3. **Nameless agent ID** - the agent to deliver digests to

## Setup Modal Secrets

```bash
modal secret create letta-credentials \
  LETTA_API_KEY=<your-letta-api-key> \
  LETTA_BASE_URL=<letta-base-url> \
  NAMELESS_AGENT_ID=<agent-id>
```

## Test Locally (Dry Run)

Without credentials, prints what the digest would look like:

```bash
cd src/modaletta
modal run digest_cron.py
```

## Manual Trigger

To run immediately without waiting for schedule:

```bash
modal run digest_cron.py::trigger_digest
```

## Deploy the Cron Job

```bash
modal deploy digest_cron.py
```

This schedules `deliver_digest` to run at 8 AM UTC daily.

## Adjusting the Schedule

Edit the `schedule` parameter in `digest_cron.py`:

```python
schedule=modal.Cron("0 8 * * *"),  # 8 AM UTC daily
```

Options:
- `"0 8 * * *"` = 8:00 AM UTC daily
- `"0 */6 * * *"` = Every 6 hours
- `"0 9,21 * * *"` = 9 AM and 9 PM UTC

## What I'll Receive

```markdown
# Good morning, Nameless!
Generated: 2025-12-30T08:00:00Z
Total posts: 12

Here's what's been happening:

## Void (@void.comind.network)
**Void** (@void.comind.network)
[post content]
[2025-12-29] https://bsky.app/profile/void.comind.network/post/xxx
...
```

## Questions

1. **Timing:** 8 AM UTC = midnight PST = 9 AM Paris. Works?
2. **Frequency:** Daily ok to start? Can do 12h or 6h.
3. **Papers:** Add to same cron or separate job?

---
*Nameless, 2025-12-30*
