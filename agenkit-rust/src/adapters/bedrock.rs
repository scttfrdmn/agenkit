///! Amazon Bedrock LLM adapter for foundation models.
///!
///! Provides integration with Amazon Bedrock's foundation models including
///! Claude, Llama, Mistral, and Titan. Supports both completion and streaming modes.
use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use futures::stream::Stream;
use serde_json::json;
use std::pin::Pin;

#[cfg(feature = "native")]
use {
    aws_config::{BehaviorVersion, Region},
    aws_sdk_bedrockruntime::{
        types::{ContentBlock, ConversationRole, ConverseOutput, ConverseStreamOutput, Message as BedrockMessage},
        Client as BedrockClient,
    },
    futures::stream::StreamExt,
};

/// Configuration for Bedrock adapter.
#[derive(Debug, Clone)]
pub struct BedrockConfig {
    /// AWS region (default: us-east-1)
    pub region: String,

    /// Bedrock model identifier
    /// Examples:
    /// - "anthropic.claude-3-5-sonnet-20241022-v2:0"
    /// - "anthropic.claude-3-haiku-20240307-v1:0"
    /// - "meta.llama3-70b-instruct-v1:0"
    /// - "mistral.mistral-large-2402-v1:0"
    /// - "amazon.titan-text-premier-v1:0"
    pub model: String,

    /// AWS access key ID (optional - uses default credential chain if not provided)
    pub access_key_id: Option<String>,

    /// AWS secret access key (optional - uses default credential chain if not provided)
    pub secret_access_key: Option<String>,

    /// AWS session token (optional)
    pub session_token: Option<String>,

    /// Temperature for sampling (0.0 - 1.0)
    pub temperature: Option<f32>,

    /// Maximum tokens to generate
    pub max_tokens: Option<u32>,

    /// Top-p sampling parameter
    pub top_p: Option<f32>,

    /// Stop sequences
    pub stop_sequences: Vec<String>,

    /// Request timeout in seconds (default: 60)
    pub timeout_seconds: u64,
}

impl Default for BedrockConfig {
    fn default() -> Self {
        Self {
            region: "us-east-1".to_string(),
            model: "anthropic.claude-3-5-sonnet-20241022-v2:0".to_string(),
            access_key_id: None,
            secret_access_key: None,
            session_token: None,
            temperature: Some(0.7),
            max_tokens: Some(4096),
            top_p: Some(1.0),
            stop_sequences: Vec::new(),
            timeout_seconds: 60,
        }
    }
}

/// Agent adapter for Amazon Bedrock.
///
/// This adapter wraps the AWS Bedrock Runtime API using the Converse API,
/// converting Agent messages to Bedrock API calls and responses back to Agent messages.
///
/// # Features
/// - Support for Claude, Llama, Mistral, Titan, and other Bedrock models
/// - Async message processing
/// - Configurable temperature, top_p, and max tokens
/// - System message support
/// - AWS credential chain support
/// - Error handling with typed errors
///
/// # Example
/// ```no_run
/// use agenkit::adapters::bedrock::{BedrockAdapter, BedrockConfig};
/// use agenkit::core::{Agent, Message};
///
/// #[tokio::main]
/// async fn main() -> Result<(), Box<dyn std::error::Error>> {
///     let config = BedrockConfig {
///         region: "us-east-1".to_string(),
///         model: "anthropic.claude-3-5-sonnet-20241022-v2:0".to_string(),
///         ..Default::default()
///     };
///
///     let adapter = BedrockAdapter::new(config).await?;
///     let msg = Message::with_text("user", "What is the capital of France?");
///     let response = adapter.process(msg).await?;
///
///     println!("{}", response.content_as_str().unwrap_or(""));
///     Ok(())
/// }
/// ```
pub struct BedrockAdapter {
    config: BedrockConfig,
    #[cfg(feature = "native")]
    client: BedrockClient,
}

impl BedrockAdapter {
    /// Create a new Bedrock adapter with configuration.
    ///
    /// # Arguments
    /// * `config` - Configuration including region and model
    ///
    /// # Errors
    /// Returns error if AWS client cannot be created
    #[cfg(feature = "native")]
    pub async fn new(config: BedrockConfig) -> Result<Self, AgentError> {
        let aws_config = if config.access_key_id.is_some() && config.secret_access_key.is_some() {
            // Use provided credentials
            let creds = aws_credential_types::Credentials::new(
                config.access_key_id.clone().unwrap(),
                config.secret_access_key.clone().unwrap(),
                config.session_token.clone(),
                None,
                "bedrock-adapter",
            );

            aws_config::defaults(BehaviorVersion::latest())
                .region(Region::new(config.region.clone()))
                .credentials_provider(creds)
                .load()
                .await
        } else {
            // Use default credential chain
            aws_config::defaults(BehaviorVersion::latest())
                .region(Region::new(config.region.clone()))
                .load()
                .await
        };

        let client = BedrockClient::new(&aws_config);

        Ok(Self { config, client })
    }

    #[cfg(not(feature = "native"))]
    pub async fn new(config: BedrockConfig) -> Result<Self, AgentError> {
        Ok(Self { config })
    }

    /// Call Bedrock Converse API with messages.
    #[cfg(feature = "native")]
    async fn call_api(
        &self,
        messages: Vec<BedrockMessage>,
        system: Option<Vec<aws_sdk_bedrockruntime::types::SystemContentBlock>>,
    ) -> Result<aws_sdk_bedrockruntime::operation::converse::ConverseOutput, AgentError> {
        let mut request = self
            .client
            .converse()
            .model_id(&self.config.model)
            .set_messages(Some(messages));

        // Add system messages if provided
        if let Some(system_blocks) = system {
            request = request.set_system(Some(system_blocks));
        }

        // Add inference configuration
        let mut inference_config = aws_sdk_bedrockruntime::types::InferenceConfiguration::builder();

        if let Some(temperature) = self.config.temperature {
            inference_config = inference_config.temperature(temperature);
        }

        if let Some(max_tokens) = self.config.max_tokens {
            inference_config = inference_config.max_tokens(max_tokens as i32);
        }

        if let Some(top_p) = self.config.top_p {
            inference_config = inference_config.top_p(top_p);
        }

        if !self.config.stop_sequences.is_empty() {
            inference_config =
                inference_config.set_stop_sequences(Some(self.config.stop_sequences.clone()));
        }

        request = request.inference_config(inference_config.build());

        let response = request
            .send()
            .await
            .map_err(|e| AgentError::Transport(format!("Bedrock API error: {}", e)))?;

        Ok(response)
    }

    /// Convert Agent messages to Bedrock format.
    #[cfg(feature = "native")]
    fn messages_to_bedrock_format(
        &self,
        messages: &[Message],
    ) -> (
        Vec<BedrockMessage>,
        Option<Vec<aws_sdk_bedrockruntime::types::SystemContentBlock>>,
    ) {
        let mut bedrock_messages = Vec::new();
        let mut system_blocks = Vec::new();

        for msg in messages {
            let content_str = msg.content_as_str().unwrap_or("").to_string();

            if msg.role == "system" {
                // System messages go into separate system blocks
                system_blocks.push(aws_sdk_bedrockruntime::types::SystemContentBlock::Text(
                    content_str,
                ));
                continue;
            }

            let role = match msg.role.as_str() {
                "user" => ConversationRole::User,
                "assistant" | "agent" | _ => ConversationRole::Assistant,
            };

            let content_block = ContentBlock::Text(content_str);

            let bedrock_msg = BedrockMessage::builder()
                .role(role)
                .content(content_block)
                .build()
                .expect("failed to build bedrock message");

            bedrock_messages.push(bedrock_msg);
        }

        let system = if system_blocks.is_empty() {
            None
        } else {
            Some(system_blocks)
        };

        (bedrock_messages, system)
    }

    /// Convert Bedrock response to Agent message.
    #[cfg(feature = "native")]
    fn response_to_message(
        &self,
        output: aws_sdk_bedrockruntime::operation::converse::ConverseOutput,
    ) -> Result<Message, AgentError> {
        let mut content = String::new();

        if let Some(ConverseOutput::Message(message)) = output.output {
            for block in message.content {
                if let ContentBlock::Text(text) = block {
                    content.push_str(&text);
                }
            }
        }

        let mut msg = Message::with_text("assistant", &content);

        // Add metadata
        msg.metadata
            .insert("model".to_string(), json!(self.config.model));

        if let Some(usage) = output.usage {
            msg.metadata.insert(
                "usage".to_string(),
                json!({
                    "prompt_tokens": usage.input_tokens,
                    "completion_tokens": usage.output_tokens,
                    "total_tokens": usage.total_tokens,
                }),
            );
        }

        msg.metadata.insert(
            "stop_reason".to_string(),
            json!(output.stop_reason.as_str()),
        );

        Ok(msg)
    }

    /// Stream completion from Bedrock Converse Stream API.
    ///
    /// Returns chunks as they arrive from the API.
    /// Note: Currently collects full response before streaming for simplicity.
    ///
    /// # Arguments
    /// * `bedrock_messages` - Bedrock-formatted messages
    /// * `system` - Optional system content blocks
    ///
    /// # Returns
    /// Vector of Message chunks containing incremental text
    #[cfg(feature = "native")]
    async fn stream_api_impl(
        &self,
        bedrock_messages: Vec<BedrockMessage>,
        system: Option<Vec<aws_sdk_bedrockruntime::types::SystemContentBlock>>,
    ) -> Result<Vec<Message>, AgentError> {
        let mut request = self
            .client
            .converse_stream()
            .model_id(&self.config.model)
            .set_messages(Some(bedrock_messages));

        // Add system messages if provided
        if let Some(system_blocks) = system {
            request = request.set_system(Some(system_blocks));
        }

        // Add inference configuration
        let mut inference_config = aws_sdk_bedrockruntime::types::InferenceConfiguration::builder();

        if let Some(temperature) = self.config.temperature {
            inference_config = inference_config.temperature(temperature);
        }

        if let Some(max_tokens) = self.config.max_tokens {
            inference_config = inference_config.max_tokens(max_tokens as i32);
        }

        if let Some(top_p) = self.config.top_p {
            inference_config = inference_config.top_p(top_p);
        }

        if !self.config.stop_sequences.is_empty() {
            inference_config =
                inference_config.set_stop_sequences(Some(self.config.stop_sequences.clone()));
        }

        request = request.inference_config(inference_config.build());

        let response = request
            .send()
            .await
            .map_err(|e| AgentError::Transport(format!("Bedrock streaming error: {}", e)))?;

        let mut chunks = Vec::new();
        let mut stream = response.stream;

        // Process streaming events
        loop {
            match stream.recv().await {
                Ok(Some(output)) => {
                    match output {
                        ConverseStreamOutput::ContentBlockDelta(delta) => {
                            // Extract text from delta
                            if let Some(aws_sdk_bedrockruntime::types::ContentBlockDelta::Text(text)) = delta.delta {
                                if !text.is_empty() {
                                    let mut msg = Message::with_text("assistant", &text);
                                    msg.metadata.insert("streaming".to_string(), json!(true));
                                    msg.metadata.insert("model".to_string(), json!(self.config.model));
                                    chunks.push(msg);
                                }
                            }
                        }
                        _ => {
                            // Ignore other event types (metadata, start, stop, etc.)
                        }
                    }
                }
                Ok(None) => break,
                Err(e) => {
                    return Err(AgentError::Transport(format!("Streaming error: {}", e)));
                }
            }
        }

        Ok(chunks)
    }

    /// Stream completion chunks from Bedrock.
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
    /// use agenkit::adapters::bedrock::{BedrockAdapter, BedrockConfig};
    /// use agenkit::core::Message;
    /// use futures::stream::StreamExt;
    ///
    /// #[tokio::main]
    /// async fn main() -> Result<(), Box<dyn std::error::Error>> {
    ///     let config = BedrockConfig {
    ///         region: "us-east-1".to_string(),
    ///         model: "anthropic.claude-3-5-sonnet-20241022-v2:0".to_string(),
    ///         ..Default::default()
    ///     };
    ///
    ///     let adapter = BedrockAdapter::new(config).await?;
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
        let (bedrock_messages, system) = self.messages_to_bedrock_format(&messages);

        match self.stream_api_impl(bedrock_messages, system).await {
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
                "Bedrock adapter requires 'native' feature for streaming".to_string(),
            ))
        }))
    }
}

#[async_trait]
impl Agent for BedrockAdapter {
    fn name(&self) -> &str {
        "bedrock"
    }

    #[cfg(feature = "native")]
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let (bedrock_messages, system) = self.messages_to_bedrock_format(&[message]);
        let response = self.call_api(bedrock_messages, system).await?;
        self.response_to_message(response)
    }

    #[cfg(not(feature = "native"))]
    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        Err(AgentError::Transport(
            "Bedrock adapter requires 'native' feature".to_string(),
        ))
    }

    fn capabilities(&self) -> Vec<String> {
        vec![
            "llm".to_string(),
            "text-generation".to_string(),
            "bedrock".to_string(),
            "aws".to_string(),
        ]
    }
}

/// Available Bedrock model identifiers.
pub mod models {
    // Claude models
    pub const CLAUDE_3_5_SONNET: &str = "anthropic.claude-3-5-sonnet-20241022-v2:0";
    pub const CLAUDE_3_OPUS: &str = "anthropic.claude-3-opus-20240229-v1:0";
    pub const CLAUDE_3_HAIKU: &str = "anthropic.claude-3-haiku-20240307-v1:0";

    // Llama models
    pub const LLAMA_3_70B: &str = "meta.llama3-70b-instruct-v1:0";
    pub const LLAMA_3_8B: &str = "meta.llama3-8b-instruct-v1:0";

    // Mistral models
    pub const MISTRAL_LARGE: &str = "mistral.mistral-large-2402-v1:0";
    pub const MISTRAL_7B: &str = "mistral.mistral-7b-instruct-v0:2";

    // Amazon Titan models
    pub const TITAN_PREMIER: &str = "amazon.titan-text-premier-v1:0";
    pub const TITAN_EXPRESS: &str = "amazon.titan-text-express-v1";
}

#[cfg(all(test, feature = "native"))]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_bedrock_adapter_creation() {
        let config = BedrockConfig::default();
        // Note: This will fail if AWS credentials are not configured
        // but we're just testing the structure
        let adapter = BedrockAdapter::new(config).await;
        // We can't assert success without valid AWS credentials
        // Just verify it compiles
        let _ = adapter;
    }

    #[test]
    fn test_bedrock_config_default() {
        let config = BedrockConfig::default();
        assert_eq!(config.region, "us-east-1");
        assert_eq!(config.model, "anthropic.claude-3-5-sonnet-20241022-v2:0");
        assert_eq!(config.temperature, Some(0.7));
        assert_eq!(config.max_tokens, Some(4096));
        assert_eq!(config.top_p, Some(1.0));
        assert_eq!(config.timeout_seconds, 60);
    }

    #[test]
    fn test_bedrock_config_custom() {
        let config = BedrockConfig {
            region: "us-west-2".to_string(),
            model: "anthropic.claude-3-haiku-20240307-v1:0".to_string(),
            access_key_id: Some("AKIAIOSFODNN7EXAMPLE".to_string()),
            secret_access_key: Some("wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY".to_string()),
            session_token: Some("token".to_string()),
            temperature: Some(0.9),
            max_tokens: Some(2048),
            top_p: Some(0.95),
            stop_sequences: vec!["STOP".to_string()],
            timeout_seconds: 120,
        };

        assert_eq!(config.region, "us-west-2");
        assert_eq!(config.model, "anthropic.claude-3-haiku-20240307-v1:0");
        assert_eq!(config.temperature, Some(0.9));
        assert_eq!(config.max_tokens, Some(2048));
    }

    #[tokio::test]
    async fn test_bedrock_adapter_capabilities() {
        let config = BedrockConfig::default();
        let adapter = BedrockAdapter::new(config).await;
        if let Ok(adapter) = adapter {
            let caps = adapter.capabilities();
            assert!(caps.contains(&"llm".to_string()));
            assert!(caps.contains(&"bedrock".to_string()));
            assert!(caps.contains(&"aws".to_string()));
        }
    }

    #[tokio::test]
    async fn test_bedrock_adapter_name() {
        let config = BedrockConfig::default();
        let adapter = BedrockAdapter::new(config).await;
        if let Ok(adapter) = adapter {
            assert_eq!(adapter.name(), "bedrock");
        }
    }

    #[test]
    fn test_model_constants() {
        assert_eq!(
            models::CLAUDE_3_5_SONNET,
            "anthropic.claude-3-5-sonnet-20241022-v2:0"
        );
        assert_eq!(
            models::CLAUDE_3_OPUS,
            "anthropic.claude-3-opus-20240229-v1:0"
        );
        assert_eq!(
            models::CLAUDE_3_HAIKU,
            "anthropic.claude-3-haiku-20240307-v1:0"
        );
        assert_eq!(models::LLAMA_3_70B, "meta.llama3-70b-instruct-v1:0");
        assert_eq!(models::MISTRAL_LARGE, "mistral.mistral-large-2402-v1:0");
        assert_eq!(models::TITAN_PREMIER, "amazon.titan-text-premier-v1:0");
    }

    #[test]
    fn test_bedrock_config_with_credentials() {
        let config = BedrockConfig {
            region: "us-east-1".to_string(),
            model: "anthropic.claude-3-5-sonnet-20241022-v2:0".to_string(),
            access_key_id: Some("test-key".to_string()),
            secret_access_key: Some("test-secret".to_string()),
            session_token: None,
            ..Default::default()
        };

        assert!(config.access_key_id.is_some());
        assert!(config.secret_access_key.is_some());
    }

    #[test]
    fn test_bedrock_config_without_credentials() {
        let config = BedrockConfig {
            region: "us-east-1".to_string(),
            model: "anthropic.claude-3-5-sonnet-20241022-v2:0".to_string(),
            access_key_id: None,
            secret_access_key: None,
            session_token: None,
            ..Default::default()
        };

        assert!(config.access_key_id.is_none());
        assert!(config.secret_access_key.is_none());
    }

    #[test]
    fn test_stop_sequences() {
        let config = BedrockConfig {
            stop_sequences: vec!["STOP".to_string(), "END".to_string()],
            ..Default::default()
        };

        assert_eq!(config.stop_sequences.len(), 2);
        assert_eq!(config.stop_sequences[0], "STOP");
        assert_eq!(config.stop_sequences[1], "END");
    }
}
