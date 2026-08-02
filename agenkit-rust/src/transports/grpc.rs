//! gRPC transport for agent communication.
//!
//! Implements the Agent interface for gRPC-based communication,
//! providing efficient binary protocol with built-in streaming support.
//!
//! # Features
//!
//! - Binary protocol with Protocol Buffers
//! - Bidirectional streaming
//! - HTTP/2 multiplexing
//! - TLS support
//! - Automatic reconnection
//! - Load balancing support
//!
//! # Example
//!
//! ```rust,no_run
//! use agenkit::transports::GrpcAgent;
//! use agenkit::core::{Agent, Message};
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // Connect to gRPC server
//! let agent = GrpcAgent::new("grpc://localhost:50051").await?;
//!
//! // Process message
//! let response = agent.process(Message::with_text("user", "Hello!")).await?;
//!
//! println!("Response: {}", response.content_as_str().unwrap_or(""));
//! # Ok(())
//! # }
//! ```
//!
//! # Protocol
//!
//! Uses the agent.proto definition:
//! - `Process(Request) -> Response` - Single request/response
//! - `ProcessStream(Request) -> stream StreamChunk` - Server streaming
//! - `BidirectionalStream(stream Request) -> stream Response` - Bidirectional
//!
//! # TLS Configuration
//!
//! ```rust,no_run
//! use agenkit::transports::{GrpcAgent, GrpcConfig};
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! let config = GrpcConfig {
//!     url: "grpcs://api.example.com:443".to_string(),
//!     use_tls: true,
//!     ca_cert: Some("/path/to/ca.pem".to_string()),
//!     ..Default::default()
//! };
//!
//! let agent = GrpcAgent::with_config(config).await?;
//! # Ok(())
//! # }
//! ```
//!
//! # Implementation Notes
//!
//! This is a stub implementation showing the API design.
//!
//! Full implementation requires:
//! 1. Add build.rs with tonic-build for proto compilation
//! 2. Generate Rust code from proto/agent.proto
//! 3. Implement AgentServiceClient integration
//! 4. Add connection pooling and retry logic
//!
//! Dependencies (already in Cargo.toml):
//! - tonic = "0.11"
//! - prost = "0.12"
//!
//! Build dependencies needed:
//! - tonic-build = "0.11"

use anyhow::Result;
use async_trait::async_trait;
use std::pin::Pin;

use crate::core::{Agent, AgentError, Message};

/// gRPC transport configuration.
#[derive(Debug, Clone)]
pub struct GrpcConfig {
    /// gRPC server URL (grpc:// or grpcs://)
    pub url: String,

    /// Enable TLS (grpcs://)
    pub use_tls: bool,

    /// Path to CA certificate for TLS verification
    pub ca_cert: Option<String>,

    /// Client certificate for mTLS
    pub client_cert: Option<String>,

    /// Client key for mTLS
    pub client_key: Option<String>,

    /// Connection timeout in seconds
    pub connect_timeout: u64,

    /// Request timeout in seconds
    pub request_timeout: u64,

    /// Keep-alive interval in seconds
    pub keepalive_interval: u64,

    /// Maximum message size in bytes
    pub max_message_size: usize,
}

impl Default for GrpcConfig {
    fn default() -> Self {
        Self {
            url: "grpc://localhost:50051".to_string(),
            use_tls: false,
            ca_cert: None,
            client_cert: None,
            client_key: None,
            connect_timeout: 10,
            request_timeout: 30,
            keepalive_interval: 30,
            max_message_size: 4 * 1024 * 1024, // 4MB
        }
    }
}

/// gRPC agent for remote communication.
///
/// Implements the Agent interface using gRPC protocol for
/// efficient binary communication with Protocol Buffers.
pub struct GrpcAgent {
    name: String,
    config: GrpcConfig,
    // In full implementation:
    // client: AgentServiceClient<tonic::transport::Channel>,
}

impl GrpcAgent {
    /// Create a new gRPC agent with default configuration.
    ///
    /// # Arguments
    ///
    /// * `url` - gRPC server URL (grpc:// or grpcs://)
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// # use agenkit::transports::GrpcAgent;
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let agent = GrpcAgent::new("grpc://localhost:50051").await?;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn new(url: &str) -> Result<Self> {
        let mut config = GrpcConfig::default();
        config.url = url.to_string();
        config.use_tls = url.starts_with("grpcs://");
        Self::with_config(config).await
    }

    /// Create a new gRPC agent with custom configuration.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// # use agenkit::transports::{GrpcAgent, GrpcConfig};
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// let config = GrpcConfig {
    ///     url: "grpcs://api.example.com:443".to_string(),
    ///     use_tls: true,
    ///     request_timeout: 60,
    ///     ..Default::default()
    /// };
    ///
    /// let agent = GrpcAgent::with_config(config).await?;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn with_config(config: GrpcConfig) -> Result<Self> {
        // Full implementation would:
        // 1. Parse URL and extract endpoint
        // 2. Configure TLS if grpcs://
        // 3. Create tonic::transport::Channel with config
        // 4. Build AgentServiceClient
        // 5. Test connection with health check
        //
        // Example:
        // let endpoint = tonic::transport::Endpoint::from_shared(config.url.clone())?
        //     .timeout(Duration::from_secs(config.request_timeout))
        //     .connect_timeout(Duration::from_secs(config.connect_timeout))
        //     .keep_alive_timeout(Duration::from_secs(config.keepalive_interval));
        //
        // let endpoint = if config.use_tls {
        //     let tls = tonic::transport::ClientTlsConfig::new();
        //     // Add CA, client cert if provided
        //     endpoint.tls_config(tls)?
        // } else {
        //     endpoint
        // };
        //
        // let channel = endpoint.connect().await?;
        // let client = AgentServiceClient::new(channel);

        Ok(Self {
            name: format!("grpc-agent-{}", config.url),
            config,
        })
    }

    /// Process a streaming request and receive chunks.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// # use agenkit::transports::GrpcAgent;
    /// # use agenkit::core::Message;
    /// # use futures::StreamExt;
    /// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
    /// # let agent = GrpcAgent::new("grpc://localhost:50051").await?;
    /// let messages = vec![Message::with_text("user", "Tell me a story")];
    ///
    /// let mut stream = agent.process_stream(messages).await?;
    ///
    /// while let Some(chunk) = stream.next().await {
    ///     match chunk {
    ///         Ok(msg) => print!("{}", msg.content_as_str().unwrap_or("")),
    ///         Err(e) => eprintln!("Error: {}", e),
    ///     }
    /// }
    /// # Ok(())
    /// # }
    /// ```
    pub async fn process_stream(
        &self,
        _messages: Vec<Message>,
    ) -> Result<Pin<Box<dyn futures::Stream<Item = Result<Message>> + Send>>> {
        // Full implementation would:
        // 1. Convert messages to proto Request
        // 2. Call client.process_stream(request)
        // 3. Return stream that converts StreamChunk to Message

        Err(anyhow::anyhow!(
            "gRPC transport not fully implemented. See implementation notes in source."
        ))
    }
}

#[async_trait]
impl Agent for GrpcAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        // Full implementation would:
        // 1. Convert messages to proto Request
        // 2. Set request ID, timestamp, metadata
        // 3. Call client.process(request).await
        // 4. Convert proto Response to Message
        // 5. Handle errors and retries
        //
        // Example:
        // let request = Request {
        //     version: "1.0".to_string(),
        //     id: uuid::Uuid::new_v4().to_string(),
        //     timestamp: chrono::Utc::now().to_rfc3339(),
        //     method: "process".to_string(),
        //     messages: messages.into_iter().map(|m| proto::Message {
        //         role: m.role,
        //         content: m.content,
        //         ..Default::default()
        //     }).collect(),
        //     ..Default::default()
        // };
        //
        // let response = self.client.process(request).await?;
        // let msg = response.into_inner().message.unwrap();
        //
        // Ok(Message {
        //     role: msg.role,
        //     content: msg.content,
        // })

        Err(AgentError::Internal(
            "gRPC transport not fully implemented. See implementation notes in source.".to_string(),
        ))
    }

    fn capabilities(&self) -> Vec<String> {
        vec![
            "grpc".to_string(),
            "streaming".to_string(),
            "binary_protocol".to_string(),
            "http2".to_string(),
        ]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_grpc_config_default() {
        let config = GrpcConfig::default();
        assert_eq!(config.url, "grpc://localhost:50051");
        assert!(!config.use_tls);
        assert_eq!(config.connect_timeout, 10);
    }

    #[tokio::test]
    async fn test_grpc_config_tls_detection() {
        let agent = GrpcAgent::new("grpcs://api.example.com:443").await;
        assert!(agent.is_ok());

        let agent = agent.unwrap();
        assert!(agent.config.use_tls);
        assert_eq!(agent.config.url, "grpcs://api.example.com:443");
    }

    #[tokio::test]
    async fn test_capabilities() {
        let agent = GrpcAgent::new("grpc://localhost:50051").await.unwrap();
        let caps = agent.capabilities();
        assert!(caps.contains(&"grpc".to_string()));
        assert!(caps.contains(&"streaming".to_string()));
    }
}
