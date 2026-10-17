const { test } = require('node:test');
const assert = require('node:assert/strict');
const { FlowOS } = require('../.commercial-labels-dist/src/flowos.js');
const { FlowLaw } = require('../.commercial-labels-dist/src/lib/flow-law.js');
const { MemoryStorage } = require('../.commercial-labels-dist/src/storage/index.js');
const { CommercialLabelRegistry } = require('../.commercial-labels-dist/src/app/commercial-labels/index.js');

const label = (key, value = 'professional', id = 'one') => ({ id, key, value, createdAt: 1 });
const codes = (violations) => violations.map(({ code }) => code).sort();
const KEY = 'COMMERCIAL_LABEL_KEY_INVALID';
const EMPTY = 'COMMERCIAL_LABEL_VALUE_EMPTY';
const DUPLICATE = 'COMMERCIAL_LABEL_KEY_DUPLICATE';

// Independent expected outcomes prevent two validators agreeing on the same bug.
const cases = [
  ['no labels', [], []],
  ['valid labels', [label('product.tier'), label('product-tier2', 'basic', 'two')], []],
  ...['', 'Product.tier', 'product tier', 'product_tier', '1product', '.product', 'product.', 'product..tier', 'product--tier', '產品', ' product.tier ']
    .map((key) => [`invalid key ${JSON.stringify(key)}`, [label(key)], [KEY]]),
  ['empty value', [label('product.tier', '')], [EMPTY]],
  ['whitespace value', [label('product.tier', ' \t\n')], [EMPTY]],
  ['duplicate key', [label('product.tier'), label('product.tier', 'basic', 'two')], [DUPLICATE]],
  ['combined violations', [label('Product Tier', '')], [KEY, EMPTY]],
];

for (const [name, labels, expected] of cases) {
  test(`registry and FlowLaw: ${name}`, () => {
    const registry = new CommercialLabelRegistry(new MemoryStorage());
    assert.deepEqual(codes(registry.validate(labels)), [...expected].sort());
    const result = new FlowLaw().evaluate([], undefined, labels);
    assert.deepEqual(codes(result.violations), [...expected].sort());
    assert.equal(result.passed, expected.length === 0);
  });
}

for (const [key, value, expected] of [
  ['Product Tier', 'valid', KEY],
  ['product.tier', '', EMPTY],
  ['product.tier', ' \t\n', EMPTY],
  [' \t ', 'valid', KEY],
]) {
  test(`registration rejects ${JSON.stringify([key, value])} without writing`, () => {
    const flow = new FlowOS();
    const before = JSON.stringify(flow.snapshot());
    assert.throws(() => flow.commercialLabels.registerLabel(key, value), { message: expected });
    assert.equal(JSON.stringify(flow.snapshot()), before);
    assert.deepEqual(flow.commercialLabels.listLabels(), []);
  });
}

test('normalizes key/value, persists metadata, and snapshots all labels', () => {
  const flow = new FlowOS();
  const first = flow.commercialLabels.registerLabel(' \tproduct.tier\n', ' professional \t');
  const second = flow.commercialLabels.registerLabel('product-region', '台灣');
  assert.equal(first.key, 'product.tier');
  assert.equal(first.value, 'professional');
  assert.ok(first.id);
  assert.ok(Number.isFinite(first.createdAt));
  assert.notEqual(first.id, second.id);
  assert.deepEqual(flow.commercialLabels.listLabels(), [first, second]);
  assert.deepEqual(flow.snapshot().commercialLabels, [first, second]);
  assert.deepEqual(JSON.parse(JSON.stringify(flow.snapshot())).commercialLabels, [first, second]);
  assert.equal(flow.stats().commercialLabels, 2);
  assert.equal(flow.enforce().passed, true);
});

for (const duplicate of ['product.tier', ' \tproduct.tier\n']) {
  test(`rejects duplicate after normalization: ${JSON.stringify(duplicate)}`, () => {
    const flow = new FlowOS();
    flow.commercialLabels.registerLabel('product.tier', 'original');
    const before = JSON.stringify(flow.snapshot());
    assert.throws(() => flow.commercialLabels.registerLabel(duplicate, 'replacement'), { message: DUPLICATE });
    assert.equal(JSON.stringify(flow.snapshot()), before);
    assert.equal(flow.enforce().passed, true);
  });
}

test('MemoryStorage preserves label IDs and upserts the same ID', () => {
  const storage = new MemoryStorage();
  storage.upsertCommercialLabel(label('product.tier'));
  const updated = label('product.tier', 'basic');
  storage.upsertCommercialLabel(updated);
  storage.upsertCommercialLabel(label('product.region', 'TW', 'two'));
  assert.deepEqual(storage.listCommercialLabels(), [updated, label('product.region', 'TW', 'two')]);
  assert.deepEqual(storage.snapshot().commercialLabels, storage.listCommercialLabels());
});

test('FlowOS.enforce evaluates stored labels rather than ignoring its registry', () => {
  const flow = new FlowOS();
  const stored = flow.commercialLabels.registerLabel('product.tier', 'professional');
  // The current storage API exposes records by reference; exercise its actual state.
  stored.value = ' ';
  assert.deepEqual(codes(flow.enforce().violations), [EMPTY]);
  assert.deepEqual(codes(flow.commercialLabels.validate(flow.snapshot().commercialLabels)), [EMPTY]);
});
