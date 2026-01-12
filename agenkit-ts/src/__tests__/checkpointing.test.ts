/**
 * Tests for Checkpointing (CheckpointManager and DurableAgent).
 */

import {
  Checkpoint,
  CheckpointManager,
  DurableAgent,
  makeDurable,
  InMemoryCheckpointStorage,
  FileCheckpointStorage,
} from '../checkpointing';
import { Agent, Message, createMessage } from '../core/interfaces';
import * as fs from 'fs';
import * as path from 'path';

// Mock Agent for testing
class MockAgent implements Agent {
  public name = 'mock-agent';
  public processCount = 0;

  async process(message: Message): Promise<Message> {
    this.processCount++;
    return createMessage({
      role: 'assistant',
      content: `Response ${this.processCount} to: ${message.content}`,
    });
  }
}

describe('CheckpointManager', () => {
  let manager: CheckpointManager;
  let storage: InMemoryCheckpointStorage;

  beforeEach(() => {
    storage = new InMemoryCheckpointStorage();
    manager = new CheckpointManager(storage);
  });

  describe('createCheckpoint', () => {
    it('should create a checkpoint', async () => {
      const msg = createMessage({ role: 'user', content: 'Hello' });

      const checkpointId = await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test-agent',
        stepNumber: 1,
        state: { counter: 1 },
        messages: [msg],
      });

      expect(checkpointId).toBeTruthy();

      const checkpoint = await manager.loadCheckpoint(checkpointId);
      expect(checkpoint).toBeDefined();
      expect(checkpoint!.sessionId).toBe('session-1');
      expect(checkpoint!.agentName).toBe('test-agent');
      expect(checkpoint!.stepNumber).toBe(1);
      expect(checkpoint!.state).toEqual({ counter: 1 });
      expect(checkpoint!.messages).toHaveLength(1);
    });

    it('should create checkpoint with metadata', async () => {
      const checkpointId = await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test-agent',
        stepNumber: 1,
        state: {},
        messages: [],
        metadata: { cost: 0.05, tokens: 100 },
      });

      const checkpoint = await manager.loadCheckpoint(checkpointId);
      expect(checkpoint!.metadata).toEqual({ cost: 0.05, tokens: 100 });
    });

    it('should link checkpoints with parent relationships', async () => {
      const checkpoint1 = await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test-agent',
        stepNumber: 1,
        state: {},
        messages: [],
      });

      const checkpoint2 = await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test-agent',
        stepNumber: 2,
        state: {},
        messages: [],
        parentCheckpointId: checkpoint1,
      });

      const loaded = await manager.loadCheckpoint(checkpoint2);
      expect(loaded!.parentCheckpointId).toBe(checkpoint1);
    });
  });

  describe('shouldCheckpoint', () => {
    it('should return false when auto-checkpoint is disabled', async () => {
      const should = await manager.shouldCheckpoint('session-1', 10);
      expect(should).toBe(false);
    });

    it('should return true when interval is reached', async () => {
      const managerWithAuto = new CheckpointManager(storage, 5);

      await managerWithAuto.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test',
        stepNumber: 1,
        state: {},
        messages: [],
      });

      const shouldAt5 = await managerWithAuto.shouldCheckpoint('session-1', 6);
      expect(shouldAt5).toBe(true);

      const shouldAt4 = await managerWithAuto.shouldCheckpoint('session-1', 5);
      expect(shouldAt4).toBe(false);
    });
  });

  describe('listCheckpoints', () => {
    it('should list checkpoints for session', async () => {
      await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test',
        stepNumber: 1,
        state: {},
        messages: [],
      });

      await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test',
        stepNumber: 2,
        state: {},
        messages: [],
      });

      await manager.createCheckpoint({
        sessionId: 'session-2',
        agentName: 'test',
        stepNumber: 1,
        state: {},
        messages: [],
      });

      const session1Checkpoints = await manager.listCheckpoints('session-1');
      expect(session1Checkpoints).toHaveLength(2);

      const session2Checkpoints = await manager.listCheckpoints('session-2');
      expect(session2Checkpoints).toHaveLength(1);
    });

    it('should respect limit parameter', async () => {
      for (let i = 1; i <= 5; i++) {
        await manager.createCheckpoint({
          sessionId: 'session-1',
          agentName: 'test',
          stepNumber: i,
          state: {},
          messages: [],
        });
      }

      const limited = await manager.listCheckpoints('session-1', 3);
      expect(limited).toHaveLength(3);
    });

    it('should return checkpoints in reverse chronological order', async () => {
      for (let i = 1; i <= 3; i++) {
        await manager.createCheckpoint({
          sessionId: 'session-1',
          agentName: 'test',
          stepNumber: i,
          state: {},
          messages: [],
        });
        // Small delay to ensure different timestamps
        await new Promise((resolve) => setTimeout(resolve, 10));
      }

      const checkpoints = await manager.listCheckpoints('session-1');
      expect(checkpoints[0].stepNumber).toBe(3);
      expect(checkpoints[1].stepNumber).toBe(2);
      expect(checkpoints[2].stepNumber).toBe(1);
    });
  });

  describe('getLatest', () => {
    it('should return latest checkpoint', async () => {
      await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test',
        stepNumber: 1,
        state: { value: 'old' },
        messages: [],
      });

      // Small delay to ensure different timestamps
      await new Promise((resolve) => setTimeout(resolve, 10));

      await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test',
        stepNumber: 2,
        state: { value: 'new' },
        messages: [],
      });

      const latest = await manager.getLatest('session-1');
      expect(latest).toBeDefined();
      expect(latest!.stepNumber).toBe(2);
      expect(latest!.state).toEqual({ value: 'new' });
    });

    it('should return undefined for non-existent session', async () => {
      const latest = await manager.getLatest('non-existent');
      expect(latest).toBeUndefined();
    });
  });

  describe('restoreState', () => {
    it('should restore state from checkpoint', async () => {
      const checkpointId = await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test',
        stepNumber: 5,
        state: { counter: 42, mode: 'active' },
        messages: [],
      });

      const checkpoint = await manager.loadCheckpoint(checkpointId);
      const state = await manager.restoreState(checkpoint!);

      expect(state).toEqual({ counter: 42, mode: 'active' });
    });
  });

  describe('replayFromCheckpoint', () => {
    it('should replay from checkpoint history', async () => {
      // Create checkpoint chain
      const cp1 = await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test',
        stepNumber: 1,
        state: { value: 1 },
        messages: [],
      });

      const cp2 = await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test',
        stepNumber: 2,
        state: { value: 2 },
        messages: [],
        parentCheckpointId: cp1,
      });

      const cp3 = await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test',
        stepNumber: 3,
        state: { value: 3 },
        messages: [],
        parentCheckpointId: cp2,
      });

      const replayFn = async (checkpoint: Checkpoint, state: Record<string, unknown>) => {
        return checkpoint.stepNumber;
      };

      const results = await manager.replayFromCheckpoint(cp3, replayFn);
      expect(results).toEqual([1, 2, 3]);
    });

    it('should respect upToStep parameter', async () => {
      const cp1 = await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test',
        stepNumber: 1,
        state: {},
        messages: [],
      });

      const cp2 = await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test',
        stepNumber: 2,
        state: {},
        messages: [],
        parentCheckpointId: cp1,
      });

      const cp3 = await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test',
        stepNumber: 3,
        state: {},
        messages: [],
        parentCheckpointId: cp2,
      });

      const replayFn = async (checkpoint: Checkpoint) => checkpoint.stepNumber;

      const results = await manager.replayFromCheckpoint(cp3, replayFn, 2);
      expect(results).toEqual([1, 2]);
    });
  });

  describe('deleteCheckpoint', () => {
    it('should delete specific checkpoint', async () => {
      const checkpointId = await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test',
        stepNumber: 1,
        state: {},
        messages: [],
      });

      const deleted = await manager.deleteCheckpoint(checkpointId);
      expect(deleted).toBe(true);

      const loaded = await manager.loadCheckpoint(checkpointId);
      expect(loaded).toBeUndefined();
    });

    it('should return false for non-existent checkpoint', async () => {
      const deleted = await manager.deleteCheckpoint('non-existent');
      expect(deleted).toBe(false);
    });
  });

  describe('deleteSession', () => {
    it('should delete all checkpoints for session', async () => {
      await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test',
        stepNumber: 1,
        state: {},
        messages: [],
      });

      await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test',
        stepNumber: 2,
        state: {},
        messages: [],
      });

      const count = await manager.deleteSession('session-1');
      expect(count).toBe(2);

      const checkpoints = await manager.listCheckpoints('session-1');
      expect(checkpoints).toHaveLength(0);
    });
  });

  describe('getSessionStats', () => {
    it('should return empty stats for session with no checkpoints', async () => {
      const stats = await manager.getSessionStats('session-1');
      expect(stats.totalCheckpoints).toBe(0);
      expect(stats.firstCheckpoint).toBeUndefined();
    });

    it('should return stats for session with checkpoints', async () => {
      await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test',
        stepNumber: 1,
        state: {},
        messages: [],
      });

      // Small delay to ensure different timestamps
      await new Promise((resolve) => setTimeout(resolve, 10));

      await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test',
        stepNumber: 5,
        state: {},
        messages: [],
      });

      const stats = await manager.getSessionStats('session-1');
      expect(stats.totalCheckpoints).toBe(2);
      expect(stats.firstStep).toBe(1);
      expect(stats.latestStep).toBe(5);
      expect(stats.stepsCovered).toBe(4);
    });
  });

  describe('pruneOldCheckpoints', () => {
    it('should prune old checkpoints', async () => {
      for (let i = 1; i <= 10; i++) {
        await manager.createCheckpoint({
          sessionId: 'session-1',
          agentName: 'test',
          stepNumber: i,
          state: {},
          messages: [],
        });
      }

      const deleted = await manager.pruneOldCheckpoints('session-1', 5);
      expect(deleted).toBe(5);

      const remaining = await manager.listCheckpoints('session-1');
      expect(remaining).toHaveLength(5);
    });

    it('should not prune when checkpoint count is below limit', async () => {
      await manager.createCheckpoint({
        sessionId: 'session-1',
        agentName: 'test',
        stepNumber: 1,
        state: {},
        messages: [],
      });

      const deleted = await manager.pruneOldCheckpoints('session-1', 10);
      expect(deleted).toBe(0);
    });
  });
});

describe('DurableAgent', () => {
  let mockAgent: MockAgent;
  let durableAgent: DurableAgent;
  const testCheckpointDir = '/tmp/test-checkpoints-' + Date.now();

  beforeEach(() => {
    mockAgent = new MockAgent();
    durableAgent = new DurableAgent({
      agent: mockAgent,
      checkpointInterval: 3,
      autoResume: false, // Disable for manual testing
    });
  });

  afterEach(() => {
    // Cleanup test checkpoint directory
    if (fs.existsSync(testCheckpointDir)) {
      fs.rmSync(testCheckpointDir, { recursive: true });
    }
  });

  describe('process', () => {
    it('should process messages and track state', async () => {
      const msg = createMessage({ role: 'user', content: 'Hello' });
      const response = await durableAgent.process(msg, 'session-1');

      expect(response.content).toContain('Response 1');
      expect(mockAgent.processCount).toBe(1);

      const state = await durableAgent.getState('session-1');
      expect(state.messageCount).toBe(1);
      expect(state.lastInput).toBe('Hello');
    });

    it('should auto-checkpoint at interval', async () => {
      for (let i = 1; i <= 5; i++) {
        const msg = createMessage({ role: 'user', content: `Message ${i}` });
        await durableAgent.process(msg, 'session-1');
      }

      const checkpoints = await durableAgent.listCheckpoints('session-1');
      // Should checkpoint at steps 3 and then not again until 6
      expect(checkpoints.length).toBeGreaterThan(0);
    });

    it('should maintain message history', async () => {
      const msg1 = createMessage({ role: 'user', content: 'First' });
      const msg2 = createMessage({ role: 'user', content: 'Second' });

      await durableAgent.process(msg1, 'session-1');
      await durableAgent.process(msg2, 'session-1');

      const messages = await durableAgent.getMessages('session-1');
      expect(messages).toHaveLength(4); // 2 user + 2 assistant
    });
  });

  describe('checkpoint', () => {
    it('should create checkpoint manually', async () => {
      const msg = createMessage({ role: 'user', content: 'Test' });
      await durableAgent.process(msg, 'session-1');

      const checkpointId = await durableAgent.checkpoint('session-1');
      expect(checkpointId).toBeTruthy();

      const checkpoints = await durableAgent.listCheckpoints('session-1');
      expect(checkpoints.length).toBeGreaterThan(0);
    });

    it('should include metadata in checkpoint', async () => {
      const msg = createMessage({ role: 'user', content: 'Test' });
      await durableAgent.process(msg, 'session-1');

      await durableAgent.checkpoint('session-1', { cost: 0.05 });

      const checkpoints = await durableAgent.listCheckpoints('session-1');
      expect(checkpoints[0].metadata).toEqual({ cost: 0.05 });
    });
  });

  describe('resume', () => {
    it('should resume from checkpoint', async () => {
      // Use shared storage for this test
      const sharedStorage = new InMemoryCheckpointStorage();
      const agent1 = new DurableAgent({
        agent: new MockAgent(),
        autoResume: false,
      });
      // Access internal manager to set shared storage (for testing)
      (agent1 as any).manager = new CheckpointManager(sharedStorage, 3);

      const msg = createMessage({ role: 'user', content: 'Test' });
      await agent1.process(msg, 'session-1');
      await agent1.checkpoint('session-1');

      // Create new agent with same shared storage
      const agent2 = new DurableAgent({
        agent: new MockAgent(),
        autoResume: false,
      });
      (agent2 as any).manager = new CheckpointManager(sharedStorage, 3);

      const state = await agent2.resume('session-1');
      expect(state).toBeDefined();
      expect(state!.messageCount).toBe(1);
    });

    it('should return undefined when no checkpoint exists', async () => {
      const state = await durableAgent.resume('non-existent');
      expect(state).toBeUndefined();
    });
  });

  describe('state management', () => {
    it('should get and set state', async () => {
      await durableAgent.setState('session-1', { custom: 'value' });
      const state = await durableAgent.getState('session-1');
      expect(state.custom).toBe('value');
    });

    it('should reset session', async () => {
      const msg = createMessage({ role: 'user', content: 'Test' });
      await durableAgent.process(msg, 'session-1');

      await durableAgent.resetSession('session-1');

      const state = await durableAgent.getState('session-1');
      expect(Object.keys(state)).toHaveLength(0);

      const messages = await durableAgent.getMessages('session-1');
      expect(messages).toHaveLength(0);
    });
  });

  describe('getSessionStats', () => {
    it('should return session statistics', async () => {
      for (let i = 1; i <= 3; i++) {
        const msg = createMessage({ role: 'user', content: `Message ${i}` });
        await durableAgent.process(msg, 'session-1');
      }

      await durableAgent.checkpoint('session-1');

      const stats = await durableAgent.getSessionStats('session-1');
      expect(stats.currentStep).toBe(3);
      expect(stats.messageCount).toBe(6); // 3 user + 3 assistant
    });
  });

  describe('deleteCheckpoints', () => {
    it('should delete all checkpoints and reset session', async () => {
      const msg = createMessage({ role: 'user', content: 'Test' });
      await durableAgent.process(msg, 'session-1');
      await durableAgent.checkpoint('session-1');

      const count = await durableAgent.deleteCheckpoints('session-1');
      expect(count).toBe(1);

      const checkpoints = await durableAgent.listCheckpoints('session-1');
      expect(checkpoints).toHaveLength(0);
    });
  });
});

describe('makeDurable', () => {
  it('should create durable agent with convenience function', () => {
    const mockAgent = new MockAgent();
    const durable = makeDurable(mockAgent, './checkpoints', 5);

    expect(durable).toBeInstanceOf(DurableAgent);
    expect(durable.name).toBe('mock-agent');
  });

  it('should use default values', () => {
    const mockAgent = new MockAgent();
    const durable = makeDurable(mockAgent);

    expect(durable).toBeInstanceOf(DurableAgent);
  });
});

describe('FileCheckpointStorage Integration', () => {
  const testDir = '/tmp/test-checkpoints-file-' + Date.now();
  let storage: FileCheckpointStorage;
  let manager: CheckpointManager;

  beforeEach(() => {
    storage = new FileCheckpointStorage(testDir);
    manager = new CheckpointManager(storage);
  });

  afterEach(() => {
    if (fs.existsSync(testDir)) {
      fs.rmSync(testDir, { recursive: true });
    }
  });

  it('should persist checkpoints to disk', async () => {
    const checkpointId = await manager.createCheckpoint({
      sessionId: 'session-1',
      agentName: 'test',
      stepNumber: 1,
      state: { persisted: true },
      messages: [],
    });

    // Create new manager with same storage
    const newManager = new CheckpointManager(storage);
    const loaded = await newManager.loadCheckpoint(checkpointId);

    expect(loaded).toBeDefined();
    expect(loaded!.state).toEqual({ persisted: true });
  });

  it('should organize checkpoints by session', async () => {
    await manager.createCheckpoint({
      sessionId: 'session-1',
      agentName: 'test',
      stepNumber: 1,
      state: {},
      messages: [],
    });

    const sessionDir = path.join(testDir, 'session-1');
    expect(fs.existsSync(sessionDir)).toBe(true);

    const files = fs.readdirSync(sessionDir);
    expect(files.length).toBeGreaterThan(0);
    expect(files[0].endsWith('.json')).toBe(true);
  });
});
