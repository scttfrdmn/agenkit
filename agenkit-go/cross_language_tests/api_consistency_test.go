package tests

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/middleware"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// APIFixtures represents the loaded JSON fixtures
type APIFixtures struct {
	Version        string         `json:"version"`
	Description    string         `json:"description"`
	TestCategories TestCategories `json:"test_categories"`
}

type TestCategories struct {
	ParameterNaming ParameterNamingCategory `json:"parameter_naming"`
	DefaultValues   DefaultValuesCategory   `json:"default_values"`
}

type ParameterNamingCategory struct {
	Description string              `json:"description"`
	TestCases   []ParameterTestCase `json:"test_cases"`
}

type ParameterTestCase struct {
	ID         string                 `json:"id"`
	Name       string                 `json:"name"`
	Component  string                 `json:"component"`
	Parameters map[string]Parameter   `json:"parameters"`
}

type Parameter struct {
	Description    string            `json:"description"`
	ExpectedNames  map[string]string `json:"expected_names"`
	MustNotBeNamed []string          `json:"must_not_be_named,omitempty"`
}

type DefaultValuesCategory struct {
	Description string            `json:"description"`
	TestCases   []DefaultTestCase `json:"test_cases"`
}

type DefaultTestCase struct {
	ID        string                  `json:"id"`
	Name      string                  `json:"name"`
	Component string                  `json:"component"`
	Defaults  map[string]DefaultValue `json:"defaults"`
}

type DefaultValue struct {
	Value       interface{} `json:"value,omitempty"`
	ValueMs     int         `json:"value_ms,omitempty"`
	Description string      `json:"description"`
}

// loadAPIFixtures loads the API consistency JSON fixtures
func loadAPIFixtures(t *testing.T) APIFixtures {
	// Find the fixtures directory
	fixturesPath := filepath.Join("..", "..", "tests", "cross_language", "fixtures", "api_consistency.json")

	data, err := os.ReadFile(fixturesPath)
	require.NoError(t, err, "Failed to read API fixtures")

	var fixtures APIFixtures
	err = json.Unmarshal(data, &fixtures)
	require.NoError(t, err, "Failed to parse API fixtures")

	return fixtures
}

// TestRetryParameterNames verifies Go uses standardized parameter names (v0.50.0)
func TestRetryParameterNames(t *testing.T) {
	// Get RetryConfig type
	configType := reflect.TypeOf(middleware.RetryConfig{})

	// Go should use standardized names per v0.50.0 spec
	_, hasMaxRetries := configType.FieldByName("MaxRetries")
	assert.True(t, hasMaxRetries, "Go should use MaxRetries (standardized in v0.50.0)")

	_, hasInitialRetryDelay := configType.FieldByName("InitialRetryDelay")
	assert.True(t, hasInitialRetryDelay, "Go should use InitialRetryDelay (standardized in v0.50.0)")

	_, hasMaxRetryDelay := configType.FieldByName("MaxRetryDelay")
	assert.True(t, hasMaxRetryDelay, "Go should use MaxRetryDelay (standardized in v0.50.0)")

	_, hasRetryMultiplier := configType.FieldByName("RetryMultiplier")
	assert.True(t, hasRetryMultiplier, "Go should use RetryMultiplier (standardized in v0.50.0)")
}

// TestRetryDefaults verifies RetryConfig default configuration values
func TestRetryDefaults(t *testing.T) {
	fixtures := loadAPIFixtures(t)

	// Find the retry defaults test case
	var testCase DefaultTestCase
	for _, tc := range fixtures.TestCategories.DefaultValues.TestCases {
		if tc.ID == "retry_defaults" {
			testCase = tc
			break
		}
	}

	require.NotEmpty(t, testCase.ID, "Could not find retry_defaults test case")

	// Create default config
	config := middleware.DefaultRetryConfig()

	// Check max_retries default
	expectedMaxRetries := int(testCase.Defaults["max_retries"].Value.(float64))
	assert.Equal(t, expectedMaxRetries, config.MaxRetries,
		"MaxRetries default should be %d", expectedMaxRetries)

	// Check initial_delay default (Go uses time.Duration)
	expectedInitialDelayMs := testCase.Defaults["initial_delay"].ValueMs
	expectedInitialDelay := time.Duration(expectedInitialDelayMs) * time.Millisecond
	assert.Equal(t, expectedInitialDelay, config.InitialRetryDelay,
		"InitialRetryDelay default should be %v", expectedInitialDelay)

	// Check max_delay default (Go uses time.Duration)
	expectedMaxDelayMs := testCase.Defaults["max_delay"].ValueMs
	expectedMaxDelay := time.Duration(expectedMaxDelayMs) * time.Millisecond
	assert.Equal(t, expectedMaxDelay, config.MaxRetryDelay,
		"MaxRetryDelay default should be %v", expectedMaxDelay)

	// Check multiplier default
	expectedMultiplier := testCase.Defaults["multiplier"].Value.(float64)
	assert.Equal(t, expectedMultiplier, config.RetryMultiplier,
		"RetryMultiplier default should be %f", expectedMultiplier)
}

// TestTimeoutDefaults verifies TimeoutConfig default configuration values
func TestTimeoutDefaults(t *testing.T) {
	fixtures := loadAPIFixtures(t)

	// Find the timeout defaults test case
	var testCase DefaultTestCase
	for _, tc := range fixtures.TestCategories.DefaultValues.TestCases {
		if tc.ID == "timeout_defaults" {
			testCase = tc
			break
		}
	}

	require.NotEmpty(t, testCase.ID, "Could not find timeout_defaults test case")

	// Create default config
	config := middleware.DefaultTimeoutConfig()

	// Check timeout default (convert from ms to Duration)
	expectedTimeoutMs := testCase.Defaults["timeout"].ValueMs
	expectedTimeout := time.Duration(expectedTimeoutMs) * time.Millisecond
	assert.Equal(t, expectedTimeout, config.Timeout,
		"Timeout default should be %v (%dms)", expectedTimeout, expectedTimeoutMs)
}

// TestRateLimiterDefaults verifies RateLimiterConfig default configuration values
func TestRateLimiterDefaults(t *testing.T) {
	fixtures := loadAPIFixtures(t)

	// Find the rate limiter defaults test case
	var testCase DefaultTestCase
	for _, tc := range fixtures.TestCategories.DefaultValues.TestCases {
		if tc.ID == "rate_limiter_defaults" {
			testCase = tc
			break
		}
	}

	require.NotEmpty(t, testCase.ID, "Could not find rate_limiter_defaults test case")

	// Create default config
	config := middleware.DefaultRateLimiterConfig()

	// Check rate default
	expectedRate := testCase.Defaults["rate"].Value.(float64)
	assert.Equal(t, expectedRate, config.Rate,
		"Rate default should be %f requests/second", expectedRate)

	// Check capacity default
	expectedCapacity := int(testCase.Defaults["capacity"].Value.(float64))
	assert.Equal(t, expectedCapacity, config.Capacity,
		"Capacity default should be %d", expectedCapacity)
}

// TestCircuitBreakerDefaults verifies CircuitBreakerConfig default configuration values
func TestCircuitBreakerDefaults(t *testing.T) {
	fixtures := loadAPIFixtures(t)

	// Find the circuit breaker defaults test case
	var testCase DefaultTestCase
	for _, tc := range fixtures.TestCategories.DefaultValues.TestCases {
		if tc.ID == "circuit_breaker_defaults" {
			testCase = tc
			break
		}
	}

	require.NotEmpty(t, testCase.ID, "Could not find circuit_breaker_defaults test case")

	// Create default config
	config := middleware.DefaultCircuitBreakerConfig()

	// Check failure_threshold default
	expectedThreshold := int(testCase.Defaults["failure_threshold"].Value.(float64))
	assert.Equal(t, expectedThreshold, config.FailureThreshold,
		"FailureThreshold default should be %d", expectedThreshold)

	// Check recovery_timeout default (convert from ms)
	expectedRecoveryMs := testCase.Defaults["recovery_timeout"].ValueMs
	expectedRecovery := time.Duration(expectedRecoveryMs) * time.Millisecond
	assert.Equal(t, expectedRecovery, config.RecoveryTimeout,
		"RecoveryTimeout default should be %v", expectedRecovery)
}

// TestAgentProcessSignature verifies Agent.Process method signature
func TestAgentProcessSignature(t *testing.T) {
	// Get Agent interface type
	var agent agenkit.Agent
	agentType := reflect.TypeOf(&agent).Elem()

	// Check Process method exists
	method, found := agentType.MethodByName("Process")
	require.True(t, found, "Agent interface should have Process method")

	// Verify signature: Process(ctx context.Context, message *Message) (*Message, error)
	methodType := method.Type

	// Should have 2 inputs: context, message (receiver not counted for interface methods)
	assert.Equal(t, 2, methodType.NumIn(),
		"Process should have 2 inputs (ctx, message)")

	// Should have 2 outputs: *Message, error
	assert.Equal(t, 2, methodType.NumOut(),
		"Process should have 2 outputs (*Message, error)")

	// First input should be context.Context
	assert.Equal(t, "context.Context", methodType.In(0).String(),
		"First parameter should be context.Context")

	// Second output should be error
	errorInterface := reflect.TypeOf((*error)(nil)).Elem()
	assert.True(t, methodType.Out(1).Implements(errorInterface),
		"Second return value should be error")
}

// TestToolExecuteSignature verifies Tool.Execute method signature
func TestToolExecuteSignature(t *testing.T) {
	// Get Tool interface type
	var tool agenkit.Tool
	toolType := reflect.TypeOf(&tool).Elem()

	// Check Execute method exists
	method, found := toolType.MethodByName("Execute")
	require.True(t, found, "Tool interface should have Execute method")

	// Verify signature: Execute(ctx context.Context, params map[string]any) (*ToolResult, error)
	methodType := method.Type

	// Should have 2 inputs: context, params (receiver not counted for interface methods)
	assert.Equal(t, 2, methodType.NumIn(),
		"Execute should have 2 inputs (ctx, params)")

	// Should have 2 outputs: *ToolResult, error
	assert.Equal(t, 2, methodType.NumOut(),
		"Execute should have 2 outputs (*ToolResult, error)")

	// First parameter should be context.Context
	assert.Equal(t, "context.Context", methodType.In(0).String(),
		"First parameter should be context.Context")

	// Second parameter should be map[string]any or similar
	paramType := methodType.In(1)
	assert.Equal(t, reflect.Map, paramType.Kind(),
		"Second parameter should be a map type")

	// Second output should be error
	errorInterface := reflect.TypeOf((*error)(nil)).Elem()
	assert.True(t, methodType.Out(1).Implements(errorInterface),
		"Second return value should be error")
}

// TestGoUsesTimeDuration verifies Go uses time.Duration (idiomatic)
func TestGoUsesTimeDuration(t *testing.T) {
	// Verify RetryConfig uses time.Duration for timing fields
	config := middleware.DefaultRetryConfig()

	// InitialRetryDelay should be Duration
	assert.IsType(t, time.Duration(0), config.InitialRetryDelay,
		"InitialRetryDelay should be time.Duration (idiomatic Go)")

	// MaxRetryDelay should be Duration
	assert.IsType(t, time.Duration(0), config.MaxRetryDelay,
		"MaxRetryDelay should be time.Duration (idiomatic Go)")

	// Verify TimeoutConfig uses time.Duration
	timeoutConfig := middleware.DefaultTimeoutConfig()
	assert.IsType(t, time.Duration(0), timeoutConfig.Timeout,
		"Timeout should be time.Duration (idiomatic Go)")

	// Verify CircuitBreakerConfig uses time.Duration
	cbConfig := middleware.DefaultCircuitBreakerConfig()
	assert.IsType(t, time.Duration(0), cbConfig.RecoveryTimeout,
		"RecoveryTimeout should be time.Duration (idiomatic Go)")
}

// TestGoExportedFieldNames verifies Go uses PascalCase for exported fields
func TestGoExportedFieldNames(t *testing.T) {
	// Get RetryConfig type
	configType := reflect.TypeOf(middleware.RetryConfig{})

	// All fields should start with uppercase (exported)
	for i := 0; i < configType.NumField(); i++ {
		field := configType.Field(i)
		firstChar := field.Name[0]
		assert.True(t, firstChar >= 'A' && firstChar <= 'Z',
			"Field %s should be exported (PascalCase)", field.Name)
	}
}
