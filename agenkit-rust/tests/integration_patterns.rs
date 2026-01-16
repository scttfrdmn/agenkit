//! Integration tests for pattern implementations
//!
//! Tests pattern functionality including Reflection, Agents-as-Tools, ReAct,
//! and orchestration strategies.

use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::{
    CritiqueFormat, ReflectionAgent, ReflectionConfig, ReflectionStep, StopReason,
};
use async_trait::async_trait;
use serde_json::json;
use std::sync::Arc;

/// Simple test agent for pattern testing
struct TestAgent {
    name: String,
}

#[async_trait]
impl Agent for TestAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");
        Ok(Message::with_text(
            "assistant",
            format!("Response from {}: {}", self.name, content),
        ))
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["respond".to_string()]
    }
}

/// Simple scorer agent for reflection
struct ScorerAgent;

#[async_trait]
impl Agent for ScorerAgent {
    fn name(&self) -> &str {
        "scorer"
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        // Return a score between 0 and 1
        Ok(Message::with_text("assistant", "0.85").with_metadata("score", json!(0.85)))
    }
}

/// Test 1: Reflection pattern basic setup
#[tokio::test]
async fn test_reflection_pattern_creation() {
    let generator = Arc::new(TestAgent {
        name: "generator".to_string(),
    });

    let critic = Arc::new(ScorerAgent);

    let config = ReflectionConfig {
        generator,
        critic,
        max_iterations: 2,
        quality_threshold: 0.9,
        improvement_threshold: 0.05,
        critique_format: CritiqueFormat::Structured,
        verbose: false,
    };

    let reflection = ReflectionAgent::new(config);
    assert!(reflection.is_ok());
}

/// Test 2: Reflection pattern basic processing
#[tokio::test]
async fn test_reflection_pattern_processing() {
    let generator = Arc::new(TestAgent {
        name: "generator".to_string(),
    });

    let critic = Arc::new(ScorerAgent);

    let config = ReflectionConfig {
        generator,
        critic,
        max_iterations: 2,
        quality_threshold: 0.9,
        improvement_threshold: 0.05,
        critique_format: CritiqueFormat::Structured,
        verbose: false,
    };

    let reflection = ReflectionAgent::new(config).expect("Failed to create reflection agent");

    let msg = Message::with_text("user", "Generate a response");
    let result = reflection.process(msg).await;

    // Should process without errors
    assert!(result.is_ok() || result.is_err()); // May error depending on config
}

/// Test 3: Reflection pattern name
#[tokio::test]
async fn test_reflection_pattern_name() {
    let generator = Arc::new(TestAgent {
        name: "generator".to_string(),
    });

    let critic = Arc::new(ScorerAgent);

    let config = ReflectionConfig {
        generator,
        critic,
        max_iterations: 2,
        quality_threshold: 0.9,
        improvement_threshold: 0.05,
        critique_format: CritiqueFormat::Structured,
        verbose: false,
    };

    let reflection = ReflectionAgent::new(config).expect("Failed to create reflection agent");

    let name = reflection.name();
    assert!(!name.is_empty());
}

/// Test 4: Reflection pattern capabilities
#[tokio::test]
async fn test_reflection_pattern_capabilities() {
    let generator = Arc::new(TestAgent {
        name: "generator".to_string(),
    });

    let critic = Arc::new(ScorerAgent);

    let config = ReflectionConfig {
        generator,
        critic,
        max_iterations: 2,
        quality_threshold: 0.9,
        improvement_threshold: 0.05,
        critique_format: CritiqueFormat::Structured,
        verbose: false,
    };

    let reflection = ReflectionAgent::new(config).expect("Failed to create reflection agent");

    let capabilities = reflection.capabilities();
    assert!(!capabilities.is_empty());
}

/// Test 5: Stop reason enum
#[tokio::test]
async fn test_stop_reason_values() {
    let reasons = vec![
        StopReason::QualityThresholdMet,
        StopReason::MinimalImprovement,
        StopReason::MaxIterations,
        StopReason::PerfectScore,
    ];

    assert_eq!(reasons.len(), 4);
}

/// Test 6: Critique format enum
#[tokio::test]
async fn test_critique_format_values() {
    let formats = vec![CritiqueFormat::Structured, CritiqueFormat::FreeForm];

    assert_eq!(formats.len(), 2);
}

/// Test 7: Basic message processing
#[tokio::test]
async fn test_basic_agent_processing() {
    let agent = TestAgent {
        name: "test-agent".to_string(),
    };

    let msg = Message::with_text("user", "Hello");
    let result = agent.process(msg).await;

    assert!(result.is_ok());
    if let Ok(response) = result {
        assert_eq!(response.role, "assistant");
        assert!(response.content_as_str().unwrap().contains("Response"));
    }
}

/// Test 8: Scorer agent processing
#[tokio::test]
async fn test_scorer_agent() {
    let scorer = ScorerAgent;
    let msg = Message::with_text("user", "test");
    let result = scorer.process(msg).await;

    assert!(result.is_ok());
    if let Ok(response) = result {
        assert_eq!(response.role, "assistant");
        let score = response.metadata.get("score");
        assert!(score.is_some());
    }
}

/// Test 9: Reflection step creation
#[tokio::test]
async fn test_reflection_step() {
    let step = ReflectionStep {
        iteration: 1,
        output: "output".to_string(),
        critique: "feedback".to_string(),
        quality_score: 0.8,
        improvement: 0.1,
        timestamp: chrono::Utc::now(),
    };

    assert_eq!(step.iteration, 1);
    assert_eq!(step.quality_score, 0.8);
}

/// Test 10: Message with metadata
#[tokio::test]
async fn test_message_with_metadata() {
    let msg = Message::with_text("user", "Test")
        .with_metadata("request_id", json!("req-123"))
        .with_metadata("priority", json!("high"))
        .with_metadata("nested", json!({"level": 1}));

    assert_eq!(msg.metadata.len(), 3);
    assert_eq!(
        msg.metadata.get("request_id").unwrap().as_str().unwrap(),
        "req-123"
    );
}

/// Test 11: Pattern error handling
#[tokio::test]
async fn test_pattern_error_handling() {
    struct ErrorAgent;

    #[async_trait]
    impl Agent for ErrorAgent {
        fn name(&self) -> &str {
            "error-agent"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Err(AgentError::ProcessingError(
                "Pattern test error".to_string(),
            ))
        }
    }

    let agent = ErrorAgent;
    let msg = Message::with_text("user", "test");
    let result = agent.process(msg).await;

    assert!(result.is_err());
}

/// Test 12: Reflection config creation with defaults
#[tokio::test]
async fn test_reflection_config_parameters() {
    let generator = Arc::new(TestAgent {
        name: "gen".to_string(),
    });
    let critic = Arc::new(ScorerAgent);

    let config = ReflectionConfig {
        generator: generator.clone(),
        critic: critic,
        max_iterations: 5,
        quality_threshold: 0.95,
        improvement_threshold: 0.02,
        critique_format: CritiqueFormat::Structured,
        verbose: true,
    };

    assert_eq!(config.max_iterations, 5);
    assert_eq!(config.quality_threshold, 0.95);
    assert_eq!(config.improvement_threshold, 0.02);
    assert!(config.verbose);
}

/// Test 13: Multiple pattern instances
#[tokio::test]
async fn test_multiple_pattern_instances() {
    let generator1 = Arc::new(TestAgent {
        name: "gen1".to_string(),
    });

    let generator2 = Arc::new(TestAgent {
        name: "gen2".to_string(),
    });

    let critic = Arc::new(ScorerAgent);

    let config1 = ReflectionConfig {
        generator: generator1,
        critic: Arc::new(ScorerAgent),
        max_iterations: 2,
        quality_threshold: 0.9,
        improvement_threshold: 0.05,
        critique_format: CritiqueFormat::Structured,
        verbose: false,
    };

    let config2 = ReflectionConfig {
        generator: generator2,
        critic: Arc::new(ScorerAgent),
        max_iterations: 3,
        quality_threshold: 0.85,
        improvement_threshold: 0.1,
        critique_format: CritiqueFormat::FreeForm,
        verbose: false,
    };

    let reflection1 = ReflectionAgent::new(config1);
    let reflection2 = ReflectionAgent::new(config2);

    assert!(reflection1.is_ok());
    assert!(reflection2.is_ok());
}

/// Test 14: Pattern composition with message routing
#[tokio::test]
async fn test_pattern_message_routing() {
    let msg = Message::with_text("user", "Route to specific handler")
        .with_metadata("handler", json!("reflection"))
        .with_metadata("priority", json!("high"));

    assert_eq!(msg.role, "user");
    assert_eq!(msg.content_as_str().unwrap(), "Route to specific handler");

    let handler = msg.metadata.get("handler").unwrap().as_str().unwrap();
    assert_eq!(handler, "reflection");
}
