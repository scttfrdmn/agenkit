//! AG-UI Adapter - Wraps agents for AG-UI event streaming
//!
//! Converts agent responses into AG-UI event streams for frontend consumption.
use crate::core::{Agent, Message};
use crate::protocols::agui::events::*;
use futures::stream::Stream;
use std::collections::HashMap;
use std::pin::Pin;
use std::sync::Arc;
use tokio::sync::mpsc;
use uuid::Uuid;

/// Configuration for AG-UI adapter.
#[derive(Debug, Clone)]
pub struct AGUIAdapterConfig {
    /// Optional agent name override
    pub agent_name: Option<String>,
    /// Size of chunks for streaming content (default: 100 bytes)
    pub chunk_size: usize,
}

impl Default for AGUIAdapterConfig {
    fn default() -> Self {
        Self {
            agent_name: None,
            chunk_size: 100,
        }
    }
}

/// AG-UI adapter that wraps an agent and streams events.
///
/// Converts agent responses into AG-UI event streams suitable for
/// frontend consumption over HTTP/SSE or WebSocket.
///
/// # Example
/// ```no_run
/// use agenkit::core::{Agent, Message};
/// use agenkit::protocols::agui::{AGUIAdapter, AGUIAdapterConfig};
/// use futures::StreamExt;
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let agent: Arc<dyn Agent> = todo!();
/// let adapter = AGUIAdapter::new(agent, AGUIAdapterConfig::default());
///
/// let message = Message::with_text("user", "Hello!");
/// let mut stream = adapter.stream_events(message, None, true).await;
///
/// while let Some(event) = stream.next().await {
///     println!("Event: {:?}", event.event_type());
/// }
/// # Ok(())
/// # }
/// ```
pub struct AGUIAdapter {
    agent: Arc<dyn Agent>,
    config: AGUIAdapterConfig,
}

impl AGUIAdapter {
    /// Create a new AG-UI adapter.
    ///
    /// # Arguments
    /// * `agent` - Agent to wrap
    /// * `config` - Adapter configuration
    pub fn new(agent: Arc<dyn Agent>, config: AGUIAdapterConfig) -> Self {
        Self { agent, config }
    }

    /// Stream AG-UI events for a message.
    ///
    /// # Arguments
    /// * `message` - Input message to process
    /// * `message_id` - Optional message ID (generated if not provided)
    /// * `emit_metadata` - Whether to emit metadata event first
    ///
    /// # Returns
    /// Stream of AG-UI events
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
            .agent_name
            .clone()
            .unwrap_or_else(|| agent.name().to_string());
        let chunk_size = self.config.chunk_size;

        let (tx, mut rx) = mpsc::channel::<Box<dyn AGUIEvent>>(100);

        tokio::spawn(async move {
            // Emit metadata if requested
            if emit_metadata {
                let metadata_event = create_metadata_event(&agent_name, agent.as_ref());
                let _ = tx.send(Box::new(metadata_event)).await;
            }

            // Emit text message start
            let start_event = TextMessageStart::new("assistant", Some(msg_id.clone()))
                .with_metadata("agent_name", serde_json::json!(agent_name));
            let _ = tx.send(Box::new(start_event)).await;

            // Process message with agent
            match agent.process(message).await {
                Ok(response) => {
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
                            .with_metadata("agent_name", serde_json::json!(agent_name));

                    // Add response metadata
                    if let Ok(metadata) = serde_json::to_value(&response.metadata) {
                        complete_event =
                            complete_event.with_metadata("response_metadata", metadata);
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
}

/// Create metadata event with agent capabilities.
fn create_metadata_event(agent_name: &str, agent: &dyn Agent) -> MetadataEvent {
    let mut data = HashMap::new();
    data.insert("agent_name".to_string(), serde_json::json!(agent_name));
    data.insert("protocol".to_string(), serde_json::json!("ag-ui"));
    data.insert("protocol_version".to_string(), serde_json::json!("1.0"));

    let mut capabilities = HashMap::new();
    capabilities.insert("streaming", serde_json::Value::Bool(true));
    capabilities.insert("tool_calls", serde_json::Value::Bool(false));
    capabilities.insert("interrupts", serde_json::Value::Bool(false));
    capabilities.insert("multimodal", serde_json::Value::Bool(false));

    data.insert(
        "capabilities".to_string(),
        serde_json::to_value(capabilities).unwrap_or(serde_json::Value::Null),
    );

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

#[cfg(test)]
mod tests {
    use super::*;
    // AgentError is used only by the mock below, and StreamExt only by the `.next()`
    // calls in the assertions, so both belong here rather than at file scope where
    // they are genuinely unused (#778).
    use crate::core::{AgentError, Message};
    use async_trait::async_trait;
    use futures::stream::StreamExt;

    struct MockAgent {
        response: String,
    }

    #[async_trait]
    impl Agent for MockAgent {
        fn name(&self) -> &str {
            "MockAgent"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Ok(Message::new(
                "assistant",
                serde_json::json!(self.response.clone()),
            ))
        }
    }

    #[tokio::test]
    async fn test_adapter_streams_events() {
        let agent = Arc::new(MockAgent {
            response: "Hello".to_string(),
        });
        let adapter = AGUIAdapter::new(agent, AGUIAdapterConfig::default());

        let message = Message::new("user", serde_json::json!("test"));
        let mut stream = adapter.stream_events(message, None, false).await;

        let mut event_types = Vec::new();
        while let Some(event) = stream.next().await {
            event_types.push(event.event_type());
        }

        assert!(event_types.contains(&EventType::TextMessageStart));
        assert!(event_types.contains(&EventType::TextMessageChunk));
        assert!(event_types.contains(&EventType::TextMessageComplete));
    }

    #[tokio::test]
    async fn test_adapter_emits_metadata() {
        let agent = Arc::new(MockAgent {
            response: "Hello".to_string(),
        });
        let adapter = AGUIAdapter::new(agent, AGUIAdapterConfig::default());

        let message = Message::new("user", serde_json::json!("test"));
        let mut stream = adapter.stream_events(message, None, true).await;

        let first_event = stream.next().await.unwrap();
        assert_eq!(first_event.event_type(), EventType::Metadata);
    }
}
