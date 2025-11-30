///! Agent adapters for LLM providers.
///!
///! This module provides adapters for connecting to various LLM providers
///! including OpenAI, Anthropic, and Ollama.

#[cfg(feature = "native")]
pub mod openai;

#[cfg(feature = "native")]
pub mod anthropic;

#[cfg(feature = "native")]
pub mod ollama;

#[cfg(feature = "native")]
pub use openai::{OpenAIAgent, OpenAIConfig};

#[cfg(feature = "native")]
pub use anthropic::{AnthropicAgent, AnthropicConfig};

#[cfg(feature = "native")]
pub use ollama::{OllamaAgent, OllamaConfig};
