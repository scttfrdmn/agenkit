//! OpenAI-Compatible API adapter.
//!
//! This module provides a generic adapter for OpenAI-compatible inference services
//! like vLLM, llama.cpp, SGLang, TensorRT-LLM, and others.
//!
//! This adapter enables Agenkit to work with any service implementing the
//! OpenAI Chat Completions API by configuring the HTTP client with a custom
//! base URL. This provides a consistent interface across different local and
//! self-hosted inference engines.
//!
//! # Supported Services
//! - vLLM: High-throughput batch inference
//! - llama.cpp: Lightweight C++ implementation (CPU-friendly)
//! - SGLang: Optimized for complex prompts
//! - TensorRT-LLM: NVIDIA GPU optimized
//! - OpenLLM: Multi-model serving platform
//! - MLC LLM: Mobile and edge deployment
//! - Text Generation Inference (TGI): HuggingFace inference server
//! - Inferflow: High-performance inference
//!
//! # Example - vLLM
//! ```no_run
//! use agenkit::adapters::openai_compatible::{OpenAICompatibleAgent, OpenAICompatibleConfig};
//! use agenkit::core::{Agent, Message};
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let config = OpenAICompatibleConfig {
//!         base_url: "http://localhost:8000/v1".to_string(),
//!         model: "meta-llama/Llama-2-7b-chat-hf".to_string(),
//!         provider: Some("vllm".to_string()),
//!         ..Default::default()
//!     };
//!
//!     let agent = OpenAICompatibleAgent::new(config);
//!     let msg = Message::with_text("user", "What is machine learning?");
//!     let response = agent.process(msg).await?;
//!
//!     println!("{}", response.content_as_str().unwrap_or(""));
//!     Ok(())
//! }
//! ```
//!
//! # Example - llama.cpp
//! ```no_run
//! use agenkit::adapters::openai_compatible::{OpenAICompatibleAgent, OpenAICompatibleConfig};
//!
//! let config = OpenAICompatibleConfig {
//!     base_url: "http://localhost:8080/v1".to_string(),
//!     model: "llama-2-7b-chat".to_string(),
//!     provider: Some("llamacpp".to_string()),
//!     ..Default::default()
//! };
//!
//! let agent = OpenAICompatibleAgent::new(config);
//! ```
use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use serde_json::json;

#[cfg(feature = "native")]
use reqwest::Client;

/// Configuration for OpenAI-Compatible API calls.
///
/// This configuration works with any service implementing the OpenAI
/// Chat Completions API.
#[derive(Debug, Clone)]
pub struct OpenAICompatibleConfig {
    /// Base URL of the inference service (e.g., "http://localhost:8000/v1").
    /// Must include the /v1 suffix for most services.
    pub base_url: String,

    /// Model name/identifier used by the inference service.
    /// Format varies by service:
    /// - vLLM: "meta-llama/Llama-2-7b-chat-hf"
    /// - llama.cpp: "llama-2-7b-chat"
    /// - SGLang: "meta-llama/Llama-2-13b-chat-hf"
    pub model: String,

    /// Optional provider name for metadata and debugging.
    /// Examples: "vllm", "llamacpp", "sglang", "tensorrt"
    pub provider: Option<String>,

    /// Optional API key. Most local services don't require authentication.
    /// Defaults to "not-needed".
    pub api_key: Option<String>,

    /// Maximum tokens to generate (default: 1024)
    pub max_tokens: i32,

    /// Temperature 0-2 (default: 0.7)
    pub temperature: f64,

    /// Top P sampling (default: 1.0)
    pub top_p: f64,

    /// Request timeout in seconds (default: 60)
    pub timeout_seconds: u64,
}

impl Default for OpenAICompatibleConfig {
    fn default() -> Self {
        Self {
            base_url: "http://localhost:8000/v1".to_string(),
            model: "llama-2-7b".to_string(),
            provider: None,
            api_key: None,
            max_tokens: 1024,
            temperature: 0.7,
            top_p: 1.0,
            timeout_seconds: 60,
        }
    }
}

/// OpenAI chat completion request message.
#[derive(Debug, Serialize)]
struct ChatMessage {
    role: String,
    content: String,
}

/// OpenAI chat completion request.
#[derive(Debug, Serialize)]
struct ChatCompletionRequest {
    model: String,
    messages: Vec<ChatMessage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    max_tokens: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    temperature: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    top_p: Option<f64>,
}

/// OpenAI chat completion response.
#[derive(Debug, Deserialize)]
struct ChatCompletionResponse {
    id: String,
    model: String,
    choices: Vec<Choice>,
    #[serde(default)]
    usage: Option<Usage>,
}

#[derive(Debug, Deserialize)]
struct Choice {
    message: ResponseMessage,
    finish_reason: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ResponseMessage {
    role: String,
    content: String,
}

#[derive(Debug, Deserialize)]
struct Usage {
    prompt_tokens: i32,
    completion_tokens: i32,
    total_tokens: i32,
}

/// Agent adapter for OpenAI-compatible services.
///
/// This adapter wraps OpenAI-compatible Chat Completions APIs, converting Agent
/// messages to API calls and responses back to Agent messages.
///
/// # Features
/// - Supports 8+ OpenAI-compatible inference services
/// - Async message processing
/// - Configurable temperature, top_p, and max_tokens
/// - Provider metadata for debugging and monitoring
/// - Error handling with typed errors
///
/// # Example
/// ```no_run
/// use agenkit::adapters::openai_compatible::{OpenAICompatibleAgent, OpenAICompatibleConfig};
/// use agenkit::core::{Agent, Message};
///
/// #[tokio::main]
/// async fn main() -> Result<(), Box<dyn std::error::Error>> {
///     // vLLM local deployment
///     let config = OpenAICompatibleConfig {
///         base_url: "http://localhost:8000/v1".to_string(),
///         model: "meta-llama/Llama-2-7b-chat-hf".to_string(),
///         provider: Some("vllm".to_string()),
///         ..Default::default()
///     };
///
///     let agent = OpenAICompatibleAgent::new(config);
///     let msg = Message::with_text("user", "What is machine learning?");
///     let response = agent.process(msg).await?;
///
///     println!("{}", response.content_as_str().unwrap_or(""));
///     Ok(())
/// }
/// ```
pub struct OpenAICompatibleAgent {
    config: OpenAICompatibleConfig,
    #[cfg(feature = "native")]
    client: Client,
}

impl OpenAICompatibleAgent {
    /// Create a new OpenAI-compatible agent with configuration.
    ///
    /// # Arguments
    /// * `config` - Configuration including base URL, model, and optional provider name
    ///
    /// # Example
    /// ```
    /// use agenkit::adapters::openai_compatible::{OpenAICompatibleAgent, OpenAICompatibleConfig};
    ///
    /// let config = OpenAICompatibleConfig {
    ///     base_url: "http://localhost:8000/v1".to_string(),
    ///     model: "llama-2-7b".to_string(),
    ///     provider: Some("vllm".to_string()),
    ///     ..Default::default()
    /// };
    ///
    /// let agent = OpenAICompatibleAgent::new(config);
    /// ```
    pub fn new(config: OpenAICompatibleConfig) -> Self {
        // Validate temperature (0-2)
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

    /// Call OpenAI-compatible API with messages.
    #[cfg(feature = "native")]
    async fn call_api(
        &self,
        messages: Vec<ChatMessage>,
    ) -> Result<ChatCompletionResponse, AgentError> {
        let mut request = ChatCompletionRequest {
            model: self.config.model.clone(),
            messages,
            max_tokens: Some(self.config.max_tokens),
            temperature: None,
            top_p: None,
        };

        // Only include optional parameters if not default
        if (self.config.temperature - 0.7).abs() > f64::EPSILON {
            request.temperature = Some(self.config.temperature);
        }
        if (self.config.top_p - 1.0).abs() > f64::EPSILON {
            request.top_p = Some(self.config.top_p);
        }

        let url = format!("{}/chat/completions", self.config.base_url);

        let api_key = self.config.api_key.as_deref().unwrap_or("not-needed");

        let response = self
            .client
            .post(&url)
            .header("Authorization", format!("Bearer {}", api_key))
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
                .unwrap_or_else(|_| "unknown error".to_string());
            return Err(AgentError::Transport(format!(
                "openai-compatible API error ({}): {}",
                status, error_text
            )));
        }

        response
            .json::<ChatCompletionResponse>()
            .await
            .map_err(AgentError::Http)
    }

    /// Convert Agent message to OpenAI format.
    ///
    /// Maps agent role to assistant for OpenAI compatibility.
    fn message_to_chat_message(&self, message: &Message) -> ChatMessage {
        let role = match message.role.as_str() {
            "system" | "user" | "tool" => message.role.clone(),
            "agent" => "assistant".to_string(),
            _ => "assistant".to_string(),
        };

        ChatMessage {
            role,
            content: message.content_as_str().unwrap_or("").to_string(),
        }
    }

    /// Convert OpenAI response to Agent message.
    ///
    /// Includes provider metadata for debugging and monitoring.
    fn response_to_message(&self, response: ChatCompletionResponse) -> Message {
        let content = if !response.choices.is_empty() {
            response.choices[0].message.content.clone()
        } else {
            String::new()
        };

        let role = if !response.choices.is_empty() {
            response.choices[0].message.role.clone()
        } else {
            "assistant".to_string()
        };

        let mut msg = Message::with_text(&role, &content);

        // Add metadata with provider information
        msg.metadata
            .insert("model".to_string(), json!(response.model));
        msg.metadata.insert("id".to_string(), json!(response.id));

        // Add usage metadata if available
        if let Some(usage) = response.usage {
            msg.metadata.insert(
                "usage".to_string(),
                json!({
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                }),
            );
        }

        // Add finish_reason if available
        if !response.choices.is_empty() {
            if let Some(finish_reason) = &response.choices[0].finish_reason {
                msg.metadata
                    .insert("finish_reason".to_string(), json!(finish_reason));
            }
        }

        // Add provider metadata for debugging
        let provider = self
            .config
            .provider
            .as_deref()
            .unwrap_or("openai_compatible");
        msg.metadata.insert("provider".to_string(), json!(provider));
        msg.metadata
            .insert("base_url".to_string(), json!(self.config.base_url));

        msg
    }
}

#[async_trait]
impl Agent for OpenAICompatibleAgent {
    fn name(&self) -> &str {
        self.config
            .provider
            .as_deref()
            .unwrap_or("openai_compatible")
    }

    #[cfg(feature = "native")]
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let chat_message = self.message_to_chat_message(&message);
        let response = self.call_api(vec![chat_message]).await?;
        Ok(self.response_to_message(response))
    }

    #[cfg(not(feature = "native"))]
    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        Err(AgentError::Transport(
            "openai-compatible adapter requires 'native' feature".to_string(),
        ))
    }

    fn capabilities(&self) -> Vec<String> {
        let mut caps = vec![
            "llm".to_string(),
            "text-generation".to_string(),
            "openai-compatible".to_string(),
        ];

        if let Some(provider) = &self.config.provider {
            caps.push(provider.clone());
        }

        caps
    }
}

/// Common provider configurations for convenience.
pub mod providers {
    use super::OpenAICompatibleConfig;

    /// vLLM configuration (default port 8000).
    pub fn vllm(model: impl Into<String>) -> OpenAICompatibleConfig {
        OpenAICompatibleConfig {
            base_url: "http://localhost:8000/v1".to_string(),
            model: model.into(),
            provider: Some("vllm".to_string()),
            ..Default::default()
        }
    }

    /// llama.cpp configuration (default port 8080).
    pub fn llamacpp(model: impl Into<String>) -> OpenAICompatibleConfig {
        OpenAICompatibleConfig {
            base_url: "http://localhost:8080/v1".to_string(),
            model: model.into(),
            provider: Some("llamacpp".to_string()),
            ..Default::default()
        }
    }

    /// SGLang configuration (default port 30000).
    pub fn sglang(model: impl Into<String>) -> OpenAICompatibleConfig {
        OpenAICompatibleConfig {
            base_url: "http://localhost:30000/v1".to_string(),
            model: model.into(),
            provider: Some("sglang".to_string()),
            ..Default::default()
        }
    }

    /// TensorRT-LLM configuration (default port 8001).
    pub fn tensorrt(model: impl Into<String>) -> OpenAICompatibleConfig {
        OpenAICompatibleConfig {
            base_url: "http://localhost:8001/v1".to_string(),
            model: model.into(),
            provider: Some("tensorrt".to_string()),
            ..Default::default()
        }
    }
}

#[cfg(all(test, feature = "native"))]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_agent_creation() {
        let config = OpenAICompatibleConfig {
            base_url: "http://localhost:8000/v1".to_string(),
            model: "llama-2-7b".to_string(),
            provider: Some("vllm".to_string()),
            ..Default::default()
        };

        let agent = OpenAICompatibleAgent::new(config);
        assert_eq!(agent.name(), "vllm");
    }

    #[tokio::test]
    async fn test_agent_creation_without_provider() {
        let config = OpenAICompatibleConfig {
            base_url: "http://localhost:8000/v1".to_string(),
            model: "llama-2-7b".to_string(),
            provider: None,
            ..Default::default()
        };

        let agent = OpenAICompatibleAgent::new(config);
        assert_eq!(agent.name(), "openai_compatible");
    }

    #[tokio::test]
    async fn test_agent_capabilities() {
        let config = OpenAICompatibleConfig {
            base_url: "http://localhost:8000/v1".to_string(),
            model: "llama-2-7b".to_string(),
            provider: Some("vllm".to_string()),
            ..Default::default()
        };

        let agent = OpenAICompatibleAgent::new(config);
        let caps = agent.capabilities();
        assert!(caps.contains(&"llm".to_string()));
        assert!(caps.contains(&"openai-compatible".to_string()));
        assert!(caps.contains(&"vllm".to_string()));
    }

    #[test]
    fn test_message_conversion() {
        let config = OpenAICompatibleConfig::default();
        let agent = OpenAICompatibleAgent::new(config);

        // Test user message
        let msg = Message::with_text("user", "Hello");
        let chat_msg = agent.message_to_chat_message(&msg);
        assert_eq!(chat_msg.role, "user");
        assert_eq!(chat_msg.content, "Hello");

        // Test agent message (should convert to assistant)
        let msg = Message::with_text("agent", "Hi there");
        let chat_msg = agent.message_to_chat_message(&msg);
        assert_eq!(chat_msg.role, "assistant");
        assert_eq!(chat_msg.content, "Hi there");

        // Test system message
        let msg = Message::with_text("system", "You are helpful");
        let chat_msg = agent.message_to_chat_message(&msg);
        assert_eq!(chat_msg.role, "system");
    }

    #[test]
    fn test_provider_configs() {
        let vllm = providers::vllm("meta-llama/Llama-2-7b-chat-hf");
        assert_eq!(vllm.base_url, "http://localhost:8000/v1");
        assert_eq!(vllm.provider, Some("vllm".to_string()));

        let llamacpp = providers::llamacpp("llama-2-7b-chat");
        assert_eq!(llamacpp.base_url, "http://localhost:8080/v1");
        assert_eq!(llamacpp.provider, Some("llamacpp".to_string()));

        let sglang = providers::sglang("meta-llama/Llama-2-13b-chat-hf");
        assert_eq!(sglang.base_url, "http://localhost:30000/v1");
        assert_eq!(sglang.provider, Some("sglang".to_string()));

        let tensorrt = providers::tensorrt("llama-2-70b");
        assert_eq!(tensorrt.base_url, "http://localhost:8001/v1");
        assert_eq!(tensorrt.provider, Some("tensorrt".to_string()));
    }
}
