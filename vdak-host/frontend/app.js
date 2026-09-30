// vdak-host/frontend/app.js
// Client-side controller for SEVA AI Kiosk: Web Speech API, state polling, and stream management.

let currentLanguage = 'mr';
let isRecognizing = false;
let recognition = null;
let pollInterval = null;

const langConfigs = {
  mr: { code: 'mr-IN', name: 'मराठी', placeholder: 'उत्पन्नाचा दाखला काढायचा आहे...' },
  hi: { code: 'hi-IN', name: 'हिन्दी', placeholder: 'आय प्रमाण पत्र बनवाना है...' },
  en: { code: 'en-IN', name: 'English', placeholder: 'I want to apply for an Income Certificate...' }
};

document.addEventListener('DOMContentLoaded', () => {
  setupLanguageSelectors();
  setupSpeechRecognition();
  setupQuickButtons();
  setupResetButton();
  startStatePolling();
});

function setupLanguageSelectors() {
  ['mr', 'hi', 'en'].forEach(lang => {
    const btn = document.getElementById(`lang-${lang}`);
    if (btn) {
      btn.addEventListener('click', () => {
        currentLanguage = lang;
        ['mr', 'hi', 'en'].forEach(l => {
          const b = document.getElementById(`lang-${l}`);
          if (l === lang) {
            b.className = 'px-5 py-2.5 rounded-lg font-bold bg-amber-500 text-slate-950 text-lg';
          } else {
            b.className = 'px-5 py-2.5 rounded-lg font-bold bg-slate-700 hover:bg-slate-600 text-lg';
          }
        });
        appendLog('SYSTEM', `Language switched to ${langConfigs[lang].name}`);
        if (recognition) {
          recognition.lang = langConfigs[lang].code;
        }
      });
    }
  });
}

function setupSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const micBtn = document.getElementById('mic-btn');
  const liveSpeechText = document.getElementById('live-speech-text');

  if (!SpeechRecognition) {
    appendLog('WARN', 'Web Speech API not supported in this browser. Use Quick Action buttons.');
    return;
  }

  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = langConfigs[currentLanguage].code;

  recognition.onstart = () => {
    isRecognizing = true;
    micBtn.classList.add('ring-4', 'ring-red-500', 'animate-pulse');
    liveSpeechText.innerText = 'ऐकत आहे (Listening)...';
  };

  recognition.onresult = (event) => {
    let transcript = '';
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      transcript += event.results[i][0].transcript;
    }
    liveSpeechText.innerText = `"${transcript}"`;
    if (event.results[0].isFinal) {
      handleCitizenTask(transcript);
    }
  };

  recognition.onerror = (event) => {
    console.error('Speech error:', event.error);
    isRecognizing = false;
    micBtn.classList.remove('ring-4', 'ring-red-500', 'animate-pulse');
  };

  recognition.onend = () => {
    isRecognizing = false;
    micBtn.classList.remove('ring-4', 'ring-red-500', 'animate-pulse');
  };

  micBtn.addEventListener('click', () => {
    if (isRecognizing) {
      recognition.stop();
    } else {
      try {
        recognition.lang = langConfigs[currentLanguage].code;
        recognition.start();
      } catch (e) {
        console.error('Recognition start error:', e);
      }
    }
  });
}

function setupQuickButtons() {
  document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const task = btn.getAttribute('data-task');
      handleCitizenTask(task);
    });
  });
}

async function handleCitizenTask(taskText) {
  if (!taskText || !taskText.trim()) return;
  appendLog('CITIZEN', `Goal input: "${taskText}"`);

  try {
    const res = await fetch('/api/start-task', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: taskText, language: currentLanguage })
    });
    const data = await res.json();
    appendLog('ODAV:START', `Session ${data.session_id} initialized. Starting loop execution...`);
    
    // Automatically trigger first step
    triggerNextStep();
  } catch (err) {
    appendLog('ERROR', `Failed to start task: ${err.message}`);
  }
}

async function triggerNextStep() {
  try {
    const res = await fetch('/api/step', { method: 'POST' });
    const data = await res.json();

    if (data.detail) {
      appendLog('INFO', data.detail);
      return;
    }

    const dec = data.decision || {};
    appendLog('OBSERVE', `DOM Signature: ${data.signature_before}`);
    appendLog('DECIDE', `Action: [${dec.action}] -> Selector: "${dec.selector}" | Thought: ${dec.thought}`);
    appendLog('ACT', `Executed: ${data.execution_msg}`);
    appendLog('VERIFY', `Mutated: ${data.mutated} | Status: ${data.status}`);

    if (data.stalled) {
      document.getElementById('stall-warning').classList.remove('hidden');
    } else {
      document.getElementById('stall-warning').classList.add('hidden');
    }

    if (!data.finished && data.status !== 'budget_exhausted') {
      setTimeout(triggerNextStep, 1000);
    } else {
      appendLog('FINISH', `Session completed with status: ${data.status}`);
    }
  } catch (err) {
    appendLog('ERROR', `Step failure: ${err.message}`);
  }
}

function setupResetButton() {
  const resetBtn = document.getElementById('reset-btn');
  if (resetBtn) {
    resetBtn.addEventListener('click', async () => {
      await fetch('/api/reset', { method: 'POST' });
      appendLog('PURGE', 'Ephemeral data wiped. Kiosk reset to idle state.');
      document.getElementById('budget-counter').innerText = '8 / 8';
      document.getElementById('stall-warning').classList.add('hidden');
      document.getElementById('active-url').innerText = 'about:blank';
    });
  }
}

function startStatePolling() {
  setInterval(async () => {
    try {
      const res = await fetch('/api/session-state');
      if (!res.ok) return;
      const state = await res.json();
      if (state.active) {
        document.getElementById('budget-counter').innerText = `${state.max_steps - state.step} / ${state.max_steps}`;
        if (state.url) {
          document.getElementById('active-url').innerText = state.url;
        }
      }
    } catch (e) {
      // Background poll silently fails if offline
    }
  }, 2000);
}

function appendLog(phase, message) {
  const container = document.getElementById('audit-log-container');
  if (!container) return;

  const entry = document.createElement('div');
  const phaseLower = phase.toLowerCase();
  entry.className = `log-entry ${phaseLower}`;
  entry.innerHTML = `<span class="font-bold text-amber-400">[${phase}]</span> ${escapeHtml(message)}`;
  container.appendChild(entry);
  container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.innerText = text;
  return div.innerHTML;
}
