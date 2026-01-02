/**
 * Modaletta Chat Application
 * Web chat interface with voice input support
 */
(function () {
    'use strict';

    // Configuration
    const API_BASE = '/api';

    // Debug logging system
    const debugLogs = [];
    const sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    let pendingLogs = [];
    let flushTimeout = null;

    function debugLog(category, message, data = null) {
        const timestamp = new Date().toISOString();
        const entry = { timestamp, category, message, data };
        debugLogs.push(entry);
        pendingLogs.push(entry);

        // Also log to console
        if (data) {
            console.log(`[${timestamp}] [${category}] ${message}`, data);
        } else {
            console.log(`[${timestamp}] [${category}] ${message}`);
        }

        // Debounce sending to server
        if (flushTimeout) clearTimeout(flushTimeout);
        flushTimeout = setTimeout(flushLogsToServer, 500);
    }

    // Send logs to server
    async function flushLogsToServer() {
        if (pendingLogs.length === 0) return;

        const logsToSend = [...pendingLogs];
        pendingLogs = [];

        try {
            await fetch(`${API_BASE}/logs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    logs: logsToSend,
                    session_id: sessionId
                })
            });
        } catch (error) {
            console.error('Failed to send logs to server:', error);
            // Put logs back if send failed
            pendingLogs = [...logsToSend, ...pendingLogs];
        }
    }

    // Export logs as downloadable file
    function downloadLogs() {
        const logText = debugLogs.map(entry => {
            let line = `[${entry.timestamp}] [${entry.category}] ${entry.message}`;
            if (entry.data) {
                line += '\n  Data: ' + JSON.stringify(entry.data, null, 2);
            }
            return line;
        }).join('\n');

        const blob = new Blob([logText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `modaletta-voice-logs-${Date.now()}.txt`;
        a.click();
        URL.revokeObjectURL(url);
    }

    // Expose to window for manual download
    window.downloadVoiceLogs = downloadLogs;
    window.getVoiceLogs = () => debugLogs;
    window.flushVoiceLogs = flushLogsToServer;
    
    // Expose toggleDebugMode globally for the HTML onclick handler
    // (will be defined later, this just creates a placeholder)
    window.toggleDebugMode = null;

    // DOM Elements
    const elements = {
        agentSelect: document.getElementById('agent-select'),
        agentIdInput: document.getElementById('agent-id-input'),
        messagesContainer: document.getElementById('messages'),
        messageInput: document.getElementById('message-input'),
        sendBtn: document.getElementById('send-btn'),
        voiceBtn: document.getElementById('voice-btn'),
        voiceFeedback: document.getElementById('voice-feedback')
    };

    // State
    let currentAgentId = null;
    let currentProjectId = null;
    let isLoading = false;
    let recognition = null;
    let silenceTimeout = null;
    let maxRecordingTimeout = null;
    let textBeforeRecording = ''; // Text in input before we started recording
    let authState = { authenticated: false, user: null, authEnabled: false };
    
    // Message history state
    let oldestMessageId = null;
    let hasMoreMessages = true;
    let isLoadingHistory = false;
    let debugMode = localStorage.getItem('debugMode') === 'true';

    // ==========================================================================
    // User Metadata Collection
    // ==========================================================================

    /**
     * Collect metadata about the current user and their environment
     */
    function collectUserMetadata() {
        // Collect context metadata (user info is extracted server-side from JWT)
        const metadata = {
            // Time info
            local_time: new Date().toLocaleTimeString(),
            local_date: new Date().toLocaleDateString(),
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            
            // Device info
            device_type: getDeviceType(),
            platform: navigator.platform,
            language: navigator.language,
        };
        
        return metadata;
    }

    /**
     * Detect device type based on user agent and screen size
     */
    function getDeviceType() {
        const ua = navigator.userAgent.toLowerCase();
        
        if (/iphone|ipod|android.*mobile|windows phone|blackberry/i.test(ua)) {
            return 'mobile';
        } else if (/ipad|android(?!.*mobile)|tablet/i.test(ua)) {
            return 'tablet';
        } else {
            return 'desktop';
        }
    }

    // ==========================================================================
    // Authentication
    // ==========================================================================

    /**
     * Check authentication status from server
     */
    async function checkAuthStatus() {
        try {
            // Auth routes are at /auth/*, not /api/auth/*
            const response = await fetch('/auth/status', {
                credentials: 'include'  // Send cookies with request
            });
            if (response.ok) {
                authState = await response.json();
                authState.authEnabled = true;
                debugLog('AUTH', 'Auth status fetched', authState);
            } else if (response.status === 404) {
                // Auth endpoints not available - auth is disabled
                authState = { authenticated: false, user: null, authEnabled: false };
                debugLog('AUTH', 'Auth endpoints not available (disabled)');
            } else {
                debugLog('AUTH', 'Auth status check failed', { status: response.status });
            }
        } catch (error) {
            debugLog('AUTH', 'Auth status check error', { error: error.message });
            authState = { authenticated: false, user: null, authEnabled: false };
        }
        updateAuthUI();
        return authState;
    }

    /**
     * Update the auth section UI based on current auth state
     */
    function updateAuthUI() {
        const authSection = document.getElementById('auth-section');
        const userLabel = document.getElementById('user-label');
        
        // Update user label in input area (first name only)
        if (userLabel) {
            if (authState.authenticated && authState.user) {
                const fullName = authState.user.name || authState.user.email || '';
                const firstName = fullName.split(/\s+/)[0]; // First word
                userLabel.textContent = firstName ? `${firstName}:` : '';
            } else {
                userLabel.textContent = '';
            }
        }
        
        if (!authSection) return;

        if (!authState.authEnabled) {
            // Auth is disabled - hide the section
            authSection.innerHTML = '';
            authSection.style.display = 'none';
            return;
        }

        authSection.style.display = 'flex';

        if (authState.authenticated && authState.user) {
            // Logged in - show user info and logout button
            const userName = authState.user.name || authState.user.email;
            const userPicture = authState.user.picture;
            
            authSection.innerHTML = `
                <div class="user-info">
                    ${userPicture ? `<img src="${userPicture}" alt="${userName}" class="user-avatar">` : ''}
                    <span class="user-name">${escapeHtml(userName)}</span>
                </div>
                <a href="/auth/logout" class="auth-btn logout-btn">Logout</a>
            `;
        } else {
            // Not logged in - show login button
            authSection.innerHTML = `
                <a href="/auth/login" class="auth-btn login-btn">Sign in with Google</a>
            `;
        }
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Check for auth errors in URL and display them
     */
    function checkAuthErrors() {
        const urlParams = new URLSearchParams(window.location.search);
        const authError = urlParams.get('auth_error');
        if (authError) {
            debugLog('AUTH', 'Auth error from URL', { error: authError });
            let errorMessage = 'Authentication failed. Please try again.';
            switch (authError) {
                case 'invalid_state':
                    errorMessage = 'Authentication session expired. Please try again.';
                    break;
                case 'missing_params':
                    errorMessage = 'Authentication failed: missing parameters.';
                    break;
                case 'callback_failed':
                    errorMessage = 'Authentication callback failed. Please try again.';
                    break;
            }
            addMessage(errorMessage, 'system');
            // Clear the error from URL
            window.history.replaceState({}, '', window.location.pathname);
        }
    }

    // ==========================================================================
    // Message History
    // ==========================================================================

    /**
     * Load message history for the current agent
     */
    async function loadMessageHistory(before = null) {
        debugLog('HISTORY', 'loadMessageHistory called', { 
            currentAgentId, 
            isLoadingHistory, 
            hasMoreMessages, 
            before 
        });
        
        if (!currentAgentId || isLoadingHistory) {
            debugLog('HISTORY', 'Early return: no agent or already loading');
            return;
        }
        if (!before && !hasMoreMessages) {
            debugLog('HISTORY', 'Early return: no more messages');
            return;
        }
        
        isLoadingHistory = true;
        debugLog('HISTORY', 'Fetching message history...', { agent_id: currentAgentId, before });
        
        try {
            const params = new URLSearchParams({
                limit: '10',
            });
            if (before) {
                params.set('before', before);
            }
            if (currentProjectId) {
                params.set('project_id', currentProjectId);
            }
            
            const response = await fetch(
                `${API_BASE}/agents/${currentAgentId}/messages?${params}`,
                { credentials: 'include' }
            );
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            debugLog('HISTORY', 'Loaded messages', { count: data.messages.length, has_more: data.has_more });
            
            // Update pagination state
            hasMoreMessages = data.has_more;
            if (data.oldest_id) {
                oldestMessageId = data.oldest_id;
            }
            
            // Display messages (they come newest-first, so reverse for display)
            const messages = data.messages.reverse();
            const container = elements.messagesContainer;
            const scrollHeightBefore = container.scrollHeight;
            
            // Insert messages at the top
            for (const msg of messages) {
                prependHistoryMessage(msg);
            }
            
            // Preserve scroll position when loading older messages
            if (before) {
                const scrollHeightAfter = container.scrollHeight;
                const chatContainer = document.getElementById('chat-container');
                chatContainer.scrollTop += (scrollHeightAfter - scrollHeightBefore);
            }
            
        } catch (error) {
            debugLog('HISTORY', 'Failed to load message history', { error: error.message });
        } finally {
            isLoadingHistory = false;
        }
    }

    /**
     * Prepend a historical message to the chat (at the top)
     */
    function prependHistoryMessage(msg) {
        const messageType = msg.message_type || 'unknown';
        const content = extractMessageContent(msg);
        
        debugLog('HISTORY', 'Processing message', { id: msg.id, type: messageType, hasContent: !!content, content: content?.substring?.(0, 50) });
        
        if (!content) return;  // Skip empty messages
        
        // Determine display type based on message_type
        let displayType = 'system';
        if (messageType === 'user_message') {
            displayType = 'user';
        } else if (messageType === 'assistant_message') {
            displayType = 'agent';
        } else if (messageType === 'tool_call_message' || messageType === 'tool_return_message') {
            if (!debugMode) return;  // Skip tool messages unless debug mode
            displayType = 'debug';
        } else if (messageType === 'reasoning_message') {
            if (!debugMode) return;  // Skip reasoning unless debug mode
            displayType = 'debug reasoning';
        } else if (messageType === 'system_message') {
            displayType = 'system';
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${displayType}`;
        messageDiv.textContent = content;
        messageDiv.dataset.messageId = msg.id;
        
        // Insert at the beginning
        elements.messagesContainer.insertBefore(messageDiv, elements.messagesContainer.firstChild);
    }

    /**
     * Extract display content from a Letta message
     */
    function extractMessageContent(msg) {
        const messageType = msg.message_type || '';
        
        // Handle different message types
        if (messageType === 'user_message') {
            // User messages have content field
            if (typeof msg.content === 'string') {
                // Try to parse JSON content (our enriched format)
                try {
                    const parsed = JSON.parse(msg.content);
                    return parsed.message || msg.content;
                } catch {
                    return msg.content;
                }
            }
            return msg.content?.text || msg.content || '';
        } else if (messageType === 'assistant_message') {
            // Assistant messages - extract the actual response
            return msg.content || msg.assistant_message || '';
        } else if (messageType === 'tool_call_message') {
            // Tool call - show function name and args
            const toolCall = msg.tool_call || msg;
            return `🔧 Tool: ${toolCall.name || 'unknown'}(${JSON.stringify(toolCall.arguments || {})})`;
        } else if (messageType === 'tool_return_message') {
            // Tool return - show result
            return `📤 Tool result: ${msg.tool_return || msg.content || ''}`;
        } else if (messageType === 'reasoning_message') {
            // Internal reasoning
            return `💭 ${msg.reasoning || msg.content || ''}`;
        } else if (messageType === 'system_message') {
            return msg.content || msg.message || '';
        }
        
        // Fallback
        return msg.content || msg.message || '';
    }

    /**
     * Setup infinite scroll to load older messages
     */
    let scrollDebounceTimeout = null;
    
    function setupInfiniteScroll() {
        const chatContainer = document.getElementById('chat-container');
        
        chatContainer.addEventListener('scroll', () => {
            // Debounce scroll events
            if (scrollDebounceTimeout) return;
            
            // Check if scrolled near the top
            if (chatContainer.scrollTop < 100 && hasMoreMessages && !isLoadingHistory && currentAgentId) {
                scrollDebounceTimeout = setTimeout(() => {
                    scrollDebounceTimeout = null;
                }, 500);  // Prevent another scroll trigger for 500ms
                loadMessageHistory(oldestMessageId);
            }
        });
    }

    /**
     * Toggle debug mode
     */
    function toggleDebugMode() {
        debugMode = !debugMode;
        localStorage.setItem('debugMode', debugMode);
        updateDebugUI();
        debugLog('DEBUG', 'Debug mode toggled', { debugMode });
        
        // Reload history to show/hide debug messages
        if (currentAgentId) {
            elements.messagesContainer.innerHTML = '';
            oldestMessageId = null;
            hasMoreMessages = true;
            loadMessageHistory();
        }
    }
    // Expose to window for HTML onclick handler
    window.toggleDebugMode = toggleDebugMode;

    /**
     * Update debug toggle UI
     */
    function updateDebugUI() {
        const debugToggle = document.getElementById('debug-toggle');
        if (debugToggle) {
            debugToggle.checked = debugMode;
        }
    }

    // Audio context for beep sounds
    let audioContext = null;

    // Play a beep sound to indicate recording stopped
    function playStopBeep() {
        try {
            if (!audioContext) {
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.frequency.value = 800; // Hz
            oscillator.type = 'sine';

            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);

            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.2);

            debugLog('VOICE', 'Played stop beep');
        } catch (error) {
            debugLog('VOICE', 'Failed to play beep', { error: error.message });
        }
    }

    // Initialize the app
    async function init() {
        // Log browser info for debugging
        debugLog('INIT', 'App initializing', {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            vendor: navigator.vendor,
            language: navigator.language
        });

        // Check for auth errors first
        checkAuthErrors();

        // Check authentication status
        await checkAuthStatus();

        // Get initial config from URL params and server defaults
        const { agentId, projectId } = await getInitialConfig();
        currentProjectId = projectId;

        await loadAgents(agentId);
        setupEventListeners();
        setupVoiceInput();
        setupInfiniteScroll();
        autoResizeTextarea();
        updateDebugUI();

        // If we have an initial agent, load message history and focus input
        debugLog('INIT', 'After loadAgents', { currentAgentId, currentProjectId });
        if (currentAgentId) {
            debugLog('INIT', 'Calling loadMessageHistory from init');
            await loadMessageHistory();
            elements.messageInput.focus();
        } else {
            debugLog('INIT', 'No currentAgentId, skipping history load');
        }
    }

    // Get initial agent and project IDs from URL params or default config
    async function getInitialConfig() {
        const urlParams = new URLSearchParams(window.location.search);

        // Check URL parameters first
        let agentId = urlParams.get('agent');
        let projectId = urlParams.get('project');

        // Fall back to defaults from server config
        try {
            const response = await fetch(`${API_BASE}/config`);
            if (response.ok) {
                const config = await response.json();
                if (!agentId) {
                    agentId = config.default_agent_id || null;
                }
                if (!projectId) {
                    projectId = config.default_project_id || null;
                }
            }
        } catch (error) {
            console.error('Error fetching config:', error);
        }

        return { agentId, projectId };
    }

    // Load available agents from API
    async function loadAgents(initialAgentId = null) {
        try {
            // Include project_id in the query if set
            const url = currentProjectId
                ? `${API_BASE}/agents?project_id=${encodeURIComponent(currentProjectId)}`
                : `${API_BASE}/agents`;
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const agents = await response.json();
            elements.agentSelect.innerHTML = '<option value="">Select an agent</option>';

            if (agents.length === 0) {
                elements.agentSelect.innerHTML = '<option value="">No agents found</option>';
                // If we have an initial agent ID but no agents loaded, still use it
                if (initialAgentId) {
                    currentAgentId = initialAgentId;
                    elements.agentIdInput.value = initialAgentId;
                }
                return;
            }

            let foundInitialAgent = false;
            agents.forEach(agent => {
                const option = document.createElement('option');
                option.value = agent.id;
                option.textContent = agent.name || agent.id.substring(0, 8) + '...';
                // Pre-select if this is the initial agent
                if (initialAgentId && agent.id === initialAgentId) {
                    option.selected = true;
                    currentAgentId = agent.id;
                    foundInitialAgent = true;
                }
                elements.agentSelect.appendChild(option);
            });

            // If initial agent ID provided but not in list, put it in the manual input
            if (initialAgentId && !foundInitialAgent) {
                currentAgentId = initialAgentId;
                elements.agentIdInput.value = initialAgentId;
            }
        } catch (error) {
            console.error('Error loading agents:', error);
            elements.agentSelect.innerHTML = '<option value="">Error loading agents</option>';
            addMessage('Failed to load agents. Check your connection.', 'system');

            // If we have an initial agent ID, still use it even if list failed
            if (initialAgentId) {
                currentAgentId = initialAgentId;
                elements.agentIdInput.value = initialAgentId;
            }
        }
    }

    // Setup event listeners
    function setupEventListeners() {
        // Agent selection from dropdown
        elements.agentSelect.addEventListener('change', async (e) => {
            currentAgentId = e.target.value;
            elements.agentIdInput.value = '';
            debugLog('HISTORY', 'Agent changed via dropdown', { currentAgentId });
            if (currentAgentId) {
                // Clear messages and load history for new agent
                elements.messagesContainer.innerHTML = '';
                oldestMessageId = null;
                hasMoreMessages = true;
                debugLog('HISTORY', 'Calling loadMessageHistory from dropdown change');
                await loadMessageHistory();
                elements.messageInput.focus();
            }
        });

        // Manual agent ID input (debounced)
        let agentInputTimeout = null;
        elements.agentIdInput.addEventListener('input', (e) => {
            const value = e.target.value.trim();
            if (value) {
                currentAgentId = value;
                elements.agentSelect.value = '';
                
                // Debounce loading history on manual input
                clearTimeout(agentInputTimeout);
                agentInputTimeout = setTimeout(async () => {
                    elements.messagesContainer.innerHTML = '';
                    oldestMessageId = null;
                    hasMoreMessages = true;
                    await loadMessageHistory();
                }, 500);
            } else {
                currentAgentId = elements.agentSelect.value;
            }
        });

        // Send message on button click
        elements.sendBtn.addEventListener('click', sendMessage);

        // Send message on Enter (Shift+Enter for newline)
        elements.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Voice input toggle
        elements.voiceBtn.addEventListener('click', toggleVoiceInput);
    }

    // Auto-resize textarea as user types
    function autoResizeTextarea() {
        elements.messageInput.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });
    }

    // Send message to agent
    async function sendMessage() {
        const message = elements.messageInput.value.trim();

        if (!message) return;

        if (!currentAgentId) {
            addMessage('Please select an agent first.', 'system');
            return;
        }

        if (isLoading) return;

        // Add user message to chat (but don't clear input yet)
        addMessage(message, 'user');

        isLoading = true;
        elements.sendBtn.disabled = true;

        // Show loading indicator
        const loadingMsg = addMessage('Thinking...', 'loading');

        try {
            // Collect user metadata to send with message
            const metadata = collectUserMetadata();
            
            const response = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    agent_id: currentAgentId,
                    message: message,
                    role: 'user',
                    project_id: currentProjectId,
                    metadata: metadata,
                    include_debug: debugMode
                })
            });

            // Remove loading message
            loadingMsg.remove();

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            // SUCCESS - now clear the input (d)
            elements.messageInput.value = '';
            elements.messageInput.style.height = 'auto';

            const data = await response.json();

            // Process response messages
            if (data.messages && Array.isArray(data.messages)) {
                let hasResponse = false;
                const showDebug = data.include_debug || debugMode;
                
                data.messages.forEach(msg => {
                    const msgType = msg.message_type;
                    
                    // Always show assistant messages
                    if (msgType === 'assistant_message') {
                        const text = msg.content;
                        if (text) {
                            addMessage(text, 'agent');
                            hasResponse = true;
                        }
                    }
                    // Show debug messages if debug mode is on
                    else if (showDebug) {
                        if (msgType === 'reasoning_message') {
                            const text = msg.reasoning || msg.content;
                            if (text) {
                                addMessage(`💭 ${text}`, 'debug reasoning');
                            }
                        } else if (msgType === 'tool_call_message') {
                            const toolName = msg.tool_call?.name || msg.name || 'unknown';
                            const toolArgs = msg.tool_call?.arguments || msg.arguments || {};
                            addMessage(`🔧 Tool: ${toolName}(${JSON.stringify(toolArgs)})`, 'debug tool');
                        } else if (msgType === 'tool_return_message') {
                            const result = msg.tool_return || msg.content || '';
                            addMessage(`📤 Result: ${result}`, 'debug tool');
                        }
                    }
                });

                if (!hasResponse && !showDebug) {
                    addMessage('Agent responded but no message content found.', 'system');
                }
            } else {
                addMessage('Received empty response from agent.', 'system');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            loadingMsg.remove();
            addMessage(`Error: ${error.message}`, 'system');
            // On error, keep the text in input so user can retry
        } finally {
            isLoading = false;
            elements.sendBtn.disabled = false;
            elements.messageInput.focus();
        }
    }

    // Add message to chat display
    function addMessage(text, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.textContent = text;
        elements.messagesContainer.appendChild(messageDiv);

        // Scroll to bottom
        scrollToBottom();

        return messageDiv;
    }

    // Scroll chat to bottom
    function scrollToBottom() {
        const container = document.getElementById('chat-container');
        container.scrollTop = container.scrollHeight;
    }

    // Setup Web Speech API for voice input
    function setupVoiceInput() {
        debugLog('VOICE', 'Setting up voice input...');

        // Check for Web Speech API support (with webkit prefix for Safari)
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        debugLog('VOICE', 'SpeechRecognition API check', {
            'window.SpeechRecognition': !!window.SpeechRecognition,
            'window.webkitSpeechRecognition': !!window.webkitSpeechRecognition,
            'resolved': !!SpeechRecognition
        });

        if (!SpeechRecognition) {
            debugLog('VOICE', 'Speech Recognition NOT supported - hiding button');
            elements.voiceBtn.classList.add('unsupported');
            return;
        }

        debugLog('VOICE', 'Creating SpeechRecognition instance...');
        recognition = new SpeechRecognition();
        recognition.continuous = true; // Keep recording until user stops or max time
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        debugLog('VOICE', 'SpeechRecognition configured', {
            continuous: recognition.continuous,
            interimResults: recognition.interimResults,
            lang: recognition.lang
        });

        recognition.onstart = () => {
            debugLog('VOICE', 'EVENT: onstart - Recognition started');
            elements.voiceBtn.classList.add('listening');
            elements.voiceFeedback.classList.remove('hidden');
            clearTimeout(silenceTimeout);
            clearTimeout(maxRecordingTimeout);

            // Set max recording time (60 seconds) to prevent infinite recording
            maxRecordingTimeout = setTimeout(() => {
                debugLog('VOICE', 'Max recording time (60s) reached, stopping');
                if (recognition) {
                    recognition.stop();
                }
            }, 60000);
        };

        recognition.onend = () => {
            debugLog('VOICE', 'EVENT: onend - Recognition ended', {
                finalTranscript: elements.messageInput.value
            });
            elements.voiceBtn.classList.remove('listening');
            elements.voiceFeedback.classList.add('hidden');
            clearTimeout(silenceTimeout);
            clearTimeout(maxRecordingTimeout);

            // Play beep to indicate recording stopped (b)
            playStopBeep();

            // If we have text, focus the input so user can send or edit
            if (elements.messageInput.value.trim()) {
                debugLog('VOICE', 'Transcript captured, focusing input');
                elements.messageInput.focus();
            }
        };

        recognition.onaudiostart = () => {
            debugLog('VOICE', 'EVENT: onaudiostart - Audio capture started');
        };

        recognition.onaudioend = () => {
            debugLog('VOICE', 'EVENT: onaudioend - Audio capture ended');
        };

        recognition.onsoundstart = () => {
            debugLog('VOICE', 'EVENT: onsoundstart - Sound detected');
        };

        recognition.onsoundend = () => {
            debugLog('VOICE', 'EVENT: onsoundend - Sound ended');
        };

        recognition.onspeechstart = () => {
            debugLog('VOICE', 'EVENT: onspeechstart - Speech detected');
        };

        recognition.onspeechend = () => {
            debugLog('VOICE', 'EVENT: onspeechend - Speech ended (continuing to listen)');
            // Don't auto-stop on speech end - let user control when to stop
            // Only stop if we hit the max recording timeout (60s)
        };

        recognition.onresult = (event) => {
            debugLog('VOICE', 'EVENT: onresult', {
                resultIndex: event.resultIndex,
                resultsLength: event.results.length
            });

            // Build the full transcript from all results
            let fullTranscript = '';
            let hasInterim = false;

            for (let i = 0; i < event.results.length; i++) {
                const result = event.results[i];
                const transcript = result[0].transcript;
                const confidence = result[0].confidence;
                const isFinal = result.isFinal;

                debugLog('VOICE', `Result[${i}]`, {
                    transcript,
                    confidence,
                    isFinal
                });

                fullTranscript += transcript;
                if (!isFinal) {
                    hasInterim = true;
                }
            }

            debugLog('VOICE', 'Transcripts', {
                full: fullTranscript,
                hasInterim,
                textBeforeRecording
            });

            // Append to text that was in input before recording started (c)
            const separator = textBeforeRecording && fullTranscript ? ' ' : '';
            elements.messageInput.value = textBeforeRecording + separator + fullTranscript;

            // Auto-resize
            elements.messageInput.style.height = 'auto';
            elements.messageInput.style.height = Math.min(elements.messageInput.scrollHeight, 120) + 'px';
        };

        recognition.onerror = (event) => {
            debugLog('VOICE', 'EVENT: onerror', {
                error: event.error,
                message: event.message
            });

            elements.voiceBtn.classList.remove('listening');
            elements.voiceFeedback.classList.add('hidden');

            if (event.error === 'not-allowed') {
                addMessage('Microphone access denied. Please allow microphone access in your browser settings.', 'system');
            } else if (event.error === 'no-speech') {
                debugLog('VOICE', 'No speech detected - this is normal');
            } else if (event.error === 'aborted') {
                debugLog('VOICE', 'Recognition aborted');
            } else if (event.error === 'network') {
                addMessage('Voice input network error. Check your connection.', 'system');
            } else if (event.error === 'service-not-allowed') {
                addMessage('Speech recognition service not allowed.', 'system');
            } else {
                addMessage(`Voice input error: ${event.error}`, 'system');
            }
        };

        recognition.onnomatch = () => {
            debugLog('VOICE', 'EVENT: onnomatch - No speech match found');
        };

        debugLog('VOICE', 'Voice input setup complete');
    }

    // Toggle voice input on/off
    function toggleVoiceInput() {
        debugLog('VOICE', 'toggleVoiceInput called', {
            recognitionExists: !!recognition,
            isListening: elements.voiceBtn.classList.contains('listening')
        });

        if (!recognition) {
            debugLog('VOICE', 'No recognition object - not supported');
            addMessage('Voice input is not supported in this browser.', 'system');
            return;
        }

        if (elements.voiceBtn.classList.contains('listening')) {
            debugLog('VOICE', 'Stopping recognition (user clicked stop)', {
                currentTranscript: elements.messageInput.value
            });
            recognition.stop();
            // Clear any pending timeouts since user explicitly stopped
            clearTimeout(silenceTimeout);
            clearTimeout(maxRecordingTimeout);
            return;
        } else {
            debugLog('VOICE', 'Starting recognition...');
            // Clear any existing timeouts
            clearTimeout(silenceTimeout);
            clearTimeout(maxRecordingTimeout);

            // Save existing text so we can append to it (c)
            textBeforeRecording = elements.messageInput.value;
            debugLog('VOICE', 'Saved text before recording', { textBeforeRecording });

            try {
                recognition.start();
                debugLog('VOICE', 'recognition.start() called successfully');
            } catch (error) {
                debugLog('VOICE', 'recognition.start() threw error', {
                    name: error.name,
                    message: error.message
                });

                // Recognition may already be started
                if (error.name === 'InvalidStateError') {
                    debugLog('VOICE', 'InvalidStateError - stopping and retrying...');
                    recognition.stop();
                    setTimeout(() => {
                        // Re-save text before recording (it may have changed)
                        textBeforeRecording = elements.messageInput.value;
                        try {
                            recognition.start();
                            debugLog('VOICE', 'Retry start() succeeded');
                        } catch (e) {
                            debugLog('VOICE', 'Retry start() failed', {
                                name: e.name,
                                message: e.message
                            });
                        }
                    }, 100);
                } else {
                    addMessage('Failed to start voice input. Please try again.', 'system');
                }
            }
        }
    }

    // Start the app when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
