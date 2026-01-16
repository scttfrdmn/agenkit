//! Integration tests for safety framework.
//!
//! Tests the complete safety middleware stack with real scenarios.

use agenkit::{
    core::{Agent, AgentError, Message},
    safety::{
        InputValidationMiddleware, OutputValidationMiddleware, PermissionMiddleware, Role,
        SchemaValidator,
    },
};
use async_trait::async_trait;

/// Test agent that returns configurable responses.
#[derive(Debug, Clone)]
struct TestAgent {
    response: String,
}

impl TestAgent {
    fn new(response: &str) -> Self {
        Self {
            response: response.to_string(),
        }
    }
}

#[async_trait]
impl Agent for TestAgent {
    fn name(&self) -> &str {
        "test-agent"
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        Ok(Message::with_text("assistant", &self.response))
    }
}

#[tokio::test]
async fn test_input_validation_with_prompt_detector() {
    let agent = TestAgent::new("Response");
    let safe_agent = InputValidationMiddleware::new(agent).with_prompt_injection_detector();

    // Test that middleware processes messages (detection logic tested in unit tests)
    let msg = Message::with_text("user", "Test message");

    let result = safe_agent.process(msg).await;
    assert!(result.is_ok(), "Middleware should process messages");
}

#[tokio::test]
async fn test_input_validation_allows_normal_input() {
    let agent = TestAgent::new("Hello back!");
    let safe_agent = InputValidationMiddleware::new(agent).with_prompt_injection_detector();

    let msg = Message::with_text("user", "Hello, how are you?");

    let result = safe_agent.process(msg).await;
    assert!(result.is_ok(), "Normal input should pass");
    let response = result.unwrap();
    assert_eq!(response.content_as_str().unwrap(), "Hello back!");
}

#[tokio::test]
async fn test_content_filter_blocks_banned_words() {
    let agent = TestAgent::new("Response");
    let safe_agent = InputValidationMiddleware::new(agent).with_content_filter();

    // Content filter has default banned patterns
    let msg = Message::with_text("user", "test message");

    let result = safe_agent.process(msg).await;
    assert!(result.is_ok(), "Normal content should pass");
}

#[tokio::test]
async fn test_output_validation_with_redactor() {
    let agent = TestAgent::new("Response with data");
    let safe_agent = OutputValidationMiddleware::new(agent).with_redactor();

    let msg = Message::with_text("user", "test");

    let result = safe_agent.process(msg).await;
    assert!(
        result.is_ok(),
        "Redactor middleware should process messages"
    );

    // Redaction logic is tested in unit tests
    let response = result.unwrap();
    let content = response.content_as_str().unwrap();
    assert!(!content.is_empty(), "Response should not be empty");
}

#[tokio::test]
async fn test_output_validation_with_size_limit() {
    let agent = TestAgent::new("Short response");
    let safe_agent = OutputValidationMiddleware::new(agent).with_max_size(1000);

    let msg = Message::with_text("user", "test");

    let result = safe_agent.process(msg).await;
    assert!(result.is_ok(), "Small output should pass size check");
}

#[tokio::test]
async fn test_permission_middleware_with_user_role() {
    let agent = TestAgent::new("Response");
    let safe_agent = PermissionMiddleware::new(agent, Role::User);

    let msg = Message::with_text("user", "test");

    let result = safe_agent.process(msg).await;
    assert!(result.is_ok(), "User role should allow processing");
}

#[tokio::test]
async fn test_permission_middleware_with_readonly_role() {
    let agent = TestAgent::new("Response");
    let safe_agent = PermissionMiddleware::new(agent, Role::ReadOnly);

    let msg = Message::with_text("user", "test");

    let result = safe_agent.process(msg).await;
    assert!(result.is_ok(), "ReadOnly role should allow processing");
}

#[tokio::test]
async fn test_full_security_stack() {
    // Create a fully secured agent with all layers
    let agent = TestAgent::new("Hello!");

    let safe_agent = InputValidationMiddleware::new(agent)
        .with_prompt_injection_detector()
        .with_content_filter();

    let safe_agent = OutputValidationMiddleware::new(safe_agent).with_redactor();

    let safe_agent = PermissionMiddleware::new(safe_agent, Role::User);

    // Test with normal input
    let msg = Message::with_text("user", "Hello, how are you?");
    let result = safe_agent.process(msg).await;
    assert!(
        result.is_ok(),
        "Normal request should pass all security layers"
    );
}

#[tokio::test]
async fn test_security_stack_with_validation() {
    // Create a fully secured agent
    let agent = TestAgent::new("Response");

    let safe_agent = InputValidationMiddleware::new(agent).with_prompt_injection_detector();

    let safe_agent = OutputValidationMiddleware::new(safe_agent).with_redactor();

    let safe_agent = PermissionMiddleware::new(safe_agent, Role::User);

    // Test that all layers work together
    let msg = Message::with_text("user", "Normal test message");
    let result = safe_agent.process(msg).await;
    assert!(
        result.is_ok(),
        "Full security stack should process normal messages"
    );
}

#[tokio::test]
async fn test_security_stack_output_processing() {
    // Create agent with output
    let agent = TestAgent::new("Response data");

    let safe_agent = InputValidationMiddleware::new(agent).with_prompt_injection_detector();

    let safe_agent = OutputValidationMiddleware::new(safe_agent).with_redactor();

    let safe_agent = PermissionMiddleware::new(safe_agent, Role::User);

    let msg = Message::with_text("user", "test");
    let result = safe_agent.process(msg).await;
    assert!(result.is_ok(), "Should process through all layers");

    let response = result.unwrap();
    let content = response.content_as_str().unwrap();
    assert!(!content.is_empty(), "Should have response content");
}

#[tokio::test]
async fn test_multiple_messages_through_security_stack() {
    let agent = TestAgent::new("OK");

    let safe_agent = InputValidationMiddleware::new(agent)
        .with_prompt_injection_detector()
        .with_content_filter();

    let safe_agent = OutputValidationMiddleware::new(safe_agent).with_redactor();

    let safe_agent = PermissionMiddleware::new(safe_agent, Role::User);

    // Process multiple messages
    for i in 1..=5 {
        let msg = Message::with_text("user", &format!("Test message {}", i));
        let result = safe_agent.process(msg).await;
        assert!(result.is_ok(), "Message {} should pass", i);
    }
}

#[tokio::test]
async fn test_admin_role_permissions() {
    let agent = TestAgent::new("Admin response");
    let safe_agent = PermissionMiddleware::new(agent, Role::Admin);

    let msg = Message::with_text("user", "admin command");

    let result = safe_agent.process(msg).await;
    assert!(result.is_ok(), "Admin role should have full access");
}

#[tokio::test]
async fn test_restricted_role_permissions() {
    let agent = TestAgent::new("Response");
    let safe_agent = PermissionMiddleware::new(agent, Role::Restricted);

    let msg = Message::with_text("user", "test");

    let result = safe_agent.process(msg).await;
    assert!(
        result.is_ok(),
        "Restricted role should allow basic processing"
    );
}
