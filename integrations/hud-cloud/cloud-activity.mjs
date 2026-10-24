const ROLES = new Set(['Walter', 'Mike', 'Jane', 'Jesse', 'Gale', 'Gus', 'Saul', 'Hank']);
const FIELDS = new Set(['schema_version', 'id', 'employee', 'execution_source', 'task_id', 'summary', 'started_at', 'completed_at', 'observed_at', 'artifact_url', 'commit_sha', 'checks_url', 'human_review', 'model', 'tokens']);
const bad = () => { throw Error('Invalid cloud receipt'); };
const text = (s, max) => typeof s === 'string' && s.length > 0 && s.length <= max && !/[\u0000-\u001f]/.test(s) ? s : bad();

export function validateCloudReceipt(r, now = Date.now()) {
  if (!r || typeof r !== 'object' || Array.isArray(r) || Object.keys(r).some(k => !FIELDS.has(k))) bad();
  if (r.schema_version !== 1 || !ROLES.has(r.employee) || r.execution_source !== 'chatgpt_cloud') bad();
  for (const key of ['id', 'task_id']) if (!/^[a-z0-9][a-z0-9-]{0,149}$/.test(r[key] || '')) bad();
  text(r.summary, 400);
  const times = ['started_at', 'completed_at', 'observed_at'].map(k => {
    if (typeof r[k] !== 'string' || !/^\d{4}-\d\d-\d\dT.*Z$/.test(r[k])) bad();
    const value = Date.parse(r[k]); if (!Number.isFinite(value)) bad(); return value;
  });
  if (times[0] > times[1] || times[1] > times[2] || times[2] > now + 300000) bad();
  if (!/^https:\/\/github\.com\/TeamRovor\/rovor-video-engine\/pull\/[1-9]\d*$/.test(r.artifact_url || '')) bad();
  if (!/^https:\/\/github\.com\/TeamRovor\/rovor-video-engine\/actions\/runs\/[1-9]\d*$/.test(r.checks_url || '')) bad();
  if (!/^[a-f0-9]{40}$/.test(r.commit_sha || '')) bad();
  // Cloud ChatGPT runs do not provide an upstream model/token receipt here.
  if (r.human_review !== 'not_recorded' || r.model !== null || r.tokens !== null) bad();
  return {...r};
}

export function validateCloudFeed(doc, now = Date.now()) {
  if (doc?.schema_version !== 1 || doc.source !== 'recorded_cloud_shifts' || !Array.isArray(doc.receipts) || doc.receipts.length > 200) bad();
  const generated = Date.parse(doc.generated_at);
  if (!Number.isFinite(generated) || generated > now + 300000) bad();
  const receipts = doc.receipts.map(r => validateCloudReceipt(r, now));
  if (new Set(receipts.map(r => r.id)).size !== receipts.length) bad();
  return {schema_version: 1, source: doc.source, generated_at: doc.generated_at,
    receipts: receipts.sort((a, b) => Date.parse(b.completed_at) - Date.parse(a.completed_at))};
}

export function describeCloudShift(receipt) {
  return `${receipt.employee} · CLOUD · COMPLETED · Human review not recorded`;
}

function startCloudActivity() {
  const panel = document.getElementById('activityPanel'), drawer = document.getElementById('drawerBody');
  if (!panel || !drawer) return;
  let feed = null, connected = false, busy = false, timer;
  const element = (tag, content, className) => {
    const e = document.createElement(tag); if (content) e.textContent = content;
    if (className) e.className = className; return e;
  };
  function section(id, detailed) {
    const root = element('section', '', detailed ? 'card' : ''); root.id = id;
    root.append(element(detailed ? 'h3' : 'div', connected ? 'RECORDED CLOUD WORK' : 'CLOUD FEED UNAVAILABLE', 'tiny-label'));
    if (!feed?.receipts.length) root.append(element('div', 'No recorded cloud result available.', 'tiny-label'));
    for (const r of (feed?.receipts || []).slice(0, detailed ? 20 : 5)) {
      const row = element(detailed ? 'article' : 'button', '', detailed ? 'card' : 'log-entry');
      if (!detailed) {
        row.type = 'button'; row.style.cssText = 'background:transparent;border:0;width:100%;text-align:left;cursor:pointer;color:inherit';
        row.addEventListener('click', () => { window.ROVOR_NATIVE?.open('activity', panel.closest('.panel')); paint(); });
      }
      row.append(element('time', new Date(r.completed_at).toLocaleString([], {month: 'numeric', day: 'numeric', hour: 'numeric', minute: '2-digit'})));
      row.append(element('span', ' ' + describeCloudShift(r)));
      if (detailed) {
        row.append(element('p', r.summary));
        row.append(element('p', 'Recorded completion, not current online activity. Upstream model and tokens unavailable.'));
        for (const [label, href] of [['View result', r.artifact_url], ['View checks', r.checks_url]]) {
          const link = element('a', label + ' ↗ '); link.href = href; link.target = '_blank'; link.rel = 'noopener noreferrer'; row.append(link);
        }
      }
      root.append(row);
    }
    if (!connected && feed) root.append(element('p', 'Showing previously fetched historical records.', 'tiny-label'));
    return root;
  }
  function paint() {
    const key = JSON.stringify([connected, feed]);
    const compact = document.getElementById('rovor-cloud-activity');
    if (!compact || compact.dataset.cloudKey !== key) {
      const scroll = panel.scrollTop, next = section('rovor-cloud-activity', false); next.dataset.cloudKey = key;
      compact?.remove(); panel.prepend(next); panel.scrollTop = scroll;
    }
    if (window.ROVOR_NATIVE?.state?.view === 'activity') {
      const detail = document.getElementById('rovor-cloud-activity-details');
      if (!detail || detail.dataset.cloudKey !== key) {
        const next = section('rovor-cloud-activity-details', true); next.dataset.cloudKey = key;
        detail?.remove(); drawer.prepend(next);
      }
    }
  }
  async function poll() {
    if (busy || document.hidden) return;
    busy = true;
    try {
      const response = await fetch(new URL('./cloud-activity.json', import.meta.url), {cache: 'no-store', credentials: 'omit', signal: AbortSignal.timeout(8000)});
      if (!response.ok) throw Error();
      const body = await response.text(); if (body.length > 524288) throw Error();
      feed = validateCloudFeed(JSON.parse(body)); connected = true;
    } catch { connected = false; }
    finally { busy = false; paint(); clearTimeout(timer); timer = setTimeout(poll, 60000); }
  }
  // Reattach after the original HUD refreshes its existing panel/drawer contents.
  const observer = new MutationObserver(paint);
  observer.observe(panel, {childList: true}); observer.observe(drawer, {childList: true});
  document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); });
  poll();
}

if (typeof document !== 'undefined') startCloudActivity();
