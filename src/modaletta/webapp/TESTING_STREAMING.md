# Testing: Streaming Responses

This document covers testing the streaming feature on the `webapp-chat-streaming` branch.

## Prerequisites

1. Modal secrets configured (`letta-credentials`, `oauth-credentials`)
2. Letta server running with an agent created
3. OAuth configured (see `AUTH_SETUP.md`)

## Running the App

```bash
cd /Users/jake/src/open_src/modaletta
modal serve src/modaletta/webapp/api.py
```

Open the URL shown in terminal (e.g., `https://jakemannix--modaletta-webapp-webapp-dev.modal.run`)

## Testing Streaming

### 1. Enable Streaming Mode

- Look for the **"Stream"** checkbox in the header (next to "Debug")
- Should be checked by default (persisted in localStorage)
- If unchecked, check it to enable streaming

### 2. Basic Streaming Test

1. Select an agent from the dropdown
2. Type a message and send
3. **Expected behavior**:
   - "Thinking..." appears briefly
   - Response text appears progressively (not all at once)
   - If agent uses tools, you'll see the response build up

### 3. Streaming + Debug Mode

1. Enable both "Stream" AND "Debug" checkboxes
2. Send a message that triggers tool use (e.g., "What time is it?" if agent has time tool)
3. **Expected behavior**:
   - Debug messages appear in real-time as agent thinks
   - `💭` reasoning messages (yellow background)
   - `🔧` tool calls (green background)
   - `📤` tool results (green background)
   - Final response appears after tools complete

### 4. Idempotency Test

This prevents duplicate messages when the client retries on timeout.

1. Open browser DevTools → Network tab
2. Send a message and note the `idempotency_key` in the request payload
3. If you could replay that exact request (same key), you'd get:
   - Cached response if completed
   - "in_flight" status if still processing

**To manually test idempotency:**
```javascript
// In browser console, send same request twice quickly:
const key = crypto.randomUUID();
fetch('/api/chat/stream', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  credentials: 'include',
  body: JSON.stringify({
    agent_id: 'YOUR_AGENT_ID',
    message: 'Hello',
    idempotency_key: key
  })
});
// Send again immediately with same key
fetch('/api/chat/stream', {
  method: 'POST', 
  headers: {'Content-Type': 'application/json'},
  credentials: 'include',
  body: JSON.stringify({
    agent_id: 'YOUR_AGENT_ID', 
    message: 'Hello',
    idempotency_key: key
  })
});
// Second request should return "in_flight" or cached result
```

### 5. Fallback to Non-Streaming

1. Uncheck the "Stream" checkbox
2. Send a message
3. **Expected behavior**:
   - Uses regular `/api/chat` endpoint (not `/api/chat/stream`)
   - Response appears all at once after processing completes
   - Still works correctly, just not progressive

## Troubleshooting

### Stream doesn't appear progressive
- Check browser console for errors
- Verify "Stream" checkbox is checked
- Try a longer response (short responses may complete too fast to notice)

### "Request in progress" message
- This means idempotency detected a duplicate request
- Wait for the original to complete, or refresh the page

### SSE connection drops
- Modal containers have timeouts; very long responses may timeout
- The idempotency cache preserves partial results for retry

## Technical Details

- **Endpoint**: `POST /api/chat/stream`
- **Response**: Server-Sent Events (SSE)
- **Event types**:
  - `chunk`: Message data with `message_type`
  - `done`: Stream completed
  - `in_flight`: Duplicate request detected
  - `error`: Error occurred

## Cleanup

Once streaming is tested and merged, this file can be deleted.
