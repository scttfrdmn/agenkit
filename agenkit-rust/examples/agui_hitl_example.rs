///! AG-UI Human-in-the-Loop Example
///!
///! Demonstrates AG-UI protocol integration with the human-in-the-loop pattern.
///! Shows how agents can request human approval via Interrupt events.
///!
///! This example shows:
///! - Creating a HumanInLoopAgent
///! - Wrapping it with AGUIHumanInLoopAdapter
///! - Streaming events with approval requests
///! - Interrupt events for low-confidence responses
///! - Approval workflow visualization
///!
///! # Running
///!
///! ```bash
///! cargo run --example agui_hitl_example
///! ```
use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::human_in_loop::{simple_approval_func, HumanInLoopAgent, HumanInLoopConfig};
use agenkit::protocols::agui::adapter::AGUIAdapterConfig;
use agenkit::protocols::agui::events::{AGUIEvent, EventType};
use agenkit::protocols::agui::hitl::{AGUIHumanInLoopAdapter, AGUIHumanInLoopConfig};
use async_trait::async_trait;
use futures::stream::StreamExt;
use std::sync::Arc;

/// Mock agent that returns responses with varying confidence levels.
struct ConfidenceAgent {
    name: String,
    response: String,
    confidence: f64,
}

impl ConfidenceAgent {
    fn new(name: impl Into<String>, response: impl Into<String>, confidence: f64) -> Self {
        Self {
            name: name.into(),
            response: response.into(),
            confidence,
        }
    }
}

#[async_trait]
impl Agent for ConfidenceAgent {
    fn name(&self) -> &str {
        &self.name
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["confidence-based".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");
        let response = format!("{} (input was: {})", self.response, content);

        Ok(Message::with_text("assistant", &response)
            .with_metadata("confidence", serde_json::json!(self.confidence)))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("AG-UI Human-in-the-Loop Example");
    println!("================================\n");

    // Example 1: High confidence - no approval needed
    println!("Example 1: High Confidence Response (No Approval Needed)");
    println!("--------------------------------------------------------");
    high_confidence_example().await?;

    println!("\n");

    // Example 2: Low confidence - approval requested
    println!("Example 2: Low Confidence Response (Approval Requested)");
    println!("-------------------------------------------------------");
    low_confidence_example().await?;

    println!("\n");

    // Example 3: Rejected response
    println!("Example 3: Low Confidence with Rejection");
    println!("-----------------------------------------");
    rejected_approval_example().await?;

    Ok(())
}

/// Example 1: High confidence response bypasses approval.
async fn high_confidence_example() -> Result<(), Box<dyn std::error::Error>> {
    // Create an agent with high confidence
    let agent = Arc::new(ConfidenceAgent::new(
        "HighConfidenceAgent",
        "I am very confident about this response",
        0.95, // High confidence
    ));

    // Wrap with human-in-loop (threshold 0.8)
    let hil_agent = HumanInLoopAgent::new(HumanInLoopConfig {
        agent,
        approval_threshold: 0.8,
        approval_func: simple_approval_func(true), // Auto-approve
        confidence_key: "confidence".to_string(),
    })?;

    // Wrap with AG-UI adapter
    let adapter = AGUIHumanInLoopAdapter::new(
        Arc::new(hil_agent),
        AGUIHumanInLoopConfig {
            base_config: AGUIAdapterConfig {
                agent_name: Some("HighConfidenceDemo".to_string()),
                chunk_size: 50,
            },
            emit_interrupts: true,
        },
    );

    // Stream events
    let message = Message::with_text("user", "What is 2+2?");
    let mut event_stream = adapter.stream_events(message, None, false).await;

    println!("Streaming events...\n");

    let mut has_interrupt = false;
    while let Some(event) = event_stream.next().await {
        match event.event_type() {
            EventType::TextMessageStart => {
                println!("  ✓ Message started");
            }
            EventType::TextMessageChunk => {
                let json = event.to_json();
                if let Some(content) = json.get("content") {
                    println!("  ✓ Content: {}", content);
                }
            }
            EventType::TextMessageComplete => {
                println!("  ✓ Message complete");
                let json = event.to_json();
                if let Some(metadata) = json.get("response_metadata") {
                    if let Some(approval_status) = metadata.get("approval_status") {
                        println!("    Approval Status: {}", approval_status);
                    }
                }
            }
            EventType::Interrupt => {
                has_interrupt = true;
                println!("  ! Interrupt Event (Approval Request)");
                let json = event.to_json();
                if let Some(context) = json.get("context") {
                    if let Some(confidence) = context.get("confidence") {
                        println!("    Confidence: {}", confidence);
                    }
                }
            }
            _ => {}
        }
    }

    if has_interrupt {
        println!("\n⚠️  Approval was requested (unexpected for high confidence)");
    } else {
        println!("\n✓ No approval needed - confidence was high enough");
    }

    Ok(())
}

/// Example 2: Low confidence response triggers approval request.
async fn low_confidence_example() -> Result<(), Box<dyn std::error::Error>> {
    // Create an agent with low confidence
    let agent = Arc::new(ConfidenceAgent::new(
        "LowConfidenceAgent",
        "I'm not very sure about this",
        0.6, // Low confidence
    ));

    // Wrap with human-in-loop (threshold 0.8)
    let hil_agent = HumanInLoopAgent::new(HumanInLoopConfig {
        agent,
        approval_threshold: 0.8,
        approval_func: simple_approval_func(true), // Auto-approve for demo
        confidence_key: "confidence".to_string(),
    })?;

    // Wrap with AG-UI adapter
    let adapter = AGUIHumanInLoopAdapter::new(
        Arc::new(hil_agent),
        AGUIHumanInLoopConfig {
            base_config: AGUIAdapterConfig {
                agent_name: Some("LowConfidenceDemo".to_string()),
                chunk_size: 50,
            },
            emit_interrupts: true,
        },
    );

    // Stream events
    let message = Message::with_text("user", "Is this safe?");
    let mut event_stream = adapter.stream_events(message, None, false).await;

    println!("Streaming events...\n");

    let mut interrupt_count = 0;
    while let Some(event) = event_stream.next().await {
        match event.event_type() {
            EventType::TextMessageStart => {
                println!("  ✓ Message started");
            }
            EventType::Interrupt => {
                interrupt_count += 1;
                println!("  🔔 Interrupt Event #{}:", interrupt_count);
                let json = event.to_json();

                if let Some(message) = json.get("message") {
                    println!("    Message: {}", message);
                }

                if let Some(context) = json.get("context") {
                    if let Some(confidence) = context.get("confidence") {
                        println!("    Confidence: {}", confidence);
                    }
                    if let Some(threshold) = context.get("threshold") {
                        println!("    Threshold: {}", threshold);
                    }
                    if let Some(shortfall) = context.get("confidence_shortfall") {
                        println!("    Shortfall: {}", shortfall);
                    }
                    if let Some(status) = context.get("approval_status") {
                        println!("    Status: {}", status);
                    }
                }

                if let Some(actions) = json.get("available_actions") {
                    println!("    Available Actions: {}", actions);
                }
            }
            EventType::TextMessageChunk => {
                let json = event.to_json();
                if let Some(content) = json.get("content") {
                    println!("  ✓ Content: {}", content);
                }
            }
            EventType::TextMessageComplete => {
                println!("  ✓ Message complete");
                let json = event.to_json();
                if let Some(approval_requested) = json.get("approval_requested") {
                    println!("    Approval Requested: {}", approval_requested);
                }
            }
            _ => {}
        }
    }

    if interrupt_count > 0 {
        println!("\n✓ Approval was requested as expected (confidence below threshold)");
    } else {
        println!("\n⚠️  No approval requested (unexpected)");
    }

    Ok(())
}

/// Example 3: Low confidence response that gets rejected.
async fn rejected_approval_example() -> Result<(), Box<dyn std::error::Error>> {
    // Create an agent with very low confidence
    let agent = Arc::new(ConfidenceAgent::new(
        "VeryLowConfidenceAgent",
        "I really don't know about this",
        0.3, // Very low confidence
    ));

    // Wrap with human-in-loop (threshold 0.8, auto-reject)
    let hil_agent = HumanInLoopAgent::new(HumanInLoopConfig {
        agent,
        approval_threshold: 0.8,
        approval_func: simple_approval_func(false), // Auto-reject
        confidence_key: "confidence".to_string(),
    })?;

    // Wrap with AG-UI adapter
    let adapter = AGUIHumanInLoopAdapter::new(
        Arc::new(hil_agent),
        AGUIHumanInLoopConfig {
            base_config: AGUIAdapterConfig {
                agent_name: Some("RejectedDemo".to_string()),
                chunk_size: 50,
            },
            emit_interrupts: true,
        },
    );

    // Stream events
    let message = Message::with_text("user", "Should I proceed?");
    let mut event_stream = adapter.stream_events(message, None, false).await;

    println!("Streaming events...\n");

    let mut rejection_seen = false;
    while let Some(event) = event_stream.next().await {
        match event.event_type() {
            EventType::Interrupt => {
                println!("  🔔 Interrupt Event");
                let json = event.to_json();

                if let Some(context) = json.get("context") {
                    if let Some(status) = context.get("approval_status") {
                        if status.as_str() == Some("rejected") {
                            rejection_seen = true;
                            println!("    ❌ Status: REJECTED");
                        }
                    }
                    if let Some(confidence) = context.get("confidence") {
                        println!("    Confidence: {} (very low)", confidence);
                    }
                }
            }
            EventType::TextMessageChunk => {
                let json = event.to_json();
                if let Some(content) = json.get("content") {
                    println!("  ✓ Content: {}", content);
                }
            }
            EventType::TextMessageComplete => {
                println!("  ✓ Message complete");
                let json = event.to_json();
                if let Some(metadata) = json.get("response_metadata") {
                    if let Some(status) = metadata.get("approval_status") {
                        println!("    Final Status: {}", status);
                    }
                }
            }
            _ => {}
        }
    }

    if rejection_seen {
        println!("\n✓ Response was rejected as expected (confidence too low)");
    } else {
        println!("\n⚠️  Response was not rejected (check implementation)");
    }

    Ok(())
}
