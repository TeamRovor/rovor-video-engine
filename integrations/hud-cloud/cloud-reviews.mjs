const REPO = 'TeamRovor/rovor-video-engine';
const OWNER = 'TeamRovor';
const MARKER = /<!-- ROVOR_REVIEW_V1\s*([\s\S]*?)\s*-->/g;
const validID = s => typeof s === 'string' && /^[a-z0-9][a-z0-9-]{0,149}$/.test(s);
const invalid = () => { throw Error('Invalid owner review'); };

export function reviewLink(receipt, decision) {
  if (!validID(receipt.id) || !/^[a-f0-9]{40}$/.test(receipt.commit_sha) || !['pass', 'fail'].includes(decision)) invalid();
  const payload = {receipt_id: receipt.id, commit_sha: receipt.commit_sha, decision};
  const body = `Decision: **${decision.toUpperCase()}**\nReceipt: ${receipt.id}\nCommit: ${receipt.commit_sha}\n\nReason:\n\n<!-- ROVOR_REVIEW_V1\n${JSON.stringify(payload)}\n-->`;
  const url = new URL('https://github.com/' + REPO + '/issues/new');
  url.searchParams.set('title', 'ROVOR review: ' + decision.toUpperCase() + ' ' + receipt.id);
  url.searchParams.set('body', body);
  return url.href;
}

export function reviewFromIssueEvent(event, receipts, now = Date.now()) {
  const issue = event?.issue, sender = event?.sender;
  if (event?.action !== 'opened' || event?.repository?.full_name !== REPO ||
      sender?.login !== OWNER || sender?.type !== 'User' || issue?.user?.login !== OWNER ||
      issue.user.type !== 'User' || issue.performed_via_github_app || issue.pull_request) return null;
  if (typeof issue.title !== 'string' || !issue.title.startsWith('ROVOR review: ')) return null;
  if (typeof issue.body !== 'string' || issue.body.length > 8192) invalid();
  const matches = [...issue.body.matchAll(MARKER)]; if (matches.length !== 1) invalid();
  let data; try { data = JSON.parse(matches[0][1]); } catch { invalid(); }
  if (!data || Object.keys(data).sort().join(',') !== 'commit_sha,decision,receipt_id' || !['pass', 'fail'].includes(data.decision)) invalid();
  const receipt = receipts.find(r => r.id === data.receipt_id && r.commit_sha === data.commit_sha);
  if (!receipt || issue.title !== 'ROVOR review: ' + data.decision.toUpperCase() + ' ' + receipt.id) invalid();
  const reason = issue.body.slice(0, matches[0].index).split('Reason:\n').slice(1).join('Reason:\n').trim();
  if (reason.length > 1000 || /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(reason)) invalid();
  return validateOwnerReview({schema_version: 1, source: 'github_owner_issue', issue_number: issue.number,
    receipt_id: receipt.id, commit_sha: receipt.commit_sha, decision: data.decision, reason,
    author: OWNER, created_at: issue.created_at, issue_url: issue.html_url}, receipts, now);
}

export function validateOwnerReview(r, receipts, now = Date.now()) {
  if (!r || r.schema_version !== 1 || r.source !== 'github_owner_issue' || r.author !== OWNER ||
      !Number.isSafeInteger(r.issue_number) || r.issue_number < 1 || !['pass', 'fail'].includes(r.decision) ||
      !validID(r.receipt_id) || !/^[a-f0-9]{40}$/.test(r.commit_sha || '') ||
      r.issue_url !== 'https://github.com/' + REPO + '/issues/' + r.issue_number ||
      typeof r.reason !== 'string' || r.reason.length > 1000) invalid();
  const at = Date.parse(r.created_at);
  const receipt = receipts.find(x => x.id === r.receipt_id && x.commit_sha === r.commit_sha);
  if (!receipt || !Number.isFinite(at) || at < Date.parse(receipt.completed_at) || at > now + 300000) invalid();
  return {schema_version: 1, source: r.source, issue_number: r.issue_number, receipt_id: r.receipt_id,
    commit_sha: r.commit_sha, decision: r.decision, reason: r.reason, author: OWNER, created_at: r.created_at, issue_url: r.issue_url};
}

export function latestOwnerReviews(rows, receipts, now = Date.now()) {
  if (!Array.isArray(rows) || rows.length > 2000) invalid();
  const out = new Map(), ids = new Set();
  for (const row of rows) {
    const r = validateOwnerReview(row, receipts, now);
    if (ids.has(r.issue_number)) invalid(); ids.add(r.issue_number);
    const old = out.get(r.receipt_id);
    if (!old || r.issue_number > old.issue_number) out.set(r.receipt_id, r);
  }
  return [...out.values()];
}
