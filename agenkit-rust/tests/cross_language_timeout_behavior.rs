/*!
 * Cross-language timeout behavior tests for Rust
 *
 * Validates that Agenkit's Rust timeout middleware behaves consistently
 * with the cross-language timeout behavior specification.
 */

use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

use serde::{Deserialize, Serialize};
use serde_json::json;
use tokio::time::sleep;

use agenkit::{Agent, AgentError, Message};

/// Agent response from fixture
#[derive(Debug, Clone, Deserialize)]
struct AgentResponse {
    success: bool,
    #[serde(default)]
    content: String,
    #[serde(default)]
    error: String,
}

/// Request in multi-request scenario
#[derive(Debug, Deserialize)]
struct TimeoutRequest {
    agent_delay_ms: u64,
    agent_response: AgentResponse,
}

/// Expected behavior from fixture
#[derive(Debug, Deserialize)]
struct ExpectedBehavior {
    successful: bool,
    timed_out: bool,
    #[serde(default)]
    final_response: String,
    #[serde(default)]
    error_type: String,
    #[serde(default)]
    error_message_contains: String,
    min_elapsed_ms: i64,
    max_elapsed_ms: i64,
}

/// Expected metrics from fixture
#[derive(Debug, Deserialize)]
struct ExpectedMetrics {
    total_requests: usize,
    successful_requests: usize,
    timed_out_requests: usize,
    success_rate: f64,
}

/// Scenario from fixture
#[derive(Debug, Deserialize)]
struct Scenario {
    #[serde(default)]
    agent_delay_ms: u64,
    #[serde(default)]
    agent_response: Option<AgentResponse>,
    #[serde(default)]
    requests: Vec<TimeoutRequest>,
}

/// Config from fixture
#[derive(Debug, Deserialize)]
struct Config {
    timeout_ms: u64,
}

/// Test case from fixture
#[derive(Debug, Deserialize)]
struct TestCase {
    id: String,
    name: String,
    config: Config,
    scenario: Scenario,
    #[serde(default)]
    expected_behavior: Option<ExpectedBehavior>,
    #[serde(default)]
    expected_metrics: Option<ExpectedMetrics>,
}

/// Fixtures file structure
#[derive(Debug, Deserialize)]
struct Fixtures {
    version: String,
    description: String,
    test_cases: Vec<TestCase>,
}

/// Mock agent that simulates delays for timeout testing
struct MockTimeoutAgent {
    delay_ms: u64,
    response: AgentResponse,
    call_count: Arc<AtomicUsize>,
}

impl MockTimeoutAgent {
    fn new(delay_ms: u64, response: AgentResponse) -> (Self, Arc<AtomicUsize>) {
        let call_count = Arc::new(AtomicUsize::new(0));
        let agent = Self {
            delay_ms,
            response,
            call_count: Arc::clone(&call_count),
        };
        (agent, call_count)
    }
}

#[async_trait::async_trait]
impl Agent for MockTimeoutAgent {
    fn name(&self) -> &str {
        "mock-timeout-agent"
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        self.call_count.fetch_add(1, Ordering::SeqCst);

        // Simulate delay
        if self.delay_ms > 0 {
            sleep(Duration::from_millis(self.delay_ms)).await;
        }

        // Return response or error
        if self.response.success {
            Ok(Message::new("agent", json!(self.response.content)))
        } else {
            Err(AgentError::ProcessingError(self.response.error.clone()))
        }
    }
}

/// Load timeout behavior fixtures
fn load_fixtures() -> Fixtures {
    let fixtures_path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../tests/cross_language/fixtures/timeout_behavior.json"
    );
    let fixtures_str =
        std::fs::read_to_string(fixtures_path).expect("Failed to read timeout_behavior.json");
    serde_json::from_str(&fixtures_str).expect("Failed to parse timeout_behavior.json")
}

/// Find a specific test case by ID
fn find_test_case<'a>(fixtures: &'a Fixtures, id: &str) -> &'a TestCase {
    fixtures
        .test_cases
        .iter()
        .find(|tc| tc.id == id)
        .expect(&format!("Test case not found: {}", id))
}

#[tokio::test]
async fn test_success_within_limit() {
    let fixtures = load_fixtures();
    let test_case = find_test_case(&fixtures, "timeout_success_within_limit");

    // Create mock agent
    let response = test_case.scenario.agent_response.as_ref().unwrap().clone();
    let (mock_agent, _call_count) =
        MockTimeoutAgent::new(test_case.scenario.agent_delay_ms, response);

    // Wrap with timeout
    let timeout = Duration::from_millis(test_case.config.timeout_ms);

    // Execute with timing
    let start = Instant::now();
    let message = Message::new("user", json!("test"));
    let result = tokio::time::timeout(timeout, mock_agent.process(message)).await;
    let elapsed = start.elapsed();

    // Verify expected behavior
    let expected = test_case.expected_behavior.as_ref().unwrap();
    assert!(result.is_ok(), "Should not timeout");
    let inner_result = result.unwrap();
    assert!(inner_result.is_ok(), "Should succeed");
    assert!(expected.successful);
    assert!(!expected.timed_out);
    assert_eq!(inner_result.unwrap().content, expected.final_response);

    let elapsed_ms = elapsed.as_millis() as i64;
    assert!(
        elapsed_ms >= expected.min_elapsed_ms,
        "Elapsed {}ms < min {}ms",
        elapsed_ms,
        expected.min_elapsed_ms
    );
    assert!(
        elapsed_ms <= expected.max_elapsed_ms,
        "Elapsed {}ms > max {}ms",
        elapsed_ms,
        expected.max_elapsed_ms
    );
}

#[tokio::test]
async fn test_timeout_exceeded() {
    let fixtures = load_fixtures();
    let test_case = find_test_case(&fixtures, "timeout_exceeded");

    // Create mock agent
    let response = test_case.scenario.agent_response.as_ref().unwrap().clone();
    let (mock_agent, _call_count) =
        MockTimeoutAgent::new(test_case.scenario.agent_delay_ms, response);

    // Wrap with timeout
    let timeout = Duration::from_millis(test_case.config.timeout_ms);

    // Execute with timing
    let start = Instant::now();
    let message = Message::new("user", json!("test"));
    let result = tokio::time::timeout(timeout, mock_agent.process(message)).await;
    let elapsed = start.elapsed();

    // Verify timeout error
    let expected = test_case.expected_behavior.as_ref().unwrap();
    assert!(result.is_err(), "Should timeout");
    assert!(!expected.successful);
    assert!(expected.timed_out);

    let elapsed_ms = elapsed.as_millis() as i64;
    assert!(
        elapsed_ms >= expected.min_elapsed_ms,
        "Elapsed {}ms < min {}ms",
        elapsed_ms,
        expected.min_elapsed_ms
    );
    assert!(
        elapsed_ms <= expected.max_elapsed_ms,
        "Elapsed {}ms > max {}ms",
        elapsed_ms,
        expected.max_elapsed_ms
    );
}

#[tokio::test]
async fn test_timeout_exactly_at_limit() {
    let fixtures = load_fixtures();
    let test_case = find_test_case(&fixtures, "timeout_exactly_at_limit");

    // Create mock agent
    let response = test_case.scenario.agent_response.as_ref().unwrap().clone();
    let (mock_agent, _call_count) =
        MockTimeoutAgent::new(test_case.scenario.agent_delay_ms, response);

    // Wrap with timeout
    let timeout = Duration::from_millis(test_case.config.timeout_ms);

    // Execute with timing
    let start = Instant::now();
    let message = Message::new("user", json!("test"));
    let result = tokio::time::timeout(timeout, mock_agent.process(message)).await;
    let elapsed = start.elapsed();

    // Verify expected behavior
    let expected = test_case.expected_behavior.as_ref().unwrap();
    assert!(result.is_ok(), "Should not timeout");
    let inner_result = result.unwrap();
    assert!(inner_result.is_ok(), "Should succeed");
    assert!(expected.successful);
    assert!(!expected.timed_out);
    assert_eq!(inner_result.unwrap().content, expected.final_response);

    let elapsed_ms = elapsed.as_millis() as i64;
    assert!(
        elapsed_ms >= expected.min_elapsed_ms,
        "Elapsed {}ms < min {}ms",
        elapsed_ms,
        expected.min_elapsed_ms
    );
    assert!(
        elapsed_ms <= expected.max_elapsed_ms,
        "Elapsed {}ms > max {}ms",
        elapsed_ms,
        expected.max_elapsed_ms
    );
}

#[tokio::test]
async fn test_zero_delay() {
    let fixtures = load_fixtures();
    let test_case = find_test_case(&fixtures, "timeout_zero_delay");

    // Create mock agent
    let response = test_case.scenario.agent_response.as_ref().unwrap().clone();
    let (mock_agent, _call_count) =
        MockTimeoutAgent::new(test_case.scenario.agent_delay_ms, response);

    // Wrap with timeout
    let timeout = Duration::from_millis(test_case.config.timeout_ms);

    // Execute with timing
    let start = Instant::now();
    let message = Message::new("user", json!("test"));
    let result = tokio::time::timeout(timeout, mock_agent.process(message)).await;
    let elapsed = start.elapsed();

    // Verify expected behavior
    let expected = test_case.expected_behavior.as_ref().unwrap();
    assert!(result.is_ok(), "Should not timeout");
    let inner_result = result.unwrap();
    assert!(inner_result.is_ok(), "Should succeed");
    assert!(expected.successful);
    assert!(!expected.timed_out);
    assert_eq!(inner_result.unwrap().content, expected.final_response);

    let elapsed_ms = elapsed.as_millis() as i64;
    assert!(
        elapsed_ms <= expected.max_elapsed_ms,
        "Elapsed {}ms > max {}ms",
        elapsed_ms,
        expected.max_elapsed_ms
    );
}

#[tokio::test]
async fn test_agent_error() {
    let fixtures = load_fixtures();
    let test_case = find_test_case(&fixtures, "timeout_agent_error");

    // Create mock agent
    let response = test_case.scenario.agent_response.as_ref().unwrap().clone();
    let (mock_agent, _call_count) =
        MockTimeoutAgent::new(test_case.scenario.agent_delay_ms, response);

    // Wrap with timeout
    let timeout = Duration::from_millis(test_case.config.timeout_ms);

    // Execute with timing
    let start = Instant::now();
    let message = Message::new("user", json!("test"));
    let result = tokio::time::timeout(timeout, mock_agent.process(message)).await;
    let elapsed = start.elapsed();

    // Verify agent error (not timeout)
    let expected = test_case.expected_behavior.as_ref().unwrap();
    assert!(result.is_ok(), "Should not timeout");
    let inner_result = result.unwrap();
    assert!(inner_result.is_err(), "Should have agent error");
    assert!(!expected.successful);
    assert!(!expected.timed_out);

    let error_msg = format!("{:?}", inner_result.unwrap_err());
    assert!(
        error_msg.contains(&expected.error_message_contains),
        "Error message '{}' should contain '{}'",
        error_msg,
        expected.error_message_contains
    );

    let elapsed_ms = elapsed.as_millis() as i64;
    assert!(
        elapsed_ms >= expected.min_elapsed_ms,
        "Elapsed {}ms < min {}ms",
        elapsed_ms,
        expected.min_elapsed_ms
    );
    assert!(
        elapsed_ms <= expected.max_elapsed_ms,
        "Elapsed {}ms > max {}ms",
        elapsed_ms,
        expected.max_elapsed_ms
    );
}

#[tokio::test]
async fn test_very_short_timeout() {
    let fixtures = load_fixtures();
    let test_case = find_test_case(&fixtures, "timeout_very_short");

    // Create mock agent
    let response = test_case.scenario.agent_response.as_ref().unwrap().clone();
    let (mock_agent, _call_count) =
        MockTimeoutAgent::new(test_case.scenario.agent_delay_ms, response);

    // Wrap with timeout
    let timeout = Duration::from_millis(test_case.config.timeout_ms);

    // Execute with timing
    let start = Instant::now();
    let message = Message::new("user", json!("test"));
    let result = tokio::time::timeout(timeout, mock_agent.process(message)).await;
    let elapsed = start.elapsed();

    // Verify timeout error
    let expected = test_case.expected_behavior.as_ref().unwrap();
    assert!(result.is_err(), "Should timeout");
    assert!(!expected.successful);
    assert!(expected.timed_out);

    let elapsed_ms = elapsed.as_millis() as i64;
    assert!(
        elapsed_ms >= expected.min_elapsed_ms,
        "Elapsed {}ms < min {}ms",
        elapsed_ms,
        expected.min_elapsed_ms
    );
    // Very short timeouts get wider tolerance
    assert!(
        elapsed_ms <= expected.max_elapsed_ms + 20,
        "Elapsed {}ms > max {}ms (with 20ms tolerance)",
        elapsed_ms,
        expected.max_elapsed_ms
    );
}

#[tokio::test]
async fn test_metrics_tracking() {
    let fixtures = load_fixtures();
    let test_case = find_test_case(&fixtures, "timeout_metrics_tracking");

    // Create timeout duration
    let timeout = Duration::from_millis(test_case.config.timeout_ms);

    // Process multiple requests
    let mut successful = 0;
    let mut timed_out = 0;

    for request in &test_case.scenario.requests {
        let (mock_agent, _call_count) =
            MockTimeoutAgent::new(request.agent_delay_ms, request.agent_response.clone());

        let message = Message::new("user", json!("test"));
        let result = tokio::time::timeout(timeout, mock_agent.process(message)).await;

        match result {
            Ok(Ok(_)) => successful += 1,
            _ => timed_out += 1,
        }
    }

    // Verify metrics
    let expected_metrics = test_case.expected_metrics.as_ref().unwrap();
    assert_eq!(
        test_case.scenario.requests.len(),
        expected_metrics.total_requests
    );
    assert_eq!(successful, expected_metrics.successful_requests);
    assert_eq!(timed_out, expected_metrics.timed_out_requests);
}
