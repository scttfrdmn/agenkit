///! Agent adapters for LLM providers.
///!
///! This module provides adapters for connecting to various LLM providers
///! including OpenAI, Anthropic, Ollama, LiteLLM, Gemini, and Bedrock.

#[cfg(feature = "native")]
pub mod openai;

#[cfg(feature = "native")]
pub mod anthropic;

#[cfg(feature = "native")]
pub mod ollama;

#[cfg(feature = "native")]
pub mod litellm;

#[cfg(feature = "native")]
pub mod gemini;

#[cfg(feature = "native")]
pub mod bedrock;

#[cfg(feature = "native")]
pub use openai::{OpenAIAgent, OpenAIConfig};

#[cfg(feature = "native")]
pub use anthropic::{AnthropicAgent, AnthropicConfig};

#[cfg(feature = "native")]
pub use ollama::{OllamaAgent, OllamaConfig};

#[cfg(feature = "native")]
pub use litellm::{LiteLLMAdapter, LiteLLMConfig};

#[cfg(feature = "native")]
pub use gemini::{GeminiAdapter, GeminiConfig};

#[cfg(feature = "native")]
pub use bedrock::{BedrockAdapter, BedrockConfig};
