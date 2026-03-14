package tests

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/middleware"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// RetryBehaviorFixtures represents the loaded retry behavior JSON fixtures
type RetryBehaviorFixtures struct {
	Version     string              `json:"version"`
	Description string              `json:"description"`
	TestCases   []RetryBehaviorTest `json:"test_cases"`
}

type RetryBehaviorTest struct {
	ID               string               `json:"id"`
	Name             string               `json:"name"`
	Config           RetryConfigData      `json:"config"`
	Scenario         RetryScenario        `json:"scenario"`
	ExpectedBehavior map[string]any       `json:"expected_behavior,omitempty"`
	ExpectedMetrics  map[string]any       `json:"expected_metrics,omitempty"`
}

type RetryConfigData struct {
	MaxRetries          int     `json:"max_retries"`
	InitialBackoffMs    int     `json:"initial_backoff_ms"`
	MaxBackoffMs        int     `json:"max_backoff_ms"`
	BackoffMultiplier   float64 `json:"backoff_multiplier"`
}

type RetryScenario struct {
	AgentResponses []AgentResponse `json:"agent_responses"`
}

type AgentResponse struct {
	Success bool   `json:"success"`
	Content string `json:"content,omitempty"`
	Error   string `json:"error,omitempty"`
}

// MockRetryAgent simulates agent responses from fixture scenarios
type MockRetryAgent struct {
	Responses []AgentResponse
	CallCount int
}

func (m *MockRetryAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if m.CallCount >= len(m.Responses) {
		return nil, errors.New("no more responses available")
	}

	response := m.Responses[m.CallCount]
	m.CallCount++

	if response.Success {
		return &agenkit.Message{
			Role:    "agent",
			Content: response.Content,
		}, nil
	}

	return nil, errors.New(response.Error)
}

func (m *MockRetryAgent) Name() string {
	return "mock-retry-agent"
}

func (m *MockRetryAgent) Capabilities() []string {
	return []string{}
}

func (m *MockRetryAgent) Introspect() *agenkit.IntrospectionResult {
	result, _ := agenkit.NewIntrospectionResult(
		m.Name(),
		m.Capabilities(),
		nil, // no memory
		map[string]interface{}{
			"call_count": m.CallCount,
		},
		nil, // no metadata
	)
	return result
}

// loadRetryBehaviorFixtures loads retry_behavior.json from tests/cross_language/fixtures
func loadRetryBehaviorFixtures(t *testing.T) *RetryBehaviorFixtures {
	fixturePath := filepath.Join("..", "..", "tests", "cross_language", "fixtures", "retry_behavior.json")
	data, err := os.ReadFile(fixturePath)
	require.NoError(t, err, "Failed to read retry_behavior.json")

	var fixtures RetryBehaviorFixtures
	err = json.Unmarshal(data, &fixtures)
	require.NoError(t, err, "Failed to parse retry_behavior.json")

	return &fixtures
}

func TestRetryBehavior_SuccessFirstAttempt(t *testing.T) {
	fixtures := loadRetryBehaviorFixtures(t)
	testCase := findTestCase(t, fixtures, "retry_success_first_attempt")

	// Create mock agent
	agent := &MockRetryAgent{Responses: testCase.Scenario.AgentResponses}

	// Create retry config
	config := middleware.RetryConfig{
		MaxRetries:          testCase.Config.MaxRetries,
		InitialRetryDelay:   time.Duration(testCase.Config.InitialBackoffMs) * time.Millisecond,
		MaxRetryDelay:       time.Duration(testCase.Config.MaxBackoffMs) * time.Millisecond,
		RetryMultiplier:     testCase.Config.BackoffMultiplier,
	}

	retry := middleware.NewRetryDecorator(agent, config)

	// Execute
	ctx := context.Background()
	msg := &agenkit.Message{Role: "user", Content: "test"}
	response, err := retry.Process(ctx, msg)

	// Verify expected behavior
	require.NoError(t, err)
	assert.Equal(t, int(testCase.ExpectedBehavior["total_attempts"].(float64)), agent.CallCount)
	assert.Equal(t, testCase.ExpectedBehavior["final_response"], response.ContentString())
	assert.True(t, testCase.ExpectedBehavior["successful"].(bool))
}

func TestRetryBehavior_SuccessAfterRetry(t *testing.T) {
	fixtures := loadRetryBehaviorFixtures(t)
	testCase := findTestCase(t, fixtures, "retry_success_second_attempt")

	agent := &MockRetryAgent{Responses: testCase.Scenario.AgentResponses}
	config := middleware.RetryConfig{
		MaxRetries:          testCase.Config.MaxRetries,
		InitialRetryDelay:   time.Duration(testCase.Config.InitialBackoffMs) * time.Millisecond,
		MaxRetryDelay:       time.Duration(testCase.Config.MaxBackoffMs) * time.Millisecond,
		RetryMultiplier:     testCase.Config.BackoffMultiplier,
	}

	retry := middleware.NewRetryDecorator(agent, config)

	// Measure time
	start := time.Now()
	ctx := context.Background()
	msg := &agenkit.Message{Role: "user", Content: "test"}
	response, err := retry.Process(ctx, msg)
	elapsed := time.Since(start).Milliseconds()

	// Verify expected behavior
	require.NoError(t, err)
	assert.Equal(t, int(testCase.ExpectedBehavior["total_attempts"].(float64)), agent.CallCount)
	assert.Equal(t, testCase.ExpectedBehavior["final_response"], response.ContentString())

	// Verify delay within expected range
	minDelay := int64(testCase.ExpectedBehavior["min_total_delay_ms"].(float64))
	maxDelay := int64(testCase.ExpectedBehavior["max_total_delay_ms"].(float64))
	assert.GreaterOrEqual(t, elapsed, minDelay, "Delay too short")
	assert.LessOrEqual(t, elapsed, maxDelay+50, "Delay too long (50ms tolerance)")
}

func TestRetryBehavior_RetriesExhausted(t *testing.T) {
	fixtures := loadRetryBehaviorFixtures(t)
	testCase := findTestCase(t, fixtures, "retry_exhausted")

	agent := &MockRetryAgent{Responses: testCase.Scenario.AgentResponses}
	config := middleware.RetryConfig{
		MaxRetries:          testCase.Config.MaxRetries,
		InitialRetryDelay:   time.Duration(testCase.Config.InitialBackoffMs) * time.Millisecond,
		MaxRetryDelay:       time.Duration(testCase.Config.MaxBackoffMs) * time.Millisecond,
		RetryMultiplier:     testCase.Config.BackoffMultiplier,
	}

	retry := middleware.NewRetryDecorator(agent, config)

	// Should fail after exhausting retries
	ctx := context.Background()
	msg := &agenkit.Message{Role: "user", Content: "test"}
	_, err := retry.Process(ctx, msg)

	// Verify expected behavior
	require.Error(t, err)
	assert.Equal(t, int(testCase.ExpectedBehavior["total_attempts"].(float64)), agent.CallCount)
	assert.False(t, testCase.ExpectedBehavior["successful"].(bool))
}

func TestRetryBehavior_ExponentialBackoff(t *testing.T) {
	fixtures := loadRetryBehaviorFixtures(t)
	testCase := findTestCase(t, fixtures, "retry_exponential_backoff")

	agent := &MockRetryAgent{Responses: testCase.Scenario.AgentResponses}
	config := middleware.RetryConfig{
		MaxRetries:          testCase.Config.MaxRetries,
		InitialRetryDelay:   time.Duration(testCase.Config.InitialBackoffMs) * time.Millisecond,
		MaxRetryDelay:       time.Duration(testCase.Config.MaxBackoffMs) * time.Millisecond,
		RetryMultiplier:     testCase.Config.BackoffMultiplier,
	}

	retry := middleware.NewRetryDecorator(agent, config)

	// Measure time
	start := time.Now()
	ctx := context.Background()
	msg := &agenkit.Message{Role: "user", Content: "test"}
	_, err := retry.Process(ctx, msg)
	elapsed := time.Since(start).Milliseconds()

	// Verify expected behavior
	require.NoError(t, err)
	assert.Equal(t, int(testCase.ExpectedBehavior["total_attempts"].(float64)), agent.CallCount)
	assert.True(t, testCase.ExpectedBehavior["successful"].(bool))

	// Verify exponential backoff timing: 100ms + 200ms + 400ms = 700ms
	minDelay := int64(testCase.ExpectedBehavior["min_total_delay_ms"].(float64))
	maxDelay := int64(testCase.ExpectedBehavior["max_total_delay_ms"].(float64))
	assert.GreaterOrEqual(t, elapsed, minDelay, "Delay too short")
	assert.LessOrEqual(t, elapsed, maxDelay+100, "Delay too long (100ms tolerance)")

	// Verify response
	expectedDelays := testCase.ExpectedBehavior["expected_delays_ms"].([]any)
	t.Logf("Expected delays: %v, Actual total: %dms", expectedDelays, elapsed)
}

func TestRetryBehavior_MaxBackoffCap(t *testing.T) {
	fixtures := loadRetryBehaviorFixtures(t)
	testCase := findTestCase(t, fixtures, "retry_max_backoff_capped")

	agent := &MockRetryAgent{Responses: testCase.Scenario.AgentResponses}
	config := middleware.RetryConfig{
		MaxRetries:          testCase.Config.MaxRetries,
		InitialRetryDelay:   time.Duration(testCase.Config.InitialBackoffMs) * time.Millisecond,
		MaxRetryDelay:       time.Duration(testCase.Config.MaxBackoffMs) * time.Millisecond,
		RetryMultiplier:     testCase.Config.BackoffMultiplier,
	}

	retry := middleware.NewRetryDecorator(agent, config)

	// Measure time
	start := time.Now()
	ctx := context.Background()
	msg := &agenkit.Message{Role: "user", Content: "test"}
	response, err := retry.Process(ctx, msg)
	elapsed := time.Since(start).Milliseconds()

	// Verify expected behavior
	require.NoError(t, err)
	assert.Equal(t, int(testCase.ExpectedBehavior["total_attempts"].(float64)), agent.CallCount)
	assert.True(t, testCase.ExpectedBehavior["successful"].(bool))
	assert.True(t, testCase.ExpectedBehavior["delays_capped"].(bool))

	// Verify capped backoff: 100ms + 200ms (capped) + 200ms + 200ms = 700ms
	minDelay := int64(testCase.ExpectedBehavior["min_total_delay_ms"].(float64))
	maxDelay := int64(testCase.ExpectedBehavior["max_total_delay_ms"].(float64))
	assert.GreaterOrEqual(t, elapsed, minDelay, "Delay too short")
	assert.LessOrEqual(t, elapsed, maxDelay+100, "Delay too long (100ms tolerance)")

	// Verify response
	assert.Equal(t, "Success", response.ContentString())
}

func TestRetryBehavior_NonRetryableError(t *testing.T) {
	fixtures := loadRetryBehaviorFixtures(t)
	testCase := findTestCase(t, fixtures, "retry_non_retryable_error")

	agent := &MockRetryAgent{Responses: testCase.Scenario.AgentResponses}

	// Define should retry predicate
	shouldRetry := func(err error) bool {
		return err != nil && err.Error() != "InvalidInput"
	}

	config := middleware.RetryConfig{
		MaxRetries:          testCase.Config.MaxRetries,
		InitialRetryDelay:   time.Duration(testCase.Config.InitialBackoffMs) * time.Millisecond,
		MaxRetryDelay:       time.Duration(testCase.Config.MaxBackoffMs) * time.Millisecond,
		RetryMultiplier:     testCase.Config.BackoffMultiplier,
		ShouldRetry:         shouldRetry,
	}

	retry := middleware.NewRetryDecorator(agent, config)

	// Should fail immediately without retrying
	ctx := context.Background()
	msg := &agenkit.Message{Role: "user", Content: "test"}
	_, err := retry.Process(ctx, msg)

	// Verify expected behavior
	require.Error(t, err)
	assert.Equal(t, int(testCase.ExpectedBehavior["total_attempts"].(float64)), agent.CallCount)
	assert.False(t, testCase.ExpectedBehavior["successful"].(bool))
	assert.True(t, testCase.ExpectedBehavior["should_not_retry"].(bool))
}

func TestRetryBehavior_MetricsTracking(t *testing.T) {
	fixtures := loadRetryBehaviorFixtures(t)
	testCase := findTestCase(t, fixtures, "retry_metrics_tracking")

	agent := &MockRetryAgent{Responses: testCase.Scenario.AgentResponses}
	config := middleware.RetryConfig{
		MaxRetries:          testCase.Config.MaxRetries,
		InitialRetryDelay:   time.Duration(testCase.Config.InitialBackoffMs) * time.Millisecond,
		MaxRetryDelay:       time.Duration(testCase.Config.MaxBackoffMs) * time.Millisecond,
		RetryMultiplier:     testCase.Config.BackoffMultiplier,
	}

	retry := middleware.NewRetryDecorator(agent, config)

	// Execute request (fails once, then succeeds)
	ctx := context.Background()
	msg := &agenkit.Message{Role: "user", Content: "test"}
	response, err := retry.Process(ctx, msg)

	// Verify success
	require.NoError(t, err)
	assert.Equal(t, "Success", response.ContentString())

	// Verify metrics
	expected := testCase.ExpectedMetrics
	metrics := retry.Metrics()

	assert.Equal(t, int64(expected["total_attempts"].(float64)), metrics.TotalAttempts)
	assert.Equal(t, int64(expected["successful_first_attempt"].(float64)), metrics.SuccessfulFirstAttempt)
	assert.Equal(t, int64(expected["successful_on_retry"].(float64)), metrics.SuccessfulOnRetry)
}

// Helper function to find a test case by ID
func findTestCase(t *testing.T, fixtures *RetryBehaviorFixtures, id string) RetryBehaviorTest {
	for _, tc := range fixtures.TestCases {
		if tc.ID == id {
			return tc
		}
	}
	t.Fatalf("Test case not found: %s", id)
	return RetryBehaviorTest{}
}
