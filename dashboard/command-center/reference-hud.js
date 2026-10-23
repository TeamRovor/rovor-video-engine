/* Reference-inspired ROVOR HUD: view only, no simulated telemetry or privileged actions. */
(function (root) {
  'use strict';
  const escape = root.RovorLiveData ? root.RovorLiveData.escapeHtml : (v => String(v));
  const STATUS_LABELS = { active: 'CLAIMED', ready: 'READY', blocked: 'BLOCKED', done: 'DONE' };
  const STATUS_ORDER = ['active', 'ready', 'blocked', 'done'];
  const DISPLAY_LIMIT = 5;

  function model(snapshot, mode) {
    const data = snapshot || {};
    const repo = data.repo_snapshot || {};
    const tasks = Array.isArray(data.tasks) ? data.tasks : (data.open_tasks || []);
    const counts = Object.assign({active: 0, ready: 0, blocked: 0, done: 0}, repo.tasks_status || {});
    if (!repo.tasks_status) tasks.forEach(t => { if (t && Object.prototype.hasOwnProperty.call(counts, t.status)) counts[t.status]++; });
    const open = tasks.filter(t => t && t.status !== 'done').sort((a, b) =>
      STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status) ||
      (Number(a.priority) || 999) - (Number(b.priority) || 999) ||
      String(a.id).localeCompare(String(b.id)));
    const routed = Number.isFinite(repo.routed_tasks) ? repo.routed_tasks : null;
    const total = Number(repo.tasks_total) || 0;
    const percent = routed !== null && total ? Math.round(100 * routed / total) : null;
    const safeCoverage = repo.routing_coverage || (routed !== null ? routed + '/' + total : 'UNKNOWN');
    return { tasks: open.slice(0, DISPLAY_LIMIT), openCount: counts.active + counts.ready + counts.blocked,
      counts, total, percent, coverage: safeCoverage, sha: repo.commit || '', prs: repo.open_prs,
      sourceAt: data.generated_at || null, mode, routingComplete: data.route_health?.complete === true,
      fileCount: repo.files_total };
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = String(value);
  }
  function render(snapshot, state) {
    if (!snapshot || typeof document === 'undefined') return;
    const v = model(snapshot, state.syncMode);
    const list = document.getElementById('activeTaskPreview');
    if (list) list.innerHTML = v.tasks.map(t => {
      const id = escape(t.id);
      const title = escape(t.title || t.id);
      const status = escape(t.status);
      const owner = escape(t.owner || 'Unclaimed');
      return '<button class="quick-task" type="button" data-task-id="' + id + '" aria-label="Inspect task ' + id + '">' +
        '<span class="status-light ' + status + '" aria-hidden="true"></span>' +
        '<span class="quick-task-copy"><strong>' + title + '</strong><small>' + id + ' · ' + owner + '</small></span>' +
        '<span class="task-state ' + status + '">' + (STATUS_LABELS[t.status] || status) + '</span></button>';
    }).join('') || '<p class="muted">No unfinished tasks in the queue.</p>';
    setText('activeTaskCount', v.openCount + ' OPEN');
    const bars = document.getElementById('workloadBars');
    if (bars) bars.innerHTML = STATUS_ORDER.map(status => {
      const count = v.counts[status] || 0;
      const width = v.total ? Math.min(100, 100 * count / v.total) : 0;
      return '<div class="workload-row"><span>' + STATUS_LABELS[status] + '</span>' +
        '<div class="workload-track"><div class="workload-fill ' + status + '" style="width:' + width + '%"></div></div>' +
        '<strong>' + count + '</strong></div>';
    }).join('');
    const facts = document.getElementById('healthFacts');
    if (facts) facts.innerHTML =
      '<div><span class="status-light ' + (state.syncMode === 'live' ? 'ok' : 'pending') + '"></span><span>GitHub source</span><strong>' + (state.syncMode === 'live' ? 'VERIFIED' : 'NOT LIVE') + '</strong></div>' +
      '<div><span class="status-light ' + (v.routingComplete ? 'ok' : 'blocked') + '"></span><span>Task routing</span><strong>' + escape(v.coverage) + '</strong></div>' +
      '<div><span class="status-light pending"></span><span>Mac execution</span><strong>NOT PROVEN</strong></div>';
    const evidences = [
      { label: 'SOURCE', value: state.syncMode === 'live' ? 'GitHub pinned SHA verified' : 'Historical / unverified snapshot', timestamp: state.lastSuccess ? new Date(state.lastSuccess).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) : '—' },
      { label: 'COMMIT', value: v.sha ? v.sha.slice(0, 12) : 'Not available', timestamp: 'SHA' },
      { label: 'OPEN PULL REQUESTS', value: v.prs == null ? 'Not available' : String(v.prs), timestamp: 'REPO' },
      { label: 'DATA GENERATED', value: v.sourceAt ? String(v.sourceAt).slice(0, 19).replace('T', ' ') : 'Unknown', timestamp: 'UTC*' }
    ];
    const feed = document.getElementById('recentEvidence');
    if (feed) feed.innerHTML = evidences.map((ev, i) =>
      '<div class="evidence-entry"><small>' + escape(ev.timestamp) + '</small><span class="evidence-dot' + (i === 0 && state.syncMode === 'live' ? ' verified' : '') + '"></span>' +
      '<div><strong>' + escape(ev.label) + '</strong><span>' + escape(ev.value) + '</span></div></div>').join('') +
      '<p class="source-caption">Snapshot timestamps and repository metadata; not a fabricated execution log.</p>';
    setText('coreTaskSummary', v.openCount + ' OPEN · ' + v.counts.active + ' CLAIMED');
    setText('coreCommit', v.sha ? 'SHA ' + v.sha.slice(0, 12) : 'Commit not verified');
    sync(state);
  }

  function sync(state) {
    if (typeof document === 'undefined') return;
    const mode = state?.syncMode || 'loading';
    setText('headerConnection', mode === 'live' ? 'GITHUB VERIFIED' : mode === 'snapshot' ? 'OFFLINE SNAPSHOT' : mode === 'error' ? 'SYNC FAILED' : 'VERIFYING SOURCE');
    setText('coreSyncMode', mode === 'live' ? 'GITHUB CONNECTED' : mode === 'snapshot' ? 'HISTORICAL SNAPSHOT' : mode === 'error' ? 'SYNC ERROR' : 'VERIFYING GITHUB');
    document.body.dataset.sourceMode = mode;
  }

  function clock() {
    if (typeof document === 'undefined') return;
    const now = new Date();
    setText('hudClock', now.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}));
    setText('hudDate', now.toLocaleDateString([], {month:'short',day:'numeric',year:'numeric'}).toUpperCase());
  }

  function openView(view, taskId) {
    const tab = document.getElementById('tab-button-' + view);
    if (!tab) return;
    tab.click();
    if (view === 'tasks' && taskId) {
      const search = document.getElementById('taskSearch');
      const statusFilter = document.getElementById('statusFilter');
      if (statusFilter) statusFilter.value = 'all';
      if (search) { search.value = taskId; search.dispatchEvent(new Event('input', {bubbles: true})); }
    }
    const main = document.querySelector('main');
    if (main) main.scrollIntoView({behavior: document.body.classList.contains('motion-paused') ? 'instant' : 'smooth', block:'start'});
  }

  if (typeof document !== 'undefined') {
    clock();
    setInterval(clock, 30000);
    document.addEventListener('click', event => {
      const target = event.target.closest('[data-open-view], [data-task-id]');
      if (!target) return;
      const view = target.dataset.openView || 'tasks';
      openView(view, target.dataset.taskId || '');
    });
  }
  root.RovorReferenceHud = { model, render, sync };
})(typeof globalThis !== 'undefined' ? globalThis : this);
