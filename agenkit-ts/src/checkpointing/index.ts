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
 *   CheckpointManager: High-level checkpoint orchestration
 *   DurableAgent: Agent wrapper with automatic checkpointing
 *
 * Example:
 *   import { DurableAgent, makeDurable } from 'agenkit';
 *
 *   // Create durable agent with automatic checkpointing
 *   const durableAgent = makeDurable(
 *     myAgent,
 *     './checkpoints',
 *     10,  // checkpoint every 10 steps
 *   );
 *
 *   // Use agent (automatically checkpoints and resumes)
 *   const response = await durableAgent.process(message, 'session-1');
 *
 *   // Or use low-level storage directly
 *   const storage = new FileCheckpointStorage('./checkpoints');
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

export { CheckpointManager } from './manager';

export { DurableAgent, makeDurable } from './durable';
