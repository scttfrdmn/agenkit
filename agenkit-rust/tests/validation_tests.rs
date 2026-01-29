//! Tests for LLM parameter validation across adapters.
//!
//! Ensures that temperature, max_tokens, and other parameters are validated
//! at construction time to provide clear panics before API calls.

use agenkit::adapters::anthropic::{AnthropicAgent, AnthropicConfig};
use agenkit::adapters::openai::{OpenAIAgent, OpenAIConfig};

#[test]
fn test_openai_valid_temperature_0() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        temperature: 0.0,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

#[test]
fn test_openai_valid_temperature_1() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        temperature: 1.0,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

#[test]
fn test_openai_valid_temperature_2() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        temperature: 2.0,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

#[test]
#[should_panic(expected = "temperature must be between 0 and 2")]
fn test_openai_invalid_temperature_negative() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        temperature: -0.5,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

#[test]
#[should_panic(expected = "temperature must be between 0 and 2")]
fn test_openai_invalid_temperature_too_high() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        temperature: 3.0,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

#[test]
fn test_openai_valid_max_tokens() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        max_tokens: 1024,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

#[test]
#[should_panic(expected = "max_tokens must be positive")]
fn test_openai_invalid_max_tokens_zero() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        max_tokens: 0,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

#[test]
#[should_panic(expected = "max_tokens must be positive")]
fn test_openai_invalid_max_tokens_negative() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        max_tokens: -10,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

#[test]
fn test_openai_valid_top_p() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        top_p: 0.9,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

#[test]
#[should_panic(expected = "top_p must be between 0 and 1")]
fn test_openai_invalid_top_p_negative() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        top_p: -0.1,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

#[test]
#[should_panic(expected = "top_p must be between 0 and 1")]
fn test_openai_invalid_top_p_too_high() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        top_p: 1.5,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

#[test]
#[should_panic(expected = "frequency_penalty must be between -2 and 2")]
fn test_openai_invalid_frequency_penalty_too_low() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        frequency_penalty: -3.0,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

#[test]
#[should_panic(expected = "frequency_penalty must be between -2 and 2")]
fn test_openai_invalid_frequency_penalty_too_high() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        frequency_penalty: 3.0,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

#[test]
#[should_panic(expected = "presence_penalty must be between -2 and 2")]
fn test_openai_invalid_presence_penalty_too_low() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        presence_penalty: -2.5,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

#[test]
#[should_panic(expected = "presence_penalty must be between -2 and 2")]
fn test_openai_invalid_presence_penalty_too_high() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        presence_penalty: 2.5,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

// Anthropic tests

#[test]
fn test_anthropic_valid_temperature_0() {
    let config = AnthropicConfig {
        api_key: "sk-ant-test".to_string(),
        temperature: 0.0,
        ..Default::default()
    };
    let _agent = AnthropicAgent::new(config);
}

#[test]
fn test_anthropic_valid_temperature_1() {
    let config = AnthropicConfig {
        api_key: "sk-ant-test".to_string(),
        temperature: 1.0,
        ..Default::default()
    };
    let _agent = AnthropicAgent::new(config);
}

#[test]
fn test_anthropic_valid_temperature_2() {
    let config = AnthropicConfig {
        api_key: "sk-ant-test".to_string(),
        temperature: 2.0,
        ..Default::default()
    };
    let _agent = AnthropicAgent::new(config);
}

#[test]
#[should_panic(expected = "temperature must be between 0 and 2")]
fn test_anthropic_invalid_temperature_negative() {
    let config = AnthropicConfig {
        api_key: "sk-ant-test".to_string(),
        temperature: -0.5,
        ..Default::default()
    };
    let _agent = AnthropicAgent::new(config);
}

#[test]
#[should_panic(expected = "temperature must be between 0 and 2")]
fn test_anthropic_invalid_temperature_too_high() {
    let config = AnthropicConfig {
        api_key: "sk-ant-test".to_string(),
        temperature: 3.0,
        ..Default::default()
    };
    let _agent = AnthropicAgent::new(config);
}

#[test]
fn test_anthropic_valid_max_tokens() {
    let config = AnthropicConfig {
        api_key: "sk-ant-test".to_string(),
        max_tokens: 4096,
        ..Default::default()
    };
    let _agent = AnthropicAgent::new(config);
}

#[test]
#[should_panic(expected = "max_tokens must be positive")]
fn test_anthropic_invalid_max_tokens_zero() {
    let config = AnthropicConfig {
        api_key: "sk-ant-test".to_string(),
        max_tokens: 0,
        ..Default::default()
    };
    let _agent = AnthropicAgent::new(config);
}

#[test]
#[should_panic(expected = "max_tokens must be positive")]
fn test_anthropic_invalid_max_tokens_negative() {
    let config = AnthropicConfig {
        api_key: "sk-ant-test".to_string(),
        max_tokens: -10,
        ..Default::default()
    };
    let _agent = AnthropicAgent::new(config);
}

#[test]
fn test_anthropic_valid_top_p() {
    let config = AnthropicConfig {
        api_key: "sk-ant-test".to_string(),
        top_p: 0.9,
        ..Default::default()
    };
    let _agent = AnthropicAgent::new(config);
}

#[test]
#[should_panic(expected = "top_p must be between 0 and 1")]
fn test_anthropic_invalid_top_p_negative() {
    let config = AnthropicConfig {
        api_key: "sk-ant-test".to_string(),
        top_p: -0.1,
        ..Default::default()
    };
    let _agent = AnthropicAgent::new(config);
}

#[test]
#[should_panic(expected = "top_p must be between 0 and 1")]
fn test_anthropic_invalid_top_p_too_high() {
    let config = AnthropicConfig {
        api_key: "sk-ant-test".to_string(),
        top_p: 1.5,
        ..Default::default()
    };
    let _agent = AnthropicAgent::new(config);
}

#[test]
#[should_panic(expected = "top_k must be positive")]
fn test_anthropic_invalid_top_k() {
    let config = AnthropicConfig {
        api_key: "sk-ant-test".to_string(),
        top_k: 0,
        ..Default::default()
    };
    let _agent = AnthropicAgent::new(config);
}

// Boundary value tests

#[test]
fn test_boundary_temperature_exactly_0() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        temperature: 0.0,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

#[test]
fn test_boundary_temperature_exactly_2() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        temperature: 2.0,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

#[test]
fn test_boundary_max_tokens_exactly_1() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        max_tokens: 1,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

#[test]
fn test_boundary_top_p_exactly_0() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        top_p: 0.0,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}

#[test]
fn test_boundary_top_p_exactly_1() {
    let config = OpenAIConfig {
        api_key: "sk-test".to_string(),
        top_p: 1.0,
        ..Default::default()
    };
    let _agent = OpenAIAgent::new(config);
}
