/**
 * ============================================================================
 * SEVA AI - Vernacular Digital Kiosk Client Engine
 * Touch-First Rural Kiosk Interface (Setu Kendras / Gram Panchayats)
 * 
 * Features:
 * - Native Web Speech API STT/TTS in Marathi (mr-IN), Hindi (hi-IN), English (en-IN)
 * - Push-to-Talk with mutual exclusion and phonetic fallbacks
 * - Live MJPEG Viewport Stream (/api/stream) with exponential backoff reconnect
 * - Canvas targeting reticle overlay with coordinate clamping [0, 1280] x [0, 720]
 * - Real-time ODAV Audit Feed (Observe-Decide-Act-Verify) with state signatures
 * - Hard 8-step budget visual indicator
 * - Human Checkpoint modal with 12-key virtual numeric keypad (0-9, Clear, Back)
 * - Ephemeral data purge (DPDP Act 2023 compliance) via /api/reset
 * ============================================================================
 */

(function () {
  'use strict';

  // --- Multi-Lingual Translation & Prompt Matrices ---
  const I18N = {
    'mr-IN': {
      code: 'mr-IN',
      name: 'मराठी',
      subtitle: 'महाराष्ट्र शासन नागरिक ई-सेवा व्हॉईस असिस्टंट',
      viewport_title: 'थेट स्क्रीन कास्ट (CDP Screencast Viewport)',
      feedback_label: 'सिस्टीम प्रतिसाद (Voice Feedback)',
      input_label: 'नागरिक मागणी (बोला किंवा प्रविष्ट करा):',
      input_placeholder: 'उदा. मला उत्पन्नाचा दाखला हवा आहे...',
      start_btn: 'सुरू करा (Start Service)',
      reset_btn: 'रद्द करा (Reset)',
      purge_btn: 'डेटा नष्ट करा (Purge)',
      budget_title: 'पायरी अंदाजपत्रक (Step Budget)',
      budget_subtitle: 'कमाल ८ पुनरावृत्ती मर्यादा (Max 8 Steps)',
      steps_label: 'पायऱ्या (Steps)',
      audit_title: 'ODAV रिअल-टाइम ऑडिट फीड (Audit Feed)',
      clear_feed: 'साफ करा (Clear)',
      quick_title: 'त्वरित सेवा निवडा (Quick Touch Prompts):',
      chip_income: 'उत्पन्नाचा दाखला (Income)',
      chip_satbara: '७/१२ सातबारा (Satbara)',
      chip_mahadbt: 'शेतकरी अनुदान (MahaDBT)',
      chip_ration: 'रेशन कार्ड सेवा (Ration)',
      prompt_income: 'मला उत्पन्नाचा दाखला काढायचा आहे',
      prompt_satbara: 'आमच्या शेताचा सातबारा उतारा दाखवा',
      prompt_mahadbt: 'नवीन शेतकरी अनुदानासाठी अर्ज करा',
      prompt_ration: 'माझे रेशन कार्ड पात्रता व धान्य तपासा',
      checkpoint_title: 'सुरक्षा पडताळणी (Human Checkpoint)',
      checkpoint_subtitle: 'नागरिक पडताळणी: ६ अंकी OTP प्रविष्ट करा',
      checkpoint_prompt: 'आपल्या नोंदणीकृत मोबाईल क्रमांकावर पाठवलेला ६ अंकी OTP टाका:',
      submit_otp: 'OTP सादर करा (Submit)',
      cancel_otp: 'रद्द करा (Cancel)',
      stalled_warning: '⚠️ सिस्टीम स्तब्ध झाली आहे. कृपया थांबा किंवा पुन्हा प्रयत्न करा.',
      purge_success: 'सर्व खाजगी माहिती तात्काळ नष्ट केली गेली आहे (DPDP Act 2023).',
      initial_greeting: 'नमस्कार! मी सेवा एआय आहे. आपल्याला कोणत्या शासकीय सेवेसाठी मदत हवी आहे?',
      reconnecting: 'स्ट्रीम पुन्हा जोडत आहे...',
      stream_connected: '25 FPS | जोडले गेले (Connected)'
    },
    'hi-IN': {
      code: 'hi-IN',
      name: 'हिंदी',
      subtitle: 'महाराष्ट्र शासन नागरिक ई-सेवा वॉयस असिस्टेंट',
      viewport_title: 'लाइव स्क्रीन कास्ट (CDP Screencast Viewport)',
      feedback_label: 'सिस्टम उत्तर (Voice Feedback)',
      input_label: 'नागरिक अनुरोध (बोलें या लिखें):',
      input_placeholder: 'उदा. मुझे आय प्रमाण पत्र चाहिए...',
      start_btn: 'शुरू करें (Start Service)',
      reset_btn: 'रद्द करें (Reset)',
      purge_btn: 'डेटा हटाएं (Purge)',
      budget_title: 'चरण सीमा (Step Budget)',
      budget_subtitle: 'अधिकतम ८ चरण सीमा (Max 8 Steps)',
      steps_label: 'चरण (Steps)',
      audit_title: 'ODAV रियल-टाइम ऑडिट फीड (Audit Feed)',
      clear_feed: 'साफ करें (Clear)',
      quick_title: 'त्वरित सेवा चुनें (Quick Touch Prompts):',
      chip_income: 'आय प्रमाण पत्र (Income)',
      chip_satbara: '७/१२ खतौनी (Satbara)',
      chip_mahadbt: 'किसान सब्सिडी (MahaDBT)',
      chip_ration: 'राशन कार्ड सेवा (Ration)',
      prompt_income: 'मुझे तहसीलदार आय प्रमाण पत्र के लिए आवेदन करना है',
      prompt_satbara: 'मेरे खेत का 7/12 सातबारा खतौनी रिकॉर्ड दिखाएं',
      prompt_mahadbt: 'किसान कृषि यंत्र सब्सिडी के लिए आवेदन करें',
      prompt_ration: 'राशन कार्ड में नाम और अनाज कोटा चेक करें',
      checkpoint_title: 'सुरक्षा सत्यापन (Human Checkpoint)',
      checkpoint_subtitle: 'नागरिक सत्यापन: ६ अंकों का OTP दर्ज करें',
      checkpoint_prompt: 'कृपया मोबाइल पर प्राप्त हुआ ६ अंकों का OTP दर्ज करें:',
      submit_otp: 'OTP जमा करें (Submit)',
      cancel_otp: 'रद्द करें (Cancel)',
      stalled_warning: '⚠️ सिस्टम में ठहराव आया है। कृपया प्रतीक्षा करें।',
      purge_success: 'समस्त व्यक्तिगत डेटा तुरंत मिटा दिया गया है (DPDP Act 2023).',
      initial_greeting: 'नमस्ते! मैं सेवा एआई हूँ। आपको किस नागरिक सेवा के लिए सहायता चाहिए?',
      reconnecting: 'स्ट्रीम पुनः कनेक्ट हो रही है...',
      stream_connected: '25 FPS | कनेक्टेड (Connected)'
    },
    'en-IN': {
      code: 'en-IN',
      name: 'English',
      subtitle: 'Government of Maharashtra Citizen e-Services Kiosk Assistant',
      viewport_title: 'Live CDP Screencast Viewport',
      feedback_label: 'Voice Feedback',
      input_label: 'Citizen Request (Speak or Type):',
      input_placeholder: 'e.g. I need an Income Certificate...',
      start_btn: 'Start Service',
      reset_btn: 'Reset Session',
      purge_btn: 'Data Purge',
      budget_title: 'Step Budget',
      budget_subtitle: 'Maximum 8 Iterations Ceiling',
      steps_label: 'Steps',
      audit_title: 'ODAV Real-Time Audit Feed',
      clear_feed: 'Clear Feed',
      quick_title: 'Quick Touch Prompts:',
      chip_income: 'Income Certificate',
      chip_satbara: '7/12 Land Record',
      chip_mahadbt: 'Farmer Subsidy',
      chip_ration: 'Ration Services',
      prompt_income: 'I want to apply for a Tahsildar Income Certificate',
      prompt_satbara: 'Please fetch my 7/12 Satbara land record',
      prompt_mahadbt: 'Apply for Farmer Agriculture Subsidy scheme',
      prompt_ration: 'Check my ration card status and grain allocation',
      checkpoint_title: 'Human Checkpoint',
      checkpoint_subtitle: 'Citizen Verification: Enter 6-digit OTP',
      checkpoint_prompt: 'Please enter the 6-digit OTP received on your mobile phone:',
      submit_otp: 'Submit OTP',
      cancel_otp: 'Cancel',
      stalled_warning: '⚠️ Action stalled across 2 consecutive cycles. Please wait.',
      purge_success: 'All citizen session memory purged successfully (DPDP Act 2023).',
      initial_greeting: 'Welcome to SEVA AI! How can I assist you with public services today?',
      reconnecting: 'Reconnecting stream...',
      stream_connected: '25 FPS | Connected'
    }
  };

  // --- Kiosk State Model ---
  const state = {
    language: 'mr-IN',
    sessionId: null,
    active: false,
    step: 0,
    maxSteps: 8,
    isListening: false,
    isSpeaking: false,
    otpBuffer: '',
    lastTapTime: 0,
    reconnectAttempts: 0,
    streamTimer: null,
    lastAction: null,
    stalled: false,
    finished: false,
    waitingCheckpoint: false,
    reticle: { x: 0, y: 0, visible: false, label: '' }
  };

  // --- DOM Elements Cache ---
  const el = {
    // Header & Controls
    headerSubtitle: document.getElementById('header-subtitle'),
    langButtons: document.querySelectorAll('.lang-btn'),
    purgeBtn: document.getElementById('purge-btn'),
    purgeBtnText: document.getElementById('purge-btn-text'),
    
    // Viewport & Reticle
    viewportTitle: document.getElementById('viewport-title'),
    viewportContainer: document.getElementById('viewport-container'),
    streamImg: document.getElementById('stream-img'),
    reticleCanvas: document.getElementById('reticle-canvas'),
    streamStatus: document.getElementById('stream-status'),
    streamReconnectOverlay: document.getElementById('stream-reconnect-overlay'),
    reconnectText: document.getElementById('reconnect-text'),
    
    // Voice & Inputs
    feedbackBanner: document.getElementById('voice-feedback-banner'),
    feedbackLabel: document.getElementById('feedback-label'),
    feedbackText: document.getElementById('feedback-text'),
    audioWaves: document.getElementById('audio-waves'),
    micBtn: document.getElementById('mic-btn'),
    inputLabel: document.getElementById('input-label'),
    voiceInput: document.getElementById('voice-input'),
    clearInputBtn: document.getElementById('clear-input-btn'),
    startBtn: document.getElementById('start-btn'),
    startBtnText: document.getElementById('start-btn-text'),
    resetBtn: document.getElementById('reset-btn'),
    resetBtnText: document.getElementById('reset-btn-text'),
    
    // Quick Chips
    quickTitle: document.getElementById('quick-chips-title'),
    promptChips: document.getElementById('prompt-chips'),
    chipIncome: document.getElementById('chip-income'),
    chipSatbara: document.getElementById('chip-satbara'),
    chipMahadbt: document.getElementById('chip-mahadbt'),
    chipRation: document.getElementById('chip-ration'),
    
    // Budget & Audit Feed
    budgetTitle: document.getElementById('budget-title'),
    budgetSubtitle: document.getElementById('budget-subtitle'),
    stepCount: document.getElementById('step-count'),
    maxSteps: document.getElementById('max-steps'),
    stepSegments: document.querySelectorAll('.step-segment'),
    sessionIdDisplay: document.getElementById('session-id-display'),
    stallBadge: document.getElementById('stall-badge'),
    taskStatusBadge: document.getElementById('task-status-badge'),
    auditTitle: document.getElementById('audit-title'),
    odavFeed: document.getElementById('odav-feed'),
    clearFeedBtn: document.getElementById('clear-feed-btn'),
    
    // Checkpoint Modal
    checkpointModal: document.getElementById('checkpoint-modal'),
    checkpointCard: document.getElementById('checkpoint-card'),
    checkpointTitle: document.getElementById('checkpoint-title'),
    checkpointSubtitle: document.getElementById('checkpoint-subtitle'),
    checkpointPrompt: document.getElementById('checkpoint-prompt'),
    otpSlots: document.querySelectorAll('.otp-slot'),
    otpInput: document.getElementById('otp-input'),
    keypad: document.getElementById('keypad'),
    submitOtpBtn: document.getElementById('submit-otp-btn'),
    submitOtpText: document.getElementById('submit-otp-text'),
    cancelOtpBtn: document.getElementById('cancel-otp-btn'),
    cancelOtpText: document.getElementById('cancel-otp-text'),
    closeModalX: document.getElementById('close-modal-x'),
    
    // Toast Container
    toastContainer: document.getElementById('toast-container')
  };

  // Canvas 2D context for Reticle Overlay
  let reticleCtx = null;
  if (el.reticleCanvas && el.reticleCanvas.getContext) {
    reticleCtx = el.reticleCanvas.getContext('2d');
  }

  // =========================================================================
  // 1. Web Speech API Integration (STT & TTS with Mutual Exclusion)
  // =========================================================================

  let recognition = null;
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = state.language;

    recognition.onstart = function () {
      state.isListening = true;
      if (el.micBtn) {
        el.micBtn.classList.add('listening');
      }
      showToast('माईक सुरू आहे - कृपया बोला... (Listening...)', 'info');
    };

    recognition.onresult = function (event) {
      if (event.results && event.results.length > 0) {
        const transcript = event.results[0][0].transcript.trim();
        if (el.voiceInput) {
          el.voiceInput.value = transcript;
          if (el.clearInputBtn) el.clearInputBtn.classList.remove('hidden');
        }
        stopListening();
        // Automatically start service with spoken request
        handleStartTask();
      }
    };

    recognition.onerror = function (event) {
      console.warn('[SPEECH STT] Recognition error:', event.error);
      stopListening();
    };

    recognition.onend = function () {
      stopListening();
    };
  } else {
    console.info('[SPEECH STT] Native SpeechRecognition not available in this browser.');
  }

  function startListening() {
    // Mutual Exclusion: cancel any currently playing TTS before listening
    stopSpeaking();

    if (!recognition) {
      showToast('या ब्राउझरमध्ये व्हॉईस इनपुट समर्थित नाही. कृपया टाइप करा.', 'warning');
      if (el.voiceInput) el.voiceInput.focus();
      return;
    }

    try {
      recognition.lang = state.language;
      recognition.start();
    } catch (e) {
      console.warn('[SPEECH STT] start() failed:', e);
      stopListening();
    }
  }

  function stopListening() {
    state.isListening = false;
    if (el.micBtn) {
      el.micBtn.classList.remove('listening');
    }
    if (recognition) {
      try { recognition.stop(); } catch (_) {}
    }
  }

  function speakFeedback(text) {
    if (!text || typeof text !== 'string') return;
    
    // Update banner text
    if (el.feedbackText) {
      el.feedbackText.textContent = text;
    }

    if (!('speechSynthesis' in window)) {
      console.info('[SPEECH TTS] SpeechSynthesis API not supported.');
      return;
    }

    // Mutual Exclusion: cancel current recognition if speaking
    if (state.isListening) {
      stopListening();
    }

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = state.language;
    utterance.rate = 0.95;
    utterance.pitch = 1.0;

    // Pick best available vernacular voice
    const voices = window.speechSynthesis.getVoices();
    const targetPrefix = state.language.split('-')[0]; // 'mr', 'hi', or 'en'
    let selectedVoice = null;

    for (let i = 0; i < voices.length; i++) {
      const v = voices[i];
      if (v.lang === state.language || v.lang.replace('_', '-') === state.language) {
        selectedVoice = v;
        break;
      }
    }

    // Fallback search
    if (!selectedVoice) {
      for (let i = 0; i < voices.length; i++) {
        const v = voices[i];
        if (v.lang.startsWith(targetPrefix)) {
          selectedVoice = v;
          break;
        }
      }
    }

    if (selectedVoice) {
      utterance.voice = selectedVoice;
    }

    utterance.onstart = function () {
      state.isSpeaking = true;
      if (el.audioWaves) el.audioWaves.classList.remove('hidden');
    };

    utterance.onend = function () {
      state.isSpeaking = false;
      if (el.audioWaves) el.audioWaves.classList.add('hidden');
    };

    utterance.onerror = function () {
      state.isSpeaking = false;
      if (el.audioWaves) el.audioWaves.classList.add('hidden');
    };

    window.speechSynthesis.speak(utterance);
  }

  function stopSpeaking() {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    state.isSpeaking = false;
    if (el.audioWaves) el.audioWaves.classList.add('hidden');
  }

  // Pre-load voices
  if ('speechSynthesis' in window) {
    window.speechSynthesis.onvoiceschanged = function () {
      window.speechSynthesis.getVoices();
    };
  }

  // =========================================================================
  // 2. Stream Reconnection & Reticle Overlay Management
  // =========================================================================

  function initStream() {
    if (!el.streamImg) return;

    el.streamImg.onerror = function () {
      handleStreamDisconnect();
    };

    el.streamImg.onload = function () {
      state.reconnectAttempts = 0;
      if (el.streamReconnectOverlay) el.streamReconnectOverlay.classList.add('hidden');
      if (el.streamStatus) {
        el.streamStatus.textContent = I18N[state.language].stream_connected;
        el.streamStatus.className = 'px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-700';
      }
    };
  }

  function handleStreamDisconnect() {
    if (el.streamReconnectOverlay) el.streamReconnectOverlay.classList.remove('hidden');
    if (el.streamStatus) {
      el.streamStatus.textContent = 'Disconnected | Reconnecting...';
      el.streamStatus.className = 'px-2 py-0.5 rounded bg-red-950 text-red-300 border border-red-700';
    }

    // Exponential backoff capped at 5000ms (1s, 2s, 4s, 5s)
    const baseDelay = 1000;
    const delay = Math.min(baseDelay * Math.pow(2, state.reconnectAttempts), 5000);
    state.reconnectAttempts++;

    clearTimeout(state.streamTimer);
    state.streamTimer = setTimeout(function () {
      if (el.streamImg) {
        el.streamImg.src = '/api/stream?retry=' + Date.now();
      }
    }, delay);
  }

  // Reticle Coordinate Clamping & Canvas Drawing
  function clampCoordinates(x, y) {
    const clampedX = Math.max(0, Math.min(1280, x));
    const clampedY = Math.max(0, Math.min(720, y));
    return { x: clampedX, y: clampedY };
  }

  function drawReticle(rawX, rawY, label, actionType) {
    if (!reticleCtx || !el.reticleCanvas) return;

    const { x, y } = clampCoordinates(rawX, rawY);
    state.reticle = { x, y, visible: true, label };

    reticleCtx.clearRect(0, 0, el.reticleCanvas.width, el.reticleCanvas.height);

    // Outer pulsed target ring
    reticleCtx.save();
    reticleCtx.beginPath();
    reticleCtx.arc(x, y, 32, 0, Math.PI * 2);
    reticleCtx.strokeStyle = '#38bdf8';
    reticleCtx.lineWidth = 3;
    reticleCtx.setLineDash([6, 4]);
    reticleCtx.stroke();

    // Inner solid precision circle
    reticleCtx.beginPath();
    reticleCtx.arc(x, y, 8, 0, Math.PI * 2);
    reticleCtx.fillStyle = actionType === 'click' ? '#ef4444' : '#10b981';
    reticleCtx.fill();
    reticleCtx.strokeStyle = '#ffffff';
    reticleCtx.lineWidth = 2;
    reticleCtx.setLineDash([]);
    reticleCtx.stroke();

    // Crosshairs
    reticleCtx.beginPath();
    reticleCtx.moveTo(x - 44, y);
    reticleCtx.lineTo(x + 44, y);
    reticleCtx.moveTo(x, y - 44);
    reticleCtx.lineTo(x, y + 44);
    reticleCtx.strokeStyle = 'rgba(56, 189, 248, 0.8)';
    reticleCtx.lineWidth = 1.5;
    reticleCtx.stroke();

    // Action Label Pill
    if (label) {
      reticleCtx.font = 'bold 16px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
      const textMetrics = reticleCtx.measureText(label);
      const padding = 10;
      const boxWidth = textMetrics.width + padding * 2;
      const boxHeight = 30;
      const boxX = Math.max(10, Math.min(1280 - boxWidth - 10, x - boxWidth / 2));
      const boxY = y + 40 > 680 ? y - 55 : y + 40;

      reticleCtx.fillStyle = 'rgba(15, 23, 42, 0.9)';
      reticleCtx.beginPath();
      reticleCtx.roundRect(boxX, boxY, boxWidth, boxHeight, 8);
      reticleCtx.fill();
      reticleCtx.strokeStyle = '#38bdf8';
      reticleCtx.lineWidth = 1.5;
      reticleCtx.stroke();

      reticleCtx.fillStyle = '#f8fafc';
      reticleCtx.fillText(label, boxX + padding, boxY + 21);
    }
    reticleCtx.restore();

    // Fade out reticle after 2.5 seconds
    setTimeout(function () {
      clearReticle();
    }, 2500);
  }

  function clearReticle() {
    if (!reticleCtx || !el.reticleCanvas) return;
    reticleCtx.clearRect(0, 0, el.reticleCanvas.width, el.reticleCanvas.height);
    state.reticle.visible = false;
  }

  // =========================================================================
  // 3. Step Budget Visual Meter & ODAV Feed Rendering
  // =========================================================================

  function updateStepBudget(currentStep, maxStepCount) {
    state.step = currentStep;
    state.maxSteps = maxStepCount || 8;

    if (el.stepCount) el.stepCount.textContent = currentStep;
    if (el.maxSteps) el.maxSteps.textContent = state.maxSteps;

    // Update 8 segment bars
    if (el.stepSegments && el.stepSegments.length) {
      el.stepSegments.forEach(function (seg, index) {
        const segStep = index + 1;
        seg.className = 'step-segment';

        if (segStep < currentStep) {
          seg.classList.add('completed');
        } else if (segStep === currentStep) {
          if (currentStep >= 6) {
            seg.classList.add('warning');
          } else {
            seg.classList.add('active');
          }
        }
      });
    }

    // Step budget warning alert
    if (currentStep >= 8) {
      if (el.taskStatusBadge) {
        el.taskStatusBadge.className = 'badge-danger px-2.5 py-1 rounded-full text-xs font-semibold';
        el.taskStatusBadge.textContent = 'मर्यादा पूर्ण (Budget Exceeded)';
      }
    } else if (currentStep >= 6) {
      if (el.taskStatusBadge) {
        el.taskStatusBadge.className = 'badge-warning px-2.5 py-1 rounded-full text-xs font-semibold';
        el.taskStatusBadge.textContent = 'शेवटच्या पायऱ्या (Near Limit)';
      }
    }
  }

  function appendOdavAuditEntry(phase, stepNum, data) {
    if (!el.odavFeed) return;

    const entry = document.createElement('div');
    entry.className = 'p-3 rounded-xl bg-slate-900/80 border border-slate-700/80 text-xs flex flex-col gap-1.5 shadow-sm transition-all';

    let phaseBadgeClass = 'badge-phase-observe';
    if (phase === 'Decide') phaseBadgeClass = 'badge-phase-decide';
    if (phase === 'Act') phaseBadgeClass = 'badge-phase-act';
    if (phase === 'Verify') phaseBadgeClass = 'badge-phase-verify';

    const timestamp = new Date().toLocaleTimeString();

    entry.innerHTML = `
      <div class="flex items-center justify-between font-bold">
        <div class="flex items-center gap-1.5">
          <span class="px-2 py-0.5 rounded text-[11px] font-black uppercase ${phaseBadgeClass}">${phase}</span>
          <span class="text-slate-300">पायरी ${stepNum}</span>
        </div>
        <span class="text-[10px] text-slate-500 font-mono">${timestamp}</span>
      </div>
      ${data.thought ? `<div class="text-slate-300 text-xs italic">💭 "${escapeHtml(data.thought)}"</div>` : ''}
      <div class="flex items-center gap-2 flex-wrap text-slate-400 font-mono text-[11px]">
        ${data.action ? `<span class="text-sky-300 font-bold">Action: ${escapeHtml(data.action)}</span>` : ''}
        ${data.selector ? `<span class="text-amber-300 truncate max-w-[180px]">Target: ${escapeHtml(data.selector)}</span>` : ''}
        ${data.value ? `<span class="text-emerald-300 truncate max-w-[140px]">Val: "${escapeHtml(data.value)}"</span>` : ''}
      </div>
      ${data.state_signature ? `
        <div class="flex items-center justify-between pt-1 border-t border-slate-800 text-[10px] text-slate-400 font-mono">
          <span>State Hash: <span class="text-sky-400">${escapeHtml(data.state_signature)}</span></span>
          ${data.stalled ? '<span class="text-amber-400 font-bold">⚠️ Stalled</span>' : '<span class="text-emerald-400">✓ Mutated</span>'}
        </div>
      ` : ''}
    `;

    el.odavFeed.appendChild(entry);
    // Auto-scroll to latest
    el.odavFeed.scrollTop = el.odavFeed.scrollHeight;
  }

  // =========================================================================
  // 4. API Orchestration & Workflow Execution
  // =========================================================================

  async function handleStartTask(overridePrompt) {
    const rawPrompt = overridePrompt || (el.voiceInput ? el.voiceInput.value : '');
    const prompt = rawPrompt.trim();

    if (!prompt) {
      showToast('कृपया सेवेसाठी मागणी प्रविष्ट करा किंवा माईक दाबून बोला.', 'warning');
      if (el.voiceInput) el.voiceInput.focus();
      return;
    }

    if (el.startBtn) el.startBtn.disabled = true;

    try {
      const response = await fetch('/api/start-task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task: prompt,
          language: state.language
        })
      });

      if (!response.ok) {
        throw new Error('Server returned ' + response.status);
      }

      const resData = await response.json();
      state.sessionId = resData.session_id;
      state.active = true;
      state.step = 0;
      state.finished = false;
      state.stalled = false;

      if (el.sessionIdDisplay) {
        el.sessionIdDisplay.textContent = state.sessionId ? state.sessionId.substring(0, 12) + '...' : 'Active';
      }
      if (el.taskStatusBadge) {
        el.taskStatusBadge.className = 'badge-success px-2.5 py-1 rounded-full text-xs font-semibold';
        el.taskStatusBadge.textContent = 'सक्रिय (In Progress)';
      }

      updateStepBudget(0, 8);

      appendOdavAuditEntry('Observe', 0, {
        thought: 'सत्र सुरू झाले: ' + prompt,
        action: 'start_task',
        state_signature: 'INIT_STATE_0000'
      });

      showToast('सेवा सुरू झाली आहे!', 'success');

      // Auto-trigger the first step
      await executeNextStep();

    } catch (err) {
      console.error('[APP] handleStartTask error:', err);
      showToast('कार्य सुरू करताना त्रुटी: ' + err.message, 'danger');
    } finally {
      if (el.startBtn) el.startBtn.disabled = false;
    }
  }

  async function executeNextStep(forceAction) {
    if (!state.active || state.finished) return;

    try {
      const payload = forceAction ? { force_action: forceAction } : {};
      const response = await fetch('/api/step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error('Step call failed with HTTP ' + response.status);
      }

      const stepData = await response.json();
      state.step = stepData.step;
      state.lastAction = stepData.action;
      state.stalled = !!stepData.stalled;

      // Update Stall Badge
      if (el.stallBadge) {
        if (state.stalled) {
          el.stallBadge.classList.remove('hidden');
          showToast(I18N[state.language].stalled_warning, 'warning');
        } else {
          el.stallBadge.classList.add('hidden');
        }
      }

      updateStepBudget(state.step, 8);

      const action = stepData.action || {};

      // Audit Log Phase entries for ODAV
      appendOdavAuditEntry('Observe', state.step, {
        thought: 'पृष्ठ रचना व घटक तपासले.',
        state_signature: stepData.state_signature
      });

      appendOdavAuditEntry('Decide', state.step, {
        thought: action.thought || 'पुढील कृती निश्चित केली.',
        action: action.action,
        selector: action.selector,
        value: action.value
      });

      appendOdavAuditEntry('Act', state.step, {
        action: action.action,
        selector: action.selector,
        value: action.value
      });

      appendOdavAuditEntry('Verify', state.step, {
        state_signature: stepData.state_signature,
        stalled: state.stalled
      });

      // Spoken Feedback from LLM decision
      if (action.feedback) {
        speakFeedback(action.feedback);
      }

      // Check for Reticle Target on Viewport
      if (action.selector) {
        // Map target selector to representative viewport coordinates
        const coords = estimateSelectorCoordinates(action.selector);
        drawReticle(coords.x, coords.y, `${action.action.toUpperCase()}: ${action.selector}`, action.action);
      }

      // Check for Human Checkpoint (action == 'wait' or OTP prompt)
      if (action.action === 'wait') {
        openCheckpointModal(action.feedback || I18N[state.language].checkpoint_prompt);
        return; // Pause auto-advancement until citizen submits OTP
      }

      // Check for Finish Gate
      if (stepData.status === 'finished' || action.action === 'finish') {
        state.finished = true;
        state.active = false;
        if (el.taskStatusBadge) {
          el.taskStatusBadge.className = 'badge-success px-2.5 py-1 rounded-full text-xs font-semibold';
          el.taskStatusBadge.textContent = 'पूर्ण झाले (Completed)';
        }
        showToast('✅ सेवा अर्ज यशस्वीरीत्या पूर्ण झाला आहे!', 'success');
        return;
      }

      // Check for Budget Ceiling
      if (stepData.status === 'budget_exceeded' || state.step >= 8) {
        state.active = false;
        showToast('कमाल पायरी मर्यादा (8 Steps) गाठली गेली.', 'warning');
        return;
      }

      // Auto-continue to next step if session is active
      if (state.active && !state.finished && !state.stalled) {
        setTimeout(function () {
          executeNextStep();
        }, 1500);
      }

    } catch (err) {
      console.error('[APP] executeNextStep error:', err);
      showToast('पायरी अंमलबजावणी त्रुटी: ' + err.message, 'danger');
    }
  }

  function estimateSelectorCoordinates(selector) {
    if (!selector) return { x: 640, y: 360 };
    const s = selector.toLowerCase();
    if (s.includes('name') || s.includes('farmer') || s.includes('district')) return { x: 500, y: 240 };
    if (s.includes('income') || s.includes('survey') || s.includes('scheme')) return { x: 500, y: 320 };
    if (s.includes('jurisdiction') || s.includes('village')) return { x: 500, y: 400 };
    if (s.includes('submit') || s.includes('btn') || s.includes('fetch') || s.includes('apply')) return { x: 640, y: 520 };
    return { x: 640, y: 360 };
  }

  // =========================================================================
  // 5. Ephemeral Data Purge (DPDP Act 2023 Compliance)
  // =========================================================================

  async function handleResetAndPurge() {
    stopSpeaking();
    stopListening();
    closeCheckpointModal();
    clearReticle();

    try {
      const response = await fetch('/api/reset', { method: 'POST' });
      if (!response.ok) {
        console.warn('[RESET] Server returned status', response.status);
      }
    } catch (e) {
      console.warn('[RESET] /api/reset network call failed:', e);
    }

    // Ephemeral Client-Side State Wipe
    state.active = false;
    state.step = 0;
    state.sessionId = null;
    state.lastAction = null;
    state.stalled = false;
    state.finished = false;
    state.otpBuffer = '';

    if (el.voiceInput) el.voiceInput.value = '';
    if (el.clearInputBtn) el.clearInputBtn.classList.add('hidden');
    if (el.sessionIdDisplay) el.sessionIdDisplay.textContent = 'निष्क्रिय (Idle)';
    if (el.taskStatusBadge) {
      el.taskStatusBadge.className = 'badge-info px-2.5 py-1 rounded-full text-xs font-semibold';
      el.taskStatusBadge.textContent = 'तयार (Ready)';
    }
    if (el.stallBadge) el.stallBadge.classList.add('hidden');

    updateStepBudget(0, 8);

    // Wipe audit feed
    if (el.odavFeed) {
      el.odavFeed.innerHTML = `
        <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-700 text-xs flex flex-col gap-1 text-slate-400">
          <div class="flex items-center justify-between font-semibold text-emerald-400">
            <span>🛡️ डेटा सुरक्षितपणे नष्ट (Purged)</span>
            <span>DPDP Act 2023</span>
          </div>
          <p>${I18N[state.language].purge_success}</p>
        </div>
      `;
    }

    // Display confirmation
    speakFeedback(I18N[state.language].purge_success);
    showToast(I18N[state.language].purge_success, 'success');
  }

  // =========================================================================
  // 6. Human Checkpoint Modal & Virtual Numeric Keypad (F15 / F19)
  // =========================================================================

  function openCheckpointModal(promptText) {
    state.waitingCheckpoint = true;
    state.otpBuffer = '';
    updateOtpDisplay();

    if (promptText && el.checkpointPrompt) {
      el.checkpointPrompt.textContent = promptText;
    }
    if (el.checkpointModal) {
      el.checkpointModal.classList.remove('hidden');
    }
  }

  function closeCheckpointModal() {
    state.waitingCheckpoint = false;
    state.otpBuffer = '';
    updateOtpDisplay();
    if (el.checkpointModal) {
      el.checkpointModal.classList.add('hidden');
    }
  }

  function updateOtpDisplay() {
    if (el.otpInput) {
      el.otpInput.value = state.otpBuffer;
    }
    if (el.otpSlots && el.otpSlots.length) {
      el.otpSlots.forEach(function (slot, i) {
        const char = state.otpBuffer[i] || '';
        slot.textContent = char;
        if (i === state.otpBuffer.length && state.otpBuffer.length < 6) {
          slot.classList.add('border-sky-400', 'bg-slate-800');
          slot.classList.remove('border-slate-600', 'bg-slate-900');
        } else {
          slot.classList.remove('border-sky-400', 'bg-slate-800');
          slot.classList.add('border-slate-600', 'bg-slate-900');
        }
      });
    }
  }

  function handleKeypadTap(key) {
    // 300ms Rapid Tap Debounce Protection
    const now = Date.now();
    if (now - state.lastTapTime < 300) {
      return;
    }
    state.lastTapTime = now;

    if (key === 'Clear') {
      state.otpBuffer = '';
      updateOtpDisplay();
      return;
    }

    if (key === 'Back') {
      if (state.otpBuffer.length > 0) {
        state.otpBuffer = state.otpBuffer.slice(0, -1);
        updateOtpDisplay();
      }
      return;
    }

    // Digit 0-9
    if (/^\d$/.test(key)) {
      if (state.otpBuffer.length < 6) {
        state.otpBuffer += key;
        updateOtpDisplay();
      }
    }
  }

  async function submitOtp() {
    if (state.otpBuffer.length !== 6 || !/^\d{6}$/.test(state.otpBuffer)) {
      showToast('कृपया पूर्ण ६ अंकी OTP प्रविष्ट करा.', 'warning');
      return;
    }

    const otpVal = state.otpBuffer;
    closeCheckpointModal();

    showToast('OTP पाठवला जात आहे...', 'info');

    // Forward to /api/step with force_action filling OTP
    await executeNextStep({
      action: 'fill',
      selector: '#otp_input',
      value: otpVal
    });
  }

  // =========================================================================
  // 7. Language Switcher & Localization
  // =========================================================================

  function switchLanguage(langCode) {
    if (!I18N[langCode]) return;
    state.language = langCode;

    // Update active button state
    if (el.langButtons && el.langButtons.length) {
      el.langButtons.forEach(function (btn) {
        if (btn.getAttribute('data-lang') === langCode) {
          btn.className = 'lang-btn min-h-[48px] px-4 rounded-lg font-bold text-sm bg-sky-600 text-white shadow transition-all';
        } else {
          btn.className = 'lang-btn min-h-[48px] px-4 rounded-lg font-bold text-sm text-slate-300 hover:text-white transition-all';
        }
      });
    }

    // Update UI elements text
    const t = I18N[langCode];
    document.documentElement.lang = langCode.split('-')[0];

    if (el.headerSubtitle) el.headerSubtitle.textContent = t.subtitle;
    if (el.viewportTitle) el.viewportTitle.textContent = t.viewport_title;
    if (el.feedbackLabel) el.feedbackLabel.textContent = t.feedback_label;
    if (el.feedbackText) el.feedbackText.textContent = t.initial_greeting;
    if (el.inputLabel) el.inputLabel.textContent = t.input_label;
    if (el.voiceInput) el.voiceInput.placeholder = t.input_placeholder;
    if (el.startBtnText) el.startBtnText.textContent = t.start_btn;
    if (el.resetBtnText) el.resetBtnText.textContent = t.reset_btn;
    if (el.purgeBtnText) el.purgeBtnText.textContent = t.purge_btn;
    if (el.budgetTitle) el.budgetTitle.textContent = t.budget_title;
    if (el.budgetSubtitle) el.budgetSubtitle.textContent = t.budget_subtitle;
    if (el.auditTitle) el.auditTitle.textContent = t.audit_title;
    if (el.clearFeedBtn) el.clearFeedBtn.textContent = t.clear_feed;
    if (el.quickTitle) el.quickTitle.textContent = t.quick_title;
    if (el.checkpointTitle) el.checkpointTitle.textContent = t.checkpoint_title;
    if (el.checkpointSubtitle) el.checkpointSubtitle.textContent = t.checkpoint_subtitle;
    if (el.checkpointPrompt) el.checkpointPrompt.textContent = t.checkpoint_prompt;
    if (el.submitOtpText) el.submitOtpText.textContent = t.submit_otp;
    if (el.cancelOtpText) el.cancelOtpText.textContent = t.cancel_otp;
    if (el.reconnectText) el.reconnectText.textContent = t.reconnecting;

    // Update Quick Chips labels and prompts
    if (el.chipIncome) {
      el.chipIncome.querySelector('.chip-text').textContent = t.chip_income;
      el.chipIncome.setAttribute('data-prompt', t.prompt_income);
    }
    if (el.chipSatbara) {
      el.chipSatbara.querySelector('.chip-text').textContent = t.chip_satbara;
      el.chipSatbara.setAttribute('data-prompt', t.prompt_satbara);
    }
    if (el.chipMahadbt) {
      el.chipMahadbt.querySelector('.chip-text').textContent = t.chip_mahadbt;
      el.chipMahadbt.setAttribute('data-prompt', t.prompt_mahadbt);
    }
    if (el.chipRation) {
      el.chipRation.querySelector('.chip-text').textContent = t.chip_ration;
      el.chipRation.setAttribute('data-prompt', t.prompt_ration);
    }

    if (recognition) {
      recognition.lang = langCode;
    }

    // Greet user in newly selected dialect
    speakFeedback(t.initial_greeting);
  }

  // =========================================================================
  // 8. Toast Notifications & Utilities
  // =========================================================================

  function showToast(message, type) {
    if (!el.toastContainer) return;

    const toast = document.createElement('div');
    let borderClass = 'border-sky-500 bg-slate-900 text-sky-200';
    if (type === 'success') borderClass = 'border-emerald-500 bg-slate-900 text-emerald-200';
    if (type === 'warning') borderClass = 'border-amber-500 bg-slate-900 text-amber-200';
    if (type === 'danger') borderClass = 'border-red-500 bg-slate-900 text-red-200';

    toast.className = `p-3 rounded-xl border shadow-xl flex items-center gap-2.5 text-xs font-medium pointer-events-auto transition-all ${borderClass}`;
    toast.textContent = message;

    el.toastContainer.appendChild(toast);
    setTimeout(function () {
      toast.style.opacity = '0';
      setTimeout(function () { toast.remove(); }, 300);
    }, 3500);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // =========================================================================
  // 9. Event Listeners Setup
  // =========================================================================

  function initEventListeners() {
    // Language Switchers
    if (el.langButtons && el.langButtons.length) {
      el.langButtons.forEach(function (btn) {
        btn.addEventListener('click', function () {
          const lang = btn.getAttribute('data-lang');
          switchLanguage(lang);
        });
      });
    }

    // Push-to-Talk (PTT)
    if (el.micBtn) {
      el.micBtn.addEventListener('click', function () {
        if (state.isListening) {
          stopListening();
        } else {
          startListening();
        }
      });
    }

    // Input Clear
    if (el.clearInputBtn && el.voiceInput) {
      el.voiceInput.addEventListener('input', function () {
        if (el.voiceInput.value.length > 0) {
          el.clearInputBtn.classList.remove('hidden');
        } else {
          el.clearInputBtn.classList.add('hidden');
        }
      });
      el.clearInputBtn.addEventListener('click', function () {
        el.voiceInput.value = '';
        el.clearInputBtn.classList.add('hidden');
        el.voiceInput.focus();
      });
    }

    // Start & Reset Buttons
    if (el.startBtn) {
      el.startBtn.addEventListener('click', function () {
        handleStartTask();
      });
    }
    if (el.resetBtn) {
      el.resetBtn.addEventListener('click', function () {
        handleResetAndPurge();
      });
    }
    if (el.purgeBtn) {
      el.purgeBtn.addEventListener('click', function () {
        handleResetAndPurge();
      });
    }

    // Quick Chips
    if (el.promptChips) {
      el.promptChips.addEventListener('click', function (e) {
        const chip = e.target.closest('.touch-chip');
        if (chip) {
          const prompt = chip.getAttribute('data-prompt');
          if (el.voiceInput) {
            el.voiceInput.value = prompt;
            if (el.clearInputBtn) el.clearInputBtn.classList.remove('hidden');
          }
          handleStartTask(prompt);
        }
      });
    }

    // Keypad Clicks
    if (el.keypad) {
      el.keypad.addEventListener('click', function (e) {
        const keyBtn = e.target.closest('.keypad-btn');
        if (keyBtn) {
          const keyVal = keyBtn.getAttribute('data-key');
          handleKeypadTap(keyVal);
        }
      });
    }

    // Checkpoint Modal Submissions
    if (el.submitOtpBtn) {
      el.submitOtpBtn.addEventListener('click', submitOtp);
    }
    if (el.cancelOtpBtn) {
      el.cancelOtpBtn.addEventListener('click', closeCheckpointModal);
    }
    if (el.closeModalX) {
      el.closeModalX.addEventListener('click', closeCheckpointModal);
    }

    // Clear Feed
    if (el.clearFeedBtn && el.odavFeed) {
      el.clearFeedBtn.addEventListener('click', function () {
        el.odavFeed.innerHTML = '';
      });
    }
  }

  // --- Initialization on DOM Ready ---
  document.addEventListener('DOMContentLoaded', function () {
    initEventListeners();
    initStream();
    switchLanguage('mr-IN');
    console.log('[SEVA AI KIOSK] Vernacular Kiosk UI Initialized Successfully.');
  });

  // Expose global methods for test harnesses or browser automation
  window.SevaKiosk = {
    state: state,
    I18N: I18N,
    switchLanguage: switchLanguage,
    startTask: handleStartTask,
    nextStep: executeNextStep,
    resetAndPurge: handleResetAndPurge,
    openCheckpointModal: openCheckpointModal,
    closeCheckpointModal: closeCheckpointModal,
    handleKeypadTap: handleKeypadTap,
    clampCoordinates: clampCoordinates,
    speakFeedback: speakFeedback
  };

})();
