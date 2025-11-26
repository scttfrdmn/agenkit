/**
 * Tests for session recording and replay.
 */

import { Agent, Message, createMessage } from '../core/interfaces';
import {
  SessionRecorder,
  SessionReplay,
  InMemoryRecordingStorage,
  FileRecordingStorage,
  SessionRecording,
  getSessionDuration,
  getTotalLatency,
  sessionRecordingToDict,
  sessionRecordingFromDict,
} from '../evaluation/recorder';
import { promises as fs } from 'fs';
import path from 'path';

// Mock agent for testing
class MockAgent implements Agent {
  name = 'mock-agent';
  capabilities = [];

  async process(message: Message): Promise<Message> {
    return createMessage('assistant', `Response: ${message.content}`);
  }
}

// Mock agent that throws errors
class ErrorAgent implements Agent {
  name = 'error-agent';
  capabilities = [];

  async process(_message: Message): Promise<Message> {
    throw new Error('Processing failed');
  }
}

describe('InMemoryRecordingStorage', () => {
  let storage: InMemoryRecordingStorage;

  beforeEach(() => {
    storage = new InMemoryRecordingStorage();
  });

  test('saves and loads recording', async () => {
    const recording: SessionRecording = {
      sessionId: 'test-123',
      agentName: 'test-agent',
      startTime: new Date('2025-01-01T00:00:00Z'),
      endTime: new Date('2025-01-01T00:01:00Z'),
      interactions: [],
      metadata: {},
    };

    await storage.saveRecording(recording);
    const loaded = await storage.loadRecording('test-123');

    expect(loaded).toBeDefined();
    expect(loaded?.sessionId).toBe('test-123');
    expect(loaded?.agentName).toBe('test-agent');
  });

  test('returns null for non-existent recording', async () => {
    const loaded = await storage.loadRecording('nonexistent');
    expect(loaded).toBeNull();
  });

  test('lists recordings', async () => {
    const recording1: SessionRecording = {
      sessionId: 'test-1',
      agentName: 'agent-1',
      startTime: new Date('2025-01-01T00:00:00Z'),
      endTime: null,
      interactions: [],
      metadata: {},
    };

    const recording2: SessionRecording = {
      sessionId: 'test-2',
      agentName: 'agent-2',
      startTime: new Date('2025-01-01T00:01:00Z'),
      endTime: null,
      interactions: [],
      metadata: {},
    };

    await storage.saveRecording(recording1);
    await storage.saveRecording(recording2);

    const recordings = await storage.listRecordings();

    expect(recordings).toHaveLength(2);
    // Should be sorted by start time (most recent first)
    expect(recordings[0].sessionId).toBe('test-2');
    expect(recordings[1].sessionId).toBe('test-1');
  });

  test('lists recordings with pagination', async () => {
    for (let i = 0; i < 5; i++) {
      await storage.saveRecording({
        sessionId: `test-${i}`,
        agentName: 'agent',
        startTime: new Date(),
        endTime: null,
        interactions: [],
        metadata: {},
      });
    }

    const page1 = await storage.listRecordings(2, 0);
    const page2 = await storage.listRecordings(2, 2);

    expect(page1).toHaveLength(2);
    expect(page2).toHaveLength(2);
  });

  test('deletes recording', async () => {
    const recording: SessionRecording = {
      sessionId: 'test-123',
      agentName: 'test-agent',
      startTime: new Date(),
      endTime: null,
      interactions: [],
      metadata: {},
    };

    await storage.saveRecording(recording);
    await storage.deleteRecording('test-123');

    const loaded = await storage.loadRecording('test-123');
    expect(loaded).toBeNull();
  });
});

describe('FileRecordingStorage', () => {
  const testDir = './test-recordings';
  let storage: FileRecordingStorage;

  beforeEach(() => {
    storage = new FileRecordingStorage(testDir);
  });

  afterEach(async () => {
    // Clean up test directory
    try {
      const files = await fs.readdir(testDir);
      for (const file of files) {
        await fs.unlink(path.join(testDir, file));
      }
      await fs.rmdir(testDir);
    } catch (error) {
      // Directory might not exist
    }
  });

  test('saves and loads recording', async () => {
    const recording: SessionRecording = {
      sessionId: 'test-123',
      agentName: 'test-agent',
      startTime: new Date('2025-01-01T00:00:00Z'),
      endTime: new Date('2025-01-01T00:01:00Z'),
      interactions: [],
      metadata: { version: '1.0' },
    };

    await storage.saveRecording(recording);
    const loaded = await storage.loadRecording('test-123');

    expect(loaded).toBeDefined();
    expect(loaded?.sessionId).toBe('test-123');
    expect(loaded?.metadata).toEqual({ version: '1.0' });
  });

  test('returns null for non-existent recording', async () => {
    const loaded = await storage.loadRecording('nonexistent');
    expect(loaded).toBeNull();
  });

  test('deletes recording', async () => {
    const recording: SessionRecording = {
      sessionId: 'test-123',
      agentName: 'test-agent',
      startTime: new Date(),
      endTime: null,
      interactions: [],
      metadata: {},
    };

    await storage.saveRecording(recording);
    await storage.deleteRecording('test-123');

    const loaded = await storage.loadRecording('test-123');
    expect(loaded).toBeNull();
  });
});

describe('SessionRecorder', () => {
  let recorder: SessionRecorder;
  let agent: Agent;

  beforeEach(() => {
    recorder = new SessionRecorder();
    agent = new MockAgent();
  });

  test('records single interaction', async () => {
    const wrapped = recorder.wrap(agent, 'test-session');
    const input = createMessage('user', 'test input');

    await wrapped.process(input);

    const recording = await recorder.finalizeSession('test-session');

    expect(recording.sessionId).toBe('test-session');
    expect(recording.agentName).toBe('mock-agent');
    expect(recording.interactions).toHaveLength(1);

    const interaction = recording.interactions[0];
    expect(interaction.inputMessage.content).toBe('test input');
    expect(interaction.outputMessage.content).toBe('Response: test input');
    expect(interaction.latencyMs).toBeGreaterThanOrEqual(0);
  });

  test('records multiple interactions', async () => {
    const wrapped = recorder.wrap(agent, 'test-session');

    await wrapped.process(createMessage('user', 'message 1'));
    await wrapped.process(createMessage('user', 'message 2'));
    await wrapped.process(createMessage('user', 'message 3'));

    const recording = await recorder.finalizeSession('test-session');

    expect(recording.interactions).toHaveLength(3);
    expect(recording.interactions[0].inputMessage.content).toBe('message 1');
    expect(recording.interactions[1].inputMessage.content).toBe('message 2');
    expect(recording.interactions[2].inputMessage.content).toBe('message 3');
  });

  test('records with default session ID', async () => {
    const wrapped = recorder.wrap(agent);

    await wrapped.process(createMessage('user', 'test'));

    const recording = await recorder.finalizeSession('default');

    expect(recording.sessionId).toBe('default');
    expect(recording.interactions).toHaveLength(1);
  });

  test('throws error for invalid session ID', async () => {
    await expect(recorder.finalizeSession('nonexistent')).rejects.toThrow(
      'No active session: nonexistent'
    );
  });

  test('saves recording to storage', async () => {
    const wrapped = recorder.wrap(agent, 'test-session');

    await wrapped.process(createMessage('user', 'test'));
    await recorder.finalizeSession('test-session');

    const loaded = await recorder.loadRecording('test-session');

    expect(loaded).toBeDefined();
    expect(loaded?.sessionId).toBe('test-session');
  });

  test('tracks session timing', async () => {
    const wrapped = recorder.wrap(agent, 'test-session');

    await wrapped.process(createMessage('user', 'test'));

    const recording = await recorder.finalizeSession('test-session');

    expect(recording.startTime).toBeInstanceOf(Date);
    expect(recording.endTime).toBeInstanceOf(Date);
    expect(recording.endTime!.getTime()).toBeGreaterThanOrEqual(
      recording.startTime.getTime()
    );
  });

  test('lists recordings', async () => {
    const wrapped1 = recorder.wrap(agent, 'session-1');
    const wrapped2 = recorder.wrap(agent, 'session-2');

    await wrapped1.process(createMessage('user', 'test 1'));
    await wrapped2.process(createMessage('user', 'test 2'));

    await recorder.finalizeSession('session-1');
    await recorder.finalizeSession('session-2');

    const recordings = await recorder.listRecordings();

    expect(recordings).toHaveLength(2);
  });

  test('deletes recording', async () => {
    const wrapped = recorder.wrap(agent, 'test-session');

    await wrapped.process(createMessage('user', 'test'));
    await recorder.finalizeSession('test-session');

    await recorder.deleteRecording('test-session');

    const loaded = await recorder.loadRecording('test-session');
    expect(loaded).toBeNull();
  });
});

describe('SessionReplay', () => {
  let replay: SessionReplay;
  let recorder: SessionRecorder;
  let agent: Agent;

  beforeEach(() => {
    replay = new SessionReplay();
    recorder = new SessionRecorder();
    agent = new MockAgent();
  });

  test('replays recorded session', async () => {
    // Record session
    const wrapped = recorder.wrap(agent, 'test-session');
    await wrapped.process(createMessage('user', 'message 1'));
    await wrapped.process(createMessage('user', 'message 2'));

    const recording = await recorder.finalizeSession('test-session');

    // Replay through same agent
    const results = await replay.replay(recording, agent);

    expect(results.sessionId).toBe('test-session');
    expect(results.originalSessionId).toBe('test-session');
    expect(results.interactions).toHaveLength(2);
    expect(results.errorCount).toBe(0);

    expect(results.interactions[0].replayOutput?.content).toBe('Response: message 1');
    expect(results.interactions[1].replayOutput?.content).toBe('Response: message 2');
  });

  test('replays with custom session ID', async () => {
    // Record session
    const wrapped = recorder.wrap(agent, 'original-session');
    await wrapped.process(createMessage('user', 'test'));

    const recording = await recorder.finalizeSession('original-session');

    // Replay with different session ID
    const results = await replay.replay(recording, agent, 'replay-session');

    expect(results.sessionId).toBe('replay-session');
    expect(results.originalSessionId).toBe('original-session');
  });

  test('tracks errors during replay', async () => {
    // Record session with normal agent
    const wrapped = recorder.wrap(agent, 'test-session');
    await wrapped.process(createMessage('user', 'test 1'));
    await wrapped.process(createMessage('user', 'test 2'));

    const recording = await recorder.finalizeSession('test-session');

    // Replay with error agent
    const errorAgent = new ErrorAgent();
    const results = await replay.replay(recording, errorAgent);

    expect(results.errorCount).toBe(2);
    expect(results.interactions[0].error).toBe('Processing failed');
    expect(results.interactions[1].error).toBe('Processing failed');
  });

  test('tracks latency during replay', async () => {
    // Record session
    const wrapped = recorder.wrap(agent, 'test-session');
    await wrapped.process(createMessage('user', 'test'));

    const recording = await recorder.finalizeSession('test-session');

    // Replay
    const results = await replay.replay(recording, agent);

    expect(results.interactions[0].originalLatencyMs).toBeGreaterThanOrEqual(0);
    expect(results.interactions[0].replayLatencyMs).toBeGreaterThanOrEqual(0);
    expect(results.totalLatencyMs).toBeGreaterThanOrEqual(0);
  });

  test('compares two replay results', async () => {
    // Record session
    const wrapped = recorder.wrap(agent, 'test-session');
    await wrapped.process(createMessage('user', 'test 1'));
    await wrapped.process(createMessage('user', 'test 2'));

    const recording = await recorder.finalizeSession('test-session');

    // Replay through two different agents
    const resultsA = await replay.replay(recording, agent);
    const resultsB = await replay.replay(recording, agent);

    // Compare
    const comparison = replay.compare(resultsA, resultsB);

    expect(comparison.interactionCount).toBe(2);
    expect(comparison.errorDiff).toBe(0);
    // Outputs should be identical for same agent
    expect(comparison.outputDifferences).toHaveLength(0);
  });

  test('detects output differences', async () => {
    // Record session
    const wrapped = recorder.wrap(agent, 'test-session');
    await wrapped.process(createMessage('user', 'test'));

    const recording = await recorder.finalizeSession('test-session');

    // Create agent with different output
    const agent2: Agent = {
      name: 'different-agent',
      capabilities: [],
      async process(message: Message) {
        return createMessage('assistant', `Different: ${message.content}`);
      },
    };

    // Replay through both agents
    const resultsA = await replay.replay(recording, agent);
    const resultsB = await replay.replay(recording, agent2);

    // Compare
    const comparison = replay.compare(resultsA, resultsB);

    expect(comparison.outputDifferences).toHaveLength(1);
    expect(comparison.outputDifferences[0].interactionIndex).toBe(0);
    expect(comparison.outputDifferences[0].outputA).toBe('Response: test');
    expect(comparison.outputDifferences[0].outputB).toBe('Different: test');
  });

  test('calculates latency difference percentage', async () => {
    // Record session
    const wrapped = recorder.wrap(agent, 'test-session');
    await wrapped.process(createMessage('user', 'test'));

    const recording = await recorder.finalizeSession('test-session');

    // Replay twice
    const resultsA = await replay.replay(recording, agent);
    const resultsB = await replay.replay(recording, agent);

    // Compare
    const comparison = replay.compare(resultsA, resultsB);

    expect(comparison.latencyDiffMs).toBeDefined();
    expect(comparison.latencyDiffPercent).toBeDefined();
  });
});

describe('Helper functions', () => {
  test('getSessionDuration calculates duration', () => {
    const recording: SessionRecording = {
      sessionId: 'test',
      agentName: 'agent',
      startTime: new Date('2025-01-01T00:00:00Z'),
      endTime: new Date('2025-01-01T00:01:00Z'),
      interactions: [],
      metadata: {},
    };

    const duration = getSessionDuration(recording);
    expect(duration).toBe(60); // 60 seconds
  });

  test('getSessionDuration returns 0 for active session', () => {
    const recording: SessionRecording = {
      sessionId: 'test',
      agentName: 'agent',
      startTime: new Date(),
      endTime: null,
      interactions: [],
      metadata: {},
    };

    const duration = getSessionDuration(recording);
    expect(duration).toBe(0);
  });

  test('getTotalLatency sums interaction latencies', () => {
    const recording: SessionRecording = {
      sessionId: 'test',
      agentName: 'agent',
      startTime: new Date(),
      endTime: null,
      interactions: [
        {
          interactionId: '1',
          sessionId: 'test',
          inputMessage: { role: 'user', content: 'test' },
          outputMessage: { role: 'assistant', content: 'response' },
          timestamp: new Date(),
          latencyMs: 100,
          metadata: {},
        },
        {
          interactionId: '2',
          sessionId: 'test',
          inputMessage: { role: 'user', content: 'test2' },
          outputMessage: { role: 'assistant', content: 'response2' },
          timestamp: new Date(),
          latencyMs: 200,
          metadata: {},
        },
      ],
      metadata: {},
    };

    const totalLatency = getTotalLatency(recording);
    expect(totalLatency).toBe(300);
  });

  test('sessionRecordingToDict converts to plain object', () => {
    const recording: SessionRecording = {
      sessionId: 'test-123',
      agentName: 'test-agent',
      startTime: new Date('2025-01-01T00:00:00Z'),
      endTime: new Date('2025-01-01T00:01:00Z'),
      interactions: [],
      metadata: { version: '1.0' },
    };

    const dict = sessionRecordingToDict(recording);

    expect(dict.session_id).toBe('test-123');
    expect(dict.agent_name).toBe('test-agent');
    expect(dict.start_time).toBe('2025-01-01T00:00:00.000Z');
    expect(dict.end_time).toBe('2025-01-01T00:01:00.000Z');
    expect(dict.metadata).toEqual({ version: '1.0' });
  });

  test('sessionRecordingFromDict creates from plain object', () => {
    const dict = {
      session_id: 'test-123',
      agent_name: 'test-agent',
      start_time: '2025-01-01T00:00:00.000Z',
      end_time: '2025-01-01T00:01:00.000Z',
      interactions: [],
      metadata: { version: '1.0' },
    };

    const recording = sessionRecordingFromDict(dict);

    expect(recording.sessionId).toBe('test-123');
    expect(recording.agentName).toBe('test-agent');
    expect(recording.startTime).toBeInstanceOf(Date);
    expect(recording.endTime).toBeInstanceOf(Date);
    expect(recording.metadata).toEqual({ version: '1.0' });
  });
});
