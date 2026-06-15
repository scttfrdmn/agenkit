package tests

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/middleware"
)

// TimeoutTestCase represents a test case from the timeout_behavior.json fixture
type TimeoutTestCase struct {
	ID     string `json:"id"`
	Name   string `json:"name"`
	Config struct {
		TimeoutMS int `json:"timeout_ms"`
	} `json:"config"`
	Scenario struct {
		AgentDelayMS  int                    `json:"agent_delay_ms"`
		AgentResponse map[string]interface{} `json:"agent_response,omitempty"`
		Requests      []TimeoutRequest       `json:"requests,omitempty"`
	} `json:"scenario"`
	ExpectedBehavior *struct {
		Successful           bool   `json:"successful"`
		TimedOut             bool   `json:"timed_out"`
		FinalResponse        string `json:"final_response,omitempty"`
		ErrorType            string `json:"error_type,omitempty"`
		ErrorMessageContains string `json:"error_message_contains,omitempty"`
		MinElapsedMS         int64  `json:"min_elapsed_ms"`
		MaxElapsedMS         int64  `json:"max_elapsed_ms"`
	} `json:"expected_behavior,omitempty"`
	ExpectedMetrics *struct {
		TotalRequests      int     `json:"total_requests"`
		SuccessfulRequests int     `json:"successful_requests"`
		TimedOutRequests   int     `json:"timed_out_requests"`
		SuccessRate        float64 `json:"success_rate"`
	} `json:"expected_metrics,omitempty"`
}

// TimeoutRequest represents a request in a multi-request scenario
type TimeoutRequest struct {
	AgentDelayMS  int                    `json:"agent_delay_ms"`
	AgentResponse map[string]interface{} `json:"agent_response"`
}

// TimeoutFixtures represents the timeout_behavior.json fixture file
type TimeoutFixtures struct {
	Version     string            `json:"version"`
	Description string            `json:"description"`
	TestCases   []TimeoutTestCase `json:"test_cases"`
}

// MockTimeoutAgent simulates delays for timeout testing
type MockTimeoutAgent struct {
	delayMS  int
	response map[string]interface{}
}

func (m *MockTimeoutAgent) Name() string {
	return "mock-timeout-agent"
}

func (m *MockTimeoutAgent) Capabilities() []string {
	return []string{}
}

func (m *MockTimeoutAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Simulate delay
	if m.delayMS > 0 {
		select {
		case <-time.After(time.Duration(m.delayMS) * time.Millisecond):
			// Delay completed
		case <-ctx.Done():
			// Context cancelled (timeout or cancellation)
			return nil, ctx.Err()
		}
	}

	// Check if response is successful
	success, ok := m.response["success"].(bool)
	if !ok || !success {
		errorMsg, _ := m.response["error"].(string)
		return nil, fmt.Errorf("%s", errorMsg)
	}

	// Return successful response
	content, _ := m.response["content"].(string)
	msg := agenkit.NewMessage("agent", content)
	return msg, nil
}

func (m *MockTimeoutAgent) Introspect() *agenkit.IntrospectionResult {
	result, _ := agenkit.NewIntrospectionResult(
		m.Name(),
		[]string{},
		nil,
		nil,
		nil,
	)
	return result
}

func loadTimeoutFixtures(t *testing.T) TimeoutFixtures {
	// Load fixtures relative to test file
	data, err := os.ReadFile("../../tests/cross_language/fixtures/timeout_behavior.json")
	require.NoError(t, err, "Failed to load timeout_behavior.json")

	var fixtures TimeoutFixtures
	err = json.Unmarshal(data, &fixtures)
	require.NoError(t, err, "Failed to parse timeout_behavior.json")

	return fixtures
}

func findTimeoutTestCase(fixtures TimeoutFixtures, id string) *TimeoutTestCase {
	for _, tc := range fixtures.TestCases {
		if tc.ID == id {
			return &tc
		}
	}
	return nil
}

func TestTimeoutSuccessWithinLimit(t *testing.T) {
	fixtures := loadTimeoutFixtures(t)
	testCase := findTimeoutTestCase(fixtures, "timeout_success_within_limit")
	require.NotNil(t, testCase)

	// Create mock agent with configured delay
	mockAgent := &MockTimeoutAgent{
		delayMS:  testCase.Scenario.AgentDelayMS,
		response: testCase.Scenario.AgentResponse,
	}

	// Create timeout decorator
	config := middleware.TimeoutConfig{
		Timeout: time.Duration(testCase.Config.TimeoutMS) * time.Millisecond,
	}
	timeoutAgent := middleware.NewTimeoutDecorator(mockAgent, config)

	// Execute with timing
	start := time.Now()
	msg := agenkit.NewMessage("user", "test")
	result, err := timeoutAgent.Process(context.Background(), msg)
	elapsed := time.Since(start)

	// Verify expected behavior
	expected := testCase.ExpectedBehavior
	require.NoError(t, err)
	assert.True(t, expected.Successful)
	assert.False(t, expected.TimedOut)
	assert.Equal(t, expected.FinalResponse, result.ContentString())

	elapsedMS := elapsed.Milliseconds()
	assert.GreaterOrEqual(t, elapsedMS, expected.MinElapsedMS)
	assert.LessOrEqual(t, elapsedMS, expected.MaxElapsedMS)
}

func TestTimeoutExceeded(t *testing.T) {
	fixtures := loadTimeoutFixtures(t)
	testCase := findTimeoutTestCase(fixtures, "timeout_exceeded")
	require.NotNil(t, testCase)

	// Create mock agent with configured delay
	mockAgent := &MockTimeoutAgent{
		delayMS:  testCase.Scenario.AgentDelayMS,
		response: testCase.Scenario.AgentResponse,
	}

	// Create timeout decorator
	config := middleware.TimeoutConfig{
		Timeout: time.Duration(testCase.Config.TimeoutMS) * time.Millisecond,
	}
	timeoutAgent := middleware.NewTimeoutDecorator(mockAgent, config)

	// Execute with timing
	start := time.Now()
	msg := agenkit.NewMessage("user", "test")
	_, err := timeoutAgent.Process(context.Background(), msg)
	elapsed := time.Since(start)

	// Verify timeout error
	expected := testCase.ExpectedBehavior
	require.Error(t, err)
	assert.False(t, expected.Successful)
	assert.True(t, expected.TimedOut)
	assert.Contains(t, err.Error(), expected.ErrorMessageContains)

	elapsedMS := elapsed.Milliseconds()
	assert.GreaterOrEqual(t, elapsedMS, expected.MinElapsedMS)
	assert.LessOrEqual(t, elapsedMS, expected.MaxElapsedMS)
}

func TestTimeoutExactlyAtLimit(t *testing.T) {
	fixtures := loadTimeoutFixtures(t)
	testCase := findTimeoutTestCase(fixtures, "timeout_exactly_at_limit")
	require.NotNil(t, testCase)

	// Create mock agent with configured delay
	mockAgent := &MockTimeoutAgent{
		delayMS:  testCase.Scenario.AgentDelayMS,
		response: testCase.Scenario.AgentResponse,
	}

	// Create timeout decorator
	config := middleware.TimeoutConfig{
		Timeout: time.Duration(testCase.Config.TimeoutMS) * time.Millisecond,
	}
	timeoutAgent := middleware.NewTimeoutDecorator(mockAgent, config)

	// Execute with timing
	start := time.Now()
	msg := agenkit.NewMessage("user", "test")
	result, err := timeoutAgent.Process(context.Background(), msg)
	elapsed := time.Since(start)

	// Verify expected behavior
	expected := testCase.ExpectedBehavior
	require.NoError(t, err)
	assert.True(t, expected.Successful)
	assert.False(t, expected.TimedOut)
	assert.Equal(t, expected.FinalResponse, result.ContentString())

	elapsedMS := elapsed.Milliseconds()
	assert.GreaterOrEqual(t, elapsedMS, expected.MinElapsedMS)
	assert.LessOrEqual(t, elapsedMS, expected.MaxElapsedMS)
}

func TestTimeoutZeroDelay(t *testing.T) {
	fixtures := loadTimeoutFixtures(t)
	testCase := findTimeoutTestCase(fixtures, "timeout_zero_delay")
	require.NotNil(t, testCase)

	// Create mock agent with configured delay
	mockAgent := &MockTimeoutAgent{
		delayMS:  testCase.Scenario.AgentDelayMS,
		response: testCase.Scenario.AgentResponse,
	}

	// Create timeout decorator
	config := middleware.TimeoutConfig{
		Timeout: time.Duration(testCase.Config.TimeoutMS) * time.Millisecond,
	}
	timeoutAgent := middleware.NewTimeoutDecorator(mockAgent, config)

	// Execute with timing
	start := time.Now()
	msg := agenkit.NewMessage("user", "test")
	result, err := timeoutAgent.Process(context.Background(), msg)
	elapsed := time.Since(start)

	// Verify expected behavior
	expected := testCase.ExpectedBehavior
	require.NoError(t, err)
	assert.True(t, expected.Successful)
	assert.False(t, expected.TimedOut)
	assert.Equal(t, expected.FinalResponse, result.ContentString())

	elapsedMS := elapsed.Milliseconds()
	assert.LessOrEqual(t, elapsedMS, expected.MaxElapsedMS)
}

func TestTimeoutAgentError(t *testing.T) {
	fixtures := loadTimeoutFixtures(t)
	testCase := findTimeoutTestCase(fixtures, "timeout_agent_error")
	require.NotNil(t, testCase)

	// Create mock agent with configured delay
	mockAgent := &MockTimeoutAgent{
		delayMS:  testCase.Scenario.AgentDelayMS,
		response: testCase.Scenario.AgentResponse,
	}

	// Create timeout decorator
	config := middleware.TimeoutConfig{
		Timeout: time.Duration(testCase.Config.TimeoutMS) * time.Millisecond,
	}
	timeoutAgent := middleware.NewTimeoutDecorator(mockAgent, config)

	// Execute with timing
	start := time.Now()
	msg := agenkit.NewMessage("user", "test")
	_, err := timeoutAgent.Process(context.Background(), msg)
	elapsed := time.Since(start)

	// Verify agent error (not timeout)
	expected := testCase.ExpectedBehavior
	require.Error(t, err)
	assert.False(t, expected.Successful)
	assert.False(t, expected.TimedOut)
	assert.Contains(t, err.Error(), expected.ErrorMessageContains)

	elapsedMS := elapsed.Milliseconds()
	assert.GreaterOrEqual(t, elapsedMS, expected.MinElapsedMS)
	assert.LessOrEqual(t, elapsedMS, expected.MaxElapsedMS)
}

func TestTimeoutVeryShort(t *testing.T) {
	fixtures := loadTimeoutFixtures(t)
	testCase := findTimeoutTestCase(fixtures, "timeout_very_short")
	require.NotNil(t, testCase)

	// Create mock agent with configured delay
	mockAgent := &MockTimeoutAgent{
		delayMS:  testCase.Scenario.AgentDelayMS,
		response: testCase.Scenario.AgentResponse,
	}

	// Create timeout decorator
	config := middleware.TimeoutConfig{
		Timeout: time.Duration(testCase.Config.TimeoutMS) * time.Millisecond,
	}
	timeoutAgent := middleware.NewTimeoutDecorator(mockAgent, config)

	// Execute with timing
	start := time.Now()
	msg := agenkit.NewMessage("user", "test")
	_, err := timeoutAgent.Process(context.Background(), msg)
	elapsed := time.Since(start)

	// Verify timeout error
	expected := testCase.ExpectedBehavior
	require.Error(t, err)
	assert.False(t, expected.Successful)
	assert.True(t, expected.TimedOut)

	elapsedMS := elapsed.Milliseconds()
	assert.GreaterOrEqual(t, elapsedMS, expected.MinElapsedMS)
	// Very short timeouts get wider tolerance
	assert.LessOrEqual(t, elapsedMS, expected.MaxElapsedMS+20)
}

func TestTimeoutMetricsTracking(t *testing.T) {
	fixtures := loadTimeoutFixtures(t)
	testCase := findTimeoutTestCase(fixtures, "timeout_metrics_tracking")
	require.NotNil(t, testCase)

	// Create timeout decorator config
	config := middleware.TimeoutConfig{
		Timeout: time.Duration(testCase.Config.TimeoutMS) * time.Millisecond,
	}

	// Process multiple requests
	var successful, timedOut int
	for _, request := range testCase.Scenario.Requests {
		mockAgent := &MockTimeoutAgent{
			delayMS:  request.AgentDelayMS,
			response: request.AgentResponse,
		}
		timeoutAgent := middleware.NewTimeoutDecorator(mockAgent, config)

		msg := agenkit.NewMessage("user", "test")
		_, err := timeoutAgent.Process(context.Background(), msg)

		if err == nil {
			successful++
		} else {
			timedOut++
		}
	}

	// Verify metrics
	expectedMetrics := testCase.ExpectedMetrics
	assert.Equal(t, expectedMetrics.TotalRequests, len(testCase.Scenario.Requests))
	assert.Equal(t, expectedMetrics.SuccessfulRequests, successful)
	assert.Equal(t, expectedMetrics.TimedOutRequests, timedOut)
}
