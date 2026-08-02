//! Session Recording and Replay Example
//!
//! Session recording captures all agent interactions (inputs, outputs, timing)
//! for later replay, analysis, and A/B testing. This is essential for:
//!   - Debugging agent behavior
//!   - Comparing different agent versions
//!   - Reproducing issues
//!   - Building regression test suites
//!   - Analyzing conversation patterns
//!
//! Run with: cargo run --example evaluation-session-recording

use agenkit::core::{Agent, AgentError, Message};
use agenkit::evaluation::recorder::{FileRecordingStorage, SessionRecorder};
use async_trait::async_trait;
use std::collections::HashMap;

/// MockAgent is a simple agent for demonstration.
struct MockAgent {
    name: String,
    version: String,
}

impl MockAgent {
    fn new(name: &str, version: &str) -> Self {
        Self {
            name: name.to_string(),
            version: version.to_string(),
        }
    }
}

#[async_trait]
impl Agent for MockAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Simple echo agent with version-specific behavior
        let content = message.content_as_str().unwrap_or("");
        let response = format!("[{}] You said: {}", self.version, content);

        Ok(Message::with_text("assistant", &response))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Session Recording and Replay Example");
    println!("=====================================\n");

    // Step 1: Create recorder with file storage
    println!("Step 1: Setting Up Session Recorder");
    println!("------------------------------------");
    let storage = FileRecordingStorage::new("./recordings");
    let recorder = SessionRecorder::new(Some(Box::new(storage)));
    println!("✓ Recorder created with file storage: ./recordings/\n");

    // Step 2: Create agent and wrap with recorder
    println!("Step 2: Creating and Wrapping Agent");
    println!("------------------------------------");
    let agent_v1 = std::sync::Arc::new(MockAgent::new("echo-agent", "v1"));
    let wrapped_agent = recorder.wrap(agent_v1.clone());
    println!("✓ Agent wrapped with recorder\n");

    // Step 3: Record a session
    println!("Step 3: Recording Agent Session");
    println!("--------------------------------");
    let session_id = "demo-session-001";

    let interactions = ["Hello, how are you?",
        "What's the weather like today?",
        "Tell me a joke",
        "Thank you!"];

    println!("Recording session: {}", session_id);
    println!("Interactions:");

    for (i, input) in interactions.iter().enumerate() {
        let message = Message::with_text("user", *input)
            .with_metadata("session_id", serde_json::json!(session_id));

        match wrapped_agent.process(message).await {
            Ok(response) => {
                println!("  {}. User: {}", i + 1, input);
                println!("     Agent: {}", response.content_as_str().unwrap_or(""));
            }
            Err(e) => {
                println!("  Error: {:?}", e);
            }
        }
    }
    println!();

    // Step 4: Inspect the active recording, then finalize (save) it.
    //
    // `get_session` returns a snapshot of the in-progress recording;
    // `finalize_session` then persists it to the configured storage.
    println!("Step 4: Finalizing Recording");
    println!("-----------------------------");
    let recording = recorder
        .get_session(session_id)
        .expect("session should be active before finalize");
    recorder.finalize_session(session_id).await?;

    println!("✓ Session recorded: {}", recording.session_id);
    println!("  Agent: {}", recording.agent_name);
    println!("  Interactions: {}", recording.interaction_count());
    println!(
        "  Duration: {:.2}s",
        recording.duration_seconds().unwrap_or(0.0)
    );
    println!("  Total Latency: {:.0}ms\n", recording.total_latency_ms());

    // Step 5: Replay the recorded inputs through the original agent (v1).
    //
    // Replaying re-processes each recorded input message through an agent so
    // its outputs can be compared. We do this directly against the recording's
    // interaction log.
    println!("Step 5: Replaying Session");
    println!("--------------------------");

    async fn replay(
        agent: &std::sync::Arc<MockAgent>,
        recording: &agenkit::evaluation::recorder::SessionRecording,
    ) -> Result<(Vec<String>, f64), AgentError> {
        let mut outputs = Vec::new();
        let mut total_latency_ms = 0.0;
        for interaction in &recording.interactions {
            let input = Message {
                role: "user".to_string(),
                content: interaction.input_message.clone(),
                metadata: HashMap::new(),
                timestamp: interaction.timestamp,
            };
            let start = std::time::Instant::now();
            let response = agent.process(input).await?;
            total_latency_ms += start.elapsed().as_secs_f64() * 1000.0;
            outputs.push(response.content_as_str().unwrap_or("").to_string());
        }
        Ok((outputs, total_latency_ms))
    }

    println!("Replaying with original agent (v1)...");
    let (outputs_v1, latency_v1) = replay(&agent_v1, &recording).await?;
    println!("✓ Replay complete");
    println!("  Total Latency: {:.0}ms\n", latency_v1);

    // Step 6: Replay with a different agent version (A/B testing)
    println!("Step 6: A/B Testing with Different Agent Version");
    println!("-------------------------------------------------");
    let agent_v2 = std::sync::Arc::new(MockAgent::new("echo-agent", "v2"));

    println!("Replaying with new agent version (v2)...");
    let (outputs_v2, latency_v2) = replay(&agent_v2, &recording).await?;
    println!("✓ Replay complete");
    println!("  Total Latency: {:.0}ms\n", latency_v2);

    // Step 7: Compare results
    println!("Step 7: Comparing Results");
    println!("-------------------------");

    let latency_diff_ms = latency_v2 - latency_v1;
    let latency_diff_percent = if latency_v1 > 0.0 {
        latency_diff_ms / latency_v1 * 100.0
    } else {
        0.0
    };
    let output_diffs: Vec<usize> = (0..outputs_v1.len())
        .filter(|&i| outputs_v1[i] != outputs_v2[i])
        .collect();

    println!("Comparison:");
    println!("  Interactions: {}", outputs_v1.len());
    println!(
        "  Latency Difference: {:.0}ms ({:.1}%)",
        latency_diff_ms, latency_diff_percent
    );
    println!("  Output Differences: {}", output_diffs.len());

    if !output_diffs.is_empty() {
        println!("\nDetailed Output Differences:");
        for &i in &output_diffs {
            println!("  Interaction {}:", i + 1);
            println!("    v1: {}", outputs_v1[i]);
            println!("    v2: {}", outputs_v2[i]);
        }
    }
    println!();

    // Summary
    println!("{}", "=".repeat(70));
    println!("Summary: Session Recording and Replay");
    println!("{}", "=".repeat(70));

    println!("\nKey Capabilities:");
    println!("1. Record: Capture all agent interactions automatically");
    println!("2. Store: Save to file, memory, or custom storage backend");
    println!("3. Replay: Re-run recorded sessions through any agent");
    println!("4. Compare: A/B test different agent versions");
    println!("5. Analyze: Inspect timing, outputs, and errors");

    println!("\nStorage Backends:");
    println!("- FileRecordingStorage: JSON files on disk (production)");
    println!("- InMemoryRecordingStorage: In-memory (testing)");
    println!("- Custom: Implement RecordingStorage trait (Redis, S3, etc.)");

    println!("\nRecording Details:");
    println!("- Session ID: Unique identifier for grouping interactions");
    println!("- Interactions: Input message, output message, latency");
    println!("- Metadata: Custom key-value pairs per session/interaction");
    println!("- Timestamps: RFC3339 format for precise timing");

    println!("\nBest Practices:");
    println!("1. Wrap agents early in development lifecycle");
    println!("2. Use descriptive session IDs (e.g., user-id-timestamp)");
    println!("3. Finalize sessions promptly to free memory");
    println!("4. Store recordings in version control as regression tests");
    println!("5. Replay after every code change to detect regressions");
    println!("6. Use metadata to tag recordings (version, feature, user)");

    println!("\nReal-World Applications:");
    println!("- Debugging: Reproduce exact user interaction that caused error");
    println!("- Regression Testing: Verify new code doesn't break old sessions");
    println!("- A/B Testing: Compare agent versions on identical inputs");
    println!("- Quality Assurance: Review agent responses before deployment");
    println!("- Training: Build datasets from production interactions");
    println!("- Compliance: Audit trail of all agent interactions");

    println!("\nPerformance:");
    println!("- Overhead: <1ms per interaction for recording");
    println!("- Storage: ~1KB per interaction (JSON)");
    println!("- Replay: Same speed as original (can be parallelized)");
    println!("- Thread-safe: Safe for concurrent recording");

    Ok(())
}
