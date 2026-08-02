//! Anthropic Claude API adapter.
//!
//! This module provides an adapter for calling Anthropic's Claude API via HTTP.
//! Supports Claude 3 Opus, Sonnet, and Haiku models with both completion and streaming.
use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use futures::stream::Stream;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::pin::Pin;

#[cfg(feature = "native")]
use reqwest::Client;

/// Configuration for Anthropic Claude API calls.
#[derive(Debug, Clone)]
pub struct AnthropicConfig {
    /// API key (required) - get from https://console.anthropic.com/
    pub api_key: String,

    /// Model to use (default: claude-sonnet-4-6)
    pub model: String,

    /// Maximum tokens to generate (default: 4096)
    pub max_tokens: i32,

    /// Temperature 0-1 (default: 1.0)
    pub temperature: f64,

    /// Top P sampling (default: 1.0)
    pub top_p: f64,

    /// Top K sampling (default: 5)
    pub top_k: i32,

    /// API endpoint (default: Anthropic production)
    pub api_base: String,

    /// API version (default: 2023-06-01)
    pub api_version: String,

    /// Request timeout in seconds (default: 60)
    pub timeout_seconds: u64,
}

impl Default for AnthropicConfig {
    fn default() -> Self {
        Self {
            api_key: std::env::var("ANTHROPIC_API_KEY").unwrap_or_default(),
            model: "claude-sonnet-4-6".to_string(),
            max_tokens: 4096,
            temperature: 1.0,
            top_p: 1.0,
            top_k: 5,
            api_base: "https://api.anthropic.com".to_string(),
            api_version: "2023-06-01".to_string(),
            timeout_seconds: 60,
        }
    }
}

/// Anthropic message format.
#[derive(Debug, Serialize)]
struct ClaudeMessage {
    role: String,
    content: String,
}

/// Anthropic messages request.
#[derive(Debug, Serialize)]
struct MessagesRequest {
    model: String,
    max_tokens: i32,
    messages: Vec<ClaudeMessage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    system: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    temperature: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    top_p: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    top_k: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    stream: Option<bool>,
}

/// Anthropic messages response.
#[derive(Debug, Deserialize)]
struct MessagesResponse {
    id: String,
    #[serde(rename = "type")]
    response_type: String,
    role: String,
    content: Vec<ContentBlock>,
    model: String,
    stop_reason: Option<String>,
    usage: Usage,
}

#[derive(Debug, Deserialize)]
struct ContentBlock {
    #[serde(rename = "type")]
    block_type: String,
    text: String,
}

#[derive(Debug, Deserialize)]
struct Usage {
    input_tokens: i32,
    output_tokens: i32,
}

/// Streaming event from Anthropic API.
#[derive(Debug, Deserialize)]
#[serde(tag = "type")]
#[allow(dead_code)]
enum StreamEvent {
    #[serde(rename = "message_start")]
    MessageStart { message: MessageStart },
    #[serde(rename = "content_block_start")]
    ContentBlockStart {
        index: i32,
        content_block: ContentBlockStart,
    },
    #[serde(rename = "content_block_delta")]
    ContentBlockDelta { index: i32, delta: Delta },
    #[serde(rename = "content_block_stop")]
    ContentBlockStop { index: i32 },
    #[serde(rename = "message_delta")]
    MessageDelta { delta: MessageDeltaData },
    #[serde(rename = "message_stop")]
    MessageStop,
    #[serde(rename = "ping")]
    Ping,
}

#[derive(Debug, Deserialize)]
struct MessageStart {
    id: String,
    #[serde(rename = "type")]
    message_type: String,
    role: String,
    content: Vec<Value>,
    model: String,
    usage: Usage,
}

#[derive(Debug, Deserialize)]
struct ContentBlockStart {
    #[serde(rename = "type")]
    block_type: String,
    text: String,
}

#[derive(Debug, Deserialize)]
#[serde(tag = "type")]
enum Delta {
    #[serde(rename = "text_delta")]
    TextDelta { text: String },
}

#[derive(Debug, Deserialize)]
struct MessageDeltaData {
    stop_reason: Option<String>,
    usage: Option<Usage>,
}

/// Agent adapter for Anthropic Claude API.
///
/// This adapter wraps the Anthropic Messages API, converting Agent messages
/// to Claude API calls and responses back to Agent messages.
///
/// # Features
/// - Supports all Claude 3 models (Opus, Sonnet, Haiku)
/// - Async message processing
/// - Configurable temperature and tokens
/// - Error handling with typed errors
///
/// # Example
/// ```no_run
/// use agenkit::adapters::anthropic::{AnthropicAgent, AnthropicConfig};
/// use agenkit::core::{Agent, Message};
///
/// #[tokio::main]
/// async fn main() -> Result<(), Box<dyn std::error::Error>> {
///     let config = AnthropicConfig {
///         api_key: std::env::var("ANTHROPIC_API_KEY")?,
///         model: "claude-sonnet-4-6".to_string(),
///         ..Default::default()
///     };
///
///     let agent = AnthropicAgent::new(config);
///     let msg = Message::with_text("user", "What is the capital of France?");
///     let response = agent.process(msg).await?;
///
///     println!("{}", response.content_as_str().unwrap_or(""));
///     Ok(())
/// }
/// ```
pub struct AnthropicAgent {
    config: AnthropicConfig,
    #[cfg(feature = "native")]
    client: Client,
}

impl AnthropicAgent {
    /// Create a new Anthropic agent with configuration.
    ///
    /// # Arguments
    /// * `config` - Configuration including API key and model
    ///
    /// # Panics
    /// Panics if API key is empty or if parameters are out of valid range
    pub fn new(config: AnthropicConfig) -> Self {
        // Validate API key
        if config.api_key.is_empty() {
            panic!("Anthropic API key cannot be empty");
        }

        // Validate temperature (0-2, standardized across all adapters)
        if !(0.0..=2.0).contains(&config.temperature) {
            panic!(
                "temperature must be between 0 and 2, got {}",
                config.temperature
            );
        }

        // Validate max_tokens (must be positive)
        if config.max_tokens <= 0 {
            panic!("max_tokens must be positive, got {}", config.max_tokens);
        }

        // Validate top_p (0-1)
        if !(0.0..=1.0).contains(&config.top_p) {
            panic!("top_p must be between 0 and 1, got {}", config.top_p);
        }

        // Validate top_k (must be positive)
        if config.top_k <= 0 {
            panic!("top_k must be positive, got {}", config.top_k);
        }

        #[cfg(feature = "native")]
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(config.timeout_seconds))
            .build()
            .expect("Failed to create HTTP client");

        Self {
            config,
            #[cfg(feature = "native")]
            client,
        }
    }

    /// Stream completion chunks from Claude.
    ///
    /// Returns a stream of Message chunks as text arrives from the API.
    /// Note: Currently collects full response before streaming for simplicity.
    ///
    /// # Arguments
    /// * `message` - Input message to process
    ///
    /// # Returns
    /// Stream of Message chunks containing incremental text
    ///
    /// # Example
    /// ```no_run
    /// use agenkit::adapters::anthropic::{AnthropicAgent, AnthropicConfig};
    /// use agenkit::core::{Agent, Message};
    /// use futures::stream::StreamExt;
    ///
    /// #[tokio::main]
    /// async fn main() -> Result<(), Box<dyn std::error::Error>> {
    ///     let config = AnthropicConfig {
    ///         api_key: std::env::var("ANTHROPIC_API_KEY")?,
    ///         ..Default::default()
    ///     };
    ///
    ///     let agent = AnthropicAgent::new(config);
    ///     let msg = Message::with_text("user", "Count to 5");
    ///
    ///     let mut stream = agent.stream(msg).await;
    ///     while let Some(chunk) = stream.next().await {
    ///         let chunk = chunk?;
    ///         print!("{}", chunk.content_as_str().unwrap_or(""));
    ///     }
    ///     Ok(())
    /// }
    /// ```
    #[cfg(feature = "native")]
    pub async fn stream(
        &self,
        message: Message,
    ) -> Pin<Box<dyn Stream<Item = Result<Message, AgentError>> + Send>> {
        let (system, messages) = self.message_to_claude_message(&message);

        match self.stream_api_impl(messages, system).await {
            Ok(chunks) => Box::pin(futures::stream::iter(chunks.into_iter().map(Ok))),
            Err(e) => Box::pin(futures::stream::once(async move { Err(e) })),
        }
    }

    #[cfg(not(feature = "native"))]
    pub async fn stream(
        &self,
        _message: Message,
    ) -> Pin<Box<dyn Stream<Item = Result<Message, AgentError>> + Send>> {
        Box::pin(futures::stream::once(async {
            Err(AgentError::Transport(
                "Anthropic adapter requires 'native' feature for streaming".to_string(),
            ))
        }))
    }

    /// Call Anthropic API with messages.
    #[cfg(feature = "native")]
    async fn call_api(
        &self,
        messages: Vec<ClaudeMessage>,
        system: Option<String>,
    ) -> Result<MessagesResponse, AgentError> {
        let mut request = MessagesRequest {
            model: self.config.model.clone(),
            max_tokens: self.config.max_tokens,
            messages,
            system,
            temperature: None,
            top_p: None,
            top_k: None,
            stream: None,
        };

        // Only include optional parameters if not default
        if (self.config.temperature - 1.0).abs() > f64::EPSILON {
            request.temperature = Some(self.config.temperature);
        }
        if (self.config.top_p - 1.0).abs() > f64::EPSILON {
            request.top_p = Some(self.config.top_p);
        }
        if self.config.top_k != 5 {
            request.top_k = Some(self.config.top_k);
        }

        let url = format!("{}/v1/messages", self.config.api_base);

        let response = self
            .client
            .post(&url)
            .header("x-api-key", &self.config.api_key)
            .header("anthropic-version", &self.config.api_version)
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await
            .map_err(AgentError::Http)?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response
                .text()
                .await
                .unwrap_or_else(|_| "Unknown error".to_string());
            return Err(AgentError::Transport(format!(
                "Anthropic API error ({}): {}",
                status, error_text
            )));
        }

        response
            .json::<MessagesResponse>()
            .await
            .map_err(AgentError::Http)
    }

    /// Stream completion from Anthropic API.
    ///
    /// Returns a stream of Message chunks as they arrive from Claude.
    /// Note: Currently collects full response before streaming for simplicity.
    /// Future versions may implement true chunk-by-chunk streaming.
    ///
    /// # Arguments
    /// * `messages` - Claude-formatted messages
    /// * `system` - Optional system message
    ///
    /// # Returns
    /// Stream of Message chunks containing incremental text
    #[cfg(feature = "native")]
    async fn stream_api_impl(
        &self,
        messages: Vec<ClaudeMessage>,
        system: Option<String>,
    ) -> Result<Vec<Message>, AgentError> {
        let mut request = MessagesRequest {
            model: self.config.model.clone(),
            max_tokens: self.config.max_tokens,
            messages,
            system,
            temperature: None,
            top_p: None,
            top_k: None,
            stream: Some(true),
        };

        // Only include optional parameters if not default
        if (self.config.temperature - 1.0).abs() > f64::EPSILON {
            request.temperature = Some(self.config.temperature);
        }
        if (self.config.top_p - 1.0).abs() > f64::EPSILON {
            request.top_p = Some(self.config.top_p);
        }
        if self.config.top_k != 5 {
            request.top_k = Some(self.config.top_k);
        }

        let url = format!("{}/v1/messages", self.config.api_base);

        let response = self
            .client
            .post(&url)
            .header("x-api-key", &self.config.api_key)
            .header("anthropic-version", &self.config.api_version)
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await
            .map_err(AgentError::Http)?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response
                .text()
                .await
                .unwrap_or_else(|_| "Unknown error".to_string());
            return Err(AgentError::Transport(format!(
                "Anthropic API error ({}): {}",
                status, error_text
            )));
        }

        // Parse Server-Sent Events (SSE)
        let bytes = response.bytes().await.map_err(AgentError::Http)?;
        let text = String::from_utf8_lossy(&bytes);

        let mut chunks = Vec::new();

        // Parse SSE format
        for line in text.lines() {
            if let Some(data) = line.strip_prefix("data: ") {
                // Skip [DONE] marker
                if data == "[DONE]" {
                    continue;
                }

                // Parse JSON event
                if let Ok(StreamEvent::ContentBlockDelta { delta, .. }) =
                    serde_json::from_str::<StreamEvent>(data)
                {
                    if let Delta::TextDelta { text } = delta {
                        let mut msg = Message::with_text("agent", &text);
                        msg.metadata.insert("streaming".to_string(), json!(true));
                        msg.metadata
                            .insert("model".to_string(), json!(self.config.model));
                        chunks.push(msg);
                    }
                }
            }
        }

        Ok(chunks)
    }

    /// Convert Agent message to Claude format, extracting system prompt if present.
    fn message_to_claude_message(&self, message: &Message) -> (Option<String>, Vec<ClaudeMessage>) {
        let mut system = None;
        let mut messages = Vec::new();

        if message.role == "system" {
            system = message.content_as_str().map(|s| s.to_string());
        } else {
            messages.push(ClaudeMessage {
                role: message.role.clone(),
                content: message.content_as_str().unwrap_or("").to_string(),
            });
        }

        (system, messages)
    }

    /// Convert Claude response to Agent message.
    fn response_to_message(&self, response: MessagesResponse) -> Message {
        let content = if !response.content.is_empty() {
            response.content[0].text.clone()
        } else {
            String::new()
        };

        let mut msg = Message::with_text(&response.role, &content);

        // Add metadata
        msg.metadata
            .insert("claude_message_id".to_string(), json!(response.id));
        msg.metadata
            .insert("model".to_string(), json!(response.model));
        msg.metadata.insert(
            "usage".to_string(),
            json!({
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }),
        );

        if let Some(stop_reason) = response.stop_reason {
            msg.metadata
                .insert("stop_reason".to_string(), json!(stop_reason));
        }

        msg
    }
}

#[async_trait]
impl Agent for AnthropicAgent {
    fn name(&self) -> &str {
        "anthropic"
    }

    #[cfg(feature = "native")]
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let (system, messages) = self.message_to_claude_message(&message);
        let response = self.call_api(messages, system).await?;
        Ok(self.response_to_message(response))
    }

    #[cfg(not(feature = "native"))]
    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        Err(AgentError::Transport(
            "Anthropic adapter requires 'native' feature".to_string(),
        ))
    }

    fn capabilities(&self) -> Vec<String> {
        vec![
            "llm".to_string(),
            "text-generation".to_string(),
            "anthropic".to_string(),
            "claude".to_string(),
        ]
    }
}

/// Available Claude models (November 2025).
pub mod models {
    /// Claude Sonnet 4 - Latest and most capable (November 2025)
    pub const SONNET_4: &str = "claude-sonnet-4-20250514";

    /// Claude 3.5 Sonnet v2 - Previous generation
    pub const SONNET_3_5_V2: &str = "claude-3-5-sonnet-20241022";

    /// Claude 3.5 Sonnet - Original 3.5
    pub const SONNET_3_5: &str = "claude-3-5-sonnet-20240620";

    /// Claude 3.5 Haiku - Fast and cost-effective
    pub const HAIKU_3_5: &str = "claude-3-5-haiku-20241022";

    /// Claude 3 Opus - Highest capability
    pub const OPUS_3: &str = "claude-3-opus-20240229";
}

#[cfg(all(test, feature = "native"))]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_anthropic_agent_creation() {
        let config = AnthropicConfig {
            api_key: "test-key".to_string(),
            ..Default::default()
        };

        let agent = AnthropicAgent::new(config);
        assert_eq!(agent.name(), "anthropic");
    }

    #[tokio::test]
    async fn test_anthropic_agent_capabilities() {
        let config = AnthropicConfig {
            api_key: "test-key".to_string(),
            ..Default::default()
        };

        let agent = AnthropicAgent::new(config);
        let caps = agent.capabilities();
        assert!(caps.contains(&"llm".to_string()));
        assert!(caps.contains(&"claude".to_string()));
    }

    #[test]
    fn test_default_config_values() {
        let config = AnthropicConfig::default();
        assert_eq!(config.model, "claude-sonnet-4-6");
        assert_eq!(config.max_tokens, 4096);
        assert!((config.temperature - 1.0).abs() < f64::EPSILON);
        assert_eq!(config.api_version, "2023-06-01");
    }

    #[tokio::test]
    async fn test_successful_completion() {
        let mut server = mockito::Server::new_async().await;

        let mock = server
            .mock("POST", "/v1/messages")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(
                r#"{
                "id": "msg_test123",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "Paris is the capital of France."}],
                "model": "claude-sonnet-4-6",
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 15, "output_tokens": 10}
            }"#,
            )
            .create_async()
            .await;

        let config = AnthropicConfig {
            api_key: "test-key".to_string(),
            api_base: server.url(),
            ..Default::default()
        };
        let agent = AnthropicAgent::new(config);
        let msg = Message::with_text("user", "What is the capital of France?");
        let response = agent.process(msg).await.unwrap();

        assert!(response.content_as_str().unwrap_or("").contains("Paris"));
        assert_eq!(response.metadata["model"], "claude-sonnet-4-6");
        assert!(response.metadata.contains_key("stop_reason"));
        assert!(response.metadata.contains_key("usage"));
        mock.assert_async().await;
    }

    #[tokio::test]
    async fn test_auth_error_handling() {
        let mut server = mockito::Server::new_async().await;

        let mock = server
            .mock("POST", "/v1/messages")
            .with_status(401)
            .with_body(
                r#"{"error": {"type": "authentication_error", "message": "Invalid API key"}}"#,
            )
            .create_async()
            .await;

        let config = AnthropicConfig {
            api_key: "invalid-key".to_string(),
            api_base: server.url(),
            ..Default::default()
        };
        let agent = AnthropicAgent::new(config);
        let msg = Message::with_text("user", "hello");
        assert!(agent.process(msg).await.is_err());
        mock.assert_async().await;
    }

    #[tokio::test]
    async fn test_rate_limit_error_handling() {
        let mut server = mockito::Server::new_async().await;

        let mock = server
            .mock("POST", "/v1/messages")
            .with_status(429)
            .with_body(
                r#"{"error": {"type": "rate_limit_error", "message": "Rate limit exceeded"}}"#,
            )
            .create_async()
            .await;

        let config = AnthropicConfig {
            api_key: "test-key".to_string(),
            api_base: server.url(),
            ..Default::default()
        };
        let agent = AnthropicAgent::new(config);
        let msg = Message::with_text("user", "hello");
        assert!(agent.process(msg).await.is_err());
        mock.assert_async().await;
    }

    #[tokio::test]
    async fn test_response_metadata_fields() {
        let mut server = mockito::Server::new_async().await;

        server
            .mock("POST", "/v1/messages")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(
                r#"{
                "id": "msg_abc",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "42"}],
                "model": "claude-sonnet-4-6",
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 5, "output_tokens": 2}
            }"#,
            )
            .create_async()
            .await;

        let config = AnthropicConfig {
            api_key: "test-key".to_string(),
            api_base: server.url(),
            ..Default::default()
        };
        let agent = AnthropicAgent::new(config);
        let response = agent
            .process(Message::with_text("user", "What is 6*7?"))
            .await
            .unwrap();

        assert!(response.metadata.contains_key("claude_message_id"));
        assert!(response.metadata.contains_key("model"));
        assert!(response.metadata.contains_key("usage"));
        assert!(response.metadata.contains_key("stop_reason"));

        // Verify usage fields
        let usage = &response.metadata["usage"];
        assert!(usage.get("input_tokens").is_some());
        assert!(usage.get("output_tokens").is_some());
    }

    #[tokio::test]
    async fn test_system_message_handling() {
        let mut server = mockito::Server::new_async().await;

        server
            .mock("POST", "/v1/messages")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(
                r#"{
                "id": "msg_sys",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "I am a helpful assistant."}],
                "model": "claude-sonnet-4-6",
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 20, "output_tokens": 8}
            }"#,
            )
            .create_async()
            .await;

        let config = AnthropicConfig {
            api_key: "test-key".to_string(),
            api_base: server.url(),
            ..Default::default()
        };
        let agent = AnthropicAgent::new(config);
        // System messages are handled by mapping role
        let msg = Message::with_text("system", "You are a helpful assistant.");
        // System messages are extracted separately, not passed as user messages
        let response = agent.process(msg).await.unwrap();
        assert!(!response.content_as_str().unwrap_or("").is_empty());
    }
}
