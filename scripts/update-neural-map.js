// origin_signature: MrLiouWord
const fs = require('fs');
const { execSync } = require('child_process');

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
    return ['main'];
  }
}

// 獲取 PR 資訊
function getPRData() {
  try {
    // 檢查 gh CLI 是否可用
    execSync('gh --version', { encoding: 'utf-8' });
    
    const prData = JSON.parse(
      execSync('gh pr list --state all --json number,title,headRefName,state,mergedAt,createdAt --limit 500', 
        { encoding: 'utf-8' })
    );
    return prData;
  } catch (error) {
    console.warn('Warning: gh CLI not available or no PRs found:', error.message);
    return [];
  }
}

// 建立神經網絡
function buildNeuralNetwork() {
  const branches = getAllBranches();
  const prData = getPRData();
  
  const neuralNetwork = {
    origin_signature: "MrLiouWord",
    updated_at: new Date().toISOString(),
    neural_network: {
      nodes: [],
      synapses: []
    }
  };
  
  // 主幹節點
  neuralNetwork.neural_network.nodes.push({
    id: "main",
    type: "trunk",
    layer: "L7",
    frequency_hz: 164.88,
    status: "active",
    energy: 1.0
  });
  
  // 處理每個分支
  branches.forEach(branch => {
    if (branch === 'main') return;
    
    const pr = prData.find(p => p.headRefName === branch);
    
    const node = {
      id: branch,
      type: getBranchType(branch),
      layer: getBranchLayer(branch),
      parent: "main",
      status: pr?.state === "MERGED" ? "merged" : "active",
      energy: pr?.state === "MERGED" ? 0.95 : 0.7
    };
    
    if (pr) {
      node.merged_pr = pr.number;
      node.created_at = pr.createdAt;
      if (pr.mergedAt) {
        node.merged_at = pr.mergedAt;
      }
    }
    
    neuralNetwork.neural_network.nodes.push(node);
    
    // 建立突觸
    neuralNetwork.neural_network.synapses.push({
      from: "main",
      to: branch,
      type: pr?.state === "MERGED" ? "merge" : "influence",
      weight: pr?.state === "MERGED" ? 0.95 : 0.5,
      pr_number: pr?.number,
      timestamp: pr?.mergedAt || pr?.createdAt || new Date().toISOString()
    });
  });
  
  return neuralNetwork;
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

module.exports = { buildNeuralNetwork, getBranchType, getBranchLayer, mergeNeuralHistory, loadNeuralHistory };
