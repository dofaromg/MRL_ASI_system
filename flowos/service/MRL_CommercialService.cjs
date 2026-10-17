// origin_signature: MrLiouWord
'use strict';
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { createHash, timingSafeEqual } = require('node:crypto');
const { FlowOS } = require('../.commercial-labels-dist/src/flowos.js');
const digest = (text) => createHash('sha256').update(text).digest('hex');
const fail = (status, code) => Object.assign(new Error(code), { status });

function createCommercialService({ accounts, dataDir, clock = () => new Date() }) {
  if (!path.isAbsolute(dataDir)) throw new Error('MRL_DATA_DIR_MUST_BE_ABSOLUTE');
  if (!Array.isArray(accounts) || !accounts.length) throw new Error('MRL_ACCOUNTS_REQUIRED');
  accounts = structuredClone(accounts);
  const ids = new Set();
  const hashes = new Set();
  for (const a of accounts) {
    if (!/^[a-zA-Z0-9_-]{1,64}$/.test(a.id) || ids.has(a.id) ||
        !/^[a-f0-9]{64}$/.test(a.keyHash) || hashes.has(a.keyHash) ||
        !Number.isSafeInteger(a.monthlyQuota) || a.monthlyQuota < 0 ||
        typeof a.enabled !== 'boolean' || typeof a.ownerGrantRef !== 'string' || !a.ownerGrantRef.trim()) {
      throw new Error('MRL_ACCOUNT_CONFIG_INVALID');
    }
    ids.add(a.id); hashes.add(a.keyHash);
  }
  fs.mkdirSync(dataDir, { recursive: true, mode: 0o700 });
  const lock = path.join(dataDir, 'service.lock');
  const lockFd = fs.openSync(lock, 'wx', 0o600);
  fs.writeSync(lockFd, String(process.pid));
  const ledger = path.join(dataDir, 'usage.jsonl');
  const records = new Map();
  const usage = new Map();
  let ledgerFd;
  let poisoned = false;
  const index = (r) => {
    const k = JSON.stringify([r.accountId, r.period, r.requestId]);
    if (records.has(k)) throw new Error('MRL_LEDGER_DUPLICATE');
    records.set(k, r);
    const uk = JSON.stringify([r.accountId, r.period]);
    usage.set(uk, (usage.get(uk) || 0) + 1);
  };
  try {
    if (fs.existsSync(ledger)) {
      const text = fs.readFileSync(ledger, 'utf8');
      if (text && !text.endsWith('\n')) throw new Error('MRL_LEDGER_INCOMPLETE');
      for (const line of text.split('\n').filter(Boolean)) {
        const r = JSON.parse(line);
        if (r.origin_signature !== 'MrLiouWord' || typeof r.accountId !== 'string' ||
            !/^\d{4}-\d{2}$/.test(r.period) || !/^[a-zA-Z0-9_-]{1,128}$/.test(r.requestId) ||
            !/^[a-f0-9]{64}$/.test(r.inputHash) || !r.result || r.units !== 1) {
          throw new Error('MRL_LEDGER_INVALID');
        }
        index(r);
      }
    }
    ledgerFd = fs.openSync(ledger, 'a', 0o600);
  } catch (error) {
    fs.closeSync(lockFd); fs.unlinkSync(lock); throw error;
  }
  const send = (res, status, body) => {
    res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
    res.end(JSON.stringify(body));
  };
  const server = http.createServer(async (req, res) => {
    try {
      if (req.url === '/health' && req.method === 'GET') {
        return send(res, poisoned ? 503 : 200, { service: 'MRL_CommercialService', status: poisoned ? 'storage_error' : 'ready', origin_signature: 'MrLiouWord' });
      }
      const token = /^Bearer ([^\s]{32,256})$/.exec(req.headers.authorization || '')?.[1];
      const keyHash = digest(token || '');
      const account = accounts.find(a => timingSafeEqual(Buffer.from(a.keyHash, 'hex'), Buffer.from(keyHash, 'hex')));
      if (!token || !account) throw fail(401, 'MRL_UNAUTHORIZED');
      if (!account.enabled) throw fail(403, 'MRL_ACCOUNT_DISABLED');
      if (poisoned) throw fail(503, 'MRL_STORAGE_UNAVAILABLE');
      if (req.url === '/v1/usage' && req.method === 'GET') {
        const period = clock().toISOString().slice(0, 7);
        return send(res, 200, { accountId: account.id, period, units: usage.get(JSON.stringify([account.id, period])) || 0, quota: account.monthlyQuota });
      }
      if (req.url !== '/v1/particles/collapse') throw fail(404, 'MRL_ROUTE_NOT_FOUND');
      if (req.method !== 'POST') throw fail(405, 'MRL_METHOD_NOT_ALLOWED');
      if ((req.headers['content-type'] || '').split(';')[0].trim().toLowerCase() !== 'application/json') throw fail(415, 'MRL_JSON_REQUIRED');
      const requestId = req.headers['idempotency-key'];
      if (typeof requestId !== 'string' || !/^[a-zA-Z0-9_-]{1,128}$/.test(requestId)) throw fail(400, 'MRL_REQUEST_ID_REQUIRED');
      const chunks = []; let size = 0;
      for await (const chunk of req) {
        size += chunk.length;
        if (size > 16384) throw fail(413, 'MRL_BODY_TOO_LARGE');
        chunks.push(chunk);
      }
      let body;
      try { body = JSON.parse(Buffer.concat(chunks).toString('utf8')); }
      catch { throw fail(400, 'MRL_JSON_INVALID'); }
      if (!body || typeof body !== 'object' || Array.isArray(body) ||
          Object.keys(body).some(k => k !== 'content') || typeof body.content !== 'string' ||
          !body.content.trim() || Buffer.byteLength(body.content) > 8192) throw fail(400, 'MRL_CONTENT_INVALID');
      // Commit section is synchronous: no await between quota check and durable append.
      const period = clock().toISOString().slice(0, 7);
      const key = JSON.stringify([account.id, period, requestId]);
      const uk = JSON.stringify([account.id, period]);
      const inputHash = digest(body.content);
      const existing = records.get(key);
      if (existing) {
        if (existing.inputHash !== inputHash) throw fail(409, 'MRL_IDEMPOTENCY_CONFLICT');
        return send(res, 200, { ...existing.result, replayed: true });
      }
      if ((usage.get(uk) || 0) >= account.monthlyQuota) throw fail(429, 'MRL_QUOTA_EXCEEDED');
      const flow = new FlowOS();
      flow.commercialLabels.registerLabel('service.name', 'MRL_CommercialService');
      const context = flow.createContext({ persona: account.id });
      const particle = flow.particles.createParticle(body.content, context);
      flow.particles.collapseParticle(particle.id, account.id, 'MRL commercial API request');
      if (!flow.enforce().passed) throw fail(500, 'MRL_FLOWLAW_REJECTED');
      const result = { requestId, accountId: account.id, period, units: 1, origin_signature: 'MrLiouWord', snapshot: flow.snapshot() };
      const record = { accountId: account.id, period, requestId, inputHash, units: 1, ownerGrantRef: account.ownerGrantRef, origin_signature: 'MrLiouWord', result };
      try {
        fs.writeFileSync(ledgerFd, JSON.stringify(record) + '\n');
        fs.fsyncSync(ledgerFd);
      } catch { poisoned = true; throw fail(503, 'MRL_STORAGE_UNAVAILABLE'); }
      index(record);
      send(res, 200, { ...result, replayed: false });
    } catch (error) {
      if (!res.headersSent && !res.destroyed) send(res, error.status || 500, { error: error.status ? error.message : 'MRL_INTERNAL_ERROR' });
    }
  });
  server.requestTimeout = 15000;
  server.headersTimeout = 10000;
  server.on('close', () => { fs.closeSync(ledgerFd); fs.closeSync(lockFd); fs.unlinkSync(lock); });
  return server;
}

if (require.main === module) {
  const accounts = JSON.parse(fs.readFileSync(process.env.MRL_ACCOUNTS_FILE, 'utf8'));
  const server = createCommercialService({ accounts, dataDir: process.env.MRL_DATA_DIR || '' });
  const port = Number(process.env.MRL_SERVICE_PORT || 7820);
  server.listen(port, '127.0.0.1', () => console.log(`MRL_CommercialService listening on 127.0.0.1:${port}`));
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => server.close());
}
module.exports = { createCommercialService, digest };
