/**
 * TrustScore AI — Frontend Application v2.1
 * Team RiskWise | Cognizant Technoverse 2026
 *
 * Features:
 *   - Tabbed UI (Score, Upload, Chat, Batch)
 *   - File drag-and-drop upload with PDF/CSV support
 *   - AI Chat agent with typing indicators + multi-turn memory
 *   - Animated particle background
 *   - Score gauge animations
 *   - History with localStorage
 *   - Model info display
 */

// ══════════════════════════════════════════════════════
// PARTICLE ANIMATION SYSTEM
// ══════════════════════════════════════════════════════

const canvas = document.getElementById('particle-canvas');
const ctx = canvas.getContext('2d');
let particles = [];
let animationFrame;

function resizeCanvas() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}

function createParticles() {
  particles = [];
  const count = Math.min(60, Math.floor(window.innerWidth / 25));
  for (let i = 0; i < count; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      size: Math.random() * 2 + 0.5,
      speedX: (Math.random() - 0.5) * 0.3,
      speedY: (Math.random() - 0.5) * 0.3,
      opacity: Math.random() * 0.3 + 0.05,
    });
  }
}

function drawParticles() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  particles.forEach((p, i) => {
    p.x += p.speedX;
    p.y += p.speedY;

    // Wrap around
    if (p.x < 0) p.x = canvas.width;
    if (p.x > canvas.width) p.x = 0;
    if (p.y < 0) p.y = canvas.height;
    if (p.y > canvas.height) p.y = 0;

    ctx.beginPath();
    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(0, 212, 255, ${p.opacity})`;
    ctx.fill();

    // Draw connections
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[j].x - p.x;
      const dy = particles[j].y - p.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 120) {
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(particles[j].x, particles[j].y);
        ctx.strokeStyle = `rgba(0, 212, 255, ${0.03 * (1 - dist / 120)})`;
        ctx.lineWidth = 0.5;
        ctx.stroke();
      }
    }
  });

  animationFrame = requestAnimationFrame(drawParticles);
}

window.addEventListener('resize', () => {
  resizeCanvas();
  createParticles();
});
resizeCanvas();
createParticles();
drawParticles();


// ══════════════════════════════════════════════════════
// TAB NAVIGATION
// ══════════════════════════════════════════════════════

const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');
const tabIndicator = document.getElementById('tab-indicator');

function switchTab(tabId) {
  tabBtns.forEach(btn => btn.classList.remove('active'));
  tabContents.forEach(tc => tc.classList.remove('active'));

  const activeBtn = document.querySelector(`[data-tab="${tabId}"]`);
  const activeContent = document.getElementById(`tab-${tabId}`);

  if (activeBtn) activeBtn.classList.add('active');
  if (activeContent) activeContent.classList.add('active');

  updateTabIndicator();
}

function updateTabIndicator() {
  const activeBtn = document.querySelector('.tab-btn.active');
  if (activeBtn && tabIndicator) {
    const nav = document.getElementById('tab-nav');
    const navRect = nav.getBoundingClientRect();
    const btnRect = activeBtn.getBoundingClientRect();
    tabIndicator.style.left = (btnRect.left - navRect.left) + 'px';
    tabIndicator.style.width = btnRect.width + 'px';
  }
}

tabBtns.forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

// Initialize tab indicator
setTimeout(updateTabIndicator, 100);
window.addEventListener('resize', updateTabIndicator);


// ══════════════════════════════════════════════════════
// DOM REFERENCES — SCORE TAB
// ══════════════════════════════════════════════════════

const scoreForm = document.getElementById('score-form');
const analyzeBtn = document.getElementById('analyze-btn');
const analyzeBtnText = document.getElementById('analyze-btn-text');
const resultPlaceholder = document.getElementById('result-placeholder');
const scoreResult = document.getElementById('score-result');
const gaugeFill = document.getElementById('gauge-fill');
const scoreNumber = document.getElementById('score-number');
const riskBadge = document.getElementById('risk-badge');
const reasonText = document.getElementById('reason-text');
const adviceBox = document.getElementById('advice-box');
const adviceText = document.getElementById('advice-text');
const loanBox = document.getElementById('loan-box');
const loanText = document.getElementById('loan-text');

const incomeInput = document.getElementById('income-input');
const ratingInput = document.getElementById('rating-input');
const gigsInput = document.getElementById('gigs-input');
const incomeDisplay = document.getElementById('income-display');
const ratingDisplay = document.getElementById('rating-display');
const gigsDisplay = document.getElementById('gigs-display');
const incomeTrack = document.getElementById('income-track');
const ratingTrack = document.getElementById('rating-track');
const gigsTrack = document.getElementById('gigs-track');

const loadSampleBtn = document.getElementById('load-sample-btn');
const runBatchBtn = document.getElementById('run-batch-btn');
const batchBtnText = document.getElementById('batch-btn-text');
const batchEmpty = document.getElementById('batch-empty');
const batchTable = document.getElementById('batch-table');
const batchTbody = document.getElementById('batch-tbody');

const historyList = document.getElementById('history-list');
const historyEmpty = document.getElementById('history-empty');
const clearHistoryBtn = document.getElementById('clear-history-btn');

// ── State ──
let batchData = [];
let lastScoreContext = null; // For chat agent context
let chatSessionId = null;    // For multi-turn chat memory
const HISTORY_KEY = 'trustscore_history';
const GAUGE_CIRCUMFERENCE = 2 * Math.PI * 88; // ~553

function normalizeRisk(risk) {
  const value = String(risk || '').toLowerCase();
  return ['low', 'medium', 'high'].includes(value) ? value : 'high';
}

function riskLabel(riskClass) {
  return riskClass.charAt(0).toUpperCase() + riskClass.slice(1);
}

function riskIcon(riskClass) {
  if (riskClass === 'low') return '✅';
  if (riskClass === 'medium') return '⚠️';
  return '🔴';
}

function createShieldIcon() {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', '18');
  svg.setAttribute('height', '18');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', '2');
  svg.setAttribute('stroke-linecap', 'round');
  svg.setAttribute('stroke-linejoin', 'round');

  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z');
  svg.appendChild(path);

  return svg;
}

function setButtonLoading(labelEl, label) {
  labelEl.textContent = '';
  const spinner = document.createElement('span');
  spinner.className = 'spinner';
  labelEl.append(spinner, document.createTextNode(' ' + label));
}


// ══════════════════════════════════════════════════════
// MODEL INFO — Fetch and display AI model
// ══════════════════════════════════════════════════════

async function fetchModelInfo() {
  try {
    const res = await fetch('/api/info');
    if (!res.ok) return;
    const info = await res.json();

    const badgeText = document.getElementById('model-badge-text');
    const footerPowered = document.getElementById('footer-powered');

    if (badgeText) {
      const modelDisplay = info.model || 'AI Engine';
      const providerDisplay = info.provider || 'AI';
      badgeText.textContent = `${modelDisplay} via ${providerDisplay}`;
    }

    if (footerPowered) {
      footerPowered.textContent = `Powered by ${info.model || 'AI'} via ${info.provider || 'AI'} • Team RiskWise`;
    }
  } catch (e) {
    // Silent fail — not critical
    const badgeText = document.getElementById('model-badge-text');
    if (badgeText) badgeText.textContent = 'AI Engine Active';
  }
}

// Fetch on load
fetchModelInfo();


// ══════════════════════════════════════════════════════
// SLIDER UPDATES
// ══════════════════════════════════════════════════════

function updateSlider(input, display, track, formatter) {
  const pct = ((input.value - input.min) / (input.max - input.min)) * 100;
  display.textContent = formatter(input.value);
  track.style.width = pct + '%';
}

function formatIncome(v) { return '₹' + Number(v).toLocaleString('en-IN'); }
function formatRating(v) { return parseFloat(v).toFixed(1) + ' ★'; }
function formatGigs(v) { return v; }

incomeInput.addEventListener('input', () => updateSlider(incomeInput, incomeDisplay, incomeTrack, formatIncome));
ratingInput.addEventListener('input', () => updateSlider(ratingInput, ratingDisplay, ratingTrack, formatRating));
gigsInput.addEventListener('input', () => updateSlider(gigsInput, gigsDisplay, gigsTrack, formatGigs));

// Initialize slider fills
updateSlider(incomeInput, incomeDisplay, incomeTrack, formatIncome);
updateSlider(ratingInput, ratingDisplay, ratingTrack, formatRating);
updateSlider(gigsInput, gigsDisplay, gigsTrack, formatGigs);


// ══════════════════════════════════════════════════════
// TOAST NOTIFICATIONS
// ══════════════════════════════════════════════════════

function showToast(message, type = 'info') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const icons = {
    info: '💡',
    success: '✅',
    error: '❌',
    warning: '⚠️',
  };

  const toast = document.createElement('div');
  toast.className = 'toast' + (type === 'error' ? ' error' : type === 'success' ? ' success' : '');
  const icon = document.createElement('span');
  icon.className = 'toast-icon';
  icon.textContent = icons[type] || icons.info;
  const text = document.createElement('span');
  text.textContent = String(message || '');
  toast.append(icon, text);
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
}


// ══════════════════════════════════════════════════════
// SCORE GAUGE ANIMATION
// ══════════════════════════════════════════════════════

function animateGauge(score, risk) {
  const riskClass = normalizeRisk(risk);
  const offset = GAUGE_CIRCUMFERENCE - (score / 100) * GAUGE_CIRCUMFERENCE;

  gaugeFill.className = 'gauge-fill ' + riskClass;
  scoreNumber.className = 'score-number ' + riskClass;

  gaugeFill.style.strokeDashoffset = GAUGE_CIRCUMFERENCE;
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      gaugeFill.style.strokeDashoffset = offset;
    });
  });

  animateNumber(scoreNumber, 0, score, 900);

  riskBadge.className = 'risk-badge ' + riskClass;
  riskBadge.textContent = '';
  const icon = document.createElement('span');
  icon.textContent = riskIcon(riskClass);
  riskBadge.append(icon, document.createTextNode(` ${riskLabel(riskClass)} Risk`));
}

function animateNumber(el, start, end, duration) {
  const startTime = performance.now();
  function update(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(start + (end - start) * eased);
    el.textContent = current;
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}


// ══════════════════════════════════════════════════════
// API CALLS
// ══════════════════════════════════════════════════════

async function fetchScore(data) {
  const res = await fetch('/api/score', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Server error');
  }
  return res.json();
}

async function fetchBatchScore(profiles) {
  const res = await fetch('/api/batch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profiles),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Server error');
  }
  return res.json();
}

async function fetchTestData() {
  const res = await fetch('/api/test-data');
  if (!res.ok) throw new Error('Failed to load test data');
  return res.json();
}

async function fetchChat(message, context) {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      context,
      session_id: chatSessionId,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Chat error');
  }
  const data = await res.json();
  // Store session ID for multi-turn memory
  if (data.session_id) {
    chatSessionId = data.session_id;
  }
  return data;
}

async function fetchUpload(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch('/api/upload', {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Upload error');
  }
  return res.json();
}


// ══════════════════════════════════════════════════════
// SINGLE SCORE
// ══════════════════════════════════════════════════════

scoreForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  const data = {
    income: Number(incomeInput.value),
    rating: parseFloat(ratingInput.value),
    gigs: parseInt(gigsInput.value),
  };

  analyzeBtn.disabled = true;
  setButtonLoading(analyzeBtnText, 'Analyzing...');

  try {
    const result = await fetchScore(data);

    resultPlaceholder.style.display = 'none';
    scoreResult.style.display = 'block';

    // Add reveal animation
    scoreResult.classList.remove('score-reveal');
    void scoreResult.offsetWidth; // trigger reflow
    scoreResult.classList.add('score-reveal');

    animateGauge(result.score, result.risk);
    reasonText.textContent = result.reason;

    if (result.advice) {
      adviceBox.style.display = 'flex';
      adviceText.textContent = result.advice;
    } else {
      adviceBox.style.display = 'none';
    }

    if (result.loan_message) {
      loanBox.style.display = 'block';
      loanBox.className = 'loan-box ' + normalizeRisk(result.risk);
      loanText.textContent = result.loan_message;
    } else {
      loanBox.style.display = 'none';
    }

    // Save context for chat
    lastScoreContext = { ...data, ...result };

    addToHistory(data, result);
    showToast(`Score: ${result.score} — ${result.risk} Risk`, 'success');

    // Smooth scroll to result on mobile
    if (window.innerWidth <= 768) {
      document.getElementById('result-card').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtnText.textContent = 'Analyze Creditworthiness';
  }
});


// ══════════════════════════════════════════════════════
// FILE UPLOAD
// ══════════════════════════════════════════════════════

const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const filePreview = document.getElementById('file-preview');
const filePreviewIcon = document.getElementById('file-preview-icon');
const filePreviewName = document.getElementById('file-preview-name');
const filePreviewSize = document.getElementById('file-preview-size');
const fileRemoveBtn = document.getElementById('file-remove-btn');
const uploadBtn = document.getElementById('upload-btn');
const uploadBtnText = document.getElementById('upload-btn-text');
const uploadProgress = document.getElementById('upload-progress');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const uploadResult = document.getElementById('upload-result');

let selectedFile = null;

// Click to browse
uploadZone.addEventListener('click', () => fileInput.click());

// File input change
fileInput.addEventListener('change', (e) => {
  if (e.target.files.length > 0) {
    handleFileSelect(e.target.files[0]);
  }
});

// Drag and drop
uploadZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadZone.classList.add('drag-over');
});

uploadZone.addEventListener('dragleave', () => {
  uploadZone.classList.remove('drag-over');
});

uploadZone.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  if (e.dataTransfer.files.length > 0) {
    handleFileSelect(e.dataTransfer.files[0]);
  }
});

function handleFileSelect(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['pdf', 'csv', 'txt'].includes(ext)) {
    showToast('Unsupported file type. Use PDF, CSV, or TXT.', 'error');
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    showToast('File too large. Maximum size: 5MB.', 'error');
    return;
  }

  selectedFile = file;

  // Show preview
  const icons = { pdf: '📕', csv: '📊', txt: '📄' };
  filePreviewIcon.textContent = icons[ext] || '📄';
  filePreviewName.textContent = file.name;
  filePreviewSize.textContent = formatFileSize(file.size);
  filePreview.style.display = 'flex';
  uploadBtn.disabled = false;

  // Hide previous results
  uploadResult.style.display = 'none';
  uploadProgress.style.display = 'none';
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// Remove file
fileRemoveBtn.addEventListener('click', () => {
  selectedFile = null;
  fileInput.value = '';
  filePreview.style.display = 'none';
  uploadBtn.disabled = true;
  uploadResult.style.display = 'none';
  uploadProgress.style.display = 'none';
});

// Upload and analyze
uploadBtn.addEventListener('click', async () => {
  if (!selectedFile) return;

  uploadBtn.disabled = true;
  setButtonLoading(uploadBtnText, 'Analyzing...');
  uploadProgress.style.display = 'block';
  uploadResult.style.display = 'none';

  // Simulate progress
  let progress = 0;
  const progressInterval = setInterval(() => {
    progress = Math.min(progress + Math.random() * 15, 90);
    progressFill.style.width = progress + '%';
    if (progress < 30) progressText.textContent = 'Extracting text from document...';
    else if (progress < 60) progressText.textContent = 'AI analyzing financial data...';
    else progressText.textContent = 'Generating TrustScore...';
  }, 300);

  try {
    const result = await fetchUpload(selectedFile);

    clearInterval(progressInterval);
    progressFill.style.width = '100%';
    progressText.textContent = 'Analysis complete!';

    setTimeout(() => {
      uploadProgress.style.display = 'none';
      displayUploadResult(result);
    }, 500);

  } catch (err) {
    clearInterval(progressInterval);
    uploadProgress.style.display = 'none';
    showToast(err.message, 'error');
  } finally {
    uploadBtn.disabled = false;
    uploadBtnText.textContent = 'Analyze Document';
  }
});

function displayUploadResult(result) {
  uploadResult.style.display = 'block';

  const summary = document.getElementById('upload-summary');
  const extractedIncome = document.getElementById('extracted-income');
  const extractedRating = document.getElementById('extracted-rating');
  const extractedGigs = document.getElementById('extracted-gigs');
  const uploadScoreSection = document.getElementById('upload-score-section');

  if (result.extracted) {
    summary.textContent = result.extracted.summary || 'Document analyzed.';
    extractedIncome.textContent = result.extracted.income > 0 ? '₹' + Number(result.extracted.income).toLocaleString('en-IN') : '—';
    extractedRating.textContent = result.extracted.rating > 0 ? result.extracted.rating + '/5' : '—';
    extractedGigs.textContent = result.extracted.gigs > 0 ? result.extracted.gigs : '—';
  }

  if (result.score_result) {
    uploadScoreSection.style.display = 'block';
    const riskClass = normalizeRisk(result.score_result.risk);

    const scoreEl = document.getElementById('upload-score-value');
    scoreEl.textContent = result.score_result.score;
    scoreEl.className = 'mini-score ' + riskClass;

    const riskEl = document.getElementById('upload-risk-badge');
    riskEl.textContent = riskLabel(riskClass) + ' Risk';
    riskEl.className = 'mini-risk ' + riskClass;

    document.getElementById('upload-reason-text').textContent = result.score_result.reason;

    const loanEl = document.getElementById('upload-loan-box');
    loanEl.textContent = result.score_result.loan_message;
    loanEl.className = 'upload-loan ' + riskClass;

    // Save to chat context
    lastScoreContext = {
      ...result.score_result,
      income: result.extracted.income,
      rating: result.extracted.rating,
      gigs: result.extracted.gigs,
      document_summary: result.extracted.summary,
    };

    showToast(`Document scored: ${result.score_result.score}/100`, 'success');
  } else {
    uploadScoreSection.style.display = 'none';
    showToast('Document read — no financial data detected for scoring.', 'warning');
  }
}


// ══════════════════════════════════════════════════════
// CHAT AGENT
// ══════════════════════════════════════════════════════

const chatMessages = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const chatSendBtn = document.getElementById('chat-send-btn');
const chatSuggestions = document.getElementById('chat-suggestions');
const charCounter = document.getElementById('char-counter');

// Enable/disable send button based on input + character counter
chatInput.addEventListener('input', () => {
  chatSendBtn.disabled = !chatInput.value.trim();
  if (charCounter) {
    charCounter.textContent = `${chatInput.value.length}/1000`;
    charCounter.classList.toggle('near-limit', chatInput.value.length > 900);
  }
});

// Suggestion chips
document.querySelectorAll('.suggestion-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    chatInput.value = chip.dataset.msg;
    chatSendBtn.disabled = false;
    if (charCounter) charCounter.textContent = `${chatInput.value.length}/1000`;
    chatForm.dispatchEvent(new Event('submit'));
  });
});

// Send message
chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  const message = chatInput.value.trim();
  if (!message) return;

  // Add user message
  addChatMessage(message, 'user');
  chatInput.value = '';
  chatSendBtn.disabled = true;
  if (charCounter) charCounter.textContent = '0/1000';

  // Hide suggestions after first message
  chatSuggestions.style.display = 'none';

  // Show typing indicator
  const typingEl = addTypingIndicator();

  try {
    const result = await fetchChat(message, lastScoreContext);
    typingEl.remove();
    addChatMessage(result.reply, 'ai');
  } catch (err) {
    typingEl.remove();
    addChatMessage('Sorry, I encountered an error. Please try again.', 'ai');
    showToast(err.message, 'error');
  }
});

function addChatMessage(text, sender) {
  const msgDiv = document.createElement('div');
  msgDiv.className = `chat-msg ${sender}`;

  const avatar = document.createElement('div');
  avatar.className = `chat-avatar ${sender === 'ai' ? 'ai-avatar' : 'user-avatar'}`;

  if (sender === 'ai') {
    avatar.appendChild(createShieldIcon());
  } else {
    avatar.textContent = '👤';
  }

  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${sender === 'ai' ? 'ai-bubble' : 'user-bubble'}`;

  // Parse text with simple line break support
  const paragraphs = text.split('\n').filter(p => p.trim());
  paragraphs.forEach((p, i) => {
    const para = document.createElement('p');
    para.textContent = p;
    if (i > 0) para.style.marginTop = '8px';
    bubble.appendChild(para);
  });

  msgDiv.appendChild(avatar);
  msgDiv.appendChild(bubble);
  chatMessages.appendChild(msgDiv);

  // Scroll to bottom
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addTypingIndicator() {
  const msgDiv = document.createElement('div');
  msgDiv.className = 'chat-msg ai';
  msgDiv.id = 'typing-indicator';

  const avatar = document.createElement('div');
  avatar.className = 'chat-avatar ai-avatar';
  avatar.appendChild(createShieldIcon());

  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble ai-bubble';
  const typing = document.createElement('div');
  typing.className = 'typing-indicator';
  for (let i = 0; i < 3; i++) {
    const dot = document.createElement('div');
    dot.className = 'typing-dot';
    typing.appendChild(dot);
  }
  bubble.appendChild(typing);

  msgDiv.appendChild(avatar);
  msgDiv.appendChild(bubble);
  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  return msgDiv;
}


// ══════════════════════════════════════════════════════
// BATCH ANALYSIS
// ══════════════════════════════════════════════════════

loadSampleBtn.addEventListener('click', async () => {
  try {
    loadSampleBtn.disabled = true;
    loadSampleBtn.textContent = '⏳ Loading...';

    batchData = await fetchTestData();
    renderBatchTable(batchData, []);
    runBatchBtn.disabled = false;

    showToast(`Loaded ${batchData.length} sample profiles`, 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    loadSampleBtn.disabled = false;
    loadSampleBtn.textContent = '📥 Load Sample Data';
  }
});

runBatchBtn.addEventListener('click', async () => {
  if (batchData.length === 0) return;

  runBatchBtn.disabled = true;
  setButtonLoading(batchBtnText, 'Scoring...');

  try {
    // Strip extra keys (expected_risk, label) — only send scoring fields
    const cleanProfiles = batchData.map(p => ({
      income: p.income,
      rating: p.rating,
      gigs: p.gigs,
    }));
    const results = await fetchBatchScore(cleanProfiles);
    renderBatchTable(batchData, results);
    showToast(`Scored ${results.length} profiles`, 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    runBatchBtn.disabled = false;
    batchBtnText.textContent = '⚡ Score All';
  }
});

function renderBatchTable(data, results) {
  batchEmpty.style.display = 'none';
  batchTable.style.display = 'table';

  batchTbody.replaceChildren();

  data.forEach((profile, i) => {
    const r = results[i];
    const riskClass = r ? normalizeRisk(r.risk) : 'high';
    const income = Number(profile.income);
    const rating = Number(profile.rating);
    const gigs = Number(profile.gigs);

    const row = document.createElement('tr');
    row.className = 'slide-up';
    row.style.animationDelay = `${i * 0.08}s`;

    const labelCell = document.createElement('td');
    labelCell.style.fontWeight = '500';
    labelCell.textContent = profile.label || 'Worker ' + (i + 1);
    row.appendChild(labelCell);

    const incomeCell = document.createElement('td');
    incomeCell.textContent = '₹' + (Number.isFinite(income) ? income.toLocaleString('en-IN') : '0');
    row.appendChild(incomeCell);

    const ratingCell = document.createElement('td');
    ratingCell.textContent = `${Number.isFinite(rating) ? rating : 0} ★`;
    row.appendChild(ratingCell);

    const gigsCell = document.createElement('td');
    gigsCell.textContent = Number.isFinite(gigs) ? String(gigs) : '0';
    row.appendChild(gigsCell);

    const scoreCell = document.createElement('td');
    if (r) {
      scoreCell.className = 'table-score';
      scoreCell.style.color = `var(--risk-${riskClass})`;
      scoreCell.textContent = String(r.score);
    } else {
      scoreCell.style.color = 'var(--text-muted)';
      scoreCell.textContent = '—';
    }
    row.appendChild(scoreCell);

    const riskCell = document.createElement('td');
    if (r) {
      const riskSpan = document.createElement('span');
      riskSpan.className = `table-risk ${riskClass}`;
      riskSpan.textContent = riskLabel(riskClass);
      riskCell.appendChild(riskSpan);
    } else {
      riskCell.style.color = 'var(--text-muted)';
      riskCell.textContent = '—';
    }
    row.appendChild(riskCell);

    const loanCell = document.createElement('td');
    if (r) {
      const loanSpan = document.createElement('span');
      loanSpan.className = `table-loan ${r.loan_eligible ? 'eligible' : 'ineligible'}`;
      loanSpan.textContent = r.loan_eligible ? '✅ Yes' : '❌ No';
      loanCell.appendChild(loanSpan);
    } else {
      loanCell.style.color = 'var(--text-muted)';
      loanCell.textContent = '—';
    }
    row.appendChild(loanCell);

    const reasonCell = document.createElement('td');
    if (r) {
      reasonCell.style.color = 'var(--text-secondary)';
      reasonCell.style.fontSize = '0.78rem';
      reasonCell.textContent = r.reason || '';
    } else {
      reasonCell.style.color = 'var(--text-muted)';
      reasonCell.textContent = '—';
    }
    row.appendChild(reasonCell);

    batchTbody.appendChild(row);
  });
}


// ══════════════════════════════════════════════════════
// HISTORY
// ══════════════════════════════════════════════════════

function getHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
  } catch {
    return [];
  }
}

function saveHistory(history) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  } catch {
    // Local storage can be disabled or full; scoring should still work.
  }
}

function addToHistory(data, result) {
  const history = getHistory();
  history.unshift({
    ...data,
    ...result,
    timestamp: Date.now(),
  });
  if (history.length > 20) history.length = 20;
  saveHistory(history);
  renderHistory();
}

function renderHistory() {
  const history = getHistory();

  if (history.length === 0) {
    historyEmpty.style.display = 'block';
    const items = historyList.querySelectorAll('.history-item');
    items.forEach(item => item.remove());
    return;
  }

  historyEmpty.style.display = 'none';

  const items = historyList.querySelectorAll('.history-item');
  items.forEach(item => item.remove());

  history.forEach((entry, i) => {
    const item = document.createElement('div');
    item.className = 'history-item fade-in';
    item.style.animationDelay = i * 0.04 + 's';

    const riskClass = normalizeRisk(entry.risk);
    const timeAgo = getTimeAgo(entry.timestamp);
    const income = Number(entry.income);
    const rating = Number(entry.rating);
    const gigs = Number(entry.gigs);
    const score = Number(entry.score);

    const details = document.createElement('div');
    details.className = 'history-item-details';

    const incomeDetail = document.createElement('span');
    incomeDetail.className = 'history-item-detail';
    incomeDetail.textContent = '💰 ₹' + (Number.isFinite(income) ? income.toLocaleString('en-IN') : '0');

    const ratingDetail = document.createElement('span');
    ratingDetail.className = 'history-item-detail';
    ratingDetail.textContent = `⭐ ${Number.isFinite(rating) ? rating : 0}`;

    const gigsDetail = document.createElement('span');
    gigsDetail.className = 'history-item-detail';
    gigsDetail.textContent = `📦 ${Number.isFinite(gigs) ? gigs : 0} gigs`;

    const timeDetail = document.createElement('span');
    timeDetail.style.color = 'var(--text-muted)';
    timeDetail.style.fontSize = '0.72rem';
    timeDetail.textContent = timeAgo;

    details.append(incomeDetail, ratingDetail, gigsDetail, timeDetail);

    const scoreWrap = document.createElement('div');
    const scoreEl = document.createElement('span');
    scoreEl.className = 'history-item-score';
    scoreEl.style.color = `var(--risk-${riskClass})`;
    scoreEl.textContent = Number.isFinite(score) ? String(score) : '0';

    const riskEl = document.createElement('span');
    riskEl.className = `table-risk ${riskClass}`;
    riskEl.style.marginLeft = '8px';
    riskEl.textContent = riskLabel(riskClass);

    scoreWrap.append(scoreEl, riskEl);
    item.append(details, scoreWrap);

    item.addEventListener('click', () => {
      incomeInput.value = entry.income;
      ratingInput.value = entry.rating;
      gigsInput.value = entry.gigs;
      updateSlider(incomeInput, incomeDisplay, incomeTrack, formatIncome);
      updateSlider(ratingInput, ratingDisplay, ratingTrack, formatRating);
      updateSlider(gigsInput, gigsDisplay, gigsTrack, formatGigs);
      switchTab('score');
      window.scrollTo({ top: 0, behavior: 'smooth' });
      showToast('Profile loaded — click Analyze to re-score', 'info');
    });

    historyList.appendChild(item);
  });
}

clearHistoryBtn.addEventListener('click', () => {
  localStorage.removeItem(HISTORY_KEY);
  renderHistory();
  showToast('History cleared', 'info');
});

function getTimeAgo(ts) {
  const seconds = Math.floor((Date.now() - ts) / 1000);
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
  if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
  return Math.floor(seconds / 86400) + 'd ago';
}


// ══════════════════════════════════════════════════════
// INITIALIZATION
// ══════════════════════════════════════════════════════

renderHistory();
