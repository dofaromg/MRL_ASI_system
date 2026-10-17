/**
 * FlowOS - Main class that orchestrates all FlowOS subsystems
 * This class provides the unified API for particles, personas, seeds, conversations, projects, artifacts, memory, and tools.
 */

import { FlowContext, FlowSnapshot, FlowLawResult, UUID } from './types';
import { ParticleEngine } from './core/particles';
import { ParticleStore } from './core/particles/store';
import { PersonaRegistry } from './core/personas';
import { SeedRegistry } from './core/seeds';
import { MerkleChain } from './core/chains';
import { ConversationManager } from './app/conversations';
import { ProjectRegistry } from './app/projects';
import { ArtifactVault } from './app/artifacts';
import { MemorySystem } from './app/memory';
import { ToolRegistry } from './app/tools';
import { CommercialLabelRegistry } from './app/commercial-labels';
import { MemoryStorage } from './storage';
import { FlowLaw } from './lib/flow-law';
import { ConfigManager } from './core/config';
import { FlowGate, GateDecision } from './core/gate';
import { NeuralLink, NeuralLinkPacket } from './core/neural_link';
import { randomId, now } from './utils';

export interface NeuralSignalResult {
  decision: GateDecision;
  packet?: NeuralLinkPacket;
}

export class FlowOS {
  private storage: MemoryStorage;
  public readonly config: ConfigManager;
  public readonly gate: FlowGate;
  public readonly neuralLink: NeuralLink;
  public readonly particles: ParticleEngine;
  public readonly personas: PersonaRegistry;
  public readonly seeds: SeedRegistry;
  public readonly chain: MerkleChain;
  public readonly conversations: ConversationManager;
  public readonly projects: ProjectRegistry;
  public readonly artifacts: ArtifactVault;
  public readonly memory: MemorySystem;
  public readonly tools: ToolRegistry;
  public readonly commercialLabels: CommercialLabelRegistry;
  private law: FlowLaw;

  constructor() {
    this.storage = new MemoryStorage();
    this.config = new ConfigManager();
    this.gate = new FlowGate();
    this.neuralLink = new NeuralLink();
    
    // Initialize core subsystems
    const particleStore = new ParticleStore(this.storage);
    this.particles = new ParticleEngine(particleStore);
    this.personas = new PersonaRegistry();
    this.seeds = new SeedRegistry();
    this.chain = new MerkleChain();
    
    // Initialize application subsystems
    this.conversations = new ConversationManager(this.storage);
    this.projects = new ProjectRegistry(this.storage);
    this.artifacts = new ArtifactVault(this.storage);
    this.memory = new MemorySystem(this.storage);
    this.tools = new ToolRegistry();
    this.commercialLabels = new CommercialLabelRegistry(this.storage);
    
    // Initialize governance
    this.law = new FlowLaw();
  }

  /**
   * Create a new FlowContext
   */
  createContext(options: Partial<FlowContext> = {}): FlowContext {
    return {
      id: randomId(),
      persona: options.persona,
      project: options.project,
      seed: options.seed,
      createdAt: now(),
      metadata: options.metadata,
    };
  }

  /**
   * Get a complete snapshot of the FlowOS state
   */
  snapshot(): FlowSnapshot {
    return this.storage.snapshot();
  }

  /**
   * Enforce FlowLaw across all particles
   */
  enforce(context?: FlowContext): FlowLawResult {
    const particles = this.particles.listParticles();
    return this.law.evaluate(particles, context, this.commercialLabels.listLabels());
  }

  async emitSignal(
    type: string,
    payload: Record<string, unknown>,
    context?: FlowContext,
  ): Promise<NeuralSignalResult> {
    const decision = this.gate.evaluate(payload, context);
    if (!decision.allowed) return { decision };
    const packet = await this.neuralLink.transmit(type, payload, context);
    return { decision, packet };
  }

  /**
   * Get system statistics
   */
  stats() {
    const snap = this.snapshot();
    return {
      particles: snap.particles.length,
      personas: snap.personas.length,
      seeds: snap.seeds.length,
      conversations: snap.conversations.length,
      projects: snap.projects.length,
      artifacts: snap.artifacts.length,
      commercialLabels: snap.commercialLabels.length,
      memories: snap.memories.length,
      tools: this.tools.listTools().length,
      chainDigest: this.chain.digest(),
    };
  }
}
