// MIA Agents Portal — main application logic
// Manages ElevenLabs voice sessions, agent switching, and client tools.
// Vanilla JS — no bundler, no framework.

(function () {
    'use strict';

    // ─── Agent Configuration ───────────────────────────────────────────────────
    // Agent IDs are loaded from the API server (which reads them from .env).
    // Falls back to localStorage for offline/dev use.

    const AGENTS = {
        orchestrator: {
            name: 'ORCHESTRATOR',
            title: 'The Feral Maestro',
            color: '#e8a835',
            agentId: '',   // populated by loadAgentConfig()
        },
        evaluator: {
            name: 'EVALUATOR',
            title: 'The Unhinged Analyst',
            color: '#5b8fb9',
            agentId: '',
        },
        executor: {
            name: 'EXECUTOR',
            title: 'The Obsessive Closer',
            color: '#00e5ff',
            agentId: '',
        },
    };

    const API_BASE = 'http://localhost:8042';

    let activeAgent = null;

    // ─── Init ──────────────────────────────────────────────────────────────────

    document.addEventListener('DOMContentLoaded', function () {
        loadTheme();
        loadAgentConfig();
        setupKeyboardShortcuts();
    });

    // ─── Agent Config Loading ──────────────────────────────────────────────────

    async function loadAgentConfig() {
        // Try API server first, fall back to localStorage
        try {
            const resp = await fetch(`${API_BASE}/api/agents/config`, { signal: AbortSignal.timeout(2000) });
            if (resp.ok) {
                const config = await resp.json();
                Object.keys(AGENTS).forEach(function (name) {
                    if (config[name] && config[name].agent_id) {
                        AGENTS[name].agentId = config[name].agent_id;
                    }
                });
                return;
            }
        } catch (_) {
            // API not running — try localStorage
        }

        // localStorage fallback (set manually for dev)
        Object.keys(AGENTS).forEach(function (name) {
            const stored = localStorage.getItem('agent_id_' + name);
            if (stored) AGENTS[name].agentId = stored;
        });
    }

    // ─── Voice Session Management ──────────────────────────────────────────────

    window.startVoiceSession = function (agentName) {
        if (activeAgent === agentName) {
            // Already active — end it
            endCurrentSession();
            return;
        }

        endCurrentSession();

        const agent = AGENTS[agentName];
        if (!agent) return;

        if (!agent.agentId) {
            showToast('Agent ID not configured. Run deploy-agents.py first.', 'error');
            return;
        }

        setAgentState(agentName, 'active');
        activeAgent = agentName;

        // Show widget container
        const placeholder = document.getElementById('chatPlaceholder');
        const wrapper = document.getElementById('widgetWrapper');
        const container = document.getElementById('chatContainer');

        placeholder.style.display = 'none';
        wrapper.style.display = 'block';
        container.className = 'chat-container ' + agentName + '-active';

        // Create ElevenLabs convai widget
        const widget = document.createElement('elevenlabs-convai');
        widget.setAttribute('agent-id', agent.agentId);

        // Listen for widget events
        widget.addEventListener('elevenlabs-convai:connect', function () {
            setAgentState(agentName, 'active');
        });

        widget.addEventListener('elevenlabs-convai:disconnect', function () {
            if (activeAgent === agentName) endCurrentSession();
        });

        widget.addEventListener('elevenlabs-convai:error', function (e) {
            showToast('Connection error: ' + (e.detail || 'unknown'), 'error');
            endCurrentSession();
        });

        wrapper.appendChild(widget);

        // Update talk button to show "End"
        updateTalkButton(agentName, true);
    };

    window.focusAgent = function (agentName) {
        // Visual focus without starting a session — highlight the card
        document.querySelectorAll('.agent-card').forEach(function (c) {
            c.style.opacity = c.dataset.agent === agentName ? '1' : '0.5';
        });
        setStatus(agentName, 'Ready for voice session');
        setTimeout(function () {
            document.querySelectorAll('.agent-card').forEach(function (c) {
                c.style.opacity = '1';
            });
        }, 1500);
    };

    function endCurrentSession() {
        if (activeAgent) {
            setAgentState(activeAgent, 'idle');
            updateTalkButton(activeAgent, false);
        }

        // Remove widget
        const wrapper = document.getElementById('widgetWrapper');
        wrapper.innerHTML = '';
        wrapper.style.display = 'none';

        // Restore placeholder
        const placeholder = document.getElementById('chatPlaceholder');
        placeholder.style.display = 'flex';

        // Reset container styling
        document.getElementById('chatContainer').className = 'chat-container';

        activeAgent = null;
    }

    // ─── UI State ──────────────────────────────────────────────────────────────

    function setAgentState(agentName, state) {
        const card = document.getElementById('card-' + agentName);
        const dot = document.getElementById('dot-' + agentName);
        const statusLine = document.getElementById('status-' + agentName);

        // Reset card classes
        if (card) {
            card.classList.toggle('active', state === 'active');
        }

        // Update status dot
        if (dot) {
            dot.className = 'agent-status-dot ' + state;
        }

        // Update status text
        const messages = {
            idle:     'Idle — click Talk to start',
            active:   'Connected — listening...',
            thinking: 'Processing...',
            error:    'Connection error',
        };
        if (statusLine) {
            statusLine.className = 'agent-status-line' + (state !== 'idle' ? ' ' + state + '-text' : '');
            statusLine.innerHTML = '<i class="fas fa-circle-dot" style="font-size:0.5rem"></i><span>' + (messages[state] || state) + '</span>';
        }
    }

    function setStatus(agentName, text) {
        const statusLine = document.getElementById('status-' + agentName);
        if (statusLine) {
            statusLine.querySelector('span').textContent = text;
        }
    }

    function updateTalkButton(agentName, isActive) {
        const card = document.getElementById('card-' + agentName);
        if (!card) return;
        const btn = card.querySelector('.btn-talk');
        if (!btn) return;
        if (isActive) {
            btn.innerHTML = '<i class="fas fa-stop"></i> End';
            btn.style.background = 'var(--error-color)';
        } else {
            btn.innerHTML = '<i class="fas fa-microphone"></i> Talk';
            btn.style.background = '';
        }
    }

    // ─── Keyboard Shortcuts ────────────────────────────────────────────────────

    function setupKeyboardShortcuts() {
        const agentKeys = { '1': 'orchestrator', '2': 'evaluator', '3': 'executor' };

        document.addEventListener('keydown', function (e) {
            // Skip if typing in an input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

            if (agentKeys[e.key]) {
                startVoiceSession(agentKeys[e.key]);
            } else if (e.key === 'Escape') {
                endCurrentSession();
            } else if (e.key === 't' || e.key === 'T') {
                toggleTheme();
            }
        });
    }

    // ─── Theme ─────────────────────────────────────────────────────────────────

    function loadTheme() {
        // Share theme key with team portal for consistency
        const saved = localStorage.getItem('team-theme') || 'dark';
        if (saved === 'light') applyLightTheme();
    }

    window.toggleTheme = function () {
        const isLight = document.body.classList.contains('light-theme');
        if (isLight) {
            document.body.classList.remove('light-theme');
            localStorage.setItem('team-theme', 'dark');
            document.getElementById('themeIcon').className = 'fas fa-moon';
        } else {
            document.body.classList.add('light-theme');
            localStorage.setItem('team-theme', 'light');
            document.getElementById('themeIcon').className = 'fas fa-sun';
        }
    };

    function applyLightTheme() {
        document.body.classList.add('light-theme');
        const icon = document.getElementById('themeIcon');
        if (icon) icon.className = 'fas fa-sun';
    }

    // ─── Toast Notifications ───────────────────────────────────────────────────

    function showToast(message, type) {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = 'toast ' + (type || 'info');

        const iconMap = { error: 'fa-circle-xmark', success: 'fa-circle-check', info: 'fa-circle-info' };
        const icon = iconMap[type] || iconMap.info;

        toast.innerHTML = '<i class="fas ' + icon + '"></i><span>' + message + '</span>';
        container.appendChild(toast);

        setTimeout(function () {
            toast.style.opacity = '0';
            toast.style.transition = '250ms ease';
            setTimeout(function () { toast.remove(); }, 300);
        }, 4000);
    }

    // Expose for potential external use (e.g. from ElevenLabs client tool callbacks)
    window.agentsApp = {
        startVoiceSession: window.startVoiceSession,
        endCurrentSession: endCurrentSession,
        showToast: showToast,
        getActiveAgent: function () { return activeAgent; },
        setAgentId: function (name, id) {
            if (AGENTS[name]) {
                AGENTS[name].agentId = id;
                localStorage.setItem('agent_id_' + name, id);
            }
        },
    };

})();
