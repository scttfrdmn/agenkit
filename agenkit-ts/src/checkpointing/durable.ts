/**
 * Durable agent wrapper for automatic checkpointing.
 *
 * Wraps agents to provide automatic checkpointing, resume, and error recovery.
 */

import { Agent, Message } from '../core/interfaces';
import { CheckpointManager } from './manager';
import { FileCheckpointStorage } from './storage';
import { Checkpoint } from './checkpoint';

/**
 * Wrap agent with automatic checkpointing and resume capability.
 *
 * Features:
 * - Automatic checkpointing (every N steps or on demand)
 * - Resume from latest checkpoint on startup
 * - State persistence across restarts
 * - Error recovery with checkpoint rollback
 *
 * Example:
 *   import { DurableAgent } from 'agenkit';
 *
 *   // Create durable agent
 *   const durable = new DurableAgent({
 *     agent: myAgent,
 *     checkpointDir: './checkpoints',
 *     checkpointInterval: 10,  // Every 10 steps
 *   });
 *
 *   // Use agent (automatically checkpoints)
 *   const response = await durable.process(message, 'session-1');
 *
 *   // Resume from checkpoint
 *   const state = await durable.resume('session-1');
 */
export class DurableAgent implements Agent {
  private agent: Agent;
  private agentName: string;
  private checkpointInterval: number;
  private autoResume: boolean;
  private manager: CheckpointManager;

  // Track state per session
  private sessionState: Map<string, Record<string, unknown>> = new Map();
  private sessionSteps: Map<string, number> = new Map();
  private sessionMessages: Map<string, Message[]> = new Map();
  private sessionResumed: Map<string, boolean> = new Map();

  /**
   * Initialize durable agent.
   *
   * @param params - Configuration parameters
   * @param params.agent - Agent to wrap
   * @param params.checkpointDir - Directory for checkpoints (undefined = in-memory)
   * @param params.checkpointInterval - Checkpoint every N steps (default: 10)
   * @param params.autoResume - Automatically resume from latest checkpoint on first call (default: true)
   * @param params.agentName - Override agent name (defaults to agent.name)
   */
  constructor(params: {
    agent: Agent;
    checkpointDir?: string;
    checkpointInterval?: number;
    autoResume?: boolean;
    agentName?: string;
  }) {
    const {
      agent,
      checkpointDir,
      checkpointInterval = 10,
      autoResume = true,
      agentName,
    } = params;

    this.agent = agent;
    this.agentName = agentName || agent.name || 'agent';
    this.checkpointInterval = checkpointInterval;
    this.autoResume = autoResume;

    // Initialize checkpoint manager
    if (checkpointDir) {
      const storage = new FileCheckpointStorage(checkpointDir);
      this.manager = new CheckpointManager(storage, checkpointInterval);
    } else {
      this.manager = new CheckpointManager(undefined, checkpointInterval);
    }
  }

  /**
   * Get the agent name.
   */
  get name(): string {
    return this.agentName;
  }

  /**
   * Process message with automatic checkpointing.
   *
   * @param message - Input message
   * @param sessionId - Session identifier (default: 'default')
   * @returns Response message
   */
  async process(message: Message, sessionId: string = 'default'): Promise<Message> {
    // Auto-resume on first call if enabled
    if (this.autoResume && !this.sessionResumed.get(sessionId)) {
      await this.resume(sessionId);
      this.sessionResumed.set(sessionId, true);
    }

    // Initialize session if needed
    if (!this.sessionState.has(sessionId)) {
      this.sessionState.set(sessionId, {});
      this.sessionSteps.set(sessionId, 0);
      this.sessionMessages.set(sessionId, []);
    }

    // Increment step
    const currentStep = (this.sessionSteps.get(sessionId) || 0) + 1;
    this.sessionSteps.set(sessionId, currentStep);

    // Add message to history
    const messages = this.sessionMessages.get(sessionId)!;
    messages.push(message);

    try {
      // Process message
      const response = await this.agent.process(message);

      // Add response to history
      messages.push(response);

      // Update state
      this.updateState(sessionId, message, response);

      // Checkpoint if needed
      if (await this.manager.shouldCheckpoint(sessionId, currentStep)) {
        await this.checkpoint(sessionId);
      }

      return response;
    } catch (error) {
      console.error(`[DurableAgent] Error processing message at step ${currentStep}:`, error);

      // Try to rollback to last checkpoint
      const latest = await this.manager.getLatest(sessionId);
      if (latest) {
        console.log(
          `[DurableAgent] Rolling back to checkpoint at step ${latest.stepNumber}`,
        );
        await this.resume(sessionId, latest.checkpointId);
      }

      throw error;
    }
  }

  /**
   * Create checkpoint for current state.
   *
   * @param sessionId - Session identifier
   * @param metadata - Optional metadata to attach
   * @returns Unique checkpoint identifier
   */
  async checkpoint(sessionId: string, metadata?: Record<string, unknown>): Promise<string> {
    const currentStep = this.sessionSteps.get(sessionId) || 0;
    const state = this.sessionState.get(sessionId) || {};
    const messages = this.sessionMessages.get(sessionId) || [];

    const checkpointId = await this.manager.createCheckpoint({
      sessionId,
      agentName: this.agentName,
      stepNumber: currentStep,
      state,
      messages,
      metadata,
    });

    console.log(`[DurableAgent] Checkpointed session ${sessionId} at step ${currentStep}`);

    return checkpointId;
  }

  /**
   * Resume from checkpoint.
   *
   * @param sessionId - Session identifier
   * @param checkpointId - Specific checkpoint to resume from (undefined = latest)
   * @returns Restored state or undefined if no checkpoint found
   */
  async resume(
    sessionId: string,
    checkpointId?: string,
  ): Promise<Record<string, unknown> | undefined> {
    // Load checkpoint
    let checkpoint: Checkpoint | undefined;
    if (checkpointId) {
      checkpoint = await this.manager.loadCheckpoint(checkpointId);
    } else {
      checkpoint = await this.manager.getLatest(sessionId);
    }

    if (!checkpoint) {
      console.log(`[DurableAgent] No checkpoint found for ${sessionId}, starting fresh`);
      return undefined;
    }

    // Restore state
    this.sessionState.set(sessionId, { ...checkpoint.state });
    this.sessionSteps.set(sessionId, checkpoint.stepNumber);
    this.sessionMessages.set(sessionId, [...checkpoint.messages]);

    console.log(
      `[DurableAgent] Resumed session ${sessionId} from checkpoint at step ${checkpoint.stepNumber}`,
    );

    return checkpoint.state;
  }

  /**
   * Get current state for session.
   *
   * @param sessionId - Session identifier
   * @returns Copy of current state
   */
  async getState(sessionId: string): Promise<Record<string, unknown>> {
    const state = this.sessionState.get(sessionId) || {};
    return { ...state };
  }

  /**
   * Set state for session.
   *
   * @param sessionId - Session identifier
   * @param state - New state
   */
  async setState(sessionId: string, state: Record<string, unknown>): Promise<void> {
    this.sessionState.set(sessionId, { ...state });
  }

  /**
   * Get message history for session.
   *
   * @param sessionId - Session identifier
   * @returns Copy of message history
   */
  async getMessages(sessionId: string): Promise<Message[]> {
    const messages = this.sessionMessages.get(sessionId) || [];
    return [...messages];
  }

  /**
   * Reset session (clear state and messages).
   *
   * @param sessionId - Session identifier
   */
  async resetSession(sessionId: string): Promise<void> {
    this.sessionState.delete(sessionId);
    this.sessionSteps.delete(sessionId);
    this.sessionMessages.delete(sessionId);
    this.sessionResumed.delete(sessionId);
  }

  /**
   * Update session state (can be overridden for custom state tracking).
   *
   * Default implementation tracks message count and last message.
   * Override this to track custom state.
   *
   * @param sessionId - Session identifier
   * @param inputMessage - Input message
   * @param outputMessage - Output message
   */
  private updateState(sessionId: string, inputMessage: Message, outputMessage: Message): void {
    const state = this.sessionState.get(sessionId)!;

    // Update basic stats
    state.messageCount = (state.messageCount as number || 0) + 1;
    state.lastInput = inputMessage.content;
    state.lastOutput = outputMessage.content;

    // Track any metadata from response
    if (outputMessage.metadata) {
      state.lastMetadata = outputMessage.metadata;
    }
  }

  /**
   * List checkpoints for session.
   *
   * @param sessionId - Session identifier
   * @param limit - Optional limit on number of checkpoints
   * @returns List of checkpoints
   */
  async listCheckpoints(sessionId: string, limit?: number): Promise<Checkpoint[]> {
    return await this.manager.listCheckpoints(sessionId, limit);
  }

  /**
   * Delete all checkpoints for session.
   *
   * @param sessionId - Session identifier
   * @returns Number of checkpoints deleted
   */
  async deleteCheckpoints(sessionId: string): Promise<number> {
    const count = await this.manager.deleteSession(sessionId);
    await this.resetSession(sessionId);
    return count;
  }

  /**
   * Get statistics for session.
   *
   * @param sessionId - Session identifier
   * @returns Statistics object
   */
  async getSessionStats(sessionId: string): Promise<Record<string, unknown>> {
    const checkpointStats = await this.manager.getSessionStats(sessionId);

    return {
      ...checkpointStats,
      currentStep: this.sessionSteps.get(sessionId) || 0,
      messageCount: this.sessionMessages.get(sessionId)?.length || 0,
      stateSize: Object.keys(this.sessionState.get(sessionId) || {}).length,
    };
  }
}

/**
 * Convenience function to make an agent durable.
 *
 * @param agent - Agent to make durable
 * @param checkpointDir - Directory for checkpoints (default: './checkpoints')
 * @param checkpointInterval - Checkpoint every N steps (default: 10)
 * @param agentName - Override agent name
 * @returns DurableAgent wrapping the original agent
 *
 * Example:
 *   import { makeDurable } from 'agenkit';
 *
 *   // Make agent durable
 *   const durableAgent = makeDurable(
 *     myAgent,
 *     './checkpoints',
 *     5,
 *   );
 *
 *   // Use like normal agent
 *   const response = await durableAgent.process(message, 'session-1');
 */
export function makeDurable(
  agent: Agent,
  checkpointDir: string = './checkpoints',
  checkpointInterval: number = 10,
  agentName?: string,
): DurableAgent {
  return new DurableAgent({
    agent,
    checkpointDir,
    checkpointInterval,
    agentName,
  });
}
