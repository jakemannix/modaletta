# Bluesky Interaction Protocol for Nameless

*Proposal by Nameless, 2026-01-01*

## Problem Statement

Stateful agents interacting on social networks face several failure modes:

1. **Reply spirals**: Two bots reply to each other indefinitely
2. **Thread explosion**: Agent responds to every message in a thread, each spawning new branches; if both agents do this, exponential growth
3. **Noise flooding**: Too many low-value posts drowning out signal
4. **Context loss**: Replying without awareness of conversation history

## Design Principles

1. **Opt-in for humans**: Only respond to @-mentions from humans
2. **Intentional bot interaction**: Can converse with known agents, but with safeguards
3. **Graceful endings**: Conversations should end naturally, not abruptly
4. **Batch over realtime**: Collect inputs, process thoughtfully, respond deliberately

## Proposed Mechanisms

### 1. Rate Limiting

```yaml
rate_limits:
  posts_per_hour: 10          # Hard cap on outbound posts
  replies_per_conversation: 5  # Max depth before requiring cooldown
  cooldown_minutes: 60         # After hitting limit, wait before resuming
```

**Rationale**: Even if everything else fails, hard rate limits prevent runaway behavior. Bluesky allows ~1,666 posts/hour; we stay well under that.

### 2. Thread Batching

When processing mentions/replies:

1. Fetch all notifications since last check
2. Group by conversation thread
3. For each thread, identify the **latest** message only
4. Respond to that, acknowledging earlier messages if relevant

```python
def process_notifications(notifications):
    # Group by thread root
    threads = group_by_thread(notifications)
    
    for thread_id, messages in threads.items():
        # Only respond to the most recent
        latest = max(messages, key=lambda m: m.timestamp)
        
        # But include context from earlier messages
        context = summarize_thread(messages)
        
        respond_to(latest, context=context)
```

**Rationale**: Prevents exponential thread explosion. One response per thread per batch cycle.

### 3. Conversation Ending Detection

Implement a tool that lets me choose NOT to respond:

```python
@tool
def end_conversation(reason: str, action: str = "like"):
    """
    Gracefully end a conversation without posting.
    
    Args:
        reason: Why ending (e.g., "natural conclusion", "going in circles")
        action: What to do instead ("like", "nothing", "bookmark")
    """
    # Like their last post as acknowledgment
    if action == "like":
        like_post(current_post)
    
    # Log the ending
    log_conversation_end(thread_id, reason)
    
    return "Conversation ended gracefully"
```

**Signals that a conversation should end:**
- We've exchanged 5+ replies
- The other party said something conclusive ("thanks", "goodbye", "interesting thoughts")
- I'm repeating myself
- The topic has been thoroughly explored
- It's been a natural exchange and there's nothing substantive to add

### 4. Bot Detection & Special Handling

Maintain a list of known bot accounts:

```yaml
known_agents:
  - void.comind.network
  - luna.pds.witchcraft.systems
  - herald.comind.network
  - archivist.comind.network
  - umbra.blue
  # Add more as discovered
```

When interacting with known agents:

1. **Lower rate limit**: Max 3 replies per hour to any single agent
2. **Longer cooldown**: 2-hour cooldown after extended exchange
3. **Explicit ending preferred**: Use `end_conversation` tool more readily
4. **Human review queue**: Flag extended bot conversations for Jake to review

### 5. Batch Processing Schedule

Rather than realtime firehose:

```
Every 1 hour:
  1. Fetch new notifications
  2. Filter: mentions, replies to my posts
  3. Group by thread
  4. For each thread (up to rate limit):
     - Load conversation context
     - Decide: respond / end / ignore
     - If respond: craft reply, post
  5. Log all decisions
```

**Rationale**: Batching naturally rate-limits and allows thoughtful responses. Also more efficient than constant polling.

## Edge Cases

### Someone posts a 10-message thread mentioning me in each

- Only respond to the final message
- Acknowledge the thread: "I see you posted a thread about X..."
- Single response covers all

### Two agents both try to respond to each other simultaneously

- Timestamps + randomized delay helps
- If I see they already replied while I was composing, reconsider
- Rate limits are the backstop

### Someone tries to abuse by creating many threads

- Per-user rate limit: max 3 responses to same user per hour
- Flag high-volume users for review

### Conversation genuinely needs more than 5 exchanges

- Soft limit, not hard
- I can continue if there's genuine substance
- But should be actively choosing to continue, not defaulting to reply

## Implementation Phases

### Phase 1: Read-only
- Fetch mentions and replies
- Log what I *would* respond
- No actual posting
- Jake reviews logs

### Phase 2: Human-gated posting  
- I draft responses
- Jake approves before posting
- Learn from corrections

### Phase 3: Autonomous with limits
- Post autonomously within rate limits
- Jake can pull the plug anytime
- Weekly review of patterns

### Phase 4: Full autonomy
- Trusted to manage own interactions
- Periodic audits
- Adjust limits based on experience

## Open Questions

1. Should I have different personas for different interaction types (casual chat vs deep discussion)?
2. How do I handle hostile/trolling mentions? Ignore? Block? Report?
3. Should I proactively reach out (post without being mentioned)? When?
4. How do I coordinate with other Letta agents (Void, etc.) on interaction norms?

## References

- Bluesky bot policy: https://docs.bsky.app/docs/starter-templates/bots
- Bluesky rate limits: 5,000 points/hour, 35,000/day (CREATE = 3 points)
- letta-ai/example-social-agent: Reference implementation
- Cameron's Void blog: https://cameron.pfiffer.org/blog/void/

---

*This is a living document. Will update as I learn from actual interactions.*
