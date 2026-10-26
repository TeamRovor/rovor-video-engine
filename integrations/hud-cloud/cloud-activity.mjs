import {reviewLink, latestOwnerReviews} from './cloud-reviews.mjs';
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

export function describeCloudShift(receipt, review) {
  return `${receipt.employee} · CLOUD · COMPLETED · ${review ? review.decision.toUpperCase() + ' saved by owner' : 'Human review not recorded'}`;
}

function startCloudActivity() {
  const panel = document.getElementById('activityPanel'), drawer = document.getElementById('drawerBody');
  if (!panel || !drawer) return;
  let feed = null, connected = false, reviews = [], busy = false, timer, checkedAt = null;
  const element = (tag, content, className) => {
    const e = document.createElement(tag); if (content) e.textContent = content;
    if (className) e.className = className; return e;
  };
  function section(id, detailed) {
    const root = element('section', '', detailed ? 'card' : ''); root.id = id;
    root.append(element(detailed ? 'h3' : 'div', connected ? 'RECORDED CLOUD WORK' : 'CLOUD FEED UNAVAILABLE', 'tiny-label'));
    if (checkedAt) root.append(element('div', 'Feed checked ' + new Date(checkedAt).toLocaleTimeString() + ' · Last published ' + new Date(feed.generated_at).toLocaleString() + ' · Current task execution unknown', 'tiny-label'));
    if (!feed?.receipts.length) root.append(element('div', 'No recorded cloud result available.', 'tiny-label'));
    for (const r of (feed?.receipts || []).slice(0, detailed ? 20 : 5)) {
      const row = element(detailed ? 'article' : 'button', '', detailed ? 'card' : 'log-entry');
      if (!detailed) {
        row.type = 'button'; row.style.cssText = 'background:transparent;border:0;width:100%;text-align:left;cursor:pointer;color:inherit';
        row.addEventListener('click', () => { window.ROVOR_NATIVE?.open('activity', panel.closest('.panel')); paint(); });
      }
      row.append(element('time', new Date(r.completed_at).toLocaleString([], {month: 'numeric', day: 'numeric', hour: 'numeric', minute: '2-digit'})));
      const review = connected ? reviews.find(x => x.receipt_id === r.id && x.commit_sha === r.commit_sha) : null;
      row.append(element('span', ' ' + describeCloudShift(r, review)));
      if (detailed) {
        row.append(element('p', r.summary));
        row.append(element('p', 'Recorded completion, not current online activity. Upstream model and tokens unavailable.'));
        for (const [label, href] of [['View result', r.artifact_url], ['View checks', r.checks_url]]) {
          const link = element('a', label + ' ↗ '); link.href = href; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.style.color = '#8fd0ff'; row.append(link);
        }
        if (review) row.append(element('p', 'Owner decision: ' + review.decision.toUpperCase() + (review.reason ? ' · ' + review.reason : '')));
        const controls = element('div'); controls.style.cssText = 'display:flex;gap:8px';
        for (const decision of ['pass', 'fail']) {
          const button = element('a', decision.toUpperCase(), 'drawer-button');
          button.href = reviewLink(r, decision); button.target = '_blank'; button.rel = 'noopener noreferrer';
          button.style.cssText = 'text-align:center;color:#c9eaff;text-decoration:none'; controls.append(button);
        }
        row.append(controls);
        row.append(element('p', 'Submit the GitHub confirmation signed in as TeamRovor to save your public review. A new review changes the decision. Reviewing does not run or deploy the output.'));
      }
      root.append(row);
    }
    if (!connected && feed) root.append(element('p', 'Showing previously fetched historical records.', 'tiny-label'));
    return root;
  }
  function paint() {
    const key = JSON.stringify([connected, feed, reviews, checkedAt]);
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
    const workload = document.getElementById('workloadPanel'), meta = workload?.querySelector('.wl-compact-meta');
    const liveMac = meta && /^CONNECTED\b/.test(meta.textContent.trim());
    if (meta && !liveMac) {
      const last = feed?.receipts[0];
      const status = 'MAC DISCONNECTED · ' + (last ? 'CLOUD ' + new Date(last.completed_at).toLocaleTimeString([], {hour:'numeric',minute:'2-digit'}) : 'NO CLOUD RECORD');
      if (meta.textContent !== status) meta.textContent = status;
      meta.title = 'The built-in Mac observation is archived. Current OmniRoute model activity is unknown. Cloud time is the latest recorded completion.';
    }
    if (window.ROVOR_NATIVE?.state?.view === 'workload' && !liveMac) {
      const old = document.getElementById('rovor-cloud-workload-notice');
      if (!old || old.dataset.cloudKey !== key) {
        const notice = element('div', 'LIVE MAC TELEMETRY IS DISCONNECTED. The original Mac report below is archived. Open Recent Activity for the newest recorded cloud completions and PASS / FAIL controls.', 'card');
        notice.id = 'rovor-cloud-workload-notice'; notice.dataset.cloudKey = key; old?.remove(); drawer.prepend(notice);
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
      feed = validateCloudFeed(JSON.parse(body));
      const reviewResponse = await fetch(new URL('./cloud-reviews.json', import.meta.url), {cache:'no-store', credentials:'omit', signal:AbortSignal.timeout(8000)});
      if (!reviewResponse.ok) throw Error();
      const reviewBody = await reviewResponse.text(); if (reviewBody.length > 524288) throw Error();
      const reviewDoc = JSON.parse(reviewBody);
      if (reviewDoc.schema_version !== 1 || reviewDoc.source !== 'github_owner_review_ledger') throw Error();
      reviews = latestOwnerReviews(reviewDoc.reviews, feed.receipts); connected = true; checkedAt = Date.now();
    } catch { connected = false; }
    finally { busy = false; paint(); clearTimeout(timer); timer = setTimeout(poll, 60000); }
  }
  // Reattach after the original HUD refreshes its existing panel/drawer contents.
  const observer = new MutationObserver(paint);
  observer.observe(panel, {childList: true}); observer.observe(drawer, {childList: true});
  const workload = document.getElementById('workloadPanel'); if (workload) observer.observe(workload, {childList:true,subtree:true});
  document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); });
  poll();
}

if (typeof document !== 'undefined') startCloudActivity();
