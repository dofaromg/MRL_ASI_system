// origin_signature: MrLiouWord
const fs = require('fs');
const { execSync, execFileSync } = require('child_process');
const { createHash } = require('crypto');

// 獲取所有分支
function getAllBranches() {
  try {
    const branches = execSync('git branch -a', { encoding: 'utf-8' })
      .split('\n')
      .map(b => b.trim().replace('* ', '').replace('remotes/origin/', ''))
      .filter(b => b && !b.includes('HEAD') && !b.includes('->'));
    
    // 去重
    return [...new Set(branches)];
  } catch (error) {
    console.error('Error getting branches:', error.message);
    throw error;
  }
}

// Paginate the complete PR collection. API/auth failures abort before writing.
// REST base.ref/head.ref are GitHub's baseRefName/headRefName equivalents.
function getPRData(run = execFileSync) {
  const pages = JSON.parse(run('gh', ['api', '--paginate', '--slurp',
    'repos/{owner}/{repo}/pulls?state=all&per_page=100'], {encoding: 'utf-8', maxBuffer:64 * 1024 * 1024}));
  if (!Array.isArray(pages) || pages.some(page => !Array.isArray(page))) {
    throw new Error('Incomplete PR collection');
  }
  return pages.flat().map(normalizePR);
}

function normalizePR(pr) {
  if (!pr.base?.ref || !pr.head?.ref || !pr.base?.repo?.full_name ||
      !pr.number || !['open', 'closed'].includes(pr.state)) {
    throw new Error('Invalid GitHub PR evidence');
  }
  const merged = !!pr.merged_at;
  if (merged && !pr.merge_commit_sha) throw new Error('Merged PR lacks merge commit');
  return {
    number: pr.number, title: pr.title, author: pr.user?.login ?? null,
    url: pr.html_url, baseRefName: pr.base.ref, headRefName: pr.head.ref,
    baseRepository: pr.base.repo.full_name,
    headRepository: pr.head.repo?.full_name ?? null,
    baseRefOid: pr.base.sha, headRefOid: pr.head.sha,
    state: merged ? 'MERGED' : pr.state.toUpperCase(),
    createdAt: pr.created_at, updatedAt: pr.updated_at, mergedAt: pr.merged_at,
    // An open PR's merge_commit_sha is a TEST merge, never a real merge.
    mergeCommit: merged ? pr.merge_commit_sha : null
  };
}

function headId(pr) {
  // Forks with identical branch names must not collapse into a local node.
  return pr.headRepository && pr.headRepository !== pr.baseRepository
    ? `${pr.headRepository}:${pr.headRefName}`
    : pr.headRepository ? pr.headRefName : `deleted-head:pr-${pr.number}:${pr.headRefName}`;
}

function mainContains(sha, run = execFileSync) {
  try {
    run('git', ['cat-file', '-e', `${sha}^{commit}`], {stdio: 'pipe'});
    run('git', ['rev-parse', '--verify', 'refs/remotes/origin/main'], {stdio: 'pipe'});
  } catch {
    return null;
  }
  try {
    run('git', ['merge-base', '--is-ancestor', sha, 'refs/remotes/origin/main'], {stdio: 'pipe'});
    return true;
  } catch (error) {
    return error.status === 1 ? false : null;
  }
}

// parent means observed PR target, not an inferred Git branch creation point.
function buildNeuralNetwork(options = {}) {
  const branches = options.branches ?? getAllBranches();
  const prData = options.prData ?? getPRData();
  const observedAt = options.observedAt ?? new Date().toISOString();
  const contains = options.mainContains ?? mainContains;
  const ids = new Set(['main', ...branches]);
  for (const pr of prData) { ids.add(pr.baseRefName); ids.add(headId(pr)); }
  const nodes = [...ids].sort().map(id => {
    const prs = prData.filter(pr => headId(pr) === id)
      .sort((a, b) => a.number - b.number);
    const latest = prs.at(-1);
    const parents = [...new Set(prs.map(pr => pr.baseRefName))];
    return id === 'main'
      ? {id, type:'trunk', layer:'L7', frequency_hz:164.88, status:'active', energy:1}
      : {id, type:getBranchType(id), layer:getBranchLayer(id),
          parent:parents.length === 1 ? parents[0] : null, parents,
          parent_semantics:'PR target; not branch creation ancestry',
          status:latest?.state === 'MERGED' ? 'merged' : latest?.state === 'CLOSED' ? 'closed' : 'active',
          energy:latest?.state === 'MERGED' ? 0.95 : 0.7,
          pr_numbers:prs.map(pr => pr.number),
          ...(latest ? {created_at:latest.createdAt, ...(latest.mergedAt ? {merged_at:latest.mergedAt, merged_pr:latest.number} : {})} : {})};
  });
  const pull_requests = [...prData].sort((a,b) => a.number-b.number).map(pr => {
    const included = pr.state === 'MERGED' ? contains(pr.mergeCommit) : null;
    return {...pr, observed_at:observedAt,
      branch_merge:pr.state === 'MERGED' ? 'merged' : 'not_merged',
      main_integration:pr.state !== 'MERGED' ? 'not_established'
        : included === true ? 'confirmed' : included === false ? 'not_in_main' : 'unknown',
      deployment:'not_verified'};
  });
  return {origin_signature:'MrLiouWord', schema_version:2, updated_at:observedAt,
    source_commit:options.sourceCommit ?? execFileSync('git', ['rev-parse','HEAD'], {encoding:'utf-8'}).trim(),
    pull_requests,
    neural_network:{nodes, synapses:pull_requests.map(pr => ({
      from:pr.baseRefName, to:headId(pr),
      type:pr.state === 'MERGED' ? 'merge' : pr.state === 'CLOSED' ? 'closed_pr' : 'influence',
      weight:pr.state === 'MERGED' ? 0.95 : 0.5, pr_number:pr.number,
      merge_commit:pr.mergeCommit, head_commit:pr.headRefOid, base_commit:pr.baseRefOid,
      timestamp:pr.mergedAt || pr.createdAt, observed_at:observedAt,
      evidence:'github_pr', main_integration:pr.main_integration, deployment:pr.deployment
    }))}};
}

// 判斷分支類型
function getBranchType(branch) {
  if (branch.startsWith('copilot/')) return 'cognitive';
  if (branch.startsWith('feature/')) return 'feature';
  if (branch.startsWith('hotfix/')) return 'hotfix';
  if (branch.startsWith('fix/')) return 'hotfix';
  if (branch.startsWith('experimental/')) return 'experimental';
  return 'experimental';
}

// 判斷分支圖層
function getBranchLayer(branch) {
  const typeLayerMap = {
    'cognitive': 'L6',
    'feature': 'L5',
    'hotfix': 'L4',
    'experimental': 'L3'
  };
  return typeLayerMap[getBranchType(branch)] || 'L3';
}

// Preserve prior observations without treating absent branches as deleted history.
function mergeNeuralHistory(current, snapshots) {
  const result = JSON.parse(JSON.stringify(current));
  if (result.schema_version === 2) {
    const observations = new Map((result.history ?? []).map(entry => [entry.sha256, entry]));
    const liveIds = new Set(result.neural_network.nodes.map(n => n.id));
    for (const snapshot of snapshots) {
      if (snapshot.origin_signature !== result.origin_signature ||
          !Array.isArray(snapshot.neural_network?.nodes) ||
          !Array.isArray(snapshot.neural_network?.synapses)) {
        throw new Error('Invalid or foreign neural history; refusing replacement');
      }
      const snapshotIds = new Set(snapshot.neural_network.nodes.map(n => n.id));
      if (snapshot.neural_network.synapses.some(e => !snapshotIds.has(e.from) || !snapshotIds.has(e.to))) {
        throw new Error('Historical edge has a missing endpoint');
      }
      for (const entry of snapshot.history ?? []) observations.set(entry.sha256, entry);
      // Avoid recursive copies and exponential growth across regeneration.
      const {history, ...payload} = snapshot;
      const sha256 = createHash('sha256').update(JSON.stringify(payload)).digest('hex');
      observations.set(sha256, {sha256, snapshot:payload});
      for (const node of snapshot.neural_network.nodes) {
        if (!liveIds.has(node.id)) {
          liveIds.add(node.id);
          result.neural_network.nodes.push({...node, parent:null, parents:[],
            status:'unknown', historical_only:true});
        }
      }
    }
    result.history = [...observations.values()];
    return result;
  }
  const nodes = new Map(result.neural_network.nodes.map(n => [n.id, n]));
  const edgeKey = e => JSON.stringify([e.from, e.to, e.type]);
  const edges = new Set(result.neural_network.synapses.map(edgeKey));
  for (const snapshot of snapshots) {
    if (snapshot.origin_signature !== result.origin_signature ||
        !Array.isArray(snapshot.neural_network?.nodes) ||
        !Array.isArray(snapshot.neural_network?.synapses)) {
      throw new Error('Invalid or foreign neural history; refusing replacement');
    }
    for (const node of snapshot.neural_network.nodes) {
      if (!nodes.has(node.id)) {
        const preserved = {...node, historical_only: true};
        nodes.set(node.id, preserved);
        result.neural_network.nodes.push(preserved);
      }
    }
    for (const edge of snapshot.neural_network.synapses) {
      if (!edges.has(edgeKey(edge))) {
        if (!nodes.has(edge.from) || !nodes.has(edge.to)) {
          throw new Error('Historical edge has a missing endpoint');
        }
        edges.add(edgeKey(edge));
        result.neural_network.synapses.push({...edge, historical_only: true});
      }
    }
  }
  return result;
}

function loadNeuralHistory() {
  const snapshots = [];
  const path = 'neural-links/branch-map.json';
  if (fs.existsSync(path)) snapshots.push(JSON.parse(fs.readFileSync(path, 'utf-8')));
  let hasMain = false;
  try {
    execSync('git rev-parse --verify refs/remotes/origin/main', {stdio: 'pipe'});
    hasMain = true;
  } catch {
    console.warn('No origin/main reference; preserving available local history only.');
  }
  if (hasMain) {
    // Failure to read a known baseline must not silently discard its history.
    snapshots.push(JSON.parse(execSync('git show refs/remotes/origin/main:neural-links/branch-map.json',
      {encoding: 'utf-8', stdio: ['ignore', 'pipe', 'pipe']})));
  }
  return snapshots;
}

// 主程序
function main() {
  console.log('🧠 Starting neural network update...');
  
  const network = mergeNeuralHistory(buildNeuralNetwork(), loadNeuralHistory());
  
  // 確保目錄存在
  if (!fs.existsSync('neural-links')) {
    fs.mkdirSync('neural-links', { recursive: true });
  }
  
  // 寫入檔案
  fs.writeFileSync(
    'neural-links/branch-map.json',
    JSON.stringify(network, null, 2)
  );
  
  console.log(`✅ Neural network updated: ${network.neural_network.nodes.length} nodes, ${network.neural_network.synapses.length} synapses`);
  console.log(`📊 Active nodes: ${network.neural_network.nodes.filter(n => n.status === 'active').length}`);
  console.log(`✔️  Merged nodes: ${network.neural_network.nodes.filter(n => n.status === 'merged').length}`);
  
  return network;
}

// 執行主程序
if (require.main === module) {
  try {
    main();
  } catch (error) {
    console.error('❌ Error updating neural network:', error.message);
    process.exit(1);
  }
}

module.exports = { getPRData, normalizePR, mainContains, headId, buildNeuralNetwork, getBranchType, getBranchLayer, mergeNeuralHistory, loadNeuralHistory };
