// origin_signature: MrLiouWord
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { once } = require('node:events');
const http = require('node:http');
const { spawn } = require('node:child_process');
const { createCommercialService, digest } = require('../service/MRL_CommercialService.cjs');
const token = 'a'.repeat(48);
const tokenB = 'b'.repeat(48);
const account = (id = 'customer-a', key = token, extra = {}) => ({ id, keyHash: digest(key), monthlyQuota: 2, enabled: true, ownerGrantRef: 'owner-grant-test-only', ...extra });
function trackedService(dataDir) {
  const opened = [];
  const open = fs.openSync;
  try {
    fs.openSync = (...args) => { const fd = open(...args); opened.push(fd); return fd; };
    return { server: createCommercialService({ accounts: [account()], dataDir }), opened };
  } finally { fs.openSync = open; }
}
function assertDescriptorsClosed(opened) {
  assert.equal(opened.length, 2);
  for (const fd of opened) assert.throws(() => fs.fstatSync(fd), { code: 'EBADF' });
}
async function fixture(t, accounts = [account()]) {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'MRL-service-'));
  let date = new Date('2026-10-17T00:00:00Z');
  let server;
  const start = async () => {
    server = createCommercialService({ accounts, dataDir, clock: () => date });
    server.listen(0, '127.0.0.1'); await once(server, 'listening');
  };
  const stop = () => new Promise((resolve, reject) => server.close(e => e ? reject(e) : resolve()));
  await start();
  t.after(async () => { if (server.listening) await stop(); fs.rmSync(dataDir, { recursive: true, force: true }); });
  const request = async (route = '/v1/particles/collapse', { key = token, id = 'request-1', content = 'MRL test particle', raw, method, headers = {} } = {}) => {
    const response = await fetch(`http://127.0.0.1:${server.address().port}${route}`, {
      method: method || (route === '/v1/particles/collapse' ? 'POST' : 'GET'),
      headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json', 'Idempotency-Key': id, ...headers },
      ...((method === 'POST' || (!method && route === '/v1/particles/collapse')) ? { body: raw ?? JSON.stringify({ content }) } : {}),
    });
    return { status: response.status, body: await response.json() };
  };
  return { request, dataDir, stop, start, setDate: d => { date = new Date(d); } };
}

test('real HTTP collapse returns FlowLaw-valid particle and durable receipt', async t => {
  const f = await fixture(t); const r = await f.request();
  assert.equal(r.status, 200); assert.equal(r.body.origin_signature, 'MrLiouWord');
  assert.equal(r.body.snapshot.particles[0].latest.status, 'collapsed');
  assert.equal(r.body.snapshot.particles[0].latest.content, 'MRL test particle');
  assert.equal(r.body.snapshot.commercialLabels[0].value, 'MRL_CommercialService');
  assert.equal((await f.request('/v1/usage')).body.units, 1);
  assert.equal(fs.readFileSync(path.join(f.dataDir, 'usage.jsonl'), 'utf8').includes(token), false);
});
test('unauthorized and disabled callers cannot consume service', async t => {
  const f = await fixture(t, [account(), account('disabled', tokenB, { enabled: false })]);
  assert.equal((await f.request(undefined, { key: 'wrong' })).status, 401);
  assert.equal((await f.request(undefined, { key: tokenB })).status, 403);
  assert.equal((await f.request('/v1/usage')).body.units, 0);
});
test('retry returns identical stored snapshot after restart without charging twice', async t => {
  const f = await fixture(t); const first = await f.request();
  await f.stop(); await f.start(); const replay = await f.request();
  assert.equal(replay.body.replayed, true);
  assert.deepEqual(replay.body.snapshot, first.body.snapshot);
  assert.equal((await f.request('/v1/usage')).body.units, 1);
});
test('idempotency conflict is rejected and quota is enforced', async t => {
  const f = await fixture(t); await f.request();
  assert.equal((await f.request(undefined, { content: 'different' })).status, 409);
  assert.equal((await f.request(undefined, { id: 'second' })).status, 200);
  assert.equal((await f.request(undefined, { id: 'third' })).status, 429);
  assert.equal((await f.request()).status, 200);
  assert.equal((await f.request('/v1/usage')).body.units, 2);
});
test('concurrent calls cannot overspend remaining quota', async t => {
  const f = await fixture(t, [account('customer-a', token, { monthlyQuota: 1 })]);
  const results = await Promise.all(Array.from({ length: 8 }, (_, i) => f.request(undefined, { id: `r-${i}` })));
  assert.equal(results.filter(r => r.status === 200).length, 1);
  assert.equal(results.filter(r => r.status === 429).length, 7);
});
test('parallel identical requests produce only one ledger entry', async t => {
  const f = await fixture(t);
  const results = await Promise.all(Array.from({ length: 5 }, () => f.request()));
  assert.equal(results.filter(r => !r.body.replayed).length, 1);
  assert.equal((await f.request('/v1/usage')).body.units, 1);
});
test('customers cannot see each other particles or usage', async t => {
  const f = await fixture(t, [account(), account('customer-b', tokenB)]);
  await f.request(undefined, { content: 'private-a' });
  const b = await f.request(undefined, { key: tokenB, content: 'private-b' });
  assert.equal(b.body.snapshot.particles.length, 1);
  assert.equal(JSON.stringify(b.body).includes('private-a'), false);
  assert.equal((await f.request('/v1/usage', { key: tokenB })).body.units, 1);
});
test('invalid JSON, empty content, extra authority fields and absent request ID do not charge', async t => {
  const f = await fixture(t);
  for (const options of [{ raw: '{' }, { content: ' ' }, { raw: JSON.stringify({ content: 'x', origin_signature: 'external' }) }, { id: '' }, { content: 'x'.repeat(8193) }]) {
    assert.equal((await f.request(undefined, options)).status, 400);
  }
  assert.equal((await f.request('/v1/usage')).body.units, 0);
});
test('UTC calendar month provides a new quota window', async t => {
  const f = await fixture(t, [account('customer-a', token, { monthlyQuota: 1 })]);
  await f.request(); f.setDate('2026-11-01T00:00:00Z');
  const r = await f.request(); assert.equal(r.body.period, '2026-11'); assert.equal(r.body.replayed, false);
});
test('exclusive local ledger lock blocks a second service process', async t => {
  const f = await fixture(t);
  assert.throws(() => createCommercialService({ accounts: [account()], dataDir: f.dataDir }), { code: 'EEXIST' });
});
test('incomplete ledger fails closed on restart and releases startup lock', async t => {
  const f = await fixture(t); await f.stop();
  fs.writeFileSync(path.join(f.dataDir, 'usage.jsonl'), '{');
  assert.throws(() => createCommercialService({ accounts: [account()], dataDir: f.dataDir }), /MRL_LEDGER_INCOMPLETE/);
  assert.equal(fs.existsSync(path.join(f.dataDir, 'service.lock')), false);
});
test('invalid provisioning is rejected before opening storage', () => {
  assert.throws(() => createCommercialService({ accounts: [account()], dataDir: 'relative' }), /MRL_DATA_DIR_MUST_BE_ABSOLUTE/);
  assert.throws(() => createCommercialService({ accounts: [account(), account()], dataDir: os.tmpdir() }), /MRL_ACCOUNT_CONFIG_INVALID/);
  assert.throws(() => createCommercialService({ accounts: [account('a', token, { ownerGrantRef: '' })], dataDir: os.tmpdir() }), /MRL_ACCOUNT_CONFIG_INVALID/);
});

test('routes and media type fail with explicit HTTP errors', async t => {
  const f = await fixture(t);
  assert.equal((await f.request('/health')).status, 200);
  assert.equal((await f.request('/missing')).status, 404);
  assert.equal((await f.request(undefined, { method: 'GET' })).status, 405);
  assert.equal((await f.request(undefined, { headers: { 'Content-Type': 'application/json-evil' } })).status, 415);
});

test('durable write failure disables new work and reports unhealthy', async t => {
  const f = await fixture(t);
  const original = fs.fsyncSync;
  try {
    fs.fsyncSync = () => { throw new Error('test disk failure'); };
    assert.equal((await f.request()).status, 503);
  } finally { fs.fsyncSync = original; }
  assert.equal((await f.request('/health')).status, 503);
  assert.equal((await f.request(undefined, { id: 'next' })).status, 503);
});

test('offline provisioning stores only a hash in config and never overwrites accounts', () => {
  const { provision } = require('../service/MRL_ProvisionAccount.cjs');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'MRL-provision-'));
  try {
    const result = provision(dir, 'customer', 10, 'test-owner-reference');
    const key = fs.readFileSync(result.keyFile, 'utf8').trim();
    const config = fs.readFileSync(result.configFile, 'utf8');
    assert.equal(key.length, 64);
    assert.equal(JSON.parse(config)[0].keyHash, digest(key));
    assert.equal(config.includes(key), false);
    assert.throws(() => provision(dir, 'second', 20, 'another-reference'), { code: 'EEXIST' });
    assert.equal(fs.existsSync(path.join(dir, 'second.key')), false);
    assert.equal(fs.readFileSync(result.configFile, 'utf8'), config);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('cross-customer receipts fail closed; restored ledger preserves isolated replays and usage', async t => {
  const f = await fixture(t, [account(), account('customer-b', tokenB)]);
  const a = await f.request(undefined, { content: 'synthetic-a' });
  const b = await f.request(undefined, { key: tokenB, content: 'synthetic-b' });
  await f.stop();
  const ledger = path.join(f.dataDir, 'usage.jsonl');
  const original = fs.readFileSync(ledger, 'utf8');
  const records = original.trim().split('\n').map(JSON.parse);
  records[0].result = records[1].result;
  const corrupt = records.map(JSON.stringify).join('\n') + '\n';
  fs.writeFileSync(ledger, corrupt);
  for (let attempt = 0; attempt < 2; attempt++) {
    assert.throws(() => createCommercialService({ accounts: [account(), account('customer-b', tokenB)], dataDir: f.dataDir }), /MRL_LEDGER_INVALID/);
    assert.equal(fs.existsSync(path.join(f.dataDir, 'service.lock')), false);
    assert.equal(fs.readFileSync(ledger, 'utf8'), corrupt);
  }
  fs.writeFileSync(ledger, original); await f.start();
  for (const [key, content, first] of [[token, 'synthetic-a', a], [tokenB, 'synthetic-b', b]]) {
    const replay = await f.request(undefined, { key, content });
    assert.equal(replay.body.replayed, true);
    assert.deepEqual(replay.body.snapshot, first.body.snapshot);
    assert.equal((await f.request('/v1/usage', { key })).body.units, 1);
  }
  assert.equal(fs.readFileSync(ledger, 'utf8'), original);
});

const invalidReceipts = {
  accountId: r => { r.result.accountId = 'customer-b'; },
  requestId: r => { r.result.requestId = 'other-request'; },
  period: r => { r.result.period = '2026-09'; },
  units: r => { r.result.units = 2; },
  signature: r => { r.result.origin_signature = 'external'; },
  missingSignature: r => { delete r.result.origin_signature; },
  nullResult: r => { r.result = null; },
  stringResult: r => { r.result = 'receipt'; },
  arrayResult: r => { r.result = []; },
  missingSnapshot: r => { delete r.result.snapshot; },
  nullSnapshot: r => { r.result.snapshot = null; },
  arraySnapshot: r => { r.result.snapshot = []; },
  brokenSnapshotCollection: r => { r.result.snapshot.particles = {}; },
  missingSnapshotCollection: r => { delete r.result.snapshot.memories; },
  invalidAccountId: r => { r.accountId = r.result.accountId = ''; },
  invalidMonth: r => { r.period = r.result.period = '2026-13'; },
  externalAuthority: r => { r.origin_signature = r.result.origin_signature = 'external'; },
  invalidGrant: r => { r.ownerGrantRef = ''; },
};
for (const [name, mutate] of Object.entries(invalidReceipts)) {
  test(`ledger rejects ${name} without modifying durable data or blocking recovery`, async t => {
    const f = await fixture(t); await f.request(); await f.stop();
    const ledger = path.join(f.dataDir, 'usage.jsonl');
    const original = fs.readFileSync(ledger, 'utf8');
    const record = JSON.parse(original); mutate(record);
    const damaged = JSON.stringify(record) + '\n';
    fs.writeFileSync(ledger, damaged);
    assert.throws(() => createCommercialService({ accounts: [account()], dataDir: f.dataDir }), /MRL_LEDGER_INVALID/);
    assert.equal(fs.existsSync(path.join(f.dataDir, 'service.lock')), false);
    assert.equal(fs.readFileSync(ledger, 'utf8'), damaged);
    fs.writeFileSync(ledger, original); await f.start();
    assert.equal((await f.request('/v1/usage')).body.units, 1);
    assert.equal((await f.request()).body.replayed, true);
  });
}

for (const [name, damage, error] of [
  ['invalid JSON after valid record', text => text + '{broken}\n', SyntaxError],
  ['null record', text => text + 'null\n', /MRL_LEDGER_INVALID/],
  ['duplicate record', text => text + text, /MRL_LEDGER_DUPLICATE/],
  ['partial trailing write', text => text + '{', /MRL_LEDGER_INCOMPLETE/],
]) {
  test(`damaged ledger: ${name} rejects the entire startup`, async t => {
    const f = await fixture(t); await f.request(); await f.stop();
    const ledger = path.join(f.dataDir, 'usage.jsonl');
    const original = fs.readFileSync(ledger, 'utf8');
    const damaged = damage(original); fs.writeFileSync(ledger, damaged);
    assert.throws(() => createCommercialService({ accounts: [account()], dataDir: f.dataDir }), error);
    assert.equal(fs.existsSync(path.join(f.dataDir, 'service.lock')), false);
    assert.equal(fs.readFileSync(ledger, 'utf8'), damaged);
    fs.writeFileSync(ledger, original); await f.start();
    assert.equal((await f.request('/v1/usage')).body.units, 1);
    assert.equal((await f.request()).body.replayed, true);
  });
}

test('occupied port releases startup descriptors and lock; later close cannot delete a replacement lock', async t => {
  const f = await fixture(t); await f.request(); await f.stop();
  const blocker = http.createServer(); blocker.listen(0, '127.0.0.1'); await once(blocker, 'listening');
  t.after(() => new Promise(resolve => blocker.close(resolve)));
  const port = blocker.address().port;
  const { server: failed, opened } = trackedService(f.dataDir);
  const ledger = fs.readFileSync(path.join(f.dataDir, 'usage.jsonl'), 'utf8');
  const error = once(failed, 'error'); failed.listen(port, '127.0.0.1');
  assert.equal((await error)[0].code, 'EADDRINUSE');
  assertDescriptorsClosed(opened);
  assert.equal(fs.existsSync(path.join(f.dataDir, 'service.lock')), false);
  await f.start();
  await new Promise(resolve => failed.close(resolve));
  assert.equal(fs.existsSync(path.join(f.dataDir, 'service.lock')), true);
  assert.throws(() => failed.listen(0), /MRL_SERVICE_CLOSED/);
  assert.throws(() => createCommercialService({ accounts: [account()], dataDir: f.dataDir }), { code: 'EEXIST' });
  assert.equal((await f.request('/v1/usage')).body.units, 1);
  assert.equal((await f.request()).body.replayed, true);
  assert.equal(fs.readFileSync(path.join(f.dataDir, 'usage.jsonl'), 'utf8'), ledger);
});

for (const port of [-1, 65536, NaN]) {
  test(`invalid port ${port} releases the lock synchronously and supports restart`, async t => {
    const f = await fixture(t); await f.stop();
    const { server: failed, opened } = trackedService(f.dataDir);
    assert.throws(() => failed.listen(port, '127.0.0.1'), { code: 'ERR_SOCKET_BAD_PORT' });
    assertDescriptorsClosed(opened);
    assert.equal(fs.existsSync(path.join(f.dataDir, 'service.lock')), false);
    await f.start();
    await new Promise(resolve => failed.close(resolve));
    assert.equal(fs.existsSync(path.join(f.dataDir, 'service.lock')), true);
    assert.equal((await f.request('/v1/usage')).body.units, 0);
    assert.equal((await f.request()).status, 200);
  });
}

test('CLI exits unsuccessfully on occupied port and leaves data directory restartable', async t => {
  const f = await fixture(t); await f.stop();
  const blocker = http.createServer(); blocker.listen(0, '127.0.0.1'); await once(blocker, 'listening');
  t.after(() => new Promise(resolve => blocker.close(resolve)));
  const config = path.join(f.dataDir, 'test-accounts.json');
  fs.writeFileSync(config, JSON.stringify([account()]));
  const child = spawn(process.execPath, [path.resolve(__dirname, '../service/MRL_CommercialService.cjs')], {
    env: { ...process.env, MRL_ACCOUNTS_FILE: config, MRL_DATA_DIR: f.dataDir, MRL_SERVICE_PORT: String(blocker.address().port) },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  t.after(() => { if (child.exitCode === null) child.kill(); });
  let stderr = ''; child.stderr.on('data', chunk => { stderr += chunk; });
  const [code] = await once(child, 'exit');
  assert.equal(code, 1); assert.match(stderr, /EADDRINUSE/);
  assert.equal(fs.existsSync(path.join(f.dataDir, 'service.lock')), false);
  await f.start(); assert.equal((await f.request()).status, 200);
});

test('failure writing the lock PID releases the acquired lock and descriptor', async t => {
  const f = await fixture(t); await f.stop();
  const write = fs.writeSync;
  const close = fs.closeSync;
  const closed = [];
  try {
    fs.writeSync = () => { throw new Error('synthetic lock write failure'); };
    fs.closeSync = fd => { closed.push(fd); return close(fd); };
    assert.throws(() => createCommercialService({ accounts: [account()], dataDir: f.dataDir }), /synthetic lock write failure/);
  } finally { fs.writeSync = write; fs.closeSync = close; }
  assert.equal(closed.length, 1);
  assert.throws(() => fs.fstatSync(closed[0]), { code: 'EBADF' });
  assert.equal(fs.existsSync(path.join(f.dataDir, 'service.lock')), false);
  await f.start(); assert.equal((await f.request()).status, 200);
});
