// Package property contains property-based tests for the agenkit-go module.
package property_test

import (
	"math"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"pgregory.net/rapid"
)

// ============================================
// Self-contained implementations for testing
// ============================================

// retryState simulates retry behavior for property testing.
type retryState struct {
	maxRetries      int
	initialDelay    time.Duration
	maxDelay        time.Duration
	retryMultiplier float64
}

// computeDelay returns the delay for a given attempt number (0-indexed).
func (r *retryState) computeDelay(attempt int) time.Duration {
	if attempt <= 0 {
		return r.initialDelay
	}
	multiplied := float64(r.initialDelay) * math.Pow(r.retryMultiplier, float64(attempt))
	if multiplied > float64(r.maxDelay) {
		return r.maxDelay
	}
	return time.Duration(multiplied)
}

// simulateRetryAttempts runs retry simulation without I/O.
// failCount is the number of failures before success.
// Returns (totalAttempts, succeeded bool).
func (r *retryState) simulateRetryAttempts(failCount int) (int, bool) {
	for attempt := 0; attempt <= r.maxRetries; attempt++ {
		if attempt < failCount {
			// failure — would sleep r.computeDelay(attempt)
			continue
		}
		// success
		return attempt + 1, true
	}
	return r.maxRetries + 1, false
}

// cbState simulates circuit breaker state for property testing.
type cbState struct {
	mu               sync.Mutex
	failureThreshold int
	successThreshold int
	recoveryTimeoutS float64
	failureCount     int
	successCount     int
	state            int // 0=closed, 1=open, 2=half_open
	lastFailureTime  float64
}

const (
	cbClosed   = 0
	cbOpen     = 1
	cbHalfOpen = 2
)

func newCBState(failureThreshold, successThreshold int, recoveryTimeoutS float64) *cbState {
	return &cbState{
		failureThreshold: failureThreshold,
		successThreshold: successThreshold,
		recoveryTimeoutS: recoveryTimeoutS,
	}
}

func (cb *cbState) tryCall(success bool, nowS float64) bool {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	// Check transition from open → half_open
	if cb.state == cbOpen {
		if cb.recoveryTimeoutS > 0 && nowS-cb.lastFailureTime >= cb.recoveryTimeoutS {
			cb.state = cbHalfOpen
			cb.successCount = 0
		} else {
			return false // rejected
		}
	}

	if success {
		if cb.state == cbHalfOpen {
			cb.successCount++
			if cb.successCount >= cb.successThreshold {
				cb.state = cbClosed
				cb.failureCount = 0
				cb.successCount = 0
			}
		} else {
			cb.failureCount = 0
		}
	} else {
		cb.failureCount++
		cb.lastFailureTime = nowS

		if cb.state == cbHalfOpen {
			cb.state = cbOpen
		} else if cb.failureCount >= cb.failureThreshold {
			cb.state = cbOpen
		}
	}
	return true
}

func (cb *cbState) reset() {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	cb.state = cbClosed
	cb.failureCount = 0
	cb.successCount = 0
}

// ============================================
// Property: Retry Invariants
// ============================================

// TestRetryNeverExceedsMaxRetries verifies that total attempts ≤ maxRetries+1.
func TestRetryNeverExceedsMaxRetries(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		maxRetries := rapid.IntRange(0, 10).Draw(t, "maxRetries")
		failCount := rapid.IntRange(0, 20).Draw(t, "failCount")

		rs := &retryState{
			maxRetries:      maxRetries,
			initialDelay:    10 * time.Millisecond,
			maxDelay:        1 * time.Second,
			retryMultiplier: 2.0,
		}

		totalAttempts, _ := rs.simulateRetryAttempts(failCount)

		// Property: total attempts ≤ maxRetries+1
		if totalAttempts > maxRetries+1 {
			t.Fatalf("totalAttempts=%d > maxRetries+1=%d", totalAttempts, maxRetries+1)
		}
	})
}

// TestRetrySucceedsWhenFailCountLessThanMaxRetries verifies eventual success.
func TestRetrySucceedsWhenFailCountLessThanMaxRetries(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		failCount := rapid.IntRange(0, 9).Draw(t, "failCount")
		extra := rapid.IntRange(1, 5).Draw(t, "extra")
		maxRetries := failCount + extra

		rs := &retryState{
			maxRetries:      maxRetries,
			initialDelay:    10 * time.Millisecond,
			maxDelay:        1 * time.Second,
			retryMultiplier: 2.0,
		}

		_, succeeded := rs.simulateRetryAttempts(failCount)

		// Property: eventually succeeds
		if !succeeded {
			t.Fatalf("should succeed with failCount=%d and maxRetries=%d", failCount, maxRetries)
		}
	})
}

// TestRetryFirstAttemptSucceedsOnZeroFails verifies no retries when first attempt works.
func TestRetryFirstAttemptSucceedsOnZeroFails(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		maxRetries := rapid.IntRange(0, 10).Draw(t, "maxRetries")

		rs := &retryState{
			maxRetries:      maxRetries,
			initialDelay:    10 * time.Millisecond,
			maxDelay:        1 * time.Second,
			retryMultiplier: 2.0,
		}

		totalAttempts, succeeded := rs.simulateRetryAttempts(0)

		// Property: 0 failures = 1 attempt, success
		if !succeeded {
			t.Fatal("should succeed on first attempt with 0 failures")
		}
		if totalAttempts != 1 {
			t.Fatalf("expected 1 attempt with 0 failures, got %d", totalAttempts)
		}
	})
}

// TestRetryDelayIsNonNegative verifies computed delays are always ≥ 0.
func TestRetryDelayIsNonNegative(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		maxRetries := rapid.IntRange(1, 10).Draw(t, "maxRetries")
		initialDelayMs := rapid.IntRange(1, 100).Draw(t, "initialDelayMs")
		maxDelayMs := rapid.IntRange(100, 10000).Draw(t, "maxDelayMs")

		rs := &retryState{
			maxRetries:      maxRetries,
			initialDelay:    time.Duration(initialDelayMs) * time.Millisecond,
			maxDelay:        time.Duration(maxDelayMs) * time.Millisecond,
			retryMultiplier: 2.0,
		}

		// Property: all computed delays are non-negative
		for i := 0; i < maxRetries; i++ {
			d := rs.computeDelay(i)
			if d < 0 {
				t.Fatalf("computeDelay(%d) = %v, want >= 0", i, d)
			}
		}
	})
}

// TestRetryDelayNeverExceedsMaxDelay verifies the delay cap.
func TestRetryDelayNeverExceedsMaxDelay(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		maxRetries := rapid.IntRange(1, 15).Draw(t, "maxRetries")
		initialDelayMs := rapid.IntRange(1, 100).Draw(t, "initialDelayMs")
		maxDelayMs := rapid.IntRange(100, 5000).Draw(t, "maxDelayMs")

		rs := &retryState{
			maxRetries:      maxRetries,
			initialDelay:    time.Duration(initialDelayMs) * time.Millisecond,
			maxDelay:        time.Duration(maxDelayMs) * time.Millisecond,
			retryMultiplier: 2.0,
		}

		// Property: no computed delay exceeds maxDelay
		for i := 0; i < maxRetries; i++ {
			d := rs.computeDelay(i)
			if d > rs.maxDelay {
				t.Fatalf("computeDelay(%d) = %v > maxDelay=%v", i, d, rs.maxDelay)
			}
		}
	})
}

// TestRetryExponentialBackoffIsNonDecreasing verifies backoff monotonicity.
func TestRetryExponentialBackoffIsNonDecreasing(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		maxRetries := rapid.IntRange(2, 15).Draw(t, "maxRetries")
		initialDelayMs := rapid.IntRange(1, 50).Draw(t, "initialDelayMs")
		// Use very large maxDelay so cap doesn't hide non-monotonicity
		rs := &retryState{
			maxRetries:      maxRetries,
			initialDelay:    time.Duration(initialDelayMs) * time.Millisecond,
			maxDelay:        100 * time.Hour, // effectively no cap
			retryMultiplier: 2.0,
		}

		// Property: delays are non-decreasing
		prev := rs.computeDelay(0)
		for i := 1; i < maxRetries; i++ {
			curr := rs.computeDelay(i)
			if curr < prev {
				t.Fatalf("delay decreased at attempt %d: prev=%v, curr=%v", i, prev, curr)
			}
			prev = curr
		}
	})
}

// ============================================
// Property: Circuit Breaker Invariants
// ============================================

// TestCircuitBreakerOpensAfterThreshold verifies circuit opens after failureThreshold failures.
func TestCircuitBreakerOpensAfterThreshold(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		failureThreshold := rapid.IntRange(1, 10).Draw(t, "failureThreshold")

		cb := newCBState(failureThreshold, 2, 1000.0)

		// Trigger exactly failureThreshold failures
		for i := 0; i < failureThreshold; i++ {
			cb.tryCall(false, float64(i))
		}

		// Property: circuit is open
		if cb.state != cbOpen {
			t.Fatalf("expected state=open after %d failures, got %d", failureThreshold, cb.state)
		}
	})
}

// TestCircuitBreakerRejectsWhenOpen verifies calls are rejected in open state.
func TestCircuitBreakerRejectsWhenOpen(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		failureThreshold := rapid.IntRange(1, 5).Draw(t, "failureThreshold")
		extraCalls := rapid.IntRange(1, 10).Draw(t, "extraCalls")

		// Very long recovery timeout so circuit stays open
		cb := newCBState(failureThreshold, 2, 1e9)

		// Open the circuit
		for i := 0; i < failureThreshold; i++ {
			cb.tryCall(false, 0.0)
		}

		// Property: all subsequent calls are rejected
		for i := 0; i < extraCalls; i++ {
			allowed := cb.tryCall(true, 0.001) // small time increment, not enough for recovery
			if allowed {
				t.Fatalf("call %d should be rejected in open state", i)
			}
		}
	})
}

// TestCircuitBreakerStaysClosedBelowThreshold verifies circuit stays closed with fewer failures.
func TestCircuitBreakerStaysClosedBelowThreshold(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		failureThreshold := rapid.IntRange(2, 10).Draw(t, "failureThreshold")

		cb := newCBState(failureThreshold, 2, 1000.0)

		// Trigger fewer failures than threshold
		for i := 0; i < failureThreshold-1; i++ {
			cb.tryCall(false, float64(i))
		}

		// Property: circuit is still closed
		if cb.state != cbClosed {
			t.Fatalf("expected state=closed after %d failures (threshold=%d), got %d",
				failureThreshold-1, failureThreshold, cb.state)
		}
	})
}

// TestCircuitBreakerResetClearsState verifies reset restores initial state.
func TestCircuitBreakerResetClearsState(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		failureThreshold := rapid.IntRange(1, 5).Draw(t, "failureThreshold")

		cb := newCBState(failureThreshold, 2, 1000.0)

		// Open the circuit
		for i := 0; i < failureThreshold; i++ {
			cb.tryCall(false, float64(i))
		}

		cb.reset()

		// Property: state is closed and failure count is 0
		if cb.state != cbClosed {
			t.Fatalf("state should be closed after reset, got %d", cb.state)
		}
		if cb.failureCount != 0 {
			t.Fatalf("failureCount should be 0 after reset, got %d", cb.failureCount)
		}
	})
}

// TestCircuitBreakerAllowsCallsAfterReset verifies calls succeed after reset.
func TestCircuitBreakerAllowsCallsAfterReset(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		failureThreshold := rapid.IntRange(1, 5).Draw(t, "failureThreshold")

		cb := newCBState(failureThreshold, 2, 1000.0)

		// Open the circuit
		for i := 0; i < failureThreshold; i++ {
			cb.tryCall(false, float64(i))
		}

		cb.reset()

		// Property: calls are allowed after reset
		allowed := cb.tryCall(true, 0.0)
		if !allowed {
			t.Fatal("call should be allowed after reset")
		}
	})
}

// TestCircuitBreakerSuccessResetsFailureCount verifies success resets failure count.
func TestCircuitBreakerSuccessResetsFailureCount(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		// Must have at least 2 failures to see effect; threshold must be > 1
		failureThreshold := rapid.IntRange(3, 10).Draw(t, "failureThreshold")
		partialFailures := rapid.IntRange(1, failureThreshold-1).Draw(t, "partialFailures")

		cb := newCBState(failureThreshold, 2, 1000.0)

		// Some failures
		for i := 0; i < partialFailures; i++ {
			cb.tryCall(false, float64(i))
		}

		// One success should reset failure count
		cb.tryCall(true, float64(partialFailures))

		// Property: failure count is 0 after success in closed state
		if cb.failureCount != 0 {
			t.Fatalf("failureCount should be 0 after success, got %d", cb.failureCount)
		}
		if cb.state != cbClosed {
			t.Fatalf("state should be closed after success, got %d", cb.state)
		}
	})
}

// ============================================
// Property: Rate Limiter Invariants
// ============================================

// rateLimiter simulates a simple token bucket rate limiter.
type rateLimiter struct {
	mu       sync.Mutex
	tokens   float64
	maxBurst int
	ratePerS float64
	lastTime float64
}

func newRateLimiter(ratePerS float64, burst int) *rateLimiter {
	return &rateLimiter{
		tokens:   float64(burst),
		maxBurst: burst,
		ratePerS: ratePerS,
		lastTime: 0.0,
	}
}

func (rl *rateLimiter) allow(nowS float64) bool {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	// Refill tokens
	elapsed := nowS - rl.lastTime
	if elapsed > 0 {
		rl.tokens += elapsed * rl.ratePerS
		if rl.tokens > float64(rl.maxBurst) {
			rl.tokens = float64(rl.maxBurst)
		}
		rl.lastTime = nowS
	}

	if rl.tokens >= 1.0 {
		rl.tokens--
		return true
	}
	return false
}

// TestRateLimiterNeverExceedsRateInWindow verifies rate limiting.
func TestRateLimiterNeverExceedsRateInWindow(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		ratePerS := rapid.Float64Range(1.0, 100.0).Draw(t, "ratePerS")
		burst := rapid.IntRange(1, 20).Draw(t, "burst")
		windowS := rapid.Float64Range(0.1, 2.0).Draw(t, "windowS")

		rl := newRateLimiter(ratePerS, burst)

		// Count allowed requests in windowS seconds
		var allowed int64
		step := 0.001 // 1ms steps
		for t := 0.0; t < windowS; t += step {
			if rl.allow(t) {
				atomic.AddInt64(&allowed, 1)
			}
		}

		// Property: allowed requests ≤ burst + (ratePerS * windowS)
		maxAllowed := float64(burst) + ratePerS*windowS
		if float64(allowed) > maxAllowed+1.0 { // +1 for floating point tolerance
			t.Fatalf("allowed=%d > maxAllowed=%.1f in %.2fs window", allowed, maxAllowed, windowS)
		}
	})
}

// TestRateLimiterTokensNeverExceedBurst verifies token count bound.
func TestRateLimiterTokensNeverExceedBurst(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		ratePerS := rapid.Float64Range(1.0, 50.0).Draw(t, "ratePerS")
		burst := rapid.IntRange(1, 10).Draw(t, "burst")

		rl := newRateLimiter(ratePerS, burst)

		// Allow time to pass (tokens should refill)
		rl.allow(100.0) // Big time jump

		// Property: tokens never exceed burst
		if rl.tokens > float64(burst)+0.001 { // small float tolerance
			t.Fatalf("tokens=%.2f > burst=%d after refill", rl.tokens, burst)
		}
	})
}

// TestTimeoutDeadlineAlwaysPositive verifies timeout duration is positive.
func TestTimeoutDeadlineAlwaysPositive(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		timeoutMs := rapid.IntRange(1, 5000).Draw(t, "timeoutMs")

		timeout := time.Duration(timeoutMs) * time.Millisecond

		// Property: timeout is always positive
		if timeout <= 0 {
			t.Fatalf("timeout=%v should be > 0", timeout)
		}

		deadline := time.Now().Add(timeout)
		// Property: deadline is in the future
		if !deadline.After(time.Now()) {
			t.Fatalf("deadline %v should be after now", deadline)
		}
	})
}
