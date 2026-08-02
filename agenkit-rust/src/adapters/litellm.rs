//! LiteLLM proxy adapter for universal LLM access.
//!
//! Provides integration with LiteLLM, a universal LLM gateway that offers
//! an OpenAI-compatible API for 100+ LLM providers. Supports both completion
//! and streaming modes.
use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use futures::Stream;
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::pin::Pin;

#[cfg(feature = "native")]
use reqwest::Client;

/// Configuration for LiteLLM adapter.
#[derive(Debug, Clone)]
pub struct LiteLLMConfig {
    /// LiteLLM proxy base URL (default: http://localhost:4000)
    pub base_url: String,

    /// Model identifier in LiteLLM format
    /// Examples: "gpt-4", "claude-3-5-sonnet-20241022", "bedrock/anthropic.claude-v2"
    pub model: String,

    /// API key for LiteLLM proxy authentication (optional)
    pub api_key: Option<String>,

    /// Temperature for sampling (0.0 - 2.0)
    pub temperature: Option<f32>,

    /// Maximum tokens to generate
    pub max_tokens: Option<u32>,

    /// Top-p sampling parameter
    pub top_p: Option<f32>,

    /// Request timeout in seconds (default: 60)
    pub timeout_seconds: u64,
}

impl Default for LiteLLMConfig {
    fn default() -> Self {
        Self {
            base_url: "http://localhost:4000".to_string(),
            model: "gpt-3.5-turbo".to_string(),
            api_key: None,
            temperature: Some(0.7),
            max_tokens: Some(1024),
            top_p: Some(1.0),
            timeout_seconds: 60,
        }
    }
}

/// LiteLLM chat message format (OpenAI-compatible).
#[derive(Debug, Serialize, Deserialize)]
struct LiteLLMMessage {
    role: String,
    content: String,
}

/// LiteLLM chat completion request.
#[derive(Debug, Serialize)]
struct LiteLLMRequest {
    model: String,
    messages: Vec<LiteLLMMessage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    temperature: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    max_tokens: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    top_p: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    stream: Option<bool>,
}

/// LiteLLM chat completion response.
#[derive(Debug, Deserialize)]
struct LiteLLMResponse {
    id: String,
    model: String,
    choices: Vec<LiteLLMChoice>,
    usage: LiteLLMUsage,
}

#[derive(Debug, Deserialize)]
struct LiteLLMChoice {
    message: LiteLLMMessage,
    finish_reason: String,
}

#[derive(Debug, Deserialize)]
struct LiteLLMUsage {
    prompt_tokens: i32,
    completion_tokens: i32,
    total_tokens: i32,
}

/// Agent adapter for LiteLLM proxy.
///
/// This adapter wraps the LiteLLM proxy API, providing access to 100+ LLM providers
/// through an OpenAI-compatible interface.
///
/// # Features
/// - Support for 100+ LLM providers through LiteLLM proxy
/// - OpenAI-compatible API
/// - Configurable temperature, top_p, and max_tokens
/// - Error handling with typed errors
/// - Optional API key authentication
///
/// # Example
/// ```no_run
/// use agenkit::adapters::litellm::{LiteLLMAdapter, LiteLLMConfig};
/// use agenkit::core::{Agent, Message};
///
/// #[tokio::main]
/// async fn main() -> Result<(), Box<dyn std::error::Error>> {
///     let config = LiteLLMConfig {
///         base_url: "http://localhost:4000".to_string(),
///         model: "gpt-4".to_string(),
///         ..Default::default()
///     };
///
///     let adapter = LiteLLMAdapter::new(config);
///     let msg = Message::with_text("user", "What is the capital of France?");
///     let response = adapter.process(msg).await?;
///
///     println!("{}", response.content_as_str().unwrap_or(""));
///     Ok(())
/// }
/// ```
pub struct LiteLLMAdapter {
    config: LiteLLMConfig,
    #[cfg(feature = "native")]
    client: Client,
}

impl LiteLLMAdapter {
    /// Create a new LiteLLM adapter with configuration.
    ///
    /// # Arguments
    /// * `config` - Configuration including base URL and model
    pub fn new(config: LiteLLMConfig) -> Self {
        #[cfg(feature = "native")]
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(config.timeout_seconds))
            .build()
            .expect("failed to create HTTP client");

        Self {
            config,
            #[cfg(feature = "native")]
            client,
        }
    }

    /// Call LiteLLM API with messages.
    #[cfg(feature = "native")]
    async fn call_api(&self, messages: Vec<LiteLLMMessage>) -> Result<LiteLLMResponse, AgentError> {
        let request = LiteLLMRequest {
            model: self.config.model.clone(),
            messages,
            temperature: self.config.temperature,
            max_tokens: self.config.max_tokens,
            top_p: self.config.top_p,
            stream: None,
        };

        let url = format!("{}/chat/completions", self.config.base_url);

        let mut req = self
            .client
            .post(&url)
            .header("Content-Type", "application/json")
            .json(&request);

        if let Some(api_key) = &self.config.api_key {
            req = req.header("Authorization", format!("Bearer {}", api_key));
        }

        let response = req.send().await.map_err(AgentError::Http)?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response
                .text()
                .await
                .unwrap_or_else(|_| "unknown error".to_string());
            return Err(AgentError::Transport(format!(
                "LiteLLM API error ({}): {}",
                status, error_text
            )));
        }

        response
            .json::<LiteLLMResponse>()
            .await
            .map_err(AgentError::Http)
    }

    /// Convert Agent message to LiteLLM format.
    fn message_to_litellm_message(&self, message: &Message) -> LiteLLMMessage {
        let role = match message.role.as_str() {
            "system" | "user" => message.role.clone(),
            "assistant" | "agent" | _ => "assistant".to_string(),
        };

        LiteLLMMessage {
            role,
            content: message.content_as_str().unwrap_or("").to_string(),
        }
    }

    /// Convert LiteLLM response to Agent message.
    fn response_to_message(&self, response: LiteLLMResponse) -> Message {
        let content = if !response.choices.is_empty() {
            response.choices[0].message.content.clone()
        } else {
            String::new()
        };

        let mut msg = Message::with_text("assistant", &content);

        // Add metadata
        msg.metadata
            .insert("litellm_message_id".to_string(), json!(response.id));
        msg.metadata
            .insert("model".to_string(), json!(response.model));
        msg.metadata.insert(
            "usage".to_string(),
            json!({
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }),
        );

        if !response.choices.is_empty() {
            msg.metadata.insert(
                "finish_reason".to_string(),
                json!(response.choices[0].finish_reason),
            );
        }

        msg
    }

    /// Stream completion from LiteLLM proxy.
    ///
    /// Returns a stream of Message chunks as they arrive from the API.
    #[cfg(feature = "native")]
    pub async fn stream(
        &self,
        message: Message,
    ) -> Pin<Box<dyn Stream<Item = Result<Message, AgentError>> + Send>> {
        let litellm_message = self.message_to_litellm_message(&message);

        match self.stream_api_impl(vec![litellm_message]).await {
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
                "LiteLLM adapter requires 'native' feature for streaming".to_string(),
            ))
        }))
    }

    /// Internal streaming implementation.
    #[cfg(feature = "native")]
    async fn stream_api_impl(
        &self,
        messages: Vec<LiteLLMMessage>,
    ) -> Result<Vec<Message>, AgentError> {
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(self.config.timeout_seconds))
            .build()
            .map_err(|e| AgentError::Transport(e.to_string()))?;

        let mut request_body = json!({
            "model": self.config.model,
            "messages": messages,
            "stream": true,
        });

        if let Some(temperature) = self.config.temperature {
            request_body["temperature"] = json!(temperature);
        }
        if let Some(max_tokens) = self.config.max_tokens {
            request_body["max_tokens"] = json!(max_tokens);
        }
        if let Some(top_p) = self.config.top_p {
            request_body["top_p"] = json!(top_p);
        }

        let mut request = client
            .post(format!("{}/chat/completions", self.config.base_url))
            .header("Content-Type", "application/json")
            .json(&request_body);

        // Add API key if provided
        if let Some(api_key) = &self.config.api_key {
            request = request.header("Authorization", format!("Bearer {}", api_key));
        }

        let response = request
            .send()
            .await
            .map_err(|e| AgentError::Transport(e.to_string()))?;

        if !response.status().is_success() {
            let status = response.status();
            let body = response.text().await.unwrap_or_default();
            return Err(AgentError::Transport(format!(
                "LiteLLM API error ({}): {}",
                status, body
            )));
        }

        // Collect full response body (pseudo-streaming)
        let body = response
            .text()
            .await
            .map_err(|e| AgentError::Transport(e.to_string()))?;

        // Parse SSE stream (OpenAI-compatible format)
        let mut chunks = Vec::new();
        for line in body.lines() {
            if line.is_empty() || !line.starts_with("data: ") {
                continue;
            }

            let json_str = &line[6..]; // Skip "data: "

            if json_str == "[DONE]" {
                break;
            }

            let chunk_json: serde_json::Value = serde_json::from_str(json_str)?;

            // Extract text from choices[0].delta.content
            if let Some(choices) = chunk_json["choices"].as_array() {
                if let Some(choice) = choices.first() {
                    if let Some(delta) = choice["delta"].as_object() {
                        if let Some(content) = delta.get("content") {
                            if let Some(text) = content.as_str() {
                                let mut msg = Message::with_text("assistant", text);
                                msg.metadata.insert("streaming".to_string(), json!(true));
                                chunks.push(msg);
                            }
                        }
                    }
                }
            }
        }

        Ok(chunks)
    }
}

#[async_trait]
impl Agent for LiteLLMAdapter {
    fn name(&self) -> &str {
        "litellm"
    }

    #[cfg(feature = "native")]
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let litellm_message = self.message_to_litellm_message(&message);
        let response = self.call_api(vec![litellm_message]).await?;
        Ok(self.response_to_message(response))
    }

    #[cfg(not(feature = "native"))]
    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        Err(AgentError::Transport(
            "LiteLLM adapter requires 'native' feature".to_string(),
        ))
    }

    fn capabilities(&self) -> Vec<String> {
        vec![
            "llm".to_string(),
            "text-generation".to_string(),
            "litellm".to_string(),
            "universal-gateway".to_string(),
        ]
    }
}

/// Common LiteLLM model identifiers.
pub mod models {
    // OpenAI models
    pub const GPT_4: &str = "gpt-4";
    pub const GPT_4_TURBO: &str = "gpt-4-turbo";
    pub const GPT_4O: &str = "gpt-4o";
    pub const GPT_4O_MINI: &str = "gpt-4o-mini";
    pub const GPT_3_5_TURBO: &str = "gpt-3.5-turbo";

    // Anthropic models
    pub const CLAUDE_3_5_SONNET: &str = "claude-3-5-sonnet-20241022";
    pub const CLAUDE_3_OPUS: &str = "claude-3-opus-20240229";
    pub const CLAUDE_3_HAIKU: &str = "claude-3-haiku-20240307";

    // Bedrock models (prefix with bedrock/)
    pub const BEDROCK_CLAUDE_3_5_SONNET: &str = "bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0";
    pub const BEDROCK_CLAUDE_3_HAIKU: &str = "bedrock/anthropic.claude-3-haiku-20240307-v1:0";

    // Gemini models (prefix with gemini/)
    pub const GEMINI_PRO: &str = "gemini/gemini-pro";
    pub const GEMINI_2_FLASH: &str = "gemini/gemini-2.0-flash-exp";

    // Ollama models (prefix with ollama/)
    pub const OLLAMA_LLAMA2: &str = "ollama/llama2";
    pub const OLLAMA_MISTRAL: &str = "ollama/mistral";
}

#[cfg(all(test, feature = "native"))]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_litellm_adapter_creation() {
        let config = LiteLLMConfig::default();
        let adapter = LiteLLMAdapter::new(config);
        assert_eq!(adapter.name(), "litellm");
    }

    #[tokio::test]
    async fn test_litellm_adapter_capabilities() {
        let config = LiteLLMConfig::default();
        let adapter = LiteLLMAdapter::new(config);
        let caps = adapter.capabilities();
        assert!(caps.contains(&"llm".to_string()));
        assert!(caps.contains(&"litellm".to_string()));
        assert!(caps.contains(&"universal-gateway".to_string()));
    }

    #[test]
    fn test_litellm_config_default() {
        let config = LiteLLMConfig::default();
        assert_eq!(config.base_url, "http://localhost:4000");
        assert_eq!(config.model, "gpt-3.5-turbo");
        assert_eq!(config.timeout_seconds, 60);
        assert_eq!(config.temperature, Some(0.7));
        assert_eq!(config.max_tokens, Some(1024));
        assert_eq!(config.top_p, Some(1.0));
    }

    #[test]
    fn test_litellm_config_custom() {
        let config = LiteLLMConfig {
            base_url: "http://custom:8000".to_string(),
            model: "gpt-4".to_string(),
            api_key: Some("test-key".to_string()),
            temperature: Some(0.9),
            max_tokens: Some(2048),
            top_p: Some(0.95),
            timeout_seconds: 120,
        };
        assert_eq!(config.base_url, "http://custom:8000");
        assert_eq!(config.model, "gpt-4");
        assert_eq!(config.api_key, Some("test-key".to_string()));
        assert_eq!(config.temperature, Some(0.9));
    }

    #[test]
    fn test_message_to_litellm_message() {
        let config = LiteLLMConfig::default();
        let adapter = LiteLLMAdapter::new(config);

        let msg = Message::with_text("user", "Hello");
        let litellm_msg = adapter.message_to_litellm_message(&msg);
        assert_eq!(litellm_msg.role, "user");
        assert_eq!(litellm_msg.content, "Hello");
    }

    #[test]
    fn test_message_role_conversion() {
        let config = LiteLLMConfig::default();
        let adapter = LiteLLMAdapter::new(config);

        // Test system role
        let system_msg = Message::with_text("system", "You are helpful");
        let litellm_msg = adapter.message_to_litellm_message(&system_msg);
        assert_eq!(litellm_msg.role, "system");

        // Test user role
        let user_msg = Message::with_text("user", "Hello");
        let litellm_msg = adapter.message_to_litellm_message(&user_msg);
        assert_eq!(litellm_msg.role, "user");

        // Test assistant role
        let assistant_msg = Message::with_text("assistant", "Hi");
        let litellm_msg = adapter.message_to_litellm_message(&assistant_msg);
        assert_eq!(litellm_msg.role, "assistant");

        // Test agent role (maps to assistant)
        let agent_msg = Message::with_text("agent", "Response");
        let litellm_msg = adapter.message_to_litellm_message(&agent_msg);
        assert_eq!(litellm_msg.role, "assistant");
    }

    #[test]
    fn test_response_to_message() {
        let config = LiteLLMConfig::default();
        let adapter = LiteLLMAdapter::new(config);

        let response = LiteLLMResponse {
            id: "chatcmpl-123".to_string(),
            model: "gpt-3.5-turbo".to_string(),
            choices: vec![LiteLLMChoice {
                message: LiteLLMMessage {
                    role: "assistant".to_string(),
                    content: "Hello!".to_string(),
                },
                finish_reason: "stop".to_string(),
            }],
            usage: LiteLLMUsage {
                prompt_tokens: 10,
                completion_tokens: 5,
                total_tokens: 15,
            },
        };

        let msg = adapter.response_to_message(response);
        assert_eq!(msg.role, "assistant");
        assert_eq!(msg.content_as_str(), Some("Hello!"));
        assert_eq!(msg.metadata.get("model").unwrap(), &json!("gpt-3.5-turbo"));
        assert_eq!(msg.metadata.get("finish_reason").unwrap(), &json!("stop"));
    }

    #[test]
    fn test_model_constants() {
        assert_eq!(models::GPT_4, "gpt-4");
        assert_eq!(models::GPT_4_TURBO, "gpt-4-turbo");
        assert_eq!(models::CLAUDE_3_5_SONNET, "claude-3-5-sonnet-20241022");
        assert_eq!(
            models::BEDROCK_CLAUDE_3_5_SONNET,
            "bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0"
        );
        assert_eq!(models::GEMINI_PRO, "gemini/gemini-pro");
        assert_eq!(models::OLLAMA_LLAMA2, "ollama/llama2");
    }
}
