/**
 * SEVA AI HUD Frontend Application
 * Communicates with FastMCP backend via WebSocket/HTTP
 * Pure vanilla JS, zero dependencies, <25MB RAM
 */

class SevaHUD {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 2000;
        this.state = {
            audioState: 'standby',
            language: 'mr-IN',
            logs: [],
            ramUsage: 0,
            cpuUsage: 0,
            netStatus: 'OFFLINE',
            camStatus: 'ACTIVE',
            mode: 'DEMO'
        };
        this.init();
    }

    init() {
        this.bindElements();
        this.connectWebSocket();
        this.startSystemMonitor();
        this.setupKeyboardShortcuts();
        console.log('[SEVA HUD] Initialized');
    }

    bindElements() {
        this.elements = {
            languagePill: document.getElementById('languagePill'),
            statusText: document.getElementById('statusText'),
            logEntries: document.getElementById('logEntries'),
            ramUsage: document.getElementById('ramUsage'),
            cpuUsage: document.getElementById('cpuUsage'),
            netStatus: document.getElementById('netStatus'),
            camStatus: document.getElementById('camStatus'),
            modeIndicator: document.getElementById('modeIndicator'),
            ringSegments: document.querySelectorAll('.ring-segment')
        };
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/hud`;

        try {
            this.ws = new WebSocket(wsUrl);
            this.ws.onopen = () => this.onWsOpen();
            this.ws.onmessage = (e) => this.onWsMessage(e);
            this.ws.onclose = () => this.onWsClose();
            this.ws.onerror = (e) => this.onWsError(e);
        } catch (e) {
            console.error('[SEVA HUD] WebSocket connection failed:', e);
            this.scheduleReconnect();
        }
    }

    onWsOpen() {
        console.log('[SEVA HUD] WebSocket connected');
        this.reconnectAttempts = 0;
        this.addLog('system', 'WebSocket connected', 'success');
        this.send({ type: 'hud_ready', client: 'seva-hud' });
    }

    onWsMessage(event) {
        try {
            const msg = JSON.parse(event.data);
            this.handleMessage(msg);
        } catch (e) {
            console.error('[SEVA HUD] Message parse error:', e);
        }
    }

    onWsClose() {
        console.log('[SEVA HUD] WebSocket disconnected');
        this.addLog('system', 'WebSocket disconnected', 'warning');
        this.scheduleReconnect();
    }

    onWsError(error) {
        console.error('[SEVA HUD] WebSocket error:', error);
    }

    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => this.connectWebSocket(), this.reconnectDelay * this.reconnectAttempts);
        }
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }

    handleMessage(msg) {
        switch (msg.type) {
            case 'audio_state':
                this.setAudioState(msg.state);
                break;
            case 'language_change':
                this.setLanguage(msg.language);
                break;
            case 'progress_log':
                this.addLog(msg.source, msg.text, msg.level);
                break;
            case 'system_stats':
                this.updateSystemStats(msg.stats);
                break;
            case 'privacy_purge':
                this.onPrivacyPurge();
                break;
            case 'confirmation_required':
                this.showConfirmation(msg.summary);
                break;
            default:
                console.log('[SEVA HUD] Unknown message type:', msg.type);
        }
    }

    setAudioState(state) {
        this.state.audioState = state;
        this.elements.statusText.textContent = state.toUpperCase();
        this.elements.ringSegments.forEach(seg => {
            seg.dataset.active = seg.dataset.state === state;
        });
    }

    setLanguage(lang) {
        this.state.language = lang;
        const langNames = {
            'mr-IN': 'मराठी', 'hi-IN': 'हिंदी', 'gu-IN': 'ગુજરાતી',
            'kn-IN': 'ಕನ್ನಡ', 'ta-IN': 'தமிழ்', 'en-IN': 'ENGLISH'
        };
        this.elements.languagePill.textContent = langNames[lang] || lang;
    }

    addLog(source, text, level = 'info') {
        const entry = {
            id: Date.now(),
            time: new Date().toLocaleTimeString(),
            source,
            text,
            level
        };
        this.state.logs.unshift(entry);
        if (this.state.logs.length > 50) this.state.logs.pop();
        this.renderLogs();
    }

    renderLogs() {
        this.elements.logEntries.innerHTML = this.state.logs.map(log => `
            <div class="log-entry ${log.level}">
                <span class="log-icon">${this.getLogIcon(log.level)}</span>
                <span class="log-text">[${log.source}] ${log.text}</span>
                <span class="log-time">${log.time}</span>
            </div>
        `).join('');
    }

    getLogIcon(level) {
        const icons = { success: '✓', warning: '⚠', error: '✗', info: 'ℹ', active: '▶' };
        return icons[level] || '•';
    }

    updateSystemStats(stats) {
        this.state.ramUsage = stats.ram || this.state.ramUsage;
        this.state.cpuUsage = stats.cpu || this.state.cpuUsage;
        this.state.netStatus = stats.net ? 'ONLINE' : 'OFFLINE';
        this.state.camStatus = stats.cam ? 'ACTIVE' : 'IDLE';

        this.elements.ramUsage.textContent = `${this.state.ramUsage} MB`;
        this.elements.cpuUsage.textContent = `${this.state.cpuUsage}%`;
        this.elements.netStatus.textContent = this.state.netStatus;
        this.elements.netStatus.className = `status-value ${this.state.netStatus.toLowerCase()}`;
        this.elements.camStatus.textContent = this.state.camStatus;
        this.elements.camStatus.className = `status-value ${this.state.camStatus.toLowerCase()}`;
    }

    startSystemMonitor() {
        setInterval(() => this.collectSystemStats(), 2000);
    }

    async collectSystemStats() {
        try {
            const response = await fetch('/api/system/stats');
            if (response.ok) {
                const stats = await response.json();
                this.updateSystemStats(stats);
            }
        } catch (e) {
            this.updateSystemStats({ net: false });
        }
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'F11') {
                e.preventDefault();
                document.documentElement.requestFullscreen?.();
            }
            if (e.ctrlKey && e.key === 'l') {
                this.addLog('manual', 'Language toggle', 'info');
                this.send({ type: 'toggle_language' });
            }
            if (e.ctrlKey && e.key === 'p') {
                this.send({ type: 'privacy_purge' });
            }
        });
    }

    showConfirmation(summary) {
        this.addLog('safety_gate', summary, 'warning');
        this.setAudioState('thinking');
    }

    onPrivacyPurge() {
        this.addLog('privacy', '15-second walk-away detected - Data purged', 'error');
        this.setAudioState('standby');
        this.state.logs = [];
        this.renderLogs();
    }
}

window.sevaSpeak = (text) => {
    console.log('[SEVA HUD] TTS:', text);
};

document.addEventListener('DOMContentLoaded', () => {
    window.sevaHUD = new SevaHUD();
});