/**
 * Checkpoint manager for high-level checkpoint operations.
 *
 * Provides operations like create, resume, replay, and time-travel debugging.
 */

import { v4 as uuidv4 } from 'uuid';
import { Checkpoint, CheckpointStorage } from './checkpoint';
import { InMemoryCheckpointStorage } from './storage';
import { Message } from '../core/interfaces';

/**
 * Manage checkpoints for long-running agents.
 *
 * Features:
 * - Create checkpoints at key points
 * - Resume from latest checkpoint
 * - Replay from specific checkpoint
 * - Time-travel debugging
 * - Automatic checkpoint creation (every N steps)
 *
 * Example:
 *   const manager = new CheckpointManager();
 *
 *   // Create checkpoint
 *   const checkpointId = await manager.createCheckpoint({
 *     sessionId: 'session-1',
 *     agentName: 'assistant',
 *     stepNumber: 10,
 *     state: { counter: 10, mode: 'active' },
 *     messages: conversationHistory,
 *   });
 *
 *   // Resume from latest
 *   const checkpoint = await manager.getLatest('session-1');
 *   const restoredState = checkpoint.state;
 */
export class CheckpointManager {
  private storage: CheckpointStorage;
  private autoCheckpointInterval: number | undefined;

  // Track step counts for auto-checkpointing
  private sessionSteps: Map<string, number> = new Map();
  private sessionLastCheckpoint: Map<string, string> = new Map();

  /**
   * Initialize checkpoint manager.
   *
   * @param storage - Checkpoint storage backend (defaults to in-memory)
   * @param autoCheckpointInterval - Automatically checkpoint every N steps (undefined = manual only)
   */
  constructor(storage?: CheckpointStorage, autoCheckpointInterval?: number) {
    this.storage = storage || new InMemoryCheckpointStorage();
    this.autoCheckpointInterval = autoCheckpointInterval;
  }

  /**
   * Create new checkpoint.
   *
   * @param params - Checkpoint parameters
   * @param params.sessionId - Session identifier
   * @param params.agentName - Agent name
   * @param params.stepNumber - Sequential step number
   * @param params.state - Agent state to save
   * @param params.messages - Conversation messages
   * @param params.metadata - Optional metadata
   * @param params.parentCheckpointId - ID of previous checkpoint
   * @returns Unique identifier for this checkpoint
   *
   * Example:
   *   const checkpointId = await manager.createCheckpoint({
   *     sessionId: 'session-1',
   *     agentName: 'assistant',
   *     stepNumber: 5,
   *     state: { counter: 5 },
   *     messages: [msg1, msg2, msg3],
   *   });
   */
  async createCheckpoint(params: {
    sessionId: string;
    agentName: string;
    stepNumber: number;
    state: Record<string, unknown>;
    messages: Message[];
    metadata?: Record<string, unknown>;
    parentCheckpointId?: string;
  }): Promise<string> {
    const { sessionId, agentName, stepNumber, state, messages, metadata, parentCheckpointId } =
      params;

    const checkpointId = uuidv4();

    // Use last checkpoint as parent if not specified
    const actualParentId = parentCheckpointId || this.sessionLastCheckpoint.get(sessionId);

    const checkpoint: Checkpoint = {
      checkpointId,
      sessionId,
      agentName,
      timestamp: new Date(),
      stepNumber,
      state,
      messages,
      metadata: metadata || {},
      parentCheckpointId: actualParentId,
    };

    await this.storage.save(checkpoint);

    // Update tracking
    this.sessionLastCheckpoint.set(sessionId, checkpointId);
    this.sessionSteps.set(sessionId, stepNumber);

    console.log(
      `[CheckpointManager] Created checkpoint ${checkpointId} for ${sessionId} at step ${stepNumber}`,
    );

    return checkpointId;
  }

  /**
   * Determine if checkpoint should be created (for auto-checkpointing).
   *
   * @param sessionId - Session identifier
   * @param stepNumber - Current step number
   * @returns True if checkpoint should be created
   */
  async shouldCheckpoint(sessionId: string, stepNumber: number): Promise<boolean> {
    if (this.autoCheckpointInterval === undefined) {
      return false;
    }

    const lastStep = this.sessionSteps.get(sessionId) || 0;
    const stepsSinceCheckpoint = stepNumber - lastStep;

    return stepsSinceCheckpoint >= this.autoCheckpointInterval;
  }

  /**
   * Get latest checkpoint for session.
   *
   * @param sessionId - Session identifier
   * @returns Latest checkpoint or undefined
   */
  async getLatest(sessionId: string): Promise<Checkpoint | undefined> {
    return await this.storage.getLatest(sessionId);
  }

  /**
   * Load specific checkpoint.
   *
   * @param checkpointId - Checkpoint identifier
   * @returns Checkpoint or undefined if not found
   */
  async loadCheckpoint(checkpointId: string): Promise<Checkpoint | undefined> {
    return await this.storage.load(checkpointId);
  }

  /**
   * List all checkpoints for session.
   *
   * @param sessionId - Session identifier
   * @param limit - Optional limit on number of checkpoints
   * @returns List of checkpoints (most recent first)
   */
  async listCheckpoints(sessionId: string, limit?: number): Promise<Checkpoint[]> {
    return await this.storage.listCheckpoints(sessionId, limit);
  }

  /**
   * Restore agent state from checkpoint.
   *
   * @param checkpoint - Checkpoint to restore from
   * @returns Restored state dictionary
   */
  async restoreState(checkpoint: Checkpoint): Promise<Record<string, unknown>> {
    console.log(
      `[CheckpointManager] Restoring state from checkpoint ${checkpoint.checkpointId} (step ${checkpoint.stepNumber})`,
    );
    return { ...checkpoint.state };
  }

  /**
   * Get checkpoint history by following parent links.
   *
   * @param checkpointId - Starting checkpoint
   * @param maxDepth - Maximum number of parents to follow
   * @returns List of checkpoints from most recent to oldest
   */
  async getCheckpointHistory(checkpointId: string, maxDepth: number = 10): Promise<Checkpoint[]> {
    return await this.storage.getCheckpointHistory(checkpointId, maxDepth);
  }

  /**
   * Replay execution from checkpoint.
   *
   * @param checkpointId - Starting checkpoint
   * @param replayFn - Async function to execute for each step
   *                   Signature: async (checkpoint, state) => result
   * @param upToStep - Optional step number to replay up to
   * @returns List of results from replay function
   *
   * Example:
   *   const replayStep = async (checkpoint, state) => {
   *     console.log(`Replaying step ${checkpoint.stepNumber}`);
   *     return processMessages(checkpoint.messages);
   *   };
   *
   *   const results = await manager.replayFromCheckpoint(
   *     'checkpoint-id',
   *     replayStep,
   *   );
   */
  async replayFromCheckpoint<T>(
    checkpointId: string,
    replayFn: (checkpoint: Checkpoint, state: Record<string, unknown>) => Promise<T>,
    upToStep?: number,
  ): Promise<T[]> {
    // Get checkpoint history
    const history = await this.getCheckpointHistory(checkpointId);
    history.reverse(); // Oldest to newest

    const results: T[] = [];

    for (const checkpoint of history) {
      // Stop if we've reached the target step
      if (upToStep !== undefined && checkpoint.stepNumber > upToStep) {
        break;
      }

      // Execute replay function
      const result = await replayFn(checkpoint, checkpoint.state);
      results.push(result);

      console.log(`[CheckpointManager] Replayed step ${checkpoint.stepNumber}`);
    }

    return results;
  }

  /**
   * Delete specific checkpoint.
   *
   * @param checkpointId - Checkpoint identifier
   * @returns True if deleted, false if not found
   */
  async deleteCheckpoint(checkpointId: string): Promise<boolean> {
    return await this.storage.delete(checkpointId);
  }

  /**
   * Delete all checkpoints for session.
   *
   * @param sessionId - Session identifier
   * @returns Number of checkpoints deleted
   */
  async deleteSession(sessionId: string): Promise<number> {
    const count = await this.storage.deleteSession(sessionId);

    // Clean up tracking
    this.sessionSteps.delete(sessionId);
    this.sessionLastCheckpoint.delete(sessionId);

    return count;
  }

  /**
   * Get statistics for session checkpoints.
   *
   * @param sessionId - Session identifier
   * @returns Statistics object
   */
  async getSessionStats(sessionId: string): Promise<{
    totalCheckpoints: number;
    firstCheckpoint?: string;
    latestCheckpoint?: string;
    firstStep?: number;
    latestStep?: number;
    stepsCovered?: number;
    timeSpanSeconds?: number;
  }> {
    const checkpoints = await this.listCheckpoints(sessionId);

    if (checkpoints.length === 0) {
      return {
        totalCheckpoints: 0,
      };
    }

    const first = checkpoints[checkpoints.length - 1];
    const latest = checkpoints[0];

    return {
      totalCheckpoints: checkpoints.length,
      firstCheckpoint: first.checkpointId,
      latestCheckpoint: latest.checkpointId,
      firstStep: first.stepNumber,
      latestStep: latest.stepNumber,
      stepsCovered: latest.stepNumber - first.stepNumber,
      timeSpanSeconds: (latest.timestamp.getTime() - first.timestamp.getTime()) / 1000,
    };
  }

  /**
   * Prune old checkpoints, keeping only the most recent N.
   *
   * @param sessionId - Session identifier
   * @param keepLast - Number of most recent checkpoints to keep
   * @returns Number of checkpoints deleted
   *
   * Example:
   *   // Keep only last 10 checkpoints
   *   const deleted = await manager.pruneOldCheckpoints('session-1', 10);
   *   console.log(`Deleted ${deleted} old checkpoints`);
   */
  async pruneOldCheckpoints(sessionId: string, keepLast: number = 10): Promise<number> {
    const checkpoints = await this.listCheckpoints(sessionId);

    if (checkpoints.length <= keepLast) {
      return 0;
    }

    // Delete old checkpoints
    const toDelete = checkpoints.slice(keepLast);
    let deletedCount = 0;

    for (const checkpoint of toDelete) {
      const deleted = await this.storage.delete(checkpoint.checkpointId);
      if (deleted) {
        deletedCount++;
      }
    }

    console.log(
      `[CheckpointManager] Pruned ${deletedCount} old checkpoints for ${sessionId}, kept ${keepLast} most recent`,
    );

    return deletedCount;
  }
}
