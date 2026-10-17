// origin_signature: MrLiouWord
const { test, afterEach } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const pkg = require('../package.json');
const entry = require(path.resolve(__dirname, '..', pkg.main));
const worker = entry.default;
const realFetch = global.fetch;
afterEach(() => { global.fetch = realFetch; });

function environment(overrides = {}) {
  const kv = { get: async () => null, put: async () => {} };
  return {
    MRLIOUWORD_VAULT: kv, PARTICLE_AUTH_VAULT: kv, GATE_CONFIG: kv,
    DB: { prepare() { throw new Error('Unexpected DB access'); } },
    PARTICLES: { list: async () => ({ objects: [{ key: 'synthetic-particle' }] }) },
    GATE_ENGINE: {
      idFromName: (name) => { assert.equal(name, 'global-gate'); return 'gate-id'; },
      get: (id) => { assert.equal(id, 'gate-id'); return { fetch: async () => Response.json({ gate: true }) }; },
    },
    MASTER_KEY: 'synthetic-key', VERSION: 'test-version', ORIGIN: 'MrLiouWord',
    ...overrides,
  };
}
function call(route, { method = 'GET', body, authorized = true, headers = {}, env = environment() } = {}) {
  return worker.fetch(new Request(`https://mrl.invalid${route}`, {
    method, headers: { ...(authorized ? { 'X-Master-Key': 'synthetic-key' } : {}), ...headers },
    body: body === undefined ? undefined : typeof body === 'string' ? body : JSON.stringify(body),
  }), env, { waitUntil() {} });
}

test('package main and declarations match freshly built output', () => {
  assert.ok(fs.statSync(path.resolve(__dirname, '..', pkg.types)).size > 0);
  assert.equal(entry.FlowOS, require('../dist/src/flowos.js').FlowOS);
  assert.equal(typeof entry.handleVCSCommit, 'function');
  assert.equal(typeof entry.CommercialLabelRegistry, 'function');
});
for (const route of ['/', '/status', '/heartbeat', '/world/heartbeat', '/frequencies']) {
  test(`public route ${route}`, async () => {
    const response = await call(route, { authorized: false });
    assert.equal(response.status, 200);
    const body = await response.json();
    assert.equal(route === '/heartbeat' ? body.origin : body.name, route === '/heartbeat' ? 'MrLiouWord' : 'MrLiouWord Particle Edge');
    assert.equal(body.version, 'test-version');
  });
}
for (const route of ['/vcs/init', '/vcs/commit_defensive', '/r2/list', '/persona/wake']) {
  test(`protected route denies missing key ${route}`, async () => {
    const response = await call(route, { method: 'POST', body: {}, authorized: false });
    assert.equal(response.status, 401);
    assert.equal((await response.json()).error, 'Unauthorized');
  });
}
for (const [route, method, body, expected] of [
  ['/vcs/init', 'POST', {}, { success: true, msg: 'VCS Initialized (Stub)' }],
  ['/vcs/add', 'POST', { path: 'synthetic', content: 'test' }, { success: true }],
  ['/vcs/add', 'POST', '{', { success: true }],
  ['/vcs/commit', 'POST', { message: 'synthetic', persona_id: 'test' }, { success: true, hash: 'new_hash' }],
  ['/vcs/status', 'GET', undefined, { head: 'latest' }],
  ['/persona/wake', 'POST', { message: 'test' }, { awakened: true, message: 'test' }],
  ['/persona/list', 'GET', undefined, { personas: [] }],
  ['/r2/list', 'GET', undefined, { count: 1, objects: [{ key: 'synthetic-particle' }] }],
]) {
  test(`${method} ${route} body=${typeof body}`, async () => {
    const response = await call(route, { method, body });
    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), expected);
  });
}
test('existing query-key compatibility', async () => {
  assert.equal((await call('/vcs/status?key=synthetic-key', { authorized: false })).status, 200);
});
test('unknown R2 route returns 404', async () => {
  assert.equal((await call('/r2/unknown')).status, 404);
});
test('heartbeat defaults and pulse header retain original contract', async () => {
  const response = await call('/anything', { headers: { 'X-Check-Pulse': '1' }, env: environment({ VERSION: '', ORIGIN: '' }) });
  const body = await response.json();
  assert.equal(body.version, '4.0.0'); assert.equal(body.origin, 'MrLiouWord');
});
test('gate uses namespace.get(id) and forwards native Response', async () => {
  const response = await call('/gate/evaluate', { method: 'POST', body: { sample: true }, env: environment({ GATE_ENGINE: {
    idFromName: (name) => { assert.equal(name, 'global-gate'); return 'id'; },
    get: (id) => { assert.equal(id, 'id'); return { fetch: async (url, init) => {
      assert.equal(url, 'https://internal/gate/evaluate'); assert.equal(init.method, 'POST');
      assert.equal(init.headers['X-Node-Id'], 'Edge-Node-L2');
      assert.deepEqual(JSON.parse(init.body), { sample: true });
      return new Response('gate-result', { status: 202, headers: { 'X-Gate': 'test' } });
    } }; },
  } }) });
  assert.equal(response.status, 202); assert.equal(response.headers.get('X-Gate'), 'test');
  assert.equal(await response.text(), 'gate-result');
});
test('GitHub sync success uses locked API version and token', async () => {
  global.fetch = async (url, init) => {
    assert.equal(url, 'https://api.github.com/user/repos');
    assert.equal(init.headers['X-GitHub-Api-Version'], '2022-11-28');
    assert.equal(init.headers.Authorization, 'Bearer synthetic-token');
    return Response.json([{ name: 'synthetic' }]);
  };
  const response = await call('/vcs/sync_github', { env: environment({ GITHUB_TOKEN: 'synthetic-token' }) });
  assert.deepEqual(await response.json(), { success: true, github_data: [{ name: 'synthetic' }] });
});
test('GitHub HTTP failure propagates status', async () => {
  global.fetch = async () => Response.json({ message: 'synthetic failure' }, { status: 403 });
  const response = await call('/vcs/sync_github');
  assert.equal(response.status, 403); assert.equal((await response.json()).success, false);
});
test('GitHub network failure maps to 503', async () => {
  global.fetch = async () => { throw new Error('synthetic offline'); };
  assert.equal((await call('/vcs/sync_github')).status, 503);
});
test('defensive commit remains routed to existing handler without external sync', async () => {
  global.fetch = async () => { throw new Error('unexpected external call'); };
  const response = await call('/vcs/commit_defensive', { method: 'POST', body: { files: {} } });
  assert.equal(response.status, 200); assert.equal((await response.json()).ok, true);
});
test('defensive commit retains configured GitHub blob sync', async () => {
  let calls = 0;
  global.fetch = async (url, init) => {
    calls++;
    assert.equal(url, 'https://api.github.com/repos/synthetic/test/git/blobs');
    assert.deepEqual(JSON.parse(init.body), { content: JSON.stringify({ test: 'synthetic' }), encoding: 'utf-8' });
    return Response.json({ sha: 'synthetic' });
  };
  const response = await call('/vcs/commit_defensive', { method: 'POST', body: { files: { test: 'synthetic' } },
    env: environment({ ENABLE_GITHUB_SYNC: true, GITHUB_REPO: 'synthetic/test' }) });
  assert.equal((await response.json()).ok, true); assert.equal(calls, 1);
});
test('asynchronous R2 failure reaches Worker 503 boundary', async () => {
  const response = await call('/r2/list', { env: environment({ PARTICLES: { list: async () => { throw new Error('synthetic R2 failure'); } } }) });
  assert.equal(response.status, 503); assert.equal((await response.json()).error, 'ASI_SYNAPSE_FAILURE');
});
test('malformed defensive commit reaches Worker 503 boundary', async () => {
  assert.equal((await call('/vcs/commit_defensive', { method: 'POST', body: '{' })).status, 503);
});
test('FlowOS preserves signals, denied gate, config and commercial label state together', async () => {
  const flow = new entry.FlowOS();
  flow.config.update({ origin_signature: 'MrLiouWord' });
  assert.equal(flow.config.get('origin_signature'), 'MrLiouWord');
  flow.commercialLabels.registerLabel('product.tier', 'test');
  const context = flow.createContext({ persona: 'synthetic' });
  const particle = flow.particles.createParticle('test', context);
  assert.equal(flow.snapshot().particles[0].id, particle.id);
  assert.equal(flow.snapshot().commercialLabels.length, 1);
  assert.equal(flow.enforce(context).violations.filter(v => v.code.startsWith('COMMERCIAL_LABEL_')).length, 0);
  const seen = [];
  flow.neuralLink.on('test', packet => { seen.push(packet); });
  const allowed = await flow.emitSignal('test', { sample: true }, context);
  assert.equal(allowed.decision.allowed, true); assert.equal(seen[0], allowed.packet);
  flow.gate.register(() => ({ allowed: false, reason: 'synthetic deny' }));
  assert.deepEqual(await flow.emitSignal('test', {}, context), { decision: { allowed: false, reason: 'synthetic deny' } });
  assert.equal(seen.length, 1);
});
