/* ROVOR team contribution attribution. Branch ownership is a convention, not authenticated identity. */
(() => {
  'use strict';
  const repo = 'TeamRovor/rovor-video-engine';
  const api = 'https://api.github.com/repos/' + repo;
  const members = [
    { id: 'amar', name: 'Amar', branch: 'amar-work', scope: 'HUD / OmniRoute oversight', issue: 208 },
    { id: 'bakir', name: 'Bakir', branch: 'bakir-work', scope: 'Video pipeline + shared Windows PR #7 sync', issue: 210 },
    { id: 'evan', name: 'Evan', branch: 'evan-work', scope: 'Moho / animation engine quality', issue: 211 }
  ];
  const activity = document.getElementById('activityPanel');
  if (!activity || !window.ROVOR_NATIVE) return;
  const records = Object.fromEntries(members.map(m => [m.id, { state: 'loading', ahead: null, behind: null, latest: null, files: [], pr: null, prsAvailable: false }]));
  let lastChecked = null, refreshError = '';
  const css = document.createElement('style');
  css.textContent = `
    .rovor-team-mini {border:1px solid #366391;background:#041329bb;padding:7px 8px;margin:6px 0 9px;color:#bcdeff;font-size:10px;flex-shrink:0}
    .rovor-team-mini strong{display:block;font-size:10px;letter-spacing:.12em;color:#a4dcff;margin-bottom:4px}
    .rovor-team-mini button{display:block;width:100%;text-align:left;color:#c8eaff;padding:5px 0;border:0;border-bottom:1px solid #36516a44;background:none;font-size:10px}
    .rovor-team-mini button:last-child{border-bottom:0}
    .rovor-team-open{border:1px solid #528dc2;color:#b9e8ff;background:#071a30;margin-left:auto;margin-right:7px;padding:4px 8px;font-size:9px;letter-spacing:.08em}
    .rovor-team-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr));gap:12px}
    .rovor-team-person{border:1px solid #2f608d;background:linear-gradient(135deg,#061a30,#030b19);padding:14px;min-width:0}
    .rovor-team-person h4{margin:0 0 8px;font-size:15px;color:#d3edff}
    .rovor-team-person .meta{color:#94c4e6;font-size:11px;line-height:1.7;overflow-wrap:anywhere}
    .rovor-team-person a,.rovor-team-shared a{color:#89d8ff;text-decoration:underline;text-underline-offset:3px}
    .rovor-team-person .state{display:block;margin-bottom:5px;color:#c1eaff;font-size:12px}
    .rovor-team-shared{padding:12px;margin-top:12px;border:1px solid #2f608d;color:#c2def1;font-size:12px;line-height:1.6;background:#061426}
    .rovor-team-caveat{font-size:11px;color:#91b9d7;line-height:1.6;margin:10px 0}
    @media(max-width:600px){.rovor-team-grid{grid-template-columns:1fr}.rovor-team-mini{margin:4px 0}.rovor-team-person{padding:11px}}
  `;
  document.head.append(css);
  const txt = (tag, className, content) => {
    const e = document.createElement(tag);
    if (className) e.className = className;
    e.textContent = content;
    return e;
  };
  const link = (text, href) => {
    const a = txt('a', '', text);
    a.href = href;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    return a;
  };
  const when = str => str && Number.isFinite(Date.parse(str)) ? new Date(str).toLocaleString() : 'Unknown';
  const status = rec => rec.state === 'loaded'
    ? (rec.ahead === 0 ? 'No unmerged commits' : rec.ahead + ' unmerged branch commit(s)') + (rec.behind > 0 ? ' · ' + rec.behind + ' behind main' : '')
    : 'GitHub status unavailable';
  function ensurePreview() {
    if (!activity.isConnected) return;
    let node = document.getElementById('rovorTeamMini');
    if (!node) {
      node = document.createElement('section');
      node.id = 'rovorTeamMini';
      node.className = 'rovor-team-mini';
      node.append(txt('strong', '', 'TEAM / GITHUB CONTRIBUTIONS'));
      for (const m of members) {
        const b = txt('button', '', m.name + ' · checking branch');
        b.type = 'button';
        b.dataset.team = m.id;
        node.append(b);
      }
      activity.prepend(node);
    }
    for (const m of members) {
      const rec = records[m.id];
      const b = node.querySelector('[data-team="' + m.id + '"]');
      if (b) b.textContent = m.name + ' · ' + status(rec);
    }
  }
  function renderDrawer() {
    const screen = document.getElementById('screen');
    const container = document.getElementById('drawerBody');
    if (!screen || screen.hidden || !container || document.getElementById('drawerTitle')?.textContent !== 'RECENT ACTIVITY') return;
    let section = document.getElementById('rovorTeamSection');
    if (!section) {
      section = document.createElement('section');
      section.id = 'rovorTeamSection';
      section.className = 'card';
      container.prepend(section);
    }
    section.replaceChildren();
    section.append(txt('h3', '', 'TEAM CONTRIBUTION TRACKING'));
    section.append(txt('p', 'rovor-team-caveat', 'GitHub activity grouped by agreed work branches. The shared TeamRovor login cannot prove which person authored a commit or connected their ChatGPT. Last checked: ' + (lastChecked ? when(lastChecked) : 'Not yet verified') + (refreshError ? ' · ' + refreshError : '') + '.'));
    const grid = txt('div', 'rovor-team-grid', '');
    for (const m of members) {
      const rec = records[m.id];
      const card = txt('article', 'rovor-team-person', '');
      card.append(txt('h4', '', m.name));
      card.append(txt('span', 'state', status(rec)));
      card.append(txt('div', 'meta', 'Responsibility: ' + m.scope));
      const assignment = txt('div', 'meta', 'Assigned work: ');
      assignment.append(link('ISSUE #' + m.issue, 'https://github.com/' + repo + '/issues/' + m.issue));
      card.append(assignment);
      const branchLine = txt('div', 'meta', 'Branch: ');
      branchLine.append(link(m.branch, 'https://github.com/' + repo + '/tree/' + encodeURIComponent(m.branch)));
      card.append(branchLine);
      const editorLine = txt('div', 'meta', 'Publish changes: ');
      editorLine.append(link('OPEN BRANCH EDITOR', 'https://github.dev/' + repo + '/tree/' + encodeURIComponent(m.branch)));
      card.append(editorLine);
      if (m.id === 'bakir') {
        const helpLine = txt('div', 'meta', 'No ChatGPT publish button? ');
        helpLine.append(link('FOLLOW BAKIR PUBLISH GUIDE', 'https://github.com/' + repo + '/blob/main/BAKIR-PUBLISH.md'));
        card.append(helpLine);
      }
      if (rec.state === 'loaded' && rec.latest) {
        const line = txt('div', 'meta', 'Latest unmerged commit: ');
        line.append(link(rec.latest.sha.slice(0, 7) + ' · ' + rec.latest.message, 'https://github.com/' + repo + '/commit/' + rec.latest.sha));
        card.append(line);
        card.append(txt('div', 'meta', 'Commit timestamp: ' + when(rec.latest.date)));
        card.append(txt('div', 'meta', 'Files changed (compare range): ' + (rec.files.length ? rec.files.join(', ') : 'No filenames reported')));
      }
      const prLine = txt('div', 'meta', rec.pr ? 'Latest attributed branch PR: ' : rec.prsAvailable ? 'Branch PR: no match in recent 100 PRs' : 'Branch PR: unavailable');
      if (rec.pr) prLine.append(link('#' + rec.pr.number + ' · ' + rec.pr.title, rec.pr.url));
      card.append(prLine);
      grid.append(card);
    }
    section.append(grid);
    const shared = txt('div', 'rovor-team-shared', 'SHARED WINDOWS PR RESPONSIBILITY · Keona + Bakir — ');
    shared.append(link('Windows reliability PR #7', 'https://github.com/' + repo + '/pull/7'));
    shared.append(txt('div', '', 'Keona retains Windows-local runtime validation; Bakir shares future PR synchronization, cross-platform CI follow-up and conflict triage. This assignment is not proof Bakir has pushed code.'));
    section.append(shared);
  }
  const header = activity.closest('.panel')?.querySelector('.panel-header');
  if (header && !document.getElementById('rovorTeamOpen')) {
    const btn = txt('button', 'rovor-team-open', 'TEAM');
    btn.type = 'button';
    btn.id = 'rovorTeamOpen';
    btn.title = 'See branch-attributed GitHub activity';
    header.insertBefore(btn, header.querySelector('.panel-expand'));
    btn.addEventListener('click', () => { window.ROVOR_NATIVE.open('activity', activity.closest('.panel')); renderDrawer(); });
  }
  activity.addEventListener('click', event => {
    if (event.target.closest('[data-team]')) {
      window.ROVOR_NATIVE.open('activity', activity.closest('.panel'));
      renderDrawer();
    }
  });
  const onChange = new MutationObserver(() => ensurePreview());
  onChange.observe(activity, { childList: true });
  const drawer = document.getElementById('drawerBody');
  if (drawer) new MutationObserver(() => {
    if (!document.getElementById('rovorTeamSection')) renderDrawer();
  }).observe(drawer, { childList: true });
  async function json(path) {
    const response = await fetch(api + path, {
      headers: { Accept: 'application/vnd.github+json' },
      cache: 'no-store',
      signal: AbortSignal.timeout(12000)
    });
    if (!response.ok) throw Error('HTTP ' + response.status);
    return response.json();
  }
  async function refresh() {
    if (document.hidden) return;
    const results = await Promise.allSettled([
      ...members.map(m => json('/compare/main...' + m.branch)),
      json('/pulls?state=all&per_page=100&sort=updated&direction=desc')
    ]);
    const prs = results[3].status === 'fulfilled' && Array.isArray(results[3].value) ? results[3].value : [];
    for (const [i, m] of members.entries()) {
      const result = results[i], rec = records[m.id];
      rec.state = result.status === 'fulfilled' && Number.isInteger(result.value?.ahead_by) ? 'loaded' : 'unavailable';
      rec.ahead = rec.state === 'loaded' ? result.value.ahead_by : null;
      rec.behind = rec.state === 'loaded' ? result.value.behind_by : null;
      rec.prsAvailable = results[3].status === 'fulfilled';
      const commits = rec.state === 'loaded' && Array.isArray(result.value.commits) ? result.value.commits : [];
      const newest = rec.ahead > 0 ? commits.at(-1) : null;
      rec.latest = newest && /^[a-f0-9]{40}$/i.test(newest.sha || '') ? {
        sha: newest.sha, message: String(newest.commit?.message || '').split('\n')[0].slice(0, 100),
        date: newest.commit?.committer?.date || null
      } : null;
      rec.files = rec.ahead > 0 && Array.isArray(result.value.files)
        ? result.value.files.slice(0, 4).map(f => String(f.filename || '')).filter(Boolean) : [];
      const pr = prs.find(p => p.head?.ref === m.branch && p.head?.repo?.full_name === repo);
      rec.pr = pr && Number.isInteger(pr.number) && typeof pr.html_url === 'string'
        ? { number: pr.number, title: String(pr.title || '').slice(0, 90), url: pr.html_url } : null;
    }
    lastChecked = new Date().toISOString();
    refreshError = results.every(x => x.status === 'rejected') ? 'GitHub temporarily unavailable' : (results[3].status === 'rejected' ? 'PR data unavailable' : '');
    ensurePreview(); renderDrawer();
  }
  ensurePreview();
  refresh();
  setInterval(refresh, 15 * 60 * 1000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden && (!lastChecked || Date.now() - Date.parse(lastChecked) > 15 * 60 * 1000)) refresh(); });
})();
