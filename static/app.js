const log        = document.getElementById('log');
const input      = document.getElementById('task-input');
const sendBtn    = document.getElementById('send-btn');
const statusDot  = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const progressWrap  = document.getElementById('progress-bar-wrap');
const progressBar   = document.getElementById('progress-bar-inner');
const progressLabel = document.getElementById('progress-label');
const histPanel  = document.getElementById('history-panel');
const histList   = document.getElementById('history-list');
const histToggle = document.getElementById('history-toggle');
const histHeader = document.getElementById('history-header');

// Toggle histórico
histHeader.addEventListener('click', () => {
  histPanel.classList.toggle('collapsed');
  histToggle.textContent = histPanel.classList.contains('collapsed') ? '▶' : '▼';
});

// Carrega histórico do servidor
async function loadHistory() {
  try {
    const res = await fetch('/history');
    const data = await res.json();
    const sessions = (data.sessions || []).slice().reverse(); // mais recente primeiro

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
        <span class="history-steps">${s.steps} steps</span>
      `;

      // Clica no item — preenche input com a tarefa
      item.addEventListener('click', () => {
        input.value = s.task;
        input.focus();
      });

      histList.appendChild(item);
    });
  } catch (e) {
    histList.innerHTML = '<div style="color:var(--muted);font-size:11px;padding:4px 8px">Erro ao carregar histórico.</div>';
  }
}

let ws;
let running = false;

function setStatus(state, text) {
  statusDot.className = state;
  statusText.textContent = text;
}

function addEntry(type, label, content) {
  const div = document.createElement('div');
  div.className = `entry ${type}`;
  div.innerHTML = `<div class="label">${label}</div>${escapeHtml(content)}`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function connect() {
  ws = new WebSocket(`ws://${location.host}/ws`);

  ws.onopen = () => {
    setStatus('connected', 'Conectado');
    sendBtn.disabled = false;
    loadHistory();
  };

  ws.onclose = () => {
    setStatus('error', 'Desconectado — reconectando...');
    sendBtn.disabled = true;
    setTimeout(connect, 2000);
  };

  ws.onerror = () => {
    setStatus('error', 'Erro de conexão');
  };

  let streamingEl = null;

  function startStreaming() {
    const div = document.createElement('div');
    div.className = 'entry thought streaming';
    div.innerHTML = '<div class="label">💭 THOUGHT</div><span class="stream-text"></span><span class="cursor">▋</span>';
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
    streamingEl = div.querySelector('.stream-text');
    return div;
  }

  function appendToken(token) {
    if (!streamingEl) return;
    streamingEl.textContent += token;
    log.scrollTop = log.scrollHeight;
  }

  function endStreaming() {
    if (!streamingEl) return;
    const cursor = streamingEl.parentElement.querySelector('.cursor');
    if (cursor) cursor.remove();
    streamingEl = null;
  }

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch (data.type) {
      case 'token_start':
        startStreaming();
        break;
      case 'token':
        appendToken(data.content);
        break;
      case 'token_end':
        endStreaming();
        break;
      case 'step': {
        addEntry('step', '▶ STEP', data.content);
        // Atualiza barra de progresso — "Step X/Y" ou "Passo X/Y"
        const match = data.content.match(/(\d+)\s*\/\s*(\d+)/);
        if (match) {
          const cur = parseInt(match[1]);
          const max = parseInt(match[2]);
          const pct = Math.round((cur / max) * 100);
          progressWrap.classList.remove('hidden');
          progressBar.style.width = pct + '%';
          progressLabel.textContent = `Step ${cur} / ${max}`;
        }
        break;
      }
      case 'action':
        addEntry('action', '⚡ ACTION', data.content);
        break;
      case 'observation':
        addEntry('observation', '👁 OBSERVATION', data.content);
        break;
      case 'error':
        addEntry('error', '✗ ERRO', data.content);
        break;
      case 'final':
        addEntry('final', '✓ RESPOSTA FINAL', data.content);
        break;
      case 'done':
        setStatus('connected', 'Pronto');
        progressBar.style.width = '100%';
        setTimeout(() => { progressWrap.classList.add('hidden'); progressBar.style.width = '0%'; }, 800);
        input.disabled = false;
        sendBtn.disabled = false;
        running = false;
        input.focus();
        loadHistory();
        break;
    }
  };
}

function sendTask() {
  const task = input.value.trim();
  if (!task || running) return;

  running = true;
  input.disabled = true;
  sendBtn.disabled = true;
  setStatus('running', 'Executando...');
  progressBar.style.width = '0%';
  progressWrap.classList.remove('hidden');
  progressLabel.textContent = 'Iniciando...';

  addEntry('task', '📋 TAREFA', task);
  input.value = '';

  ws.send(JSON.stringify({ task }));
}

sendBtn.addEventListener('click', sendTask);

input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendTask();
  }
});

connect();
