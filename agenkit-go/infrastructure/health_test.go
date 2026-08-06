package infrastructure

import (
	"context"
	"fmt"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// health.go shipped with no test file at all, which is how four defects survived
// into a documented example (#857):
//
//  1. CheckStartup called CheckReadiness, but CheckReadiness returns Unhealthy
//     while startupComplete is false and only CheckStartup sets it — so an agent
//     configured with StartupEnabled could never become healthy.
//  2. `err != nil || response.ContentString() == ""` dereferenced the nil *Message
//     that Process returns on error.
//  3. readinessLoop read metrics.ConsecutiveFailures under hc.mu instead of
//     metrics.mu — a data race.
//  4. startupCheck waited a hardcoded 10s between attempts, so the default
//     StartupTimeout of 30s made 27 of the 30 configured attempts unreachable.

// mockAgentHC is a test double whose health can be flipped mid-test.
type mockAgentHC struct {
	name      string
	callCount atomic.Int64
	// failures counts down: while > 0 Process fails, then it succeeds.
	failures atomic.Int64
	// emptyReply makes Process succeed but return blank content.
	emptyReply atomic.Bool
	// blockFor delays each Process call, to exercise the readiness timeout.
	blockFor atomic.Int64
}

func newMockAgentHC(name string) *mockAgentHC {
	return &mockAgentHC{name: name}
}

func (m *mockAgentHC) Name() string           { return m.name }
func (m *mockAgentHC) Capabilities() []string { return []string{"mock"} }
func (m *mockAgentHC) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{AgentName: m.name}
}

func (m *mockAgentHC) Process(ctx context.Context, _ *agenkit.Message) (*agenkit.Message, error) {
	m.callCount.Add(1)

	if d := time.Duration(m.blockFor.Load()); d > 0 {
		select {
		case <-time.After(d):
		case <-ctx.Done():
			return nil, ctx.Err()
		}
	}

	if m.failures.Load() > 0 {
		m.failures.Add(-1)
		// Deliberately a nil *Message alongside the error: that is the real
		// contract, and it is what defect (2) dereferenced.
		return nil, fmt.Errorf("%s: simulated failure", m.name)
	}

	if m.emptyReply.Load() {
		return agenkit.NewMessage("agent", ""), nil
	}

	return agenkit.NewMessage("agent", "ok"), nil
}

// fastStartupConfig keeps the probe intervals small so tests stay quick.
func fastStartupConfig() HealthCheckConfig {
	return HealthCheckConfig{
		LivenessEnabled:           true,
		LivenessInterval:          20 * time.Millisecond,
		LivenessTimeout:           500 * time.Millisecond,
		LivenessFailureThreshold:  3,
		ReadinessEnabled:          true,
		ReadinessInterval:         20 * time.Millisecond,
		ReadinessTimeout:          500 * time.Millisecond,
		ReadinessFailureThreshold: 2,
		StartupEnabled:            true,
		StartupTimeout:            2 * time.Second,
		StartupFailureThreshold:   10,
	}
}

// TestStartupCompletesWithStartupEnabled is the regression test for defect (1).
// Before the fix this reported unhealthy forever: CheckStartup delegated to
// CheckReadiness, which refused because startup had not completed.
func TestStartupCompletesWithStartupEnabled(t *testing.T) {
	agent := newMockAgentHC("healthy")
	hc := NewHealthChecker(agent, fastStartupConfig())

	result := hc.CheckStartup(context.Background())
	if result.Status != Healthy {
		t.Fatalf("startup on a healthy agent should pass, got %v (%q)", result.Status, result.Message)
	}
	if result.ProbeType != Startup {
		t.Errorf("expected probe type %q, got %q", Startup, result.ProbeType)
	}

	// A passing startup probe must also make readiness pass, and hence IsHealthy.
	if !hc.IsHealthy() {
		t.Error("IsHealthy() should be true immediately after a successful startup probe")
	}
	if r := hc.CheckReadiness(context.Background()); r.Status != Healthy {
		t.Errorf("readiness after startup should pass, got %v (%q)", r.Status, r.Message)
	}
}

// TestStartupLoopReachesHealthy drives the background goroutines, which is what
// the production_agent example does. StartupEnabled + ReadinessEnabled together
// deadlocked before the fix.
func TestStartupLoopReachesHealthy(t *testing.T) {
	agent := newMockAgentHC("healthy")
	hc := NewHealthChecker(agent, fastStartupConfig())

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	hc.Start(ctx)
	defer hc.Stop()

	deadline := time.Now().Add(2 * time.Second)
	for !hc.IsHealthy() {
		if time.Now().After(deadline) {
			t.Fatal("health checker never became healthy; startup and readiness are mutually blocked")
		}
		time.Sleep(10 * time.Millisecond)
	}
}

// TestReadinessGatedUntilStartup asserts the gate itself still works — the fix
// must not have removed it, only stopped startup from depending on it.
func TestReadinessGatedUntilStartup(t *testing.T) {
	agent := newMockAgentHC("healthy")
	hc := NewHealthChecker(agent, fastStartupConfig())

	result := hc.CheckReadiness(context.Background())
	if result.Status != Unhealthy {
		t.Errorf("readiness before startup should be Unhealthy, got %v", result.Status)
	}
	if !strings.Contains(result.Message, "Startup not complete") {
		t.Errorf("expected a startup-gating message, got %q", result.Message)
	}
	if agent.callCount.Load() != 0 {
		t.Errorf("gated readiness should not call the agent, got %d calls", agent.callCount.Load())
	}
}

// TestProbeHandlesFailingAgent is the regression test for defect (2): Process
// returns (nil, err), and the old `err != nil || response.ContentString() == ""`
// dereferenced that nil.
func TestProbeHandlesFailingAgent(t *testing.T) {
	agent := newMockAgentHC("failing")
	agent.failures.Store(1)

	cfg := fastStartupConfig()
	cfg.StartupEnabled = false // probe readiness directly
	hc := NewHealthChecker(agent, cfg)

	result := hc.CheckReadiness(context.Background()) // must not panic
	if result.Status != Unhealthy {
		t.Fatalf("readiness against a failing agent should be Unhealthy, got %v", result.Status)
	}
	if !strings.Contains(result.Message, "simulated failure") {
		t.Errorf("expected the agent's error in the message, got %q", result.Message)
	}
}

// TestProbeRejectsEmptyContent covers the other Unhealthy branch: a successful
// call that returns nothing useful.
func TestProbeRejectsEmptyContent(t *testing.T) {
	agent := newMockAgentHC("empty")
	agent.emptyReply.Store(true)

	cfg := fastStartupConfig()
	cfg.StartupEnabled = false
	hc := NewHealthChecker(agent, cfg)

	result := hc.CheckReadiness(context.Background())
	if result.Status != Unhealthy {
		t.Fatalf("empty content should be Unhealthy, got %v", result.Status)
	}
	if !strings.Contains(result.Message, "empty content") {
		t.Errorf("expected an empty-content message, got %q", result.Message)
	}
}

// TestReadinessTimeoutIsEnforced proves ReadinessTimeout actually bounds the
// agent call, rather than the check hanging as long as the agent does.
func TestReadinessTimeoutIsEnforced(t *testing.T) {
	agent := newMockAgentHC("slow")
	agent.blockFor.Store(int64(5 * time.Second))

	cfg := fastStartupConfig()
	cfg.StartupEnabled = false
	cfg.ReadinessTimeout = 50 * time.Millisecond
	hc := NewHealthChecker(agent, cfg)

	start := time.Now()
	result := hc.CheckReadiness(context.Background())
	elapsed := time.Since(start)

	if result.Status != Unhealthy {
		t.Errorf("a timed-out probe should be Unhealthy, got %v", result.Status)
	}
	if elapsed > time.Second {
		t.Errorf("ReadinessTimeout not enforced: check took %v", elapsed)
	}
}

// TestStartupRetriesUntilAgentRecovers is the regression test for defect (4). With
// the old hardcoded 10s wait and a 2s StartupTimeout only one attempt ever ran, so
// an agent that needed three probes to come up never started.
func TestStartupRetriesUntilAgentRecovers(t *testing.T) {
	agent := newMockAgentHC("slow-starter")
	agent.failures.Store(3)

	cfg := fastStartupConfig()
	cfg.StartupTimeout = 2 * time.Second
	cfg.StartupFailureThreshold = 10
	hc := NewHealthChecker(agent, cfg)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	hc.Start(ctx)
	defer hc.Stop()

	deadline := time.Now().Add(3 * time.Second)
	for !hc.IsHealthy() {
		if time.Now().After(deadline) {
			t.Fatalf("never became healthy after %d probes; startup retry interval too coarse",
				agent.callCount.Load())
		}
		time.Sleep(10 * time.Millisecond)
	}

	if got := agent.callCount.Load(); got < 4 {
		t.Errorf("expected at least 4 probes (3 failures + 1 success), got %d", got)
	}
}

// TestMetricsCountEachProbeOnce guards against double-counting: CheckStartup and
// probe() both used to record the Startup probe.
func TestMetricsCountEachProbeOnce(t *testing.T) {
	agent := newMockAgentHC("healthy")
	hc := NewHealthChecker(agent, fastStartupConfig())

	if r := hc.CheckStartup(context.Background()); r.Status != Healthy {
		t.Fatalf("startup should pass, got %q", r.Message)
	}

	m := hc.Metrics()
	if got := m.TotalChecks[Startup]; got != 1 {
		t.Errorf("expected 1 startup check recorded, got %d", got)
	}
	if got := m.SuccessfulChecks[Startup]; got != 1 {
		t.Errorf("expected 1 successful startup check, got %d", got)
	}
	if got := m.FailedChecks[Startup]; got != 0 {
		t.Errorf("expected 0 failed startup checks, got %d", got)
	}
	if got := agent.callCount.Load(); got != 1 {
		t.Errorf("startup should probe the agent exactly once, got %d", got)
	}
}

// TestConsecutiveFailuresFlipReadiness exercises readinessLoop's threshold logic,
// where defect (3) (reading ConsecutiveFailures under the wrong mutex) lived. Run
// under -race this fails on the unfixed code.
func TestConsecutiveFailuresFlipReadiness(t *testing.T) {
	agent := newMockAgentHC("flaky")
	cfg := fastStartupConfig()
	cfg.ReadinessFailureThreshold = 2
	hc := NewHealthChecker(agent, cfg)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	hc.Start(ctx)
	defer hc.Stop()

	// Come up healthy first.
	deadline := time.Now().Add(2 * time.Second)
	for !hc.IsHealthy() {
		if time.Now().After(deadline) {
			t.Fatal("never became healthy")
		}
		time.Sleep(10 * time.Millisecond)
	}

	// Now fail every subsequent probe and expect readiness to drop.
	agent.emptyReply.Store(true)

	deadline = time.Now().Add(2 * time.Second)
	for hc.IsHealthy() {
		if time.Now().After(deadline) {
			t.Fatal("readiness never dropped after sustained probe failures")
		}
		time.Sleep(10 * time.Millisecond)
	}
}

// TestLivenessIndependentOfStartup: liveness only calls Name/Capabilities, so it
// must pass even for an agent whose Process fails.
func TestLivenessIndependentOfStartup(t *testing.T) {
	agent := newMockAgentHC("broken-process")
	agent.failures.Store(1000)
	hc := NewHealthChecker(agent, fastStartupConfig())

	if result := hc.CheckLiveness(context.Background()); result.Status != Healthy {
		t.Errorf("liveness should not depend on Process, got %v (%q)", result.Status, result.Message)
	}
}

// TestExportPrometheusMetricsIncludesProbes checks the exporter emits the probe
// labels rather than an empty scrape body.
func TestExportPrometheusMetricsIncludesProbes(t *testing.T) {
	agent := newMockAgentHC("healthy")
	hc := NewHealthChecker(agent, fastStartupConfig())

	if r := hc.CheckStartup(context.Background()); r.Status != Healthy {
		t.Fatalf("startup should pass, got %q", r.Message)
	}

	out := hc.ExportPrometheusMetrics()
	for _, want := range []string{
		"agenkit_health_checks_total",
		`probe="startup"`,
		"agenkit_agent_healthy 1",
	} {
		if !strings.Contains(out, want) {
			t.Errorf("Prometheus output missing %q:\n%s", want, out)
		}
	}
}

// TestStopIsIdempotentlySafe: Stop closes stopChan and waits for the goroutines,
// so a Start/Stop pair must not leak or panic.
func TestStopReleasesGoroutines(t *testing.T) {
	agent := newMockAgentHC("healthy")
	hc := NewHealthChecker(agent, fastStartupConfig())

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	hc.Start(ctx)

	done := make(chan struct{})
	go func() {
		hc.Stop()
		close(done)
	}()

	select {
	case <-done:
	case <-time.After(2 * time.Second):
		t.Fatal("Stop() did not return; a health goroutine is not honouring stopChan")
	}
}
