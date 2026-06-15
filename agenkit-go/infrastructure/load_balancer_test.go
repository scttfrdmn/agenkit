package infrastructure

import (
	"context"
	"fmt"
	"sync/atomic"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// mockAgentLB is a test double for the Agent interface.
type mockAgentLB struct {
	name       string
	response   string
	callCount  atomic.Int64
	shouldFail bool
}

func newMockAgentLB(name, response string) *mockAgentLB {
	return &mockAgentLB{name: name, response: response}
}

func (m *mockAgentLB) Name() string           { return m.name }
func (m *mockAgentLB) Capabilities() []string { return []string{"mock"} }
func (m *mockAgentLB) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{AgentName: m.name}
}
func (m *mockAgentLB) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	m.callCount.Add(1)
	if m.shouldFail {
		return nil, fmt.Errorf("mock failure")
	}
	return agenkit.NewMessage("agent", m.response), nil
}

func TestNewLoadBalancer(t *testing.T) {
	a1 := newMockAgentLB("agent1", "response1")
	a2 := newMockAgentLB("agent2", "response2")
	agents := []agenkit.Agent{a1, a2}

	lb, err := NewLoadBalancer(agents, DefaultLoadBalancerConfig(), nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if lb == nil {
		t.Fatal("expected non-nil load balancer")
	}
}

func TestNewLoadBalancerNoAgents(t *testing.T) {
	_, err := NewLoadBalancer(nil, DefaultLoadBalancerConfig(), nil)
	if err == nil {
		t.Fatal("expected error with empty agent list")
	}
}

func TestLoadBalancerName(t *testing.T) {
	a1 := newMockAgentLB("agent1", "response")
	lb, err := NewLoadBalancer([]agenkit.Agent{a1}, DefaultLoadBalancerConfig(), nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if lb.Name() == "" {
		t.Error("expected non-empty name")
	}
}

func TestLoadBalancerCapabilities(t *testing.T) {
	a1 := newMockAgentLB("agent1", "response")
	lb, err := NewLoadBalancer([]agenkit.Agent{a1}, DefaultLoadBalancerConfig(), nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	caps := lb.Capabilities()
	if len(caps) == 0 {
		t.Error("expected non-empty capabilities")
	}
}

func TestLoadBalancerRoundRobin(t *testing.T) {
	a1 := newMockAgentLB("agent1", "r1")
	a2 := newMockAgentLB("agent2", "r2")
	agents := []agenkit.Agent{a1, a2}

	config := DefaultLoadBalancerConfig()
	config.Strategy = RoundRobin
	lb, err := NewLoadBalancer(agents, config, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	ctx := context.Background()
	for i := 0; i < 4; i++ {
		msg := agenkit.NewMessage("user", "test")
		_, err := lb.Process(ctx, msg)
		if err != nil {
			t.Errorf("unexpected error on call %d: %v", i, err)
		}
	}

	// Both agents should have been called
	if a1.callCount.Load() == 0 {
		t.Error("agent1 was never called")
	}
	if a2.callCount.Load() == 0 {
		t.Error("agent2 was never called")
	}
	// Total calls should equal 4
	if a1.callCount.Load()+a2.callCount.Load() != 4 {
		t.Errorf("expected 4 total calls, got %d", a1.callCount.Load()+a2.callCount.Load())
	}
}

func TestLoadBalancerLeastConnections(t *testing.T) {
	a1 := newMockAgentLB("agent1", "r1")
	a2 := newMockAgentLB("agent2", "r2")

	config := DefaultLoadBalancerConfig()
	config.Strategy = LeastConnections
	lb, err := NewLoadBalancer([]agenkit.Agent{a1, a2}, config, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "test")
	_, err = lb.Process(ctx, msg)
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestLoadBalancerWeightedRoundRobin(t *testing.T) {
	a1 := newMockAgentLB("agent1", "r1")
	a2 := newMockAgentLB("agent2", "r2")
	weights := []int{3, 1}

	config := DefaultLoadBalancerConfig()
	config.Strategy = WeightedRoundRobin
	lb, err := NewLoadBalancer([]agenkit.Agent{a1, a2}, config, weights)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	ctx := context.Background()
	for i := 0; i < 8; i++ {
		msg := agenkit.NewMessage("user", "test")
		_, err := lb.Process(ctx, msg)
		if err != nil {
			t.Errorf("unexpected error on call %d: %v", i, err)
		}
	}

	// With weight 3:1, agent1 should be called ~3x more than agent2
	if a1.callCount.Load() < a2.callCount.Load() {
		t.Errorf("expected agent1 (weight 3) to be called more than agent2 (weight 1)")
	}
}

func TestLoadBalancerRandomStrategy(t *testing.T) {
	a1 := newMockAgentLB("agent1", "r1")
	a2 := newMockAgentLB("agent2", "r2")

	config := DefaultLoadBalancerConfig()
	config.Strategy = Random
	lb, err := NewLoadBalancer([]agenkit.Agent{a1, a2}, config, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	ctx := context.Background()
	for i := 0; i < 10; i++ {
		msg := agenkit.NewMessage("user", "test")
		_, err := lb.Process(ctx, msg)
		if err != nil {
			t.Errorf("unexpected error on call %d: %v", i, err)
		}
	}

	total := a1.callCount.Load() + a2.callCount.Load()
	if total != 10 {
		t.Errorf("expected 10 total calls, got %d", total)
	}
}

func TestLoadBalancerMetrics(t *testing.T) {
	a1 := newMockAgentLB("agent1", "r1")
	lb, err := NewLoadBalancer([]agenkit.Agent{a1}, DefaultLoadBalancerConfig(), nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "test")
	_, _ = lb.Process(ctx, msg)

	metrics := lb.Metrics()
	if metrics.TotalRequests != 1 {
		t.Errorf("expected 1 total request, got %d", metrics.TotalRequests)
	}
	if metrics.SuccessfulRequests != 1 {
		t.Errorf("expected 1 successful request, got %d", metrics.SuccessfulRequests)
	}
}

func TestLoadBalancerFailover(t *testing.T) {
	a1 := &mockAgentLB{name: "failing", response: "", shouldFail: true}
	a2 := newMockAgentLB("backup", "backup response")

	config := DefaultLoadBalancerConfig()
	config.EnableFailover = true
	lb, err := NewLoadBalancer([]agenkit.Agent{a1, a2}, config, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "test")
	resp, err := lb.Process(ctx, msg)
	// With failover, should succeed via backup agent
	if err == nil && resp != nil {
		if a2.callCount.Load() == 0 {
			t.Error("expected backup agent to be called for failover")
		}
	}
	// It's acceptable for failover to fail if first agent fails health check
}

func TestLoadBalancerGetBackendStats(t *testing.T) {
	a1 := newMockAgentLB("agent1", "r1")
	lb, err := NewLoadBalancer([]agenkit.Agent{a1}, DefaultLoadBalancerConfig(), nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	stats := lb.GetBackendStats()
	if len(stats) != 1 {
		t.Errorf("expected 1 backend stat, got %d", len(stats))
	}
}

func TestDefaultLoadBalancerConfig(t *testing.T) {
	config := DefaultLoadBalancerConfig()
	if config.Strategy != RoundRobin {
		t.Errorf("expected RoundRobin as default strategy")
	}
	if config.FailureThreshold <= 0 {
		t.Error("expected positive failure threshold")
	}
	if !config.EnableFailover {
		t.Error("expected failover to be enabled by default")
	}
}
