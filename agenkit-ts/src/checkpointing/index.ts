/**
 * Checkpointing and durable execution for long-running agents.
 *
 * This package provides checkpointing capabilities for long-running autonomous agents,
 * enabling state persistence, crash recovery, and time-travel debugging.
 *
 * Classes:
 *   Checkpoint: Checkpoint data structure
 *   CheckpointStorage: Abstract storage interface
 *   InMemoryCheckpointStorage: In-memory storage (testing)
 *   FileCheckpointStorage: File-based storage (production)
 *
 * Example:
 *   import { FileCheckpointStorage, Checkpoint } from 'agenkit';
 *
 *   // Create storage
 *   const storage = new FileCheckpointStorage('./checkpoints');
 *
 *   // Save checkpoint
 *   const checkpoint: Checkpoint = {
 *     checkpointId: 'ckpt-123',
 *     sessionId: 'session-456',
 *     agentName: 'assistant',
 *     timestamp: new Date(),
 *     stepNumber: 5,
 *     state: { counter: 10 },
 *     messages: [],
 *     metadata: {},
 *   };
 *   await storage.save(checkpoint);
 *
 *   // Load checkpoint
 *   const loaded = await storage.load('ckpt-123');
 */

export {
  Checkpoint,
  CheckpointStorage,
  checkpointToDict,
  checkpointFromDict,
  checkpointToJson,
  checkpointFromJson,
} from './checkpoint';

export { InMemoryCheckpointStorage, FileCheckpointStorage } from './storage';
