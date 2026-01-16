//! Tests for Chain-of-Thought reasoning technique

use agenkit::core::{Agent, AgentError, Message};
use agenkit::techniques::reasoning::{ChainOfThoughtAgent, ChainOfThoughtConfig};
use async_trait::async_trait;
use std::sync::Arc;

/// Mock agent that returns predefined responses
struct MockAgent {
    responses: Vec<String>,
    call_count: std::sync::Mutex<usize>,
}

impl MockAgent {
    fn new(responses: Vec<String>) -> Self {
        Self {
            responses,
            call_count: std::sync::Mutex::new(0),
        }
    }
}

#[async_trait]
impl Agent for MockAgent {
    fn name(&self) -> &str {
        "mock_agent"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["mock".to_string(), "testing".to_string()]
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        let mut count = self.call_count.lock().unwrap();
        let idx = *count % self.responses.len();
        *count += 1;

        Ok(Message::with_text("assistant", self.responses[idx].clone()))
    }
}

#[tokio::test]
async fn test_basic_functionality() {
    let mock = Arc::new(MockAgent::new(vec![
        "1. First, analyze the problem.\n2. Then, calculate.\n3. The answer is 42.".to_string(),
    ]));

    let config = ChainOfThoughtConfig::default();
    let cot = ChainOfThoughtAgent::new(mock, config);

    let message = Message::with_text("user", "What is the answer?");
    let result = cot.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    // Check technique metadata
    assert_eq!(
        response
            .metadata
            .get("technique")
            .unwrap()
            .as_str()
            .unwrap(),
        "chain_of_thought"
    );

    // Check reasoning steps were parsed
    let steps = response.metadata.get("reasoning_steps").unwrap();
    assert!(steps.is_array());
    let steps_vec = steps.as_array().unwrap();
    assert_eq!(steps_vec.len(), 3);

    // Check num_steps
    let num_steps = response.metadata.get("num_steps").unwrap();
    assert_eq!(num_steps.as_u64().unwrap(), 3);
}

#[tokio::test]
async fn test_name_and_capabilities() {
    let mock = Arc::new(MockAgent::new(vec!["test".to_string()]));
    let cot = ChainOfThoughtAgent::new(mock, ChainOfThoughtConfig::default());

    assert_eq!(cot.name(), "chain_of_thought");

    let caps = cot.capabilities();
    assert_eq!(caps.len(), 4);
    assert!(caps.contains(&"reasoning".to_string()));
    assert!(caps.contains(&"step_by_step".to_string()));
    assert!(caps.contains(&"chain_of_thought".to_string()));
    assert!(caps.contains(&"explainable_ai".to_string()));
}

#[tokio::test]
async fn test_numbered_steps_parsing() {
    let mock = Arc::new(MockAgent::new(vec![
        "1. Identify the problem.\n2. Gather information.\n3. Analyze options.\n4. Make a decision.".to_string(),
    ]));

    let cot = ChainOfThoughtAgent::new(mock, ChainOfThoughtConfig::default());
    let result = cot
        .process(Message::with_text("user", "Test"))
        .await
        .unwrap();

    let steps = result
        .metadata
        .get("reasoning_steps")
        .unwrap()
        .as_array()
        .unwrap();
    assert_eq!(steps.len(), 4);
    assert_eq!(steps[0].as_str().unwrap(), "Identify the problem.");
    assert_eq!(steps[1].as_str().unwrap(), "Gather information.");
    assert_eq!(steps[2].as_str().unwrap(), "Analyze options.");
    assert_eq!(steps[3].as_str().unwrap(), "Make a decision.");
}

#[tokio::test]
async fn test_numbered_steps_with_parentheses() {
    let mock = Arc::new(MockAgent::new(vec![
        "1) First step here.\n2) Second step follows.\n3) Third and final step.".to_string(),
    ]));

    let cot = ChainOfThoughtAgent::new(mock, ChainOfThoughtConfig::default());
    let result = cot
        .process(Message::with_text("user", "Test"))
        .await
        .unwrap();

    let steps = result
        .metadata
        .get("reasoning_steps")
        .unwrap()
        .as_array()
        .unwrap();
    assert_eq!(steps.len(), 3);
    assert_eq!(steps[0].as_str().unwrap(), "First step here.");
    assert_eq!(steps[1].as_str().unwrap(), "Second step follows.");
    assert_eq!(steps[2].as_str().unwrap(), "Third and final step.");
}

#[tokio::test]
async fn test_bullet_points_parsing() {
    let mock = Arc::new(MockAgent::new(vec![
        "- Consider the context\n- Evaluate alternatives\n- Choose best option".to_string(),
    ]));

    let cot = ChainOfThoughtAgent::new(mock, ChainOfThoughtConfig::default());
    let result = cot
        .process(Message::with_text("user", "Test"))
        .await
        .unwrap();

    let steps = result
        .metadata
        .get("reasoning_steps")
        .unwrap()
        .as_array()
        .unwrap();
    assert_eq!(steps.len(), 3);
    assert_eq!(steps[0].as_str().unwrap(), "Consider the context");
    assert_eq!(steps[1].as_str().unwrap(), "Evaluate alternatives");
}

#[tokio::test]
async fn test_custom_prompt_template() {
    let mock = Arc::new(MockAgent::new(vec!["Step by step answer".to_string()]));

    let config = ChainOfThoughtConfig {
        prompt_template: "Solve carefully:\n{query}".to_string(),
        ..Default::default()
    };

    let cot = ChainOfThoughtAgent::new(mock, config);
    let result = cot.process(Message::with_text("user", "Problem X")).await;

    assert!(result.is_ok());
}

#[tokio::test]
async fn test_parse_steps_disabled() {
    let mock = Arc::new(MockAgent::new(vec![
        "1. Step one.\n2. Step two.".to_string()
    ]));

    let config = ChainOfThoughtConfig {
        parse_steps: false,
        ..Default::default()
    };

    let cot = ChainOfThoughtAgent::new(mock, config);
    let result = cot
        .process(Message::with_text("user", "Test"))
        .await
        .unwrap();

    // Should have technique but not reasoning_steps
    assert!(result.metadata.contains_key("technique"));
    assert!(!result.metadata.contains_key("reasoning_steps"));
    assert!(!result.metadata.contains_key("num_steps"));
}

#[tokio::test]
async fn test_max_steps_limiting() {
    let mock = Arc::new(MockAgent::new(vec![
        "1. First.\n2. Second.\n3. Third.\n4. Fourth.\n5. Fifth.".to_string(),
    ]));

    let config = ChainOfThoughtConfig {
        max_steps: Some(3),
        ..Default::default()
    };

    let cot = ChainOfThoughtAgent::new(mock, config);
    let result = cot
        .process(Message::with_text("user", "Test"))
        .await
        .unwrap();

    let steps = result
        .metadata
        .get("reasoning_steps")
        .unwrap()
        .as_array()
        .unwrap();
    assert_eq!(steps.len(), 3);
    assert_eq!(
        result.metadata.get("num_steps").unwrap().as_u64().unwrap(),
        3
    );
}

#[tokio::test]
async fn test_delimiter_based_parsing() {
    let mock = Arc::new(MockAgent::new(vec![
        "First thought\nSecond thought\nThird thought".to_string(),
    ]));

    let cot = ChainOfThoughtAgent::new(mock, ChainOfThoughtConfig::default());
    let result = cot
        .process(Message::with_text("user", "Test"))
        .await
        .unwrap();

    let steps = result
        .metadata
        .get("reasoning_steps")
        .unwrap()
        .as_array()
        .unwrap();
    assert!(steps.len() >= 3);
}

#[tokio::test]
async fn test_custom_delimiter() {
    let mock = Arc::new(MockAgent::new(vec!["Step A | Step B | Step C".to_string()]));

    let config = ChainOfThoughtConfig {
        step_delimiter: " | ".to_string(),
        ..Default::default()
    };

    let cot = ChainOfThoughtAgent::new(mock, config);
    let result = cot
        .process(Message::with_text("user", "Test"))
        .await
        .unwrap();

    let steps = result
        .metadata
        .get("reasoning_steps")
        .unwrap()
        .as_array()
        .unwrap();
    assert_eq!(steps.len(), 3);
    assert_eq!(steps[0].as_str().unwrap(), "Step A");
    assert_eq!(steps[1].as_str().unwrap(), "Step B");
    assert_eq!(steps[2].as_str().unwrap(), "Step C");
}

#[tokio::test]
async fn test_invalid_template() {
    let mock = Arc::new(MockAgent::new(vec!["response".to_string()]));

    let config = ChainOfThoughtConfig {
        prompt_template: "No placeholder here".to_string(),
        ..Default::default()
    };

    let cot = ChainOfThoughtAgent::new(mock, config);
    let result = cot.process(Message::with_text("user", "Test")).await;

    assert!(result.is_err());
    match result.unwrap_err() {
        AgentError::InvalidInput(msg) => {
            assert!(msg.contains("placeholder"));
        }
        _ => panic!("Expected InvalidInput error"),
    }
}

#[tokio::test]
async fn test_empty_response() {
    let mock = Arc::new(MockAgent::new(vec!["".to_string()]));

    let cot = ChainOfThoughtAgent::new(mock, ChainOfThoughtConfig::default());
    let result = cot.process(Message::with_text("user", "Test")).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    let steps = response
        .metadata
        .get("reasoning_steps")
        .unwrap()
        .as_array()
        .unwrap();
    assert_eq!(steps.len(), 0);
}
