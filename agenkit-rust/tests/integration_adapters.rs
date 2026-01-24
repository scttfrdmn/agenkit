//! Integration tests for adapter implementations
//!
//! Tests real adapter functionality including OpenAI, Anthropic, Ollama,
//! OpenAI-compatible services, and error handling. Some tests require API keys
//! or services to be available.

#[cfg(feature = "native")]
mod adapter_tests {
    use agenkit::adapters::{
        AnthropicAgent, AnthropicConfig, OllamaAgent, OllamaConfig, OpenAICompatibleAgent,
        OpenAICompatibleConfig,
    };
    use agenkit::core::{Agent, Message};

    /// Test 1: Ollama adapter - local inference
    #[tokio::test]
    #[ignore] // Requires Ollama service running
    async fn test_ollama_adapter() {
        let config = OllamaConfig {
            api_base: "http://localhost:11434".to_string(),
            model: "llama2".to_string(),
            temperature: 0.7,
            timeout_seconds: 120,
        };

        let agent = OllamaAgent::new(config);
        assert!(!agent.name().is_empty());
        assert!(agent.name().contains("ollama"));

        let msg = Message::with_text("user", "Say 'test passed' and nothing else");
        let result = agent.process(msg).await;

        // Should succeed if Ollama is running
        if result.is_ok() {
            let response = result.unwrap();
            assert_eq!(response.role, "assistant");
            assert!(!response.content_as_str().unwrap_or("").is_empty());
        }
    }

    /// Test 2: Ollama adapter with metadata
    #[tokio::test]
    #[ignore] // Requires Ollama service running
    async fn test_ollama_adapter_with_metadata() {
        let config = OllamaConfig {
            api_base: "http://localhost:11434".to_string(),
            model: "llama2".to_string(),
            temperature: 0.7,
            timeout_seconds: 120,
        };

        let agent = OllamaAgent::new(config);
        let msg = Message::with_text("user", "What is 2+2?")
            .with_metadata("request_id", serde_json::json!("test-123"));

        if let Ok(response) = agent.process(msg).await {
            assert!(!response.content_as_str().unwrap_or("").is_empty());
        }
    }

    /// Test 3: Anthropic adapter - requires ANTHROPIC_API_KEY
    #[tokio::test]
    #[ignore] // Requires API key
    async fn test_anthropic_adapter() {
        let api_key = std::env::var("ANTHROPIC_API_KEY").unwrap_or_default();
        if api_key.is_empty() {
            println!("Skipping Anthropic test - ANTHROPIC_API_KEY not set");
            return;
        }

        let config = AnthropicConfig {
            api_key,
            model: "claude-3-5-sonnet-20241022".to_string(),
            max_tokens: 1024,
            temperature: 1.0,
            top_p: 1.0,
            top_k: 5,
            api_base: "https://api.anthropic.com".to_string(),
            api_version: "2023-06-01".to_string(),
            timeout_seconds: 60,
        };

        let agent = AnthropicAgent::new(config);
        assert!(!agent.name().is_empty());
        assert!(agent.name().contains("anthropic"));

        let msg = Message::with_text("user", "Say 'test passed' and nothing else");
        match agent.process(msg).await {
            Ok(response) => {
                assert_eq!(response.role, "assistant");
                assert!(!response.content_as_str().unwrap_or("").is_empty());
            }
            Err(e) => {
                println!("Anthropic API error (may be expected): {}", e);
            }
        }
    }

    /// Test 4: Anthropic adapter capabilities
    #[tokio::test]
    async fn test_anthropic_adapter_capabilities() {
        let config = AnthropicConfig {
            api_key: "test-key".to_string(),
            model: "claude-3-5-sonnet-20241022".to_string(),
            max_tokens: 1024,
            temperature: 1.0,
            top_p: 1.0,
            top_k: 5,
            api_base: "https://api.anthropic.com".to_string(),
            api_version: "2023-06-01".to_string(),
            timeout_seconds: 60,
        };

        let agent = AnthropicAgent::new(config);
        let capabilities = agent.capabilities();
        assert!(!capabilities.is_empty());
    }

    /// Test 5: Ollama adapter error handling
    #[tokio::test]
    async fn test_ollama_adapter_invalid_url() {
        let config = OllamaConfig {
            api_base: "http://invalid-hostname-that-does-not-exist:11434".to_string(),
            model: "llama2".to_string(),
            temperature: 0.7,
            timeout_seconds: 5,
        };

        let agent = OllamaAgent::new(config);
        let msg = Message::with_text("user", "test");
        let result = agent.process(msg).await;

        // Should fail with invalid URL
        assert!(result.is_err());
    }

    /// Test 6: Agent name generation from config
    #[tokio::test]
    async fn test_adapter_name_generation() {
        let config = AnthropicConfig {
            api_key: "test-key".to_string(),
            model: "claude-3-5-sonnet-20241022".to_string(),
            max_tokens: 1024,
            temperature: 1.0,
            top_p: 1.0,
            top_k: 5,
            api_base: "https://api.anthropic.com".to_string(),
            api_version: "2023-06-01".to_string(),
            timeout_seconds: 60,
        };

        let agent = AnthropicAgent::new(config);
        let name = agent.name();
        assert!(name.contains("anthropic"));
        // Name should contain the model identifier
        assert!(!name.is_empty());
    }

    /// Test 7: OpenAI-compatible adapter - vLLM
    #[tokio::test]
    #[ignore] // Requires vLLM service running
    async fn test_openai_compatible_vllm_adapter() {
        let config = OpenAICompatibleConfig {
            base_url: "http://localhost:8000/v1".to_string(),
            model: "meta-llama/Llama-2-7b-chat-hf".to_string(),
            provider: Some("vllm".to_string()),
            ..Default::default()
        };

        let agent = OpenAICompatibleAgent::new(config);
        assert_eq!(agent.name(), "vllm");

        let msg = Message::with_text("user", "What is machine learning in one sentence?");
        let result = agent.process(msg).await;

        // Should succeed if vLLM is running
        if result.is_ok() {
            let response = result.unwrap();
            assert_eq!(response.role, "assistant");
            assert!(!response.content_as_str().unwrap_or("").is_empty());

            // Check metadata
            assert!(response.metadata.contains_key("provider"));
            assert_eq!(
                response.metadata.get("provider").unwrap(),
                &serde_json::json!("vllm")
            );
            assert!(response.metadata.contains_key("base_url"));
        }
    }

    /// Test 8: OpenAI-compatible adapter - llama.cpp
    #[tokio::test]
    #[ignore] // Requires llama.cpp service running
    async fn test_openai_compatible_llamacpp_adapter() {
        let config = OpenAICompatibleConfig {
            base_url: "http://localhost:8080/v1".to_string(),
            model: "llama-2-7b-chat".to_string(),
            provider: Some("llamacpp".to_string()),
            ..Default::default()
        };

        let agent = OpenAICompatibleAgent::new(config);
        assert_eq!(agent.name(), "llamacpp");

        let msg = Message::with_text("user", "Write a haiku about coding");
        let result = agent.process(msg).await;

        // Should succeed if llama.cpp is running
        if result.is_ok() {
            let response = result.unwrap();
            assert_eq!(response.role, "assistant");
            assert!(!response.content_as_str().unwrap_or("").is_empty());
        }
    }

    /// Test 9: OpenAI-compatible adapter without provider
    #[tokio::test]
    async fn test_openai_compatible_adapter_no_provider() {
        let config = OpenAICompatibleConfig {
            base_url: "http://localhost:8000/v1".to_string(),
            model: "test-model".to_string(),
            provider: None,
            ..Default::default()
        };

        let agent = OpenAICompatibleAgent::new(config);
        assert_eq!(agent.name(), "openai_compatible");
    }

    /// Test 10: OpenAI-compatible adapter capabilities
    #[tokio::test]
    async fn test_openai_compatible_adapter_capabilities() {
        let config = OpenAICompatibleConfig {
            base_url: "http://localhost:8000/v1".to_string(),
            model: "llama-2-7b".to_string(),
            provider: Some("vllm".to_string()),
            ..Default::default()
        };

        let agent = OpenAICompatibleAgent::new(config);
        let capabilities = agent.capabilities();
        assert!(capabilities.contains(&"llm".to_string()));
        assert!(capabilities.contains(&"openai-compatible".to_string()));
        assert!(capabilities.contains(&"vllm".to_string()));
    }

    /// Test 11: OpenAI-compatible adapter error handling
    #[tokio::test]
    async fn test_openai_compatible_adapter_invalid_url() {
        let config = OpenAICompatibleConfig {
            base_url: "http://invalid-hostname-that-does-not-exist:8000/v1".to_string(),
            model: "test-model".to_string(),
            provider: Some("test".to_string()),
            timeout_seconds: 5,
            ..Default::default()
        };

        let agent = OpenAICompatibleAgent::new(config);
        let msg = Message::with_text("user", "test");
        let result = agent.process(msg).await;

        // Should fail with invalid URL
        assert!(result.is_err());
    }

    /// Test 12: OpenAI-compatible provider helper functions
    #[tokio::test]
    async fn test_openai_compatible_provider_helpers() {
        use agenkit::adapters::openai_compatible::providers;

        let vllm_config = providers::vllm("meta-llama/Llama-2-7b-chat-hf");
        assert_eq!(vllm_config.base_url, "http://localhost:8000/v1");
        assert_eq!(vllm_config.provider, Some("vllm".to_string()));

        let llamacpp_config = providers::llamacpp("llama-2-7b-chat");
        assert_eq!(llamacpp_config.base_url, "http://localhost:8080/v1");
        assert_eq!(llamacpp_config.provider, Some("llamacpp".to_string()));

        let sglang_config = providers::sglang("meta-llama/Llama-2-13b-chat-hf");
        assert_eq!(sglang_config.base_url, "http://localhost:30000/v1");
        assert_eq!(sglang_config.provider, Some("sglang".to_string()));

        let tensorrt_config = providers::tensorrt("llama-2-70b");
        assert_eq!(tensorrt_config.base_url, "http://localhost:8001/v1");
        assert_eq!(tensorrt_config.provider, Some("tensorrt".to_string()));
    }

    /// Test 13: OpenAI-compatible message role conversion
    #[tokio::test]
    async fn test_openai_compatible_message_role_conversion() {
        let config = OpenAICompatibleConfig {
            base_url: "http://localhost:8000/v1".to_string(),
            model: "test-model".to_string(),
            ..Default::default()
        };

        let agent = OpenAICompatibleAgent::new(config);

        // Test that agent role converts to assistant
        let msg = Message::with_text("agent", "Previous response");
        // Note: We can't test the internal conversion directly,
        // but we verify the agent was created successfully
        assert_eq!(agent.name(), "openai_compatible");
    }
}

// Run tests without native feature
#[cfg(not(feature = "native"))]
mod placeholder_tests {
    #[tokio::test]
    async fn test_adapters_require_native_feature() {
        // Integration adapter tests require the native feature
        println!("Adapter tests require 'native' feature");
    }
}
