// ---- CONSTANTES ----
const MAX_TABS = 5;

// ---- DOM GLOBAL ----
const input        = document.getElementById('task-input');
const sendBtn      = document.getElementById('send-btn');
const micBtn       = document.getElementById('mic-btn');
const cancelBtn    = document.getElementById('cancel-btn');
const clearBtn     = document.getElementById('clear-btn');
const themeBtn     = document.getElementById('theme-btn');
const statusDot    = document.getElementById('status-dot');
const statusText   = document.getElementById('status-text');
const progressWrap = document.getElementById('progress-bar-wrap');
const progressBar  = document.getElementById('progress-bar-inner');
const progressLabel= document.getElementById('progress-label');
const tokenBadge   = document.getElementById('token-badge');
const histPanel    = document.getElementById('history-panel');
const histSearch   = document.getElementById('history-search');
const histList     = document.getElementById('history-list');
const histToggle   = document.getElementById('history-toggle');
const histHeader   = document.getElementById('history-header');
const healthBtn    = document.getElementById('health-btn');
const healthOv     = document.getElementById('health-overlay');
const healthClose  = document.getElementById('health-close');
const healthCont   = document.getElementById('health-content');
const logsBtn      = document.getElementById('logs-btn');
const logsPanel    = document.getElementById('logs-panel');
const logsClose    = document.getElementById('logs-close');
const logsCont     = document.getElementById('logs-content');
const tabsBar      = document.getElementById('tabs-bar');
const logContainer = document.getElementById('log-container');
const modelSelect  = document.getElementById('model-select');
const agentsPanel  = document.getElementById('agents-panel');
const templatesBtn = document.getElementById('templates-btn');
const templatesMenu= document.getElementById('templates-menu');

// ---- ESTADO GLOBAL ----
let tabs       = [];
let activeTabId= null;
let nextTabId  = 1;

// ---- GERENCIAMENTO DE ABAS ----
function createTab(label) {
  if (tabs.length >= MAX_TABS) return;
  const id = nextTabId++;
  const logEl = document.createElement('main');
  logEl.className = 'log-pane';
  logContainer.appendChild(logEl);

  // Drag & drop por aba
  logEl.addEventListener('dragover', e => { e.preventDefault(); logEl.classList.add('drag-over'); });
  logEl.addEventListener('dragleave', () => logEl.classList.remove('drag-over'));
  logEl.addEventListener('drop', e => handleDrop(e, logEl));

  const tab = {
    id,
    label:          label || `Chat ${id}`,
    logEl,
    ws:             null,
    running:        false,
    streamingEl:    null,
    finalStreamEl:  null,
    finalStreamText:'',
    agentMsgEl:     null,
    thinkingEl:     null,
    stepCount:      0,
    taskLabel:      null,
  };
  tabs.push(tab);
  switchTab(id);
  renderTabBar();
  connectTab(tab);
  return tab;
}

function closeTab(id) {
  const idx = tabs.findIndex(t => t.id === id);
  if (idx === -1) return;
  const tab = tabs[idx];
  if (tab.ws) tab.ws.close();
  tab.logEl.remove();
  tabs.splice(idx, 1);

  if (tabs.length === 0) {
    createTab();
    return;
  }
  if (activeTabId === id) {
    const next = tabs[Math.min(idx, tabs.length - 1)];
    switchTab(next.id);
  }
  renderTabBar();
}

function switchTab(id) {
  activeTabId = id;
  tabs.forEach(t => {
    t.logEl.classList.toggle('active', t.id === id);
  });
  const tab = getActiveTab();
  if (tab) syncUIToTab(tab);
  renderTabBar();
}

function getActiveTab() {
  return tabs.find(t => t.id === activeTabId) || null;
}

function syncUIToTab(tab) {
  const running = tab.running;
  input.disabled    = running;
  sendBtn.disabled  = !tab.ws || tab.ws.readyState !== WebSocket.OPEN || running;
  cancelBtn.classList.toggle('hidden', !running);
  if (running) {
    setStatus('running', 'Executando...');
  } else if (tab.ws && tab.ws.readyState === WebSocket.OPEN) {
    setStatus('connected', 'Pronto');
  } else {
    setStatus('error', 'Desconectado');
  }
}

function renderTabBar() {
  tabsBar.innerHTML = '';
  tabs.forEach(tab => {
    const btn = document.createElement('button');
    btn.className = 'tab-btn' + (tab.id === activeTabId ? ' active' : '');
    btn.title = tab.label;

    const dot = document.createElement('span');
    dot.className = 'tab-dot' + (tab.running ? ' running' : '');
    btn.appendChild(dot);

    const label = document.createElement('span');
    label.className = 'tab-label';
    label.textContent = tab.label;
    btn.appendChild(label);

    const closeX = document.createElement('button');
    closeX.className = 'tab-close';
    closeX.textContent = '✕';
    closeX.title = 'Fechar aba';
    closeX.addEventListener('click', e => { e.stopPropagation(); closeTab(tab.id); });
    btn.appendChild(closeX);

    btn.addEventListener('click', () => switchTab(tab.id));
    tabsBar.appendChild(btn);
  });

  // Botão nova aba
  if (tabs.length < MAX_TABS) {
    const newBtn = document.createElement('button');
    newBtn.className = 'new-tab-btn';
    newBtn.textContent = '+';
    newBtn.title = 'Nova aba (Ctrl+T)';
    newBtn.addEventListener('click', () => createTab());
    tabsBar.appendChild(newBtn);
  }
}

// ---- WEBSOCKET POR ABA ----
function connectTab(tab) {
  tab.ws = new WebSocket(`ws://${location.host}/ws`);

  tab.ws.onopen = () => {
    // Envia token JWT no handshake (ignorado pelo servidor se auth desativado)
    const token = getToken();
    if (token) tab.ws.send(JSON.stringify({ type: 'auth', token }));
    if (tab.id === activeTabId) syncUIToTab(tab);
    loadHistory();
  };

  tab.ws.onclose = () => {
    if (tab.id === activeTabId) syncUIToTab(tab);
    // Reconecta após 2s se aba ainda existe
    if (tabs.find(t => t.id === tab.id)) {
      setTimeout(() => connectTab(tab), 2000);
    }
  };

  tab.ws.onerror = () => {
    if (tab.id === activeTabId) setStatus('error', 'Erro de conexão');
  };

  tab.ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleMessage(tab, data);
  };
}

function handleMessage(tab, data) {
  const isActive = tab.id === activeTabId;

  switch (data.type) {
    case 'token_start':
      startStreaming(tab);
      break;
    case 'token':
      appendToken(tab, data.content);
      break;
    case 'token_end':
      endStreaming(tab);
      break;
    case 'agent_status':
      updateAgentChip(data.agent, data.status, data.subtask || '');
      if (data.status === 'done' && data.result) {
        addEntry(tab, 'observation', `✓ ${data.agent}`, data.result);
      }
      break;
    case 'final_stream_start':
      endStreaming(tab);
      startFinalStreaming(tab);
      break;
    case 'final_token':
      appendFinalToken(tab, data.content);
      break;
    case 'final_stream_end':
      endFinalStreaming(tab);
      break;
    case 'thought':
      addEntry(tab, 'thought', '💭 THOUGHT', data.content);
      break;
    case 'step': {
      addEntry(tab, 'step', '▶ STEP', data.content);
      if (isActive) {
        const match = data.content.match(/(\d+)\s*\/\s*(\d+)/);
        if (match) {
          const cur = parseInt(match[1]);
          const max = parseInt(match[2]);
          progressWrap.classList.remove('hidden');
          progressBar.style.width = Math.round((cur / max) * 100) + '%';
          progressLabel.textContent = `Step ${cur} / ${max}`;
        }
      }
      break;
    }
    case 'action':
      addEntry(tab, 'action', '⚡ ACTION', data.content);
      break;
    case 'observation':
      addEntry(tab, 'observation', '👁 OBSERVATION', data.content);
      break;
    case 'error':
      addEntry(tab, 'error', '✗ ERRO', data.content);
      break;
    case 'final':
      addEntry(tab, 'final', '✓ RESPOSTA FINAL', data.content);
      break;
    case 'token_usage':
      if (isActive) {
        tokenBadge.textContent = `↑${data.prompt} ↓${data.completion} tokens`;
        tokenBadge.classList.remove('hidden');
      }
      break;
    case 'done': {
      tab.running = false;
      renderTabBar();
      if (isActive) {
        setStatus('connected', 'Pronto');
        progressBar.style.width = '100%';
        setTimeout(() => { progressWrap.classList.add('hidden'); progressBar.style.width = '0%'; }, 800);
        input.disabled = false;
        sendBtn.disabled = false;
        cancelBtn.classList.add('hidden');
        input.focus();
        loadHistory();
      }
      if (!document.hasFocus()) notifyDone(tab.taskLabel || 'Tarefa concluída');
      break;
    }
  }
}

// ---- STREAMING (thought tokens → thinking section) ----
function startStreaming(tab) {
  ensureAgentMsg(tab);
  const div = document.createElement('div');
  div.className = 'think-entry thought streaming';
  div.innerHTML = '<span class="think-label">💭</span><span class="stream-text"></span><span class="cursor">▋</span>';
  tab.thinkingEl.appendChild(div);
  tab.logEl.scrollTop = tab.logEl.scrollHeight;
  tab.streamingEl = div.querySelector('.stream-text');
}

function appendToken(tab, token) {
  if (!tab.streamingEl) return;
  tab.streamingEl.textContent += token;
  tab.logEl.scrollTop = tab.logEl.scrollHeight;
}

function endStreaming(tab) {
  if (!tab.streamingEl) return;
  const entry = tab.streamingEl.closest('.think-entry');
  entry?.querySelector('.cursor')?.remove();
  entry?.classList.remove('streaming');
  tab.stepCount++;
  const cnt = tab.agentMsgEl?.querySelector('.step-count');
  if (cnt) cnt.textContent = `${tab.stepCount} passo${tab.stepCount !== 1 ? 's' : ''}`;
  tab.streamingEl = null;
}

// ---- PAINEL DE AGENTES COLABORATIVOS ----
const _agentChips = {};

function updateAgentChip(agent, status, subtask) {
  agentsPanel.classList.remove('hidden');
  if (!_agentChips[agent]) {
    const chip = document.createElement('div');
    chip.className = 'agent-chip';
    chip.id = `chip-${agent}`;
    agentsPanel.appendChild(chip);
    _agentChips[agent] = chip;
  }
  const chip = _agentChips[agent];
  chip.className = `agent-chip ${status}`;
  chip.textContent = status === 'running' ? `⏳ ${agent}` : `✓ ${agent}`;
  chip.title = subtask;
  if (status === 'done') {
    setTimeout(() => {
      chip.remove();
      delete _agentChips[agent];
      if (agentsPanel.children.length === 0) agentsPanel.classList.add('hidden');
    }, 3000);
  }
}

// ---- AGENT RESPONSE CONTAINER ----
function ensureAgentMsg(tab) {
  if (tab.agentMsgEl) return;
  const msg = document.createElement('div');
  msg.className = 'msg agent';
  msg.innerHTML = `
    <div class="avatar">🤖</div>
    <div class="msg-body">
      <div class="bubble thinking-bubble">
        <span class="typing-dots"><span></span><span></span><span></span></span>
      </div>
      <details class="thinking-details">
        <summary class="thinking-summary">💭 <span class="step-count">pensando...</span></summary>
        <div class="thinking-content"></div>
      </details>
    </div>`;
  tab.logEl.appendChild(msg);
  tab.logEl.scrollTop = tab.logEl.scrollHeight;
  tab.agentMsgEl = msg;
  tab.thinkingEl = msg.querySelector('.thinking-content');
  tab.stepCount  = 0;
}

function addThinkingEntry(tab, type, icon, content) {
  ensureAgentMsg(tab);
  const div = document.createElement('div');
  div.className = `think-entry ${type}`;
  div.innerHTML = `<span class="think-label">${icon}</span>${escapeHtml(String(content))}`;
  tab.thinkingEl.appendChild(div);
  tab.stepCount++;
  const cnt = tab.agentMsgEl.querySelector('.step-count');
  if (cnt) cnt.textContent = `${tab.stepCount} passo${tab.stepCount !== 1 ? 's' : ''}`;
  tab.logEl.scrollTop = tab.logEl.scrollHeight;
}

function _addMsgActions(tab, content) {
  if (!tab.agentMsgEl) return;
  const row = document.createElement('div');
  row.className = 'msg-actions';
  const cp = document.createElement('button');
  cp.className = 'action-btn copy-btn'; cp.textContent = '⎘ copiar';
  cp.addEventListener('click', () => {
    navigator.clipboard.writeText(content).then(() => {
      cp.textContent = '✓ copiado'; cp.classList.add('copied');
      setTimeout(() => { cp.textContent = '⎘ copiar'; cp.classList.remove('copied'); }, 2000);
    });
  });
  const sp = document.createElement('button');
  sp.className = 'action-btn speak-btn'; sp.textContent = '🔊';
  sp.addEventListener('click', () => speakText(content));
  row.appendChild(cp); row.appendChild(sp);
  tab.agentMsgEl.querySelector('.msg-body').appendChild(row);
}

function finalizeAgentResponse(tab, content) {
  ensureAgentMsg(tab);
  const bubble = tab.agentMsgEl.querySelector('.bubble');
  bubble.classList.remove('thinking-bubble');
  if (typeof marked !== 'undefined') {
    bubble.className = 'bubble md';
    bubble.innerHTML = marked.parse(content);
  } else {
    bubble.className = 'bubble';
    bubble.textContent = content;
  }
  _addMsgActions(tab, content);
  const summary = tab.agentMsgEl.querySelector('.thinking-summary');
  if (summary && tab.stepCount > 0) {
    summary.querySelector('.step-count').textContent = `${tab.stepCount} passo${tab.stepCount !== 1 ? 's' : ''} — clique para ver`;
  } else if (summary && tab.stepCount === 0) {
    tab.agentMsgEl.querySelector('.thinking-details')?.remove();
  }
  tab.agentMsgEl = null; tab.thinkingEl = null;
  tab.logEl.scrollTop = tab.logEl.scrollHeight;
}

// ---- STREAMING DA RESPOSTA FINAL ----
function startFinalStreaming(tab) {
  ensureAgentMsg(tab);
  const bubble = tab.agentMsgEl.querySelector('.bubble');
  bubble.classList.remove('thinking-bubble');
  bubble.innerHTML = '<span class="stream-text"></span><span class="cursor">▋</span>';
  tab.finalStreamEl   = bubble;
  tab.finalStreamText = '';
}

function appendFinalToken(tab, token) {
  if (!tab.finalStreamEl) return;
  tab.finalStreamText += token;
  tab.finalStreamEl.querySelector('.stream-text').textContent = tab.finalStreamText;
  tab.logEl.scrollTop = tab.logEl.scrollHeight;
}

function endFinalStreaming(tab) {
  if (!tab.finalStreamEl) return;
  const content = tab.finalStreamText || '';
  const bubble  = tab.finalStreamEl;
  const cursor  = bubble.querySelector('.cursor');
  if (cursor) cursor.remove();
  if (typeof marked !== 'undefined') {
    bubble.className = 'bubble md';
    bubble.innerHTML = marked.parse(content);
  } else {
    bubble.textContent = content;
  }
  _addMsgActions(tab, content);
  const summary = tab.agentMsgEl?.querySelector('.thinking-summary');
  if (summary && tab.stepCount > 0) {
    summary.querySelector('.step-count').textContent = `${tab.stepCount} passo${tab.stepCount !== 1 ? 's' : ''} — clique para ver`;
  } else if (summary) {
    tab.agentMsgEl?.querySelector('.thinking-details')?.remove();
  }
  tab.finalStreamEl = null; tab.finalStreamText = '';
  tab.agentMsgEl = null; tab.thinkingEl = null;
  tab.logEl.scrollTop = tab.logEl.scrollHeight;
}

// ---- ENTRADAS NO LOG ----
function addEntry(tab, type, label, content) {
  if (type === 'task') {
    // Mensagem do usuário — bubble direita
    const msg = document.createElement('div');
    msg.className = 'msg user';
    msg.innerHTML = `<div class="bubble">${escapeHtml(content)}</div>`;
    tab.logEl.appendChild(msg);
    tab.logEl.scrollTop = tab.logEl.scrollHeight;
    return;
  }
  if (type === 'final') {
    finalizeAgentResponse(tab, content);
    return;
  }
  if (type === 'thought')     { addThinkingEntry(tab, 'thought',     '💭', content); return; }
  if (type === 'action')      { addThinkingEntry(tab, 'action',      '⚡', content); return; }
  if (type === 'observation') { addThinkingEntry(tab, 'observation', '👁', content); return; }
  if (type === 'error')       { addThinkingEntry(tab, 'error',       '✗', content); return; }
  // step / outros — mensagem de sistema pequena
  if (type === 'step') return; // progresso já no progress bar
  const msg = document.createElement('div');
  msg.className = 'msg system';
  msg.innerHTML = `<div class="sys-msg">${escapeHtml(content)}</div>`;
  tab.logEl.appendChild(msg);
  tab.logEl.scrollTop = tab.logEl.scrollHeight;
}

// ---- ENVIO DE TAREFA ----
function sendTask() {
  const tab = getActiveTab();
  if (!tab || !tab.ws || tab.running) return;
  const task = input.value.trim();
  if (!task) return;

  // Atualiza label da aba com a primeira tarefa
  if (tab.label.startsWith('Chat ')) {
    tab.label = task.slice(0, 22) + (task.length > 22 ? '…' : '');
    renderTabBar();
  }
  tab.taskLabel = task;
  tab.running   = true;

  input.disabled = true;
  sendBtn.disabled = true;
  cancelBtn.classList.remove('hidden');
  setStatus('running', 'Executando...');
  progressBar.style.width = '0%';
  progressWrap.classList.remove('hidden');
  progressLabel.textContent = 'Iniciando...';
  tokenBadge.classList.add('hidden');

  addEntry(tab, 'task', '📋 TAREFA', task);
  input.value = '';
  renderTabBar();
  tab.ws.send(JSON.stringify({ task }));
}

// ---- UTILITÁRIOS ----
function setStatus(state, text) {
  statusDot.className = state;
  statusText.textContent = text;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function notifyDone(task) {
  if (Notification.permission === 'granted') {
    new Notification('Agente IA', { body: `✓ ${task.slice(0, 80)}` });
  }
}

async function speakText(text) {
  try {
    const res = await fetch('/speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    const buf = await res.arrayBuffer();
    const ctx = new AudioContext();
    const src = ctx.createBufferSource();
    src.buffer = await ctx.decodeAudioData(buf);
    src.connect(ctx.destination);
    src.start();
  } catch {}
}

// ---- UPLOAD / DRAG & DROP ----
async function handleDrop(e, logEl) {
  e.preventDefault();
  logEl.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (!file) return;
  const tab = getActiveTab();
  if (!tab) return;
  const fd = new FormData();
  fd.append('file', file);
  const imageExts = ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'];
  const isImage   = imageExts.some(e => file.name.toLowerCase().endsWith(e));
  try {
    const res  = await fetch('/upload', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.rag && data.rag.status === 'indexed') {
      addEntry(tab, 'step', '🧠 RAG', `PDF indexado: ${data.name} — ${data.rag.chunks} chunks, ${data.rag.pages} páginas`);
      input.value = `analise o documento "${data.name}" e faça um resumo dos principais pontos`;
    } else if (isImage) {
      addEntry(tab, 'step', '🖼 IMAGEM', `Enviada: ${data.name} (${data.size} bytes)`);
      input.value = `analise a imagem "${data.name}" e descreva o que você vê`;
    } else {
      addEntry(tab, 'step', '📁 ARQUIVO', `Enviado: ${data.name} (${data.size} bytes) → ${data.path}`);
      input.value = `leia e analise o arquivo: ${data.path}`;
    }
    input.focus();
  } catch {
    addEntry(tab, 'error', '✗ ERRO', 'Falha ao enviar arquivo.');
  }
}

// ---- GRAVAÇÃO DE VOZ ----
let mediaRecorder = null;
let audioChunks   = [];

micBtn.addEventListener('click', async () => {
  if (mediaRecorder && mediaRecorder.state === 'recording') { mediaRecorder.stop(); return; }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks   = [];
    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      micBtn.textContent = '🎙';
      micBtn.classList.remove('recording');
      const blob = new Blob(audioChunks, { type: 'audio/webm' });
      const fd   = new FormData();
      fd.append('file', blob, 'audio.webm');
      micBtn.textContent = '⏳';
      try {
        const res  = await fetch('/transcribe', { method: 'POST', body: fd });
        const data = await res.json();
        if (data.text) { input.value = data.text; input.focus(); }
      } catch {}
      micBtn.textContent = '🎙';
    };
    mediaRecorder.start();
    micBtn.textContent = '⏹';
    micBtn.classList.add('recording');
  } catch (e) {
    alert('Microfone não disponível: ' + e.message);
  }
});

// ---- TEMA ----
if (localStorage.getItem('theme') === 'light') {
  document.body.classList.add('light');
  themeBtn.textContent = '🌙';
}
themeBtn.addEventListener('click', () => {
  document.body.classList.toggle('light');
  const isLight = document.body.classList.contains('light');
  localStorage.setItem('theme', isLight ? 'light' : 'dark');
  themeBtn.textContent = isLight ? '🌙' : '☀️';
});

// ---- LIMPAR LOG ----
clearBtn.addEventListener('click', () => {
  const tab = getActiveTab();
  if (tab) tab.logEl.innerHTML = '';
});

// ---- HEALTH ----
healthBtn.addEventListener('click', async () => {
  healthOv.classList.remove('hidden');
  healthCont.innerHTML = 'Carregando...';
  try {
    const d = await (await fetch('/health')).json();
    const ol = d.ollama, g = d.gpu;
    healthCont.innerHTML = `
      <div class="health-row"><span class="health-label">Ollama</span>
        <span class="${ol.ok ? 'health-ok' : 'health-bad'}">${ol.ok ? '✓ online' : '✗ offline'}</span></div>
      ${ol.models.length ? `<div class="health-row"><span class="health-label">Modelos</span><span>${ol.models.join(', ')}</span></div>` : ''}
      ${g.name ? `
      <hr style="border-color:var(--border);margin:10px 0">
      <div class="health-row"><span class="health-label">GPU</span><span>${g.name}</span></div>
      <div class="health-row"><span class="health-label">Temperatura</span>
        <span class="${parseInt(g.temp)>80?'health-bad':'health-ok'}">${g.temp}°C</span></div>
      <div class="health-row"><span class="health-label">Uso GPU</span><span>${g.util}%</span></div>
      <div class="health-row"><span class="health-label">VRAM</span><span>${g.vram_used}/${g.vram_total} MB</span></div>
      ` : '<div style="color:var(--muted);margin-top:10px">nvidia-smi não disponível</div>'}`;
  } catch { healthCont.innerHTML = '<span style="color:var(--error)">Erro ao buscar status.</span>'; }
});
healthClose.addEventListener('click', () => healthOv.classList.add('hidden'));
healthOv.addEventListener('click', e => { if (e.target === healthOv) healthOv.classList.add('hidden'); });

// ---- LOGS ----
let logsInterval = null;
async function refreshLogs() {
  try {
    const lines = await (await fetch('/logs')).json();
    logsCont.innerHTML = lines.map(l =>
      `<div class="log-line ${l.level}">${l.t} [${l.level}] ${escapeHtml(l.msg)}</div>`
    ).join('');
    logsCont.scrollTop = logsCont.scrollHeight;
  } catch {}
}
logsBtn.addEventListener('click', () => {
  const open = logsPanel.classList.toggle('hidden') === false;
  if (open) { refreshLogs(); logsInterval = setInterval(refreshLogs, 3000); }
  else clearInterval(logsInterval);
});
logsClose.addEventListener('click', () => { logsPanel.classList.add('hidden'); clearInterval(logsInterval); });

// ---- NOTIFICAÇÕES ----
if ('Notification' in window && Notification.permission === 'default') Notification.requestPermission();

// ---- TEMPLATES ----
const TEMPLATES = [
  { label: '💵 Cotação do dólar',   task: 'qual o valor do dólar hoje em reais?' },
  { label: '📰 Notícias do Brasil', task: 'pesquise as principais notícias do Brasil hoje' },
  { label: '🌡 Temperatura SP',     task: 'qual a temperatura em São Paulo agora?' },
  { label: '₿ Preço do Bitcoin',   task: 'qual o preço atual do Bitcoin em dólares?' },
  { label: '📋 Listar workspace',   task: 'liste os arquivos na pasta workspace' },
  { label: '🕐 Que horas são?',     task: 'que horas são?' },
  { label: '📄 PDFs indexados',     task: 'liste os documentos PDF que foram indexados para pesquisa' },
];
TEMPLATES.forEach(t => {
  const div = document.createElement('div');
  div.className = 'template-item';
  div.textContent = t.label;
  div.addEventListener('click', () => { input.value = t.task; templatesMenu.classList.add('hidden'); input.focus(); });
  templatesMenu.appendChild(div);
});
templatesBtn.addEventListener('click', e => { e.stopPropagation(); templatesMenu.classList.toggle('hidden'); });
document.addEventListener('click', () => templatesMenu.classList.add('hidden'));

// ---- HISTÓRICO ----
histHeader.addEventListener('click', e => {
  if (e.target === histSearch) return;
  histPanel.classList.toggle('collapsed');
  histToggle.textContent = histPanel.classList.contains('collapsed') ? '▶' : '▼';
});
histSearch.addEventListener('input', () => {
  const q = histSearch.value.toLowerCase();
  histList.querySelectorAll('.history-item').forEach(item => {
    const text = item.querySelector('.history-task')?.textContent.toLowerCase() || '';
    item.style.display = text.includes(q) ? '' : 'none';
  });
});
async function loadHistory() {
  try {
    const res = await fetch('/history');
    const data = await res.json();
    const sessions = (data.sessions || []).slice().reverse();
    if (!sessions.length) {
      histList.innerHTML = '<div style="color:var(--muted);font-size:11px;padding:4px 8px">Nenhuma sessão anterior.</div>';
      return;
    }
    histList.innerHTML = '';
    sessions.forEach(s => {
      const item = document.createElement('div');
      item.className = 'history-item';
      const date = s.timestamp ? s.timestamp.slice(0, 16).replace('T', ' ') : '';
      item.innerHTML = `
        <span class="history-date">${date}</span>
        <span class="history-task">${escapeHtml(s.task)}</span>
        <span class="history-steps">${s.steps} steps</span>`;
      item.addEventListener('click', () => { input.value = s.task; input.focus(); });
      histList.appendChild(item);
    });
  } catch {
    histList.innerHTML = '<div style="color:var(--muted);font-size:11px;padding:4px 8px">Erro ao carregar histórico.</div>';
  }
}

// ---- SEND / CANCEL ----
sendBtn.addEventListener('click', sendTask);
cancelBtn.addEventListener('click', () => {
  const tab = getActiveTab();
  if (!tab || !tab.running) return;
  tab.ws.send(JSON.stringify({ type: 'cancel' }));
  cancelBtn.classList.add('hidden');
  setStatus('connected', 'Cancelando...');
});
input.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendTask(); }
});

// ---- HOTKEYS ----
document.addEventListener('keydown', e => {
  if (e.ctrlKey && e.key === 'k') { e.preventDefault(); input.focus(); input.select(); }
  if (e.ctrlKey && e.key === 'l') { e.preventDefault(); const tab = getActiveTab(); if (tab) tab.logEl.innerHTML = ''; }
  if (e.ctrlKey && e.key === 't') { e.preventDefault(); createTab(); }
  if (e.ctrlKey && e.key === 'w') { e.preventDefault(); if (activeTabId) closeTab(activeTabId); }
  if (e.key === 'Escape') {
    const tab = getActiveTab();
    if (tab?.running) { tab.ws.send(JSON.stringify({ type: 'cancel' })); cancelBtn.classList.add('hidden'); }
  }
  // Ctrl+1–5 para trocar abas
  if (e.ctrlKey && e.key >= '1' && e.key <= '5') {
    const idx = parseInt(e.key) - 1;
    if (tabs[idx]) { e.preventDefault(); switchTab(tabs[idx].id); }
  }
});

// ---- MODELO ----
async function loadModels() {
  try {
    const d = await (await fetch('/models')).json();
    modelSelect.innerHTML = '';
    (d.models.length ? d.models : [d.current]).forEach(m => {
      const opt = document.createElement('option');
      opt.value = m;
      opt.textContent = m;
      if (m === d.current) opt.selected = true;
      modelSelect.appendChild(opt);
    });
  } catch {}
}
modelSelect.addEventListener('change', async () => {
  try {
    await fetch('/model', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ model: modelSelect.value })
    });
  } catch {}
});

// ---- PWA Service Worker ----
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/sw.js').catch(() => {});
}

// ---- JWT: envia token no handshake do WS se existir ----
function getToken() { return localStorage.getItem('jwt_token') || ''; }

// ---- INICIALIZAÇÃO ----
createTab();
loadHistory();
loadModels();
