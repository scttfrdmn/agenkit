package infrastructure

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/scttfrdmn/agenkit/core"
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
	LivenessEnabled         bool
	LivenessInterval        time.Duration
	LivenessTimeout         time.Duration
	LivenessFailureThreshold int

	// Readiness probe settings
	ReadinessEnabled         bool
	ReadinessInterval        time.Duration
	ReadinessTimeout         time.Duration
	ReadinessFailureThreshold int

	// Startup probe settings
	StartupEnabled         bool
	StartupTimeout         time.Duration
	StartupFailureThreshold int

	// Custom health check function
	CustomCheck func(core.Agent) bool
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
	TotalChecks          map[ProbeType]int64
	SuccessfulChecks     map[ProbeType]int64
	FailedChecks         map[ProbeType]int64
	LastCheckTime        map[ProbeType]time.Time
	LastCheckDuration    map[ProbeType]float64
	ConsecutiveFailures  map[ProbeType]int
	UptimeStart          time.Time
	mu                   sync.RWMutex
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
	agent            core.Agent
	config           HealthCheckConfig
	metrics          *HealthMetrics
	isAlive          bool
	isReady          bool
	startupComplete  bool
	lastSuccessfulRequest time.Time
	mu               sync.RWMutex
	stopChan         chan struct{}
	wg               sync.WaitGroup
}

// NewHealthChecker creates a new health checker.
func NewHealthChecker(agent core.Agent, config HealthCheckConfig) *HealthChecker {
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
func (hc *HealthChecker) CheckReadiness(ctx context.Context) HealthCheckResult {
	startTime := time.Now()
	probeType := Readiness

	hc.trackCheckStarted(probeType)

	// Check if startup completed
	if hc.config.StartupEnabled && !hc.startupComplete {
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

	// Test with a simple request
	checkCtx, cancel := context.WithTimeout(ctx, hc.config.ReadinessTimeout)
	defer cancel()

	testMsg := core.Message{
		Role:    "system",
		Content: "readiness_check",
	}

	response, err := hc.agent.Process(checkCtx, testMsg)
	duration := time.Since(startTime).Milliseconds()

	if err != nil || response.Content == "" {
		hc.trackCheckFailure(probeType, float64(duration))
		return HealthCheckResult{
			Status:     Unhealthy,
			ProbeType:  probeType,
			Message:    fmt.Sprintf("Readiness check failed: %v", err),
			Timestamp:  time.Now(),
			DurationMS: float64(duration),
		}
	}

	// Success
	hc.trackCheckSuccess(probeType, float64(duration))
	hc.mu.Lock()
	hc.lastSuccessfulRequest = time.Now()
	hc.mu.Unlock()

	return HealthCheckResult{
		Status:     Healthy,
		ProbeType:  probeType,
		Message:    "Agent is ready to handle requests",
		Timestamp:  time.Now(),
		DurationMS: float64(duration),
	}
}

// CheckStartup performs a startup check.
func (hc *HealthChecker) CheckStartup(ctx context.Context) HealthCheckResult {
	startTime := time.Now()
	probeType := Startup

	hc.trackCheckStarted(probeType)

	// Perform readiness check as startup test
	readinessResult := hc.CheckReadiness(ctx)

	if readinessResult.Status == Healthy {
		hc.mu.Lock()
		hc.startupComplete = true
		hc.mu.Unlock()

		duration := time.Since(startTime).Milliseconds()
		hc.trackCheckSuccess(probeType, float64(duration))

		return HealthCheckResult{
			Status:     Healthy,
			ProbeType:  probeType,
			Message:    "Startup complete",
			Timestamp:  time.Now(),
			DurationMS: float64(duration),
		}
	}

	duration := time.Since(startTime).Milliseconds()
	hc.trackCheckFailure(probeType, float64(duration))

	return HealthCheckResult{
		Status:     Unhealthy,
		ProbeType:  probeType,
		Message:    "Startup checks not passing yet",
		Timestamp:  time.Now(),
		DurationMS: float64(duration),
	}
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

			hc.mu.Lock()
			if result.Status == Unhealthy {
				failures := hc.metrics.ConsecutiveFailures[Readiness]
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
		case <-time.After(10 * time.Second):
			// Wait 10s between startup checks
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
