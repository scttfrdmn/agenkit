///! Core types and traits for agenkit.
///!
///! This module provides the foundational interfaces for building AI agents:
///! - `Message`: Universal message format for agent communication
///! - `Agent`: Core trait that all agents must implement
///! - `Tool`: Interface for deterministic operations
///!
///! # Example
///! ```
///! use agenkit::core::{Agent, Message};
///! use async_trait::async_trait;
///!
///! struct MyAgent;
///!
///! #[async_trait]
///! impl Agent for MyAgent {
///!     fn name(&self) -> &str {
///!         "my_agent"
///!     }
///!
///!     async fn process(&self, message: Message) -> Result<Message, agenkit::core::AgentError> {
///!         Ok(Message::with_text("assistant", "Hello!"))
///!     }
///! }
///! ```

mod agent;
mod message;

pub use agent::{Agent, AgentError, Debuggable, Tool};
pub use message::{Message, MessageError, ToolResult};
