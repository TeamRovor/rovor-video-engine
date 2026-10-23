/* ROVOR Command Center v2 — open-page polling of LIVE, PUBLIC GitHub data. */
const Live = globalThis.RovorLiveData;
const REFRESH_MS = 180000;      // Main HEAD and pinned queue/route every 3 minutes.
const EXTRAS_MS = 900000;       // Tree + open PRs every 15 minutes (~28 API calls/hour).
const state = {
  raw: null, filteredTasks: [], syncMode: 'loading', warnings: [],
  lastSuccess: null, lastExtras: null, busy: false, timer: null,
};
const E = Live.escapeHtml;

function syncView() {
  const stateEl = document.getElementById('syncState');
  const details = document.getElementById('syncDetails');
  const when = document.getElementById('syncLast');
  stateEl.textContent = state.syncMode === 'live' ? 'LIVE GITHUB' : state.syncMode === 'snapshot' ? 'OFFLINE SNAPSHOT' : state.syncMode === 'error' ? 'SYNC FAILED' : 'CONNECTING';
  stateEl.className = 'sync-pill ' + state.syncMode;
  details.textContent = state.warnings.length ? state.warnings.join(' · ') :
    (state.syncMode === 'live' ? 'Pinned to one GitHub commit; automatic refresh every 3 minutes while open.' : 'Fetching public ROVOR data…');
  when.textContent = state.lastSuccess ? 'Last verified: ' + new Date(state.lastSuccess).toLocaleString() : 'Not yet verified';
  document.getElementById('refreshBtn').disabled = state.busy;
  document.getElementById('refreshBtn').textContent = state.busy ? 'Syncing…' : 'Refresh GitHub';
}

async function syncGitHub(forceExtras = false) {
  if (state.busy) return;
  state.busy = true;
  syncView();
  try {
    const now = Date.now();
    const includeExtras = forceExtras || !state.lastExtras || (now - state.lastExtras >= EXTRAS_MS);
    const result = await Live.fetchGitHubSnapshot({ fetchImpl: fetch, previous: state.raw, includeExtras, now });
    state.raw = result.snapshot;
    state.syncMode = 'live';
    state.warnings = result.warnings;
    state.lastSuccess = now;
    if (includeExtras) state.lastExtras = now; // Limit optional API calls even when an endpoint fails.
    renderAll();
  } catch (error) {
    // Never relabel cached/stale values as live after an API error.
    state.syncMode = state.raw ? 'snapshot' : 'error';
    state.warnings = ['GitHub sync failed: ' + (error && error.message ? error.message : 'unknown error')];
    if (state.raw) renderAll();
  } finally {
    state.busy = false;
    syncView();
  }
}

async function boot() {
  wireTabs();
  wireControls();
  syncView();
  // Fallback is visibly stale, never treated as live or silently refreshed.
  try {
    const response = await fetch('snapshot.json', {cache:'no-store'});
    if (response.ok) {
      const snapshot = await response.json();
      if (snapshot && snapshot.repo_snapshot) {
        state.raw = snapshot;
        state.syncMode = 'snapshot';
        state.warnings = ['Historical bundled snapshot; GitHub has not been verified yet'];
        renderAll();
        syncView();
      }
    }
  } catch (_) { /* file:// fallback may be inaccessible; live fetch still runs */ }
  await syncGitHub();
  state.timer = setInterval(() => { if (!document.hidden) syncGitHub(false); }, REFRESH_MS);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && (!state.lastSuccess || Date.now() - state.lastSuccess >= REFRESH_MS)) syncGitHub(false);
  });
}

function renderAll() {
  if (!state.raw) return;
  filterTasks(false);
  renderMeta(); renderMetrics(); renderStatusBars(); renderNotes();
  renderSystemNetwork(); renderOverviewColumns(); renderTasks();
  renderSystems(); renderRepoBars(); renderRepoMeta(); renderWorkers();
}

function renderMeta() {
  const {repo_snapshot: snap, repo} = state.raw;
  const rows = [['Repo', repo], ['Commit', snap.commit?.slice(0, 12) || 'unknown'],
    ['GitHub checked', state.raw.generated_at || 'unknown'], ['Coverage', snap.routing_coverage]];
  document.getElementById('snapshotMeta').innerHTML = rows.map(([k,v]) => `<div><strong>${E(k)}</strong>${E(v)}</div>`).join('');
  const pct = snap.tasks_total ? Math.max(0,Math.min(100,Math.round(100 * (snap.routed_tasks ?? snap.routing_rules) / snap.tasks_total))) : 0;
  document.getElementById('integrityPct').textContent = pct + '%';
  document.getElementById('integrityRing').style.strokeDashoffset = String(540 * (1 - pct / 100));
}

function renderMetrics() {
  const snap = state.raw.repo_snapshot;
  const data = [['Tasks',snap.tasks_total],['Files',snap.files_total],['Open PRs',snap.open_prs],['Routes',snap.routing_rules]];
  document.getElementById('metrics').innerHTML = data.map(([label,val]) =>
    `<div class="metric"><div class="label">${E(label)}</div><div class="value">${val === null || val === undefined ? '—' : E(val)}</div></div>`).join('');
}

function renderStatusBars() {
  const colors = {done:'#54f0c7',active:'#62f2ff',blocked:'#ff5c77',ready:'#ffd255'};
  const status = state.raw.repo_snapshot.tasks_status || {};
  const entries = Object.entries(status);
  const total = entries.reduce((a,[,v])=>a+v,0)||1;
  const max = Math.max(1,...entries.map(x=>x[1]));
  document.getElementById('statusBars').innerHTML = entries.map(([key,num]) => `
    <div class="status-bar-item"><div class="status-bar" style="height:${Math.max(18,num/max*92)}px;background:${colors[key] || '#62f2ff'}"></div><label>${E(key)}</label><span>${num} / ${Math.round(num/total*100)}%</span></div>`).join('');
}
function renderNotes() {
  document.getElementById('notesList').innerHTML = (state.raw.notes || []).map(n => `<li>${E(n)}</li>`).join('');
}
function renderSystemNetwork() {
  document.getElementById('systemNetwork').innerHTML = (state.raw.systems || []).map(s =>
    `<article class="system-card"><span class="pill ${normalizeState(s.state)}">${E(s.state)}</span><h3>${E(s.name)}</h3><p>${E(s.summary)}</p></article>`).join('');
}
function renderOverviewColumns() {
  const tasks = state.raw.open_tasks || [];
  document.getElementById('readyTasks').innerHTML = tasks.filter(t=>t.status==='ready').map(taskCard).join('') || '<div class="footer-hint">No ready tasks.</div>';
  document.getElementById('blockedTasks').innerHTML = tasks.filter(t=>t.status==='blocked').map(taskCard).join('') || '<div class="footer-hint">No blocked tasks.</div>';
}
function taskCard(t) {
  return `<div class="task-card"><div class="task-id">${E(t.id)}</div><div class="task-title">${E(t.title)}</div>
    <div class="task-meta">Status: <strong>${E(t.status)}</strong> · P${E(t.priority)}<div>Owner: ${E(t.owner || 'Unclaimed')}</div>
    <div>Dependencies: ${E((t.depends_on || []).join(', ') || 'none')}</div></div></div>`;
}
function renderTasks() {
  document.getElementById('taskTable').innerHTML = state.filteredTasks.map(t =>
    `<div class="table-row"><div class="cell"><div class="col-head">Task ID</div>${E(t.id)}</div>
    <div class="cell"><div class="col-head">Status</div><span class="pill ${normalizeState(t.status)}">${E(t.status)}</span></div>
    <div class="cell"><div class="col-head">Title</div>${E(t.title)}</div>
    <div class="cell"><div class="col-head">Owner</div>${E(t.owner || 'Unclaimed')}</div>
    <div class="cell"><div class="col-head">Dependencies</div>${E((t.depends_on || []).join(', ') || 'none')}</div></div>`).join('') || '<div class="footer-hint">No tasks match your filters.</div>';
}
function renderSystems() {
  document.getElementById('systemsGrid').innerHTML = (state.raw.systems || []).map(s =>
    `<div class="system-mini"><span class="pill ${normalizeState(s.state)}">${E(s.state)}</span><strong>${E(s.name)}</strong><div class="muted">${E(s.summary)}</div></div>`).join('');
}
function renderRepoBars() {
  const list = state.raw.file_groups || [];
  const max = Math.max(1,...list.map(g=>g.count));
  document.getElementById('repoBars').innerHTML = list.map(g=>
    `<div class="repo-bar-row"><div class="repo-bar-head"><span>${E(g.name)}</span><span>${E(g.count)}</span></div>
    <div class="repo-bar-track"><div class="repo-bar-fill" style="width:${Math.max(0,Math.min(100,100*g.count/max))}%"></div></div></div>`).join('') || '<div class="footer-hint">File map not available yet.</div>';
}
function renderRepoMeta() {
  const s = state.raw.repo_snapshot;
  document.getElementById('repoName').textContent = state.raw.repo;
  document.getElementById('commitSha').textContent = (s.commit || 'unknown').slice(0,16);
  document.getElementById('routeCoverage').textContent = s.routing_coverage || '—';
  document.getElementById('prCount').textContent = s.open_prs ?? '—';
  document.getElementById('repoDataHelp').textContent = 'Tasks and routes refresh from one pinned GitHub commit. PR and file-map counts refresh every 15 minutes. No API key stored in your browser.';
}
function renderWorkers() {
  document.getElementById('workersGrid').innerHTML = (state.raw.workers || []).map(w =>
    `<div class="worker-card"><span class="pill ${normalizeState(w.status)}">${E(w.status)}</span><h3>${E(w.name)}</h3>
    <div class="muted">Claimed task ownership only — not a signal this worker is online.</div>
    <ul>${(w.focus || []).map(item=>`<li>${E(item)}</li>`).join('')}</ul></div>`).join('') || '<div class="footer-hint">No assigned workers in this snapshot.</div>';
}
function normalizeState(stateName) {
  const s = String(stateName).toLowerCase();
  if (['verified','healthy','done','ok'].includes(s)) return 'verified';
  if (['blocked','unverified','danger'].includes(s)) return 'blocked';
  return 'development';
}
function wireTabs() {
  document.querySelectorAll('.tab').forEach(button => button.addEventListener('click',()=>{
    document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
    document.querySelectorAll('.tab-view').forEach(view=>view.classList.remove('active'));
    button.classList.add('active');
    document.getElementById('tab-'+button.dataset.tab).classList.add('active');
  }));
}
function filterTasks(render=true) {
  const text=(document.getElementById('taskSearch')?.value || '').trim().toLowerCase();
  const status=document.getElementById('statusFilter')?.value || 'all';
  const tasks=state.raw?.tasks || state.raw?.open_tasks || [];
  state.filteredTasks=tasks.filter(t => (status==='all'||t.status===status) &&
    (!text || [t.id,t.title,t.owner||''].join(' ').toLowerCase().includes(text)));
  if(render) renderTasks();
}
function wireControls() {
  document.getElementById('taskSearch').addEventListener('input',()=>filterTasks());
  document.getElementById('statusFilter').addEventListener('change',()=>filterTasks());
  document.getElementById('refreshBtn').addEventListener('click',()=>syncGitHub(false));
  document.getElementById('exportBtn').addEventListener('click',()=>{
    if (!state.raw) return;
    const blob = new Blob([JSON.stringify({sync_mode:state.syncMode,exported_at:new Date().toISOString(),snapshot:state.raw},null,2)],{type:'application/json'});
    const anchor=document.createElement('a');
    const uri=URL.createObjectURL(blob);
    anchor.href=uri;anchor.download='rovor-github-hud-'+new Date().toISOString().slice(0,10)+'.json';anchor.click();
    setTimeout(()=>URL.revokeObjectURL(uri),1000);
  });
}

boot();
