package tests

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/middleware"
	"github.com/stretchr/testify/require"
)

// MockRateLimiterAgent is a mock agent for rate limiter testing.
type MockRateLimiterAgent struct {
	callCount int
}

// Verify that MockRateLimiterAgent implements Agent interface.
var _ agenkit.Agent = (*MockRateLimiterAgent)(nil)

func (m *MockRateLimiterAgent) Name() string {
	return "mock-rate-limiter-agent"
}

func (m *MockRateLimiterAgent) Capabilities() []string {
	return []string{}
}

func (m *MockRateLimiterAgent) Introspect() *agenkit.IntrospectionResult {
	result, _ := agenkit.NewIntrospectionResult(
		m.Name(),
		[]string{},
		nil, // memoryState
		nil, // internalState
		nil, // metadata
	)
	return result
}

func (m *MockRateLimiterAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	m.callCount++
	return &agenkit.Message{
		Role:    "agent",
		Content: fmt.Sprintf("Response %d", m.callCount),
	}, nil
}

// RateLimiterTestCase represents a rate limiter test case from fixtures.
type RateLimiterTestCase struct {
	ID       string `json:"id"`
	Name     string `json:"name"`
	Config   struct {
		Rate             float64  `json:"rate"`
		Capacity         int      `json:"capacity"`
		TokensPerRequest int      `json:"tokens_per_request"`
		MaxWaitMs        *int     `json:"max_wait_ms"`
	} `json:"config"`
	Scenario struct {
		Requests []struct {
			DelayMs int `json:"delay_ms"`
		} `json:"requests,omitempty"`
		Steps []struct {
			Action     string `json:"action"`
			DurationMs int    `json:"duration_ms,omitempty"`
		} `json:"steps,omitempty"`
	} `json:"scenario"`
	ExpectedBehavior *struct {
		AllSuccessful        bool `json:"all_successful"`
		TotalRequests        int  `json:"total_requests"`
		AllowedRequests      int  `json:"allowed_requests"`
		RejectedRequests     int  `json:"rejected_requests"`
		MinTotalTimeMs       int  `json:"min_total_time_ms,omitempty"`
		MaxTotalTimeMs       int  `json:"max_total_time_ms,omitempty"`
		SixthRequestWaited   bool `json:"sixth_request_waited,omitempty"`
		MinWaitTimeMs        int  `json:"min_wait_time_ms,omitempty"`
		MaxWaitTimeMs        int  `json:"max_wait_time_ms,omitempty"`
		ThirdRequestRejected bool `json:"third_request_rejected,omitempty"`
		TokensRefilled       bool `json:"tokens_refilled,omitempty"`
		BurstHandled         bool `json:"burst_handled,omitempty"`
	} `json:"expected_behavior,omitempty"`
	ExpectedMetrics *struct {
		TotalRequests           int `json:"total_requests"`
		AllowedRequests         int `json:"allowed_requests"`
		RejectedRequests        int `json:"rejected_requests"`
		TotalWaitTimeGreaterThan int `json:"total_wait_time_greater_than"`
	} `json:"expected_metrics,omitempty"`
}

// RateLimiterFixtures represents the rate limiter test fixtures file.
type RateLimiterFixtures struct {
	Version     string                    `json:"version"`
	Description string                    `json:"description"`
	TestCases   []RateLimiterTestCase     `json:"test_cases"`
}

func loadRateLimiterFixtures(t *testing.T) *RateLimiterFixtures {
	fixturesPath := filepath.Join("..", "..", "tests", "cross_language", "fixtures", "rate_limiter_behavior.json")
	data, err := os.ReadFile(fixturesPath)
	require.NoError(t, err, "Failed to read fixtures file")

	var fixtures RateLimiterFixtures
	err = json.Unmarshal(data, &fixtures)
	require.NoError(t, err, "Failed to parse fixtures JSON")

	return &fixtures
}

func findRateLimiterTestCase(fixtures *RateLimiterFixtures, testID string) *RateLimiterTestCase {
	for i := range fixtures.TestCases {
		if fixtures.TestCases[i].ID == testID {
			return &fixtures.TestCases[i]
		}
	}
	return nil
}

func TestRateLimiterAllowsWithinCapacity(t *testing.T) {
	fixtures := loadRateLimiterFixtures(t)
	testCase := findRateLimiterTestCase(fixtures, "rate_limiter_allows_within_capacity")
	require.NotNil(t, testCase, "Test case not found")

	// Create mock agent
	mockAgent := &MockRateLimiterAgent{}

	// Create rate limiter
	var maxWaitTimeout time.Duration
	if testCase.Config.MaxWaitMs != nil {
		maxWaitTimeout = time.Duration(*testCase.Config.MaxWaitMs) * time.Millisecond
	}

	config := middleware.RateLimiterConfig{
		Rate:             testCase.Config.Rate,
		Capacity:         testCase.Config.Capacity,
		TokensPerRequest: testCase.Config.TokensPerRequest,
		MaxWaitTimeout:   maxWaitTimeout,
	}
	rateLimiter := middleware.NewRateLimiterDecorator(mockAgent, config)

	// Execute requests
	start := time.Now()
	successful := 0
	for range testCase.Scenario.Requests {
		msg := &agenkit.Message{Role: "user", Content: "test"}
		_, err := rateLimiter.Process(context.Background(), msg)
		if err == nil {
			successful++
		}
	}
	elapsed := time.Since(start)

	// Verify expected behavior
	expected := testCase.ExpectedBehavior
	require.True(t, expected.AllSuccessful)

	metrics := rateLimiter.Metrics()
	require.Equal(t, int64(expected.TotalRequests), metrics.TotalRequests)
	require.Equal(t, int64(expected.AllowedRequests), metrics.AllowedRequests)
	require.Equal(t, int64(expected.RejectedRequests), metrics.RejectedRequests)
	require.Equal(t, expected.TotalRequests, successful)

	elapsedMs := int(elapsed.Milliseconds())
	require.GreaterOrEqual(t, elapsedMs, expected.MinTotalTimeMs)
	require.LessOrEqual(t, elapsedMs, expected.MaxTotalTimeMs)
}

func TestRateLimiterWaitsForTokens(t *testing.T) {
	fixtures := loadRateLimiterFixtures(t)
	testCase := findRateLimiterTestCase(fixtures, "rate_limiter_waits_for_tokens")
	require.NotNil(t, testCase, "Test case not found")

	// Create mock agent
	mockAgent := &MockRateLimiterAgent{}

	// Create rate limiter
	var maxWaitTimeout time.Duration
	if testCase.Config.MaxWaitMs != nil {
		maxWaitTimeout = time.Duration(*testCase.Config.MaxWaitMs) * time.Millisecond
	}

	config := middleware.RateLimiterConfig{
		Rate:             testCase.Config.Rate,
		Capacity:         testCase.Config.Capacity,
		TokensPerRequest: testCase.Config.TokensPerRequest,
		MaxWaitTimeout:   maxWaitTimeout,
	}
	rateLimiter := middleware.NewRateLimiterDecorator(mockAgent, config)

	// Execute requests and track timing
	var waitTimes []time.Duration
	for range testCase.Scenario.Requests {
		msg := &agenkit.Message{Role: "user", Content: "test"}
		start := time.Now()
		_, err := rateLimiter.Process(context.Background(), msg)
		require.NoError(t, err)
		elapsed := time.Since(start)
		waitTimes = append(waitTimes, elapsed)
	}

	// Verify expected behavior
	expected := testCase.ExpectedBehavior
	require.True(t, expected.AllSuccessful)

	metrics := rateLimiter.Metrics()
	require.Equal(t, int64(expected.TotalRequests), metrics.TotalRequests)
	require.Equal(t, int64(expected.AllowedRequests), metrics.AllowedRequests)
	require.Equal(t, int64(expected.RejectedRequests), metrics.RejectedRequests)
	require.True(t, expected.SixthRequestWaited)

	// Sixth request (index 5) should have waited
	sixthWaitMs := int(waitTimes[5].Milliseconds())
	require.GreaterOrEqual(t, sixthWaitMs, expected.MinWaitTimeMs)
	require.LessOrEqual(t, sixthWaitMs, expected.MaxWaitTimeMs)
}

func TestRateLimiterRejectsOnTimeout(t *testing.T) {
	fixtures := loadRateLimiterFixtures(t)
	testCase := findRateLimiterTestCase(fixtures, "rate_limiter_rejects_on_timeout")
	require.NotNil(t, testCase, "Test case not found")

	// Create mock agent
	mockAgent := &MockRateLimiterAgent{}

	// Create rate limiter
	var maxWaitTimeout time.Duration
	if testCase.Config.MaxWaitMs != nil {
		maxWaitTimeout = time.Duration(*testCase.Config.MaxWaitMs) * time.Millisecond
	}

	config := middleware.RateLimiterConfig{
		Rate:             testCase.Config.Rate,
		Capacity:         testCase.Config.Capacity,
		TokensPerRequest: testCase.Config.TokensPerRequest,
		MaxWaitTimeout:   maxWaitTimeout,
	}
	rateLimiter := middleware.NewRateLimiterDecorator(mockAgent, config)

	// Execute requests
	rejected := 0
	for range testCase.Scenario.Requests {
		msg := &agenkit.Message{Role: "user", Content: "test"}
		_, err := rateLimiter.Process(context.Background(), msg)
		if err != nil {
			rejected++
		}
	}

	// Verify expected behavior
	expected := testCase.ExpectedBehavior
	require.False(t, expected.AllSuccessful)

	metrics := rateLimiter.Metrics()
	require.Equal(t, int64(expected.TotalRequests), metrics.TotalRequests)
	require.Equal(t, int64(expected.AllowedRequests), metrics.AllowedRequests)
	require.Equal(t, int64(expected.RejectedRequests), metrics.RejectedRequests)
	require.Equal(t, expected.RejectedRequests, rejected)
	require.True(t, expected.ThirdRequestRejected)
}

func TestRateLimiterTokenRefill(t *testing.T) {
	fixtures := loadRateLimiterFixtures(t)
	testCase := findRateLimiterTestCase(fixtures, "rate_limiter_token_refill")
	require.NotNil(t, testCase, "Test case not found")

	// Create mock agent
	mockAgent := &MockRateLimiterAgent{}

	// Create rate limiter
	var maxWaitTimeout time.Duration
	if testCase.Config.MaxWaitMs != nil {
		maxWaitTimeout = time.Duration(*testCase.Config.MaxWaitMs) * time.Millisecond
	}

	config := middleware.RateLimiterConfig{
		Rate:             testCase.Config.Rate,
		Capacity:         testCase.Config.Capacity,
		TokensPerRequest: testCase.Config.TokensPerRequest,
		MaxWaitTimeout:   maxWaitTimeout,
	}
	rateLimiter := middleware.NewRateLimiterDecorator(mockAgent, config)

	// Execute steps
	for _, step := range testCase.Scenario.Steps {
		if step.Action == "request" {
			msg := &agenkit.Message{Role: "user", Content: "test"}
			_, err := rateLimiter.Process(context.Background(), msg)
			require.NoError(t, err)
		} else if step.Action == "wait" {
			time.Sleep(time.Duration(step.DurationMs) * time.Millisecond)
		}
	}

	// Verify expected behavior
	expected := testCase.ExpectedBehavior
	require.True(t, expected.AllSuccessful)

	metrics := rateLimiter.Metrics()
	require.Equal(t, int64(expected.TotalRequests), metrics.TotalRequests)
	require.Equal(t, int64(expected.AllowedRequests), metrics.AllowedRequests)
	require.Equal(t, int64(expected.RejectedRequests), metrics.RejectedRequests)
	require.True(t, expected.TokensRefilled)
}

func TestRateLimiterBurstCapacity(t *testing.T) {
	fixtures := loadRateLimiterFixtures(t)
	testCase := findRateLimiterTestCase(fixtures, "rate_limiter_burst_capacity")
	require.NotNil(t, testCase, "Test case not found")

	// Create mock agent
	mockAgent := &MockRateLimiterAgent{}

	// Create rate limiter
	var maxWaitTimeout time.Duration
	if testCase.Config.MaxWaitMs != nil {
		maxWaitTimeout = time.Duration(*testCase.Config.MaxWaitMs) * time.Millisecond
	}

	config := middleware.RateLimiterConfig{
		Rate:             testCase.Config.Rate,
		Capacity:         testCase.Config.Capacity,
		TokensPerRequest: testCase.Config.TokensPerRequest,
		MaxWaitTimeout:   maxWaitTimeout,
	}
	rateLimiter := middleware.NewRateLimiterDecorator(mockAgent, config)

	// Execute burst of requests
	start := time.Now()
	for range testCase.Scenario.Requests {
		msg := &agenkit.Message{Role: "user", Content: "test"}
		_, err := rateLimiter.Process(context.Background(), msg)
		require.NoError(t, err)
	}
	elapsed := time.Since(start)

	// Verify expected behavior
	expected := testCase.ExpectedBehavior
	require.True(t, expected.AllSuccessful)

	metrics := rateLimiter.Metrics()
	require.Equal(t, int64(expected.TotalRequests), metrics.TotalRequests)
	require.Equal(t, int64(expected.AllowedRequests), metrics.AllowedRequests)
	require.Equal(t, int64(expected.RejectedRequests), metrics.RejectedRequests)
	require.True(t, expected.BurstHandled)

	elapsedMs := int(elapsed.Milliseconds())
	require.LessOrEqual(t, elapsedMs, expected.MaxTotalTimeMs)
}

func TestRateLimiterMultipleTokensPerRequest(t *testing.T) {
	fixtures := loadRateLimiterFixtures(t)
	testCase := findRateLimiterTestCase(fixtures, "rate_limiter_multiple_tokens_per_request")
	require.NotNil(t, testCase, "Test case not found")

	// Create mock agent
	mockAgent := &MockRateLimiterAgent{}

	// Create rate limiter
	var maxWaitTimeout time.Duration
	if testCase.Config.MaxWaitMs != nil {
		maxWaitTimeout = time.Duration(*testCase.Config.MaxWaitMs) * time.Millisecond
	}

	config := middleware.RateLimiterConfig{
		Rate:             testCase.Config.Rate,
		Capacity:         testCase.Config.Capacity,
		TokensPerRequest: testCase.Config.TokensPerRequest,
		MaxWaitTimeout:   maxWaitTimeout,
	}
	rateLimiter := middleware.NewRateLimiterDecorator(mockAgent, config)

	// Execute requests
	for range testCase.Scenario.Requests {
		msg := &agenkit.Message{Role: "user", Content: "test"}
		_, err := rateLimiter.Process(context.Background(), msg)
		require.NoError(t, err)
	}

	// Verify expected behavior
	expected := testCase.ExpectedBehavior
	require.True(t, expected.AllSuccessful)

	metrics := rateLimiter.Metrics()
	require.Equal(t, int64(expected.TotalRequests), metrics.TotalRequests)
	require.Equal(t, int64(expected.AllowedRequests), metrics.AllowedRequests)
	require.Equal(t, int64(expected.RejectedRequests), metrics.RejectedRequests)
}

func TestRateLimiterMetricsTracking(t *testing.T) {
	fixtures := loadRateLimiterFixtures(t)
	testCase := findRateLimiterTestCase(fixtures, "rate_limiter_metrics_tracking")
	require.NotNil(t, testCase, "Test case not found")

	// Create mock agent
	mockAgent := &MockRateLimiterAgent{}

	// Create rate limiter
	var maxWaitTimeout time.Duration
	if testCase.Config.MaxWaitMs != nil {
		maxWaitTimeout = time.Duration(*testCase.Config.MaxWaitMs) * time.Millisecond
	}

	config := middleware.RateLimiterConfig{
		Rate:             testCase.Config.Rate,
		Capacity:         testCase.Config.Capacity,
		TokensPerRequest: testCase.Config.TokensPerRequest,
		MaxWaitTimeout:   maxWaitTimeout,
	}
	rateLimiter := middleware.NewRateLimiterDecorator(mockAgent, config)

	// Execute requests
	for range testCase.Scenario.Requests {
		msg := &agenkit.Message{Role: "user", Content: "test"}
		_, _ = rateLimiter.Process(context.Background(), msg)
	}

	// Verify expected metrics
	expected := testCase.ExpectedMetrics
	metrics := rateLimiter.Metrics()
	require.Equal(t, int64(expected.TotalRequests), metrics.TotalRequests)
	require.Equal(t, int64(expected.AllowedRequests), metrics.AllowedRequests)
	require.Equal(t, int64(expected.RejectedRequests), metrics.RejectedRequests)

	totalWaitMs := int(metrics.TotalWaitTime.Milliseconds())
	require.GreaterOrEqual(t, totalWaitMs, expected.TotalWaitTimeGreaterThan)
}
