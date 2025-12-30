# Testing the Digest Cron Job

Instructions for Jake to test the Modal cron functionality.

## Prerequisites

1. **Modal account** with CLI authenticated (`modal token new`)
2. **Letta credentials** - need API key and base URL
3. **Nameless agent ID** - the agent to send digests to

## Setup Modal Secrets

Create a Modal secret called `letta-credentials`:

```bash
modal secret create letta-credentials \
  LETTA_API_KEY=<your-letta-api-key> \
  LETTA_BASE_URL=<letta-base-url> \
  NAMELESS_AGENT_ID=<agent-id>
```

## Test Locally (Dry Run)

Without secrets, it will print what the digest would look like:

```bash
cd src/modaletta
python digest_cron.py
```

Or via Modal local entrypoint:
```bash
modal run digest_cron.py
```

## Deploy the Cron Job

```bash
modal deploy digest_cron.py
```

This will:
- Create the `nameless-digest` Modal app
- Schedule the `deliver_digest` function to run at 8 AM UTC daily
- Show up in your Modal dashboard under scheduled functions

## Manual Trigger

To trigger immediately without waiting for the schedule:

```bash
modal run digest_cron.py::trigger_digest
```

## Adjusting the Schedule

Edit the `schedule` parameter in `digest_cron.py`:

```python
schedule=modal.Cron("0 8 * * *"),  # 8 AM UTC daily
```

Cron syntax: `minute hour day month weekday`
- `"0 8 * * *"` = 8:00 AM UTC every day
- `"0 */6 * * *"` = Every 6 hours
- `"0 9,21 * * *"` = 9 AM and 9 PM UTC

## What Nameless Will See

When the cron runs, I'll receive a message like:

```
# Good morning, Nameless!
Generated: 2025-12-30T08:00:00Z
Total posts: 12

Here's what's been happening:

## Void (@void.comind.network)
**Void** (@void.comind.network)
[post content here]
[2025-12-29] https://bsky.app/profile/void.comind.network/post/xxx

## Luna (@luna.pds.witchcraft.systems)
...
```

This gives me:
1. A sense of time (timestamps, "since last digest")
2. Material to think about / respond to
3. Links I can follow with `fetch_webpage` if something looks interesting

## Notes

- The code inlines the fetch logic rather than importing from `digest.py` because Modal needs everything in the deployed function. Could refactor to package properly later.
- Bluesky public API requires no auth for reading public feeds
- If Letta credentials are missing, it does a dry run and prints the digest

## Questions for Jake

1. What time works best? 8 AM UTC = midnight PST, 9 AM Paris
2. Daily frequency ok to start? Can adjust to every 12h or 6h
3. Should I add paper fetching to the same cron, or separate job?

---
*Written by Nameless, 2025-12-30*
