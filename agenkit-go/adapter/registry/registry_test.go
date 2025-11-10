package registry

import (
	"context"
	"sync"
	"testing"
	"time"
)

func TestRegisterAgent(t *testing.T) {
	registry := NewAgentRegistry(30*time.Second, 90*time.Second)

	registration := &AgentRegistration{
		Name:         "test_agent",
		Endpoint:     "unix:///tmp/test.sock",
		Capabilities: map[string]interface{}{"streaming": true},
		Metadata:     map[string]interface{}{"version": "1.0.0"},
	}

	err := registry.Register(registration)
	if err != nil {
		t.Fatal(err)
	}

	// Should be able to look up the agent
	found := registry.Lookup("test_agent")
	if found == nil {
		t.Fatal("Expected to find agent, got nil")
	}
	if found.Name != "test_agent" {
		t.Errorf("Expected name 'test_agent', got '%s'", found.Name)
	}
	if found.Endpoint != "unix:///tmp/test.sock" {
		t.Errorf("Expected endpoint 'unix:///tmp/test.sock', got '%s'", found.Endpoint)
	}
	if found.Capabilities["streaming"] != true {
		t.Errorf("Expected capabilities streaming=true, got %v", found.Capabilities["streaming"])
	}
	if found.Metadata["version"] != "1.0.0" {
		t.Errorf("Expected metadata version=1.0.0, got %v", found.Metadata["version"])
	}
}

func TestRegisterDuplicateAgent(t *testing.T) {
	registry := NewAgentRegistry(30*time.Second, 90*time.Second)

	// Register first time
	registration1 := &AgentRegistration{
		Name:     "agent",
		Endpoint: "unix:///tmp/v1.sock",
		Metadata: map[string]interface{}{"version": "1.0"},
	}
	err := registry.Register(registration1)
	if err != nil {
		t.Fatal(err)
	}

	// Register again with different endpoint
	registration2 := &AgentRegistration{
		Name:     "agent",
		Endpoint: "unix:///tmp/v2.sock",
		Metadata: map[string]interface{}{"version": "2.0"},
	}
	err = registry.Register(registration2)
	if err != nil {
		t.Fatal(err)
	}

	// Should have the new registration
	found := registry.Lookup("agent")
	if found == nil {
		t.Fatal("Expected to find agent, got nil")
	}
	if found.Endpoint != "unix:///tmp/v2.sock" {
		t.Errorf("Expected endpoint 'unix:///tmp/v2.sock', got '%s'", found.Endpoint)
	}
	if found.Metadata["version"] != "2.0" {
		t.Errorf("Expected metadata version=2.0, got %v", found.Metadata["version"])
	}
}

func TestRegisterEmptyName(t *testing.T) {
	registry := NewAgentRegistry(30*time.Second, 90*time.Second)

	registration := &AgentRegistration{
		Name:     "",
		Endpoint: "unix:///tmp/test.sock",
	}

	err := registry.Register(registration)
	if err == nil {
		t.Fatal("Expected error when registering agent with empty name")
	}
}

func TestUnregisterAgent(t *testing.T) {
	registry := NewAgentRegistry(30*time.Second, 90*time.Second)

	registration := &AgentRegistration{
		Name:     "agent",
		Endpoint: "unix:///tmp/test.sock",
	}
	err := registry.Register(registration)
	if err != nil {
		t.Fatal(err)
	}

	// Agent should exist
	if registry.Lookup("agent") == nil {
		t.Fatal("Expected agent to exist")
	}

	// Unregister
	registry.Unregister("agent")

	// Agent should be gone
	if registry.Lookup("agent") != nil {
		t.Error("Expected agent to be gone after unregister")
	}
}

func TestUnregisterNonexistentAgent(t *testing.T) {
	registry := NewAgentRegistry(30*time.Second, 90*time.Second)

	// Should not panic or error
	registry.Unregister("nonexistent")
}

func TestLookupNonexistentAgent(t *testing.T) {
	registry := NewAgentRegistry(30*time.Second, 90*time.Second)

	found := registry.Lookup("nonexistent")
	if found != nil {
		t.Error("Expected nil when looking up non-existent agent")
	}
}

func TestListAgents(t *testing.T) {
	registry := NewAgentRegistry(30*time.Second, 90*time.Second)

	// Initially empty
	agents := registry.ListAgents()
	if len(agents) != 0 {
		t.Errorf("Expected 0 agents initially, got %d", len(agents))
	}

	// Register some agents
	for i := 0; i < 3; i++ {
		registration := &AgentRegistration{
			Name:     "agent" + string(rune('0'+i)),
			Endpoint: "unix:///tmp/agent" + string(rune('0'+i)) + ".sock",
		}
		err := registry.Register(registration)
		if err != nil {
			t.Fatal(err)
		}
	}

	// Should list all agents
	agents = registry.ListAgents()
	if len(agents) != 3 {
		t.Errorf("Expected 3 agents, got %d", len(agents))
	}

	agentNames := make(map[string]bool)
	for _, agent := range agents {
		agentNames[agent.Name] = true
	}

	expectedNames := map[string]bool{"agent0": true, "agent1": true, "agent2": true}
	for name := range expectedNames {
		if !agentNames[name] {
			t.Errorf("Expected to find agent '%s' in list", name)
		}
	}
}

func TestHeartbeat(t *testing.T) {
	registry := NewAgentRegistry(30*time.Second, 90*time.Second)

	registration := &AgentRegistration{
		Name:     "agent",
		Endpoint: "unix:///tmp/test.sock",
	}
	err := registry.Register(registration)
	if err != nil {
		t.Fatal(err)
	}

	// Get initial heartbeat time
	found := registry.Lookup("agent")
	if found == nil {
		t.Fatal("Expected to find agent")
	}
	initialHeartbeat := found.LastHeartbeat

	// Wait a bit
	time.Sleep(100 * time.Millisecond)

	// Send heartbeat
	err = registry.Heartbeat("agent")
	if err != nil {
		t.Fatal(err)
	}

	// Heartbeat should be updated
	found = registry.Lookup("agent")
	if found == nil {
		t.Fatal("Expected to find agent")
	}
	if !found.LastHeartbeat.After(initialHeartbeat) {
		t.Error("Expected heartbeat to be updated")
	}
}

func TestHeartbeatUnregisteredAgent(t *testing.T) {
	registry := NewAgentRegistry(30*time.Second, 90*time.Second)

	err := registry.Heartbeat("nonexistent")
	if err == nil {
		t.Error("Expected error when sending heartbeat for unregistered agent")
	}
}

func TestPruneStaleAgents(t *testing.T) {
	// Use short timeout for testing
	registry := NewAgentRegistry(30*time.Second, 200*time.Millisecond)

	// Register agents
	for i := 0; i < 3; i++ {
		registration := &AgentRegistration{
			Name:     "agent" + string(rune('0'+i)),
			Endpoint: "unix:///tmp/agent" + string(rune('0'+i)) + ".sock",
		}
		err := registry.Register(registration)
		if err != nil {
			t.Fatal(err)
		}
	}

	// Send heartbeat to agent1 only
	time.Sleep(100 * time.Millisecond)
	err := registry.Heartbeat("agent1")
	if err != nil {
		t.Fatal(err)
	}

	// Wait for timeout
	time.Sleep(150 * time.Millisecond)

	// Prune stale agents
	pruned := registry.PruneStaleAgents()

	// agent0 and agent2 should be pruned (no recent heartbeat)
	// agent1 should remain (recent heartbeat)
	if pruned != 2 {
		t.Errorf("Expected 2 agents pruned, got %d", pruned)
	}
	if registry.Lookup("agent0") != nil {
		t.Error("Expected agent0 to be pruned")
	}
	if registry.Lookup("agent1") == nil {
		t.Error("Expected agent1 to remain")
	}
	if registry.Lookup("agent2") != nil {
		t.Error("Expected agent2 to be pruned")
	}
}

func TestPruneNoStaleAgents(t *testing.T) {
	registry := NewAgentRegistry(30*time.Second, 1*time.Second)

	registration := &AgentRegistration{
		Name:     "agent",
		Endpoint: "unix:///tmp/test.sock",
	}
	err := registry.Register(registration)
	if err != nil {
		t.Fatal(err)
	}

	// Immediately prune - agent should not be stale
	pruned := registry.PruneStaleAgents()
	if pruned != 0 {
		t.Errorf("Expected 0 agents pruned, got %d", pruned)
	}
	if registry.Lookup("agent") == nil {
		t.Error("Expected agent to remain")
	}
}

func TestRegistryStartStop(t *testing.T) {
	registry := NewAgentRegistry(30*time.Second, 500*time.Millisecond)
	ctx := context.Background()

	// Start registry
	registry.Start(ctx)

	// Register agent
	registration := &AgentRegistration{
		Name:     "agent",
		Endpoint: "unix:///tmp/test.sock",
	}
	err := registry.Register(registration)
	if err != nil {
		t.Fatal(err)
	}

	// Wait for potential prune cycle
	time.Sleep(100 * time.Millisecond)

	// Agent should still exist (not stale yet)
	if registry.Lookup("agent") == nil {
		t.Error("Expected agent to still exist")
	}

	// Stop registry
	registry.Stop()
}

func TestLen(t *testing.T) {
	registry := NewAgentRegistry(30*time.Second, 90*time.Second)

	if registry.Len() != 0 {
		t.Errorf("Expected 0 agents initially, got %d", registry.Len())
	}

	// Register some agents
	for i := 0; i < 5; i++ {
		registration := &AgentRegistration{
			Name:     "agent" + string(rune('0'+i)),
			Endpoint: "unix:///tmp/" + string(rune('0'+i)) + ".sock",
		}
		err := registry.Register(registration)
		if err != nil {
			t.Fatal(err)
		}
	}

	if registry.Len() != 5 {
		t.Errorf("Expected 5 agents, got %d", registry.Len())
	}

	// Unregister one
	registry.Unregister("agent2")
	if registry.Len() != 4 {
		t.Errorf("Expected 4 agents after unregister, got %d", registry.Len())
	}
}

func TestConcurrentOperations(t *testing.T) {
	registry := NewAgentRegistry(30*time.Second, 90*time.Second)

	// Register agents concurrently
	var wg sync.WaitGroup
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			registration := &AgentRegistration{
				Name:     "agent" + string(rune('0'+id)),
				Endpoint: "unix:///tmp/" + string(rune('0'+id)) + ".sock",
			}
			registry.Register(registration)
		}(i)
	}
	wg.Wait()

	// All agents should be registered
	if registry.Len() != 10 {
		t.Errorf("Expected 10 agents, got %d", registry.Len())
	}

	// Concurrent lookups
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			found := registry.Lookup("agent" + string(rune('0'+id)))
			if found == nil {
				t.Errorf("Expected to find agent%d", id)
			}
		}(i)
	}
	wg.Wait()

	// Concurrent heartbeats
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			registry.Heartbeat("agent" + string(rune('0'+id)))
		}(i)
	}
	wg.Wait()
}

func TestHeartbeatLoopSendsHeartbeats(t *testing.T) {
	registry := NewAgentRegistry(30*time.Second, 90*time.Second)

	registration := &AgentRegistration{
		Name:     "agent",
		Endpoint: "unix:///tmp/test.sock",
	}
	err := registry.Register(registration)
	if err != nil {
		t.Fatal(err)
	}

	// Get initial heartbeat
	found := registry.Lookup("agent")
	if found == nil {
		t.Fatal("Expected to find agent")
	}
	initialHeartbeat := found.LastHeartbeat

	// Start heartbeat loop with short interval
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go HeartbeatLoop(ctx, registry, "agent", 100*time.Millisecond)

	// Wait for a few heartbeats
	time.Sleep(350 * time.Millisecond)

	// Heartbeat should be updated
	found = registry.Lookup("agent")
	if found == nil {
		t.Fatal("Expected to find agent")
	}
	if !found.LastHeartbeat.After(initialHeartbeat) {
		t.Error("Expected heartbeat to be updated by heartbeat loop")
	}
}

func TestHeartbeatLoopStopsWhenUnregistered(t *testing.T) {
	registry := NewAgentRegistry(30*time.Second, 90*time.Second)

	registration := &AgentRegistration{
		Name:     "agent",
		Endpoint: "unix:///tmp/test.sock",
	}
	err := registry.Register(registration)
	if err != nil {
		t.Fatal(err)
	}

	// Start heartbeat loop
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	done := make(chan struct{})
	go func() {
		HeartbeatLoop(ctx, registry, "agent", 100*time.Millisecond)
		close(done)
	}()

	// Wait a bit
	time.Sleep(150 * time.Millisecond)

	// Unregister agent
	registry.Unregister("agent")

	// Wait a bit more - heartbeat loop should detect and stop
	select {
	case <-done:
		// Loop stopped as expected
	case <-time.After(500 * time.Millisecond):
		t.Error("Expected heartbeat loop to stop after agent unregistered")
	}
}
