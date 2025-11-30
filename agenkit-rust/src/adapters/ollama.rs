///! Ollama API adapter.
///!
///! This module provides an adapter for calling Ollama's local LLM API.
///! Supports all Ollama models including Llama, Mistral, and others.

use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use serde_json::json;

#[cfg(feature = "native")]
use reqwest::Client;

/// Configuration for Ollama API calls.
#[derive(Debug, Clone)]
pub struct OllamaConfig {
    /// Model to use (default: llama2)
    pub model: String,

    /// Temperature 0-2 (default: 0.7)
    pub temperature: f64,

    /// API endpoint (default: local Ollama)
    pub api_base: String,

    /// Request timeout in seconds (default: 120)
    pub timeout_seconds: u64,
}

impl Default for OllamaConfig {
    fn default() -> Self {
        Self {
            model: "llama2".to_string(),
            temperature: 0.7,
            api_base: "http://localhost:11434".to_string(),
            timeout_seconds: 120,
        }
    }
}

/// Ollama chat message.
#[derive(Debug, Serialize)]
struct OllamaMessage {
    role: String,
    content: String,
}

/// Ollama chat request.
#[derive(Debug, Serialize)]
struct ChatRequest {
    model: String,
    messages: Vec<OllamaMessage>,
    stream: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    options: Option<ChatOptions>,
}

#[derive(Debug, Serialize)]
struct ChatOptions {
    temperature: f64,
}

/// Ollama chat response.
#[derive(Debug, Deserialize)]
struct ChatResponse {
    model: String,
    message: ResponseMessage,
    done: bool,
    #[serde(default)]
    total_duration: Option<u64>,
    #[serde(default)]
    prompt_eval_count: Option<i32>,
    #[serde(default)]
    eval_count: Option<i32>,
}

#[derive(Debug, Deserialize)]
struct ResponseMessage {
    role: String,
    content: String,
}

/// Agent adapter for Ollama API.
///
/// This adapter wraps the Ollama Chat API, enabling use of local LLM models
/// through Ollama's simple HTTP interface.
///
/// # Features
/// - Supports all Ollama models (Llama, Mistral, etc.)
/// - Local inference (no API key required)
/// - Async message processing
/// - Configurable temperature
///
/// # Example
/// ```no_run
/// use agenkit::adapters::ollama::{OllamaAgent, OllamaConfig};
/// use agenkit::core::{Agent, Message};
///
/// #[tokio::main]
/// async fn main() -> Result<(), Box<dyn std::error::Error>> {
///     let config = OllamaConfig {
///         model: "llama2".to_string(),
///         ..Default::default()
///     };
///
///     let agent = OllamaAgent::new(config);
///     let msg = Message::with_text("user", "What is the capital of France?");
///     let response = agent.process(msg).await?;
///
///     println!("{}", response.content_as_str().unwrap_or(""));
///     Ok(())
/// }
/// ```
pub struct OllamaAgent {
    config: OllamaConfig,
    #[cfg(feature = "native")]
    client: Client,
}

impl OllamaAgent {
    /// Create a new Ollama agent with configuration.
    ///
    /// # Arguments
    /// * `config` - Configuration including model and endpoint
    pub fn new(config: OllamaConfig) -> Self {
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

    /// Call Ollama API with messages.
    #[cfg(feature = "native")]
    async fn call_api(&self, messages: Vec<OllamaMessage>) -> Result<ChatResponse, AgentError> {
        let request = ChatRequest {
            model: self.config.model.clone(),
            messages,
            stream: false,
            options: Some(ChatOptions {
                temperature: self.config.temperature,
            }),
        };

        let url = format!("{}/api/chat", self.config.api_base);

        let response = self
            .client
            .post(&url)
            .json(&request)
            .send()
            .await
            .map_err(|e| AgentError::Http(e))?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_else(|_| "Unknown error".to_string());
            return Err(AgentError::Transport(format!(
                "Ollama API error ({}): {}",
                status, error_text
            )));
        }

        response
            .json::<ChatResponse>()
            .await
            .map_err(|e| AgentError::Http(e))
    }

    /// Convert Agent message to Ollama format.
    fn message_to_ollama_message(&self, message: &Message) -> OllamaMessage {
        OllamaMessage {
            role: message.role.clone(),
            content: message.content_as_str().unwrap_or("").to_string(),
        }
    }

    /// Convert Ollama response to Agent message.
    fn response_to_message(&self, response: ChatResponse) -> Message {
        let mut msg = Message::with_text(
            &response.message.role,
            &response.message.content,
        );

        // Add metadata
        msg.metadata.insert("model".to_string(), json!(response.model));

        if let Some(duration) = response.total_duration {
            msg.metadata.insert("total_duration_ns".to_string(), json!(duration));
        }

        if let (Some(prompt_tokens), Some(completion_tokens)) =
            (response.prompt_eval_count, response.eval_count) {
            msg.metadata.insert("usage".to_string(), json!({
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }));
        }

        msg
    }
}

#[async_trait]
impl Agent for OllamaAgent {
    fn name(&self) -> &str {
        "ollama"
    }

    #[cfg(feature = "native")]
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let ollama_message = self.message_to_ollama_message(&message);
        let response = self.call_api(vec![ollama_message]).await?;
        Ok(self.response_to_message(response))
    }

    #[cfg(not(feature = "native"))]
    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        Err(AgentError::Transport(
            "Ollama adapter requires 'native' feature".to_string(),
        ))
    }

    fn capabilities(&self) -> Vec<String> {
        vec![
            "llm".to_string(),
            "text-generation".to_string(),
            "ollama".to_string(),
            "local".to_string(),
        ]
    }
}

/// Popular Ollama models.
pub mod models {
    /// Llama 2 (7B) - General purpose
    pub const LLAMA2: &str = "llama2";

    /// Llama 2 (13B) - More capable
    pub const LLAMA2_13B: &str = "llama2:13b";

    /// Llama 3 (8B) - Latest Llama model
    pub const LLAMA3: &str = "llama3";

    /// Mistral (7B) - Fast and efficient
    pub const MISTRAL: &str = "mistral";

    /// CodeLlama (7B) - Code generation
    pub const CODELLAMA: &str = "codellama";

    /// Phi-2 (2.7B) - Small but capable
    pub const PHI2: &str = "phi";
}

#[cfg(all(test, feature = "native"))]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_ollama_agent_creation() {
        let config = OllamaConfig::default();
        let agent = OllamaAgent::new(config);
        assert_eq!(agent.name(), "ollama");
    }

    #[tokio::test]
    async fn test_ollama_agent_capabilities() {
        let config = OllamaConfig::default();
        let agent = OllamaAgent::new(config);
        let caps = agent.capabilities();
        assert!(caps.contains(&"llm".to_string()));
        assert!(caps.contains(&"ollama".to_string()));
        assert!(caps.contains(&"local".to_string()));
    }
}
