/**
 * METACODE - 元代碼核心實現
 * 
 * 這是一個自我描述、自我執行、自我演化的代碼系統
 * 整合：MRLsmall + MetaEnv + Particle Evolution + Provenance
 * 
 * @author Mr. Liou Yu Lin & Claude
 * @version 2.0.0-alpha
 */

import crypto from 'crypto';

// ===== 元代碼核心類 =====
class MetaCode {
  constructor() {
    this.id = this.generateId();
    this.version = '2.0.0-alpha';
    this.created_at = new Date().toISOString();
    this.self = this.describe();
    this.particles = new Map();
    this.links = new Map();
    this.cycles = [];
    this.journal = [];
  }

  // 生成唯一ID
  generateId() {
    const timestamp = new Date().toISOString();
    const random = crypto.randomBytes(4).toString('hex');
    return `meta:${timestamp}:${random}`;
  }

  // 自我描述
  describe() {
    return {
      type: 'MetaCode',
      id: this.id,
      capabilities: [
        'self-describe',    // 自我描述
        'self-execute',     // 自我執行
        'self-evolve',      // 自我演化
        'self-verify',      // 自我驗證
        'cross-domain'      // 跨域連結
      ],
      structure: {
        particles: 'MRLsmall units',
        links: 'Relationship graph',
        cycles: 'Evolution history',
        journal: 'Event log'
      }
    };
  }

  // ===== MRLsmall 粒子創建 =====
  createParticle(data) {
    const particle = {
      id: `p:${new Date().toISOString()}:${crypto.randomBytes(4).toString('hex')}`,
      type: 'MRLsmall',
      stamp: {
        t: new Date().toISOString(),
        tz: '+08:00'
      },
      
      // 能力容量
      cap: {
        mag: data.mag || 1.0,
        axes: {
          zoom: data.zoom || 0.5,
          surprisal: data.surprisal || 0.5,
          conf: data.conf || 0.8,
          gran_meso: data.gran_meso || 1.0,
          gran_micro: data.gran_micro || 0.0,
          gran_macro: data.gran_macro || 0.0
        },
        embed: data.embed || this.generateEmbedding()
      },
      
      // 正規化
      norm: {
        scale: data.scale || 'minmax',
        window: data.window || 128
      },
      
      // 分類器
      classifier: {
        metric: 'cosine',
        w: {
          zoom: 1.2,
          surprisal: 1.0,
          conf: 1.1,
          gran_meso: 0.8
        },
        tau_match: 0.92,
        tau_border: 0.80,
        constraints: ['cap.mag > 0']
      },
      
      // 放大公式
      amplify: {
        formula: 'P_{k+1} = N_k · P_k · η_k',
        N: data.N || null,
        eta: data.eta || null,
        present: null,
        ratio: null
      },
      
      // 關聯與標籤
      links: [],
      tags: data.tags || ['spawn-enabled'],
      
      // 追蹤來源
      trace: {
        src: data.src || 'metacode',
        domain: data.domain || 'unknown'
      }
    };

    // 計算 present 和 ratio
    if (particle.amplify.N && particle.amplify.eta) {
      particle.amplify.present = particle.cap.mag * particle.amplify.N * particle.amplify.eta;
      particle.amplify.ratio = particle.amplify.present;
    }

    this.particles.set(particle.id, particle);
    
    // 記錄事件
    this.logEvent('particle.create', {
      particle_id: particle.id,
      domain: particle.trace.domain
    });

    return particle;
  }

  // 生成嵌入向量
  generateEmbedding(dim = 8) {
    return Array.from({ length: dim }, () => 
      Math.random() * 2 - 1
    );
  }

  // ===== 一致性匹配 =====
  matchParticle(candidate) {
    let bestMatch = null;
    let bestScore = -Infinity;

    // 遍歷所有粒子
    for (const [pid, particle] of this.particles) {
      if (pid === candidate.id) continue;

      const score = this.calculateSimilarity(candidate, particle);

      if (score > bestScore) {
        bestScore = score;
        bestMatch = particle;
      }
    }

    // 決策
    let decision, reason;
    if (bestScore >= candidate.classifier.tau_match) {
      decision = 'bind';
      reason = 'consistent';
    } else if (bestScore >= candidate.classifier.tau_border) {
      decision = 'border';
      reason = 'review-needed';
    } else {
      decision = 'spawn';
      reason = this.analyzeSpawnReason(candidate, bestMatch, bestScore);
    }

    const result = {
      candidate: candidate.id,
      best_match: bestMatch?.id,
      score: bestScore,
      decision,
      reason,
      tau_match: candidate.classifier.tau_match,
      tau_border: candidate.classifier.tau_border
    };

    // 記錄
    this.logEvent('particle.match', result);

    return result;
  }

  // 計算相似度（加權歐氏距離）
  calculateSimilarity(p1, p2) {
    const w = p1.classifier.w;
    const axes1 = p1.cap.axes;
    const axes2 = p2.cap.axes;

    let weightedDist = 0;
    let totalWeight = 0;

    for (const key in w) {
      if (axes1[key] !== undefined && axes2[key] !== undefined) {
        const diff = Math.abs(axes1[key] - axes2[key]);
        weightedDist += w[key] * diff;
        totalWeight += w[key];
      }
    }

    // 正規化並轉為相似度（1 - 距離）
    const normalizedDist = totalWeight > 0 ? weightedDist / totalWeight : 1;
    return 1 - normalizedDist;
  }

  // 分析 spawn 原因
  analyzeSpawnReason(candidate, bestMatch, score) {
    if (!bestMatch) return 'new-class';
    
    // 檢查尺度差異
    const zoomDiff = Math.abs(candidate.cap.axes.zoom - bestMatch.cap.axes.zoom);
    if (zoomDiff > 0.3) return 'scale-mismatch';

    // 檢查信度
    if (candidate.cap.axes.conf < 0.5) return 'noise';

    // 檢查結構不變量
    if (!this.checkInvariants(candidate)) return 'transform-error';

    return 'new-class';
  }

  // 檢查不變量
  checkInvariants(particle) {
    // 1. 單調性：放大不減能力
    if (particle.amplify.N && particle.amplify.eta) {
      if (particle.amplify.present < particle.cap.mag) {
        return false;
      }
    }

    // 2. η 邊界：效率在 (0, 1]
    if (particle.amplify.eta !== null) {
      if (particle.amplify.eta <= 0 || particle.amplify.eta > 1) {
        return false;
      }
    }

    // 3. mag 正值
    if (particle.cap.mag <= 0) {
      return false;
    }

    return true;
  }

  // ===== 粒子演化 =====
  evolveParticle(particleId, params = {}) {
    const particle = this.particles.get(particleId);
    if (!particle) throw new Error(`Particle ${particleId} not found`);

    const N = params.N || Math.floor(Math.random() * 100) + 50;
    const eta = params.eta || 0.7 + Math.random() * 0.3;

    // 應用放大公式
    const Pk = particle.cap.mag;
    const present = Pk * N * eta;
    const ratio = present / Pk;

    // 更新粒子
    particle.amplify.N = N;
    particle.amplify.eta = eta;
    particle.amplify.present = present;
    particle.amplify.ratio = ratio;

    // 記錄演化週期
    const cycle = {
      t: new Date().toISOString(),
      id: particleId,
      Pk,
      N,
      eta,
      present,
      ratio
    };

    this.cycles.push(cycle);

    // 記錄事件
    this.logEvent('particle.evolve', cycle);

    return cycle;
  }

  // ===== 關聯建立 =====
  createLink(fromId, toId, relation) {
    const link = {
      from: fromId,
      to: toId,
      rel: relation,
      created_at: new Date().toISOString()
    };

    const linkId = `link:${fromId}:${toId}:${relation}`;
    this.links.set(linkId, link);

    // 更新粒子的 links 欄位
    const fromParticle = this.particles.get(fromId);
    const toParticle = this.particles.get(toId);

    if (fromParticle) {
      fromParticle.links.push({ rel: relation, to: toId });
    }

    if (toParticle) {
      toParticle.links.push({ rel: `inverse-${relation}`, to: fromId });
    }

    this.logEvent('link.create', link);

    return link;
  }

  // ===== 一致性傳播 =====
  propagate(particleId) {
    const particle = this.particles.get(particleId);
    if (!particle) return [];

    const affected = [];

    // 遍歷所有依賴此粒子的關聯
    for (const [linkId, link] of this.links) {
      if (link.from === particleId) {
        const targetParticle = this.particles.get(link.to);
        if (targetParticle) {
          // 重新計算目標粒子
          this.evolveParticle(link.to, {
            N: particle.amplify.N,
            eta: particle.amplify.eta * 0.95 // 傳播時有 5% 損失
          });
          affected.push(link.to);
        }
      }
    }

    this.logEvent('propagate', {
      source: particleId,
      affected: affected.length
    });

    return affected;
  }

  // ===== 事件日誌 =====
  logEvent(event, data) {
    const entry = {
      t: new Date().toISOString(),
      evt: event,
      data
    };

    this.journal.push(entry);
  }

  // ===== 計算指標 =====
  calculateMetrics() {
    const totalParticles = this.particles.size;
    
    // 計算 bind/border/spawn 比例
    const decisions = this.journal
      .filter(e => e.evt === 'particle.match')
      .map(e => e.data.decision);

    const bindCount = decisions.filter(d => d === 'bind').length;
    const borderCount = decisions.filter(d => d === 'border').length;
    const spawnCount = decisions.filter(d => d === 'spawn').length;

    const coverage = totalParticles > 0 ? bindCount / totalParticles : 0;
    const spawnRate = totalParticles > 0 ? spawnCount / totalParticles : 0;

    // 計算平均 η
    const etas = Array.from(this.particles.values())
      .filter(p => p.amplify.eta !== null)
      .map(p => p.amplify.eta);

    const avgEta = etas.length > 0 
      ? etas.reduce((a, b) => a + b, 0) / etas.length 
      : 0;

    return {
      total_particles: totalParticles,
      total_links: this.links.size,
      total_cycles: this.cycles.length,
      coverage,
      spawn_rate: spawnRate,
      border_count: borderCount,
      avg_eta: avgEta,
      domains: this.getDomains()
    };
  }

  // 獲取所有域
  getDomains() {
    const domains = new Set();
    for (const particle of this.particles.values()) {
      domains.add(particle.trace.domain);
    }
    return Array.from(domains);
  }

  // ===== 自我驗證 =====
  verify() {
    const errors = [];

    // 檢查所有粒子
    for (const [pid, particle] of this.particles) {
      // 檢查不變量
      if (!this.checkInvariants(particle)) {
        errors.push({
          type: 'invariant-violation',
          particle_id: pid,
          message: 'Particle violates invariants'
        });
      }

      // 檢查 links 完整性
      for (const link of particle.links) {
        if (!this.particles.has(link.to)) {
          errors.push({
            type: 'broken-link',
            particle_id: pid,
            target: link.to,
            message: 'Link target not found'
          });
        }
      }
    }

    return {
      ok: errors.length === 0,
      errors,
      timestamp: new Date().toISOString()
    };
  }

  // ===== 導出為 JSON =====
  export() {
    return {
      meta: {
        id: this.id,
        version: this.version,
        created_at: this.created_at,
        exported_at: new Date().toISOString()
      },
      self: this.self,
      particles: Array.from(this.particles.values()),
      links: Array.from(this.links.values()),
      cycles: this.cycles,
      journal: this.journal,
      metrics: this.calculateMetrics()
    };
  }

  // ===== 從 JSON 導入 =====
  import(data) {
    // Validate a detached candidate before changing any current state.
    const invalid = () => { throw new Error('MRL_METACODE_IMPORT_INVALID'); };
    if (!data || !Array.isArray(data.particles) || !Array.isArray(data.links)) invalid();
    const candidate = structuredClone(data);
    const cycles = candidate.cycles ?? [];
    const journal = candidate.journal ?? [];
    if (!Array.isArray(cycles) || !Array.isArray(journal)) invalid();
    const particles = new Map();
    const links = new Map();
    const nonempty = value => typeof value === 'string' && value.length > 0;
    for (const particle of candidate.particles) {
      if (!particle || !nonempty(particle.id) || particles.has(particle.id) ||
          !particle.cap || !Number.isFinite(particle.cap.mag) ||
          !particle.amplify || !Array.isArray(particle.links) ||
          !this.checkInvariants(particle)) invalid();
      for (const value of ['N', 'eta', 'present', 'ratio'].map(k => particle.amplify[k])) {
        if (value !== null && !Number.isFinite(value)) invalid();
      }
      particles.set(particle.id, particle);
    }
    for (const particle of particles.values()) {
      for (const link of particle.links) {
        if (!link || !nonempty(link.rel) || !particles.has(link.to)) invalid();
      }
    }
    for (const link of candidate.links) {
      if (!link || !nonempty(link.rel) || !particles.has(link.from) || !particles.has(link.to)) invalid();
      const linkId = `link:${link.from}:${link.to}:${link.rel}`;
      if (links.has(linkId)) invalid();
      links.set(linkId, link);
    }
    let id = this.id;
    let version = this.version;
    let createdAt = this.created_at;
    let self = structuredClone(this.self);
    if (candidate.meta !== undefined) {
      const meta = candidate.meta;
      if (!meta || !nonempty(meta.id) || !nonempty(meta.version) ||
          !nonempty(meta.created_at) || !Number.isFinite(Date.parse(meta.created_at))) invalid();
      id = meta.id;
      version = meta.version;
      createdAt = meta.created_at;
      if (!candidate.self || candidate.self.id !== id || candidate.self.type !== 'MetaCode') invalid();
      self = candidate.self;
    } else if (candidate.self !== undefined) {
      // Legacy packets may omit both meta and self; never silently re-root them.
      if (!candidate.self || candidate.self.id !== id || candidate.self.type !== 'MetaCode') invalid();
      self = candidate.self;
    }
    const event = {
      t: new Date().toISOString(), evt: 'system.import',
      data: { particles: particles.size, links: links.size }
    };
    // Synchronous commit; no user callbacks or validation occur after it begins.
    this.id = id;
    this.version = version;
    this.created_at = createdAt;
    this.self = self;
    this.particles = particles;
    this.links = links;
    this.cycles = cycles;
    this.journal = [...journal, event];
  }

  // ===== 自我執行（演示） =====
  async selfExecute() {
    console.log('🌟 MetaCode Self-Execution Started\n');

    // 1. 創建跨域粒子
    console.log('📦 Creating cross-domain particles...');
    const mathParticle = this.createParticle({
      domain: 'math',
      mag: 1.0,
      zoom: 0.8,
      surprisal: 0.2,
      conf: 0.95,
      N: 100,
      eta: 0.9,
      tags: ['math', 'hausdorff']
    });

    const physicsParticle = this.createParticle({
      domain: 'physics',
      mag: 1.0,
      zoom: 0.75,
      surprisal: 0.3,
      conf: 0.9,
      N: 80,
      eta: 0.85,
      tags: ['physics', 'quantum']
    });

    const computeParticle = this.createParticle({
      domain: 'compute',
      mag: 1.0,
      zoom: 0.7,
      surprisal: 0.4,
      conf: 0.88,
      N: 120,
      eta: 0.8,
      tags: ['compute', 'cpu']
    });

    console.log(`✓ Created 3 particles\n`);

    // 2. 演化
    console.log('🔄 Evolving particles...');
    this.evolveParticle(mathParticle.id);
    this.evolveParticle(physicsParticle.id);
    this.evolveParticle(computeParticle.id);
    console.log(`✓ Evolution complete\n`);

    // 3. 建立關聯
    console.log('🔗 Creating links...');
    this.createLink(mathParticle.id, physicsParticle.id, 'theoretical-foundation');
    this.createLink(physicsParticle.id, computeParticle.id, 'implementation');
    console.log(`✓ Links established\n`);

    // 4. 創建候選粒子並匹配
    console.log('🔍 Matching new particle...');
    const candidate = this.createParticle({
      domain: 'math',
      mag: 1.0,
      zoom: 0.82,  // 接近 mathParticle
      surprisal: 0.22,
      conf: 0.93,
      tags: ['candidate']
    });

    const matchResult = this.matchParticle(candidate);
    console.log(`✓ Match result: ${matchResult.decision} (score: ${matchResult.score.toFixed(3)})\n`);

    // 5. 傳播變化
    console.log('📡 Propagating changes...');
    const affected = this.propagate(mathParticle.id);
    console.log(`✓ Affected ${affected.length} particles\n`);

    // 6. 自我驗證
    console.log('✅ Self-verification...');
    const verification = this.verify();
    console.log(`✓ Verification: ${verification.ok ? 'PASSED' : 'FAILED'}\n`);

    // 7. 指標
    console.log('📊 Metrics:');
    const metrics = this.calculateMetrics();
    console.log(`   Total Particles: ${metrics.total_particles}`);
    console.log(`   Total Links: ${metrics.total_links}`);
    console.log(`   Coverage: ${(metrics.coverage * 100).toFixed(2)}%`);
    console.log(`   Spawn Rate: ${(metrics.spawn_rate * 100).toFixed(2)}%`);
    console.log(`   Avg η: ${metrics.avg_eta.toFixed(3)}`);
    console.log(`   Domains: ${metrics.domains.join(', ')}\n`);

    console.log('✨ MetaCode Self-Execution Complete\n');

    return this.export();
  }
}

// ===== 導出 =====
export default MetaCode;

// ===== 使用示例 =====
if (import.meta.url === `file://${process.argv[1]}`) {
  const meta = new MetaCode();
  
  meta.selfExecute().then(result => {
    console.log('📄 Export Preview:');
    console.log(JSON.stringify(result.metrics, null, 2));
  });
}
