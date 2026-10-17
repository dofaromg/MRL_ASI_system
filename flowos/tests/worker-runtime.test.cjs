// origin_signature: MrLiouWord
// Run against the Wrangler dry-run bundle using only ephemeral local bindings.
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { Miniflare } = require('miniflare');
let runtime;
before(() => {
  const bundle = process.env.MRL_WORKER_BUNDLE;
  assert.ok(bundle, 'MRL_WORKER_BUNDLE must name the freshly built Worker bundle');
  runtime = new Miniflare({
    modules: true, modulesRoot: path.dirname(bundle), scriptPath: bundle,
    compatibilityDate: '2024-12-01', compatibilityFlags: ['nodejs_compat'],
    bindings: { MASTER_KEY: 'synthetic-key', VERSION: 'runtime-test', ORIGIN: 'MrLiouWord' },
    kvNamespaces: ['MRLIOUWORD_VAULT', 'PARTICLE_AUTH_VAULT', 'GATE_CONFIG'],
    r2Buckets: ['PARTICLES'],
  });
});
after(async () => { if (runtime) await runtime.dispose(); });
for (const [route, method, auth, body, status, expected] of [
  ['/heartbeat', 'GET', false, undefined, 200, { status: 'ALIVE', origin: 'MrLiouWord' }],
  ['/vcs/init', 'POST', false, undefined, 401, { error: 'Unauthorized' }],
  ['/vcs/init', 'POST', true, undefined, 200, { success: true, msg: 'VCS Initialized (Stub)' }],
  ['/r2/list', 'GET', true, undefined, 200, { count: 0, objects: [] }],
  ['/persona/wake', 'POST', true, '{"message":"synthetic"}', 200, { awakened: true, message: 'synthetic' }],
  ['/vcs/commit_defensive', 'POST', true, '{"files":{}}', 200, { ok: true }],
]) {
  test(`workerd ${method} ${route} authorized=${auth}`, async () => {
    const response = await runtime.dispatchFetch(`https://mrl.invalid${route}`, {
      method, headers: auth ? { 'X-Master-Key': 'synthetic-key' } : {}, body,
    });
    assert.equal(response.status, status);
    const actual = await response.json();
    for (const [key, value] of Object.entries(expected)) assert.deepEqual(actual[key], value);
  });
}
