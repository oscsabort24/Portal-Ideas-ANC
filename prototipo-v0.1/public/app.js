/* ─────────────────────────────────────────────
   STATE
───────────────────────────────────────────── */
const STORAGE_KEY = 'portalIdeasState';

let currentAbortController = null;

const state = {
  history:            [],
  blockStatus:        { 1: 'pending', 2: 'pending', 3: 'pending', 4: 'pending', 5: 'pending' },
  readyForCharter:    false,
  isLoading:          false,
  selectedDocs:       [],
  generatedDocs:      {},
  lastRecommendation: null,
  displayMessages:    []
};

const BLOCK_NAMES = {
  1: 'Problema y Alcance',
  2: 'Objetivo Medible',
  3: 'Beneficios Esperados',
  4: 'Entregables Principales',
  5: 'Riesgos y Mitigación'
};

const DOC_LABELS = {
  charter:      'Project Charter',
  bpmn:         'Diagrama de proceso (BPMN)',
  onepager:     'One-pager',
  raci:         'RACI',
  bmc:          'Business Model Canvas',
  businesscase: 'Business Case + ROI',
};

/* ─────────────────────────────────────────────
   SESSION PERSISTENCE (localStorage)
───────────────────────────────────────────── */
function saveSession() {
  try {
    const stateToSave = {
      ...state,
      history: state.history.slice(-30)
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave));
  } catch (e) {
    if (e.name === 'QuotaExceededError') {
      showStorageWarning('Almacenamiento lleno. No se puede guardar la conversación.');
    } else {
      console.warn('No se pudo guardar la sesión:', e.message);
    }
  }
}

function showStorageWarning(message) {
  let warning = document.getElementById('storageWarning');
  if (!warning) {
    warning = document.createElement('div');
    warning.id = 'storageWarning';
    warning.className = 'storage-warning';
    warning.innerHTML = `
      <span class="warning-icon">⚠️</span>
      <span>${message}</span>
    `;
    document.body.appendChild(warning);
    setTimeout(() => warning.remove(), 5000);
  }
}

function loadSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) { return null; }
}

function clearSession() {
  localStorage.removeItem(STORAGE_KEY);
}

function restoreSession(saved) {
  state.history            = saved.history            || [];
  state.blockStatus        = saved.blockStatus        || { 1:'pending',2:'pending',3:'pending',4:'pending',5:'pending' };
  state.readyForCharter    = saved.readyForCharter    || false;
  state.selectedDocs       = saved.selectedDocs       || [];
  state.generatedDocs      = saved.generatedDocs      || {};
  state.lastRecommendation = saved.lastRecommendation || null;
  state.displayMessages    = saved.displayMessages    || [];

  Object.entries(state.blockStatus).forEach(([id, status]) => {
    const el = document.getElementById(`block-${id}`);
    if (el) el.dataset.status = status;
  });

  state.displayMessages.forEach(({ role, text }) => {
    addMessage(role, text, { save: false });
  });

  updateProgressIndicator();

  if (state.readyForCharter) showCharterButton();

  if (Object.keys(state.generatedDocs).length > 0) {
    document.getElementById('viewDocsBtn').style.display = 'flex';
  } else if (state.lastRecommendation) {
    showDocumentSelector(state.lastRecommendation);
  }
}

/* ─────────────────────────────────────────────
   WELCOME SCREEN
───────────────────────────────────────────── */
function showWelcome() {
  document.querySelector('.chat-area').classList.add('welcome-active');
}

function hideWelcome() {
  document.querySelector('.chat-area').classList.remove('welcome-active');
}

function startInterview() {
  hideWelcome();
  initConversation();
}

/* ─────────────────────────────────────────────
   INIT
───────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  setupInput();
  setupReset();

  const saved = loadSession();
  if (saved && Array.isArray(saved.displayMessages) && saved.displayMessages.length > 0) {
    hideWelcome();
    restoreSession(saved);
  }
});

async function initConversation() {
  setLoading(true);
  clearMessages();
  clearOptions();

  try {
    const responseText = await callAPI([], '__INIT__');
    const parsed = JSON.parse(responseText);

    state.history = [
      { role: 'user',      content: '__INIT__' },
      { role: 'assistant', content: responseText }
    ];

    handleAIResponse(parsed);
    saveSession();
  } catch (err) {
    if (err.name === 'AbortError') return;
    if (err.errorType === 'quota_exceeded') {
      showQuotaError();
    } else {
      showErrorBanner('No se pudo iniciar la conversación. ' + err.message, initConversation);
    }
  } finally {
    setLoading(false);
  }
}

/* ─────────────────────────────────────────────
   SEND MESSAGE
───────────────────────────────────────────── */
async function sendMessage(overrideText, { skipDOMMessage = false } = {}) {
  if (state.isLoading) return;

  const input = document.getElementById('userInput');
  const text = (overrideText ?? input.value).trim();
  if (!text) return;

  if (!skipDOMMessage) {
    input.value = '';
    resizeTextarea(input);
    addMessage('user', text);
  }
  clearOptions();

  const historySnapshot = [...state.history];

  setLoading(true);
  try {
    const responseText = await callAPI(historySnapshot, text);
    const parsed = JSON.parse(responseText);

    state.history.push(
      { role: 'user',      content: text },
      { role: 'assistant', content: responseText }
    );

    handleAIResponse(parsed);
    saveSession();
  } catch (err) {
    if (err.name === 'AbortError') return;
    if (err.errorType === 'quota_exceeded') {
      showQuotaError();
    } else {
      showErrorBanner('Error al enviar mensaje: ' + err.message,
        () => sendMessage(text, { skipDOMMessage: true }));
    }
  } finally {
    setLoading(false);
  }
}

/* ─────────────────────────────────────────────
   SKIP FIELD
───────────────────────────────────────────── */
function skipField() {
  sendMessage('No tengo ese dato, lo dejaré como pendiente de definir por ahora.');
}

/* ─────────────────────────────────────────────
   GENERATE DOCS
───────────────────────────────────────────── */
async function generateDocs(selectedDocs) {
  if (state.isLoading || !selectedDocs || !selectedDocs.length) return;

  const btn = document.getElementById('generateDocsBtn');
  if (btn) { btn.disabled = true; btn.textContent = 'Generando…'; }

  const message = `__GENERATE_DOCS__ ${JSON.stringify(selectedDocs)}`;
  const historySnapshot = [...state.history];

  setLoading(true);
  try {
    const responseText = await callAPI(historySnapshot, message);
    const parsed = JSON.parse(responseText);

    state.history.push(
      { role: 'user',      content: message },
      { role: 'assistant', content: responseText }
    );

    if (parsed.documents) {
      Object.assign(state.generatedDocs, parsed.documents);
      addMessage('assistant', 'Los documentos han sido generados. Podés revisarlos, imprimirlos o copiarlos.');
      const selectorBtn = document.getElementById('openSelectorBtn');
      if (selectorBtn) selectorBtn.style.display = 'none';
      document.getElementById('viewDocsBtn').style.display = 'flex';
      openDocsModal();
      saveSession();
    } else {
      throw new Error('La respuesta no contiene documentos válidos.');
    }
  } catch (err) {
    if (err.name === 'AbortError') return;
    if (err.errorType === 'quota_exceeded') {
      showQuotaError();
    } else {
      showErrorBanner('Error al generar documentos: ' + err.message, () => generateDocs(selectedDocs));
    }
  } finally {
    setLoading(false);
    if (btn) { btn.disabled = false; btn.textContent = 'Generar documentos seleccionados'; }
  }
}

// Shim para compatibilidad — el flujo ahora usa generateDocs() directamente
function generateCharter() {
  if (Object.keys(state.generatedDocs).length > 0) {
    openDocsModal();
  } else if (state.lastRecommendation) {
    showDocumentSelector(state.lastRecommendation);
  }
}

/* ─────────────────────────────────────────────
   DOCUMENT SELECTOR (in-chat)
───────────────────────────────────────────── */
function showDocumentSelector(recommendation) {
  const container = document.getElementById('messagesContainer');
  const allKeys   = ['charter', 'bpmn', 'onepager', 'raci', 'bmc', 'businesscase'];

  state.selectedDocs = [...(recommendation.recommended || [])];

  const wrapper = document.createElement('div');
  wrapper.className = 'message assistant';
  wrapper.id = 'docSelectorMessage';

  const label = document.createElement('div');
  label.className = 'msg-label';
  label.textContent = 'Asistente ANC';

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble doc-selector-bubble';

  const reasonEl = document.createElement('p');
  reasonEl.className = 'doc-selector-reason';
  reasonEl.textContent = recommendation.reason || '';
  bubble.appendChild(reasonEl);

  const hintEl = document.createElement('p');
  hintEl.className = 'doc-selector-hint';
  hintEl.textContent = 'Seleccioná los documentos que querés generar:';
  bubble.appendChild(hintEl);

  const chipsEl = document.createElement('div');
  chipsEl.className = 'doc-chips';

  allKeys.forEach(key => {
    const isSelected = state.selectedDocs.includes(key);
    const chip = document.createElement('button');
    chip.className = `doc-chip${isSelected ? ' selected' : ''}`;
    chip.dataset.docKey = key;
    chip.textContent = DOC_LABELS[key] || key;
    chip.onclick = () => {
      const idx = state.selectedDocs.indexOf(key);
      if (idx === -1) { state.selectedDocs.push(key); chip.classList.add('selected'); }
      else            { state.selectedDocs.splice(idx, 1); chip.classList.remove('selected'); }
    };
    chipsEl.appendChild(chip);
  });
  bubble.appendChild(chipsEl);

  const generateBtn = document.createElement('button');
  generateBtn.id = 'generateDocsBtn';
  generateBtn.className = 'btn-generate-docs';
  generateBtn.textContent = 'Generar documentos seleccionados';
  generateBtn.onclick = () => generateDocs(state.selectedDocs);
  bubble.appendChild(generateBtn);

  wrapper.appendChild(label);
  wrapper.appendChild(bubble);
  container.appendChild(wrapper);
  scrollToBottom();
}

/* ─────────────────────────────────────────────
   DOCS MODAL
───────────────────────────────────────────── */
function getRenderer(key) {
  const map = {
    charter:      renderCharter,
    bpmn:         renderBpmn,
    onepager:     renderOnepager,
    raci:         renderRaci,
    bmc:          renderBmc,
    businesscase: renderBusinessCase,
  };
  return map[key] || (() => '<p style="padding:20px;color:var(--text-muted)">Sin renderer para este tipo de documento.</p>');
}

function openDocsModal() {
  const docs = state.generatedDocs;
  const keys = Object.keys(docs);
  if (!keys.length) return;

  const tabsEl    = document.getElementById('docTabs');
  const contentEl = document.getElementById('docTabContent');
  const overlay   = document.getElementById('charterOverlay');

  tabsEl.innerHTML = keys.map((key, i) =>
    `<button class="doc-tab${i === 0 ? ' active' : ''}" data-tab="${key}" onclick="switchDocTab('${key}')">${escapeHTML(DOC_LABELS[key] || key)}</button>`
  ).join('');

  contentEl.innerHTML = getRenderer(keys[0])(docs[keys[0]]);
  contentEl.scrollTop = 0;

  overlay.style.display = 'flex';
  overlay.setAttribute('aria-hidden', 'false');
}

function openCharter() { openDocsModal(); }

function switchDocTab(key) {
  document.querySelectorAll('.doc-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === key));
  const content = document.getElementById('docTabContent');
  if (content) {
    content.innerHTML = getRenderer(key)(state.generatedDocs[key]);
    content.scrollTop = 0;
  }
}

/* ─────────────────────────────────────────────
   API CALL
───────────────────────────────────────────── */
async function callAPI(history, message) {
  currentAbortController = new AbortController();
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ history, message }),
    signal: currentAbortController.signal
  });

  const data = await res.json();

  if (!res.ok) {
    const err = new Error(data.message || data.error || `HTTP ${res.status}`);
    err.errorType = data.error;
    throw err;
  }

  return data.response;
}

/* ─────────────────────────────────────────────
   HANDLE AI RESPONSE
───────────────────────────────────────────── */
function handleAIResponse(parsed) {
  if (parsed.message) {
    addMessage('assistant', parsed.message);
  }

  if (parsed.blockStatus) {
    updateBlockStatus(parsed.blockStatus);
  }

  if (Array.isArray(parsed.options) && parsed.options.length > 0) {
    showOptions(parsed.options);
  }

  if (parsed.readyForCharter && !state.readyForCharter) {
    state.readyForCharter = true;
    showCharterButton();
  }

  if (parsed.documentRecommendation && !state.lastRecommendation) {
    state.lastRecommendation = parsed.documentRecommendation;
    showDocumentSelector(parsed.documentRecommendation);
  }
}

/* ─────────────────────────────────────────────
   UI – MESSAGES
───────────────────────────────────────────── */
function addMessage(role, text, { save = true } = {}) {
  const container = document.getElementById('messagesContainer');

  const wrapper = document.createElement('div');
  wrapper.className = `message ${role}`;

  const label = document.createElement('div');
  label.className = 'msg-label';
  label.textContent = role === 'user' ? 'Tú' : 'Asistente ANC';

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.textContent = text;

  wrapper.appendChild(label);
  wrapper.appendChild(bubble);
  container.appendChild(wrapper);
  scrollToBottom();

  if (save) {
    state.displayMessages.push({ role, text });
  }
}

function showTypingIndicator() {
  const container = document.getElementById('messagesContainer');
  const wrapper = document.createElement('div');
  wrapper.className = 'message assistant typing';
  wrapper.id = 'typingMsg';

  const label = document.createElement('div');
  label.className = 'msg-label';
  label.textContent = 'Asistente ANC';

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';

  const typingLabel = document.createElement('span');
  typingLabel.className = 'typing-label';
  typingLabel.textContent = 'Escribiendo';
  bubble.appendChild(typingLabel);

  [1, 2, 3].forEach(() => {
    const dot = document.createElement('span');
    dot.className = 'typing-dot';
    bubble.appendChild(dot);
  });

  wrapper.appendChild(label);
  wrapper.appendChild(bubble);
  container.appendChild(wrapper);
  scrollToBottom();
}

function hideTypingIndicator() {
  const el = document.getElementById('typingMsg');
  if (el) el.remove();
}

function clearMessages() {
  document.getElementById('messagesContainer').innerHTML = '';
}

function scrollToBottom() {
  const c = document.getElementById('messagesContainer');
  c.scrollTop = c.scrollHeight;
}

function showErrorBanner(msg, retryFn) {
  const container = document.getElementById('messagesContainer');
  const el = document.createElement('div');
  el.className = 'msg-error';

  const textSpan = document.createElement('span');
  textSpan.textContent = '⚠ ' + msg;
  el.appendChild(textSpan);

  if (typeof retryFn === 'function') {
    const retryBtn = document.createElement('button');
    retryBtn.className = 'btn-retry';
    retryBtn.textContent = 'Reintentar';
    retryBtn.onclick = () => { el.remove(); retryFn(); };
    el.appendChild(retryBtn);
  }

  container.appendChild(el);
  scrollToBottom();
}

function showQuotaError() {
  const container = document.getElementById('messagesContainer');
  const el = document.createElement('div');
  el.className = 'msg-quota-error';

  const clockSVG = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;

  el.innerHTML = `
    <div class="quota-icon">${clockSVG}</div>
    <div class="quota-body">
      <div class="quota-title">Cuota diaria agotada</div>
      <div class="quota-desc">La IA alcanzó el límite de peticiones gratuitas de hoy. Podés volver mañana a partir de las 3am (hora Costa Rica) cuando se reinicia la cuota.</div>
    </div>
    <button class="btn-quota-dismiss">Entendido</button>
  `;

  el.querySelector('.btn-quota-dismiss').onclick = () => el.remove();
  container.appendChild(el);
  scrollToBottom();
}

/* ─────────────────────────────────────────────
   UI – OPTIONS CHIPS
───────────────────────────────────────────── */
function showOptions(options) {
  const area = document.getElementById('optionsArea');
  area.innerHTML = '';

  options.forEach((opt, i) => {
    const chip = document.createElement('button');
    chip.className = 'option-chip';
    chip.textContent = opt;
    chip.style.animationDelay = `${i * 0.05}s`;
    chip.onclick = () => { clearOptions(); sendMessage(opt); };
    area.appendChild(chip);
  });

  setSkipVisible(false);
}

function clearOptions() {
  document.getElementById('optionsArea').innerHTML = '';
  if (!state.isLoading) setSkipVisible(true);
}

/* ─────────────────────────────────────────────
   UI – BLOCK STATUS PANEL
───────────────────────────────────────────── */
function updateBlockStatus(newStatus) {
  Object.entries(newStatus).forEach(([id, status]) => {
    if (state.blockStatus[id] === status) return;
    state.blockStatus[id] = status;
    const el = document.getElementById(`block-${id}`);
    if (el) el.dataset.status = status;
  });
  updateProgressIndicator();
}

/* ─────────────────────────────────────────────
   UI – PROGRESS INDICATOR
───────────────────────────────────────────── */
function updateProgressIndicator() {
  const completed = Object.values(state.blockStatus).filter(s => s === 'complete').length;
  const pct = (completed / 5) * 100;
  const textEl = document.getElementById('progressText');
  const fillEl = document.getElementById('progressFill');
  if (textEl) textEl.textContent = `${completed} de 5 bloques completados`;
  if (fillEl)  fillEl.style.width = `${pct}%`;
}

/* ─────────────────────────────────────────────
   UI – SKIP BUTTON
───────────────────────────────────────────── */
function setSkipVisible(visible) {
  const row = document.getElementById('skipRow');
  if (row) row.style.display = visible ? 'flex' : 'none';
}

/* ─────────────────────────────────────────────
   UI – CHARTER/DOCS BUTTON
───────────────────────────────────────────── */
function showCharterButton() {
  const banner = document.getElementById('charterReadyBanner');
  if (banner) banner.style.display = 'flex';
  const selectorBtn = document.getElementById('openSelectorBtn');
  if (selectorBtn) selectorBtn.style.display = 'flex';
}

function openDocSelector() {
  const existing = document.getElementById('docSelectorMessage');
  if (existing) {
    existing.scrollIntoView({ behavior: 'smooth', block: 'center' });
    return;
  }
  if (state.lastRecommendation) {
    showDocumentSelector(state.lastRecommendation);
  } else {
    scrollToBottom();
  }
}

/* ─────────────────────────────────────────────
   DOCUMENT RENDERERS
───────────────────────────────────────────── */

/* Shared footer injected into every document */
const DOC_FOOTER = `
  <div class="doc-footer">
    Generado por Portal de Ideas · Transformación Digital · Grupo ANC
  </div>`;

/* Shared document header with brand and title */
function docHeader(title, tag, showBrand = false) {
  const brand = showBrand ? `
    <div class="doc-brand" style="display:flex;align-items:center;gap:12px;background:#fff;padding:4px 0;">
      <img src="/assets/logo.jpg" alt="Grupo ANC" style="height:67px;width:auto;object-fit:contain;background:#fff;">
      <div>
        <div style="color:#2b9777;font-size:0.95rem;font-weight:700;">Grupo ANC</div>
        <div style="font-size:0.7rem;color:#666;">Alamo · Enterprise · National</div>
      </div>
    </div>` : '';
  return `
    <div class="charter-doc-header" style="border-bottom-color:#2b9777">
      ${brand}
      <div class="doc-title-block">
        <div class="doc-title" style="color:#2b9777">${escapeHTML(title)}</div>
        <div class="doc-program-tag" style="background:#e8f4fd;color:#2e5faa;border:1px solid #2e5faa">${escapeHTML(tag)}</div>
      </div>
    </div>`;
}

/* ── renderCharter ── */
function renderCharter(c) {
  const isReady    = (c.estado||'').toLowerCase().includes('listo');
  const badgeClass = isReady ? 'ready' : 'draft';
  const badgeIcon  = isReady
    ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
    : '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';

  const risksHTML = Array.isArray(c.riesgosIdentificados) && c.riesgosIdentificados.length
    ? `<table class="risk-table">
        <thead><tr><th class="risk-col-risk" style="background:#239a5b">Riesgo identificado</th><th style="background:#239a5b">Estrategia de mitigación</th></tr></thead>
        <tbody>${c.riesgosIdentificados.map(r =>
          `<tr><td>${escapeHTML(r.riesgo||'')}</td><td>${escapeHTML(r.mitigacion||'')}</td></tr>`
        ).join('')}</tbody>
      </table>`
    : '<p class="section-content">Pendiente de definir</p>';

  return `<div class="charter-document">
    ${docHeader(c.nombreProyecto||'Project Charter', c.programa||'Transformación Digital', true)}
    <div class="charter-meta">
      <div class="meta-row"><div class="meta-label" style="color:#2b9777">Nombre del Proyecto</div><div class="meta-value">${escapeHTML(c.nombreProyecto||'—')}</div></div>
      <div class="meta-row"><div class="meta-label" style="color:#2b9777">Área Solicitante</div><div class="meta-value">${escapeHTML(c.areaSolicitante||'—')}</div></div>
      <div class="meta-row"><div class="meta-label" style="color:#2b9777">Solicitante</div><div class="meta-value">${escapeHTML(c.solicitante||'—')}</div></div>
      <div class="meta-row"><div class="meta-label" style="color:#2b9777">Fecha de Emisión</div><div class="meta-value">${escapeHTML(c.fechaEmision||'—')}</div></div>
      <div class="meta-row"><div class="meta-label" style="color:#2b9777">Procedimiento SIG</div><div class="meta-value">${escapeHTML(c.procedimientoSIG||'No existe')}</div></div>
    </div>
    <div class="charter-section"><div class="section-title" style="color:#239a5b;border-left-color:#239a5b">Justificación y Alcance del Proyecto</div><div class="section-content">${escapeHTML(c.justificacionAlcance||'Pendiente de definir')}</div></div>
    <div class="charter-section"><div class="section-title" style="color:#239a5b;border-left-color:#239a5b">Objetivos del Proyecto</div><div class="section-content">${escapeHTML(c.objetivos||'Pendiente de definir')}</div></div>
    <div class="charter-section"><div class="section-title" style="color:#239a5b;border-left-color:#239a5b">Beneficios Esperados</div><div class="section-content">${escapeHTML(c.beneficiosEsperados||'Pendiente de definir')}</div></div>
    <div class="charter-section"><div class="section-title" style="color:#239a5b;border-left-color:#239a5b">Principales Entregables</div><div class="section-content">${escapeHTML(c.principalesEntregables||'Pendiente de definir')}</div></div>
    <div class="charter-section"><div class="section-title" style="color:#239a5b;border-left-color:#239a5b">Riesgos Identificados</div>${risksHTML}</div>
    <div class="charter-status-row">
      <span class="status-label">Estado del documento:</span>
      <span class="status-badge ${badgeClass}" style="${isReady ? 'background:#d4efe7;color:#1a6b4a;border:1px solid #2aa964' : 'background:#fff3e0;color:#b45309;border:1px solid #f59e0b'}">${badgeIcon} ${escapeHTML(c.estado||'—')}</span>
    </div>
    ${DOC_FOOTER}
  </div>`;
}

/* ── renderBpmn ── */
function renderBpmn(data) {
  const typeIcon = t => ({ decision:'◆', inicio:'●', fin:'■' }[t] || '▶');

  const stepRows = (steps, side) => (steps||[]).map((s, i) => `
    <tr>
      <td class="bpmn-num" style="color:#2b9777">${i + 1}</td>
      <td class="bpmn-icon" title="${escapeHTML(s.tipo||'tarea')}">${typeIcon(s.tipo)}</td>
      <td>
        <span class="bpmn-actor" style="color:#239a5b">${escapeHTML(s.actor||'—')}</span>
        <span class="bpmn-action">${escapeHTML(s.accion||'—')}</span>
      </td>
    </tr>`).join('');

  const actorChips = (data.actores||[]).map(a =>
    `<span class="bpmn-actor-chip" style="background:#d4efe7;color:#1a6b4a;border:1px solid #2b9777">${escapeHTML(a)}</span>`).join('');

  return `<div class="charter-document">
    ${docHeader(data.titulo||'Diagrama de Proceso', 'BPMN', true)}
    ${data.descripcion ? `<p class="doc-description">${escapeHTML(data.descripcion)}</p>` : ''}
    <div class="charter-section">
      <div class="section-title" style="color:#239a5b;border-left-color:#239a5b">Participantes del proceso</div>
      <div class="bpmn-actors">${actorChips || '<span class="text-muted">No especificados</span>'}</div>
    </div>
    <div class="bpmn-grid">
      <div class="bpmn-col">
        <div class="bpmn-col-header bpmn-asis" style="background:#fff3e0;color:#b45309;border:1px solid #f59e0b">Proceso Actual (AS-IS)</div>
        <div style="overflow-x:auto">
          <table class="bpmn-table">
            <thead><tr><th>#</th><th></th><th>Actor · Acción</th></tr></thead>
            <tbody>${stepRows(data.pasos_as_is, 'as-is')}</tbody>
          </table>
        </div>
      </div>
      <div class="bpmn-col">
        <div class="bpmn-col-header bpmn-tobe" style="background:#d4efe7;color:#1a6b4a;border:1px solid #2b9777">Proceso Futuro (TO-BE)</div>
        <div style="overflow-x:auto">
          <table class="bpmn-table">
            <thead><tr><th>#</th><th></th><th>Actor · Acción</th></tr></thead>
            <tbody>${stepRows(data.pasos_to_be, 'to-be')}</tbody>
          </table>
        </div>
      </div>
    </div>
    <div class="bpmn-legend">
      <span>▶ Tarea</span><span>◆ Decisión</span><span>● Inicio</span><span>■ Fin</span>
    </div>
    ${DOC_FOOTER}
  </div>`;
}

/* ── renderOnepager ── */
function renderOnepager(data) {
  const levelClass = v => {
    const l = (v||'').toLowerCase();
    if (l.includes('alto'))  return 'badge-high';
    if (l.includes('medio')) return 'badge-mid';
    return 'badge-low';
  };
  const levelStyle = v => {
    const l = (v||'').toLowerCase();
    if (l.includes('alto'))  return 'background:#d4efe7;color:#1a6b4a;border:1px solid #2b9777';
    if (l.includes('medio')) return 'background:#fff3e0;color:#b45309;border:1px solid #f59e0b';
    return 'background:#e8e8e8;color:#555555;border:1px solid #ccc';
  };

  const chips = (data.beneficios||[]).map(b =>
    `<span class="benefit-chip" style="background:#d4efe7;color:#1a6b4a;border:1px solid #2aa964">${escapeHTML(b)}</span>`).join('');

  return `<div class="charter-document">
    ${docHeader(data.titulo||'One-Pager', 'One-pager', true)}
    <div class="onepager-cols">
      <div class="onepager-col">
        <div class="onepager-col-label" style="color:#2b9777">El problema</div>
        <div class="onepager-col-body">${escapeHTML(data.problema||'—')}</div>
      </div>
      <div class="onepager-divider"></div>
      <div class="onepager-col">
        <div class="onepager-col-label" style="color:#2b9777">La solución</div>
        <div class="onepager-col-body">${escapeHTML(data.solucion||'—')}</div>
      </div>
    </div>
    <div class="charter-section">
      <div class="section-title" style="color:#239a5b;border-left-color:#239a5b">Beneficios esperados</div>
      <div class="benefit-chips">${chips || '<span class="text-muted">No especificados</span>'}</div>
    </div>
    <div class="onepager-badges" style="display:flex;flex-direction:column;gap:8px;margin-bottom:20px;">
      <div><span style="font-size:0.78rem;color:#666;margin-right:6px;">Impacto</span><span class="level-badge ${levelClass(data.impacto)}" style="${levelStyle(data.impacto)}">${escapeHTML(data.impacto||'—')}</span></div>
      <div><span style="font-size:0.78rem;color:#666;margin-right:6px;">Esfuerzo</span><span class="level-badge ${levelClass(data.esfuerzo)}" style="${levelStyle(data.esfuerzo)}">${escapeHTML(data.esfuerzo||'—')}</span></div>
    </div>
    <div class="charter-section">
      <div class="section-title" style="color:#239a5b;border-left-color:#239a5b">Próximo paso recomendado</div>
      <div class="next-step-box" style="border-left-color:#2b9777;background:#f0faf6">${escapeHTML(data.proximoPaso||'—')}</div>
    </div>
    ${DOC_FOOTER}
  </div>`;
}

/* ── renderRaci ── */
function renderRaci(data) {
  const roles = [...new Set((data.actividades||[]).flatMap(a => Object.keys(a.roles||{})))];

  const raciColor = v => ({
    R: 'raci-R', A: 'raci-A', C: 'raci-C', I: 'raci-I'
  }[v] || '');
  const raciStyle = v => ({
    R: 'background:#d4efe7;color:#1a6b4a;font-weight:700',
    A: 'background:#e8f4fd;color:#1a5a8a;font-weight:700',
    C: 'background:#fff3e0;color:#b45309;font-weight:700',
    I: 'background:#f3e8ff;color:#6b21a8;font-weight:700'
  }[v] || '');

  const headerCells = roles.map(r => `<th style="background:#239a5b">${escapeHTML(r)}</th>`).join('');
  const rows = (data.actividades||[]).map(a => {
    const cells = roles.map(r => {
      const val = (a.roles||{})[r] || '—';
      return `<td><span class="raci-badge ${raciColor(val)}" style="${raciStyle(val)}">${escapeHTML(val)}</span></td>`;
    }).join('');
    return `<tr><td class="raci-activity">${escapeHTML(a.actividad||'')}</td>${cells}</tr>`;
  }).join('');

  const leyenda = Object.entries(data.leyenda||{
    R: 'Responsable — quien ejecuta',
    A: 'Aprobador — quien aprueba y rinde cuentas',
    C: 'Consultado — quien da input',
    I: 'Informado — quien recibe updates',
  }).map(([k, v]) =>
    `<div class="raci-legend-row">
      <span class="raci-badge raci-${k}" style="${raciStyle(k)}">${escapeHTML(k)}</span>
      <span class="raci-legend-text">${escapeHTML(v)}</span>
    </div>`).join('');

  return `<div class="charter-document">
    ${docHeader(data.titulo||'Matriz RACI', 'RACI', true)}
    <div style="overflow-x:auto">
      <table class="risk-table raci-table">
        <thead><tr><th class="raci-activity-col" style="background:#239a5b">Actividad</th>${headerCells}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    <div class="raci-legend-grid">${leyenda}</div>
    ${DOC_FOOTER}
  </div>`;
}

/* ── renderBmc ── */
function renderBmc(data) {
  const b = data;
  const cell = (label, content, bg = '#f0faf6') => `
    <div style="border:1px solid #239a5b;border-radius:6px;overflow:hidden;min-height:120px;">
      <div style="background:${bg};padding:8px 12px;border-bottom:2px solid #239a5b;">
        <span style="font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:#1a6b4a;">${label}</span>
      </div>
      <div style="padding:10px 12px;font-size:0.82rem;line-height:1.5;color:#22282E;background:#fff;">${escapeHTML(content||'Por definir')}</div>
    </div>`;

  const cellBlue = (label, content) => cell(label, content, '#e8f4fd');

  return `<div class="charter-document">
    ${docHeader(b.titulo||'Business Model Canvas', 'BMC', true)}
    <div style="display:grid;gap:8px;margin-top:24px;">
      <!-- Fila 1: 5 columnas -->
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr 1fr;gap:8px;">
        ${cell('Socios Clave', b.sociosClave, '#f0faf6')}
        <div style="display:grid;grid-template-rows:1fr 1fr;gap:8px;">
          ${cell('Actividades Clave', b.actividadesClave, '#f0faf6')}
          ${cell('Recursos Clave', b.recursosClave, '#f0faf6')}
        </div>
        ${cell('Propuesta de Valor', b.propuestaValor, '#e8f4fd')}
        <div style="display:grid;grid-template-rows:1fr 1fr;gap:8px;">
          ${cell('Relaciones con Clientes', b.relacionesClientes, '#f0faf6')}
          ${cell('Canales', b.canales, '#f0faf6')}
        </div>
        ${cell('Segmentos de Clientes', b.segmentosClientes, '#f0faf6')}
      </div>
      <!-- Fila 2: 2 columnas -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
        ${cellBlue('Estructura de Costos', b.estructuraCostos)}
        ${cellBlue('Fuentes de Ingreso', b.fuentesIngreso)}
      </div>
    </div>
    ${DOC_FOOTER}
  </div>`;
}

/* ── renderBusinessCase ── */
function renderBusinessCase(data) {
  const rec = (data.recomendacion||'').toLowerCase();
  const isGo    = rec === 'go';
  const isNogo  = rec === 'no go';
  const recClass = isGo ? 'rec-go' : isNogo ? 'rec-nogo' : 'rec-pending';
  const recLabel = isGo ? '✓ GO' : isNogo ? '✗ NO GO' : '⚠️ Pendiente de análisis';
  const recStyle = isGo ? 'background:#2aa964' : isNogo ? '' : 'background:#fff0f0;color:#c0392b;border:2px solid #e74c3c';

  const supuestos = (data.supuestos||[]).map(s =>
    `<li class="bc-supuesto">${escapeHTML(s)}</li>`).join('');

  return `<div class="charter-document">
    ${docHeader(data.titulo||'Business Case', 'Business Case', true)}
    <div class="bc-executive-box" style="border-left-color:#2b9777;background:#f0faf6">
      <div class="bc-executive-label">Resumen Ejecutivo</div>
      <div class="bc-executive-body">${escapeHTML(data.resumenEjecutivo||'—')}</div>
    </div>
    <div class="onepager-cols">
      <div class="onepager-col">
        <div class="onepager-col-label">El problema</div>
        <div class="onepager-col-body">${escapeHTML(data.problema||'—')}</div>
      </div>
      <div class="onepager-divider"></div>
      <div class="onepager-col">
        <div class="onepager-col-label">Solución propuesta</div>
        <div class="onepager-col-body">${escapeHTML(data.solucionPropuesta||'—')}</div>
      </div>
    </div>
    <div class="charter-section">
      <div class="section-title" style="color:#239a5b;border-left-color:#239a5b">Métricas financieras</div>
      <table class="bc-metrics-table">
        <tbody>
          <tr><td class="bc-metric-label" style="color:#2b9777">Costo estimado</td><td class="bc-metric-value">${escapeHTML(data.costoEstimado||'Por definir')}</td></tr>
          <tr><td class="bc-metric-label" style="color:#2b9777">Beneficio estimado</td><td class="bc-metric-value">${escapeHTML(data.beneficioEstimado||'Por definir')}</td></tr>
          <tr><td class="bc-metric-label" style="color:#2b9777">ROI estimado</td><td class="bc-metric-value">${escapeHTML(data.roiEstimado||'Por definir')}</td></tr>
          <tr><td class="bc-metric-label" style="color:#2b9777">Payback estimado</td><td class="bc-metric-value">${escapeHTML(data.paybackEstimado||'Por definir')}</td></tr>
        </tbody>
      </table>
    </div>
    <div class="charter-section">
      <div class="section-title" style="color:#239a5b;border-left-color:#239a5b">Supuestos</div>
      <ul class="bc-supuestos-list">${supuestos || '<li class="text-muted">No especificados</li>'}</ul>
    </div>
    <div class="bc-recommendation">
      <span class="bc-rec-label">Recomendación</span>
      <span class="bc-rec-badge ${recClass}" style="${recStyle}">${recLabel}</span>
    </div>
    ${DOC_FOOTER}
  </div>`;
}

/* ─────────────────────────────────────────────
   MODAL ACTIONS
───────────────────────────────────────────── */
function closeDocsModal() {
  const overlay = document.getElementById('charterOverlay');
  overlay.style.display = 'none';
  overlay.setAttribute('aria-hidden', 'true');
}

function closeCharter() { closeDocsModal(); }

function overlayClick(e) {
  if (e.target === document.getElementById('charterOverlay')) closeDocsModal();
}

function printCurrentDoc() {
  const contentEl = document.getElementById('docTabContent');
  if (!contentEl || !contentEl.innerHTML.trim()) {
    alert('No hay documento para imprimir.');
    return;
  }

  // Clonar todo el CSS ya cargado en la página principal
  let cssText = '';
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules) {
        cssText += rule.cssText + '\n';
      }
    } catch (e) {
      // Hojas de otro origen pueden lanzar SecurityError, las saltamos
    }
  }

  console.log('CSS clonado - longitud total:', cssText.length);
  console.log('Contiene .charter-meta?:', cssText.includes('.charter-meta'));
  console.log('Contiene .section-title?:', cssText.includes('.section-title'));
  console.log('Contiene --primary?:', cssText.includes('--primary'));

  const rawHTML = contentEl.innerHTML
    .replace(/src="\/assets\/logo\.jpg"/g, 'src="http://localhost:3000/assets/logo.jpg"')
    .replace(/var\(--primary\)/g, '#2b9777')
    .replace(/var\(--secondary\)/g, '#239a5b')
    .replace(/var\(--success\)/g, '#00713d')
    .replace(/var\(--text\)/g, '#22282E')
    .replace(/var\(--text-muted\)/g, '#666666')
    .replace(/var\(--bg\)/g, '#f4f4f2')
    .replace(/var\(--border\)/g, '#e0e0e0')
    .replace(/var\(--warning\)/g, '#92400E')
    .replace(/var\(--warning-bg\)/g, '#FFFBEB')
    .replace(/var\(--warning-border\)/g, '#FDE68A')
    .replace(/var\(--error\)/g, '#B91C1C')
    .replace(/var\(--error-bg\)/g, '#FEF2F2')
    .replace(/var\(--error-border\)/g, '#FECACA');

  // Eliminar iframe anterior si existe
  const existing = document.getElementById('printFrame');
  if (existing) existing.remove();

  // Crear iframe oculto
  const iframe = document.createElement('iframe');
  iframe.id = 'printFrame';
  iframe.style.cssText = 'position:fixed;top:-9999px;left:-9999px;width:900px;height:600px;border:none;';
  document.body.appendChild(iframe);

  const doc = iframe.contentDocument || iframe.contentWindow.document;
  doc.open();
  doc.write(`<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Documento — Grupo ANC</title>
  <style>
    ${cssText}
    /* Overrides solo para impresión */
    body { background: #fff !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; margin: 0; }
    .charter-document { padding: 48px 52px !important; box-shadow: none !important; }
    @media print {
      body { margin: 0; }
      .charter-document { padding: 20px 28px !important; }
    }
  </style>
</head>
<body>
  ${rawHTML}
</body>
</html>`);
  doc.close();

  iframe.onload = () => {
    setTimeout(() => {
      iframe.contentWindow.focus();
      iframe.contentWindow.print();
      setTimeout(() => iframe.remove(), 1000);
    }, 300);
  };
}

function copyCharter() {
  const contentEl = document.getElementById('docTabContent');
  if (!contentEl || !contentEl.innerText.trim()) {
    alert('No hay documentos generados aún.');
    return;
  }

  navigator.clipboard.writeText(contentEl.innerText).then(() => {
    const btn = document.getElementById('copyCharterBtn');
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = '✓ Copiado';
      btn.style.color = 'var(--success)';
      setTimeout(() => { btn.innerHTML = orig; btn.style.color = ''; }, 2000);
    }
  }).catch(() => {
    alert('No se pudo copiar automáticamente. Por favor, usa Ctrl+A y Ctrl+C en el documento.');
  });
}

/* ─────────────────────────────────────────────
   UI – LOADING STATE
───────────────────────────────────────────── */
function setLoading(on) {
  state.isLoading = on;
  const btn   = document.getElementById('sendBtn');
  const input = document.getElementById('userInput');

  if (on) {
    btn.disabled = input.disabled = true;
    setSkipVisible(false);
    showTypingIndicator();
  } else {
    btn.disabled = input.disabled = false;
    hideTypingIndicator();
    const hasOptions = document.getElementById('optionsArea').children.length > 0;
    if (!hasOptions) setSkipVisible(true);
    input.focus();
  }
}

/* ─────────────────────────────────────────────
   UI – INPUT SETUP
───────────────────────────────────────────── */
function setupInput() {
  const input = document.getElementById('userInput');
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  input.addEventListener('input', () => resizeTextarea(input));
}

function resizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

/* ─────────────────────────────────────────────
   RESET
───────────────────────────────────────────── */
function setupReset() {
  document.getElementById('resetBtn').addEventListener('click', () => {
    if (!confirm('¿Iniciar una nueva conversación? La actual se perderá.')) return;

    if (currentAbortController) {
      currentAbortController.abort();
      currentAbortController = null;
    }

    state.history            = [];
    state.blockStatus        = { 1:'pending',2:'pending',3:'pending',4:'pending',5:'pending' };
    state.readyForCharter    = false;
    state.selectedDocs       = [];
    state.generatedDocs      = {};
    state.lastRecommendation = null;
    state.displayMessages    = [];

    clearSession();

    [1,2,3,4,5].forEach(id => {
      const el = document.getElementById(`block-${id}`);
      if (el) el.dataset.status = 'pending';
    });

    updateProgressIndicator();
    setSkipVisible(false);

    document.getElementById('charterReadyBanner').style.display = 'none';
    document.getElementById('openSelectorBtn').style.display = 'none';
    document.getElementById('viewDocsBtn').style.display = 'none';

    closeDocsModal();
    showWelcome();
  });
}

/* ─────────────────────────────────────────────
   HELPERS
───────────────────────────────────────────── */
function escapeHTML(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}
