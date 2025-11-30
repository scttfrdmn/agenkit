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
use agenkit::evaluation::recorder::{SessionRecorder, FileRecordingStorage};
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

    let interactions = vec![
        "Hello, how are you?",
        "What's the weather like today?",
        "Tell me a joke",
        "Thank you!",
    ];

    println!("Recording session: {}", session_id);
    println!("Interactions:");

    for (i, input) in interactions.iter().enumerate() {
        let mut metadata = HashMap::new();
        metadata.insert("session_id".to_string(), serde_json::json!(session_id));

        let message = Message::with_text("user", input)
            .with_metadata_map(metadata);

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

    // Step 4: Finalize and save recording
    println!("Step 4: Finalizing Recording");
    println!("-----------------------------");
    let recording = recorder.finalize_session(session_id).await?;

    println!("✓ Session recorded: {}", recording.session_id);
    println!("  Interactions: {}", recording.interaction_count());
    println!("  Duration: {:.2}s", recording.duration_seconds().unwrap_or(0.0));
    println!("  Total Latency: {:.0}ms\n", recording.total_latency_ms());

    // Step 5: Load and replay session
    println!("Step 5: Loading and Replaying Session");
    println!("--------------------------------------");
    let loaded_recording = recorder.load_recording(session_id).await?;

    match loaded_recording {
        Some(ref rec) => {
            println!("✓ Loaded recording: {}", rec.session_id);
            println!("  Agent: {}", rec.agent_name);
            println!("  Interactions: {}\n", rec.interactions.len());

            // Replay with original agent
            println!("Replaying with original agent (v1)...");
            let results_v1 = recorder.replay(&rec, agent_v1.clone(), None).await?;

            println!("✓ Replay complete");
            println!("  Total Latency: {:.0}ms",
                results_v1.get("total_latency_ms").and_then(|v| v.as_f64()).unwrap_or(0.0));
            println!("  Errors: {}\n",
                results_v1.get("error_count").and_then(|v| v.as_i64()).unwrap_or(0));

            // Step 6: Replay with different agent version (A/B testing)
            println!("Step 6: A/B Testing with Different Agent Version");
            println!("-------------------------------------------------");
            let agent_v2 = std::sync::Arc::new(MockAgent::new("echo-agent", "v2"));

            println!("Replaying with new agent version (v2)...");
            let results_v2 = recorder.replay(&rec, agent_v2, None).await?;

            println!("✓ Replay complete");
            println!("  Total Latency: {:.0}ms",
                results_v2.get("total_latency_ms").and_then(|v| v.as_f64()).unwrap_or(0.0));
            println!("  Errors: {}\n",
                results_v2.get("error_count").and_then(|v| v.as_i64()).unwrap_or(0));

            // Step 7: Compare results
            println!("Step 7: Comparing Results");
            println!("-------------------------");
            let comparison = recorder.compare(&results_v1, &results_v2);

            println!("Comparison:");
            println!("  Interactions: {}",
                comparison.get("interaction_count").and_then(|v| v.as_i64()).unwrap_or(0));
            println!("  Latency Difference: {:.0}ms ({:.1}%)",
                comparison.get("latency_diff_ms").and_then(|v| v.as_f64()).unwrap_or(0.0),
                comparison.get("latency_diff_percent").and_then(|v| v.as_f64()).unwrap_or(0.0));
            println!("  Error Difference: {}",
                comparison.get("error_diff").and_then(|v| v.as_i64()).unwrap_or(0));

            let output_diffs = comparison.get("output_differences")
                .and_then(|v| v.as_array())
                .map(|a| a.len())
                .unwrap_or(0);
            println!("  Output Differences: {}", output_diffs);

            if output_diffs > 0 {
                println!("\nDetailed Output Differences:");
                if let Some(diffs) = comparison.get("output_differences").and_then(|v| v.as_array()) {
                    for diff in diffs {
                        let idx = diff.get("interaction_index").and_then(|v| v.as_i64()).unwrap_or(0);
                        let output_a = diff.get("output_a").and_then(|v| v.as_str()).unwrap_or("");
                        let output_b = diff.get("output_b").and_then(|v| v.as_str()).unwrap_or("");
                        println!("  Interaction {}:", idx + 1);
                        println!("    v1: {}", output_a);
                        println!("    v2: {}", output_b);
                    }
                }
            }
            println!();
        }
        None => {
            println!("Recording not found");
        }
    }

    // Step 8: List all recordings
    println!("Step 8: Listing All Recordings");
    println!("-------------------------------");
    let recordings = recorder.list_recordings(10, 0).await?;

    println!("Found {} recordings:", recordings.len());
    for (i, rec) in recordings.iter().enumerate() {
        println!("  {}. {} ({})", i + 1, rec.session_id, rec.agent_name);
        println!("     Interactions: {}, Duration: {:.2}s",
            rec.interaction_count(),
            rec.duration_seconds().unwrap_or(0.0));
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
