// MIA Agents Portal — main application logic
// Manages ElevenLabs voice sessions, agent switching, diagnostics, and handoffs.
// Vanilla JS — no bundler, no framework.

(function () {
    'use strict';

    const AGENTS = {
        orchestrator: {
            name: 'ORCHESTRATOR',
            title: 'The Feral Maestro',
            color: '#e8a835',
            agentId: '',
            next: 'evaluator',
        },
        evaluator: {
            name: 'EVALUATOR',
            title: 'The Unhinged Analyst',
            color: '#5b8fb9',
            agentId: '',
            next: 'executor',
        },
        executor: {
            name: 'EXECUTOR',
            title: 'The Obsessive Closer',
            color: '#00e5ff',
            agentId: '',
            next: 'evaluator',
        },
    };

    const MODE_AGENT = {
        plan: 'orchestrator',
        review: 'evaluator',
        execute: 'executor',
        diagnose: 'evaluator',
    };

    const API_BASE = (typeof window.MIA_AGENTS_API_BASE === 'string' && window.MIA_AGENTS_API_BASE)
        ? window.MIA_AGENTS_API_BASE.replace(/\/$/, '')
        : '';

    let activeAgent = null;
    let configLoaded = false;
    let lastEndedAgent = null;
    let configRetryDisabled = false;
    let voiceConsentAccepted = localStorage.getItem('agents-voice-consent') === 'yes';
    const missingI18nKeys = new Set();

    document.addEventListener('DOMContentLoaded', async function () {
        if (window.__I18N_READY__ && typeof window.__I18N_READY__.then === 'function') {
            try {
                await window.__I18N_READY__;
            } catch (_) {
                // The inline bootstrap already logs i18n initialization failures.
            }
        }
        loadTheme();
        setupCards();
        setupTaskModes();
        setupDiagnostics();
        setupLanguageState();
        setupKeyboardShortcuts();
        updateRecommendedAgent('plan');
        loadAgentConfigWithRetry();
        refreshAgentHealth();
    });

    async function loadAgentConfigWithRetry() {
        setAllCardsLoading(true);
        setStatusPill('statusConfig', t('agents.system.config_loading', 'Agent config loading...'), 'warn');

        const delays = [0, 1200, 2500, 5000];
        for (let i = 0; i < delays.length; i += 1) {
            if (delays[i] > 0) await sleep(delays[i]);
            const ok = await loadAgentConfig();
            if (ok) {
                configLoaded = true;
                setAllCardsLoading(false);
                refreshConfigStatus();
                setStatusPill('statusConfig', t('agents.system.config_ready', 'Agent config ready'), 'ok');
                updateDiagnostics('config-loaded');
                return;
            }
            if (configRetryDisabled) break;
        }

        configLoaded = true;
        setAllCardsLoading(false);
        refreshConfigStatus();
        setStatusPill('statusConfig', t('agents.system.config_missing', 'Agent config missing'), 'warn');
        updateDiagnostics('config-missing');
        showToast(t('agents.toast.config_unavailable', 'Agent configuration unavailable. Using cached data if present.'), 'info');
    }

    async function loadAgentConfig() {
        try {
            const resp = await fetchWithTimeout(`${API_BASE}/api/agents/config`, {}, 3000);
            if (resp.ok) {
                const config = await resp.json();
                Object.keys(AGENTS).forEach(function (name) {
                    if (config[name] && config[name].agent_id) {
                        AGENTS[name].agentId = config[name].agent_id;
                    }
                });
                return Object.values(AGENTS).some(function (agent) { return Boolean(agent.agentId); });
            }
            if (resp.status === 404) {
                configRetryDisabled = true;
            }
        } catch (_) {
            // API unavailable; fall back to localStorage.
        }

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

    async function refreshAgentHealth() {
        setStatusPill('statusApi', t('agents.system.api_checking', 'API checking...'), 'warn');
        try {
            const resp = await fetchWithTimeout(`${API_BASE}/api/agents/status`, {}, 3000);
            if (!resp.ok) throw new Error('status ' + resp.status);
            const status = await resp.json();
            setStatusPill('statusApi', t('agents.system.api_online', 'API online'), 'ok');
            updateDiagnostics('api-online', status);
        } catch (error) {
            setStatusPill('statusApi', t('agents.system.api_offline', 'API offline'), 'error');
            updateDiagnostics('api-offline', { error: error.message });
        }
    }

    function refreshConfigStatus() {
        Object.keys(AGENTS).forEach(function (name) {
            if (activeAgent === name) return;
            setAgentState(name, AGENTS[name].agentId ? 'idle' : 'unavailable');
        });
        updateDiagnostics('config-status');
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

    window.startVoiceSession = async function (agentName) {
        if (activeAgent === agentName) {
            endCurrentSession(true);
            return;
        }

        endCurrentSession(false);
        hideSessionSummary();

        const agent = AGENTS[agentName];
        if (!agent) return;

        showTimeline();
        setTimelineStep('config', 'active');

        if (!agent.agentId) {
            setTimelineStep('config', 'error');
            setAgentState(agentName, 'unavailable');
            showToast(t('agents.toast.agent_unavailable', 'This agent is not yet available. Please try again later or contact support.'), 'error');
            return;
        }

        if (!ensureVoiceConsent()) {
            hideTimeline();
            setAgentState(agentName, 'idle');
            return;
        }

        setTimelineStep('config', 'done');
        setAgentState(agentName, 'active');
        activeAgent = agentName;

        const placeholder = document.getElementById('chatPlaceholder');
        const wrapper = document.getElementById('widgetWrapper');
        const container = document.getElementById('chatContainer');

        placeholder.style.display = 'none';
        wrapper.style.display = 'block';
        container.className = 'chat-container ' + agentName + '-active';

        let widget;
        try {
            setTimelineStep('signed', 'active');
            const sigResp = await fetchWithTimeout(
                `${API_BASE}/api/agents/signed-url?agent=${encodeURIComponent(agentName)}`,
                {},
                5000
            );
            if (sigResp.ok) {
                const responseJson = await sigResp.json();
                widget = document.createElement('elevenlabs-convai');
                widget.setAttribute('signed-url', responseJson.signed_url);
                setTimelineStep('signed', 'done');
            } else {
                throw new Error('Signed-URL error ' + sigResp.status);
            }
        } catch (sigErr) {
            console.warn('Signed URL unavailable, falling back to public agent-id:', sigErr.message);
            showToast(t('agents.toast.signed_url_fallback', 'Signed URL unavailable; using public agent ID fallback for this session.'), 'info');
            setTimelineStep('signed', 'done');
            widget = document.createElement('elevenlabs-convai');
            widget.setAttribute('agent-id', agent.agentId);
        }

        setTimelineStep('widget', 'active');
        widget.addEventListener('elevenlabs-convai:connect', function () {
            setTimelineStep('widget', 'done');
            setTimelineStep('connected', 'done');
            setAgentState(agentName, 'active');
        });

        widget.addEventListener('elevenlabs-convai:disconnect', function () {
            if (activeAgent === agentName) endCurrentSession(true);
        });

        widget.addEventListener('elevenlabs-convai:error', function (e) {
            setTimelineStep('widget', 'error');
            showToast(t('agents.toast.connection_error', 'Connection error') + ': ' + formatErrorDetail(e.detail), 'error');
            endCurrentSession(true);
        });

        wrapper.appendChild(widget);
        setTimelineStep('widget', 'done');
        setTimelineStep('connected', 'active');
        updateTalkButton(agentName, true);
    };

    function ensureVoiceConsent() {
        if (voiceConsentAccepted) return true;
        const accepted = window.confirm(t(
            'agents.voice_consent.message',
            'Voice sessions may use your microphone and the ElevenLabs conversational AI service. Continue?'
        ));
        if (accepted) {
            voiceConsentAccepted = true;
            localStorage.setItem('agents-voice-consent', 'yes');
        }
        return accepted;
    }

    window.focusAgent = function (agentName) {
        const targetCard = document.getElementById('card-' + agentName);
        if (targetCard) {
            targetCard.focus({ preventScroll: true });
            targetCard.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
        document.querySelectorAll('.agent-card').forEach(function (card) {
            card.style.opacity = card.dataset.agent === agentName ? '1' : '0.5';
        });
        if (AGENTS[agentName] && AGENTS[agentName].agentId) {
            setStatus(agentName, t('agents.status.ready', 'Ready for voice session'));
        }
        setTimeout(function () {
            document.querySelectorAll('.agent-card').forEach(function (card) {
                card.style.opacity = '1';
            });
        }, 1500);
    };

    function endCurrentSession(showSummary) {
        const endedAgent = activeAgent;
        if (activeAgent) {
            setAgentState(activeAgent, AGENTS[activeAgent].agentId ? 'idle' : 'unavailable');
            updateTalkButton(activeAgent, false);
        }

        const wrapper = document.getElementById('widgetWrapper');
        wrapper.textContent = '';
        wrapper.style.display = 'none';

        document.getElementById('chatPlaceholder').style.display = 'flex';
        document.getElementById('chatContainer').className = 'chat-container';

        activeAgent = null;
        hideTimeline();

        if (showSummary && endedAgent) {
            lastEndedAgent = endedAgent;
            showSessionSummary(endedAgent);
        }
    }

    function setAgentState(agentName, state) {
        const card = document.getElementById('card-' + agentName);
        const dot = document.getElementById('dot-' + agentName);
        const statusLine = document.getElementById('status-' + agentName);

        if (card) card.classList.toggle('active', state === 'active');
        if (dot) dot.className = 'agent-status-dot ' + state;

        const messages = {
            idle: t('agents.status.idle', 'Idle — click Talk to start'),
            active: t('agents.status.active', 'Connected — listening...'),
            thinking: t('agents.status.thinking', 'Processing...'),
            error: t('agents.status.error', 'Connection error'),
            unavailable: t('agents.status.unavailable', 'Unavailable — missing agent ID'),
        };

        if (statusLine) {
            statusLine.className = 'agent-status-line' + (state !== 'idle' ? ' ' + state + '-text' : '');
            setStatusText(statusLine, messages[state] || state);
        }

        if (state !== 'active') updateTalkButton(agentName, false);
    }

    function setStatus(agentName, text, stateClass) {
        const statusLine = document.getElementById('status-' + agentName);
        if (!statusLine) return;
        if (stateClass) statusLine.className = 'agent-status-line ' + stateClass + '-text';
        setStatusText(statusLine, text);
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
        const unavailable = configLoaded && !AGENTS[agentName].agentId && !isActive;

        btn.textContent = '';
        const icon = document.createElement('i');
        const label = document.createElement('span');
        if (isActive) {
            icon.className = 'fas fa-stop';
            label.textContent = t('agents.buttons.end', 'End');
            btn.style.background = 'var(--error-color)';
            btn.disabled = false;
            btn.setAttribute('aria-disabled', 'false');
        } else {
            icon.className = 'fas fa-microphone';
            label.textContent = t('agents.buttons.talk', 'Talk');
            btn.style.background = '';
            btn.disabled = unavailable;
            btn.setAttribute('aria-disabled', unavailable ? 'true' : 'false');
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

    function setupTaskModes() {
        document.querySelectorAll('.mode-chip').forEach(function (button) {
            button.addEventListener('click', function () {
                const mode = button.getAttribute('data-mode');
                document.querySelectorAll('.mode-chip').forEach(function (chip) {
                    const active = chip === button;
                    chip.classList.toggle('active', active);
                    chip.setAttribute('aria-pressed', active ? 'true' : 'false');
                });
                updateRecommendedAgent(mode);
            });
        });
    }

    function updateRecommendedAgent(mode) {
        const agentName = MODE_AGENT[mode] || 'orchestrator';
        document.querySelectorAll('.agent-card').forEach(function (card) {
            const recommended = card.dataset.agent === agentName;
            card.classList.toggle('recommended', recommended);
            if (recommended) {
                card.setAttribute('data-recommended', t('agents.recommended', 'Recommended'));
            } else {
                card.removeAttribute('data-recommended');
            }
        });
        const helper = document.getElementById('modeHelper');
        if (helper) {
            const key = 'agents.modes.' + mode + '_helper';
            if (!helper.dataset.fallback) helper.dataset.fallback = helper.textContent.trim();
            helper.setAttribute('data-i18n-path', key);
            helper.textContent = t(key, helper.dataset.fallback);
        }
    }

    function setupDiagnostics() {
        const toggle = document.getElementById('diagnosticsToggle');
        const panel = document.getElementById('diagnosticsPanel');
        if (toggle && panel) {
            toggle.addEventListener('click', function () {
                const hidden = panel.hasAttribute('hidden');
                panel.toggleAttribute('hidden', !hidden);
                toggle.setAttribute('aria-expanded', hidden ? 'true' : 'false');
            });
        }

        const cta = document.getElementById('handoffCta');
        if (cta) {
            cta.addEventListener('click', async function () {
                const source = lastEndedAgent || 'orchestrator';
                cta.disabled = true;
                try {
                    await startVoiceSession(AGENTS[source].next);
                } catch (error) {
                    showToast(t('agents.toast.handoff_error', 'Could not start the next agent handoff.') + ' ' + formatErrorDetail(error), 'error');
                } finally {
                    cta.disabled = false;
                }
            });
        }
    }

    function updateDiagnostics(apiState, statusPayload) {
        const diagApi = document.getElementById('diagApi');
        if (diagApi && (apiState === 'api-online' || apiState === 'api-offline')) {
            diagApi.textContent = apiState === 'api-online'
                ? t('agents.system.api_online', 'API online')
                : t('agents.system.api_offline', 'API offline');
        }

        Object.keys(AGENTS).forEach(function (name) {
            const el = document.getElementById('diag-' + name);
            if (!el) return;
            const fromApi = statusPayload && statusPayload.agents && statusPayload.agents[name];
            const configured = fromApi ? fromApi.configured : Boolean(AGENTS[name].agentId);
            el.textContent = configured
                ? t('agents.system.configured', 'Configured')
                : t('agents.system.missing', 'Missing');
        });
    }

    function setStatusPill(id, text, state) {
        const el = document.getElementById(id);
        if (!el) return;
        el.classList.remove('ok', 'warn', 'error');
        if (state) el.classList.add(state);
        const span = el.querySelector('span');
        if (span) span.textContent = text;
    }

    function showTimeline() {
        const timeline = document.getElementById('connectionTimeline');
        if (!timeline) return;
        timeline.hidden = false;
        timeline.querySelectorAll('.timeline-step').forEach(function (step) {
            step.classList.remove('active', 'done', 'error');
        });
    }

    function hideTimeline() {
        const timeline = document.getElementById('connectionTimeline');
        if (timeline) timeline.hidden = true;
    }

    function setTimelineStep(stepName, state) {
        const step = document.querySelector('.timeline-step[data-step="' + stepName + '"]');
        if (!step) return;
        step.classList.remove('active', 'done', 'error');
        step.classList.add(state);

        if (state === 'error') {
            const panel = document.getElementById('diagnosticsPanel');
            const toggle = document.getElementById('diagnosticsToggle');
            if (panel && toggle) {
                panel.hidden = false;
                toggle.setAttribute('aria-expanded', 'true');
            }
        }
    }

    function showSessionSummary(sourceAgent) {
        const panel = document.getElementById('sessionSummary');
        const text = document.getElementById('summaryText');
        const cta = document.getElementById('handoffCta');
        if (!panel || !text || !cta) return;

        const next = AGENTS[sourceAgent].next;
        const key = 'agents.summary.after_' + sourceAgent;
        text.textContent = t(key, 'Session ended. Continue with ' + AGENTS[next].name + ' for the next step.');
        const label = cta.querySelector('span');
        if (label) label.textContent = t('agents.summary.start_' + next, 'Start ' + AGENTS[next].name);
        panel.hidden = false;
    }

    function hideSessionSummary() {
        const panel = document.getElementById('sessionSummary');
        if (panel) panel.hidden = true;
    }

    function setupLanguageState() {
        updateLanguageButtons();
        if (window.I18nLoader && typeof window.I18nLoader.onLanguageChange === 'function') {
            window.I18nLoader.onLanguageChange(function () {
                updateLanguageButtons();
                refreshDynamicCopy();
                updateThemeButton(document.body.classList.contains('light-theme'));
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
            } else {
                setAgentState(name, AGENTS[name].agentId ? 'idle' : 'unavailable');
                updateTalkButton(name, false);
            }
        });

        const activeMode = document.querySelector('.mode-chip.active');
        if (activeMode) updateRecommendedAgent(activeMode.getAttribute('data-mode'));
        relocalizeStatusPills();
        updateDiagnostics('language-refresh');
    }

    function relocalizeStatusPills() {
        const apiPill = document.getElementById('statusApi');
        if (apiPill) {
            if (apiPill.classList.contains('ok')) {
                setStatusPill('statusApi', t('agents.system.api_online', 'API online'), 'ok');
            } else if (apiPill.classList.contains('error')) {
                setStatusPill('statusApi', t('agents.system.api_offline', 'API offline'), 'error');
            } else {
                setStatusPill('statusApi', t('agents.system.api_checking', 'API checking...'), 'warn');
            }
        }

        const configPill = document.getElementById('statusConfig');
        if (configPill) {
            if (configPill.classList.contains('ok')) {
                setStatusPill('statusConfig', t('agents.system.config_ready', 'Agent config ready'), 'ok');
            } else if (configLoaded) {
                setStatusPill('statusConfig', t('agents.system.config_missing', 'Agent config missing'), 'warn');
            } else {
                setStatusPill('statusConfig', t('agents.system.config_loading', 'Agent config loading...'), 'warn');
            }
        }
    }

    function setupKeyboardShortcuts() {
        const agentKeys = { '1': 'orchestrator', '2': 'evaluator', '3': 'executor' };
        document.addEventListener('keydown', function (e) {
            const target = e.target;
            if (target && (
                target.tagName === 'INPUT' ||
                target.tagName === 'TEXTAREA' ||
                target.tagName === 'SELECT' ||
                target.isContentEditable ||
                (typeof target.closest === 'function' && target.closest('[contenteditable="true"], elevenlabs-convai'))
            )) return;
            if (e.altKey || e.ctrlKey || e.metaKey) return;

            if (agentKeys[e.key]) {
                focusAgent(agentKeys[e.key]);
            } else if (e.key === 'Escape') {
                endCurrentSession(true);
            } else if (e.key === 't' || e.key === 'T') {
                toggleTheme();
            }
        });
    }

    function loadTheme() {
        const saved = localStorage.getItem('team-theme') || 'dark';
        if (saved === 'light') applyLightTheme();
        updateThemeButton(saved === 'light');
    }

    window.toggleTheme = function () {
        const isLight = document.body.classList.contains('light-theme');
        if (isLight) {
            document.body.classList.remove('light-theme');
            localStorage.setItem('team-theme', 'dark');
            document.getElementById('themeIcon').className = 'fas fa-moon';
            updateThemeButton(false);
        } else {
            document.body.classList.add('light-theme');
            localStorage.setItem('team-theme', 'light');
            document.getElementById('themeIcon').className = 'fas fa-sun';
            updateThemeButton(true);
        }
    };

    function applyLightTheme() {
        document.body.classList.add('light-theme');
        const icon = document.getElementById('themeIcon');
        if (icon) icon.className = 'fas fa-sun';
        updateThemeButton(true);
    }

    function updateThemeButton(isLight) {
        const button = document.getElementById('themeBtn');
        if (!button) return;
        button.setAttribute('aria-pressed', isLight ? 'true' : 'false');
        button.setAttribute('aria-label', isLight
            ? t('agents.theme.switch_dark', 'Switch to dark theme')
            : t('agents.theme.switch_light', 'Switch to light theme'));
    }

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

        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'toast-close';
        closeBtn.setAttribute('aria-label', t('agents.toast.dismiss', 'Dismiss notification'));
        closeBtn.textContent = '×';
        closeBtn.addEventListener('click', function () { toast.remove(); });
        toast.appendChild(closeBtn);

        container.appendChild(toast);

        if (type !== 'error') {
            setTimeout(function () {
                toast.style.opacity = '0';
                toast.style.transition = '250ms ease';
                setTimeout(function () { toast.remove(); }, 300);
            }, 4000);
        }
    }

    function sleep(ms) {
        return new Promise(function (resolve) { setTimeout(resolve, ms); });
    }

    function t(path, fallback) {
        if (!window.I18nLoader || typeof window.I18nLoader.getValue !== 'function') return fallback;
        const value = window.I18nLoader.getValue(path);
        if (!value) {
            if (!missingI18nKeys.has(path)) {
                missingI18nKeys.add(path);
                console.warn('Missing i18n key:', path);
            }
            return fallback;
        }
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

    window.agentsApp = {
        startVoiceSession: window.startVoiceSession,
        endCurrentSession: function () { endCurrentSession(true); },
        showToast: showToast,
        refreshAgentHealth: refreshAgentHealth,
        getActiveAgent: function () { return activeAgent; },
        setAgentId: function (name, id) {
            if (AGENTS[name]) {
                AGENTS[name].agentId = id;
                localStorage.setItem('agent_id_' + name, id);
                configLoaded = true;
                refreshConfigStatus();
                setStatusPill('statusConfig', t('agents.system.config_ready', 'Agent config ready'), 'ok');
            }
        },
    };
})();
