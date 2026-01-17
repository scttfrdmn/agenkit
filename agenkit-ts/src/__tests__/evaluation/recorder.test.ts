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
    expect(recording.interactionCount).toBe(0);
  });

  it('should record interaction', async () => {
    await recorder.startSession('test-session', 'test_agent');

    const input = createMessage('user', 'Hello');
    const output = createMessage('assistant', 'Hi there');

    await recorder.recordInteraction('test-session', input, output, 10.5);

    const recording = await recorder.finalizeSession('test-session');

    expect(recording.interactionCount).toBe(1);
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

    expect(recording.interactionCount).toBe(5);
    expect(recording.totalLatencyMs).toBe(60); // 10+11+12+13+14
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

    expect(recording.averageLatencyMs).toBe(20);
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

    const wrappedAgent = recorder.wrap(baseAgent, { autoStart: true });

    const input = createMessage('user', 'Test');
    const output = await wrappedAgent.process(input);

    expect(output.content).toBe('Response');

    // Recording should have been created automatically
    const sessions = await storage.listSessions();
    expect(sessions.length).toBe(1);
  });

  it('should use specified session ID', async () => {
    const storage = new InMemoryRecordingStorage();
    const recorder = new SessionRecorder(storage);
    const baseAgent = new MockAgent();

    const wrappedAgent = recorder.wrap(baseAgent, { sessionId: 'custom-session' });

    const input = createMessage('user', 'Test');
    await wrappedAgent.process(input);

    const recording = await storage.get('custom-session');
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

    const replay = new SessionReplay(recording);
    const agent = new MockAgent();

    const results = await replay.replay(agent);

    expect(results.length).toBe(1);
    expect(results[0].input.content).toBe('Hello');
  });

  it('should compare replay with original', async () => {
    const storage = new InMemoryRecordingStorage();
    const recorder = new SessionRecorder(storage);

    await recorder.startSession('test-session', 'test_agent');
    const input = createMessage('user', 'Test');
    const output = createMessage('assistant', 'Response');
    await recorder.recordInteraction('test-session', input, output, 10);
    const recording = await recorder.finalizeSession('test-session');

    const replay = new SessionReplay(recording);
    const agent = new MockAgent(['Response']); // Same response

    const comparison = await replay.compare(agent);

    expect(comparison.totalInteractions).toBe(1);
    expect(comparison.matchingOutputs).toBe(1);
    expect(comparison.matchRate).toBe(1.0);
  });

  it('should detect differences in replay', async () => {
    const storage = new InMemoryRecordingStorage();
    const recorder = new SessionRecorder(storage);

    await recorder.startSession('test-session', 'test_agent');
    const input = createMessage('user', 'Test');
    const output = createMessage('assistant', 'Original');
    await recorder.recordInteraction('test-session', input, output, 10);
    const recording = await recorder.finalizeSession('test-session');

    const replay = new SessionReplay(recording);
    const agent = new MockAgent(['Different']); // Different response

    const comparison = await replay.compare(agent);

    expect(comparison.matchingOutputs).toBe(0);
    expect(comparison.matchRate).toBe(0.0);
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

    const retrieved = await storage.get('test-123');

    expect(retrieved).toEqual(recording);
  });

  it('should list all sessions', async () => {
    const storage = new InMemoryRecordingStorage();
    const recorder = new SessionRecorder(storage);

    await recorder.startSession('session-1', 'agent');
    await recorder.finalizeSession('session-1');

    await recorder.startSession('session-2', 'agent');
    await recorder.finalizeSession('session-2');

    const sessions = await storage.listSessions();

    expect(sessions).toHaveLength(2);
    expect(sessions).toContain('session-1');
    expect(sessions).toContain('session-2');
  });

  it('should delete recordings', async () => {
    const storage = new InMemoryRecordingStorage();
    const recorder = new SessionRecorder(storage);

    await recorder.startSession('test-123', 'agent');
    await recorder.finalizeSession('test-123');

    await storage.delete('test-123');

    const retrieved = await storage.get('test-123');
    expect(retrieved).toBeNull();
  });
});
