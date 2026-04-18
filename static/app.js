/**
 * TrustScore AI — Frontend Application
 * Team RiskWise | Cognizant Technoverse 2026
 */

// ── DOM References ──
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
const HISTORY_KEY = 'trustscore_history';
const GAUGE_CIRCUMFERENCE = 2 * Math.PI * 88; // ~553

// ── Slider Updates ──
function updateSlider(input, display, track, formatter) {
  const pct = ((input.value - input.min) / (input.max - input.min)) * 100;
  display.textContent = formatter(input.value);
  track.style.width = pct + '%';
}

function formatIncome(v) {
  return '₹' + Number(v).toLocaleString('en-IN');
}

function formatRating(v) {
  return parseFloat(v).toFixed(1) + ' ★';
}

function formatGigs(v) {
  return v;
}

incomeInput.addEventListener('input', () => updateSlider(incomeInput, incomeDisplay, incomeTrack, formatIncome));
ratingInput.addEventListener('input', () => updateSlider(ratingInput, ratingDisplay, ratingTrack, formatRating));
gigsInput.addEventListener('input', () => updateSlider(gigsInput, gigsDisplay, gigsTrack, formatGigs));

// Initialize slider fills
updateSlider(incomeInput, incomeDisplay, incomeTrack, formatIncome);
updateSlider(ratingInput, ratingDisplay, ratingTrack, formatRating);
updateSlider(gigsInput, gigsDisplay, gigsTrack, formatGigs);

// ── Toast Notifications ──
function showToast(message, isError = false) {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'toast' + (isError ? ' error' : '');
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
}

// ── Score Gauge Animation ──
function animateGauge(score, risk) {
  const riskClass = risk.toLowerCase();
  const offset = GAUGE_CIRCUMFERENCE - (score / 100) * GAUGE_CIRCUMFERENCE;

  // Reset classes
  gaugeFill.className = 'gauge-fill ' + riskClass;
  scoreNumber.className = 'score-number ' + riskClass;

  // Animate fill
  gaugeFill.style.strokeDashoffset = GAUGE_CIRCUMFERENCE;
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      gaugeFill.style.strokeDashoffset = offset;
    });
  });

  // Count up number
  animateNumber(scoreNumber, 0, score, 900);

  // Risk badge
  riskBadge.className = 'risk-badge ' + riskClass;
  riskBadge.innerHTML = `<span>${riskClass === 'low' ? '✅' : riskClass === 'medium' ? '⚠️' : '🔴'}</span> ${risk} Risk`;
}

function animateNumber(el, start, end, duration) {
  const startTime = performance.now();
  function update(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Ease out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(start + (end - start) * eased);
    el.textContent = current;
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

// ── API Calls ──
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

// ── Single Score ──
scoreForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  const data = {
    income: Number(incomeInput.value),
    rating: parseFloat(ratingInput.value),
    gigs: parseInt(gigsInput.value),
  };

  // Show loading
  analyzeBtn.disabled = true;
  analyzeBtnText.innerHTML = '<span class="spinner"></span> Analyzing...';

  try {
    const result = await fetchScore(data);

    // Show result
    resultPlaceholder.style.display = 'none';
    scoreResult.style.display = 'block';

    animateGauge(result.score, result.risk);
    reasonText.textContent = result.reason;

    // Show advice
    if (result.advice) {
      adviceBox.style.display = 'flex';
      adviceText.textContent = result.advice;
    } else {
      adviceBox.style.display = 'none';
    }

    // Show loan eligibility
    if (result.loan_message) {
      loanBox.style.display = 'block';
      loanBox.className = 'loan-box ' + result.risk.toLowerCase();
      loanText.textContent = result.loan_message;
    } else {
      loanBox.style.display = 'none';
    }

    // Save to history
    addToHistory(data, result);

    showToast(`Score: ${result.score} — ${result.risk} Risk`);

  } catch (err) {
    showToast(err.message, true);
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtnText.textContent = 'Analyze Creditworthiness';
  }
});

// ── Batch ──
loadSampleBtn.addEventListener('click', async () => {
  try {
    loadSampleBtn.disabled = true;
    loadSampleBtn.textContent = '⏳ Loading...';

    batchData = await fetchTestData();
    renderBatchTable(batchData, []);
    runBatchBtn.disabled = false;

    showToast(`Loaded ${batchData.length} sample profiles`);
  } catch (err) {
    showToast(err.message, true);
  } finally {
    loadSampleBtn.disabled = false;
    loadSampleBtn.textContent = '📥 Load Sample Data';
  }
});

runBatchBtn.addEventListener('click', async () => {
  if (batchData.length === 0) return;

  runBatchBtn.disabled = true;
  batchBtnText.innerHTML = '<span class="spinner"></span> Scoring...';

  try {
    const results = await fetchBatchScore(batchData);
    renderBatchTable(batchData, results);
    showToast(`Scored ${results.length} profiles`);
  } catch (err) {
    showToast(err.message, true);
  } finally {
    runBatchBtn.disabled = false;
    batchBtnText.textContent = '⚡ Score All';
  }
});

function renderBatchTable(data, results) {
  batchEmpty.style.display = 'none';
  batchTable.style.display = 'table';

  batchTbody.innerHTML = data.map((profile, i) => {
    const r = results[i];
    const scoreCell = r
      ? `<td class="table-score" style="color: var(--risk-${r.risk.toLowerCase()})">${r.score}</td>`
      : `<td style="color: var(--text-muted)">—</td>`;
    const riskCell = r
      ? `<td><span class="table-risk ${r.risk.toLowerCase()}">${r.risk}</span></td>`
      : `<td style="color: var(--text-muted)">—</td>`;
    const loanCell = r
      ? `<td><span class="table-loan ${r.loan_eligible ? 'eligible' : 'ineligible'}">${r.loan_eligible ? '✅ Yes' : '❌ No'}</span></td>`
      : `<td style="color: var(--text-muted)">—</td>`;
    const reasonCell = r
      ? `<td style="color: var(--text-secondary); font-size: 0.78rem;">${r.reason}</td>`
      : `<td style="color: var(--text-muted)">—</td>`;

    return `
      <tr class="slide-up" style="animation-delay: ${i * 0.08}s">
        <td style="font-weight: 500;">${profile.label || 'Worker ' + (i + 1)}</td>
        <td>₹${Number(profile.income).toLocaleString('en-IN')}</td>
        <td>${profile.rating} ★</td>
        <td>${profile.gigs}</td>
        ${scoreCell}
        ${riskCell}
        ${loanCell}
        ${reasonCell}
      </tr>
    `;
  }).join('');
}

// ── History ──
function getHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
  } catch {
    return [];
  }
}

function saveHistory(history) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
}

function addToHistory(data, result) {
  const history = getHistory();
  history.unshift({
    ...data,
    ...result,
    timestamp: Date.now(),
  });
  // Keep max 20 entries
  if (history.length > 20) history.length = 20;
  saveHistory(history);
  renderHistory();
}

function renderHistory() {
  const history = getHistory();

  if (history.length === 0) {
    historyEmpty.style.display = 'block';
    // Remove all items except the empty message
    const items = historyList.querySelectorAll('.history-item');
    items.forEach(item => item.remove());
    return;
  }

  historyEmpty.style.display = 'none';

  // Clear and re-render
  const items = historyList.querySelectorAll('.history-item');
  items.forEach(item => item.remove());

  history.forEach((entry, i) => {
    const item = document.createElement('div');
    item.className = 'history-item fade-in';
    item.style.animationDelay = i * 0.04 + 's';

    const riskClass = entry.risk.toLowerCase();
    const timeAgo = getTimeAgo(entry.timestamp);

    item.innerHTML = `
      <div class="history-item-details">
        <span class="history-item-detail">💰 ₹${Number(entry.income).toLocaleString('en-IN')}</span>
        <span class="history-item-detail">⭐ ${entry.rating}</span>
        <span class="history-item-detail">📦 ${entry.gigs} gigs</span>
        <span style="color: var(--text-muted); font-size: 0.72rem;">${timeAgo}</span>
      </div>
      <div>
        <span class="history-item-score" style="color: var(--risk-${riskClass})">${entry.score}</span>
        <span class="table-risk ${riskClass}" style="margin-left: 8px;">${entry.risk}</span>
      </div>
    `;

    // Click to load into form
    item.addEventListener('click', () => {
      incomeInput.value = entry.income;
      ratingInput.value = entry.rating;
      gigsInput.value = entry.gigs;
      updateSlider(incomeInput, incomeDisplay, incomeTrack, formatIncome);
      updateSlider(ratingInput, ratingDisplay, ratingTrack, formatRating);
      updateSlider(gigsInput, gigsDisplay, gigsTrack, formatGigs);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    historyList.appendChild(item);
  });
}

clearHistoryBtn.addEventListener('click', () => {
  localStorage.removeItem(HISTORY_KEY);
  renderHistory();
  showToast('History cleared');
});

function getTimeAgo(ts) {
  const seconds = Math.floor((Date.now() - ts) / 1000);
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
  if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
  return Math.floor(seconds / 86400) + 'd ago';
}

// ── Init ──
renderHistory();
