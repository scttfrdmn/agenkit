package tests

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/middleware"
)

// CircuitBreakerTestCase represents a test case from the circuit_breaker_behavior.json fixture
type CircuitBreakerTestCase struct {
	ID     string `json:"id"`
	Name   string `json:"name"`
	Config struct {
		FailureThreshold  int `json:"failure_threshold"`
		RecoveryTimeoutMS int `json:"recovery_timeout_ms"`
		SuccessThreshold  int `json:"success_threshold"`
		TimeoutMS         int `json:"timeout_ms"`
	} `json:"config"`
	Scenario struct {
		AgentResponses []map[string]interface{} `json:"agent_responses,omitempty"`
		Steps          []CircuitBreakerStep     `json:"steps,omitempty"`
	} `json:"scenario"`
	ExpectedBehavior *struct {
		FinalState                   string   `json:"final_state"`
		TotalRequests                int      `json:"total_requests,omitempty"`
		SuccessfulRequests           int      `json:"successful_requests,omitempty"`
		FailedRequests               int      `json:"failed_requests,omitempty"`
		RejectedRequests             int      `json:"rejected_requests,omitempty"`
		AllRequestsCompleted         bool     `json:"all_requests_completed,omitempty"`
		StateTransitions             []string `json:"state_transitions,omitempty"`
		FourthRequestRejected        bool     `json:"fourth_request_rejected,omitempty"`
		RecoverySuccessful           bool     `json:"recovery_successful,omitempty"`
		TotalSuccessfulInHalfOpen    int      `json:"total_successful_in_half_open,omitempty"`
		CircuitFullyRecovered        bool     `json:"circuit_fully_recovered,omitempty"`
		ReopenedAfterPartialRecovery bool     `json:"reopened_after_partial_recovery,omitempty"`
		AllRejectedWhileOpen         bool     `json:"all_rejected_while_open,omitempty"`
	} `json:"expected_behavior,omitempty"`
	ExpectedMetrics *struct {
		TotalRequests      int            `json:"total_requests"`
		SuccessfulRequests int            `json:"successful_requests"`
		FailedRequests     int            `json:"failed_requests"`
		RejectedRequests   int            `json:"rejected_requests"`
		StateChanges       map[string]int `json:"state_changes"`
		FinalState         string         `json:"final_state"`
	} `json:"expected_metrics,omitempty"`
}

// CircuitBreakerStep represents a step in a multi-step scenario
type CircuitBreakerStep struct {
	Action        string                 `json:"action"`
	AgentResponse map[string]interface{} `json:"agent_response,omitempty"`
	DurationMS    int                    `json:"duration_ms,omitempty"`
}

// CircuitBreakerFixtures represents the circuit_breaker_behavior.json fixture file
type CircuitBreakerFixtures struct {
	Version     string                   `json:"version"`
	Description string                   `json:"description"`
	TestCases   []CircuitBreakerTestCase `json:"test_cases"`
}

// MockCircuitBreakerAgent simulates responses for circuit breaker testing
type MockCircuitBreakerAgent struct {
	responses []map[string]interface{}
	callCount int
}

func (m *MockCircuitBreakerAgent) Name() string {
	return "mock-circuit-breaker-agent"
}

func (m *MockCircuitBreakerAgent) Capabilities() []string {
	return []string{}
}

func (m *MockCircuitBreakerAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if m.callCount >= len(m.responses) {
		return nil, fmt.Errorf("no more responses available")
	}

	response := m.responses[m.callCount]
	m.callCount++

	success, ok := response["success"].(bool)
	if !ok || !success {
		errorMsg, _ := response["error"].(string)
		return nil, fmt.Errorf("%s", errorMsg)
	}

	content, _ := response["content"].(string)
	return agenkit.NewMessage("agent", content), nil
}

func (m *MockCircuitBreakerAgent) Introspect() *agenkit.IntrospectionResult {
	result, _ := agenkit.NewIntrospectionResult(
		m.Name(),
		[]string{},
		nil,
		nil,
		nil,
	)
	return result
}

func loadCircuitBreakerFixtures(t *testing.T) CircuitBreakerFixtures {
	data, err := os.ReadFile("../../tests/cross_language/fixtures/circuit_breaker_behavior.json")
	require.NoError(t, err, "Failed to load circuit_breaker_behavior.json")

	var fixtures CircuitBreakerFixtures
	err = json.Unmarshal(data, &fixtures)
	require.NoError(t, err, "Failed to parse circuit_breaker_behavior.json")

	return fixtures
}

func findCircuitBreakerTestCase(fixtures CircuitBreakerFixtures, id string) *CircuitBreakerTestCase {
	for _, tc := range fixtures.TestCases {
		if tc.ID == id {
			return &tc
		}
	}
	return nil
}

func TestCircuitBreakerClosedSuccess(t *testing.T) {
	fixtures := loadCircuitBreakerFixtures(t)
	testCase := findCircuitBreakerTestCase(fixtures, "circuit_breaker_closed_success")
	require.NotNil(t, testCase)

	// Create mock agent
	mockAgent := &MockCircuitBreakerAgent{
		responses: testCase.Scenario.AgentResponses,
	}

	// Create circuit breaker
	config := middleware.CircuitBreakerConfig{
		FailureThreshold: testCase.Config.FailureThreshold,
		RecoveryTimeout:  time.Duration(testCase.Config.RecoveryTimeoutMS) * time.Millisecond,
		SuccessThreshold: testCase.Config.SuccessThreshold,
		Timeout:          time.Duration(testCase.Config.TimeoutMS) * time.Millisecond,
	}
	circuitBreaker := middleware.NewCircuitBreakerDecorator(mockAgent, config)

	// Execute requests
	successful := 0
	for i := 0; i < len(testCase.Scenario.AgentResponses); i++ {
		msg := agenkit.NewMessage("user", "test")
		_, err := circuitBreaker.Process(context.Background(), msg)
		if err == nil {
			successful++
		}
	}

	// Verify expected behavior
	expected := testCase.ExpectedBehavior
	metrics := circuitBreaker.Metrics()

	assert.Equal(t, "closed", circuitBreaker.State().String())
	assert.Equal(t, int64(expected.TotalRequests), metrics.TotalRequests)
	assert.Equal(t, int64(expected.SuccessfulRequests), metrics.SuccessfulRequests)
	assert.Equal(t, int64(expected.FailedRequests), metrics.FailedRequests)
	assert.Equal(t, int64(expected.RejectedRequests), metrics.RejectedRequests)
	assert.Equal(t, expected.TotalRequests, successful)
}

func TestCircuitBreakerOpensOnFailures(t *testing.T) {
	fixtures := loadCircuitBreakerFixtures(t)
	testCase := findCircuitBreakerTestCase(fixtures, "circuit_breaker_opens_on_failures")
	require.NotNil(t, testCase)

	// Create mock agent
	mockAgent := &MockCircuitBreakerAgent{
		responses: testCase.Scenario.AgentResponses,
	}

	// Create circuit breaker
	config := middleware.CircuitBreakerConfig{
		FailureThreshold: testCase.Config.FailureThreshold,
		RecoveryTimeout:  time.Duration(testCase.Config.RecoveryTimeoutMS) * time.Millisecond,
		SuccessThreshold: testCase.Config.SuccessThreshold,
		Timeout:          time.Duration(testCase.Config.TimeoutMS) * time.Millisecond,
	}
	circuitBreaker := middleware.NewCircuitBreakerDecorator(mockAgent, config)

	// Execute requests, recording each outcome so per-request claims can be checked
	rejected := 0
	outcomes := make([]string, 0, len(testCase.Scenario.AgentResponses))
	for i := 0; i < len(testCase.Scenario.AgentResponses); i++ {
		msg := agenkit.NewMessage("user", "test")
		_, err := circuitBreaker.Process(context.Background(), msg)
		switch {
		case err == nil:
			outcomes = append(outcomes, "ok")
		case errors.As(err, new(*middleware.CircuitBreakerError)):
			rejected++
			outcomes = append(outcomes, "rejected")
		default:
			outcomes = append(outcomes, "failed")
		}
	}

	// Verify expected behavior
	expected := testCase.ExpectedBehavior
	metrics := circuitBreaker.Metrics()

	assert.Equal(t, "open", circuitBreaker.State().String())
	assert.Equal(t, int64(expected.TotalRequests), metrics.TotalRequests)
	assert.Equal(t, int64(expected.FailedRequests), metrics.FailedRequests)
	assert.Equal(t, int64(expected.RejectedRequests), metrics.RejectedRequests)

	// `assert.True(t, expected.FourthRequestRejected)` was a tautology: it asserted a
	// `true` literal read out of the fixture, so it passed with the middleware deleted
	// (#791). Check the actual claim — the fourth request was rejected by the open
	// circuit, not merely failed by the inner agent (whose fourth scripted response is a
	// success).
	if expected.FourthRequestRejected {
		require.Len(t, outcomes, 4)
		assert.Equal(t, "rejected", outcomes[3], "expected 4th request rejected, got %v", outcomes)
	}
}

func TestCircuitBreakerHalfOpenTransition(t *testing.T) {
	fixtures := loadCircuitBreakerFixtures(t)
	testCase := findCircuitBreakerTestCase(fixtures, "circuit_breaker_half_open_transition")
	require.NotNil(t, testCase)

	// Extract responses from steps
	var responses []map[string]interface{}
	for _, step := range testCase.Scenario.Steps {
		if step.Action == "request" {
			responses = append(responses, step.AgentResponse)
		}
	}

	mockAgent := &MockCircuitBreakerAgent{
		responses: responses,
	}

	// Create circuit breaker
	config := middleware.CircuitBreakerConfig{
		FailureThreshold: testCase.Config.FailureThreshold,
		RecoveryTimeout:  time.Duration(testCase.Config.RecoveryTimeoutMS) * time.Millisecond,
		SuccessThreshold: testCase.Config.SuccessThreshold,
		Timeout:          time.Duration(testCase.Config.TimeoutMS) * time.Millisecond,
	}
	circuitBreaker := middleware.NewCircuitBreakerDecorator(mockAgent, config)

	// Execute steps
	for _, step := range testCase.Scenario.Steps {
		if step.Action == "request" {
			msg := agenkit.NewMessage("user", "test")
			_, _ = circuitBreaker.Process(context.Background(), msg)
		} else if step.Action == "wait" {
			time.Sleep(time.Duration(step.DurationMS) * time.Millisecond)
		}
	}

	// Verify expected behavior
	expected := testCase.ExpectedBehavior
	assert.Equal(t, expected.FinalState, circuitBreaker.State().String())

	// `assert.True(t, expected.RecoverySuccessful)` was a tautology (#791). The real
	// claim is that the circuit opened, then recovered *through* half-open — a breaker
	// that never opened at all would also end "closed" and pass the final-state check.
	if expected.RecoverySuccessful {
		changes := circuitBreaker.Metrics().StateChanges
		assert.GreaterOrEqual(t, changes["closed->open"], int64(1), "never opened: %v", changes)
		assert.GreaterOrEqual(t, changes["open->half_open"], int64(1), "never probed half-open: %v", changes)
		assert.GreaterOrEqual(t, changes["half_open->closed"], int64(1), "never closed from half-open: %v", changes)
	}
}

func TestCircuitBreakerHalfOpenToClosed(t *testing.T) {
	fixtures := loadCircuitBreakerFixtures(t)
	testCase := findCircuitBreakerTestCase(fixtures, "circuit_breaker_half_open_to_closed")
	require.NotNil(t, testCase)

	// Extract responses from steps
	var responses []map[string]interface{}
	for _, step := range testCase.Scenario.Steps {
		if step.Action == "request" {
			responses = append(responses, step.AgentResponse)
		}
	}

	mockAgent := &MockCircuitBreakerAgent{
		responses: responses,
	}

	// Create circuit breaker
	config := middleware.CircuitBreakerConfig{
		FailureThreshold: testCase.Config.FailureThreshold,
		RecoveryTimeout:  time.Duration(testCase.Config.RecoveryTimeoutMS) * time.Millisecond,
		SuccessThreshold: testCase.Config.SuccessThreshold,
		Timeout:          time.Duration(testCase.Config.TimeoutMS) * time.Millisecond,
	}
	circuitBreaker := middleware.NewCircuitBreakerDecorator(mockAgent, config)

	// Execute steps
	for _, step := range testCase.Scenario.Steps {
		if step.Action == "request" {
			msg := agenkit.NewMessage("user", "test")
			_, _ = circuitBreaker.Process(context.Background(), msg)
		} else if step.Action == "wait" {
			time.Sleep(time.Duration(step.DurationMS) * time.Millisecond)
		}
	}

	// Verify expected behavior
	expected := testCase.ExpectedBehavior
	assert.Equal(t, expected.FinalState, circuitBreaker.State().String())

	// `assert.True(t, expected.CircuitFullyRecovered)` was a tautology (#791). Check the
	// real claim: the circuit did close from half-open rather than skipping that probe.
	if expected.CircuitFullyRecovered {
		changes := circuitBreaker.Metrics().StateChanges
		assert.GreaterOrEqual(t, changes["open->half_open"], int64(1), "never probed half-open: %v", changes)
		assert.GreaterOrEqual(t, changes["half_open->closed"], int64(1), "never closed from half-open: %v", changes)
	}
}

func TestCircuitBreakerHalfOpenReopens(t *testing.T) {
	fixtures := loadCircuitBreakerFixtures(t)
	testCase := findCircuitBreakerTestCase(fixtures, "circuit_breaker_half_open_reopens")
	require.NotNil(t, testCase)

	// Extract responses from steps
	var responses []map[string]interface{}
	for _, step := range testCase.Scenario.Steps {
		if step.Action == "request" {
			responses = append(responses, step.AgentResponse)
		}
	}

	mockAgent := &MockCircuitBreakerAgent{
		responses: responses,
	}

	// Create circuit breaker
	config := middleware.CircuitBreakerConfig{
		FailureThreshold: testCase.Config.FailureThreshold,
		RecoveryTimeout:  time.Duration(testCase.Config.RecoveryTimeoutMS) * time.Millisecond,
		SuccessThreshold: testCase.Config.SuccessThreshold,
		Timeout:          time.Duration(testCase.Config.TimeoutMS) * time.Millisecond,
	}
	circuitBreaker := middleware.NewCircuitBreakerDecorator(mockAgent, config)

	// Execute steps
	for _, step := range testCase.Scenario.Steps {
		if step.Action == "request" {
			msg := agenkit.NewMessage("user", "test")
			_, _ = circuitBreaker.Process(context.Background(), msg)
		} else if step.Action == "wait" {
			time.Sleep(time.Duration(step.DurationMS) * time.Millisecond)
		}
	}

	// Verify expected behavior
	expected := testCase.ExpectedBehavior
	assert.Equal(t, expected.FinalState, circuitBreaker.State().String())

	// `assert.True(t, expected.ReopenedAfterPartialRecovery)` was a tautology (#791). The
	// real claim is the full path closed -> open -> half_open -> open: a breaker that
	// opened once and never probed would also end "open" and pass the final-state check.
	if expected.ReopenedAfterPartialRecovery {
		changes := circuitBreaker.Metrics().StateChanges
		assert.GreaterOrEqual(t, changes["closed->open"], int64(1), "never opened: %v", changes)
		assert.GreaterOrEqual(t, changes["open->half_open"], int64(1), "never probed half-open: %v", changes)
		assert.GreaterOrEqual(t, changes["half_open->open"], int64(1), "never reopened from half-open: %v", changes)
	}
}

func TestCircuitBreakerRejectsWhenOpen(t *testing.T) {
	fixtures := loadCircuitBreakerFixtures(t)
	testCase := findCircuitBreakerTestCase(fixtures, "circuit_breaker_rejects_when_open")
	require.NotNil(t, testCase)

	// Create mock agent
	mockAgent := &MockCircuitBreakerAgent{
		responses: testCase.Scenario.AgentResponses,
	}

	// Create circuit breaker
	config := middleware.CircuitBreakerConfig{
		FailureThreshold: testCase.Config.FailureThreshold,
		RecoveryTimeout:  time.Duration(testCase.Config.RecoveryTimeoutMS) * time.Millisecond,
		SuccessThreshold: testCase.Config.SuccessThreshold,
		Timeout:          time.Duration(testCase.Config.TimeoutMS) * time.Millisecond,
	}
	circuitBreaker := middleware.NewCircuitBreakerDecorator(mockAgent, config)

	// Execute requests
	rejected := 0
	for i := 0; i < len(testCase.Scenario.AgentResponses); i++ {
		msg := agenkit.NewMessage("user", "test")
		_, err := circuitBreaker.Process(context.Background(), msg)
		if err != nil {
			if _, ok := err.(*middleware.CircuitBreakerError); ok {
				rejected++
			}
		}
	}

	// Verify expected behavior
	expected := testCase.ExpectedBehavior
	metrics := circuitBreaker.Metrics()

	assert.Equal(t, expected.FinalState, circuitBreaker.State().String())
	assert.Equal(t, int64(expected.RejectedRequests), metrics.RejectedRequests)
	assert.Equal(t, expected.RejectedRequests, rejected)
}

func TestCircuitBreakerMetricsTracking(t *testing.T) {
	fixtures := loadCircuitBreakerFixtures(t)
	testCase := findCircuitBreakerTestCase(fixtures, "circuit_breaker_metrics_tracking")
	require.NotNil(t, testCase)

	// Extract responses from steps
	var responses []map[string]interface{}
	for _, step := range testCase.Scenario.Steps {
		if step.Action == "request" {
			responses = append(responses, step.AgentResponse)
		}
	}

	mockAgent := &MockCircuitBreakerAgent{
		responses: responses,
	}

	// Create circuit breaker
	config := middleware.CircuitBreakerConfig{
		FailureThreshold: testCase.Config.FailureThreshold,
		RecoveryTimeout:  time.Duration(testCase.Config.RecoveryTimeoutMS) * time.Millisecond,
		SuccessThreshold: testCase.Config.SuccessThreshold,
		Timeout:          time.Duration(testCase.Config.TimeoutMS) * time.Millisecond,
	}
	circuitBreaker := middleware.NewCircuitBreakerDecorator(mockAgent, config)

	// Execute steps
	for _, step := range testCase.Scenario.Steps {
		if step.Action == "request" {
			msg := agenkit.NewMessage("user", "test")
			_, _ = circuitBreaker.Process(context.Background(), msg)
		} else if step.Action == "wait" {
			time.Sleep(time.Duration(step.DurationMS) * time.Millisecond)
		}
	}

	// Verify expected metrics
	expected := testCase.ExpectedMetrics
	metrics := circuitBreaker.Metrics()

	assert.Equal(t, int64(expected.TotalRequests), metrics.TotalRequests)
	assert.Equal(t, int64(expected.SuccessfulRequests), metrics.SuccessfulRequests)
	assert.Equal(t, int64(expected.FailedRequests), metrics.FailedRequests)
	assert.Equal(t, int64(expected.RejectedRequests), metrics.RejectedRequests)
	assert.Equal(t, expected.FinalState, circuitBreaker.State().String())

	// Assert the StateChanges map itself, not just the scalar counters. This field is the
	// cross-language transition-key contract; it went unasserted in all five harnesses
	// long enough for four different key formats to appear (#791).
	wantChanges := make(map[string]int64, len(expected.StateChanges))
	for k, v := range expected.StateChanges {
		wantChanges[k] = int64(v)
	}
	assert.Equal(t, wantChanges, metrics.StateChanges)
}
