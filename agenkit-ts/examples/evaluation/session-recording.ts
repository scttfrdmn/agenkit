/**
 * Session Recording and Replay Example
 *
 * Session recording captures all agent interactions (inputs, outputs, timing)
 * for later replay, analysis, and A/B testing. This is essential for:
 * - Debugging agent behavior
 * - Comparing different agent versions
 * - Reproducing issues
 * - Building regression test suites
 * - Analyzing conversation patterns
 *
 * Run with: npx tsx examples/evaluation/session-recording.ts
 */

import {
  SessionRecorder,
  FileRecordingStorage,
  SessionReplay,
} from '../../src/evaluation';
import { Agent, Message } from '../../src/core/interfaces';

/**
 * Mock agent for demonstration purposes.
 */
class MockAgent implements Agent {
  constructor(
    private name: string,
    private version: string
  ) {}

  getName(): string {
    return this.name;
  }

  getCapabilities(): string[] {
    return ['chat'];
  }

  async process(message: Message, sessionId?: string): Promise<Message> {
    // Simple echo agent with version-specific behavior
    const response = `[${this.version}] You said: ${message.content}`;

    return {
      role: 'assistant',
      content: response,
      metadata: {},
    };
  }
}

async function main() {
  console.log('Session Recording and Replay Example');
  console.log('=====================================\n');

  // Step 1: Create recorder with file storage
  console.log('Step 1: Setting Up Session Recorder');
  console.log('------------------------------------');
  const storage = new FileRecordingStorage('./recordings');
  const recorder = new SessionRecorder(storage);
  console.log('✓ Recorder created with file storage: ./recordings/\n');

  // Step 2: Create agent and wrap with recorder
  console.log('Step 2: Creating and Wrapping Agent');
  console.log('------------------------------------');
  const agentV1 = new MockAgent('echo-agent', 'v1');
  const wrappedAgent = recorder.wrap(agentV1);
  console.log('✓ Agent wrapped with recorder\n');

  // Step 3: Record a session
  console.log('Step 3: Recording Agent Session');
  console.log('--------------------------------');
  const sessionId = 'demo-session-001';

  const interactions = [
    'Hello, how are you?',
    "What's the weather like today?",
    'Tell me a joke',
    'Thank you!',
  ];

  console.log(`Recording session: ${sessionId}`);
  console.log('Interactions:');

  for (let i = 0; i < interactions.length; i++) {
    const input = interactions[i];
    const message: Message = {
      role: 'user',
      content: input,
      metadata: {
        session_id: sessionId,
      },
    };

    const response = await wrappedAgent.process(message, sessionId);
    console.log(`  ${i + 1}. User: ${input}`);
    console.log(`     Agent: ${response.content}`);
  }
  console.log();

  // Step 4: Finalize and save recording
  console.log('Step 4: Finalizing Recording');
  console.log('-----------------------------');
  const recording = await recorder.finalizeSession(sessionId);

  console.log(`✓ Session recorded: ${recording.sessionId}`);
  console.log(`  Interactions: ${recording.interactions.length}`);
  console.log(
    `  Duration: ${((recording.endTime!.getTime() - recording.startTime.getTime()) / 1000).toFixed(2)}s`
  );

  const totalLatency = recording.interactions.reduce(
    (sum, i) => sum + i.latencyMs,
    0
  );
  console.log(`  Total Latency: ${totalLatency.toFixed(0)}ms\n`);

  // Step 5: Load and replay session
  console.log('Step 5: Loading and Replaying Session');
  console.log('--------------------------------------');
  const loadedRecording = await recorder.loadRecording(sessionId);

  if (!loadedRecording) {
    console.log('Recording not found');
    return;
  }

  console.log(`✓ Loaded recording: ${loadedRecording.sessionId}`);
  console.log(`  Agent: ${loadedRecording.agentName}`);
  console.log(`  Interactions: ${loadedRecording.interactions.length}\n`);

  // Replay with original agent
  const replay = new SessionReplay();
  console.log('Replaying with original agent (v1)...');
  const resultsV1 = await replay.replay(loadedRecording, agentV1);

  console.log('✓ Replay complete');
  console.log(`  Total Latency: ${resultsV1.totalLatencyMs.toFixed(0)}ms`);
  console.log(`  Errors: ${resultsV1.errorCount}\n`);

  // Step 6: Replay with different agent version (A/B testing)
  console.log('Step 6: A/B Testing with Different Agent Version');
  console.log('-------------------------------------------------');
  const agentV2 = new MockAgent('echo-agent', 'v2');

  console.log('Replaying with new agent version (v2)...');
  const resultsV2 = await replay.replay(loadedRecording, agentV2);

  console.log('✓ Replay complete');
  console.log(`  Total Latency: ${resultsV2.totalLatencyMs.toFixed(0)}ms`);
  console.log(`  Errors: ${resultsV2.errorCount}\n`);

  // Step 7: Compare results
  console.log('Step 7: Comparing Results');
  console.log('-------------------------');
  const comparison = replay.compare(resultsV1, resultsV2);

  console.log('Comparison:');
  console.log(`  Interactions: ${comparison.interactionCount}`);
  console.log(
    `  Latency Difference: ${comparison.latencyDiffMs.toFixed(0)}ms (${comparison.latencyDiffPercent.toFixed(1)}%)`
  );
  console.log(`  Error Difference: ${comparison.errorDiff}`);
  console.log(`  Output Differences: ${comparison.outputDifferences.length}`);

  if (comparison.outputDifferences.length > 0) {
    console.log('\nDetailed Output Differences:');
    comparison.outputDifferences.forEach(diff => {
      console.log(`  Interaction ${diff.interactionIndex + 1}:`);
      console.log(`    v1: ${diff.outputA}`);
      console.log(`    v2: ${diff.outputB}`);
    });
  }
  console.log();

  // Step 8: List all recordings
  console.log('Step 8: Listing All Recordings');
  console.log('-------------------------------');
  const recordings = await recorder.listRecordings(10, 0);

  console.log(`Found ${recordings.length} recordings:`);
  recordings.forEach((rec, i) => {
    const duration = rec.endTime
      ? ((rec.endTime.getTime() - rec.startTime.getTime()) / 1000).toFixed(2)
      : '0.00';
    console.log(`  ${i + 1}. ${rec.sessionId} (${rec.agentName})`);
    console.log(
      `     Interactions: ${rec.interactions.length}, Duration: ${duration}s`
    );
  });
  console.log();

  // Summary
  console.log('='.repeat(70));
  console.log('Summary: Session Recording and Replay');
  console.log('='.repeat(70));

  console.log('\nKey Capabilities:');
  console.log('1. Record: Capture all agent interactions automatically');
  console.log('2. Store: Save to file, memory, or custom storage backend');
  console.log('3. Replay: Re-run recorded sessions through any agent');
  console.log('4. Compare: A/B test different agent versions');
  console.log('5. Analyze: Inspect timing, outputs, and errors');

  console.log('\nStorage Backends:');
  console.log('- FileRecordingStorage: JSON files on disk (production)');
  console.log('- InMemoryRecordingStorage: In-memory (testing)');
  console.log('- Custom: Implement RecordingStorage interface (Redis, S3, etc.)');

  console.log('\nRecording Details:');
  console.log('- Session ID: Unique identifier for grouping interactions');
  console.log('- Interactions: Input message, output message, latency');
  console.log('- Metadata: Custom key-value pairs per session/interaction');
  console.log('- Timestamps: ISO 8601 format for precise timing');

  console.log('\nBest Practices:');
  console.log('1. Wrap agents early in development lifecycle');
  console.log('2. Use descriptive session IDs (e.g., user-id-timestamp)');
  console.log('3. Finalize sessions promptly to free memory');
  console.log('4. Store recordings in version control as regression tests');
  console.log('5. Replay after every code change to detect regressions');
  console.log('6. Use metadata to tag recordings (version, feature, user)');

  console.log('\nReal-World Applications:');
  console.log('- Debugging: Reproduce exact user interaction that caused error');
  console.log('- Regression Testing: Verify new code doesn\'t break old sessions');
  console.log('- A/B Testing: Compare agent versions on identical inputs');
  console.log('- Quality Assurance: Review agent responses before deployment');
  console.log('- Training: Build datasets from production interactions');
  console.log('- Compliance: Audit trail of all agent interactions');

  console.log('\nPerformance:');
  console.log('- Overhead: <1ms per interaction for recording');
  console.log('- Storage: ~1KB per interaction (JSON)');
  console.log('- Replay: Same speed as original (can be parallelized)');
}

main().catch(console.error);
