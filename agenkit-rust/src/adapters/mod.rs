///! Agent adapters for LLM providers.
///!
///! This module provides adapters for connecting to various LLM providers
///! including OpenAI, Anthropic, Ollama, LiteLLM, Gemini, Bedrock, and
///! OpenAI-compatible services (vLLM, llama.cpp, SGLang, etc.).

/// Typed token usage normalization. No provider SDK dependency, so it is
/// available regardless of the `native` feature.
pub mod usage;
pub use usage::{usage_from_message, Usage};

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
pub mod openai_compatible;

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

#[cfg(feature = "native")]
pub use openai_compatible::{OpenAICompatibleAgent, OpenAICompatibleConfig};
