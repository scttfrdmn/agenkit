package infrastructure

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// HealthStatus represents health check status.
type HealthStatus string

const (
	// Healthy indicates the agent is functioning normally.
	Healthy HealthStatus = "healthy"
	// Unhealthy indicates the agent is not functioning.
	Unhealthy HealthStatus = "unhealthy"
	// Degraded indicates partial functionality.
	Degraded HealthStatus = "degraded"
	// Unknown indicates health status cannot be determined.
	Unknown HealthStatus = "unknown"
)

// ProbeType defines types of health probes.
type ProbeType string

const (
	// Liveness checks if the process is alive.
	Liveness ProbeType = "liveness"
	// Readiness checks if the agent is ready to accept traffic.
	Readiness ProbeType = "readiness"
	// Startup checks if initialization has completed.
	Startup ProbeType = "startup"
)

// HealthCheckResult contains the result of a health check.
type HealthCheckResult struct {
	Status     HealthStatus
	ProbeType  ProbeType
	Message    string
	Timestamp  time.Time
	DurationMS float64
	Metadata   map[string]interface{}
}

// HealthCheckConfig configures health check behavior.
type HealthCheckConfig struct {
	// Liveness probe settings
	LivenessEnabled          bool
	LivenessInterval         time.Duration
	LivenessTimeout          time.Duration
	LivenessFailureThreshold int

	// Readiness probe settings
	ReadinessEnabled          bool
	ReadinessInterval         time.Duration
	ReadinessTimeout          time.Duration
	ReadinessFailureThreshold int

	// Startup probe settings
	StartupEnabled          bool
	StartupTimeout          time.Duration
	StartupFailureThreshold int

	// Custom health check function
	CustomCheck func(agenkit.Agent) bool
}

// DefaultHealthCheckConfig returns default configuration.
func DefaultHealthCheckConfig() HealthCheckConfig {
	return HealthCheckConfig{
		LivenessEnabled:           true,
		LivenessInterval:          10 * time.Second,
		LivenessTimeout:           5 * time.Second,
		LivenessFailureThreshold:  3,
		ReadinessEnabled:          true,
		ReadinessInterval:         5 * time.Second,
		ReadinessTimeout:          3 * time.Second,
		ReadinessFailureThreshold: 2,
		StartupEnabled:            true,
		StartupTimeout:            30 * time.Second,
		StartupFailureThreshold:   30,
	}
}

// HealthMetrics tracks health check metrics.
type HealthMetrics struct {
	TotalChecks         map[ProbeType]int64
	SuccessfulChecks    map[ProbeType]int64
	FailedChecks        map[ProbeType]int64
	LastCheckTime       map[ProbeType]time.Time
	LastCheckDuration   map[ProbeType]float64
	ConsecutiveFailures map[ProbeType]int
	UptimeStart         time.Time
	mu                  sync.RWMutex
}

// NewHealthMetrics creates new health metrics.
func NewHealthMetrics() *HealthMetrics {
	return &HealthMetrics{
		TotalChecks:         make(map[ProbeType]int64),
		SuccessfulChecks:    make(map[ProbeType]int64),
		FailedChecks:        make(map[ProbeType]int64),
		LastCheckTime:       make(map[ProbeType]time.Time),
		LastCheckDuration:   make(map[ProbeType]float64),
		ConsecutiveFailures: make(map[ProbeType]int),
		UptimeStart:         time.Now(),
	}
}

// GetUptime returns uptime in seconds.
func (hm *HealthMetrics) GetUptime() float64 {
	return time.Since(hm.UptimeStart).Seconds()
}

// HealthChecker monitors agent health.
type HealthChecker struct {
	agent                 agenkit.Agent
	config                HealthCheckConfig
	metrics               *HealthMetrics
	isAlive               bool
	isReady               bool
	startupComplete       bool
	lastSuccessfulRequest time.Time
	mu                    sync.RWMutex
	stopChan              chan struct{}
	wg                    sync.WaitGroup
}

// NewHealthChecker creates a new health checker.
func NewHealthChecker(agent agenkit.Agent, config HealthCheckConfig) *HealthChecker {
	return &HealthChecker{
		agent:           agent,
		config:          config,
		metrics:         NewHealthMetrics(),
		isAlive:         true,
		isReady:         false,
		startupComplete: false,
		stopChan:        make(chan struct{}),
	}
}

// IsHealthy returns overall health status.
func (hc *HealthChecker) IsHealthy() bool {
	hc.mu.RLock()
	defer hc.mu.RUnlock()
	return hc.isAlive && hc.isReady
}

// Start begins background health check tasks.
func (hc *HealthChecker) Start(ctx context.Context) {
	if hc.config.LivenessEnabled {
		hc.wg.Add(1)
		go hc.livenessLoop(ctx)
	}

	if hc.config.ReadinessEnabled {
		hc.wg.Add(1)
		go hc.readinessLoop(ctx)
	}

	if hc.config.StartupEnabled && !hc.startupComplete {
		hc.wg.Add(1)
		go hc.startupCheck(ctx)
	}
}

// Stop stops background health check tasks.
func (hc *HealthChecker) Stop() {
	close(hc.stopChan)
	hc.wg.Wait()
}

// CheckLiveness performs a liveness check.
func (hc *HealthChecker) CheckLiveness(ctx context.Context) HealthCheckResult {
	startTime := time.Now()
	probeType := Liveness

	hc.trackCheckStarted(probeType)

	// Basic liveness: Can we call methods?
	_ = hc.agent.Name()
	_ = hc.agent.Capabilities()

	// Custom check if provided
	if hc.config.CustomCheck != nil {
		if !hc.config.CustomCheck(hc.agent) {
			duration := time.Since(startTime).Milliseconds()
			hc.trackCheckFailure(probeType, float64(duration))
			return HealthCheckResult{
				Status:     Unhealthy,
				ProbeType:  probeType,
				Message:    "Custom health check failed",
				Timestamp:  time.Now(),
				DurationMS: float64(duration),
			}
		}
	}

	// Success
	duration := time.Since(startTime).Milliseconds()
	hc.trackCheckSuccess(probeType, float64(duration))

	return HealthCheckResult{
		Status:     Healthy,
		ProbeType:  probeType,
		Message:    "Agent process is alive",
		Timestamp:  time.Now(),
		DurationMS: float64(duration),
	}
}

// CheckReadiness performs a readiness check.
//
// Readiness is gated on startup having completed, so this reports Unhealthy until
// then. CheckStartup deliberately does NOT call this method — it calls probe()
// directly. Routing startup through the gate made the two mutually dependent:
// startup asked readiness, readiness answered "startup not complete", and
// startupComplete (which only CheckStartup sets) could never be reached. An
// example configured with StartupEnabled+ReadinessEnabled therefore never became
// healthy, and every probe of a healthy agent reported failure. health.go had no
// test file at all, so nothing caught it (#857).
func (hc *HealthChecker) CheckReadiness(ctx context.Context) HealthCheckResult {
	startTime := time.Now()
	probeType := Readiness

	hc.trackCheckStarted(probeType)

	// Check if startup completed
	hc.mu.RLock()
	startupPending := hc.config.StartupEnabled && !hc.startupComplete
	hc.mu.RUnlock()

	if startupPending {
		duration := time.Since(startTime).Milliseconds()
		hc.trackCheckFailure(probeType, float64(duration))
		return HealthCheckResult{
			Status:     Unhealthy,
			ProbeType:  probeType,
			Message:    "Startup not complete",
			Timestamp:  time.Now(),
			DurationMS: float64(duration),
		}
	}

	result := hc.probe(ctx, probeType, startTime)
	if result.Status == Healthy {
		hc.mu.Lock()
		hc.lastSuccessfulRequest = time.Now()
		hc.mu.Unlock()
	}
	return result
}

// probe sends one test message to the agent and classifies the outcome. Shared by
// CheckReadiness and CheckStartup so that startup does not have to go through the
// readiness gate it is itself a precondition of.
//
// Records success/failure for probeType; the caller records the start. startTime is
// the caller's so DurationMS covers the whole check, not just the agent call.
func (hc *HealthChecker) probe(ctx context.Context, probeType ProbeType, startTime time.Time) HealthCheckResult {
	// Test with a simple request
	checkCtx, cancel := context.WithTimeout(ctx, hc.config.ReadinessTimeout)
	defer cancel()

	testMsg := &agenkit.Message{
		Role:    "system",
		Content: "readiness_check",
	}

	response, err := hc.agent.Process(checkCtx, testMsg)
	duration := time.Since(startTime).Milliseconds()

	// `response.ContentString()` only after confirming err == nil: Process returns a
	// nil *Message on error, and ContentString has a pointer receiver, so evaluating
	// both sides of the `||` panicked whenever the agent failed. Go's `||` is
	// short-circuiting, which masked it — but only while err was non-nil AND the
	// first operand was checked first. A probe of a *failing* agent nil-dereferenced
	// as soon as anything reordered it.
	if err != nil {
		hc.trackCheckFailure(probeType, float64(duration))
		return HealthCheckResult{
			Status:     Unhealthy,
			ProbeType:  probeType,
			Message:    fmt.Sprintf("%s check failed: %v", probeType, err),
			Timestamp:  time.Now(),
			DurationMS: float64(duration),
		}
	}

	if response == nil || response.ContentString() == "" {
		hc.trackCheckFailure(probeType, float64(duration))
		return HealthCheckResult{
			Status:     Unhealthy,
			ProbeType:  probeType,
			Message:    fmt.Sprintf("%s check failed: agent returned empty content", probeType),
			Timestamp:  time.Now(),
			DurationMS: float64(duration),
		}
	}

	// Success
	hc.trackCheckSuccess(probeType, float64(duration))

	return HealthCheckResult{
		Status:     Healthy,
		ProbeType:  probeType,
		Message:    "Agent is ready to handle requests",
		Timestamp:  time.Now(),
		DurationMS: float64(duration),
	}
}

// CheckStartup performs a startup check.
//
// Probes the agent directly rather than calling CheckReadiness: readiness is gated
// on startupComplete, which only this method sets, so going through it could never
// succeed (#857). See CheckReadiness.
func (hc *HealthChecker) CheckStartup(ctx context.Context) HealthCheckResult {
	startTime := time.Now()
	probeType := Startup

	hc.trackCheckStarted(probeType)

	// probe records the success/failure counter for Startup itself, so this method
	// only reshapes the message. Tracking it again here would double-count every
	// startup probe against TotalChecks.
	probeResult := hc.probe(ctx, probeType, startTime)

	if probeResult.Status == Healthy {
		hc.mu.Lock()
		hc.startupComplete = true
		// A passing startup probe IS a passing readiness probe — it is the same
		// request against the same agent. Handing off directly (as Kubernetes does
		// when a startupProbe succeeds) is what makes IsHealthy() true promptly;
		// otherwise readiness stays false until readinessLoop's first tick, so an
		// agent that was ready immediately still reported unhealthy for a full
		// ReadinessInterval.
		hc.isReady = true
		hc.lastSuccessfulRequest = time.Now()
		hc.mu.Unlock()

		probeResult.Message = "Startup complete"
		return probeResult
	}

	probeResult.Message = "Startup checks not passing yet"
	return probeResult
}

func (hc *HealthChecker) livenessLoop(ctx context.Context) {
	defer hc.wg.Done()

	ticker := time.NewTicker(hc.config.LivenessInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-hc.stopChan:
			return
		case <-ticker.C:
			result := hc.CheckLiveness(ctx)

			hc.mu.Lock()
			if result.Status == Unhealthy {
				failures := hc.metrics.ConsecutiveFailures[Liveness]
				if failures >= hc.config.LivenessFailureThreshold {
					hc.isAlive = false
				}
			} else {
				hc.isAlive = true
			}
			hc.mu.Unlock()
		}
	}
}

func (hc *HealthChecker) readinessLoop(ctx context.Context) {
	defer hc.wg.Done()

	ticker := time.NewTicker(hc.config.ReadinessInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-hc.stopChan:
			return
		case <-ticker.C:
			result := hc.CheckReadiness(ctx)

			// ConsecutiveFailures is guarded by metrics.mu, not hc.mu. Reading it
			// under the wrong mutex was a data race that `go test -race` never saw
			// because health.go had no tests at all.
			hc.metrics.mu.RLock()
			failures := hc.metrics.ConsecutiveFailures[Readiness]
			hc.metrics.mu.RUnlock()

			hc.mu.Lock()
			if result.Status == Unhealthy {
				if failures >= hc.config.ReadinessFailureThreshold {
					hc.isReady = false
				}
			} else {
				hc.isReady = true
			}
			hc.mu.Unlock()
		}
	}
}

func (hc *HealthChecker) startupCheck(ctx context.Context) {
	defer hc.wg.Done()

	startTime := time.Now()
	attempts := 0

	// Spread StartupFailureThreshold attempts over StartupTimeout instead of waiting
	// a hardcoded 10s between them. With the default 30s timeout and 30 attempts the
	// old interval allowed exactly three probes before the timeout fired, so 27 of
	// the 30 configured attempts were unreachable — and a caller who shortened
	// StartupTimeout below 10s got exactly one.
	interval := hc.config.StartupTimeout / time.Duration(max(hc.config.StartupFailureThreshold, 1))
	interval = min(max(interval, 100*time.Millisecond), 10*time.Second)

	for {
		if time.Since(startTime) > hc.config.StartupTimeout {
			break
		}

		attempts++
		if attempts > hc.config.StartupFailureThreshold {
			break
		}

		result := hc.CheckStartup(ctx)
		if result.Status == Healthy {
			break
		}

		select {
		case <-ctx.Done():
			return
		case <-hc.stopChan:
			return
		case <-time.After(interval):
		}
	}
}

func (hc *HealthChecker) trackCheckStarted(probeType ProbeType) {
	hc.metrics.mu.Lock()
	hc.metrics.TotalChecks[probeType]++
	hc.metrics.mu.Unlock()
}

func (hc *HealthChecker) trackCheckSuccess(probeType ProbeType, durationMS float64) {
	hc.metrics.mu.Lock()
	hc.metrics.SuccessfulChecks[probeType]++
	hc.metrics.LastCheckTime[probeType] = time.Now()
	hc.metrics.LastCheckDuration[probeType] = durationMS
	hc.metrics.ConsecutiveFailures[probeType] = 0
	hc.metrics.mu.Unlock()
}

func (hc *HealthChecker) trackCheckFailure(probeType ProbeType, durationMS float64) {
	hc.metrics.mu.Lock()
	hc.metrics.FailedChecks[probeType]++
	hc.metrics.LastCheckTime[probeType] = time.Now()
	hc.metrics.LastCheckDuration[probeType] = durationMS
	hc.metrics.ConsecutiveFailures[probeType]++
	hc.metrics.mu.Unlock()
}

// ExportPrometheusMetrics exports metrics in Prometheus format.
func (hc *HealthChecker) ExportPrometheusMetrics() string {
	hc.metrics.mu.RLock()
	defer hc.metrics.mu.RUnlock()

	var sb strings.Builder

	// Total checks
	sb.WriteString("# HELP agenkit_health_checks_total Total number of health checks performed\n")
	sb.WriteString("# TYPE agenkit_health_checks_total counter\n")
	for probeType, count := range hc.metrics.TotalChecks {
		sb.WriteString(fmt.Sprintf("agenkit_health_checks_total{probe=\"%s\"} %d\n", probeType, count))
	}

	// Failed checks
	sb.WriteString("\n# HELP agenkit_health_check_failures_total Total number of failed health checks\n")
	sb.WriteString("# TYPE agenkit_health_check_failures_total counter\n")
	for probeType, count := range hc.metrics.FailedChecks {
		sb.WriteString(fmt.Sprintf("agenkit_health_check_failures_total{probe=\"%s\"} %d\n", probeType, count))
	}

	// Duration
	sb.WriteString("\n# HELP agenkit_health_check_duration_ms Duration of last health check in milliseconds\n")
	sb.WriteString("# TYPE agenkit_health_check_duration_ms gauge\n")
	for probeType, duration := range hc.metrics.LastCheckDuration {
		sb.WriteString(fmt.Sprintf("agenkit_health_check_duration_ms{probe=\"%s\"} %.2f\n", probeType, duration))
	}

	// Uptime
	sb.WriteString("\n# HELP agenkit_agent_uptime_seconds Uptime in seconds\n")
	sb.WriteString("# TYPE agenkit_agent_uptime_seconds gauge\n")
	sb.WriteString(fmt.Sprintf("agenkit_agent_uptime_seconds %.2f\n", hc.metrics.GetUptime()))

	// Health status
	sb.WriteString("\n# HELP agenkit_agent_healthy Agent health status (1=healthy, 0=unhealthy)\n")
	sb.WriteString("# TYPE agenkit_agent_healthy gauge\n")
	healthValue := 0
	if hc.IsHealthy() {
		healthValue = 1
	}
	sb.WriteString(fmt.Sprintf("agenkit_agent_healthy %d\n", healthValue))

	return sb.String()
}

// Metrics returns current metrics.
func (hc *HealthChecker) Metrics() *HealthMetrics {
	return hc.metrics
}
