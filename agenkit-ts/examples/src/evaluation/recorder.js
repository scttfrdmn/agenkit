"use strict";
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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.SessionReplay = exports.SessionRecorder = exports.InMemoryRecordingStorage = exports.FileRecordingStorage = void 0;
exports.getSessionDuration = getSessionDuration;
exports.getTotalLatency = getTotalLatency;
exports.interactionRecordToDict = interactionRecordToDict;
exports.interactionRecordFromDict = interactionRecordFromDict;
exports.sessionRecordingToDict = sessionRecordingToDict;
exports.sessionRecordingFromDict = sessionRecordingFromDict;
const fs_1 = require("fs");
const path_1 = __importDefault(require("path"));
const crypto_1 = require("crypto");
/**
 * Convert message to dictionary.
 *
 * @param message Message to convert
 * @returns Dictionary representation
 */
function messageToDict(message) {
    return {
        role: message.role,
        content: message.content,
        metadata: message.metadata || {},
    };
}
/**
 * Calculate session duration in seconds.
 *
 * @param recording Session recording
 * @returns Duration in seconds (0 if session not ended)
 */
function getSessionDuration(recording) {
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
function getTotalLatency(recording) {
    return recording.interactions.reduce((sum, interaction) => sum + interaction.latencyMs, 0);
}
/**
 * Convert interaction record to plain object.
 *
 * @param record Interaction record
 * @returns Plain object representation
 */
function interactionRecordToDict(record) {
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
function interactionRecordFromDict(data) {
    return {
        interactionId: String(data.interaction_id),
        sessionId: String(data.session_id),
        inputMessage: data.input_message,
        outputMessage: data.output_message,
        timestamp: new Date(String(data.timestamp)),
        latencyMs: Number(data.latency_ms),
        metadata: data.metadata || {},
    };
}
/**
 * Convert session recording to plain object.
 *
 * @param recording Session recording
 * @returns Plain object representation
 */
function sessionRecordingToDict(recording) {
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
function sessionRecordingFromDict(data) {
    return {
        sessionId: String(data.session_id),
        agentName: String(data.agent_name),
        startTime: new Date(String(data.start_time)),
        endTime: data.end_time ? new Date(String(data.end_time)) : null,
        interactions: (data.interactions || []).map(interactionRecordFromDict),
        metadata: data.metadata || {},
    };
}
/**
 * File-based recording storage.
 *
 * Stores recordings as JSON files on disk.
 */
class FileRecordingStorage {
    /**
     * Create file storage.
     *
     * @param recordingsDir Directory to store recordings
     */
    constructor(recordingsDir = './recordings') {
        this.recordingsDir = recordingsDir;
    }
    /**
     * Ensure recordings directory exists.
     */
    async ensureDir() {
        try {
            await fs_1.promises.mkdir(this.recordingsDir, { recursive: true });
        }
        catch (error) {
            // Directory might already exist
        }
    }
    async saveRecording(recording) {
        await this.ensureDir();
        const filePath = path_1.default.join(this.recordingsDir, `${recording.sessionId}.json`);
        const data = JSON.stringify(sessionRecordingToDict(recording), null, 2);
        await fs_1.promises.writeFile(filePath, data, 'utf-8');
    }
    async loadRecording(sessionId) {
        const filePath = path_1.default.join(this.recordingsDir, `${sessionId}.json`);
        try {
            const data = await fs_1.promises.readFile(filePath, 'utf-8');
            const parsed = JSON.parse(data);
            return sessionRecordingFromDict(parsed);
        }
        catch (error) {
            return null;
        }
    }
    async listRecordings(limit = 100, offset = 0) {
        await this.ensureDir();
        try {
            const files = await fs_1.promises.readdir(this.recordingsDir);
            const jsonFiles = files.filter(f => f.endsWith('.json'));
            // Get file stats for sorting by modification time
            const fileStats = await Promise.all(jsonFiles.map(async (file) => {
                const filePath = path_1.default.join(this.recordingsDir, file);
                const stats = await fs_1.promises.stat(filePath);
                return { file, mtime: stats.mtime };
            }));
            // Sort by modification time (most recent first)
            fileStats.sort((a, b) => b.mtime.getTime() - a.mtime.getTime());
            // Apply pagination
            const paginatedFiles = fileStats.slice(offset, offset + limit);
            // Load recordings
            const recordings = [];
            for (const { file } of paginatedFiles) {
                const filePath = path_1.default.join(this.recordingsDir, file);
                const data = await fs_1.promises.readFile(filePath, 'utf-8');
                const parsed = JSON.parse(data);
                recordings.push(sessionRecordingFromDict(parsed));
            }
            return recordings;
        }
        catch (error) {
            return [];
        }
    }
    async deleteRecording(sessionId) {
        const filePath = path_1.default.join(this.recordingsDir, `${sessionId}.json`);
        try {
            await fs_1.promises.unlink(filePath);
        }
        catch (error) {
            // File might not exist
        }
    }
}
exports.FileRecordingStorage = FileRecordingStorage;
/**
 * In-memory recording storage for testing.
 *
 * Does not persist recordings across restarts.
 */
class InMemoryRecordingStorage {
    constructor() {
        this.recordings = new Map();
    }
    async saveRecording(recording) {
        this.recordings.set(recording.sessionId, recording);
    }
    async loadRecording(sessionId) {
        return this.recordings.get(sessionId) || null;
    }
    async listRecordings(limit = 100, offset = 0) {
        const recordings = Array.from(this.recordings.values());
        // Sort by start time (most recent first)
        recordings.sort((a, b) => b.startTime.getTime() - a.startTime.getTime());
        return recordings.slice(offset, offset + limit);
    }
    async deleteRecording(sessionId) {
        this.recordings.delete(sessionId);
    }
}
exports.InMemoryRecordingStorage = InMemoryRecordingStorage;
/**
 * Record agent sessions for replay and analysis.
 *
 * Automatically records all interactions with an agent,
 * storing inputs, outputs, timing, and metadata.
 */
class SessionRecorder {
    /**
     * Create session recorder.
     *
     * @param storage Storage backend (defaults to in-memory)
     */
    constructor(storage) {
        this.activeSessions = new Map();
        this.storage = storage || new InMemoryRecordingStorage();
    }
    /**
     * Wrap agent to record interactions.
     *
     * @param agent Agent to wrap
     * @param sessionId Optional session ID for all interactions
     * @returns Wrapped agent that records all interactions
     */
    wrap(agent, sessionId) {
        const recorder = this;
        const wrapped = {
            name: agent.name || 'recording_wrapper',
            capabilities: agent.capabilities || [],
            async process(message) {
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
    async startSession(sessionId, agentName, metadata) {
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
    async recordInteraction(sessionId, inputMessage, outputMessage, latencyMs, metadata) {
        // Get or create session
        if (!this.activeSessions.has(sessionId)) {
            await this.startSession(sessionId, 'unknown');
        }
        const session = this.activeSessions.get(sessionId);
        // Create interaction record
        const record = {
            interactionId: (0, crypto_1.randomUUID)(),
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
    async finalizeSession(sessionId) {
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
    async loadRecording(sessionId) {
        return this.storage.loadRecording(sessionId);
    }
    /**
     * List all recordings.
     *
     * @param limit Maximum number of recordings to return
     * @param offset Offset for pagination
     * @returns List of session recordings
     */
    async listRecordings(limit, offset) {
        return this.storage.listRecordings(limit, offset);
    }
    /**
     * Delete recording.
     *
     * @param sessionId Session to delete
     */
    async deleteRecording(sessionId) {
        return this.storage.deleteRecording(sessionId);
    }
}
exports.SessionRecorder = SessionRecorder;
/**
 * Replay recorded sessions for analysis and A/B testing.
 *
 * Takes recorded session and replays it through a (possibly different)
 * agent to compare behavior.
 */
class SessionReplay {
    /**
     * Replay session through agent.
     *
     * @param recording Session recording to replay
     * @param agent Agent to replay through
     * @param sessionId Optional session ID (defaults to original)
     * @returns Replay results with outputs and metrics
     */
    async replay(recording, agent, sessionId) {
        const sid = sessionId || recording.sessionId;
        const results = {
            sessionId: sid,
            originalSessionId: recording.sessionId,
            interactions: [],
            totalLatencyMs: 0,
            errorCount: 0,
        };
        for (const interaction of recording.interactions) {
            // Reconstruct input message
            const inputMsg = {
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
            }
            catch (error) {
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
    compare(resultsA, resultsB) {
        const comparison = {
            interactionCount: resultsA.interactions.length,
            latencyDiffMs: resultsB.totalLatencyMs - resultsA.totalLatencyMs,
            latencyDiffPercent: resultsA.totalLatencyMs > 0
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
exports.SessionReplay = SessionReplay;
