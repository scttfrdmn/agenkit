///! Agenkit - Minimal, composable interfaces for AI agents in Rust.
///!
///! Agenkit provides foundational building blocks for creating AI agent systems
///! with a focus on simplicity, composability, and performance.
///!
///! # Core Concepts
///!
///! ## Message
///! Universal message format for agent communication:
///! ```
///! use agenkit::core::Message;
///! use serde_json::json;
///!
///! let msg = Message::with_text("user", "Hello, agent!");
///! let msg_with_metadata = msg.with_metadata("session_id", json!("abc123"));
///! ```
///!
///! ## Agent
///! Core trait that all agents must implement:
///! ```
///! use agenkit::core::{Agent, Message, AgentError};
///! use async_trait::async_trait;
///!
///! struct EchoAgent;
///!
///! #[async_trait]
///! impl Agent for EchoAgent {
///!     fn name(&self) -> &str {
///!         "echo"
///!     }
///!
///!     async fn process(&self, message: Message) -> Result<Message, AgentError> {
///!         Ok(Message::with_text("assistant", message.content_as_str().unwrap_or("")))
///!     }
///! }
///! ```
///!
///! ## HTTP Transport
///! Expose agents over HTTP or connect to remote agents:
///! ```no_run
///! use agenkit::transports::{HttpServer, HttpAgent, HttpTransportConfig};
///! use agenkit::core::{Agent, Message, AgentError};
///! use async_trait::async_trait;
///!
///! struct MyAgent;
///!
///! #[async_trait]
///! impl Agent for MyAgent {
///!     fn name(&self) -> &str { "my_agent" }
///!     async fn process(&self, message: Message) -> Result<Message, AgentError> {
///!         Ok(Message::with_text("assistant", "Hello!"))
///!     }
///! }
///!
///! #[tokio::main]
///! async fn main() {
///!     // Serve an agent over HTTP
///!     let agent = MyAgent;
///!     let server = HttpServer::new(agent, "127.0.0.1:8080");
///!     tokio::spawn(async move {
///!         server.serve().await.unwrap();
///!     });
///!
///!     // Connect to a remote agent
///!     let config = HttpTransportConfig {
///!         base_url: "http://localhost:8080".to_string(),
///!         timeout_secs: 30,
///!         api_key: None,
///!     };
///!     let client = HttpAgent::new("remote", config);
///! }
///! ```
///!
///! # Features
///!
///! - **Simple**: Minimal interface with only 2 required methods
///! - **Composable**: Easy to wrap and extend agents
///! - **Type-safe**: Full Rust type safety
///! - **Async**: Built on tokio for high-performance async I/O
///! - **Production-ready**: HTTP transport with timeouts, error handling
///!
///! # Architecture
///!
///! Agenkit follows a layered architecture:
///! 1. **Core**: Message types and Agent trait
///! 2. **Adapters**: Local agent implementations
///! 3. **Transports**: HTTP, WebSocket, gRPC
///! 4. **Patterns**: Reflection, Agents-as-Tools, Orchestration
///! 5. **Evaluation**: Benchmarking and testing (future)

pub mod core;
pub mod adapters;
pub mod runtime;

#[cfg(feature = "native")]
pub mod transports;

pub mod patterns;
pub mod evaluation;
pub mod techniques;
pub mod middleware;
pub mod safety;

// Re-export commonly used types
pub use core::{
    create_default_introspection_result, Agent, AgentError, IntrospectionResult, Message, Tool,
    ToolResult,
};

#[cfg(feature = "native")]
pub use transports::{HttpAgent, HttpServer, HttpTransportConfig};

pub use middleware::{
    BatchingConfig, BatchingConfigBuilder, BatchingMiddleware, CachingConfig,
    CachingConfigBuilder, CachingMiddleware, CircuitBreakerConfig, CircuitBreakerConfigBuilder,
    CircuitBreakerMiddleware, CircuitState, RateLimiterConfig, RateLimiterConfigBuilder,
    RateLimiterMiddleware, RetryConfig, RetryConfigBuilder, RetryMiddleware, TimeoutConfig,
    TimeoutConfigBuilder, TimeoutMiddleware,
};

// WASM-specific initialization
#[cfg(feature = "wasm")]
pub mod wasm;

#[cfg(feature = "wasm")]
pub use wasm::*;
