#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {reviewFromIssueEvent} from './cloud-reviews.mjs';
import {readCloudReceipts} from './build-cloud-activity.mjs';

export async function saveOwnerReview(review, api) {
  const resource = '/contents/coordination/cloud-reviews/issue-' + review.issue_number + '.json';
  const content = JSON.stringify(review, null, 2) + '\n';
  for (let attempt = 0; attempt < 3; attempt++) {
    const existing = await api('GET', resource + '?ref=main');
    if (existing.status === 200) {
      if (Buffer.from(existing.body.content, 'base64').toString('utf8') !== content) throw Error('Review ledger entry is immutable');
      const head = await api('GET', '/commits/main');
      if (head.status !== 200 || !/^[a-f0-9]{40}$/.test(head.body.sha)) throw Error('Review head unavailable');
      return head.body.sha;
    }
    if (existing.status !== 404) throw Error('Review ledger read denied');
    const saved = await api('PUT', resource, {message: 'review: record owner ' + review.decision + ' for ' + review.receipt_id,
      branch: 'main', content: Buffer.from(content).toString('base64')});
    if (saved.status === 200 || saved.status === 201) {
      if (!/^[a-f0-9]{40}$/.test(saved.body.commit?.sha || '')) throw Error('Review commit unavailable');
      return saved.body.commit.sha;
    }
    if (![409, 422].includes(saved.status)) throw Error('Review ledger write denied');
  }
  throw Error('Concurrent review update; rerun this issue workflow');
}

async function github(method, resource, body) {
  if (!/^\/(contents\/coordination\/cloud-reviews\/issue-[1-9]\d*\.json(?:\?ref=main)?|commits\/main)$/.test(resource)) throw Error('Review path denied');
  const r = await fetch('https://api.github.com/repos/TeamRovor/rovor-video-engine' + resource, {
    method, redirect: 'error', signal: AbortSignal.timeout(15000), headers: {Accept: 'application/vnd.github+json',
      Authorization: 'Bearer ' + process.env.GITHUB_TOKEN, 'Content-Type': 'application/json', 'X-GitHub-Api-Version': '2022-11-28'},
    ...(body ? {body: JSON.stringify(body)} : {})});
  return {status: r.status, body: await r.json()};
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.env.GITHUB_EVENT_NAME !== 'issues' || process.env.GITHUB_REPOSITORY !== 'TeamRovor/rovor-video-engine') throw Error('Trusted issue event required');
  const event = JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH, 'utf8'));
  const review = reviewFromIssueEvent(event, readCloudReceipts());
  if (!review) {
    fs.appendFileSync(process.env.GITHUB_OUTPUT, 'accepted=false\n'); console.log('Ignored non-owner or non-review issue.');
  } else {
    const sha = await saveOwnerReview(review, github);
    fs.appendFileSync(process.env.GITHUB_OUTPUT, 'accepted=true\nsource_sha=' + sha + '\n');
    console.log('Saved account-authenticated owner decision for ' + review.receipt_id + '.');
  }
}
