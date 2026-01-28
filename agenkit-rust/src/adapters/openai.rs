///! OpenAI API adapter.
///!
///! This module provides an adapter for calling OpenAI's GPT API via HTTP.
///! Supports GPT-4, GPT-4 Turbo, GPT-3.5 Turbo, and other OpenAI models.
use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use futures::Stream;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::pin::Pin;

#[cfg(feature = "native")]
use reqwest::Client;

/// Configuration for OpenAI API calls.
#[derive(Debug, Clone)]
pub struct OpenAIConfig {
    /// API key (required) - get from https://platform.openai.com/api-keys
    pub api_key: String,

    /// Model to use (default: gpt-4-turbo)
    pub model: String,

    /// Maximum tokens to generate (default: 1024)
    pub max_tokens: i32,

    /// Temperature 0-2 (default: 0.7)
    pub temperature: f64,

    /// Top P sampling (default: 1.0)
    pub top_p: f64,

    /// Frequency penalty -2.0 to 2.0 (default: 0.0)
    pub frequency_penalty: f64,

    /// Presence penalty -2.0 to 2.0 (default: 0.0)
    pub presence_penalty: f64,

    /// API endpoint (default: OpenAI production)
    pub api_base: String,

    /// Request timeout in seconds (default: 60)
    pub timeout_seconds: u64,
}

impl Default for OpenAIConfig {
    fn default() -> Self {
        Self {
            api_key: std::env::var("OPENAI_API_KEY").unwrap_or_default(),
            model: "gpt-4-turbo".to_string(),
            max_tokens: 1024,
            temperature: 0.7,
            top_p: 1.0,
            frequency_penalty: 0.0,
            presence_penalty: 0.0,
            api_base: "https://api.openai.com".to_string(),
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
    #[serde(skip_serializing_if = "Option::is_none")]
    frequency_penalty: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    presence_penalty: Option<f64>,
}

/// OpenAI chat completion response.
#[derive(Debug, Deserialize)]
struct ChatCompletionResponse {
    id: String,
    model: String,
    choices: Vec<Choice>,
    usage: Usage,
}

#[derive(Debug, Deserialize)]
struct Choice {
    message: ResponseMessage,
    finish_reason: String,
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

/// Agent adapter for OpenAI API.
///
/// This adapter wraps the OpenAI Chat Completions API, converting Agent messages
/// to OpenAI API calls and responses back to Agent messages.
///
/// # Features
/// - Supports all OpenAI chat models (GPT-4, GPT-3.5, etc.)
/// - Async message processing
/// - Configurable temperature, top_p, and penalties
/// - Error handling with typed errors
///
/// # Example
/// ```no_run
/// use agenkit::adapters::openai::{OpenAIAgent, OpenAIConfig};
/// use agenkit::core::{Agent, Message};
///
/// #[tokio::main]
/// async fn main() -> Result<(), Box<dyn std::error::Error>> {
///     let config = OpenAIConfig {
///         api_key: std::env::var("OPENAI_API_KEY")?,
///         model: "gpt-4-turbo".to_string(),
///         ..Default::default()
///     };
///
///     let agent = OpenAIAgent::new(config);
///     let msg = Message::with_text("user", "What is the capital of France?");
///     let response = agent.process(msg).await?;
///
///     println!("{}", response.content_as_str().unwrap_or(""));
///     Ok(())
/// }
/// ```
pub struct OpenAIAgent {
    config: OpenAIConfig,
    #[cfg(feature = "native")]
    client: Client,
}

impl OpenAIAgent {
    /// Create a new OpenAI agent with configuration.
    ///
    /// # Arguments
    /// * `config` - Configuration including API key and model
    ///
    /// # Panics
    /// Panics if API key is empty
    pub fn new(config: OpenAIConfig) -> Self {
        if config.api_key.is_empty() {
            panic!("OpenAI API key cannot be empty");
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

    /// Call OpenAI API with messages.
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
            frequency_penalty: None,
            presence_penalty: None,
        };

        // Only include optional parameters if not default
        if (self.config.temperature - 0.7).abs() > f64::EPSILON {
            request.temperature = Some(self.config.temperature);
        }
        if (self.config.top_p - 1.0).abs() > f64::EPSILON {
            request.top_p = Some(self.config.top_p);
        }
        if self.config.frequency_penalty.abs() > f64::EPSILON {
            request.frequency_penalty = Some(self.config.frequency_penalty);
        }
        if self.config.presence_penalty.abs() > f64::EPSILON {
            request.presence_penalty = Some(self.config.presence_penalty);
        }

        let url = format!("{}/v1/chat/completions", self.config.api_base);

        let response = self
            .client
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.config.api_key))
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await
            .map_err(|e| AgentError::Http(e))?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response
                .text()
                .await
                .unwrap_or_else(|_| "Unknown error".to_string());
            return Err(AgentError::Transport(format!(
                "OpenAI API error ({}): {}",
                status, error_text
            )));
        }

        response
            .json::<ChatCompletionResponse>()
            .await
            .map_err(|e| AgentError::Http(e))
    }

    /// Convert Agent message to OpenAI format.
    fn message_to_chat_message(&self, message: &Message) -> ChatMessage {
        ChatMessage {
            role: message.role.clone(),
            content: message.content_as_str().unwrap_or("").to_string(),
        }
    }

    /// Convert OpenAI response to Agent message.
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

        // Add metadata
        msg.metadata
            .insert("openai_message_id".to_string(), json!(response.id));
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

    /// Stream completion from OpenAI API.
    ///
    /// Returns a stream of Message chunks as they arrive from the API.
    #[cfg(feature = "native")]
    pub async fn stream(
        &self,
        message: Message,
    ) -> Pin<Box<dyn Stream<Item = Result<Message, AgentError>> + Send>> {
        let chat_message = self.message_to_chat_message(&message);

        match self.stream_api_impl(vec![chat_message]).await {
            Ok(chunks) => {
                Box::pin(futures::stream::iter(chunks.into_iter().map(Ok)))
            }
            Err(e) => {
                Box::pin(futures::stream::once(async move { Err(e) }))
            }
        }
    }

    #[cfg(not(feature = "native"))]
    pub async fn stream(
        &self,
        _message: Message,
    ) -> Pin<Box<dyn Stream<Item = Result<Message, AgentError>> + Send>> {
        Box::pin(futures::stream::once(async {
            Err(AgentError::Transport(
                "OpenAI adapter requires 'native' feature for streaming".to_string(),
            ))
        }))
    }

    /// Internal streaming implementation.
    #[cfg(feature = "native")]
    async fn stream_api_impl(
        &self,
        messages: Vec<ChatMessage>,
    ) -> Result<Vec<Message>, AgentError> {
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(self.config.timeout_seconds))
            .build()
            .map_err(|e| AgentError::Transport(e.to_string()))?;

        let mut request_body = serde_json::to_value(&ChatCompletionRequest {
            model: self.config.model.clone(),
            messages,
            max_tokens: Some(self.config.max_tokens),
            temperature: Some(self.config.temperature),
            top_p: Some(self.config.top_p),
            frequency_penalty: Some(self.config.frequency_penalty),
            presence_penalty: Some(self.config.presence_penalty),
        })
        ?;

        // Add stream parameter
        request_body["stream"] = json!(true);

        let response = client
            .post(format!("{}/v1/chat/completions", self.config.api_base))
            .header("Authorization", format!("Bearer {}", self.config.api_key))
            .header("Content-Type", "application/json")
            .json(&request_body)
            .send()
            .await
            .map_err(|e| AgentError::Transport(e.to_string()))?;

        if !response.status().is_success() {
            let status = response.status();
            let body = response.text().await.unwrap_or_default();
            return Err(AgentError::Transport(format!(
                "OpenAI API error ({}): {}",
                status, body
            )));
        }

        // Collect full response body first (pseudo-streaming)
        let body = response
            .text()
            .await
            .map_err(|e| AgentError::Transport(e.to_string()))?;

        // Parse SSE stream
        let mut chunks = Vec::new();
        for line in body.lines() {
            if line.is_empty() || !line.starts_with("data: ") {
                continue;
            }

            let json_str = &line[6..]; // Skip "data: "

            if json_str == "[DONE]" {
                break;
            }

            let chunk_json: Value = serde_json::from_str(json_str)
                ?;

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
impl Agent for OpenAIAgent {
    fn name(&self) -> &str {
        "openai"
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
            "OpenAI adapter requires 'native' feature".to_string(),
        ))
    }

    fn capabilities(&self) -> Vec<String> {
        vec![
            "llm".to_string(),
            "text-generation".to_string(),
            "openai".to_string(),
        ]
    }
}

/// Available OpenAI models (November 2025).
pub mod models {
    /// GPT-4 Turbo - Most capable, 128k context
    pub const GPT_4_TURBO: &str = "gpt-4-turbo";

    /// GPT-4 - High capability, 8k context
    pub const GPT_4: &str = "gpt-4";

    /// GPT-4o - Multimodal flagship
    pub const GPT_4O: &str = "gpt-4o";

    /// GPT-4o Mini - Fast and affordable
    pub const GPT_4O_MINI: &str = "gpt-4o-mini";

    /// GPT-3.5 Turbo - Fast and cost-effective
    pub const GPT_3_5_TURBO: &str = "gpt-3.5-turbo";
}

#[cfg(all(test, feature = "native"))]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_openai_agent_creation() {
        let config = OpenAIConfig {
            api_key: "test-key".to_string(),
            ..Default::default()
        };

        let agent = OpenAIAgent::new(config);
        assert_eq!(agent.name(), "openai");
    }

    #[tokio::test]
    async fn test_openai_agent_capabilities() {
        let config = OpenAIConfig {
            api_key: "test-key".to_string(),
            ..Default::default()
        };

        let agent = OpenAIAgent::new(config);
        let caps = agent.capabilities();
        assert!(caps.contains(&"llm".to_string()));
        assert!(caps.contains(&"openai".to_string()));
    }
}
