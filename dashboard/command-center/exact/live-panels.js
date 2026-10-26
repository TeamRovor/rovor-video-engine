/* ROVOR exact-reference HUD — optional LIVE data overlays.
   Read-only. Uses the already-verified, SHA-pinned state in exact/app.js.
   No extra API traffic, credentials, or worker execution. */
(() => {
  'use strict';
  const root = window.ROVOR_HUD;
  const layer = document.getElementById('livePanels');
  const toggle = document.getElementById('liveDataButton');
  if (!root || !layer || !toggle) return;

  let enabled = false;
  const $ = (id) => document.getElementById(id);
  const stamp = (date) => {
    const t = Date.parse(date || '');
    return Number.isFinite(t) ? new Date(t).toLocaleString() : 'Not recorded';
  };
  const short = (s, n = 36) => String(s || '').slice(0, n);
  const el = (tag, className, content) => {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (content !== undefined) item.textContent = String(content);
    return item;
  };
  function action(text, view, itemId) {
    const btn = el('button', 'telemetry-action', text);
    btn.type = 'button';
    btn.addEventListener('click', () => {
      if (itemId) {
        root.openView('tasks');
        // Existing inspector controls the source-grounded task detail.
        requestAnimationFrame(() => {
          const row = [...document.querySelectorAll('#taskResults [data-task]')]
            .find((node) => node.dataset.task === itemId);
          if (row) row.click();
          else {
            const input = $('taskSearch');
            if (input) {
              input.value = itemId;
              input.dispatchEvent(new Event('input', { bubbles: true }));
              requestAnimationFrame(() => {
                document.querySelector('#taskResults [data-task]')?.click();
              });
            }
          }
        });
      } else root.openView(view);
    });
    return btn;
  }
  function createPanel(id, title, area) {
    const panel = el('section', 'telemetry-panel telemetry-' + area);
    panel.setAttribute('aria-label', title + ' (verified GitHub data)');
    const heading = el('div', 'telemetry-heading', title);
    const body = el('div', 'telemetry-body');
    body.id = id;
    panel.append(heading, body);
    layer.append(panel);
    return body;
  }
  const tasksBody = createPanel('telemetryTasks', 'ACTIVE TASKS', 'tasks');
  const resourcesBody = createPanel('telemetryResources', 'QUEUE DISTRIBUTION', 'resources');
  const activityBody = createPanel('telemetryActivity', 'REPOSITORY ACTIVITY', 'activity');
  const healthBody = createPanel('telemetryHealth', 'SYSTEM VERIFICATION', 'health');
  const quotaBody = createPanel('telemetryQuota', 'API QUOTA / GITHUB', 'quota');
  const mediaBody = createPanel('telemetryMedia', 'SOURCE FEED', 'media');

  function line(parent, name, value, css = '') {
    const row = el('div', 'telemetry-line ' + css);
    row.append(el('span', '', name), el('strong', '', value));
    parent.append(row);
    return row;
  }
  function bar(parent, name, val, total) {
    const row = el('div', 'telemetry-bar-row');
    const count = el('strong', '', val);
    const label = el('span', '', name);
    const track = el('div', 'telemetry-track');
    const fill = el('i', 'telemetry-fill');
    fill.style.width = total ? (100 * val / total).toFixed(1) + '%' : '0%';
    track.append(fill);
    row.append(label, track, count);
    parent.append(row);
  }
  function clear(...nodes) { nodes.forEach((n) => n.replaceChildren()); }
  function unverifiable() {
    for (const node of [tasksBody, resourcesBody, activityBody, healthBody, quotaBody, mediaBody]) {
      clear(node);
      node.append(el('p', 'telemetry-note', 'NO VERIFIED LIVE DATA'));
      node.append(el('p', 'telemetry-help', 'GitHub connection required. The original image is an illustrative design reference.'));
    }
  }
  function update() {
    if (!enabled) return;
    const s = root.state;
    const verified = s.mode === 'verified' && /^[a-f\d]{40}$/i.test(s.sha || '');
    layer.dataset.status = verified ? 'verified' : 'unverified';
    toggle.dataset.status = verified ? 'verified' : 'unverified';
    if (!verified) return unverifiable();

    const list = s.tasks.filter((task) => task.status !== 'done')
      .sort((a, b) => a.priority - b.priority || String(a.title).localeCompare(String(b.title)));
    const counts = { active: 0, ready: 0, blocked: 0, done: 0 };
    s.tasks.forEach((t) => { if (t.status in counts) counts[t.status]++; });
    clear(tasksBody, resourcesBody, activityBody, healthBody, quotaBody, mediaBody);
    const taskCount = el('div', 'telemetry-count', String(list.length) + ' OPEN');
    tasksBody.append(taskCount);
    list.slice(0, 5).forEach(t => {
      const btn = action(short(t.title, 40), 'tasks', t.id);
      btn.append(el('small', '', t.status === 'active' ? 'CLAIMED' : t.status.toUpperCase()));
      tasksBody.append(btn);
    });
    resourcesBody.append(el('p', 'telemetry-help', 'Real task statuses · not Mac hardware usage'));
    ['active', 'ready', 'blocked', 'done'].forEach(k => bar(resourcesBody, k.toUpperCase(), counts[k], s.tasks.length));
    const recent = s.tasks.filter(t => t.updated_at)
      .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at));
    recent.slice(0, 5).forEach(t => {
      const row = action(short(t.title, 42), 'tasks', t.id);
      row.append(el('small', '', stamp(t.updated_at)));
      activityBody.append(row);
    });
    line(healthBody, 'GitHub data', 'VERIFIED', 'telemetry-good');
    line(healthBody, 'Routing entries', s.tasks.length - (s.missing?.length || 0) + ' / ' + s.tasks.length);
    line(healthBody, 'Stale rules', String(s.stale?.length || 0));
    line(healthBody, 'Mac executor', 'NOT VERIFIED', 'telemetry-pending');
    line(healthBody, 'Render pipeline', 'NOT MONITORED', 'telemetry-pending');
    const left = Number.isFinite(s.rateLimit) ? String(s.rateLimit) : 'NOT AVAILABLE';
    line(quotaBody, 'GitHub API left', left);
    line(quotaBody, 'Reset', s.rateReset ? new Date(s.rateReset).toLocaleTimeString() : 'NOT AVAILABLE');
    quotaBody.append(el('p', 'telemetry-help', 'OmniRoute / provider quotas are not connected.'));
    line(mediaBody, 'GitHub source', short(s.sha, 12));
    line(mediaBody, 'Verified', new Date(s.lastVerified).toLocaleTimeString());
    line(mediaBody, 'Camera feed', 'NOT CONNECTED');
    mediaBody.append(action('OPEN SOURCE DETAILS ↗', 'github'));
  }
  function setEnabled(next) {
    enabled = !!next;
    layer.hidden = !enabled;
    toggle.setAttribute('aria-pressed', String(enabled));
    toggle.textContent = enabled ? 'LIVE PANELS: ON' : 'LIVE PANELS: OFF';
    document.body.classList.toggle('live-panels-visible', enabled);
    if (enabled) update();
  }
  toggle.addEventListener('click', () => setEnabled(!enabled));
  document.addEventListener('keydown', (e) => {
    if (e.key.toLowerCase() !== 'l' || e.metaKey || e.ctrlKey || e.altKey ||
      e.target?.closest?.('input,textarea,select,[contenteditable]') ||
      !$('overlay').hidden) return;
    e.preventDefault();
    setEnabled(!enabled);
  });
  document.addEventListener('rovor:source', update);
  setEnabled(false);
  window.ROVOR_LIVE_PANELS = { setEnabled, update, get enabled() { return enabled; } };
})();
