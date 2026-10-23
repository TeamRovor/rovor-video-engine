/* ROVOR Live Data v1: no credentials, no writes, pin queue & routes to ONE commit. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.RovorLiveData = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const REPO = 'TeamRovor/rovor-video-engine';
  const API = 'https://api.github.com/repos/' + REPO;
  const RAW = 'https://raw.githubusercontent.com/' + REPO;
  const SHA = /^[a-f0-9]{40}$/i;
  const STATUSES = ['ready', 'active', 'blocked', 'done'];
  const SYSTEMS = [
    { name: 'GitHub Control Plane', state: 'verified', summary: 'Versioned task queue, atomic intake, routing rules and hosted CI source checks' },
    { name: 'Video Engine', state: 'development', summary: 'Original Evan art, animation, audio planning and render quality workstreams' },
    { name: 'Business Operations', state: 'conditional', summary: 'Sales, offers, proof, client delivery and operational workflows' },
    { name: 'OmniRoute Gateway', state: 'development', summary: 'Model routing and guarded receipts; not native computer execution' },
    { name: 'Mac Native Executor', state: 'unverified', summary: 'No authenticated, operational private Mac executor established by GitHub source data' }
  ];
  const NOTES = [
    'Task owners are GitHub assignments, NOT presence indicators or online worker sessions.',
    'Hosted CI success does not prove Moho, Blender or Final Cut can be controlled on Amar\'s Mac.',
    'Updates are checked only while this dashboard is open; Whimsical is a separate manually maintained diagram.'
  ];

  function escapeHtml(value) {
    return String(value === undefined || value === null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  async function getJson(url, fetchImpl) {
    const response = await fetchImpl(url, { cache: 'no-store', headers: { 'Accept': 'application/vnd.github+json' } });
    if (!response || !response.ok) {
      const status = response ? response.status : 'network';
      if (status === 403 || status === 429) throw new Error('GitHub API limit or permission failure (HTTP ' + status + ')');
      throw new Error('GitHub request failed (HTTP ' + status + ')');
    }
    return response.json();
  }

  function safeTask(t) {
    if (!t || typeof t.id !== 'string' || !t.id || !STATUSES.includes(t.status)) throw new Error('Invalid task record');
    return {
      id: t.id, title: typeof t.title === 'string' ? t.title : t.id,
      status: t.status, priority: Number.isFinite(t.priority) ? t.priority : 999,
      owner: typeof t.owner === 'string' ? t.owner : null,
      depends_on: Array.isArray(t.depends_on) ? t.depends_on.filter(x => typeof x === 'string') : [],
      updated_at: typeof t.updated_at === 'string' ? t.updated_at : null,
      next_action: typeof t.next_action === 'string' ? t.next_action : ''
    };
  }

  function summarizeWorkers(tasks) {
    const owners = new Map();
    for (const task of tasks) {
      if ((task.status !== 'active' && task.status !== 'blocked') || !task.owner) continue;
      if (!owners.has(task.owner)) owners.set(task.owner, { name: task.owner, active: 0, blocked: 0, focus: [] });
      const entry = owners.get(task.owner);
      entry[task.status] += 1;
      entry.focus.push(task.id);
    }
    return [...owners.values()].sort((a, b) => (b.active - a.active) || a.name.localeCompare(b.name)).map(w => ({
      name: w.name, status: w.active ? 'claimed' : 'blocked',
      focus: w.focus, counts: { active: w.active, blocked: w.blocked }
    }));
  }

  function fileGroups(tree) {
    if (!tree || !Array.isArray(tree.tree) || tree.truncated === true) throw new Error('Incomplete GitHub tree');
    const groups = new Map();
    for (const file of tree.tree) {
      if (!file || file.type !== 'blob' || typeof file.path !== 'string') continue;
      const name = file.path.includes('/') ? file.path.split('/')[0] : '(root)';
      groups.set(name, (groups.get(name) || 0) + 1);
    }
    return [...groups].map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
  }

  function deriveSnapshot({ commit, queue, routes, tree, pulls, previous, now }) {
    if (!SHA.test(commit)) throw new Error('Invalid GitHub commit identity');
    if (!queue || !Array.isArray(queue.tasks) || !routes || !routes.tasks || typeof routes.tasks !== 'object' || Array.isArray(routes.tasks)) throw new Error('Invalid ROVOR queue or routing document');
    const tasks = queue.tasks.map(safeTask);
    const taskIds = tasks.map(t => t.id);
    const ids = new Set(taskIds);
    if (ids.size !== tasks.length) throw new Error('Duplicate GitHub task IDs');
    const ruleIds = Object.keys(routes.tasks);
    const missing = taskIds.filter(id => !(id in routes.tasks));
    const stale = ruleIds.filter(id => !ids.has(id));
    const status = Object.fromEntries(STATUSES.map(s => [s, tasks.filter(t => t.status === s).length]));
    const old = previous || {};
    let groups = old.file_groups || [], filesTotal = old.repo_snapshot?.files_total ?? null;
    let openPrs = old.repo_snapshot?.open_prs ?? null;
    if (tree !== undefined) { groups = fileGroups(tree); filesTotal = groups.reduce((n, group) => n + group.count, 0); }
    if (pulls !== undefined) {
      if (!Array.isArray(pulls)) throw new Error('Invalid GitHub PR collection');
      openPrs = pulls.length === 100 ? '100+' : pulls.length;
    }
    const workers = summarizeWorkers(tasks);
    return {
      generated_at: new Date(now).toISOString(), repo: REPO,
      repo_snapshot: {
        commit, tasks_total: tasks.length, tasks_status: status,
        routing_rules: ruleIds.length, routed_tasks: tasks.length - missing.length,
        routing_coverage: (tasks.length - missing.length) + '/' + tasks.length,
        files_total: filesTotal, open_prs: openPrs
      },
      route_health: { missing, stale, complete: !missing.length && !stale.length },
      open_tasks: tasks.filter(t => t.status !== 'done'), tasks,
      workers, systems: SYSTEMS, notes: NOTES, file_groups: groups,
      supplemental_at: (tree !== undefined && pulls !== undefined) ? new Date(now).toISOString() : (old.supplemental_at || null),
      source: 'github-pinned',
    };
  }

  async function fetchGitHubSnapshot({ fetchImpl, previous = null, includeExtras = true, now = Date.now() }) {
    if (typeof fetchImpl !== 'function') throw new Error('Missing network fetch implementation');
    const head = await getJson(API + '/commits/main', fetchImpl);
    const sha = head && head.sha;
    if (!SHA.test(sha)) throw new Error('Invalid GitHub HEAD response');
    const encodedSha = encodeURIComponent(sha);
    const [queue, routes] = await Promise.all([
      getJson(RAW + '/' + encodedSha + '/coordination/tasks.json', fetchImpl),
      getJson(RAW + '/' + encodedSha + '/coordination/work-routing.json', fetchImpl)
    ]);
    // Critical files must succeed together. Supplementary endpoints may fail
    // independently, but never quietly mark old PR counts or repo map as current.
    let tree, pulls;
    const warnings = [];
    if (includeExtras) {
      const extras = await Promise.allSettled([
        getJson(API + '/git/trees/' + encodedSha + '?recursive=1', fetchImpl),
        getJson(API + '/pulls?state=open&per_page=100', fetchImpl)
      ]);
      if (extras[0].status === 'fulfilled') {
        try { fileGroups(extras[0].value); tree = extras[0].value; }
        catch (_) { warnings.push('GitHub returned incomplete repository file map; showing last known map'); }
      } else warnings.push('Repository file map unavailable; showing last known map');
      if (extras[1].status === 'fulfilled') pulls = extras[1].value;
      else warnings.push('Pull request count unavailable; showing last known count');
    }
    const snapshot = deriveSnapshot({ commit: sha, queue, routes, tree, pulls, previous, now });
    if (!snapshot.route_health.complete) warnings.push('Queue/routing mismatch: ' + snapshot.route_health.missing.length + ' missing and ' + snapshot.route_health.stale.length + ' obsolete');
    if (!includeExtras && snapshot.supplemental_at) warnings.push('PR count and file map last checked separately');
    return { snapshot, warnings, commit: sha };
  }

  return { REPO, API, RAW, escapeHtml, summarizeWorkers, fileGroups, deriveSnapshot, fetchGitHubSnapshot };
});
