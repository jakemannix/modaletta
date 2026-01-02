# Testing: Web Chat Interface

This document covers testing the webapp features on the `webapp-chat` branch.

## Prerequisites

1. **Modal secrets configured**:
   - `letta-credentials` (LETTA_API_KEY, LETTA_SERVER_URL)
   - `oauth-credentials` (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, JWT_SECRET)

2. **Letta server** running with at least one agent created

3. **OAuth configured** (see `AUTH_SETUP.md` for Google Cloud Console setup)

4. **Authorization whitelist** (optional):
   - Copy `authorized_users.yaml.example` to `authorized_users.yaml`
   - Add your email to the allowed list

## Running the App

```bash
cd /Users/jake/src/open_src/modaletta
modal serve src/modaletta/webapp/api.py
```

Open the URL shown (e.g., `https://jakemannix--modaletta-webapp-webapp-dev.modal.run`)

---

## Testing OAuth Authentication

### 1. Login Flow

1. Open the app URL in a fresh browser/incognito window
2. **Expected**: Redirected to `/login.html` with "Sign in with Google" button
3. Click the button
4. **Expected**: Google OAuth consent screen appears
5. Sign in with your Google account
6. **Expected**: 
   - If authorized: Redirected to main app, see your avatar/name in header
   - If not authorized: Redirected to `/unauthorized.html` with your email shown

### 2. Logout Flow

1. When logged in, click "Logout" in the header
2. **Expected**: Cookie cleared, redirected to login page

### 3. Auth Status Persistence

1. Log in successfully
2. Close the browser tab
3. Open the URL again
4. **Expected**: Still logged in (JWT cookie persists)

---

## Testing Message History

### 1. Initial Load

1. Log in and select an agent
2. **Expected**: Last 10 messages load automatically (if agent has history)
3. Messages appear in chronological order (oldest at top)

### 2. Infinite Scroll

1. If agent has more than 10 messages in history
2. Scroll to the TOP of the messages container
3. **Expected**: Older messages load automatically
4. Scroll position should stay stable (not jump around)

### 3. Agent Switching

1. Select a different agent from dropdown
2. **Expected**: Messages clear, new agent's history loads
3. Manual agent ID input also works (with 500ms debounce)

---

## Testing Debug Mode

### 1. Enable Debug Mode

1. Find the **"Debug"** checkbox in the header
2. Check it to enable
3. **Expected**: Persists in localStorage (survives refresh)

### 2. Debug Messages Display

1. With Debug enabled, send a message
2. **Expected**: In addition to agent response, you see:
   - Reasoning messages (yellow background) - agent's thoughts
   - Tool calls (green background) - when agent uses tools
   - Tool results (green background) - tool outputs

### 3. Debug in History

1. Enable Debug mode
2. Switch to an agent with tool-use history
3. **Expected**: Historical debug messages also appear

### 4. Toggle Off

1. Uncheck Debug
2. **Expected**: Debug messages hidden (history reloads without them)

---

## Testing Basic Chat

### 1. Send Message

1. Select an agent
2. Type a message in the input
3. Press Enter or click Send
4. **Expected**:
   - User message appears immediately
   - "Thinking..." loading indicator
   - Agent response appears
   - Input clears on success

### 2. User Context

1. Send a message
2. Check Modal logs for the formatted message
3. **Expected**: Message includes user email/name from JWT and context (time, timezone, device)

### 3. User Label

1. When logged in, look at the message input area
2. **Expected**: Your first name appears before the input (e.g., "Jake:")

---

## Testing Voice Input (if available)

1. Click the microphone button
2. Grant microphone permission if prompted
3. Speak your message
4. **Expected**: 
   - Button shows "listening" state
   - Speech transcribed to input field
   - Beep sound when recording stops

---

## Troubleshooting

### "No agents found"
- Check Letta server is running
- Verify LETTA_API_KEY and LETTA_SERVER_URL in Modal secrets

### OAuth redirect fails
- Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
- Verify redirect URI in Google Cloud Console matches your Modal URL

### History doesn't load
- Check browser console for errors
- Verify agent has message history in Letta

### Debug messages don't appear
- Ensure Debug checkbox is checked
- Agent must actually use tools/reasoning for those messages to exist

---

## Cleanup

Once testing is complete and features are merged, this file can be deleted.
