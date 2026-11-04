/** HUD alerts: pure evaluation plus a cooldown-based notifier. Alerts are local macOS notifications only. */
const HOUR = 3600000;

export function evaluateAlerts(data, {quotaPercent = 85} = {}) {
  const alerts = [];
  const seen = new Set();
  for (const r of data?.quota?.records || []) {
    if (!(r.used_percent >= quotaPercent)) continue;
    const key = `quota:${r.provider}:${r.account_slot ?? ''}`;
    if (seen.has(key)) continue;
    seen.add(key);
    alerts.push({key, title: `${r.provider} quota ${Math.round(r.used_percent)}% used`, body: `${Math.max(0, Math.round(r.remaining))} left in the current window.`});
  }
  const hb = data?.workforce?.heartbeat;
  if (hb && hb.available === true && hb.recent === false) {
    alerts.push({key: 'workers:stalled', title: 'Workers look stalled', body: 'No recent worker heartbeat. Check the worker LaunchAgent.'});
  }
  return alerts;
}

export function createNotifier({notify, clock = Date.now, cooldownMs = 6 * HOUR}) {
  const last = new Map();
  return async function run(data) {
    const sent = [];
    const alerts = evaluateAlerts(data);
    for (const a of alerts) {
      if (last.has(a.key) && clock() - last.get(a.key) < cooldownMs) continue;
      last.set(a.key, clock());
      try { await notify(a); sent.push(a.key); } catch { last.delete(a.key); }
    }
    for (const k of [...last.keys()]) if (!alerts.some(a => a.key === k)) last.delete(k);
    return sent;
  };
}

export function macNotify(spawnImpl) {
  return async ({title, body}) => {
    const esc = s => String(s).replace(/[\\"]/g, ' ').slice(0, 120);
    await new Promise((res, rej) => {
      const p = spawnImpl('/usr/bin/osascript', ['-e', `display notification "${esc(body)}" with title "ROVOR HUD" subtitle "${esc(title)}"`], {stdio: 'ignore'});
      p.on('error', rej); p.on('exit', c => (c === 0 ? res() : rej(new Error('notify_failed'))));
    });
  };
}
