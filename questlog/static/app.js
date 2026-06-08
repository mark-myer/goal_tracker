const state = {
  quests: [],
};

const elements = {
  form: document.getElementById('createQuestForm'),
  questList: document.getElementById('questList'),
  refreshButton: document.getElementById('refreshButton'),
  statusMessage: document.getElementById('statusMessage'),
  statXp: document.getElementById('statXp'),
  statLevel: document.getElementById('statLevel'),
  statStreak: document.getElementById('statStreak'),
};

const api = {
  async request(path, options = {}) {
    const response = await fetch(path, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options,
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Request failed (${response.status})`);
    }
    if (response.status === 204) {
      return null;
    }
    return response.json();
  },

  listQuests() {
    return this.request('/quests');
  },

  userStats() {
    return this.request('/user/stats');
  },

  createQuest(payload) {
    return this.request('/quests', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  deleteQuest(questId) {
    return this.request(`/quests/${questId}`, { method: 'DELETE' });
  },

  logMetric(metricId, rawValue) {
    return this.request(`/metrics/${metricId}/log`, {
      method: 'POST',
      body: JSON.stringify({ raw_value: rawValue }),
    });
  },
};

function setStatus(message, type = '') {
  elements.statusMessage.textContent = message;
  elements.statusMessage.className = `status-message ${type}`.trim();
}

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function renderQuests() {
  if (!state.quests.length) {
    elements.questList.innerHTML = '<p class="empty">No quests yet. Create one to get started.</p>';
    return;
  }

  elements.questList.innerHTML = state.quests
    .map((quest) => {
      const progress = Math.min(100, Math.max(0, quest.progress_pct || 0)).toFixed(1);
      const metrics = quest.metrics.length
        ? quest.metrics
            .map(
              (metric) => `
                <article class="metric-item">
                  <div class="metric-head">
                    <strong>${escapeHtml(metric.label)}</strong>
                    <span>${metric.current_value} / ${metric.target_value}${metric.unit ? ` ${escapeHtml(metric.unit)}` : ''}</span>
                  </div>
                  <form class="metric-update" data-metric-id="${metric.id}">
                    <input type="number" step="any" name="rawValue" placeholder="Log value" required />
                    <button class="btn secondary" type="submit">Log</button>
                  </form>
                </article>
              `
            )
            .join('')
        : '<p class="empty">No metrics configured.</p>';

      return `
        <article class="quest-card">
          <div class="quest-header">
            <div>
              <h3>${escapeHtml(quest.title)}</h3>
              <p class="quest-meta">${escapeHtml(quest.category || 'Uncategorized')} · ${escapeHtml(quest.status)} · ${quest.xp_reward} XP</p>
              ${quest.description ? `<p>${escapeHtml(quest.description)}</p>` : ''}
            </div>
            <button class="btn danger" type="button" data-delete-quest="${quest.id}">Delete</button>
          </div>
          <div class="progress" aria-label="Quest progress">
            <div class="progress-bar" style="width:${progress}%"></div>
          </div>
          <p class="quest-meta">Progress: ${progress}%</p>
          <div class="metric-list">${metrics}</div>
        </article>
      `;
    })
    .join('');
}

function readOptionalNumber(value) {
  if (value === '' || value == null) {
    return null;
  }
  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    return null;
  }
  return parsed;
}

async function loadDashboard() {
  const [quests, stats] = await Promise.all([api.listQuests(), api.userStats()]);
  state.quests = quests;
  renderQuests();
  elements.statXp.textContent = String(stats.total_xp);
  elements.statLevel.textContent = String(stats.level);
  elements.statStreak.textContent = String(stats.streak);
}

async function handleCreateQuest(event) {
  event.preventDefault();
  const form = new FormData(elements.form);
  const metricLabel = form.get('metric_label')?.toString().trim() || '';
  const metricTarget = readOptionalNumber(form.get('metric_target'));

  const payload = {
    title: form.get('title')?.toString().trim() || '',
    category: form.get('category')?.toString().trim() || null,
    description: form.get('description')?.toString().trim() || null,
    xp_reward: Number(form.get('xp_reward') || 0),
    metrics: [],
  };

  if (metricLabel || metricTarget != null) {
    if (!metricLabel || metricTarget == null) {
      setStatus('Metric needs both label and target value.', 'error');
      return;
    }
    payload.metrics.push({
      label: metricLabel,
      target_value: metricTarget,
      current_value: readOptionalNumber(form.get('metric_current')) || 0,
      unit: form.get('metric_unit')?.toString().trim() || null,
      source_type: 'manual',
    });
  }

  try {
    await api.createQuest(payload);
    elements.form.reset();
    elements.form.querySelector('#questXp').value = '0';
    elements.form.querySelector('#metricCurrent').value = '0';
    await loadDashboard();
    setStatus('Quest created.', 'success');
  } catch (error) {
    setStatus(`Unable to create quest: ${error.message}`, 'error');
  }
}

async function handleQuestListClick(event) {
  const button = event.target.closest('[data-delete-quest]');
  if (!button) {
    return;
  }
  const questId = Number(button.getAttribute('data-delete-quest'));
  if (!questId) {
    return;
  }
  try {
    await api.deleteQuest(questId);
    await loadDashboard();
    setStatus('Quest deleted.', 'success');
  } catch (error) {
    setStatus(`Unable to delete quest: ${error.message}`, 'error');
  }
}

async function handleMetricLog(event) {
  const form = event.target.closest('.metric-update');
  if (!form) {
    return;
  }
  event.preventDefault();
  const metricId = Number(form.getAttribute('data-metric-id'));
  const rawValueField = form.querySelector('input[name="rawValue"]');
  const rawValue = Number(rawValueField.value);
  if (!Number.isFinite(rawValue)) {
    setStatus('Enter a valid number for metric update.', 'error');
    return;
  }

  try {
    await api.logMetric(metricId, rawValue);
    rawValueField.value = '';
    await loadDashboard();
    setStatus('Metric progress updated.', 'success');
  } catch (error) {
    setStatus(`Unable to log metric: ${error.message}`, 'error');
  }
}

function setupLiveUpdates() {
  const source = new EventSource('/events');
  source.addEventListener('metric_update', async () => {
    try {
      await loadDashboard();
      setStatus('Live update received.', 'success');
    } catch (error) {
      setStatus(`Refresh failed after live update: ${error.message}`, 'error');
    }
  });
  source.onerror = () => {
    setStatus('Live updates unavailable. Manual refresh still works.', 'error');
  };
}

async function init() {
  elements.form.addEventListener('submit', handleCreateQuest);
  elements.questList.addEventListener('click', handleQuestListClick);
  elements.questList.addEventListener('submit', handleMetricLog);
  elements.refreshButton.addEventListener('click', () =>
    loadDashboard()
      .then(() => setStatus('Dashboard refreshed.', 'success'))
      .catch((error) => setStatus(`Unable to refresh: ${error.message}`, 'error'))
  );

  try {
    await loadDashboard();
    setStatus('Dashboard ready.', 'success');
  } catch (error) {
    setStatus(`Unable to load dashboard: ${error.message}`, 'error');
  }
  setupLiveUpdates();
}

init();
