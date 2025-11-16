package budget

import (
	"context"
	"sort"
	"sync"
	"time"
)

// Cost represents a single cost record.
//
// Fields:
//   - SessionID: Session identifier
//   - AgentName: Agent name
//   - Model: Model identifier
//   - InputTokens: Number of input tokens
//   - OutputTokens: Number of output tokens
//   - InputCost: Cost for input tokens ($)
//   - OutputCost: Cost for output tokens ($)
//   - TotalCost: Total cost ($)
//   - Timestamp: When cost was recorded
//   - Metadata: Additional metadata
type Cost struct {
	SessionID    string
	AgentName    string
	Model        string
	InputTokens  int
	OutputTokens int
	InputCost    float64
	OutputCost   float64
	TotalCost    float64
	Timestamp    time.Time
	Metadata     map[string]interface{}
}

// ToMap converts Cost to a map for serialization.
func (c *Cost) ToMap() map[string]interface{} {
	return map[string]interface{}{
		"session_id":    c.SessionID,
		"agent_name":    c.AgentName,
		"model":         c.Model,
		"input_tokens":  c.InputTokens,
		"output_tokens": c.OutputTokens,
		"input_cost":    c.InputCost,
		"output_cost":   c.OutputCost,
		"total_cost":    c.TotalCost,
		"timestamp":     c.Timestamp.Format(time.RFC3339),
		"metadata":      c.Metadata,
	}
}

// Storage is the interface for cost storage backends.
type Storage interface {
	// Store saves a cost record.
	Store(ctx context.Context, cost *Cost) error

	// Query retrieves cost records matching the criteria.
	Query(ctx context.Context, sessionID, agentName string, startTime, endTime *time.Time) ([]*Cost, error)
}

// InMemoryStorage provides in-memory storage for cost records.
type InMemoryStorage struct {
	mu    sync.RWMutex
	costs []*Cost
}

// NewInMemoryStorage creates a new in-memory storage instance.
func NewInMemoryStorage() *InMemoryStorage {
	return &InMemoryStorage{
		costs: make([]*Cost, 0),
	}
}

// Store saves a cost record in memory.
func (s *InMemoryStorage) Store(ctx context.Context, cost *Cost) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.costs = append(s.costs, cost)
	return nil
}

// Query retrieves cost records from memory matching the criteria.
func (s *InMemoryStorage) Query(ctx context.Context, sessionID, agentName string, startTime, endTime *time.Time) ([]*Cost, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	results := make([]*Cost, 0)

	for _, cost := range s.costs {
		// Filter by session_id
		if sessionID != "" && cost.SessionID != sessionID {
			continue
		}

		// Filter by agent_name
		if agentName != "" && cost.AgentName != agentName {
			continue
		}

		// Filter by time range
		if startTime != nil && cost.Timestamp.Before(*startTime) {
			continue
		}
		if endTime != nil && cost.Timestamp.After(*endTime) {
			continue
		}

		results = append(results, cost)
	}

	return results, nil
}

// CostTracker tracks LLM costs per session, agent, and globally.
//
// Features:
//   - Per-session cost tracking
//   - Per-agent cost tracking
//   - Global cost tracking
//   - Cost breakdown by model
//   - Time-series cost data
//
// Example:
//
//	tracker := NewCostTracker(nil)
//	cost, _ := tracker.RecordCost(ctx,
//	    "user-123", "assistant", "claude-sonnet-4",
//	    1000, 500, nil)
//	total, _ := tracker.GetSessionCost(ctx, "user-123", nil, nil)
//	fmt.Printf("Session cost: $%.2f\n", total)
type CostTracker struct {
	storage      Storage
	modelPricing *ModelPricing
}

// NewCostTracker creates a new cost tracker.
//
// Args:
//
//	storage: Storage backend (uses in-memory if nil)
//
// Example:
//
//	tracker := NewCostTracker(nil) // Uses default in-memory storage
func NewCostTracker(storage Storage) *CostTracker {
	if storage == nil {
		storage = NewInMemoryStorage()
	}

	return &CostTracker{
		storage:      storage,
		modelPricing: NewModelPricing(),
	}
}

// RecordCost records a cost event.
//
// Args:
//
//	ctx: Context
//	sessionID: Session identifier
//	agentName: Agent name
//	model: Model identifier
//	inputTokens: Number of input tokens
//	outputTokens: Number of output tokens
//	metadata: Optional metadata
//
// Returns:
//
//	Cost record
//
// Example:
//
//	cost, err := tracker.RecordCost(ctx,
//	    "session-1", "assistant", "claude-sonnet-4",
//	    1000, 500, nil)
//	fmt.Printf("$%.4f\n", cost.TotalCost) // $0.0105
func (t *CostTracker) RecordCost(
	ctx context.Context,
	sessionID, agentName, model string,
	inputTokens, outputTokens int,
	metadata map[string]interface{},
) (*Cost, error) {
	// Calculate costs
	inputCost, err := t.modelPricing.Calculate(model, inputTokens, "input")
	if err != nil {
		return nil, err
	}

	outputCost, err := t.modelPricing.Calculate(model, outputTokens, "output")
	if err != nil {
		return nil, err
	}

	totalCost := inputCost + outputCost

	// Create record
	if metadata == nil {
		metadata = make(map[string]interface{})
	}

	cost := &Cost{
		SessionID:    sessionID,
		AgentName:    agentName,
		Model:        model,
		InputTokens:  inputTokens,
		OutputTokens: outputTokens,
		InputCost:    inputCost,
		OutputCost:   outputCost,
		TotalCost:    totalCost,
		Timestamp:    time.Now().UTC(),
		Metadata:     metadata,
	}

	// Store
	if err := t.storage.Store(ctx, cost); err != nil {
		return nil, err
	}

	return cost, nil
}

// GetSessionCost returns the total cost for a session.
//
// Args:
//
//	ctx: Context
//	sessionID: Session identifier
//	startTime: Optional start time
//	endTime: Optional end time
//
// Returns:
//
//	Total cost in dollars
//
// Example:
//
//	total, _ := tracker.GetSessionCost(ctx, "session-1", nil, nil)
//	fmt.Printf("$%.2f\n", total) // $1.50
func (t *CostTracker) GetSessionCost(ctx context.Context, sessionID string, startTime, endTime *time.Time) (float64, error) {
	costs, err := t.storage.Query(ctx, sessionID, "", startTime, endTime)
	if err != nil {
		return 0, err
	}

	total := 0.0
	for _, cost := range costs {
		total += cost.TotalCost
	}
	return total, nil
}

// GetAgentCost returns the total cost for an agent.
//
// Args:
//
//	ctx: Context
//	agentName: Agent name
//	startTime: Optional start time
//	endTime: Optional end time
//
// Returns:
//
//	Total cost in dollars
func (t *CostTracker) GetAgentCost(ctx context.Context, agentName string, startTime, endTime *time.Time) (float64, error) {
	costs, err := t.storage.Query(ctx, "", agentName, startTime, endTime)
	if err != nil {
		return 0, err
	}

	total := 0.0
	for _, cost := range costs {
		total += cost.TotalCost
	}
	return total, nil
}

// GetGlobalCost returns the total global cost.
//
// Args:
//
//	ctx: Context
//	startTime: Optional start time
//	endTime: Optional end time
//
// Returns:
//
//	Total cost in dollars
func (t *CostTracker) GetGlobalCost(ctx context.Context, startTime, endTime *time.Time) (float64, error) {
	costs, err := t.storage.Query(ctx, "", "", startTime, endTime)
	if err != nil {
		return 0, err
	}

	total := 0.0
	for _, cost := range costs {
		total += cost.TotalCost
	}
	return total, nil
}

// GetBreakdown returns cost breakdown by model.
//
// Args:
//
//	ctx: Context
//	sessionID: Optional session filter
//	agentName: Optional agent filter
//
// Returns:
//
//	Map from model to total cost
//
// Example:
//
//	breakdown, _ := tracker.GetBreakdown(ctx, "session-1", "")
//	// map[claude-sonnet-4:2.50 claude-opus-4:5.75]
func (t *CostTracker) GetBreakdown(ctx context.Context, sessionID, agentName string) (map[string]float64, error) {
	costs, err := t.storage.Query(ctx, sessionID, agentName, nil, nil)
	if err != nil {
		return nil, err
	}

	breakdown := make(map[string]float64)
	for _, cost := range costs {
		breakdown[cost.Model] += cost.TotalCost
	}

	return breakdown, nil
}

// GetTopSessions returns top N sessions by cost.
//
// Args:
//
//	ctx: Context
//	limit: Number of sessions to return
//	startTime: Optional start time
//	endTime: Optional end time
//
// Returns:
//
//	List of (sessionID, totalCost) tuples, sorted by cost descending
//
// Example:
//
//	top, _ := tracker.GetTopSessions(ctx, 5, nil, nil)
//	for _, item := range top {
//	    fmt.Printf("%s: $%.2f\n", item.SessionID, item.TotalCost)
//	}
func (t *CostTracker) GetTopSessions(ctx context.Context, limit int, startTime, endTime *time.Time) ([]SessionCost, error) {
	costs, err := t.storage.Query(ctx, "", "", startTime, endTime)
	if err != nil {
		return nil, err
	}

	sessionTotals := make(map[string]float64)
	for _, cost := range costs {
		sessionTotals[cost.SessionID] += cost.TotalCost
	}

	// Convert to slice and sort
	results := make([]SessionCost, 0, len(sessionTotals))
	for sessionID, total := range sessionTotals {
		results = append(results, SessionCost{SessionID: sessionID, TotalCost: total})
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].TotalCost > results[j].TotalCost
	})

	if len(results) > limit {
		results = results[:limit]
	}

	return results, nil
}

// SessionCost represents a session with its total cost.
type SessionCost struct {
	SessionID string
	TotalCost float64
}

// GetTopAgents returns top N agents by cost.
//
// Args:
//
//	ctx: Context
//	limit: Number of agents to return
//	startTime: Optional start time
//	endTime: Optional end time
//
// Returns:
//
//	List of (agentName, totalCost) tuples
func (t *CostTracker) GetTopAgents(ctx context.Context, limit int, startTime, endTime *time.Time) ([]AgentCost, error) {
	costs, err := t.storage.Query(ctx, "", "", startTime, endTime)
	if err != nil {
		return nil, err
	}

	agentTotals := make(map[string]float64)
	for _, cost := range costs {
		agentTotals[cost.AgentName] += cost.TotalCost
	}

	// Convert to slice and sort
	results := make([]AgentCost, 0, len(agentTotals))
	for agentName, total := range agentTotals {
		results = append(results, AgentCost{AgentName: agentName, TotalCost: total})
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].TotalCost > results[j].TotalCost
	})

	if len(results) > limit {
		results = results[:limit]
	}

	return results, nil
}

// AgentCost represents an agent with its total cost.
type AgentCost struct {
	AgentName string
	TotalCost float64
}

// GetStatistics returns cost statistics.
//
// Args:
//
//	ctx: Context
//	sessionID: Optional session filter
//	agentName: Optional agent filter
//
// Returns:
//
//	Map with statistics (total_cost, total_tokens, avg_cost_per_request, etc.)
func (t *CostTracker) GetStatistics(ctx context.Context, sessionID, agentName string) (map[string]interface{}, error) {
	costs, err := t.storage.Query(ctx, sessionID, agentName, nil, nil)
	if err != nil {
		return nil, err
	}

	if len(costs) == 0 {
		return map[string]interface{}{
			"total_cost":             0.0,
			"total_requests":         0,
			"total_input_tokens":     0,
			"total_output_tokens":    0,
			"avg_cost_per_request":   0.0,
			"avg_tokens_per_request": 0.0,
		}, nil
	}

	totalCost := 0.0
	totalInputTokens := 0
	totalOutputTokens := 0

	for _, cost := range costs {
		totalCost += cost.TotalCost
		totalInputTokens += cost.InputTokens
		totalOutputTokens += cost.OutputTokens
	}

	totalTokens := totalInputTokens + totalOutputTokens
	numRequests := len(costs)

	return map[string]interface{}{
		"total_cost":             totalCost,
		"total_requests":         numRequests,
		"total_input_tokens":     totalInputTokens,
		"total_output_tokens":    totalOutputTokens,
		"total_tokens":           totalTokens,
		"avg_cost_per_request":   totalCost / float64(numRequests),
		"avg_tokens_per_request": float64(totalTokens) / float64(numRequests),
	}, nil
}
