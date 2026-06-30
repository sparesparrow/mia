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

    // API_BASE is configurable via window.MIA_AGENTS_API_BASE (injected by server/template),
    // falls back to relative URL so it works behind any reverse proxy without hardcoding localhost.
    var API_BASE = (typeof window.MIA_AGENTS_API_BASE === 'string' && window.MIA_AGENTS_API_BASE)
        ? window.MIA_AGENTS_API_BASE.replace(/\/$/, '')
        : '';

    let activeAgent = null;
    let configLoaded = false;

    // ─── Init ──────────────────────────────────────────────────────────────────

    document.addEventListener('DOMContentLoaded', function () {
        loadTheme();
        setupCards();
        setupLanguageState();
        loadAgentConfigWithRetry();
        setupKeyboardShortcuts();
    });

    // ─── Agent Config Loading ──────────────────────────────────────────────────

    async function loadAgentConfigWithRetry() {
        setAllCardsLoading(true);
        const delays = [0, 2000, 4000, 8000];
        for (let i = 0; i < delays.length; i++) {
            if (delays[i] > 0) await sleep(delays[i]);
            const ok = await loadAgentConfig();
            if (ok) {
                configLoaded = true;
                setAllCardsLoading(false);
                refreshConfigStatus();
                return;
            }
        }
        setAllCardsLoading(false);
        configLoaded = true;
        refreshConfigStatus();
        // All retries exhausted — show toast but don't crash
        showToast(t('agents.toast.config_unavailable', 'Agent configuration unavailable. Using cached data if present.'), 'info');
    }

    async function loadAgentConfig() {
        // Try API server first, fall back to localStorage
        try {
            const resp = await fetchWithTimeout(`${API_BASE}/api/agents/config`, {}, 3000);
            if (resp.ok) {
                const config = await resp.json();
                Object.keys(AGENTS).forEach(function (name) {
                    if (config[name] && config[name].agent_id) {
                        AGENTS[name].agentId = config[name].agent_id;
                    }
                });
                return true;
            }
        } catch (_) {
            // API not running — try localStorage
        }

        // localStorage fallback (set manually for dev)
        let found = false;
        Object.keys(AGENTS).forEach(function (name) {
            const stored = localStorage.getItem('agent_id_' + name);
            if (stored) {
                AGENTS[name].agentId = stored;
                found = true;
            }
        });
        return found;
    }

    function setAllCardsLoading(loading) {
        Object.keys(AGENTS).forEach(function (name) {
            const card = document.getElementById('card-' + name);
            if (!card) return;
            if (loading) {
                card.classList.add('loading');
                card.setAttribute('aria-busy', 'true');
                setStatus(name, t('agents.status.loading', 'Loading agent configuration...'), 'thinking');
            } else {
                card.classList.remove('loading');
                card.removeAttribute('aria-busy');
            }
        });
    }

    function refreshConfigStatus() {
        Object.keys(AGENTS).forEach(function (name) {
            if (activeAgent === name) return;
            if (AGENTS[name].agentId) {
                setAgentState(name, 'idle');
            } else {
                setAgentState(name, 'unavailable');
            }
        });
    }

    // ─── Voice Session Management ──────────────────────────────────────────────

    window.startVoiceSession = async function (agentName) {
        if (activeAgent === agentName) {
            // Already active — end it
            endCurrentSession();
            return;
        }

        endCurrentSession();

        const agent = AGENTS[agentName];
        if (!agent) return;

        if (!agent.agentId) {
            setAgentState(agentName, 'unavailable');
            showToast(t('agents.toast.agent_unavailable', 'This agent is not yet available. Please try again later or contact support.'), 'error');
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

        // Fetch a signed URL so the agent session is authenticated and rate-limited server-side.
        // Falls back to public agent-id if the signed-url endpoint is unavailable (e.g. local dev).
        let widget;
        try {
            const sigResp = await fetchWithTimeout(
                `${API_BASE}/api/agents/signed-url?agent=${encodeURIComponent(agentName)}`,
                {},
                5000
            );
            if (sigResp.ok) {
                const { signed_url } = await sigResp.json();
                widget = document.createElement('elevenlabs-convai');
                widget.setAttribute('signed-url', signed_url);
            } else {
                throw new Error(`Signed-URL error ${sigResp.status}`);
            }
        } catch (sigErr) {
            // Fallback: use public agent-id (works for public agents in local dev)
            console.warn('Signed URL unavailable, falling back to public agent-id:', sigErr.message);
            widget = document.createElement('elevenlabs-convai');
            widget.setAttribute('agent-id', agent.agentId);
        }

        // Listen for widget events
        widget.addEventListener('elevenlabs-convai:connect', function () {
            setAgentState(agentName, 'active');
        });

        widget.addEventListener('elevenlabs-convai:disconnect', function () {
            if (activeAgent === agentName) endCurrentSession();
        });

        widget.addEventListener('elevenlabs-convai:error', function (e) {
            showToast(t('agents.toast.connection_error', 'Connection error') + ': ' + formatErrorDetail(e.detail), 'error');
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
        if (AGENTS[agentName] && AGENTS[agentName].agentId) {
            setStatus(agentName, t('agents.status.ready', 'Ready for voice session'));
        }
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
            idle:        t('agents.status.idle', 'Idle — click Talk to start'),
            active:      t('agents.status.active', 'Connected — listening...'),
            thinking:    t('agents.status.thinking', 'Processing...'),
            error:       t('agents.status.error', 'Connection error'),
            unavailable: t('agents.status.unavailable', 'Unavailable — missing agent ID'),
        };
        if (statusLine) {
            statusLine.className = 'agent-status-line' + (state !== 'idle' ? ' ' + state + '-text' : '');
            setStatusText(statusLine, messages[state] || state);
        }
    }

    function setStatus(agentName, text, stateClass) {
        const statusLine = document.getElementById('status-' + agentName);
        if (statusLine) {
            if (stateClass) {
                statusLine.className = 'agent-status-line ' + stateClass + '-text';
            }
            setStatusText(statusLine, text);
        }
    }

    function setStatusText(statusLine, text) {
        let icon = statusLine.querySelector('i');
        if (!icon) {
            icon = document.createElement('i');
            icon.className = 'fas fa-circle-dot';
            icon.style.fontSize = '0.5rem';
            statusLine.appendChild(icon);
        }

        let span = statusLine.querySelector('span');
        if (!span) {
            span = document.createElement('span');
            statusLine.appendChild(span);
        }
        span.textContent = text;
    }

    function updateTalkButton(agentName, isActive) {
        const card = document.getElementById('card-' + agentName);
        if (!card) return;
        const btn = card.querySelector('.btn-talk');
        if (!btn) return;
        btn.textContent = '';
        const icon = document.createElement('i');
        const label = document.createElement('span');
        if (isActive) {
            icon.className = 'fas fa-stop';
            label.textContent = t('agents.buttons.end', 'End');
            btn.style.background = 'var(--error-color)';
        } else {
            icon.className = 'fas fa-microphone';
            label.textContent = t('agents.buttons.talk', 'Talk');
            btn.style.background = '';
        }
        btn.appendChild(icon);
        btn.appendChild(label);
    }

    function setupCards() {
        document.querySelectorAll('.agent-card').forEach(function (card) {
            card.addEventListener('click', function (e) {
                if (e.target.closest('button, a')) return;
                focusAgent(card.dataset.agent);
            });
            card.addEventListener('keydown', function (e) {
                if (e.key !== 'Enter' && e.key !== ' ') return;
                e.preventDefault();
                focusAgent(card.dataset.agent);
            });
        });
    }

    function setupLanguageState() {
        updateLanguageButtons();
        if (window.I18nLoader && typeof window.I18nLoader.onLanguageChange === 'function') {
            window.I18nLoader.onLanguageChange(function () {
                updateLanguageButtons();
                refreshDynamicCopy();
            });
        }
    }

    function updateLanguageButtons() {
        const lang = window.I18nLoader ? window.I18nLoader.getLanguage() : (localStorage.getItem('mia-lang') || 'en');
        document.documentElement.lang = lang;
        document.querySelectorAll('.btn-lang').forEach(function (btn) {
            const active = btn.getAttribute('data-lang') === lang;
            btn.classList.toggle('active', active);
            btn.setAttribute('aria-pressed', active ? 'true' : 'false');
        });
    }

    function refreshDynamicCopy() {
        Object.keys(AGENTS).forEach(function (name) {
            if (activeAgent === name) {
                setAgentState(name, 'active');
                updateTalkButton(name, true);
            } else if (!configLoaded && !AGENTS[name].agentId) {
                setStatus(name, t('agents.status.loading', 'Loading agent configuration...'));
            } else if (AGENTS[name].agentId) {
                setAgentState(name, 'idle');
                updateTalkButton(name, false);
            } else {
                setAgentState(name, 'unavailable');
                updateTalkButton(name, false);
            }
        });
    }

    // ─── Keyboard Shortcuts ────────────────────────────────────────────────────

    function setupKeyboardShortcuts() {
        const agentKeys = { '1': 'orchestrator', '2': 'evaluator', '3': 'executor' };

        document.addEventListener('keydown', function (e) {
            // Skip if typing in an input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
            if (e.altKey || e.ctrlKey || e.metaKey) return;

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
        toast.setAttribute('role', type === 'error' ? 'alert' : 'status');

        const iconMap = { error: 'fa-circle-xmark', success: 'fa-circle-check', info: 'fa-circle-info' };
        const icon = iconMap[type] || iconMap.info;

        const iconEl = document.createElement('i');
        iconEl.className = 'fas ' + icon;
        const textEl = document.createElement('span');
        textEl.textContent = message;
        toast.appendChild(iconEl);
        toast.appendChild(textEl);
        container.appendChild(toast);

        setTimeout(function () {
            toast.style.opacity = '0';
            toast.style.transition = '250ms ease';
            setTimeout(function () { toast.remove(); }, 300);
        }, 4000);
    }

    // ─── Utilities ─────────────────────────────────────────────────────────────

    function sleep(ms) {
        return new Promise(function (resolve) { setTimeout(resolve, ms); });
    }

    function t(path, fallback) {
        if (!window.I18nLoader || typeof window.I18nLoader.getValue !== 'function') return fallback;
        const value = window.I18nLoader.getValue(path);
        if (!value) return fallback;
        if (typeof value === 'string') return value;
        const lang = window.I18nLoader.getLanguage ? window.I18nLoader.getLanguage() : 'en';
        return value[lang] || value.en || value.cs || fallback;
    }

    async function fetchWithTimeout(url, options, timeoutMs) {
        const fetchOptions = Object.assign({}, options || {});
        if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
            fetchOptions.signal = AbortSignal.timeout(timeoutMs);
            return fetch(url, fetchOptions);
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(function () { controller.abort(); }, timeoutMs);
        fetchOptions.signal = controller.signal;
        try {
            return await fetch(url, fetchOptions);
        } finally {
            clearTimeout(timeoutId);
        }
    }

    function formatErrorDetail(detail) {
        if (!detail) return 'unknown';
        if (typeof detail === 'string') return detail;
        if (detail.message) return detail.message;
        try {
            return JSON.stringify(detail);
        } catch (_) {
            return String(detail);
        }
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
                configLoaded = true;
                refreshConfigStatus();
            }
        },
    };

})();
