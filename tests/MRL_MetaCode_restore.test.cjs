// origin_signature: MrLiouWord
const { test } = require('node:test');
const assert = require('node:assert/strict');
const MetaCode = import('../metacode_core.js').then(m => m.default);

async function populated() {
  const C = await MetaCode;
  const core = new C();
  const a = core.createParticle({ domain: 'memory', embed: [1, 0] });
  const b = core.createParticle({ domain: 'runtime', embed: [0, 1] });
  core.createLink(a.id, b.id, 'depends-on');
  return core;
}

test('restore preserves original identity, version, timestamps and self description', async () => {
  const source = await populated(); const saved = source.export();
  const C = await MetaCode; const target = new C(); target.import(saved);
  assert.equal(target.id, saved.meta.id);
  assert.equal(target.version, saved.meta.version);
  assert.equal(target.created_at, saved.meta.created_at);
  assert.deepEqual(target.self, saved.self);
  assert.deepEqual([...target.particles.values()], saved.particles);
  assert.deepEqual([...target.links.values()], saved.links);
  assert.equal(target.verify().ok, true);
});

test('invalid import leaves existing state intact', async () => {
  const core = await populated();
  const before = JSON.stringify({ id: core.id, particles: [...core.particles], links: [...core.links], cycles: core.cycles, journal: core.journal });
  assert.throws(() => core.import({ particles: [{ id: 'bad' }], links: null }));
  assert.equal(JSON.stringify({ id: core.id, particles: [...core.particles], links: [...core.links], cycles: core.cycles, journal: core.journal }), before);
});

for (const [name, mutate] of [
  ['duplicate particles', d => d.particles.push(d.particles[0])],
  ['duplicate links', d => d.links.push(d.links[0])],
  ['missing link target', d => { d.links[0].to = 'missing'; }],
  ['missing particle link target', d => { d.particles[0].links[0].to = 'missing'; }],
  ['invalid invariant', d => { d.particles[0].cap.mag = -1; }],
  ['non-finite magnitude', d => { d.particles[0].cap.mag = Infinity; }],
  ['invalid cycles', d => { d.cycles = {}; }],
  ['invalid journal', d => { d.journal = {}; }],
  ['conflicting identity', d => { d.self.id = 'another-root'; }],
]) {
  test(`rejects ${name} atomically`, async () => {
    const core = await populated(); const saved = structuredClone(core.export());
    const before = JSON.stringify([...core.particles]); mutate(saved);
    assert.throws(() => core.import(saved));
    assert.equal(JSON.stringify([...core.particles]), before);
  });
}

test('import does not alias caller data', async () => {
  const source = await populated(); const data = source.export();
  const C = await MetaCode; const restored = new C(); restored.import(data);
  data.particles[0].cap.mag = 999; data.self.id = 'changed';
  assert.notEqual([...restored.particles.values()][0].cap.mag, 999);
  assert.notEqual(restored.self.id, 'changed');
});

test('legacy particle/link-only packet retains current root identity', async () => {
  const source = await populated(); const C = await MetaCode; const target = new C();
  const id = target.id; const saved = source.export();
  target.import({ particles: saved.particles, links: saved.links });
  assert.equal(target.id, id); assert.equal(target.verify().ok, true);
});
