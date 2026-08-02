use agenkit::adapters::anthropic::{AnthropicAgent, AnthropicConfig};
use agenkit::adapters::gemini::{GeminiAdapter, GeminiConfig};
///! Tests for LLM parameter validation across all adapters
use agenkit::adapters::openai::{OpenAIAgent, OpenAIConfig};
use agenkit::adapters::openai_compatible::{OpenAICompatibleAgent, OpenAICompatibleConfig};

#[cfg(test)]
mod openai_validation {
    use super::*;

    #[test]
    fn test_valid_temperature() {
        let config = OpenAIConfig {
            api_key: "test-key".to_string(),
            model: "gpt-4".to_string(),
            temperature: 0.0,
            ..Default::default()
        };
        assert!(std::panic::catch_unwind(|| OpenAIAgent::new(config)).is_ok());

        let config = OpenAIConfig {
            api_key: "test-key".to_string(),
            model: "gpt-4".to_string(),
            temperature: 1.0,
            ..Default::default()
        };
        assert!(std::panic::catch_unwind(|| OpenAIAgent::new(config)).is_ok());

        let config = OpenAIConfig {
            api_key: "test-key".to_string(),
            model: "gpt-4".to_string(),
            temperature: 2.0,
            ..Default::default()
        };
        assert!(std::panic::catch_unwind(|| OpenAIAgent::new(config)).is_ok());
    }

    #[test]
    #[should_panic(expected = "temperature must be between 0 and 2")]
    fn test_invalid_temperature_too_low() {
        let config = OpenAIConfig {
            api_key: "test-key".to_string(),
            model: "gpt-4".to_string(),
            temperature: -0.1,
            ..Default::default()
        };
        OpenAIAgent::new(config);
    }

    #[test]
    #[should_panic(expected = "temperature must be between 0 and 2")]
    fn test_invalid_temperature_too_high() {
        let config = OpenAIConfig {
            api_key: "test-key".to_string(),
            model: "gpt-4".to_string(),
            temperature: 2.1,
            ..Default::default()
        };
        OpenAIAgent::new(config);
    }

    #[test]
    #[should_panic(expected = "max_tokens must be positive")]
    fn test_invalid_max_tokens_zero() {
        let config = OpenAIConfig {
            api_key: "test-key".to_string(),
            model: "gpt-4".to_string(),
            max_tokens: 0,
            ..Default::default()
        };
        OpenAIAgent::new(config);
    }

    #[test]
    #[should_panic(expected = "max_tokens must be positive")]
    fn test_invalid_max_tokens_negative() {
        let config = OpenAIConfig {
            api_key: "test-key".to_string(),
            model: "gpt-4".to_string(),
            max_tokens: -100,
            ..Default::default()
        };
        OpenAIAgent::new(config);
    }

    #[test]
    #[should_panic(expected = "top_p must be between 0 and 1")]
    fn test_invalid_top_p_too_low() {
        let config = OpenAIConfig {
            api_key: "test-key".to_string(),
            model: "gpt-4".to_string(),
            top_p: -0.1,
            ..Default::default()
        };
        OpenAIAgent::new(config);
    }

    #[test]
    #[should_panic(expected = "top_p must be between 0 and 1")]
    fn test_invalid_top_p_too_high() {
        let config = OpenAIConfig {
            api_key: "test-key".to_string(),
            model: "gpt-4".to_string(),
            top_p: 1.1,
            ..Default::default()
        };
        OpenAIAgent::new(config);
    }

    #[test]
    #[should_panic(expected = "frequency_penalty must be between -2 and 2")]
    fn test_invalid_frequency_penalty_too_low() {
        let config = OpenAIConfig {
            api_key: "test-key".to_string(),
            model: "gpt-4".to_string(),
            frequency_penalty: -2.1,
            ..Default::default()
        };
        OpenAIAgent::new(config);
    }

    #[test]
    #[should_panic(expected = "frequency_penalty must be between -2 and 2")]
    fn test_invalid_frequency_penalty_too_high() {
        let config = OpenAIConfig {
            api_key: "test-key".to_string(),
            model: "gpt-4".to_string(),
            frequency_penalty: 2.5,
            ..Default::default()
        };
        OpenAIAgent::new(config);
    }

    #[test]
    #[should_panic(expected = "presence_penalty must be between -2 and 2")]
    fn test_invalid_presence_penalty_too_low() {
        let config = OpenAIConfig {
            api_key: "test-key".to_string(),
            model: "gpt-4".to_string(),
            presence_penalty: -2.1,
            ..Default::default()
        };
        OpenAIAgent::new(config);
    }

    #[test]
    #[should_panic(expected = "presence_penalty must be between -2 and 2")]
    fn test_invalid_presence_penalty_too_high() {
        let config = OpenAIConfig {
            api_key: "test-key".to_string(),
            model: "gpt-4".to_string(),
            presence_penalty: 2.5,
            ..Default::default()
        };
        OpenAIAgent::new(config);
    }
}

#[cfg(test)]
mod gemini_validation {
    use super::*;

    #[test]
    fn test_valid_temperature() {
        let config = GeminiConfig {
            api_key: "test-key".to_string(),
            temperature: Some(0.0),
            ..Default::default()
        };
        assert!(GeminiAdapter::new(config).is_ok());

        let config = GeminiConfig {
            api_key: "test-key".to_string(),
            temperature: Some(2.0),
            ..Default::default()
        };
        assert!(GeminiAdapter::new(config).is_ok());
    }

    #[test]
    fn test_invalid_temperature() {
        let config = GeminiConfig {
            api_key: "test-key".to_string(),
            temperature: Some(-0.1),
            ..Default::default()
        };
        assert!(GeminiAdapter::new(config).is_err());

        let config = GeminiConfig {
            api_key: "test-key".to_string(),
            temperature: Some(2.1),
            ..Default::default()
        };
        assert!(GeminiAdapter::new(config).is_err());
    }

    #[test]
    fn test_invalid_max_tokens() {
        let config = GeminiConfig {
            api_key: "test-key".to_string(),
            max_tokens: Some(0),
            ..Default::default()
        };
        assert!(GeminiAdapter::new(config).is_err());
    }

    #[test]
    fn test_invalid_top_p() {
        let config = GeminiConfig {
            api_key: "test-key".to_string(),
            top_p: Some(-0.1),
            ..Default::default()
        };
        assert!(GeminiAdapter::new(config).is_err());

        let config = GeminiConfig {
            api_key: "test-key".to_string(),
            top_p: Some(1.1),
            ..Default::default()
        };
        assert!(GeminiAdapter::new(config).is_err());
    }
}

#[cfg(test)]
mod openai_compatible_validation {
    use super::*;

    #[test]
    #[should_panic(expected = "temperature must be between 0 and 2")]
    fn test_invalid_temperature() {
        let config = OpenAICompatibleConfig {
            base_url: "http://localhost:8000/v1".to_string(),
            model: "test-model".to_string(),
            temperature: 3.0,
            ..Default::default()
        };
        OpenAICompatibleAgent::new(config);
    }

    #[test]
    #[should_panic(expected = "max_tokens must be positive")]
    fn test_invalid_max_tokens() {
        let config = OpenAICompatibleConfig {
            base_url: "http://localhost:8000/v1".to_string(),
            model: "test-model".to_string(),
            max_tokens: 0,
            ..Default::default()
        };
        OpenAICompatibleAgent::new(config);
    }

    #[test]
    #[should_panic(expected = "top_p must be between 0 and 1")]
    fn test_invalid_top_p() {
        let config = OpenAICompatibleConfig {
            base_url: "http://localhost:8000/v1".to_string(),
            model: "test-model".to_string(),
            top_p: 1.5,
            ..Default::default()
        };
        OpenAICompatibleAgent::new(config);
    }
}

#[cfg(test)]
mod anthropic_validation {
    use super::*;

    #[test]
    fn test_valid_temperature() {
        let config = AnthropicConfig {
            api_key: "test-key".to_string(),
            temperature: 0.0,
            ..Default::default()
        };
        assert!(std::panic::catch_unwind(|| AnthropicAgent::new(config)).is_ok());

        let config = AnthropicConfig {
            api_key: "test-key".to_string(),
            temperature: 2.0,
            ..Default::default()
        };
        assert!(std::panic::catch_unwind(|| AnthropicAgent::new(config)).is_ok());
    }

    #[test]
    #[should_panic(expected = "temperature must be between 0 and 2")]
    fn test_invalid_temperature() {
        let config = AnthropicConfig {
            api_key: "test-key".to_string(),
            temperature: 2.5,
            ..Default::default()
        };
        AnthropicAgent::new(config);
    }

    #[test]
    #[should_panic(expected = "max_tokens must be positive")]
    fn test_invalid_max_tokens() {
        let config = AnthropicConfig {
            api_key: "test-key".to_string(),
            max_tokens: 0,
            ..Default::default()
        };
        AnthropicAgent::new(config);
    }

    #[test]
    #[should_panic(expected = "top_p must be between 0 and 1")]
    fn test_invalid_top_p() {
        let config = AnthropicConfig {
            api_key: "test-key".to_string(),
            top_p: 1.1,
            ..Default::default()
        };
        AnthropicAgent::new(config);
    }
}
