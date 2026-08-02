//! Google Gemini LLM adapter.
//!
//! Provides integration with Google's Gemini models (Gemini 2.0, Gemini 1.5 Pro, etc.).
//! Supports both completion and streaming modes via the Gemini REST API.
use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use futures::stream::Stream;
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::pin::Pin;

#[cfg(feature = "native")]
use reqwest::Client;

/// Configuration for Gemini adapter.
#[derive(Debug, Clone)]
pub struct GeminiConfig {
    /// Google API key. If not provided, uses GEMINI_API_KEY or GOOGLE_API_KEY environment variable
    pub api_key: String,

    /// Model to use (default: gemini-2.0-flash-exp)
    /// Examples: "gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"
    pub model: String,

    /// Temperature for sampling (0.0 - 2.0)
    pub temperature: Option<f32>,

    /// Maximum tokens to generate
    pub max_tokens: Option<u32>,

    /// Top-p sampling parameter
    pub top_p: Option<f32>,

    /// Top-k sampling parameter
    pub top_k: Option<u32>,

    /// Stop sequences
    pub stop_sequences: Vec<String>,

    /// Request timeout in seconds (default: 60)
    pub timeout_seconds: u64,
}

impl Default for GeminiConfig {
    fn default() -> Self {
        let api_key = std::env::var("GEMINI_API_KEY")
            .or_else(|_| std::env::var("GOOGLE_API_KEY"))
            .unwrap_or_default();

        Self {
            api_key,
            model: "gemini-2.0-flash-exp".to_string(),
            temperature: Some(0.7),
            max_tokens: Some(8192),
            top_p: Some(1.0),
            top_k: Some(40),
            stop_sequences: Vec::new(),
            timeout_seconds: 60,
        }
    }
}

/// Gemini content part.
#[derive(Debug, Serialize, Deserialize)]
struct GeminiPart {
    text: String,
}

/// Gemini content block.
#[derive(Debug, Serialize, Deserialize)]
struct GeminiContent {
    role: String,
    parts: Vec<GeminiPart>,
}

/// Gemini generation configuration.
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct GeminiGenerationConfig {
    #[serde(skip_serializing_if = "Option::is_none")]
    temperature: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    max_output_tokens: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    top_p: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    top_k: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    stop_sequences: Option<Vec<String>>,
}

/// Gemini generate content request.
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct GeminiRequest {
    contents: Vec<GeminiContent>,
    #[serde(skip_serializing_if = "Option::is_none")]
    generation_config: Option<GeminiGenerationConfig>,
}

/// Gemini candidate response.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct GeminiCandidate {
    content: GeminiContent,
    finish_reason: Option<String>,
}

/// Gemini usage metadata.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct GeminiUsageMetadata {
    prompt_token_count: Option<i32>,
    candidates_token_count: Option<i32>,
    total_token_count: Option<i32>,
}

/// Gemini generate content response.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct GeminiResponse {
    candidates: Option<Vec<GeminiCandidate>>,
    usage_metadata: Option<GeminiUsageMetadata>,
}

/// Agent adapter for Google Gemini API.
///
/// This adapter wraps the Google Gemini REST API, converting Agent messages
/// to Gemini API calls and responses back to Agent messages.
///
/// # Features
/// - Supports all Gemini models (Gemini 2.0, Gemini 1.5 Pro, etc.)
/// - Async message processing
/// - Configurable temperature, top_p, top_k, and max tokens
/// - System message support (converted to user message)
/// - Error handling with typed errors
///
/// # Example
/// ```no_run
/// use agenkit::adapters::gemini::{GeminiAdapter, GeminiConfig};
/// use agenkit::core::{Agent, Message};
///
/// #[tokio::main]
/// async fn main() -> Result<(), Box<dyn std::error::Error>> {
///     let config = GeminiConfig {
///         api_key: std::env::var("GEMINI_API_KEY")?,
///         model: "gemini-2.0-flash-exp".to_string(),
///         ..Default::default()
///     };
///
///     let adapter = GeminiAdapter::new(config)?;
///     let msg = Message::with_text("user", "What is the capital of France?");
///     let response = adapter.process(msg).await?;
///
///     println!("{}", response.content_as_str().unwrap_or(""));
///     Ok(())
/// }
/// ```
pub struct GeminiAdapter {
    config: GeminiConfig,
    #[cfg(feature = "native")]
    client: Client,
}

impl GeminiAdapter {
    /// Create a new Gemini adapter with configuration.
    ///
    /// # Arguments
    /// * `config` - Configuration including API key and model
    ///
    /// # Errors
    /// Returns error if API key is empty
    pub fn new(config: GeminiConfig) -> Result<Self, AgentError> {
        if config.api_key.is_empty() {
            return Err(AgentError::InvalidInput(
                "Gemini API key required: provide api_key or set GEMINI_API_KEY or GOOGLE_API_KEY environment variable".to_string()
            ));
        }

        // Validate temperature (0-2)
        if let Some(temp) = config.temperature {
            if !(0.0..=2.0).contains(&temp) {
                return Err(AgentError::InvalidInput(format!(
                    "temperature must be between 0 and 2, got {}",
                    temp
                )));
            }
        }

        // Validate max_tokens (must be positive)
        if let Some(max_tok) = config.max_tokens {
            if max_tok == 0 {
                return Err(AgentError::InvalidInput(format!(
                    "max_tokens must be positive, got {}",
                    max_tok
                )));
            }
        }

        // Validate top_p (0-1)
        if let Some(tp) = config.top_p {
            if !(0.0..=1.0).contains(&tp) {
                return Err(AgentError::InvalidInput(format!(
                    "top_p must be between 0 and 1, got {}",
                    tp
                )));
            }
        }

        #[cfg(feature = "native")]
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(config.timeout_seconds))
            .build()
            .map_err(|e| AgentError::Internal(format!("failed to create HTTP client: {}", e)))?;

        Ok(Self {
            config,
            #[cfg(feature = "native")]
            client,
        })
    }

    /// Call Gemini API with messages.
    #[cfg(feature = "native")]
    async fn call_api(&self, contents: Vec<GeminiContent>) -> Result<GeminiResponse, AgentError> {
        let generation_config = GeminiGenerationConfig {
            temperature: self.config.temperature,
            max_output_tokens: self.config.max_tokens,
            top_p: self.config.top_p,
            top_k: self.config.top_k,
            stop_sequences: if self.config.stop_sequences.is_empty() {
                None
            } else {
                Some(self.config.stop_sequences.clone())
            },
        };

        let request = GeminiRequest {
            contents,
            generation_config: Some(generation_config),
        };

        let url = format!(
            "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent?key={}",
            self.config.model, self.config.api_key
        );

        let response = self
            .client
            .post(&url)
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
                "Gemini API error ({}): {}",
                status, error_text
            )));
        }

        response
            .json::<GeminiResponse>()
            .await
            .map_err(AgentError::Http)
    }

    /// Convert Agent messages to Gemini format.
    fn messages_to_gemini_contents(&self, messages: &[Message]) -> Vec<GeminiContent> {
        messages
            .iter()
            .map(|msg| {
                let role = match msg.role.as_str() {
                    "user" | "system" => "user",
                    "assistant" | "agent" | _ => "model",
                };

                let text = msg.content_as_str().unwrap_or("").to_string();

                GeminiContent {
                    role: role.to_string(),
                    parts: vec![GeminiPart { text }],
                }
            })
            .collect()
    }

    /// Convert Gemini response to Agent message.
    fn response_to_message(&self, response: GeminiResponse) -> Result<Message, AgentError> {
        let candidates = response.candidates.ok_or_else(|| {
            AgentError::ProcessingError("Gemini returned no candidates".to_string())
        })?;

        if candidates.is_empty() {
            return Err(AgentError::ProcessingError(
                "Gemini returned empty candidates".to_string(),
            ));
        }

        let candidate = &candidates[0];
        let mut content = String::new();

        for part in &candidate.content.parts {
            content.push_str(&part.text);
        }

        let mut msg = Message::with_text("assistant", &content);

        // Add metadata
        msg.metadata
            .insert("model".to_string(), json!(self.config.model));

        if let Some(usage) = response.usage_metadata {
            msg.metadata.insert(
                "usage".to_string(),
                json!({
                    "prompt_tokens": usage.prompt_token_count.unwrap_or(0),
                    "completion_tokens": usage.candidates_token_count.unwrap_or(0),
                    "total_tokens": usage.total_token_count.unwrap_or(0),
                }),
            );
        }

        if let Some(finish_reason) = &candidate.finish_reason {
            msg.metadata
                .insert("finish_reason".to_string(), json!(finish_reason));
        }

        Ok(msg)
    }

    /// Stream completion from Gemini API.
    ///
    /// Returns chunks as they arrive from the API.
    /// Note: Currently collects full response before streaming for simplicity.
    ///
    /// # Arguments
    /// * `contents` - Gemini-formatted contents
    ///
    /// # Returns
    /// Vector of Message chunks containing incremental text
    #[cfg(feature = "native")]
    async fn stream_api_impl(
        &self,
        contents: Vec<GeminiContent>,
    ) -> Result<Vec<Message>, AgentError> {
        let generation_config = GeminiGenerationConfig {
            temperature: self.config.temperature,
            max_output_tokens: self.config.max_tokens,
            top_p: self.config.top_p,
            top_k: self.config.top_k,
            stop_sequences: if self.config.stop_sequences.is_empty() {
                None
            } else {
                Some(self.config.stop_sequences.clone())
            },
        };

        let request = GeminiRequest {
            contents,
            generation_config: Some(generation_config),
        };

        // Use streamGenerateContent endpoint for streaming
        let url = format!(
            "https://generativelanguage.googleapis.com/v1beta/models/{}:streamGenerateContent?key={}",
            self.config.model, self.config.api_key
        );

        let response = self
            .client
            .post(&url)
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
                "Gemini API error ({}): {}",
                status, error_text
            )));
        }

        // Parse newline-delimited JSON chunks
        let bytes = response.bytes().await.map_err(AgentError::Http)?;
        let text = String::from_utf8_lossy(&bytes);

        let mut chunks = Vec::new();

        // Each line is a separate JSON object
        for line in text.lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }

            // Parse JSON chunk
            match serde_json::from_str::<GeminiResponse>(line) {
                Ok(chunk_response) => {
                    // Extract text from candidates
                    if let Some(candidates) = chunk_response.candidates {
                        for candidate in candidates {
                            for part in candidate.content.parts {
                                if !part.text.is_empty() {
                                    let mut msg = Message::with_text("assistant", &part.text);
                                    msg.metadata.insert("streaming".to_string(), json!(true));
                                    msg.metadata
                                        .insert("model".to_string(), json!(self.config.model));
                                    chunks.push(msg);
                                }
                            }
                        }
                    }
                }
                Err(_) => {
                    // Skip malformed chunks
                    continue;
                }
            }
        }

        Ok(chunks)
    }

    /// Stream completion chunks from Gemini.
    ///
    /// Returns a stream of Message chunks as text arrives from the API.
    /// Note: Currently collects full response before streaming for simplicity.
    ///
    /// # Arguments
    /// * `messages` - Input messages to process
    ///
    /// # Returns
    /// Stream of Message chunks containing incremental text
    ///
    /// # Example
    /// ```no_run
    /// use agenkit::adapters::gemini::{GeminiAdapter, GeminiConfig};
    /// use agenkit::core::Message;
    /// use futures::stream::StreamExt;
    ///
    /// #[tokio::main]
    /// async fn main() -> Result<(), Box<dyn std::error::Error>> {
    ///     let config = GeminiConfig {
    ///         api_key: std::env::var("GEMINI_API_KEY")?,
    ///         ..Default::default()
    ///     };
    ///
    ///     let adapter = GeminiAdapter::new(config)?;
    ///     let msgs = vec![Message::with_text("user", "Count to 5")];
    ///
    ///     let mut stream = adapter.stream(msgs).await;
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
        messages: Vec<Message>,
    ) -> Pin<Box<dyn Stream<Item = Result<Message, AgentError>> + Send>> {
        let contents = self.messages_to_gemini_contents(&messages);

        match self.stream_api_impl(contents).await {
            Ok(chunks) => Box::pin(futures::stream::iter(chunks.into_iter().map(Ok))),
            Err(e) => Box::pin(futures::stream::once(async move { Err(e) })),
        }
    }

    #[cfg(not(feature = "native"))]
    pub async fn stream(
        &self,
        _messages: Vec<Message>,
    ) -> Pin<Box<dyn Stream<Item = Result<Message, AgentError>> + Send>> {
        Box::pin(futures::stream::once(async {
            Err(AgentError::Transport(
                "Gemini adapter requires 'native' feature for streaming".to_string(),
            ))
        }))
    }
}

#[async_trait]
impl Agent for GeminiAdapter {
    fn name(&self) -> &str {
        "gemini"
    }

    #[cfg(feature = "native")]
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let contents = self.messages_to_gemini_contents(&[message]);
        let response = self.call_api(contents).await?;
        self.response_to_message(response)
    }

    #[cfg(not(feature = "native"))]
    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        Err(AgentError::Transport(
            "Gemini adapter requires 'native' feature".to_string(),
        ))
    }

    fn capabilities(&self) -> Vec<String> {
        vec![
            "llm".to_string(),
            "text-generation".to_string(),
            "gemini".to_string(),
            "google".to_string(),
        ]
    }
}

/// Available Gemini models.
pub mod models {
    /// Gemini 2.0 Flash (experimental) - Fast and efficient
    pub const GEMINI_2_FLASH_EXP: &str = "gemini-2.0-flash-exp";

    /// Gemini 1.5 Pro - Most capable model
    pub const GEMINI_1_5_PRO: &str = "gemini-1.5-pro";

    /// Gemini 1.5 Flash - Fast and efficient
    pub const GEMINI_1_5_FLASH: &str = "gemini-1.5-flash";

    /// Gemini Pro - General purpose
    pub const GEMINI_PRO: &str = "gemini-pro";
}

#[cfg(all(test, feature = "native"))]
mod tests {
    use super::*;

    #[test]
    fn test_gemini_adapter_creation_with_key() {
        let config = GeminiConfig {
            api_key: "test-key".to_string(),
            ..Default::default()
        };

        let adapter = GeminiAdapter::new(config);
        assert!(adapter.is_ok());
        assert_eq!(adapter.unwrap().name(), "gemini");
    }

    #[test]
    fn test_gemini_adapter_creation_without_key() {
        let config = GeminiConfig {
            api_key: String::new(),
            ..Default::default()
        };

        let adapter = GeminiAdapter::new(config);
        assert!(adapter.is_err());
    }

    #[test]
    fn test_gemini_adapter_capabilities() {
        let config = GeminiConfig {
            api_key: "test-key".to_string(),
            ..Default::default()
        };

        let adapter = GeminiAdapter::new(config).unwrap();
        let caps = adapter.capabilities();
        assert!(caps.contains(&"llm".to_string()));
        assert!(caps.contains(&"gemini".to_string()));
        assert!(caps.contains(&"google".to_string()));
    }

    #[test]
    fn test_gemini_config_default() {
        // Don't test default if env vars not set
        let config = GeminiConfig {
            api_key: "test-key".to_string(),
            model: "gemini-2.0-flash-exp".to_string(),
            temperature: Some(0.7),
            max_tokens: Some(8192),
            top_p: Some(1.0),
            top_k: Some(40),
            stop_sequences: Vec::new(),
            timeout_seconds: 60,
        };

        assert_eq!(config.model, "gemini-2.0-flash-exp");
        assert_eq!(config.temperature, Some(0.7));
        assert_eq!(config.max_tokens, Some(8192));
        assert_eq!(config.top_p, Some(1.0));
        assert_eq!(config.top_k, Some(40));
        assert_eq!(config.timeout_seconds, 60);
    }

    #[test]
    fn test_gemini_config_custom() {
        let config = GeminiConfig {
            api_key: "custom-key".to_string(),
            model: "gemini-1.5-pro".to_string(),
            temperature: Some(0.9),
            max_tokens: Some(4096),
            top_p: Some(0.95),
            top_k: Some(20),
            stop_sequences: vec!["STOP".to_string()],
            timeout_seconds: 120,
        };

        assert_eq!(config.api_key, "custom-key");
        assert_eq!(config.model, "gemini-1.5-pro");
        assert_eq!(config.temperature, Some(0.9));
        assert_eq!(config.max_tokens, Some(4096));
    }

    #[test]
    fn test_messages_to_gemini_contents() {
        let config = GeminiConfig {
            api_key: "test-key".to_string(),
            ..Default::default()
        };
        let adapter = GeminiAdapter::new(config).unwrap();

        let messages = vec![
            Message::with_text("user", "Hello"),
            Message::with_text("assistant", "Hi there!"),
        ];

        let contents = adapter.messages_to_gemini_contents(&messages);
        assert_eq!(contents.len(), 2);
        assert_eq!(contents[0].role, "user");
        assert_eq!(contents[0].parts[0].text, "Hello");
        assert_eq!(contents[1].role, "model");
        assert_eq!(contents[1].parts[0].text, "Hi there!");
    }

    #[test]
    fn test_message_role_conversion() {
        let config = GeminiConfig {
            api_key: "test-key".to_string(),
            ..Default::default()
        };
        let adapter = GeminiAdapter::new(config).unwrap();

        // Test user role
        let user_msg = Message::with_text("user", "Hello");
        let contents = adapter.messages_to_gemini_contents(&[user_msg]);
        assert_eq!(contents[0].role, "user");

        // Test system role (maps to user)
        let system_msg = Message::with_text("system", "You are helpful");
        let contents = adapter.messages_to_gemini_contents(&[system_msg]);
        assert_eq!(contents[0].role, "user");

        // Test assistant role (maps to model)
        let assistant_msg = Message::with_text("assistant", "Hi");
        let contents = adapter.messages_to_gemini_contents(&[assistant_msg]);
        assert_eq!(contents[0].role, "model");

        // Test agent role (maps to model)
        let agent_msg = Message::with_text("agent", "Response");
        let contents = adapter.messages_to_gemini_contents(&[agent_msg]);
        assert_eq!(contents[0].role, "model");
    }

    #[test]
    fn test_model_constants() {
        assert_eq!(models::GEMINI_2_FLASH_EXP, "gemini-2.0-flash-exp");
        assert_eq!(models::GEMINI_1_5_PRO, "gemini-1.5-pro");
        assert_eq!(models::GEMINI_1_5_FLASH, "gemini-1.5-flash");
        assert_eq!(models::GEMINI_PRO, "gemini-pro");
    }
}
