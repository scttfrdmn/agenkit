# Rust Testing Framework

## Current State

The Rust implementation has **646 tests across all modules** with comprehensive coverage. Basic mock agents and test utilities are available throughout the codebase.

**Test Coverage:**
- Core agent interface: 25+ tests
- Message handling: 30+ tests
- Patterns (Sequential, Parallel, Reflection, etc.): 133 tests
- LLM Adapters: 31 tests
- Middleware (Retry, Circuit Breaker, Timeout): 50+ tests
- Observability (Tracing, Metrics, Logging, Audit): 66 tests
- Safety: 40+ tests
- Evaluation Frameworks: 73 tests
- Infrastructure and utilities: 100+ tests

**Note:** Issue #541 tracks adding a dedicated `test_utils` module with shared mock agents and builder patterns, similar to the Zig `src/test_utils.zig`. The patterns below reflect both current practice and the planned utilities.

---

## Basic Test Patterns

### `#[cfg(test)]` Modules

Co-locate unit tests with the code they test:

```rust
// src/agents/echo.rs
use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;

pub struct EchoAgent;

#[async_trait]
impl Agent for EchoAgent {
    fn name(&self) -> &str { "echo" }
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let text = message.content_as_str().unwrap_or("(empty)");
        Ok(Message::assistant(&format!("Echo: {}", text)))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_echo_returns_input() {
        let agent = EchoAgent;
        let msg = Message::with_text("user", "Hello!");
        let response = agent.process(msg).await.expect("should succeed");

        assert_eq!(response.content_as_str().unwrap_or(""), "Echo: Hello!");
        assert_eq!(response.role, "assistant");
    }

    #[tokio::test]
    async fn test_echo_handles_empty_input() {
        let agent = EchoAgent;
        let msg = Message::with_text("user", "");
        let response = agent.process(msg).await.expect("should not fail on empty");
        assert!(response.content_as_str().is_some());
    }
}
```

### Async Tests with `#[tokio::test]`

All agent tests require `#[tokio::test]` since `process()` is async:

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use agenkit::core::{Agent, AgentError, Message};

    // Basic async test
    #[tokio::test]
    async fn test_agent_processes_successfully() {
        let agent = MyAgent::new();
        let msg = Message::user("test input");
        let result = agent.process(msg).await;
        assert!(result.is_ok());
    }

    // Test error conditions
    #[tokio::test]
    async fn test_agent_returns_error_on_empty_input() {
        let agent = StrictAgent::new();
        let msg = Message::user("");
        let result = agent.process(msg).await;
        assert!(matches!(result, Err(AgentError::InvalidInput(_))));
    }

    // Test with timeout (for agents that can hang)
    #[tokio::test(flavor = "multi_thread", worker_threads = 2)]
    async fn test_agent_with_timeout() {
        use tokio::time::{timeout, Duration};

        let agent = MyAgent::new();
        let msg = Message::user("test");

        let result = timeout(Duration::from_secs(5), agent.process(msg)).await;
        assert!(result.is_ok(), "agent timed out");
        assert!(result.unwrap().is_ok());
    }
}
```

---

## Mock Agents

### Simple Mock Agent

```rust
use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

/// A mock agent that cycles through predefined responses.
pub struct MockAgent {
    responses: Vec<String>,
    call_count: Arc<AtomicUsize>,
}

impl MockAgent {
    pub fn new(responses: Vec<&str>) -> Self {
        Self {
            responses: responses.iter().map(|s| s.to_string()).collect(),
            call_count: Arc::new(AtomicUsize::new(0)),
        }
    }

    pub fn call_count(&self) -> usize {
        self.call_count.load(Ordering::SeqCst)
    }

    pub fn reset(&self) {
        self.call_count.store(0, Ordering::SeqCst);
    }
}

#[async_trait]
impl Agent for MockAgent {
    fn name(&self) -> &str { "mock" }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        let idx = self.call_count.fetch_add(1, Ordering::SeqCst);
        let response = &self.responses[idx % self.responses.len()];
        Ok(Message::assistant(response))
    }
}

/// A mock agent that always fails with a specified error.
pub struct FailingMockAgent {
    error: AgentError,
    call_count: Arc<AtomicUsize>,
}

impl FailingMockAgent {
    pub fn new(error: AgentError) -> Self {
        Self {
            error,
            call_count: Arc::new(AtomicUsize::new(0)),
        }
    }
}

#[async_trait]
impl Agent for FailingMockAgent {
    fn name(&self) -> &str { "failing-mock" }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        self.call_count.fetch_add(1, Ordering::SeqCst);
        // Clone the error variant (AgentError must implement Clone or use a factory)
        Err(AgentError::ProcessingFailed("mock failure".to_string()))
    }
}
```

**Usage in tests:**

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use agenkit::patterns::SequentialPattern;

    #[tokio::test]
    async fn test_mock_agent_cycles_responses() {
        let mock = MockAgent::new(vec!["First", "Second", "Third"]);

        let msg = Message::user("test");

        let r1 = mock.process(msg.clone()).await.unwrap();
        let r2 = mock.process(msg.clone()).await.unwrap();
        let r3 = mock.process(msg.clone()).await.unwrap();
        let r4 = mock.process(msg.clone()).await.unwrap(); // cycles back

        assert_eq!(r1.content_as_str().unwrap_or(""), "First");
        assert_eq!(r2.content_as_str().unwrap_or(""), "Second");
        assert_eq!(r3.content_as_str().unwrap_or(""), "Third");
        assert_eq!(r4.content_as_str().unwrap_or(""), "First");
        assert_eq!(mock.call_count(), 4);
    }

    #[tokio::test]
    async fn test_sequential_with_mock_agents() {
        let pipeline = SequentialPattern::new(vec![
            Box::new(MockAgent::new(vec!["step-1-output"])),
            Box::new(MockAgent::new(vec!["step-2-output"])),
        ]).expect("valid pipeline");

        let result = pipeline.process(Message::user("start")).await.unwrap();
        assert_eq!(result.content_as_str().unwrap_or(""), "step-2-output");
    }
}
```

---

## Mocking with `mockall`

For more sophisticated mocking with expectations and call verification:

```bash
cargo add mockall --dev
```

```rust
use mockall::automock;
use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;

// Generate mock with #[automock]
#[automock]
#[async_trait]
pub trait LLMProvider: Send + Sync {
    async fn complete(&self, prompt: &str) -> Result<String, AgentError>;
}

#[cfg(test)]
mod tests {
    use super::*;
    use mockall::predicate::*;

    #[tokio::test]
    async fn test_agent_calls_llm_with_correct_prompt() {
        let mut mock_llm = MockLLMProvider::new();

        // Set expectation: called once with any string, returns "response"
        mock_llm
            .expect_complete()
            .times(1)
            .returning(|_| Ok("mocked response".to_string()));

        let agent = MyAgentWithLLM::new(Box::new(mock_llm));
        let msg = Message::user("user query");
        let result = agent.process(msg).await.unwrap();

        assert_eq!(result.content_as_str().unwrap_or(""), "mocked response");
        // mockall automatically verifies expectations when mock is dropped
    }

    #[tokio::test]
    async fn test_agent_handles_llm_failure() {
        let mut mock_llm = MockLLMProvider::new();
        mock_llm
            .expect_complete()
            .returning(|_| Err(AgentError::NetworkError("connection refused".to_string())));

        let agent = MyAgentWithLLM::new(Box::new(mock_llm));
        let result = agent.process(Message::user("query")).await;

        assert!(matches!(result, Err(AgentError::NetworkError(_))));
    }
}
```

---

## Property-Based Tests with `proptest`

```bash
cargo add proptest --dev
```

```rust
use proptest::prelude::*;
use agenkit::core::Message;

proptest! {
    // Test that echo agent always returns its input
    #[test]
    fn echo_agent_is_identity(s in "\\PC*") {  // Any printable unicode string
        let rt = tokio::runtime::Runtime::new().unwrap();
        let agent = EchoAgent;
        let msg = Message::user(&s);

        let result = rt.block_on(agent.process(msg)).unwrap();
        let expected = format!("Echo: {}", s);
        prop_assert_eq!(result.content_as_str().unwrap_or(""), expected.as_str());
    }

    // Test that message role is preserved
    #[test]
    fn response_is_always_assistant_role(content in "\\PC{1,500}") {
        let rt = tokio::runtime::Runtime::new().unwrap();
        let agent = EchoAgent;
        let msg = Message::user(&content);
        let result = rt.block_on(agent.process(msg)).unwrap();
        prop_assert_eq!(&result.role, "assistant");
    }

    // Test retry count bounds
    #[test]
    fn retry_decorator_respects_max_attempts(max_attempts in 1u32..=10) {
        use agenkit::middleware::RetryDecorator;
        use std::time::Duration;

        let rt = tokio::runtime::Runtime::new().unwrap();
        let failing = FailingMockAgent::new(AgentError::ProcessingFailed("fail".to_string()));
        let agent = RetryDecorator::new(failing, max_attempts, Duration::from_millis(1));

        let result = rt.block_on(agent.process(Message::user("test")));
        prop_assert!(result.is_err());
        // Call count should not exceed max_attempts
        // (actual assertion depends on MockAgent call_count access)
    }
}
```

---

## Integration Tests

Integration tests live in `tests/` and test multiple components together:

```rust
// tests/integration_test.rs
use agenkit::core::{Agent, AgentError, Message};
use agenkit::middleware::{RetryDecorator, TimeoutDecorator};
use agenkit::patterns::SequentialPattern;
use std::time::Duration;

#[tokio::test]
async fn test_full_pipeline_with_middleware() {
    let pipeline = SequentialPattern::new(vec![
        Box::new(RetryDecorator::new(
            MockAgent::new(vec!["stage-1"]),
            3,
            Duration::from_millis(1),
        )),
        Box::new(MockAgent::new(vec!["stage-2"])),
    ]).expect("valid pipeline");

    let agent = TimeoutDecorator::new(pipeline, Duration::from_secs(5));

    let result = agent.process(Message::user("test")).await.unwrap();
    assert_eq!(result.content_as_str().unwrap_or(""), "stage-2");
}

#[tokio::test]
async fn test_middleware_chain_propagates_errors() {
    use agenkit::core::AgentError;

    let failing = FailingMockAgent::new(AgentError::ProcessingFailed("fail".to_string()));
    let agent = RetryDecorator::new(failing, 2, Duration::from_millis(1));

    let result = agent.process(Message::user("test")).await;
    assert!(result.is_err());
}
```

---

## Running Tests

```bash
# Run all tests
cargo test

# Run a specific test
cargo test test_echo_returns_input

# Run all tests in a module
cargo test agents::tests

# Run with output visible (do not capture stdout)
cargo test -- --nocapture

# Run tests in release mode (faster, but no debug assertions)
cargo test --release

# Run only integration tests
cargo test --test integration_test

# Run tests with specific feature flags
cargo test --features observability

# Run safety module tests
cargo test --lib safety

# Parallel vs sequential execution
cargo test -- --test-threads=1  # Sequential (useful for tests that share state)
cargo test -- --test-threads=4  # Explicit parallelism
```

---

## Related Issues

- #541 — Shared `test_utils` module for mock agents and builder patterns (planned)
- #217 — Test coverage improvements (completed in v0.75.0)
- #360 — Property-based tests for middleware (completed in v0.75.0)

---

**Version**: v0.75.0
**Last Updated**: March 17, 2026
