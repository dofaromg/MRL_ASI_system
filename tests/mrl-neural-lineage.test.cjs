// origin_signature: MrLiouWord
const test = require('node:test');
const assert = require('node:assert/strict');
const {buildNeuralNetwork, normalizePR, getPRData, mergeNeuralHistory, mainContains} = require('../scripts/update-neural-map.js');
const raw = require('./fixtures/mrl-neural-prs-20261017.json');
const prs = raw.map(normalizePR);
const build = (extra={}) => buildNeuralNetwork({branches:['main','unassociated'], prData:prs,
  observedAt:'2026-10-17T18:30:00Z', sourceCommit:'284e1a971cd8c9f6f0a22e21e403e08a3707e7ff',
  mainContains:sha => sha === prs.find(p=>p.number===7).mergeCommit, ...extra});
const pr = (map,n) => map.pull_requests.find(p=>p.number===n);
const edge = (map,n) => map.neural_network.synapses.find(e=>e.pr_number===n);

test('PR 9 merges into PR 8 branch, while PR 8 remains open against main', () => {
  const map=build();
  assert.equal(edge(map,9).from, prs.find(p=>p.number===8).headRefName);
  assert.equal(edge(map,9).type,'merge');
  assert.equal(edge(map,9).merge_commit,'f022d69e41e8c415cc955a226ff84b64313060e2');
  assert.equal(pr(map,9).branch_merge,'merged');
  assert.equal(pr(map,9).main_integration,'not_in_main');
  assert.equal(edge(map,8).from,'main');
  assert.equal(edge(map,8).type,'influence');
  assert.equal(pr(map,8).branch_merge,'not_merged');
  assert.equal(pr(map,8).mergeCommit,null);
  assert.equal(pr(map,8).main_integration,'not_established');
  assert.equal(map.neural_network.nodes.find(n=>n.id===edge(map,9).to).parent,edge(map,9).from);
});
test('direct main merge requires actual merge evidence; deployment stays unverified', () => {
  const map=build();
  assert.equal(edge(map,7).from,'main');
  assert.equal(pr(map,7).main_integration,'confirmed');
  assert.ok(map.pull_requests.every(p=>p.deployment==='not_verified'));
});
test('nested merge only becomes main integrated when its exact merge SHA is contained', () => {
  assert.equal(pr(build({mainContains:()=>true}),9).main_integration,'confirmed');
  assert.equal(pr(build({mainContains:()=>null}),9).main_integration,'unknown');
});
test('PR metadata includes original author, SHAs, dates and URL without fabricated author', () => {
  const p=pr(build(),9), source=raw.find(p=>p.number===9);
  assert.equal(p.author,source.user.login);
  assert.equal(p.headRefOid,source.head.sha);
  assert.equal(p.baseRefOid,source.base.sha);
  assert.equal(p.mergedAt,source.merged_at);
  assert.equal(p.createdAt,source.created_at);
  assert.equal(p.url,source.html_url);
});
test('deleted PR branches survive and repeated head branches retain every PR', () => {
  const map=build({branches:['main']});
  assert.equal(map.pull_requests.length,raw.length);
  assert.deepEqual(map.neural_network.nodes.find(n=>n.id===prs.find(p=>p.number===3).headRefName).pr_numbers,[3,5]);
  assert.ok(edge(map,9));
});
test('fork head names do not collapse into same-repository branch names', () => {
  const external=normalizePR({...raw[0],number:99,head:{...raw[0].head,repo:{full_name:'external/repo'}}});
  const map=build({prData:[...prs,external]});
  assert.equal(edge(map,99).to,`external/repo:${external.headRefName}`);
});
test('fork and deleted-head classification uses the original branch ref', () => {
  for (const repository of [{full_name:'external/repo'}, null]) {
    for (const [ref,type,layer] of [['feature/work','feature','L5'],['fix/work','hotfix','L4'],['copilot/work','cognitive','L6']]) {
      const external=normalizePR({...raw[0],number:99,head:{...raw[0].head,ref,repo:repository}});
      const map=build({prData:[external]});
      const node=map.neural_network.nodes.find(n=>n.pr_numbers?.includes(99));
      assert.equal(node.type,type); assert.equal(node.layer,layer);
      assert.notEqual(node.id,ref);
    }
  }
});
test('malformed historical identities fail closed without mutating either input', () => {
  const {createHash}=require('node:crypto');
  const snapshot=build(), sha256=createHash('sha256').update(JSON.stringify(snapshot)).digest('hex');
  for (const bad of [null, {}, {snapshot}, {sha256:'',snapshot}, {sha256:'bad',snapshot},
    {sha256:'0'.repeat(64),snapshot}, {sha256,snapshot:{...snapshot,history:[]}}]) {
    for (const location of ['current','incoming']) {
      const current=build(), incoming=build();
      (location==='current'?current:incoming).history=[bad,bad];
      const before=JSON.stringify([current,incoming]);
      assert.throws(()=>mergeNeuralHistory(current,[incoming]),/Invalid neural history identity/);
      assert.equal(JSON.stringify([current,incoming]),before);
    }
  }
});
test('conflicting identity metadata fails closed; identical duplicates are idempotent', () => {
  const archived=mergeNeuralHistory(build(),[build()]);
  const duplicate=structuredClone(archived);
  duplicate.history[0].original_source='conflicting metadata';
  assert.throws(()=>mergeNeuralHistory(archived,[duplicate]),/Conflicting neural history identity/);
  assert.deepEqual(mergeNeuralHistory(archived,[archived]),archived);
});
test('existing observation metadata survives when the same snapshot is archived again', () => {
  const snapshot=build(), current=mergeNeuralHistory(build(),[snapshot]);
  current.history[0].original_source='preserved evidence';
  assert.deepEqual(mergeNeuralHistory(current,[snapshot]),current);
});
test('PR 16 conflict resolution preserves main effective observation and both original snapshots', () => {
  const fs=require('node:fs'),{createHash}=require('node:crypto');
  const sources=[
    ['bf4569431afaf9e5b64facdddcda0d0879dbc999','a6a9252c064ea741dbfb0461882853af1561cc7853d9ad741d3fe078b3704ea8'],
    ['9016d4c7cdca4e17a45889ebed4eb7cb45fe1fce','41969a7313cf38de657da156ea11baf72e1a06254015fdeff24f16f2092d88d9']
  ].map(([commit,expected])=>{
    const bytes=fs.readFileSync(`neural-links/history/${commit}.branch-map.json`);
    assert.equal(createHash('sha256').update(bytes).digest('hex'),expected);
    return JSON.parse(bytes);
  });
  const resolved=mergeNeuralHistory(sources[0],sources);
  const {history,...effective}=resolved,{history:oldHistory,...mainEffective}=sources[0];
  assert.deepEqual(effective,mainEffective);
  assert.equal(history.length,12);
  for (const source of sources) {
    for (const entry of source.history) assert.deepEqual(history.find(e=>e.sha256===entry.sha256),entry);
    const {history:ignored,...payload}=source;
    assert.ok(history.some(e=>JSON.stringify(e.snapshot)===JSON.stringify(payload)));
  }
  assert.equal(pr(resolved,9).main_integration,'not_in_main');
  assert.equal(pr(resolved,15).mergeCommit,'d16872f594b62b896d57fedc7bc2830cf8961ac9');
  assert.equal(pr(resolved,16).baseRefName,'main');
  assert.equal(pr(resolved,16).mergeCommit,null);
  assert.equal(pr(resolved,16).main_integration,'not_established');
  const map=JSON.parse(fs.readFileSync('neural-links/branch-map.json','utf8'));
  for (const entry of resolved.history) assert.deepEqual(map.history.find(e=>e.sha256===entry.sha256),entry);
});
test('unassociated branches get no fabricated main parent or edge', () => {
  const map=build();
  assert.equal(map.neural_network.nodes.find(n=>n.id==='unassociated').parent,null);
  assert.ok(!map.neural_network.synapses.some(e=>e.to==='unassociated'));
});
test('closed unmerged PR is not a merge; test merge SHA is discarded', () => {
  const closed=normalizePR({...raw[0],state:'closed',merged_at:null});
  const map=build({prData:[closed]});
  assert.equal(edge(map,closed.number).type,'closed_pr');
  assert.equal(pr(map,closed.number).mergeCommit,null);
});
test('API pagination is complete and failures/invalid evidence propagate', () => {
  const result=getPRData((cmd,args)=>{
    assert.equal(cmd,'gh'); assert.ok(args.includes('--paginate')); assert.ok(args.includes('--slurp'));
    return JSON.stringify([raw.slice(0,2),raw.slice(2)]);
  });
  assert.equal(result.length,raw.length);
  assert.throws(()=>getPRData(()=>{throw new Error('auth unavailable')}),/auth unavailable/);
  assert.throws(()=>getPRData(()=>JSON.stringify({error:'denied'})));
  assert.throws(()=>normalizePR({...raw[0],base:{}}));
  assert.throws(()=>normalizePR({...raw.find(p=>p.number===9),merge_commit_sha:null}));
});
test('wrong old PR 9 main edge remains archived, never returns as effective lineage', () => {
  const old=require('../neural-links/history/0bf3a9f9eff42c49b87985997bde7195795a242b.branch-map.json');
  const original=JSON.stringify(old);
  const map=mergeNeuralHistory(build(),[old]);
  assert.ok(old.neural_network.synapses.some(e=>e.from==='main'&&e.pr_number===9));
  assert.ok(!map.neural_network.synapses.some(e=>e.from==='main'&&e.pr_number===9));
  assert.equal(map.history[0].snapshot.updated_at,old.updated_at);
  assert.deepEqual(map.history[0].snapshot,old);
  assert.equal(JSON.stringify(old),original);
  assert.deepEqual(mergeNeuralHistory(map,[old]),map);
});
test('all snapshot generations survive regeneration without recursive duplication', () => {
  const old=require('../neural-links/history/0bf3a9f9eff42c49b87985997bde7195795a242b.branch-map.json');
  const once=mergeNeuralHistory(build(),[old]);
  const twice=mergeNeuralHistory(build({observedAt:'2026-10-17T19:00:00Z'}),[once,old]);
  assert.equal(twice.history.length,2);
  assert.ok(twice.history.every(e=>!e.snapshot.history));
  assert.ok(twice.history.some(e=>e.snapshot.updated_at===old.updated_at));
});
test('missing commit or main ref stays unknown and ancestry exit 1 means not contained', () => {
  assert.equal(mainContains('abc',()=>{throw Object.assign(new Error(),{status:128})}),null);
  assert.equal(mainContains('abc',(cmd,args)=>{if(args[0]==='merge-base')throw Object.assign(new Error(),{status:1});}),false);
  assert.equal(mainContains('abc',()=>''),true);
});
test('checked-in graph is reproducible from pinned GitHub observations and keeps both snapshots', () => {
  const fs=require('node:fs');
  const {generateMermaidGraph}=require('../scripts/generate-mermaid.js');
  const map=JSON.parse(fs.readFileSync('neural-links/branch-map.json','utf8'));
  const proof=require('./fixtures/mrl-neural-ancestry-20261017.json');
  const generated=build({branches:proof.branches.map(b=>b.name), observedAt:proof.observed_at,
    sourceCommit:proof.main_commit,
    mainContains:sha=>proof.merge_commit_ancestry.find(p=>p.merge_commit===sha)?.main_contains??null});
  generated.observation_source='tests/fixtures/mrl-neural-ancestry-20261017.json';
  // Rehydrate complete archived observations; current PR evidence always wins.
  const originals=map.history.map(e=>e.snapshot).filter(s=>s.updated_at === '2026-10-17T11:47:23.671Z' || s.updated_at.startsWith('2026-10-17T14:41:'));
  const rebuilt=mergeNeuralHistory(generated,originals);
  const pinned=map.updated_at === proof.observed_at ? map
    : map.history.find(e=>e.snapshot.updated_at === proof.observed_at)?.snapshot;
  assert.ok(pinned, 'original corrected observation must remain available');
  assert.deepEqual(rebuilt.neural_network,pinned.neural_network);
  assert.deepEqual(rebuilt.pull_requests,pinned.pull_requests);
  assert.equal(fs.readFileSync('neural-links/synaptic-graph.mermaid','utf8').trimEnd(),generateMermaidGraph(map).trimEnd());
  assert.ok(map.history.some(e=>e.snapshot.updated_at==='2026-10-17T11:47:23.671Z'));
  assert.ok(map.history.some(e=>e.snapshot.updated_at.startsWith('2026-10-17T14:41:')));
});
