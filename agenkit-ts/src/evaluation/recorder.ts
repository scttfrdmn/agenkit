/**
 * Session recording and replay for evaluation.
 *
 * Records agent interactions for later replay, analysis, and A/B testing.
 *
 * Example:
 * ```typescript
 * const recorder = new SessionRecorder(new FileRecordingStorage('./recordings'));
 * const wrappedAgent = recorder.wrap(agent);
 *
 * // Use agent normally (automatically recorded)
 * await wrappedAgent.process(message, 'test-123');
 *
 * // Save recording
 * await recorder.finalizeSession('test-123');
 *
 * // Later: replay session
 * const recording = await recorder.loadRecording('test-123');
 * const replay = new SessionReplay();
 * const results = await replay.replay(recording, newAgent);
 * ```
 */

import { Agent, Message } from '../core/interfaces';
import { promises as fs } from 'fs';
import path from 'path';
import { randomUUID } from 'crypto';

/**
 * Record of single agent interaction.
 *
 * Contains input, output, timing, and metadata.
 */
export interface InteractionRecord {
  /** Unique interaction identifier */
  interactionId: string;
  /** Session this interaction belongs to */
  sessionId: string;
  /** Input message to agent */
  inputMessage: MessageDict;
  /** Output message from agent */
  outputMessage: MessageDict;
  /** Timestamp of interaction */
  timestamp: Date;
  /** Processing time in milliseconds */
  latencyMs: number;
  /** Additional metadata */
  metadata: Record<string, unknown>;
}

/**
 * Message as dictionary.
 */
export interface MessageDict {
  role: string;
  content: string;
  metadata?: Record<string, unknown>;
}

/**
 * Convert message to dictionary.
 *
 * @param message Message to convert
 * @returns Dictionary representation
 */
function messageToDict(message: Message): MessageDict {
  return {
    role: message.role,
    content: String(message.content),
    metadata: message.metadata || {},
  };
}

/**
 * Recording of entire session.
 *
 * Contains all interactions and session metadata.
 */
export interface SessionRecording {
  /** Unique session identifier */
  sessionId: string;
  /** Name of agent being recorded */
  agentName: string;
  /** Session start time */
  startTime: Date;
  /** Session end time (null if still active) */
  endTime: Date | null;
  /** List of interactions */
  interactions: InteractionRecord[];
  /** Session metadata */
  metadata: Record<string, unknown>;
}

/**
 * Calculate session duration in seconds.
 *
 * @param recording Session recording
 * @returns Duration in seconds (0 if session not ended)
 */
export function getSessionDuration(recording: SessionRecording): number {
  if (!recording.endTime) {
    return 0;
  }
  return (recording.endTime.getTime() - recording.startTime.getTime()) / 1000;
}

/**
 * Get total latency across all interactions.
 *
 * @param recording Session recording
 * @returns Total latency in milliseconds
 */
export function getTotalLatency(recording: SessionRecording): number {
  return recording.interactions.reduce((sum, interaction) => sum + interaction.latencyMs, 0);
}

/**
 * Convert interaction record to plain object.
 *
 * @param record Interaction record
 * @returns Plain object representation
 */
export function interactionRecordToDict(record: InteractionRecord): Record<string, unknown> {
  return {
    interaction_id: record.interactionId,
    session_id: record.sessionId,
    input_message: record.inputMessage,
    output_message: record.outputMessage,
    timestamp: record.timestamp.toISOString(),
    latency_ms: record.latencyMs,
    metadata: record.metadata,
  };
}

/**
 * Create interaction record from plain object.
 *
 * @param data Plain object
 * @returns Interaction record
 */
export function interactionRecordFromDict(data: Record<string, unknown>): InteractionRecord {
  return {
    interactionId: String(data.interaction_id),
    sessionId: String(data.session_id),
    inputMessage: data.input_message as MessageDict,
    outputMessage: data.output_message as MessageDict,
    timestamp: new Date(String(data.timestamp)),
    latencyMs: Number(data.latency_ms),
    metadata: (data.metadata as Record<string, unknown>) || {},
  };
}

/**
 * Convert session recording to plain object.
 *
 * @param recording Session recording
 * @returns Plain object representation
 */
export function sessionRecordingToDict(recording: SessionRecording): Record<string, unknown> {
  return {
    session_id: recording.sessionId,
    agent_name: recording.agentName,
    start_time: recording.startTime.toISOString(),
    end_time: recording.endTime ? recording.endTime.toISOString() : null,
    interactions: recording.interactions.map(interactionRecordToDict),
    metadata: recording.metadata,
  };
}

/**
 * Create session recording from plain object.
 *
 * @param data Plain object
 * @returns Session recording
 */
export function sessionRecordingFromDict(data: Record<string, unknown>): SessionRecording {
  return {
    sessionId: String(data.session_id),
    agentName: String(data.agent_name),
    startTime: new Date(String(data.start_time)),
    endTime: data.end_time ? new Date(String(data.end_time)) : null,
    interactions: ((data.interactions as Array<Record<string, unknown>>) || []).map(
      interactionRecordFromDict
    ),
    metadata: (data.metadata as Record<string, unknown>) || {},
  };
}

/**
 * Protocol for recording storage backends.
 *
 * Implement this to create custom storage (Redis, S3, database, etc.).
 */
export interface RecordingStorage {
  /**
   * Save recording to storage.
   *
   * @param recording Session recording
   */
  saveRecording(recording: SessionRecording): Promise<void>;

  /**
   * Load recording from storage.
   *
   * @param sessionId Session identifier
   * @returns Session recording if found, null otherwise
   */
  loadRecording(sessionId: string): Promise<SessionRecording | null>;

  /**
   * List recordings from storage.
   *
   * @param limit Maximum number of recordings to return
   * @param offset Offset for pagination
   * @returns List of session recordings
   */
  listRecordings(limit?: number, offset?: number): Promise<SessionRecording[]>;

  /**
   * Delete recording from storage.
   *
   * @param sessionId Session identifier
   */
  deleteRecording(sessionId: string): Promise<void>;
}

/**
 * File-based recording storage.
 *
 * Stores recordings as JSON files on disk.
 */
export class FileRecordingStorage implements RecordingStorage {
  private recordingsDir: string;

  /**
   * Create file storage.
   *
   * @param recordingsDir Directory to store recordings
   */
  constructor(recordingsDir: string = './recordings') {
    this.recordingsDir = recordingsDir;
  }

  /**
   * Ensure recordings directory exists.
   */
  private async ensureDir(): Promise<void> {
    try {
      await fs.mkdir(this.recordingsDir, { recursive: true });
    } catch (error) {
      // Directory might already exist
    }
  }

  async saveRecording(recording: SessionRecording): Promise<void> {
    await this.ensureDir();
    const filePath = path.join(this.recordingsDir, `${recording.sessionId}.json`);
    const data = JSON.stringify(sessionRecordingToDict(recording), null, 2);
    await fs.writeFile(filePath, data, 'utf-8');
  }

  async loadRecording(sessionId: string): Promise<SessionRecording | null> {
    const filePath = path.join(this.recordingsDir, `${sessionId}.json`);

    try {
      const data = await fs.readFile(filePath, 'utf-8');
      const parsed = JSON.parse(data);
      return sessionRecordingFromDict(parsed);
    } catch (error) {
      return null;
    }
  }

  async listRecordings(limit: number = 100, offset: number = 0): Promise<SessionRecording[]> {
    await this.ensureDir();

    try {
      const files = await fs.readdir(this.recordingsDir);
      const jsonFiles = files.filter(f => f.endsWith('.json'));

      // Get file stats for sorting by modification time
      const fileStats = await Promise.all(
        jsonFiles.map(async file => {
          const filePath = path.join(this.recordingsDir, file);
          const stats = await fs.stat(filePath);
          return { file, mtime: stats.mtime };
        })
      );

      // Sort by modification time (most recent first)
      fileStats.sort((a, b) => b.mtime.getTime() - a.mtime.getTime());

      // Apply pagination
      const paginatedFiles = fileStats.slice(offset, offset + limit);

      // Load recordings
      const recordings: SessionRecording[] = [];
      for (const { file } of paginatedFiles) {
        const filePath = path.join(this.recordingsDir, file);
        const data = await fs.readFile(filePath, 'utf-8');
        const parsed = JSON.parse(data);
        recordings.push(sessionRecordingFromDict(parsed));
      }

      return recordings;
    } catch (error) {
      return [];
    }
  }

  async deleteRecording(sessionId: string): Promise<void> {
    const filePath = path.join(this.recordingsDir, `${sessionId}.json`);

    try {
      await fs.unlink(filePath);
    } catch (error) {
      // File might not exist
    }
  }
}

/**
 * In-memory recording storage for testing.
 *
 * Does not persist recordings across restarts.
 */
export class InMemoryRecordingStorage implements RecordingStorage {
  private recordings: Map<string, SessionRecording> = new Map();

  async saveRecording(recording: SessionRecording): Promise<void> {
    this.recordings.set(recording.sessionId, recording);
  }

  async loadRecording(sessionId: string): Promise<SessionRecording | null> {
    return this.recordings.get(sessionId) || null;
  }

  async listRecordings(limit: number = 100, offset: number = 0): Promise<SessionRecording[]> {
    const recordings = Array.from(this.recordings.values());
    // Sort by start time (most recent first)
    recordings.sort((a, b) => b.startTime.getTime() - a.startTime.getTime());
    return recordings.slice(offset, offset + limit);
  }

  async deleteRecording(sessionId: string): Promise<void> {
    this.recordings.delete(sessionId);
  }
}

/**
 * Agent wrapper that records interactions.
 */
interface RecordingAgent extends Agent {
  /** Original session ID (optional) */
  __recordingSessionId?: string;
}

/**
 * Record agent sessions for replay and analysis.
 *
 * Automatically records all interactions with an agent,
 * storing inputs, outputs, timing, and metadata.
 */
export class SessionRecorder {
  private storage: RecordingStorage;
  private activeSessions: Map<string, SessionRecording> = new Map();

  /**
   * Create session recorder.
   *
   * @param storage Storage backend (defaults to in-memory)
   */
  constructor(storage?: RecordingStorage) {
    this.storage = storage || new InMemoryRecordingStorage();
  }

  /**
   * Wrap agent to record interactions.
   *
   * @param agent Agent to wrap
   * @param sessionId Optional session ID for all interactions
   * @returns Wrapped agent that records all interactions
   */
  wrap(agent: Agent, sessionId?: string): Agent {
    const recorder = this;

    const wrapped: RecordingAgent = {
      name: agent.name || 'recording_wrapper',
      capabilities: agent.capabilities || [],

      async process(message: Message): Promise<Message> {
        const sid = sessionId || 'default';

        // Start session if not already started
        if (!recorder.activeSessions.has(sid)) {
          await recorder.startSession(sid, wrapped.name);
        }

        // Process with timing
        const startTime = performance.now();
        const output = await agent.process(message);
        const latency = performance.now() - startTime;

        // Record interaction
        await recorder.recordInteraction(sid, message, output, latency);

        return output;
      },
    };

    if (sessionId) {
      wrapped.__recordingSessionId = sessionId;
    }

    return wrapped;
  }

  /**
   * Start recording session.
   *
   * @param sessionId Session identifier
   * @param agentName Name of agent being recorded
   * @param metadata Optional session metadata
   */
  async startSession(
    sessionId: string,
    agentName: string,
    metadata?: Record<string, unknown>
  ): Promise<void> {
    this.activeSessions.set(sessionId, {
      sessionId,
      agentName,
      startTime: new Date(),
      endTime: null,
      interactions: [],
      metadata: metadata || {},
    });
  }

  /**
   * Record single interaction.
   *
   * @param sessionId Session identifier
   * @param inputMessage Input to agent
   * @param outputMessage Agent response
   * @param latencyMs Processing time in milliseconds
   * @param metadata Optional interaction metadata
   */
  async recordInteraction(
    sessionId: string,
    inputMessage: Message,
    outputMessage: Message,
    latencyMs: number,
    metadata?: Record<string, unknown>
  ): Promise<void> {
    // Get or create session
    if (!this.activeSessions.has(sessionId)) {
      await this.startSession(sessionId, 'unknown');
    }

    const session = this.activeSessions.get(sessionId)!;

    // Create interaction record
    const record: InteractionRecord = {
      interactionId: randomUUID(),
      sessionId,
      inputMessage: messageToDict(inputMessage),
      outputMessage: messageToDict(outputMessage),
      timestamp: new Date(),
      latencyMs,
      metadata: metadata || {},
    };

    session.interactions.push(record);
  }

  /**
   * Finalize and save session recording.
   *
   * @param sessionId Session to finalize
   * @returns Session recording
   */
  async finalizeSession(sessionId: string): Promise<SessionRecording> {
    const session = this.activeSessions.get(sessionId);
    if (!session) {
      throw new Error(`No active session: ${sessionId}`);
    }

    this.activeSessions.delete(sessionId);
    session.endTime = new Date();

    // Save to storage
    await this.storage.saveRecording(session);

    return session;
  }

  /**
   * Load recording from storage.
   *
   * @param sessionId Session to load
   * @returns Session recording if found
   */
  async loadRecording(sessionId: string): Promise<SessionRecording | null> {
    return this.storage.loadRecording(sessionId);
  }

  /**
   * List all recordings.
   *
   * @param limit Maximum number of recordings to return
   * @param offset Offset for pagination
   * @returns List of session recordings
   */
  async listRecordings(limit?: number, offset?: number): Promise<SessionRecording[]> {
    return this.storage.listRecordings(limit, offset);
  }

  /**
   * Delete recording.
   *
   * @param sessionId Session to delete
   */
  async deleteRecording(sessionId: string): Promise<void> {
    return this.storage.deleteRecording(sessionId);
  }
}

/**
 * Results from replaying a session.
 */
export interface ReplayResults {
  /** Session ID for this replay */
  sessionId: string;
  /** Original session ID */
  originalSessionId: string;
  /** List of interaction results */
  interactions: ReplayInteraction[];
  /** Total latency across all interactions */
  totalLatencyMs: number;
  /** Number of errors encountered */
  errorCount: number;
}

/**
 * Result of replaying a single interaction.
 */
export interface ReplayInteraction {
  /** Input message */
  input: MessageDict;
  /** Original output from recording */
  originalOutput: MessageDict;
  /** Output from replay agent */
  replayOutput?: MessageDict;
  /** Original latency in milliseconds */
  originalLatencyMs?: number;
  /** Replay latency in milliseconds */
  replayLatencyMs?: number;
  /** Error if replay failed */
  error?: string;
}

/**
 * Comparison between two replay results.
 */
export interface ReplayComparison {
  /** Number of interactions compared */
  interactionCount: number;
  /** Latency difference in milliseconds (B - A) */
  latencyDiffMs: number;
  /** Latency difference as percentage */
  latencyDiffPercent: number;
  /** Error count difference (B - A) */
  errorDiff: number;
  /** List of output differences */
  outputDifferences: OutputDifference[];
}

/**
 * Difference between two outputs.
 */
export interface OutputDifference {
  /** Index of interaction */
  interactionIndex: number;
  /** Output from first replay */
  outputA: string;
  /** Output from second replay */
  outputB: string;
}

/**
 * Replay recorded sessions for analysis and A/B testing.
 *
 * Takes recorded session and replays it through a (possibly different)
 * agent to compare behavior.
 */
export class SessionReplay {
  /**
   * Replay session through agent.
   *
   * @param recording Session recording to replay
   * @param agent Agent to replay through
   * @param sessionId Optional session ID (defaults to original)
   * @returns Replay results with outputs and metrics
   */
  async replay(
    recording: SessionRecording,
    agent: Agent,
    sessionId?: string
  ): Promise<ReplayResults> {
    const sid = sessionId || recording.sessionId;
    const results: ReplayResults = {
      sessionId: sid,
      originalSessionId: recording.sessionId,
      interactions: [],
      totalLatencyMs: 0,
      errorCount: 0,
    };

    for (const interaction of recording.interactions) {
      // Reconstruct input message
      const inputMsg: Message = {
        role: interaction.inputMessage.role,
        content: interaction.inputMessage.content,
        metadata: interaction.inputMessage.metadata || {},
      };

      try {
        // Replay through agent
        const startTime = performance.now();
        const outputMsg = await agent.process(inputMsg);
        const latency = performance.now() - startTime;

        results.interactions.push({
          input: interaction.inputMessage,
          originalOutput: interaction.outputMessage,
          replayOutput: messageToDict(outputMsg),
          originalLatencyMs: interaction.latencyMs,
          replayLatencyMs: latency,
        });

        results.totalLatencyMs += latency;
      } catch (error) {
        results.errorCount++;
        results.interactions.push({
          input: interaction.inputMessage,
          originalOutput: interaction.outputMessage,
          error: error instanceof Error ? error.message : String(error),
        });
      }
    }

    return results;
  }

  /**
   * Compare two replay results.
   *
   * Useful for A/B testing different agent versions.
   *
   * @param resultsA First replay results
   * @param resultsB Second replay results
   * @returns Comparison metrics
   */
  compare(resultsA: ReplayResults, resultsB: ReplayResults): ReplayComparison {
    const comparison: ReplayComparison = {
      interactionCount: resultsA.interactions.length,
      latencyDiffMs: resultsB.totalLatencyMs - resultsA.totalLatencyMs,
      latencyDiffPercent:
        resultsA.totalLatencyMs > 0
          ? ((resultsB.totalLatencyMs - resultsA.totalLatencyMs) / resultsA.totalLatencyMs) * 100
          : 0,
      errorDiff: resultsB.errorCount - resultsA.errorCount,
      outputDifferences: [],
    };

    // Compare outputs
    for (let i = 0; i < resultsA.interactions.length; i++) {
      const ia = resultsA.interactions[i];
      const ib = resultsB.interactions[i];

      if (ia.error || ib.error) {
        continue;
      }

      const outputA = ia.replayOutput?.content || '';
      const outputB = ib.replayOutput?.content || '';

      if (outputA !== outputB) {
        comparison.outputDifferences.push({
          interactionIndex: i,
          outputA,
          outputB,
        });
      }
    }

    return comparison;
  }
}
