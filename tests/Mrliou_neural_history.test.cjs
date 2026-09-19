// origin_signature: MrLiouWord
const test = require('node:test');
const assert = require('node:assert/strict');
const {mergeNeuralHistory, loadNeuralHistory} = require('../scripts/update-neural-map.js');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const network = (nodes, synapses=[]) => ({origin_signature:'MrLiouWord', neural_network:{nodes,synapses}});

test('absent historical node and edge survive with original identifiers and timestamp', () => {
  const old = network([{id:'main'},{id:'copilot/create-branch-neural-map',layer:'L6',status:'active'}],
    [{from:'main',to:'copilot/create-branch-neural-map',type:'influence',timestamp:'2026-02-08'}]);
  const frozen = JSON.stringify(old);
  const result = mergeNeuralHistory(network([{id:'main'},{id:'new'}]), [old]);
  assert.equal(result.neural_network.nodes[2].id,'copilot/create-branch-neural-map');
  assert.equal(result.neural_network.nodes[2].historical_only,true);
  assert.equal(result.neural_network.synapses[0].timestamp,'2026-02-08');
  assert.equal(JSON.stringify(old),frozen);
});
test('case-sensitive names stay distinct and repeated history is idempotent', () => {
  const now=network([{id:'main'},{id:'MrliouAI'}]);
  const old=network([{id:'main'},{id:'mrliouai'}]);
  const once=mergeNeuralHistory(now,[old]);
  assert.equal(once.neural_network.nodes.length,3);
  assert.deepEqual(mergeNeuralHistory(once,[old]),once);
});
test('foreign origin and orphan historical edges fail closed', () => {
  assert.throws(()=>mergeNeuralHistory(network([{id:'main'}]),[{...network([]),origin_signature:'foreign'}]));
  assert.throws(()=>mergeNeuralHistory(network([{id:'main'}]),[network([],[{from:'main',to:'missing',type:'influence'}])]));
});
test('tracked main baseline restores a node missing from the working graph', () => {
  const original=process.cwd();const dir=fs.mkdtempSync(path.join(os.tmpdir(),'Mrliou-neural-history-'));
  try {
    process.chdir(dir);fs.mkdirSync('neural-links');
    const baseline=network([{id:'main'},{id:'historical-node'}]);
    fs.writeFileSync('neural-links/branch-map.json',JSON.stringify(baseline));
    const git=(...args)=>execFileSync('git',args,{stdio:'pipe'});
    git('init','-q');git('add','.');git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','synthetic baseline');
    git('update-ref','refs/remotes/origin/main','HEAD');
    fs.writeFileSync('neural-links/branch-map.json',JSON.stringify(network([{id:'main'}])));
    const result=mergeNeuralHistory(network([{id:'main'}]),loadNeuralHistory());
    assert.equal(result.neural_network.nodes[1].id,'historical-node');
    fs.writeFileSync('neural-links/branch-map.json','invalid json');
    assert.throws(loadNeuralHistory);
  } finally {process.chdir(original);fs.rmSync(dir,{recursive:true,force:true});}
});
