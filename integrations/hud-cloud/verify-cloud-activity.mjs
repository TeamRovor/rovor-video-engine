#!/usr/bin/env node
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateCloudReceipt} from './cloud-activity.mjs';
import {compileCloudActivity, readCloudReceipts} from './build-cloud-activity.mjs';

export async function verifyCloudEvidence(receipt, read, now = Date.now()) {
  const r = validateCloudReceipt(receipt, now);
  const pr = await read('/pulls/' + r.artifact_url.split('/').at(-1));
  const mergeResult = pr.merged === true && pr.merge_commit_sha === r.commit_sha;
  const reviewableHead = (pr.merged === true || pr.state === 'open') && pr.head?.sha === r.commit_sha;
  if ((!mergeResult && !reviewableHead) || pr.html_url !== r.artifact_url) throw Error('Cloud result does not match GitHub artifact');
  const resultTime = Date.parse(mergeResult ? pr.merged_at : pr.created_at);
  if (!Number.isFinite(resultTime) || resultTime > Date.parse(r.completed_at)) throw Error('Result unavailable at recorded completion');
  const run = await read('/actions/runs/' + r.checks_url.split('/').at(-1));
  if (run.status !== 'completed' || run.conclusion !== 'success' || run.html_url !== r.checks_url ||
    run.repository?.full_name !== 'TeamRovor/rovor-video-engine' ||
    ![r.commit_sha, pr.head?.sha].includes(run.head_sha)) throw Error('Cloud check does not match successful result revision');
  return r.id;
}

async function readGitHub(resource) {
  if (!/^\/(pulls\/[1-9]\d*|actions\/runs\/[1-9]\d*)$/.test(resource)) throw Error('Evidence path denied');
  const headers = {Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'};
  if (process.env.GITHUB_TOKEN) headers.Authorization = 'Bearer ' + process.env.GITHUB_TOKEN;
  const response = await fetch('https://api.github.com/repos/TeamRovor/rovor-video-engine' + resource,
    {headers, redirect: 'error', signal: AbortSignal.timeout(10000)});
  if (!response.ok) throw Error('GitHub evidence unavailable: ' + response.status);
  return response.json();
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const receipts = compileCloudActivity(readCloudReceipts()).receipts;
  for (const r of receipts) await verifyCloudEvidence(r, readGitHub);
  console.log('Verified public GitHub artifacts and successful checks for ' + receipts.length + ' recorded cloud shifts. This does not verify upstream model usage or human approval.');
}
