// Package registry provides agent discovery and health monitoring.
package registry

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"
)

// AgentRegistration contains information about a registered agent.
type AgentRegistration struct {
	Name          string
	Endpoint      string // e.g., "unix:///tmp/agent.sock" or "tcp://localhost:8080"
	Capabilities  map[string]interface{}
	Metadata      map[string]interface{}
	RegisteredAt  time.Time
	LastHeartbeat time.Time
}

// AgentRegistry is a central registry for agent discovery and health monitoring.
//
// This is an in-process registry suitable for single-process scenarios
// and testing. For production distributed systems, use a Redis or etcd
// backed registry.
type AgentRegistry struct {
	agents            map[string]*AgentRegistration
	heartbeatInterval time.Duration
	heartbeatTimeout  time.Duration
	mu                sync.RWMutex
	pruneTask         context.CancelFunc
	pruneDone         chan struct{}
}

// NewAgentRegistry creates a new agent registry.
//
// Args:
//   - heartbeatInterval: Expected interval between heartbeats
//   - heartbeatTimeout: Time before marking agent as stale
func NewAgentRegistry(heartbeatInterval, heartbeatTimeout time.Duration) *AgentRegistry {
	return &AgentRegistry{
		agents:            make(map[string]*AgentRegistration),
		heartbeatInterval: heartbeatInterval,
		heartbeatTimeout:  heartbeatTimeout,
	}
}

// Start starts the registry and background tasks.
func (r *AgentRegistry) Start(ctx context.Context) {
	r.mu.Lock()
	defer r.mu.Unlock()

	if r.pruneTask != nil {
		return // Already started
	}

	pruneCtx, cancel := context.WithCancel(ctx)
	r.pruneTask = cancel
	r.pruneDone = make(chan struct{})

	go r.pruneLoop(pruneCtx)
	log.Println("Agent registry started")
}

// Stop stops the registry and background tasks.
func (r *AgentRegistry) Stop() {
	r.mu.Lock()
	defer r.mu.Unlock()

	if r.pruneTask != nil {
		r.pruneTask()
		<-r.pruneDone
		r.pruneTask = nil
		log.Println("Agent registry stopped")
	}
}

// Register registers an agent.
//
// Args:
//   - registration: Agent registration information
//
// Returns:
//   - error: If agent name is empty
func (r *AgentRegistry) Register(registration *AgentRegistration) error {
	if registration.Name == "" {
		return fmt.Errorf("agent name cannot be empty")
	}

	r.mu.Lock()
	defer r.mu.Unlock()

	now := time.Now().UTC()
	if registration.RegisteredAt.IsZero() {
		registration.RegisteredAt = now
	}
	if registration.LastHeartbeat.IsZero() {
		registration.LastHeartbeat = now
	}

	if _, exists := r.agents[registration.Name]; exists {
		log.Printf("Re-registering agent: %s\n", registration.Name)
	} else {
		log.Printf("Registering new agent: %s\n", registration.Name)
	}

	r.agents[registration.Name] = registration
	return nil
}

// Unregister unregisters an agent.
//
// Args:
//   - agentName: Name of agent to unregister
func (r *AgentRegistry) Unregister(agentName string) {
	r.mu.Lock()
	defer r.mu.Unlock()

	if _, exists := r.agents[agentName]; exists {
		delete(r.agents, agentName)
		log.Printf("Unregistered agent: %s\n", agentName)
	} else {
		log.Printf("Attempted to unregister unknown agent: %s\n", agentName)
	}
}

// Lookup finds an agent by name.
//
// Args:
//   - agentName: Name of agent to find
//
// Returns:
//   - *AgentRegistration: Agent registration if found, nil otherwise
func (r *AgentRegistry) Lookup(agentName string) *AgentRegistration {
	r.mu.RLock()
	defer r.mu.RUnlock()

	return r.agents[agentName]
}

// ListAgents lists all registered agents.
//
// Returns:
//   - []*AgentRegistration: List of all agent registrations
func (r *AgentRegistry) ListAgents() []*AgentRegistration {
	r.mu.RLock()
	defer r.mu.RUnlock()

	agents := make([]*AgentRegistration, 0, len(r.agents))
	for _, agent := range r.agents {
		agents = append(agents, agent)
	}
	return agents
}

// Heartbeat updates agent heartbeat timestamp.
//
// Args:
//   - agentName: Name of agent sending heartbeat
//
// Returns:
//   - error: If agent is not registered
func (r *AgentRegistry) Heartbeat(agentName string) error {
	r.mu.Lock()
	defer r.mu.Unlock()

	agent, exists := r.agents[agentName]
	if !exists {
		return fmt.Errorf("agent '%s' is not registered", agentName)
	}

	agent.LastHeartbeat = time.Now().UTC()
	log.Printf("Heartbeat received from agent: %s\n", agentName)
	return nil
}

// PruneStaleAgents removes agents with expired heartbeats.
//
// Returns:
//   - int: Number of agents pruned
func (r *AgentRegistry) PruneStaleAgents() int {
	now := time.Now().UTC()
	pruned := 0

	r.mu.Lock()
	defer r.mu.Unlock()

	staleAgents := []string{}

	for name, registration := range r.agents {
		timeSinceHeartbeat := now.Sub(registration.LastHeartbeat)
		if timeSinceHeartbeat > r.heartbeatTimeout {
			staleAgents = append(staleAgents, name)
		}
	}

	for _, name := range staleAgents {
		timeSinceHeartbeat := now.Sub(r.agents[name].LastHeartbeat)
		delete(r.agents, name)
		log.Printf("Pruned stale agent: %s (no heartbeat for %.1fs)\n",
			name, timeSinceHeartbeat.Seconds())
		pruned++
	}

	return pruned
}

// Len returns the number of registered agents.
func (r *AgentRegistry) Len() int {
	r.mu.RLock()
	defer r.mu.RUnlock()

	return len(r.agents)
}

// pruneLoop is a background task to periodically prune stale agents.
func (r *AgentRegistry) pruneLoop(ctx context.Context) {
	defer close(r.pruneDone)

	ticker := time.NewTicker(60 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			pruned := r.PruneStaleAgents()
			if pruned > 0 {
				log.Printf("Pruned %d stale agent(s)\n", pruned)
			}
		}
	}
}

// HeartbeatLoop is a background task to send periodic heartbeats.
//
// Args:
//   - ctx: Context for cancellation
//   - registry: Agent registry to send heartbeats to
//   - agentName: Name of agent sending heartbeats
//   - interval: Interval between heartbeats
func HeartbeatLoop(ctx context.Context, registry *AgentRegistry, agentName string, interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			err := registry.Heartbeat(agentName)
			if err != nil {
				// Agent not registered - stop sending heartbeats
				log.Printf("Agent %s not registered, stopping heartbeats\n", agentName)
				return
			}
		}
	}
}
