/**
 * Checkpoint data structures and storage interface.
 *
 * Checkpoints capture agent state at a point in time, enabling:
 * - Resume after crashes/restarts
 * - Time-travel debugging
 * - Durable execution for long-running agents
 */

import { Message, createMessage } from '../core/interfaces';

/**
 * Checkpoint capturing agent state at a point in time.
 *
 * Example:
 *   const checkpoint: Checkpoint = {
 *     checkpointId: 'ckpt-123',
 *     sessionId: 'session-456',
 *     agentName: 'assistant',
 *     timestamp: new Date(),
 *     stepNumber: 5,
 *     state: { counter: 10 },
 *     messages: [msg1, msg2],
 *     metadata: { cost: 0.05 },
 *     parentCheckpointId: 'ckpt-122',
 *   };
 */
export interface Checkpoint {
  /** Unique checkpoint identifier */
  checkpointId: string;

  /** Session this checkpoint belongs to */
  sessionId: string;

  /** Name of the agent */
  agentName: string;

  /** When checkpoint was created */
  timestamp: Date;

  /** Sequential step number in session */
  stepNumber: number;

  /** Agent state (custom data) */
  state: Record<string, unknown>;

  /** Conversation messages up to this point */
  messages: Message[];

  /** Additional metadata (cost, tokens, etc.) */
  metadata: Record<string, unknown>;

  /** ID of previous checkpoint (for history) */
  parentCheckpointId?: string;
}

/**
 * Convert checkpoint to dictionary for serialization.
 */
export function checkpointToDict(checkpoint: Checkpoint): Record<string, unknown> {
  const data: Record<string, unknown> = {
    ...checkpoint,
    timestamp: checkpoint.timestamp.toISOString(),
  };

  // Serialize messages (convert timestamp to ISO format)
  const serializedMessages: Record<string, unknown>[] = [];
  for (const msg of checkpoint.messages) {
    const msgDict: Record<string, unknown> = { ...msg };
    if (msg.timestamp) {
      msgDict.timestamp = msg.timestamp;
    }
    serializedMessages.push(msgDict);
  }
  data.messages = serializedMessages;

  return data;
}

/**
 * Create checkpoint from dictionary.
 */
export function checkpointFromDict(data: Record<string, unknown>): Checkpoint {
  const dataCopy = { ...data };
  dataCopy.timestamp = new Date(dataCopy.timestamp as string);

  // Deserialize messages (convert ISO timestamps back to Date)
  const deserializedMessages: Message[] = [];
  for (const msg of (dataCopy.messages as Record<string, unknown>[]) || []) {
    const msgCopy = { ...msg };
    if (msgCopy.timestamp && typeof msgCopy.timestamp === 'string') {
      msgCopy.timestamp = msgCopy.timestamp;
    }
    deserializedMessages.push(
      createMessage({
        role: msgCopy.role as 'user' | 'assistant' | 'system',
        content: msgCopy.content as string,
        metadata: msgCopy.metadata as Record<string, unknown> | undefined,
        timestamp: msgCopy.timestamp as string | undefined,
      }),
    );
  }
  dataCopy.messages = deserializedMessages;

  return dataCopy as Checkpoint;
}

/**
 * Serialize checkpoint to JSON.
 */
export function checkpointToJson(checkpoint: Checkpoint): string {
  return JSON.stringify(checkpointToDict(checkpoint), null, 2);
}

/**
 * Deserialize checkpoint from JSON.
 */
export function checkpointFromJson(jsonStr: string): Checkpoint {
  const data = JSON.parse(jsonStr);
  return checkpointFromDict(data);
}

/**
 * Abstract interface for checkpoint storage backends.
 *
 * Implementations:
 * - InMemoryCheckpointStorage: For testing/development
 * - FileCheckpointStorage: For persistence to disk
 * - RedisCheckpointStorage: For distributed systems
 */
export interface CheckpointStorage {
  /**
   * Save checkpoint to storage.
   */
  save(checkpoint: Checkpoint): Promise<void>;

  /**
   * Load checkpoint by ID.
   *
   * Returns checkpoint if found, undefined otherwise.
   */
  load(checkpointId: string): Promise<Checkpoint | undefined>;

  /**
   * List checkpoints for session.
   *
   * Returns list of checkpoints (most recent first).
   */
  listCheckpoints(sessionId: string, limit?: number): Promise<Checkpoint[]>;

  /**
   * Get latest checkpoint for session.
   *
   * Returns latest checkpoint if exists, undefined otherwise.
   */
  getLatest(sessionId: string): Promise<Checkpoint | undefined>;

  /**
   * Delete checkpoint.
   *
   * Returns true if deleted, false if not found.
   */
  delete(checkpointId: string): Promise<boolean>;

  /**
   * Delete all checkpoints for session.
   *
   * Returns number of checkpoints deleted.
   */
  deleteSession(sessionId: string): Promise<number>;

  /**
   * Get checkpoint history by following parent links.
   *
   * Returns list of checkpoints from most recent to oldest.
   */
  getCheckpointHistory(checkpointId: string, maxDepth?: number): Promise<Checkpoint[]>;
}
