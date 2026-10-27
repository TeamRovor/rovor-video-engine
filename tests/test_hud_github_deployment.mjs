import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
  validateDeploymentSecrets, prepareConfig, assertGithubReleaseContext
} from '../integrations/hud-cloud/prepare-github-deploy.mjs';
import {verifyGithubHud, verifiedOrigin} from '../integrations/hud-cloud/verify-github-deploy.mjs';
import {handle} from '../integrations/hud-cloud/worker.mjs';

const dir = new URL('../integrations/hud-cloud/', import.meta.url);
const template = readFileSync(new URL('wrangler.jsonc', dir), 'utf8');
const D1 = 'abcdefff-1111-2222-3333-0123456789ab';
const secrets = {CLOUDFLARE_API_TOKEN: 'cloudflare-scope-limited-token',
  CLOUDFLARE_ACCOUNT_ID: 'a'.repeat(32), ROVOR_HUD_D1_ID: D1,
  ROVOR_HUD_WRITER_TOKEN: 'w'.repeat(40), ROVOR_HUD_READER_TOKEN: 'r'.repeat(40)};

test('only the reviewed Worker-first PRIVATE config may receive the remote D1 id', () => {
  const config = prepareConfig(template, D1);
  assert.equal(config.name, 'rovor-hud-telemetry');
  assert.equal(config.d1_databases[0].database_id, D1);
  assert.equal(config.assets.run_worker_first, true);
  assert.equal(config.assets.binding, 'ASSETS');
  assert.equal(config.main, 'worker.mjs');
  assert.equal(template.includes(D1), false);
  assert.throws(() => prepareConfig(template, 'REPLACE_WITH_PROVISIONED_D1_ID'), /provisioned_d1/);
  const wrong = JSON.parse(template); wrong.assets.run_worker_first = false;
  assert.throws(() => prepareConfig(JSON.stringify(wrong), D1), /unreviewed_private/);
  wrong.assets.run_worker_first = true; wrong.name = 'public-hud';
  assert.throws(() => prepareConfig(JSON.stringify(wrong), D1), /unreviewed_private/);
});

test('release context and distinct credentials fail closed, no bypass with PR branch', () => {
  assert.equal(validateDeploymentSecrets(secrets), true);
  assert.equal(assertGithubReleaseContext({GITHUB_REF:'refs/heads/main',
    GITHUB_REPOSITORY:'TeamRovor/rovor-video-engine'}), true);
  assert.throws(() => assertGithubReleaseContext({GITHUB_REF:'refs/pull/44/merge',
    GITHUB_REPOSITORY:'TeamRovor/rovor-video-engine'}), /trusted_main/);
  assert.throws(() => validateDeploymentSecrets({...secrets,
    ROVOR_HUD_READER_TOKEN: secrets.ROVOR_HUD_WRITER_TOKEN}), /independent/);
  assert.throws(() => validateDeploymentSecrets({...secrets,
    ROVOR_HUD_D1_ID: 'REPLACE_WITH_PROVISIONED_D1_ID'}), /provisioned_d1/);
});

test('readback refuses insecure, redirected, userinfo or mixed-origin URLs', () => {
  assert.equal(verifiedOrigin('https://rovor-hud-telemetry.example.workers.dev/'),
    'https://rovor-hud-telemetry.example.workers.dev');
  for (const bad of ['http://hud.example','https://a:b@hud.example',
    'https://hud.example/file','https://hud.example/#token',
    'https://hud.example/?token=secret','https://127.0.0.1/']) {
    assert.throws(() => verifiedOrigin(bad), /invalid_private|public_https/);
  }
});

test('private Worker serves tracked nine-meter script, but only to authenticated reader', async () => {
  const env = {DB: {}, HUD_READER_TOKEN: 'r'.repeat(40),
    HUD_WRITER_TOKEN: 'w'.repeat(40),
    ASSETS: {fetch: async req => {
      const path = new URL(req.url).pathname;
      return path === '/' ? new Response('<html><body>ROVOR_START_OMNIROUTE</body></html>',
        {headers:{'Content-Type':'text/html'}}) :
        path === '/live-quota-board.js' ?
          new Response('window.ROVOR_QUOTA_BOARD={}', {headers:{'Content-Type':'text/javascript'}}) :
          new Response('Not found', {status:404});
    }}};
  const send = (path, token) => handle(new Request('https://hud.example' + path, {
    headers: token ? {Authorization: 'Bearer ' + token} : {}
  }),env);
  assert.equal((await send('/live-quota-board.js')).status,401);
  assert.equal((await send('/')).status,303);
  assert.equal((await send('/live-quota-board.js',env.HUD_WRITER_TOKEN)).status,401);
  assert.equal((await send('/',env.HUD_READER_TOKEN)).status,200);
  const html = await (await send('/',env.HUD_READER_TOKEN)).text();
  assert.match(html, /<script src="\/live-quota-board\.js"><\/script>/);
  assert.equal((await send('/live-quota-board.js',env.HUD_READER_TOKEN)).status,200);
});

test('readback requires actual auth and live assets, not mere deploy success', async () => {
  const token='r'.repeat(40);
  const fetchOK=async (url, opts) => {
    const path=new URL(url).pathname;
    const auth=opts.headers.Authorization === 'Bearer ' + token;
    if (!auth && path === '/') return new Response(null, {
      status:303,headers:{Location:'https://hud.example/login'}});
    if (!auth) return new Response('{}', {status:401});
    if (path === '/') return new Response('<html><body>ROVOR_START_OMNIROUTE<script src="/live-quota-board.js"></script></body></html>');
    if (path === '/live-quota-board.js')
      return new Response('window.ROVOR_QUOTA_BOARD={}; rvq-overview rvq-ring Mac requests / 24h');
    if (path === '/api/hud/status') return Response.json({
      source:'cloud_hud_telemetry',connection:'never_received',snapshot:null});
    return new Response('{}', {status:404});
  };
  const verified=await verifyGithubHud({origin:'https://hud.example',readerToken:token,send:fetchOK});
  assert.equal(verified.private_auth_verified,true);
  assert.equal(verified.quota_board_verified,true);
  assert.equal(verified.all_nine_live_verified,false);
  await assert.rejects(() => verifyGithubHud({origin:'https://hud.example',
    readerToken:token, send:async (url,opts) => {
      if (!opts.headers.Authorization && new URL(url).pathname==='/live-quota-board.js')
        return new Response('PUBLIC', {status:200});
      return fetchOK(url,opts);
    }}), /anonymous_quota_asset/);
});

test('GitHub deployment requires main and explicit opt-in for unattended releases', () => {
  const workflow=readFileSync(new URL('../.github/workflows/deploy-private-hud-cloudflare.yml',import.meta.url),'utf8');
  assert.match(workflow, /github.ref == 'refs\/heads\/main'/);
  assert.match(workflow, /ROVOR_HUD_GITHUB_AUTO_DEPLOY == 'enabled'/);
  assert.match(workflow, /github.event_name == 'workflow_dispatch'/);
  assert.match(workflow, /wrangler d1 execute DB --remote/);
  assert.match(workflow, /wrangler deploy --config wrangler.github.jsonc/);
  assert.match(workflow, /verify-github-deploy\.mjs/);
  assert.doesNotMatch(workflow, /ChatGPT Site.*deploy/);
});
