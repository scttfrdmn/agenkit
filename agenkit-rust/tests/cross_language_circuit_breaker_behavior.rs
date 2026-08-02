/*! Cross-language circuit breaker behavior tests for Rust
 *
 * Validates that Agenkit's Rust circuit breaker middleware behaves consistently
 * with the cross-language circuit breaker behavior specification.
 */

use std::collections::HashMap;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;

use serde::Deserialize;
use serde_json::json;
use tokio::time::sleep;

use agenkit::middleware::{CircuitBreakerConfig, CircuitBreakerMiddleware, CircuitState};
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

/// Step in a multi-step scenario
#[derive(Debug, Deserialize)]
struct CircuitBreakerStep {
    action: String,
    #[serde(default)]
    agent_response: Option<AgentResponse>,
    #[serde(default)]
    duration_ms: Option<u64>,
}

/// Scenario from fixture
#[derive(Debug, Deserialize)]
struct Scenario {
    #[serde(default)]
    agent_responses: Vec<AgentResponse>,
    #[serde(default)]
    steps: Vec<CircuitBreakerStep>,
}

/// Expected behavior from fixture
//
// The `fourth_request_rejected` / `recovery_successful` / `circuit_fully_recovered` /
// `reopened_after_partial_recovery` flags are now genuinely asserted (#791) -- they used
// to be read and then `assert!`ed directly, which only proved the fixture contained
// `true`. Still unasserted: `state_transitions` (no core records transition *order*, only
// counts, so nothing can check it yet) and the `all_requests_completed` /
// `all_rejected_while_open` flags, which restate what the counters already cover.
#[derive(Debug, Deserialize)]
#[allow(dead_code)]
struct ExpectedBehavior {
    final_state: String,
    #[serde(default)]
    total_requests: Option<usize>,
    #[serde(default)]
    successful_requests: Option<usize>,
    #[serde(default)]
    failed_requests: Option<usize>,
    #[serde(default)]
    rejected_requests: Option<usize>,
    #[serde(default)]
    all_requests_completed: Option<bool>,
    #[serde(default)]
    state_transitions: Vec<String>,
    #[serde(default)]
    fourth_request_rejected: Option<bool>,
    #[serde(default)]
    recovery_successful: Option<bool>,
    #[serde(default)]
    total_successful_in_half_open: Option<usize>,
    #[serde(default)]
    circuit_fully_recovered: Option<bool>,
    #[serde(default)]
    reopened_after_partial_recovery: Option<bool>,
    #[serde(default)]
    all_rejected_while_open: Option<bool>,
}

/// Expected metrics from fixture
//
// Every field here is asserted, including `state_changes` -- which was the bug in #791.
// Five key formats had drifted apart (Python/Go `closed->open`, Rust/TS `CLOSED->OPEN`,
// Zig `CLOSED_to_OPEN`, this fixture `closed_to_open`, and C++ not keyed at all) purely
// because no harness read the field. The canonical form is now lowercase with `->`.
#[derive(Debug, Deserialize)]
struct ExpectedMetrics {
    total_requests: usize,
    successful_requests: usize,
    failed_requests: usize,
    rejected_requests: usize,
    state_changes: HashMap<String, usize>,
    final_state: String,
}

/// Config from fixture
#[derive(Debug, Deserialize)]
struct Config {
    failure_threshold: u32,
    recovery_timeout_ms: u64,
    success_threshold: u32,
    timeout_ms: u64,
}

/// Test case from fixture
#[derive(Debug, Deserialize)]
#[allow(dead_code)]
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
#[allow(dead_code)]
struct Fixtures {
    version: String,
    description: String,
    test_cases: Vec<TestCase>,
}

/// Mock agent that simulates responses for circuit breaker testing
struct MockCircuitBreakerAgent {
    responses: Vec<AgentResponse>,
    call_count: Arc<AtomicUsize>,
}

impl MockCircuitBreakerAgent {
    fn new(responses: Vec<AgentResponse>) -> (Self, Arc<AtomicUsize>) {
        let call_count = Arc::new(AtomicUsize::new(0));
        let agent = Self {
            responses,
            call_count: Arc::clone(&call_count),
        };
        (agent, call_count)
    }
}

#[async_trait::async_trait]
impl Agent for MockCircuitBreakerAgent {
    fn name(&self) -> &str {
        "mock-circuit-breaker-agent"
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        let count = self.call_count.fetch_add(1, Ordering::SeqCst);

        if count >= self.responses.len() {
            return Err(AgentError::ProcessingError(
                "No more responses available".to_string(),
            ));
        }

        let response = &self.responses[count];

        if response.success {
            Ok(Message::new("agent", json!(response.content.clone())))
        } else {
            Err(AgentError::ProcessingError(response.error.clone()))
        }
    }
}

/// Load circuit breaker behavior fixtures
fn load_fixtures() -> Fixtures {
    let fixtures_path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../tests/cross_language/fixtures/circuit_breaker_behavior.json"
    );
    let fixtures_str = std::fs::read_to_string(fixtures_path)
        .expect("Failed to read circuit_breaker_behavior.json");
    serde_json::from_str(&fixtures_str).expect("Failed to parse circuit_breaker_behavior.json")
}

/// Find a specific test case by ID
fn find_test_case<'a>(fixtures: &'a Fixtures, id: &str) -> &'a TestCase {
    fixtures
        .test_cases
        .iter()
        .find(|tc| tc.id == id)
        .unwrap_or_else(|| panic!("Test case not found: {}", id))
}

/// Convert state string to CircuitState
// Kept for symmetry with the other harnesses' state parsers; this file compares
// state names as strings and never needs the enum (#778).
#[allow(dead_code)]
fn state_from_string(s: &str) -> CircuitState {
    match s {
        "closed" => CircuitState::Closed,
        "open" => CircuitState::Open,
        "half_open" => CircuitState::HalfOpen,
        _ => panic!("Unknown state: {}", s),
    }
}

/// Convert CircuitState to lowercase string
fn state_to_string(state: CircuitState) -> String {
    match state {
        CircuitState::Closed => "closed".to_string(),
        CircuitState::Open => "open".to_string(),
        CircuitState::HalfOpen => "half_open".to_string(),
    }
}

/// Assert every named transition was taken at least once.
///
/// Final-state checks alone are weak: a breaker that opened and never probed half-open
/// ends "open" just like one that reopened after a failed probe, and one that never
/// opened at all ends "closed" just like one that fully recovered. Checking the path is
/// what distinguishes them (#791).
fn assert_transitions(changes: &HashMap<String, u64>, expected: &[&str]) {
    for key in expected {
        assert!(
            changes.get(*key).copied().unwrap_or(0) >= 1,
            "transition {} never happened: {:?}",
            key,
            changes
        );
    }
}

#[tokio::test]
async fn test_circuit_breaker_closed_success() {
    let fixtures = load_fixtures();
    let test_case = find_test_case(&fixtures, "circuit_breaker_closed_success");

    // Create mock agent
    let (mock_agent, _call_count) =
        MockCircuitBreakerAgent::new(test_case.scenario.agent_responses.clone());

    // Create circuit breaker
    let config = CircuitBreakerConfig::builder()
        .failure_threshold(test_case.config.failure_threshold)
        .recovery_timeout(Duration::from_millis(test_case.config.recovery_timeout_ms))
        .success_threshold(test_case.config.success_threshold)
        .timeout(Duration::from_millis(test_case.config.timeout_ms))
        .build();

    let circuit_breaker = CircuitBreakerMiddleware::new(mock_agent, config);

    // Execute requests
    let mut successful = 0;
    for _ in 0..test_case.scenario.agent_responses.len() {
        let message = Message::new("user", json!("test"));
        let result = circuit_breaker.process(message).await;
        if result.is_ok() {
            successful += 1;
        }
    }

    // Verify expected behavior
    let expected = test_case.expected_behavior.as_ref().unwrap();
    let metrics = circuit_breaker.get_metrics().await;
    assert_eq!(state_to_string(metrics.current_state), expected.final_state);

    // The counters, not just the final state — Python and Go both check all four here, and
    // `successful` is compared against `successful_requests` rather than `total_requests`
    // so the assertion still means something in a scenario that isn't all-success.
    assert_eq!(
        metrics.total_requests,
        expected.total_requests.unwrap() as u64
    );
    assert_eq!(
        metrics.successful_requests,
        expected.successful_requests.unwrap() as u64
    );
    assert_eq!(
        metrics.failed_requests,
        expected.failed_requests.unwrap() as u64
    );
    assert_eq!(
        metrics.rejected_requests,
        expected.rejected_requests.unwrap() as u64
    );
    assert_eq!(successful, expected.successful_requests.unwrap());

    // A closed circuit records no transitions at all.
    assert!(
        metrics.state_changes.is_empty(),
        "circuit should never have left CLOSED: {:?}",
        metrics.state_changes
    );
}

#[tokio::test]
async fn test_circuit_breaker_opens_on_failures() {
    let fixtures = load_fixtures();
    let test_case = find_test_case(&fixtures, "circuit_breaker_opens_on_failures");

    // Create mock agent
    let (mock_agent, _call_count) =
        MockCircuitBreakerAgent::new(test_case.scenario.agent_responses.clone());

    // Create circuit breaker
    let config = CircuitBreakerConfig::builder()
        .failure_threshold(test_case.config.failure_threshold)
        .recovery_timeout(Duration::from_millis(test_case.config.recovery_timeout_ms))
        .success_threshold(test_case.config.success_threshold)
        .timeout(Duration::from_millis(test_case.config.timeout_ms))
        .build();

    let circuit_breaker = CircuitBreakerMiddleware::new(mock_agent, config);

    // Execute requests, recording each outcome so per-request claims can be checked
    let mut rejected = 0;
    let mut outcomes = Vec::new();
    for _ in 0..test_case.scenario.agent_responses.len() {
        let message = Message::new("user", json!("test"));
        match circuit_breaker.process(message).await {
            Ok(_) => outcomes.push("ok"),
            Err(AgentError::ProcessingError(msg)) if msg.contains("circuit breaker is open") => {
                rejected += 1;
                outcomes.push("rejected");
            }
            Err(_) => outcomes.push("failed"),
        }
    }

    // Verify expected behavior
    let expected = test_case.expected_behavior.as_ref().unwrap();
    let metrics = circuit_breaker.get_metrics().await;
    assert_eq!(state_to_string(metrics.current_state), expected.final_state);
    assert!(rejected > 0);

    // `assert!(expected.fourth_request_rejected.unwrap())` was a tautology: it asserted a
    // `true` literal read out of the fixture, so it passed with the middleware deleted
    // (#791). Check the actual claim -- the fourth request was rejected by the open
    // circuit, not merely failed by the inner agent (whose fourth scripted response is a
    // success).
    if expected.fourth_request_rejected == Some(true) {
        assert_eq!(
            outcomes.get(3),
            Some(&"rejected"),
            "expected 4th request rejected, got {:?}",
            outcomes
        );
    }
}

#[tokio::test]
async fn test_circuit_breaker_half_open_transition() {
    let fixtures = load_fixtures();
    let test_case = find_test_case(&fixtures, "circuit_breaker_half_open_transition");

    // Extract responses from steps
    let responses: Vec<AgentResponse> = test_case
        .scenario
        .steps
        .iter()
        .filter_map(|step| {
            if step.action == "request" {
                step.agent_response.clone()
            } else {
                None
            }
        })
        .collect();

    let (mock_agent, _call_count) = MockCircuitBreakerAgent::new(responses);

    // Create circuit breaker
    let config = CircuitBreakerConfig::builder()
        .failure_threshold(test_case.config.failure_threshold)
        .recovery_timeout(Duration::from_millis(test_case.config.recovery_timeout_ms))
        .success_threshold(test_case.config.success_threshold)
        .timeout(Duration::from_millis(test_case.config.timeout_ms))
        .build();

    let circuit_breaker = CircuitBreakerMiddleware::new(mock_agent, config);

    // Execute steps
    for step in &test_case.scenario.steps {
        if step.action == "request" {
            let message = Message::new("user", json!("test"));
            let _ = circuit_breaker.process(message).await;
        } else if step.action == "wait" {
            sleep(Duration::from_millis(step.duration_ms.unwrap())).await;
        }
    }

    // Verify expected behavior
    let expected = test_case.expected_behavior.as_ref().unwrap();
    let metrics = circuit_breaker.get_metrics().await;
    assert_eq!(state_to_string(metrics.current_state), expected.final_state);

    // `assert!(expected.recovery_successful.unwrap())` was a tautology (#791). The real
    // claim is that the circuit opened, then recovered *through* half-open -- a breaker
    // that never opened would also end "closed" and pass the final-state check.
    if expected.recovery_successful == Some(true) {
        assert_transitions(
            &metrics.state_changes,
            &["closed->open", "open->half_open", "half_open->closed"],
        );
    }
}

#[tokio::test]
async fn test_circuit_breaker_half_open_to_closed() {
    let fixtures = load_fixtures();
    let test_case = find_test_case(&fixtures, "circuit_breaker_half_open_to_closed");

    // Extract responses from steps
    let responses: Vec<AgentResponse> = test_case
        .scenario
        .steps
        .iter()
        .filter_map(|step| {
            if step.action == "request" {
                step.agent_response.clone()
            } else {
                None
            }
        })
        .collect();

    let (mock_agent, _call_count) = MockCircuitBreakerAgent::new(responses);

    // Create circuit breaker
    let config = CircuitBreakerConfig::builder()
        .failure_threshold(test_case.config.failure_threshold)
        .recovery_timeout(Duration::from_millis(test_case.config.recovery_timeout_ms))
        .success_threshold(test_case.config.success_threshold)
        .timeout(Duration::from_millis(test_case.config.timeout_ms))
        .build();

    let circuit_breaker = CircuitBreakerMiddleware::new(mock_agent, config);

    // Execute steps
    for step in &test_case.scenario.steps {
        if step.action == "request" {
            let message = Message::new("user", json!("test"));
            let _ = circuit_breaker.process(message).await;
        } else if step.action == "wait" {
            sleep(Duration::from_millis(step.duration_ms.unwrap())).await;
        }
    }

    // Verify expected behavior
    let expected = test_case.expected_behavior.as_ref().unwrap();
    let metrics = circuit_breaker.get_metrics().await;
    assert_eq!(state_to_string(metrics.current_state), expected.final_state);

    // `assert!(expected.circuit_fully_recovered.unwrap())` was a tautology (#791). Check
    // the real claim: the circuit did close from half-open rather than skipping the probe.
    if expected.circuit_fully_recovered == Some(true) {
        assert_transitions(
            &metrics.state_changes,
            &["open->half_open", "half_open->closed"],
        );
    }
}

#[tokio::test]
async fn test_circuit_breaker_half_open_reopens() {
    let fixtures = load_fixtures();
    let test_case = find_test_case(&fixtures, "circuit_breaker_half_open_reopens");

    // Extract responses from steps
    let responses: Vec<AgentResponse> = test_case
        .scenario
        .steps
        .iter()
        .filter_map(|step| {
            if step.action == "request" {
                step.agent_response.clone()
            } else {
                None
            }
        })
        .collect();

    let (mock_agent, _call_count) = MockCircuitBreakerAgent::new(responses);

    // Create circuit breaker
    let config = CircuitBreakerConfig::builder()
        .failure_threshold(test_case.config.failure_threshold)
        .recovery_timeout(Duration::from_millis(test_case.config.recovery_timeout_ms))
        .success_threshold(test_case.config.success_threshold)
        .timeout(Duration::from_millis(test_case.config.timeout_ms))
        .build();

    let circuit_breaker = CircuitBreakerMiddleware::new(mock_agent, config);

    // Execute steps
    for step in &test_case.scenario.steps {
        if step.action == "request" {
            let message = Message::new("user", json!("test"));
            let _ = circuit_breaker.process(message).await;
        } else if step.action == "wait" {
            sleep(Duration::from_millis(step.duration_ms.unwrap())).await;
        }
    }

    // Verify expected behavior
    let expected = test_case.expected_behavior.as_ref().unwrap();
    let metrics = circuit_breaker.get_metrics().await;
    assert_eq!(state_to_string(metrics.current_state), expected.final_state);

    // `assert!(expected.reopened_after_partial_recovery.unwrap())` was a tautology (#791).
    // The real claim is the full path closed -> open -> half_open -> open: a breaker that
    // opened once and never probed would also end "open" and pass the final-state check.
    if expected.reopened_after_partial_recovery == Some(true) {
        assert_transitions(
            &metrics.state_changes,
            &["closed->open", "open->half_open", "half_open->open"],
        );
    }
}

#[tokio::test]
async fn test_circuit_breaker_rejects_when_open() {
    let fixtures = load_fixtures();
    let test_case = find_test_case(&fixtures, "circuit_breaker_rejects_when_open");

    // Create mock agent
    let (mock_agent, _call_count) =
        MockCircuitBreakerAgent::new(test_case.scenario.agent_responses.clone());

    // Create circuit breaker
    let config = CircuitBreakerConfig::builder()
        .failure_threshold(test_case.config.failure_threshold)
        .recovery_timeout(Duration::from_millis(test_case.config.recovery_timeout_ms))
        .success_threshold(test_case.config.success_threshold)
        .timeout(Duration::from_millis(test_case.config.timeout_ms))
        .build();

    let circuit_breaker = CircuitBreakerMiddleware::new(mock_agent, config);

    // Execute requests
    let mut rejected = 0;
    for _ in 0..test_case.scenario.agent_responses.len() {
        let message = Message::new("user", json!("test"));
        let result = circuit_breaker.process(message).await;
        if let Err(AgentError::ProcessingError(msg)) = result {
            if msg.contains("circuit breaker is open") {
                rejected += 1;
            }
        }
    }

    // Verify expected behavior
    let expected = test_case.expected_behavior.as_ref().unwrap();
    let metrics = circuit_breaker.get_metrics().await;
    assert_eq!(state_to_string(metrics.current_state), expected.final_state);
    assert_eq!(rejected, expected.rejected_requests.unwrap());
}

#[tokio::test]
async fn test_circuit_breaker_metrics_tracking() {
    let fixtures = load_fixtures();
    let test_case = find_test_case(&fixtures, "circuit_breaker_metrics_tracking");

    // Extract responses from steps
    let responses: Vec<AgentResponse> = test_case
        .scenario
        .steps
        .iter()
        .filter_map(|step| {
            if step.action == "request" {
                step.agent_response.clone()
            } else {
                None
            }
        })
        .collect();

    let (mock_agent, _call_count) = MockCircuitBreakerAgent::new(responses);

    // Create circuit breaker
    let config = CircuitBreakerConfig::builder()
        .failure_threshold(test_case.config.failure_threshold)
        .recovery_timeout(Duration::from_millis(test_case.config.recovery_timeout_ms))
        .success_threshold(test_case.config.success_threshold)
        .timeout(Duration::from_millis(test_case.config.timeout_ms))
        .build();

    let circuit_breaker = CircuitBreakerMiddleware::new(mock_agent, config);

    // Execute steps
    for step in &test_case.scenario.steps {
        if step.action == "request" {
            let message = Message::new("user", json!("test"));
            let _ = circuit_breaker.process(message).await;
        } else if step.action == "wait" {
            sleep(Duration::from_millis(step.duration_ms.unwrap())).await;
        }
    }

    // Verify expected metrics
    let expected = test_case.expected_metrics.as_ref().unwrap();
    let metrics = circuit_breaker.get_metrics().await;

    assert_eq!(metrics.total_requests, expected.total_requests as u64);
    assert_eq!(
        metrics.successful_requests,
        expected.successful_requests as u64
    );
    assert_eq!(metrics.failed_requests, expected.failed_requests as u64);
    assert_eq!(metrics.rejected_requests, expected.rejected_requests as u64);
    assert_eq!(state_to_string(metrics.current_state), expected.final_state);

    // Assert the state_changes map itself, not just the scalar counters. This field is the
    // cross-language transition-key contract; it went unasserted in all five harnesses long
    // enough for four different key formats to appear (#791).
    let want_changes: HashMap<String, u64> = expected
        .state_changes
        .iter()
        .map(|(k, v)| (k.clone(), *v as u64))
        .collect();
    assert_eq!(metrics.state_changes, want_changes);
}
