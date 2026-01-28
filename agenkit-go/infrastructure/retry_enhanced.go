package infrastructure

import (
	"context"
	"fmt"
	"math"
	"math/rand"
	"strings"
	"sync"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// JitterType defines types of jitter for retry backoff.
type JitterType int

const (
	// NoJitter applies no jitter.
	NoJitter JitterType = iota
	// FullJitter applies random 0 to backoff.
	FullJitter
	// EqualJitter applies random backoff/2 to backoff.
	EqualJitter
	// DecorrelatedJitter applies exponential with randomness.
	DecorrelatedJitter
)

// ErrorClass classification for retry strategies.
type ErrorClass int

const (
	// Transient errors are temporary, retry immediately.
	Transient ErrorClass = iota
	// RateLimit errors need longer backoff.
	RateLimit
	// Timeout errors may need longer timeout.
	Timeout
	// ServerError for server issues, retry with backoff.
	ServerError
	// ClientError for client issues, don't retry.
	ClientError
	// UnknownError for unknown errors, use default strategy.
	UnknownError
)

func (ec ErrorClass) String() string {
	switch ec {
	case Transient:
		return "transient"
	case RateLimit:
		return "rate_limit"
	case Timeout:
		return "timeout"
	case ServerError:
		return "server_error"
	case ClientError:
		return "client_error"
	default:
		return "unknown"
	}
}

// ErrorStrategy defines retry strategy for specific error class.
type ErrorStrategy struct {
	ErrorClass        ErrorClass
	MaxAttempts       int
	InitialBackoff    time.Duration
	MaxBackoff        time.Duration
	BackoffMultiplier float64
	ShouldRetry       bool
}

// RetryBudget limits retry costs.
type RetryBudget struct {
	MaxCost            float64
	CurrentCost        float64
	MaxRetriesPerHour  int64
	RetryCount         int64
	WindowStart        time.Time
	mu                 sync.Mutex
}

// EnhancedRetryConfig configures enhanced retry behavior.
type EnhancedRetryConfig struct {
	// Basic retry settings
	MaxAttempts       int
	InitialBackoff    time.Duration
	MaxBackoff        time.Duration
	BackoffMultiplier float64

	// Jitter settings
	JitterType     JitterType
	JitterMinRatio float64 // For EqualJitter

	// Error-specific strategies
	ErrorStrategies  map[ErrorClass]ErrorStrategy
	ErrorClassifier  func(error) ErrorClass

	// Budget settings
	EnableBudget       bool
	CostTracker        func(agenkit.Message) float64
	MaxCostPerHour     float64
	MaxRetriesPerHour  int64

	// Backpressure detection
	EnableBackpressure  bool
	BackpressureThreshold float64
	BackpressureWindow  int
}

// DefaultEnhancedRetryConfig returns default configuration with error strategies.
func DefaultEnhancedRetryConfig() EnhancedRetryConfig {
	config := EnhancedRetryConfig{
		MaxAttempts:            3,
		InitialBackoff:         1 * time.Second,
		MaxBackoff:             30 * time.Second,
		BackoffMultiplier:      2.0,
		JitterType:             FullJitter,
		JitterMinRatio:         0.5,
		EnableBudget:           false,
		MaxCostPerHour:         100.0,
		MaxRetriesPerHour:      1000,
		EnableBackpressure:     true,
		BackpressureThreshold:  0.5,
		BackpressureWindow:     100,
	}

	// Default error strategies
	config.ErrorStrategies = map[ErrorClass]ErrorStrategy{
		Transient: {
			ErrorClass:        Transient,
			MaxAttempts:       5,
			InitialBackoff:    100 * time.Millisecond,
			MaxBackoff:        5 * time.Second,
			BackoffMultiplier: 2.0,
			ShouldRetry:       true,
		},
		RateLimit: {
			ErrorClass:        RateLimit,
			MaxAttempts:       10,
			InitialBackoff:    60 * time.Second,
			MaxBackoff:        300 * time.Second,
			BackoffMultiplier: 1.5,
			ShouldRetry:       true,
		},
		Timeout: {
			ErrorClass:        Timeout,
			MaxAttempts:       3,
			InitialBackoff:    2 * time.Second,
			MaxBackoff:        30 * time.Second,
			BackoffMultiplier: 2.0,
			ShouldRetry:       true,
		},
		ServerError: {
			ErrorClass:        ServerError,
			MaxAttempts:       3,
			InitialBackoff:    5 * time.Second,
			MaxBackoff:        60 * time.Second,
			BackoffMultiplier: 2.0,
			ShouldRetry:       true,
		},
		ClientError: {
			ErrorClass:        ClientError,
			MaxAttempts:       1,
			InitialBackoff:    0,
			MaxBackoff:        0,
			BackoffMultiplier: 1.0,
			ShouldRetry:       false,
		},
	}

	return config
}

// EnhancedRetryMetrics tracks retry performance.
type EnhancedRetryMetrics struct {
	TotalAttempts          int64
	SuccessfulFirstAttempt int64
	SuccessfulOnRetry      int64
	FailedAfterRetries     int64
	TotalRetries           int64
	TotalJitterAdded       float64
	BudgetExceededCount    int64
	BackpressureDetected   int64
	ErrorClassCounts       map[ErrorClass]int64
	RecentResults          []bool
	mu                     sync.Mutex
}

// EnhancedRetryDecorator wraps an agent with enhanced retry logic.
type EnhancedRetryDecorator struct {
	agent   agenkit.Agent
	config  EnhancedRetryConfig
	metrics *EnhancedRetryMetrics
	budget  *RetryBudget
}

// NewEnhancedRetryDecorator creates a new enhanced retry decorator.
func NewEnhancedRetryDecorator(agent agenkit.Agent, config EnhancedRetryConfig) *EnhancedRetryDecorator {
	return &EnhancedRetryDecorator{
		agent:   agent,
		config:  config,
		metrics: &EnhancedRetryMetrics{
			ErrorClassCounts: make(map[ErrorClass]int64),
			RecentResults:    make([]bool, 0, config.BackpressureWindow),
		},
		budget: &RetryBudget{
			MaxCost:           config.MaxCostPerHour,
			MaxRetriesPerHour: config.MaxRetriesPerHour,
			WindowStart:       time.Now(),
		},
	}
}

// Name returns the underlying agent name.
func (erd *EnhancedRetryDecorator) Name() string {
	return erd.agent.Name()
}

// Capabilities returns the underlying agent capabilities.
func (erd *EnhancedRetryDecorator) Capabilities() []string {
	return erd.agent.Capabilities()
}

// Introspect returns introspection data from the wrapped agent.
func (erd *EnhancedRetryDecorator) Introspect() *agenkit.IntrospectionResult {
	return erd.agent.Introspect()
}

func (erd *EnhancedRetryDecorator) classifyError(err error) ErrorClass {
	if erd.config.ErrorClassifier != nil {
		return erd.config.ErrorClassifier(err)
	}

	// Default classification
	errStr := strings.ToLower(err.Error())

	if strings.Contains(errStr, "rate limit") || strings.Contains(errStr, "429") {
		return RateLimit
	} else if strings.Contains(errStr, "timeout") || strings.Contains(errStr, "timed out") {
		return Timeout
	} else if strings.Contains(errStr, "500") || strings.Contains(errStr, "502") || strings.Contains(errStr, "503") {
		return ServerError
	} else if strings.Contains(errStr, "400") || strings.Contains(errStr, "401") || strings.Contains(errStr, "403") || strings.Contains(errStr, "404") {
		return ClientError
	}

	return UnknownError
}

func (erd *EnhancedRetryDecorator) getStrategy(errorClass ErrorClass) ErrorStrategy {
	if strategy, ok := erd.config.ErrorStrategies[errorClass]; ok {
		return strategy
	}

	// Default strategy
	return ErrorStrategy{
		ErrorClass:        errorClass,
		MaxAttempts:       erd.config.MaxAttempts,
		InitialBackoff:    erd.config.InitialBackoff,
		MaxBackoff:        erd.config.MaxBackoff,
		BackoffMultiplier: erd.config.BackoffMultiplier,
		ShouldRetry:       true,
	}
}

func (erd *EnhancedRetryDecorator) calculateBackoff(baseBackoff time.Duration, attempt int) time.Duration {
	switch erd.config.JitterType {
	case NoJitter:
		return baseBackoff

	case FullJitter:
		jittered := time.Duration(rand.Float64() * float64(baseBackoff))
		erd.metrics.mu.Lock()
		erd.metrics.TotalJitterAdded += float64(baseBackoff-jittered) / float64(time.Second)
		erd.metrics.mu.Unlock()
		return jittered

	case EqualJitter:
		minBackoff := time.Duration(float64(baseBackoff) * erd.config.JitterMinRatio)
		jittered := minBackoff + time.Duration(rand.Float64()*float64(baseBackoff-minBackoff))
		erd.metrics.mu.Lock()
		erd.metrics.TotalJitterAdded += float64(baseBackoff-jittered) / float64(time.Second)
		erd.metrics.mu.Unlock()
		return jittered

	case DecorrelatedJitter:
		if attempt == 1 {
			return baseBackoff
		}
		previous := erd.calculateBackoff(baseBackoff, attempt-1)
		jittered := time.Duration(rand.Float64()*float64(previous)*3 + float64(baseBackoff))
		if jittered > erd.config.MaxBackoff {
			return erd.config.MaxBackoff
		}
		return jittered

	default:
		return baseBackoff
	}
}

func (erd *EnhancedRetryDecorator) checkBudget(cost float64) bool {
	if !erd.config.EnableBudget {
		return true
	}

	erd.budget.mu.Lock()
	defer erd.budget.mu.Unlock()

	// Reset window if hour has passed
	if time.Since(erd.budget.WindowStart) > time.Hour {
		erd.budget.CurrentCost = 0.0
		erd.budget.RetryCount = 0
		erd.budget.WindowStart = time.Now()
	}

	// Check cost budget
	if erd.budget.CurrentCost+cost > erd.budget.MaxCost {
		erd.metrics.mu.Lock()
		erd.metrics.BudgetExceededCount++
		erd.metrics.mu.Unlock()
		return false
	}

	// Check retry count budget
	if erd.budget.RetryCount >= erd.budget.MaxRetriesPerHour {
		erd.metrics.mu.Lock()
		erd.metrics.BudgetExceededCount++
		erd.metrics.mu.Unlock()
		return false
	}

	return true
}

func (erd *EnhancedRetryDecorator) checkBackpressure() bool {
	if !erd.config.EnableBackpressure {
		return false
	}

	erd.metrics.mu.Lock()
	defer erd.metrics.mu.Unlock()

	recent := erd.metrics.RecentResults
	if len(recent) < erd.config.BackpressureWindow {
		return false
	}

	// Calculate failure rate
	failures := 0
	for _, success := range recent {
		if !success {
			failures++
		}
	}

	failureRate := float64(failures) / float64(len(recent))

	if failureRate > erd.config.BackpressureThreshold {
		erd.metrics.BackpressureDetected++
		return true
	}

	return false
}

// Process processes a message with enhanced retry logic.
func (erd *EnhancedRetryDecorator) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	var lastError error
	var errorClass ErrorClass
	var strategy ErrorStrategy

	for attempt := 1; attempt <= erd.config.MaxAttempts; attempt++ {
		erd.metrics.mu.Lock()
		erd.metrics.TotalAttempts++
		erd.metrics.mu.Unlock()

		// Check budget before attempt
		if erd.config.EnableBudget && erd.config.CostTracker != nil {
			estimatedCost := erd.config.CostTracker(*message)
			if !erd.checkBudget(estimatedCost) {
				return nil, fmt.Errorf("retry budget exceeded")
			}
		}

		// Check backpressure
		if erd.checkBackpressure() {
			time.Sleep(5 * time.Second)
		}

		// Process message
		response, err := erd.agent.Process(ctx, message)

		if err == nil {
			// Success
			erd.metrics.mu.Lock()
			if attempt == 1 {
				erd.metrics.SuccessfulFirstAttempt++
			} else {
				erd.metrics.SuccessfulOnRetry++
			}
			erd.metrics.RecentResults = append(erd.metrics.RecentResults, true)
			if len(erd.metrics.RecentResults) > erd.config.BackpressureWindow {
				erd.metrics.RecentResults = erd.metrics.RecentResults[1:]
			}
			erd.metrics.mu.Unlock()

			// Track cost
			if erd.config.EnableBudget && erd.config.CostTracker != nil {
				cost := erd.config.CostTracker(*message)
				erd.budget.mu.Lock()
				erd.budget.CurrentCost += cost
				erd.budget.mu.Unlock()
			}

			return response, nil
		}

		// Failure
		lastError = err

		// Track failure for backpressure
		erd.metrics.mu.Lock()
		erd.metrics.RecentResults = append(erd.metrics.RecentResults, false)
		if len(erd.metrics.RecentResults) > erd.config.BackpressureWindow {
			erd.metrics.RecentResults = erd.metrics.RecentResults[1:]
		}
		erd.metrics.mu.Unlock()

		// Classify error
		errorClass = erd.classifyError(err)
		erd.metrics.mu.Lock()
		erd.metrics.ErrorClassCounts[errorClass]++
		erd.metrics.mu.Unlock()

		// Get strategy for error class
		strategy = erd.getStrategy(errorClass)

		// Check if should retry
		if !strategy.ShouldRetry {
			erd.metrics.mu.Lock()
			erd.metrics.FailedAfterRetries++
			erd.metrics.mu.Unlock()
			return nil,fmt.Errorf("non-retryable error (%s): %w", errorClass, err)
		}

		// Check if exceeded max attempts for this error class
		if attempt >= strategy.MaxAttempts {
			break
		}

		// Track retry
		erd.metrics.mu.Lock()
		erd.metrics.TotalRetries++
		erd.metrics.mu.Unlock()

		erd.budget.mu.Lock()
		erd.budget.RetryCount++
		erd.budget.mu.Unlock()

		// Calculate backoff with jitter
		baseBackoff := time.Duration(float64(strategy.InitialBackoff) * math.Pow(strategy.BackoffMultiplier, float64(attempt-1)))
		if baseBackoff > strategy.MaxBackoff {
			baseBackoff = strategy.MaxBackoff
		}
		backoff := erd.calculateBackoff(baseBackoff, attempt)

		// Sleep with backoff
		select {
		case <-ctx.Done():
			return nil,ctx.Err()
		case <-time.After(backoff):
		}
	}

	// All attempts failed
	erd.metrics.mu.Lock()
	erd.metrics.FailedAfterRetries++
	erd.metrics.mu.Unlock()

	return nil,fmt.Errorf("max retry attempts (%d) exceeded for %s: %w", strategy.MaxAttempts, errorClass, lastError)
}

// Metrics returns current metrics.
func (erd *EnhancedRetryDecorator) Metrics() *EnhancedRetryMetrics {
	return erd.metrics
}
