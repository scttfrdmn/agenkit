/**
 * Tests for session recording and replay.
 *
 * Tests SessionRecorder, SessionReplay, and storage backends.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import type { Agent, Message } from '../../core/interfaces';
import { createMessage } from '../../core/interfaces';
import {
  SessionRecorder,
  InMemoryRecordingStorage,
  SessionReplay,
  getTotalLatency,
} from '../../evaluation/recorder';

// Mock agent for testing
class MockAgent implements Agent {
  name = 'mock-agent';
  capabilities = [];
  private responses: string[];
  private callCount = 0;

  constructor(responses: string[] = ['Response']) {
    this.responses = responses;
  }

  async process(message: Message): Promise<Message> {
    const response = this.responses[this.callCount % this.responses.length];
    this.callCount++;
    return createMessage('assistant', response);
  }
}

// ============================================
// SessionRecorder Basic Tests
// ============================================

describe('SessionRecorder: Basic Functionality', () => {
  let storage: InMemoryRecordingStorage;
  let recorder: SessionRecorder;

  beforeEach(() => {
    storage = new InMemoryRecordingStorage();
    recorder = new SessionRecorder(storage);
  });

  it('should start and finalize session', async () => {
    await recorder.startSession('test-session', 'test_agent');

    const recording = await recorder.finalizeSession('test-session');

    expect(recording.sessionId).toBe('test-session');
    expect(recording.agentName).toBe('test_agent');
    expect(recording.interactions.length).toBe(0);
  });

  it('should record interaction', async () => {
    await recorder.startSession('test-session', 'test_agent');

    const input = createMessage('user', 'Hello');
    const output = createMessage('assistant', 'Hi there');

    await recorder.recordInteraction('test-session', input, output, 10.5);

    const recording = await recorder.finalizeSession('test-session');

    expect(recording.interactions.length).toBe(1);
    expect(recording.interactions[0].latencyMs).toBe(10.5);
  });

  it('should record multiple interactions', async () => {
    await recorder.startSession('test-session', 'test_agent');

    for (let i = 0; i < 5; i++) {
      const input = createMessage('user', `Message ${i}`);
      const output = createMessage('assistant', `Response ${i}`);
      await recorder.recordInteraction('test-session', input, output, 10.0 + i);
    }

    const recording = await recorder.finalizeSession('test-session');

    expect(recording.interactions.length).toBe(5);
    expect(getTotalLatency(recording)).toBe(60); // 10+11+12+13+14
  });

  it('should calculate average latency', async () => {
    await recorder.startSession('test-session', 'test_agent');

    const latencies = [10, 20, 30];
    for (const latency of latencies) {
      const input = createMessage('user', 'Test');
      const output = createMessage('assistant', 'Response');
      await recorder.recordInteraction('test-session', input, output, latency);
    }

    const recording = await recorder.finalizeSession('test-session');

    const totalLatency = getTotalLatency(recording);
    const avgLatency = totalLatency / recording.interactions.length;
    expect(avgLatency).toBe(20);
  });
});

// ============================================
// Agent Wrapping Tests
// ============================================

describe('SessionRecorder: Agent Wrapping', () => {
  it('should wrap agent and record automatically', async () => {
    const storage = new InMemoryRecordingStorage();
    const recorder = new SessionRecorder(storage);
    const baseAgent = new MockAgent();

    const wrappedAgent = recorder.wrap(baseAgent);

    const input = createMessage('user', 'Test');
    const output = await wrappedAgent.process(input);

    expect(output.content).toBe('Response');

    // Finalize session to save to storage
    await recorder.finalizeSession('default');

    // Recording should have been created and saved
    const recordings = await storage.listRecordings();
    expect(recordings.length).toBe(1);
  });

  it('should use specified session ID', async () => {
    const storage = new InMemoryRecordingStorage();
    const recorder = new SessionRecorder(storage);
    const baseAgent = new MockAgent();

    const wrappedAgent = recorder.wrap(baseAgent, 'custom-session');

    const input = createMessage('user', 'Test');
    await wrappedAgent.process(input);

    // Finalize session to save to storage
    await recorder.finalizeSession('custom-session');

    const recording = await storage.loadRecording('custom-session');
    expect(recording?.sessionId).toBe('custom-session');
  });
});

// ============================================
// SessionReplay Tests
// ============================================

describe('SessionReplay', () => {
  it('should replay recorded session', async () => {
    const storage = new InMemoryRecordingStorage();
    const recorder = new SessionRecorder(storage);

    await recorder.startSession('test-session', 'test_agent');
    const input = createMessage('user', 'Hello');
    const output = createMessage('assistant', 'Hi');
    await recorder.recordInteraction('test-session', input, output, 10);
    const recording = await recorder.finalizeSession('test-session');

    const replay = new SessionReplay();
    const agent = new MockAgent();

    const results = await replay.replay(recording, agent);

    expect(results.interactions.length).toBe(1);
    expect(results.interactions[0].input.content).toBe('Hello');
  });

  it('should compare replay with original', async () => {
    const storage = new InMemoryRecordingStorage();
    const recorder = new SessionRecorder(storage);

    await recorder.startSession('test-session', 'test_agent');
    const input = createMessage('user', 'Test');
    const output = createMessage('assistant', 'Response');
    await recorder.recordInteraction('test-session', input, output, 10);
    const recording = await recorder.finalizeSession('test-session');

    const replay = new SessionReplay();
    const agentA = new MockAgent(['Response']); // Same response
    const agentB = new MockAgent(['Response']); // Same response

    const resultsA = await replay.replay(recording, agentA);
    const resultsB = await replay.replay(recording, agentB);
    const comparison = replay.compare(resultsA, resultsB);

    expect(comparison.interactionCount).toBe(1);
    expect(comparison.outputDifferences.length).toBe(0);
  });

  it('should detect differences in replay', async () => {
    const storage = new InMemoryRecordingStorage();
    const recorder = new SessionRecorder(storage);

    await recorder.startSession('test-session', 'test_agent');
    const input = createMessage('user', 'Test');
    const output = createMessage('assistant', 'Original');
    await recorder.recordInteraction('test-session', input, output, 10);
    const recording = await recorder.finalizeSession('test-session');

    const replay = new SessionReplay();
    const agentA = new MockAgent(['Response A']); // First response
    const agentB = new MockAgent(['Response B']); // Different response

    const resultsA = await replay.replay(recording, agentA);
    const resultsB = await replay.replay(recording, agentB);
    const comparison = replay.compare(resultsA, resultsB);

    expect(comparison.outputDifferences.length).toBe(1);
  });
});

// ============================================
// Storage Backend Tests
// ============================================

describe('InMemoryRecordingStorage', () => {
  it('should store and retrieve recordings', async () => {
    const storage = new InMemoryRecordingStorage();
    const recorder = new SessionRecorder(storage);

    await recorder.startSession('test-123', 'agent');
    const recording = await recorder.finalizeSession('test-123');

    const retrieved = await storage.loadRecording('test-123');

    expect(retrieved).toEqual(recording);
  });

  it('should list all recordings', async () => {
    const storage = new InMemoryRecordingStorage();
    const recorder = new SessionRecorder(storage);

    await recorder.startSession('session-1', 'agent');
    await recorder.finalizeSession('session-1');

    await recorder.startSession('session-2', 'agent');
    await recorder.finalizeSession('session-2');

    const recordings = await storage.listRecordings();

    expect(recordings).toHaveLength(2);
    const sessionIds = recordings.map((r) => r.sessionId);
    expect(sessionIds).toContain('session-1');
    expect(sessionIds).toContain('session-2');
  });

  it('should delete recordings', async () => {
    const storage = new InMemoryRecordingStorage();
    const recorder = new SessionRecorder(storage);

    await recorder.startSession('test-123', 'agent');
    await recorder.finalizeSession('test-123');

    await storage.deleteRecording('test-123');

    const retrieved = await storage.loadRecording('test-123');
    expect(retrieved).toBeNull();
  });
});
