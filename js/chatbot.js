/* =========================================================================
   chatbot.js
   -------------------------------------------------------------------------
   Module 6: AI Wellness Chatbot & Engagement Module Client API
   Handles API requests for conversational AI messaging, Speech-to-Text (Mic Input),
   and Text-to-Speech (Voice Output).
   ========================================================================= */

async function chatbotApiRequest(path, { method = "GET", body, token } = {}) {
  try {
    const headers = {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    };

    const response = await fetch(`${API_BASE_URL}/chatbot${path}`, {
      method,
      headers,
      cache: "no-store",
      body: body ? JSON.stringify(body) : undefined
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401 || response.status === 422) {
        if (typeof clearSession === "function") clearSession();
        window.location.href = "login-user.html";
        throw new Error("Session expired. Please sign in again.");
      }
      throw new Error(data.message || `Chatbot API request failed (${response.status})`);
    }
    return data;
  } catch (err) {
    if (err instanceof TypeError) {
      throw new Error("Couldn't reach chatbot server. Is backend running?");
    }
    throw err;
  }
}

function sendChatMessage(message, token) {
  return chatbotApiRequest("/message", { method: "POST", body: { message }, token });
}

function getChatHistory(token) {
  return chatbotApiRequest("/history", { method: "GET", token });
}

function clearChatHistory(token) {
  return chatbotApiRequest("/clear", { method: "POST", token });
}

function getWellnessReminders(token) {
  return chatbotApiRequest("/reminders", { method: "GET", token });
}

function createWellnessReminder(payload, token) {
  return chatbotApiRequest("/reminders", { method: "POST", body: payload, token });
}

function deleteWellnessReminder(id, token) {
  return chatbotApiRequest(`/reminders/${id}`, { method: "DELETE", token });
}

function getScheduledCheckups(token) {
  return chatbotApiRequest("/checkups", { method: "GET", token });
}

function scheduleHealthCheckup(payload, token) {
  return chatbotApiRequest("/checkups", { method: "POST", body: payload, token });
}

function deleteCheckup(checkupId, token) {
  return chatbotApiRequest(`/checkups/${checkupId}`, { method: "DELETE", token });
}

/* =========================================================================
   SPEECH RECOGNITION (VOICE INPUT - STT) & SPEECH SYNTHESIS (VOICE OUTPUT - TTS)
   ========================================================================= */
let isVoiceOutputEnabled = true;
let speechRecognitionInstance = null;

function speakText(text) {
  if (!isVoiceOutputEnabled || !('speechSynthesis' in window)) return;

  // Clean markdown, symbols, arrows, and units for natural speech synthesis
  const monthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  const cleanText = text
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/\*(.*?)\*/g, '$1')
    .replace(/_(.*?)_/g, '$1')
    .replace(/_/g, '')
    .replace(/(\d{4})-(\d{2})-(\d{2})/g, (m, y, mo, d) => `${monthNames[parseInt(mo,10)-1]} ${parseInt(d,10)}, ${y}`)
    .replace(/→|->|=>/g, ' then ')
    .replace(/—/g, ', ')
    .replace(/(\d+)s\b/gi, '$1 seconds')
    .replace(/(\d+)min\b/gi, '$1 minutes')
    .replace(/(\d+)hr\b/gi, '$1 hours')
    .replace(/[•●▪️■\-]/g, '')
    .replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu, '')
    .replace(/[🚫📅⏰🎯💡🔥💧🧘💤🥗🏃🧠😊👋🤖🌿⚡🇮🇳⚠️]/gu, '')
    .replace(/\n+/g, '. ')
    .replace(/\s+/g, ' ')
    .trim();

  window.speechSynthesis.cancel(); // Stop any ongoing speech
  const utterance = new SpeechSynthesisUtterance(cleanText);
  utterance.rate = 0.98;
  utterance.pitch = 1.0;
  
  // Choose a natural English voice if available
  const voices = window.speechSynthesis.getVoices();
  const naturalVoice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Jenny') || v.name.includes('Guy')));
  if (naturalVoice) utterance.voice = naturalVoice;

  window.speechSynthesis.speak(utterance);
}

function toggleVoiceSpeech(enabled) {
  isVoiceOutputEnabled = enabled;
  if ('speechSynthesis' in window) {
    if (!enabled) {
      if (window.speechSynthesis.speaking) {
        window.speechSynthesis.pause(); // Pause at exact word where stopped
      }
    } else {
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume(); // Resume reading from exact word where stopped
      }
    }
  }
}

function initSpeechRecognition(onResultCallback, onEndCallback) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    throw new Error("Speech recognition is not supported in this browser. Try Chrome or Edge!");
  }

  if (!speechRecognitionInstance) {
    speechRecognitionInstance = new SpeechRecognition();
    speechRecognitionInstance.continuous = false;
    speechRecognitionInstance.interimResults = false;
    speechRecognitionInstance.lang = 'en-US';

    speechRecognitionInstance.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      if (onResultCallback) onResultCallback(transcript);
    };

    speechRecognitionInstance.onend = () => {
      if (onEndCallback) onEndCallback();
    };

    speechRecognitionInstance.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      if (onEndCallback) onEndCallback();
    };
  }

  speechRecognitionInstance.start();
}

/* =========================================================================
   REAL-TIME DESKTOP & IN-APP NOTIFICATION SYSTEM FOR WELLNESS REMINDERS
   ========================================================================= */
function requestNotificationPermission() {
  if ("Notification" in window && Notification.permission !== "granted" && Notification.permission !== "denied") {
    Notification.requestPermission().then(permission => {
      if (permission === "granted") {
        console.log("Desktop notifications enabled for Wellness Reminders!");
      }
    });
  }
}

function sendDesktopNotification(title, body) {
  if ("Notification" in window && Notification.permission === "granted") {
    try {
      new Notification(title, {
        body: body,
        icon: "favicon.ico",
        tag: "wellness-reminder"
      });
    } catch (e) {
      console.warn("Desktop notification error:", e);
    }
  }
}

function playNotificationChime() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
    osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.3); // A5
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.3);
  } catch (e) {
    // Audio context may be restricted before user interaction
  }
}

let activeReminderTimer = null;
let triggeredReminderIds = new Set();

function startReminderScheduler(token) {
  requestNotificationPermission();

  if (activeReminderTimer) clearInterval(activeReminderTimer);

  // Check active reminders every 30 seconds
  activeReminderTimer = setInterval(async () => {
    if (!token) return;
    try {
      const res = await getWellnessReminders(token);
      const reminders = res.reminders || [];

      reminders.forEach(reminder => {
        // Trigger a test alert for newly created active reminders if not notified yet
        if (!triggeredReminderIds.has(reminder.id)) {
          triggeredReminderIds.add(reminder.id);
          const alertMsg = `⏰ Reminder Alert: ${reminder.title} (${reminder.timeStr})`;
          
          if (typeof showToast === "function") {
            showToast(alertMsg, "success");
          }
          sendDesktopNotification("🔔 Wellness Reminder", `${reminder.title} — ${reminder.timeStr}`);
          playNotificationChime();

          if (isVoiceOutputEnabled) {
            speakText(reminder.title);
          }
        }
      });
    } catch (err) {
      // Ignore background poll error
    }
  }, 30000);
}
