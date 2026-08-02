//! AG-UI Human-in-the-Loop Integration
//!
//! Integrates the HumanInLoopAgent pattern with AG-UI protocol using Interrupt events.
//! Provides streaming approval workflow where agents can request human approval via
//! Interrupt events, and frontends can respond with InterruptResponse messages.
use crate::core::{Agent, AgentError, Message};
use crate::patterns::human_in_loop::HumanInLoopAgent;
use crate::protocols::agui::adapter::{AGUIAdapter, AGUIAdapterConfig};
use crate::protocols::agui::events::*;
use futures::stream::{Stream, StreamExt};
use std::collections::HashMap;
use std::pin::Pin;
use std::sync::Arc;
use tokio::sync::mpsc;
use uuid::Uuid;

/// Configuration for AG-UI HITL adapter.
#[derive(Debug, Clone)]
pub struct AGUIHumanInLoopConfig {
    /// Base adapter configuration
    pub base_config: AGUIAdapterConfig,
    /// Whether to emit Interrupt events for approval requests
    pub emit_interrupts: bool,
}

impl Default for AGUIHumanInLoopConfig {
    fn default() -> Self {
        Self {
            base_config: AGUIAdapterConfig::default(),
            emit_interrupts: true,
        }
    }
}

/// AG-UI adapter with human-in-the-loop support via Interrupt events.
///
/// This adapter integrates the HumanInLoopAgent pattern with AG-UI protocol.
/// When an agent requires approval (confidence < threshold), an Interrupt event
/// is emitted to request human approval. The frontend can respond via
/// InterruptResponse.
///
/// The adapter handles:
/// - Converting approval requests to Interrupt events
/// - Processing InterruptResponse from frontend
/// - Streaming approval workflow
/// - Metadata about approval decisions
///
/// # Example
/// ```no_run
/// use agenkit::core::{Agent, Message};
/// use agenkit::patterns::{HumanInLoopAgent, HumanInLoopConfig, simple_approval_func};
/// use agenkit::protocols::agui::{AGUIHumanInLoopAdapter, AGUIHumanInLoopConfig, AGUIEvent, EventType};
/// use futures::StreamExt;
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let agent: Arc<dyn Agent> = todo!();
/// let hil_agent = HumanInLoopAgent::new(HumanInLoopConfig {
///     agent,
///     approval_threshold: 0.8,
///     approval_func: simple_approval_func(true),
///     confidence_key: "confidence".to_string(),
/// })?;
///
/// let adapter = AGUIHumanInLoopAdapter::new(
///     Arc::new(hil_agent),
///     AGUIHumanInLoopConfig::default()
/// );
///
/// let message = Message::with_text("user", "Process this action");
/// let mut stream = adapter.stream_events(message, None, true).await;
///
/// while let Some(event) = stream.next().await {
///     if event.event_type() == EventType::Interrupt {
///         // Display approval request to user
///         println!("Approval needed!");
///     }
/// }
/// # Ok(())
/// # }
/// ```
pub struct AGUIHumanInLoopAdapter {
    agent: Arc<dyn Agent>,
    base_adapter: AGUIAdapter,
    config: AGUIHumanInLoopConfig,
}

impl AGUIHumanInLoopAdapter {
    /// Create a new AG-UI human-in-loop adapter.
    ///
    /// # Arguments
    /// * `agent` - Agent to wrap (HumanInLoopAgent or regular Agent)
    /// * `config` - Adapter configuration
    pub fn new(agent: Arc<dyn Agent>, config: AGUIHumanInLoopConfig) -> Self {
        let base_adapter = AGUIAdapter::new(agent.clone(), config.base_config.clone());

        Self {
            agent,
            base_adapter,
            config,
        }
    }

    /// Stream AG-UI events with interrupt support.
    ///
    /// When the agent requires approval, emits an Interrupt event to notify
    /// the frontend about the approval decision.
    ///
    /// Note: This implementation emits Interrupt events after the approval
    /// decision has been made (informational). For true bidirectional HITL,
    /// use a custom approvalFunc that integrates with your transport layer.
    ///
    /// # Arguments
    /// * `message` - Input message to process
    /// * `message_id` - Optional message ID
    /// * `emit_metadata` - Whether to emit metadata event first
    ///
    /// # Returns
    /// Stream of AG-UI events (includes Interrupt events for approval notifications)
    pub async fn stream_events(
        &self,
        message: Message,
        message_id: Option<String>,
        emit_metadata: bool,
    ) -> Pin<Box<dyn Stream<Item = Box<dyn AGUIEvent>> + Send>> {
        let msg_id = message_id.unwrap_or_else(|| format!("msg_{}", Uuid::new_v4()));
        let agent = self.agent.clone();
        let agent_name = self
            .config
            .base_config
            .agent_name
            .clone()
            .unwrap_or_else(|| agent.name().to_string());
        let chunk_size = self.config.base_config.chunk_size;
        let emit_interrupts = self.config.emit_interrupts;

        // Check if agent is a HumanInLoopAgent
        let is_hil_agent = self.is_human_in_loop_agent();

        // For regular agents or if interrupts disabled, use standard streaming
        if !is_hil_agent || !emit_interrupts {
            return self
                .base_adapter
                .stream_events(message, Some(msg_id), emit_metadata)
                .await;
        }

        let (tx, mut rx) = mpsc::channel::<Box<dyn AGUIEvent>>(100);

        tokio::spawn(async move {
            // Emit metadata about agent capabilities (including HITL)
            if emit_metadata {
                let metadata_event = create_hitl_metadata_event(&agent_name, agent.as_ref());
                let _ = tx.send(Box::new(metadata_event)).await;
            }

            // Emit text message start
            let start_event = TextMessageStart::new("assistant", Some(msg_id.clone()))
                .with_metadata("agent_name", serde_json::json!(agent_name));
            let _ = tx.send(Box::new(start_event)).await;

            // Process message with agent
            match agent.process(message).await {
                Ok(response) => {
                    // Check if approval was requested by examining metadata
                    let approval_needed = response
                        .metadata
                        .get("approval_needed")
                        .and_then(|v| v.as_bool())
                        .unwrap_or(false);

                    let confidence = response
                        .metadata
                        .get("confidence")
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0);

                    let approval_threshold = response
                        .metadata
                        .get("approval_threshold")
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.8);

                    let approval_status = response
                        .metadata
                        .get("approval_status")
                        .and_then(|v| v.as_str())
                        .unwrap_or("unknown");

                    // If approval was requested, emit Interrupt event
                    if approval_needed {
                        let interrupt_id = format!("interrupt_{}", Uuid::new_v4());
                        let interrupt = create_approval_interrupt(
                            interrupt_id,
                            confidence,
                            approval_threshold,
                            approval_status,
                            &response,
                        );
                        let _ = tx.send(Box::new(interrupt)).await;
                    }

                    // Extract content as string
                    let content = match response.content {
                        serde_json::Value::String(s) => s,
                        other => other.to_string(),
                    };

                    // Stream content in chunks
                    for (i, chunk) in content.as_bytes().chunks(chunk_size).enumerate() {
                        let chunk_str = String::from_utf8_lossy(chunk).to_string();
                        let chunk_event = TextMessageChunk::new(chunk_str, Some(msg_id.clone()))
                            .with_metadata("chunk_index", serde_json::json!(i));
                        let _ = tx.send(Box::new(chunk_event)).await;
                    }

                    // Emit complete event
                    let mut complete_event =
                        TextMessageComplete::new(content, "stop", Some(msg_id.clone()))
                            .with_metadata("agent_name", serde_json::json!(agent_name))
                            .with_metadata(
                                "approval_requested",
                                serde_json::json!(approval_needed),
                            );

                    // Add response metadata
                    if let Some(metadata) = serde_json::to_value(&response.metadata).ok() {
                        complete_event =
                            complete_event.with_metadata("response_metadata", metadata);
                    }

                    // Add approval details if present
                    if approval_needed {
                        complete_event = complete_event.with_metadata(
                            "approval_details",
                            serde_json::json!({
                                "confidence": confidence,
                                "threshold": approval_threshold,
                                "status": approval_status,
                            }),
                        );
                    }

                    let _ = tx.send(Box::new(complete_event)).await;
                }
                Err(error) => {
                    // Emit error event
                    let error_event = ErrorEvent::new(
                        "agent_error",
                        error.to_string(),
                        true,
                        Some(serde_json::json!({
                            "message_id": msg_id,
                            "error_type": format!("{:?}", error),
                        })),
                    );
                    let _ = tx.send(Box::new(error_event)).await;

                    // Emit complete with error finish reason
                    let complete_event =
                        TextMessageComplete::new("", "error", Some(msg_id.clone()))
                            .with_metadata("error", serde_json::json!(error.to_string()));
                    let _ = tx.send(Box::new(complete_event)).await;
                }
            }
        });

        Box::pin(async_stream::stream! {
            while let Some(event) = rx.recv().await {
                yield event;
            }
        })
    }

    /// Get the underlying agent.
    pub fn agent(&self) -> &Arc<dyn Agent> {
        &self.agent
    }

    /// Check if the agent is a HumanInLoopAgent by checking its capabilities.
    fn is_human_in_loop_agent(&self) -> bool {
        let caps = self.agent.capabilities();
        caps.contains(&"human-in-loop".to_string())
    }
}

/// Create metadata event with HITL capabilities.
fn create_hitl_metadata_event(agent_name: &str, agent: &dyn Agent) -> MetadataEvent {
    let mut data = HashMap::new();
    data.insert("agent_name".to_string(), serde_json::json!(agent_name));
    data.insert("protocol".to_string(), serde_json::json!("ag-ui"));
    data.insert("protocol_version".to_string(), serde_json::json!("1.0"));

    let caps = agent.capabilities();
    let is_hitl = caps.contains(&"human-in-loop".to_string());

    let mut capabilities = HashMap::new();
    capabilities.insert("streaming", serde_json::Value::Bool(true));
    capabilities.insert("tool_calls", serde_json::Value::Bool(false));
    capabilities.insert("interrupts", serde_json::Value::Bool(is_hitl));
    capabilities.insert("multimodal", serde_json::Value::Bool(false));

    data.insert(
        "capabilities".to_string(),
        serde_json::to_value(capabilities).unwrap_or(serde_json::Value::Null),
    );

    // Add HITL-specific metadata if available
    if is_hitl {
        // Note: In Rust, we can't easily extract private fields from HumanInLoopAgent
        // So we use default values or rely on the agent's introspection if available
        data.insert(
            "hitl".to_string(),
            serde_json::json!({
                "enabled": true,
                "approval_threshold": 0.8,
                "confidence_key": "confidence",
            }),
        );
    }

    // Add agent capabilities if available
    let introspection = agent.introspect();
    if !introspection.capabilities.is_empty() {
        data.insert(
            "agent_capabilities".to_string(),
            serde_json::to_value(&introspection.capabilities).unwrap_or(serde_json::Value::Null),
        );
    }

    MetadataEvent::new(data)
}

/// Create an Interrupt event for approval request.
fn create_approval_interrupt(
    interrupt_id: String,
    confidence: f64,
    threshold: f64,
    approval_status: &str,
    response: &Message,
) -> Interrupt {
    // Determine if approved based on status
    let approved = approval_status == "approved" || approval_status == "bypassed";

    // Create interrupt message
    let message = if approved {
        format!("Agent action approved (confidence: {:.2})", confidence)
    } else if approval_status == "rejected" {
        format!(
            "Agent action rejected (confidence: {:.2}, threshold: {:.2})",
            confidence, threshold
        )
    } else {
        format!(
            "Agent action requires approval (confidence: {:.2}, threshold: {:.2})",
            confidence, threshold
        )
    };

    // Extract content preview
    let content_preview = match &response.content {
        serde_json::Value::String(s) => {
            if s.len() > 100 {
                format!("{}...", &s[..100])
            } else {
                s.clone()
            }
        }
        other => {
            let s = other.to_string();
            if s.len() > 100 {
                format!("{}...", &s[..100])
            } else {
                s
            }
        }
    };

    let mut context = HashMap::new();
    context.insert(
        "approval_status".to_string(),
        serde_json::json!(approval_status),
    );
    context.insert("confidence".to_string(), serde_json::json!(confidence));
    context.insert("threshold".to_string(), serde_json::json!(threshold));
    context.insert(
        "confidence_shortfall".to_string(),
        serde_json::json!((threshold - confidence).max(0.0)),
    );
    context.insert(
        "response_preview".to_string(),
        serde_json::json!(content_preview),
    );
    context.insert(
        "timestamp".to_string(),
        serde_json::json!(response.timestamp.to_rfc3339()),
    );

    // Add any additional context from response metadata
    if let Some(agent_name) = response.metadata.get("agent") {
        context.insert("agent".to_string(), agent_name.clone());
    }

    Interrupt::new(
        InterruptReason::ApprovalRequired,
        message,
        vec![
            InterruptAction::Approve,
            InterruptAction::Reject,
            InterruptAction::Edit,
        ],
        context,
        Some(interrupt_id),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::patterns::human_in_loop::{simple_approval_func, HumanInLoopConfig};
    use async_trait::async_trait;

    struct MockAgent {
        response: String,
        confidence: f64,
    }

    #[async_trait]
    impl Agent for MockAgent {
        fn name(&self) -> &str {
            "MockAgent"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Ok(
                Message::new("assistant", serde_json::json!(self.response.clone()))
                    .with_metadata("confidence", serde_json::json!(self.confidence)),
            )
        }
    }

    #[tokio::test]
    async fn test_hitl_adapter_streams_events() {
        let agent = Arc::new(MockAgent {
            response: "Test response".to_string(),
            confidence: 0.5,
        });

        let hil_agent = HumanInLoopAgent::new(HumanInLoopConfig {
            agent,
            approval_threshold: 0.8,
            approval_func: simple_approval_func(true),
            confidence_key: "confidence".to_string(),
        })
        .unwrap();

        let adapter =
            AGUIHumanInLoopAdapter::new(Arc::new(hil_agent), AGUIHumanInLoopConfig::default());

        let message = Message::new("user", serde_json::json!("test"));
        let mut stream = adapter.stream_events(message, None, false).await;

        let mut event_types = Vec::new();
        while let Some(event) = stream.next().await {
            event_types.push(event.event_type());
        }

        assert!(event_types.contains(&EventType::TextMessageStart));
        assert!(event_types.contains(&EventType::TextMessageChunk));
        assert!(event_types.contains(&EventType::TextMessageComplete));
        assert!(event_types.contains(&EventType::Interrupt)); // Should have interrupt for low confidence
    }

    #[tokio::test]
    async fn test_hitl_adapter_emits_metadata() {
        let agent = Arc::new(MockAgent {
            response: "Test".to_string(),
            confidence: 0.5,
        });

        let hil_agent = HumanInLoopAgent::new(HumanInLoopConfig {
            agent,
            approval_threshold: 0.8,
            approval_func: simple_approval_func(true),
            confidence_key: "confidence".to_string(),
        })
        .unwrap();

        let adapter =
            AGUIHumanInLoopAdapter::new(Arc::new(hil_agent), AGUIHumanInLoopConfig::default());

        let message = Message::new("user", serde_json::json!("test"));
        let mut stream = adapter.stream_events(message, None, true).await;

        let first_event = stream.next().await.unwrap();
        assert_eq!(first_event.event_type(), EventType::Metadata);

        // Check that metadata includes HITL capabilities
        let json = first_event.to_json();
        assert_eq!(json.get("protocol"), Some(&serde_json::json!("ag-ui")));
        assert!(json.get("hitl").is_some());
    }

    #[tokio::test]
    async fn test_hitl_adapter_high_confidence_bypasses() {
        let agent = Arc::new(MockAgent {
            response: "High confidence".to_string(),
            confidence: 0.95,
        });

        let hil_agent = HumanInLoopAgent::new(HumanInLoopConfig {
            agent,
            approval_threshold: 0.8,
            approval_func: simple_approval_func(true),
            confidence_key: "confidence".to_string(),
        })
        .unwrap();

        let adapter =
            AGUIHumanInLoopAdapter::new(Arc::new(hil_agent), AGUIHumanInLoopConfig::default());

        let message = Message::new("user", serde_json::json!("test"));
        let mut stream = adapter.stream_events(message, None, false).await;

        let mut has_interrupt = false;
        while let Some(event) = stream.next().await {
            if event.event_type() == EventType::Interrupt {
                has_interrupt = true;
            }
        }

        // High confidence should not trigger interrupt
        assert!(!has_interrupt);
    }

    #[tokio::test]
    async fn test_hitl_adapter_regular_agent_no_interrupts() {
        let agent = Arc::new(MockAgent {
            response: "Regular agent".to_string(),
            confidence: 0.5,
        });

        let adapter = AGUIHumanInLoopAdapter::new(agent, AGUIHumanInLoopConfig::default());

        let message = Message::new("user", serde_json::json!("test"));
        let mut stream = adapter.stream_events(message, None, false).await;

        let mut has_interrupt = false;
        while let Some(event) = stream.next().await {
            if event.event_type() == EventType::Interrupt {
                has_interrupt = true;
            }
        }

        // Regular agent (not HumanInLoopAgent) should not emit interrupts
        assert!(!has_interrupt);
    }
}
