package budget

import (
	"context"
	"fmt"
	"log"
	"sync"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// BudgetExceededError is raised when budget is exceeded.
type BudgetExceededError struct {
	Message string
}

func (e *BudgetExceededError) Error() string {
	return e.Message
}

// ModelSwitcher is a function that switches models when budget is exceeded.
type ModelSwitcher func(currentModel string) string

// BudgetLimiter is middleware that enforces cost budgets.
//
// Stops agent execution when budget exceeded. Supports per-session,
// per-agent, and global budgets.
//
// Actions on budget exceeded:
//   - "error": Raise BudgetExceededError
//   - "warning": Log warning and continue
//   - "switch_model": Switch to cheaper model (requires model_switcher)
//
// Example:
//
//	tracker := NewCostTracker(nil)
//	limiter := NewBudgetLimiter(
//	    tracker,
//	    &BudgetLimiterConfig{
//	        SessionBudget: 10.00, // $10 per session
//	        Action:        "error",
//	    },
//	)
//	wrappedAgent := limiter.Wrap(myAgent)
//	// Agent will raise BudgetExceededError if session exceeds $10
type BudgetLimiter struct {
	tracker           *CostTracker
	sessionBudget     *float64
	agentBudget       *float64
	globalBudget      *float64
	action            string
	modelSwitcher     ModelSwitcher
	agentNameOverride string
}

// BudgetLimiterConfig specifies configuration for budget limiter.
type BudgetLimiterConfig struct {
	SessionBudget *float64      // Max $ per session (nil = unlimited)
	AgentBudget   *float64      // Max $ per agent (nil = unlimited)
	GlobalBudget  *float64      // Max $ globally (nil = unlimited)
	Action        string        // "error", "warning", "switch_model"
	ModelSwitcher ModelSwitcher // Function to switch models (for switch_model action)
	AgentName     string        // Override agent name for tracking
}

// NewBudgetLimiter creates a new budget limiter.
//
// Args:
//
//	tracker: CostTracker instance
//	config: Budget limiter configuration
//
// Example:
//
//	limiter := NewBudgetLimiter(tracker, &BudgetLimiterConfig{
//	    SessionBudget: pointerTo(10.0),
//	    Action: "error",
//	})
func NewBudgetLimiter(tracker *CostTracker, config *BudgetLimiterConfig) (*BudgetLimiter, error) {
	if config.Action != "error" && config.Action != "warning" && config.Action != "switch_model" {
		return nil, fmt.Errorf("action must be 'error', 'warning', or 'switch_model', got: %s", config.Action)
	}

	if config.Action == "switch_model" && config.ModelSwitcher == nil {
		return nil, fmt.Errorf("model_switcher required when action='switch_model'")
	}

	return &BudgetLimiter{
		tracker:           tracker,
		sessionBudget:     config.SessionBudget,
		agentBudget:       config.AgentBudget,
		globalBudget:      config.GlobalBudget,
		action:            config.Action,
		modelSwitcher:     config.ModelSwitcher,
		agentNameOverride: config.AgentName,
	}, nil
}

// Wrap wraps an agent with budget enforcement.
//
// Args:
//
//	agent: Agent to wrap
//
// Returns:
//
//	Wrapped agent with budget enforcement
func (l *BudgetLimiter) Wrap(agent agenkit.Agent) agenkit.Agent {
	return &budgetLimitedAgent{
		agent:   agent,
		limiter: l,
	}
}

type budgetLimitedAgent struct {
	agent   agenkit.Agent
	limiter *BudgetLimiter
}

func (a *budgetLimitedAgent) Name() string {
	return a.agent.Name()
}

func (a *budgetLimitedAgent) Capabilities() []string {
	return a.agent.Capabilities()
}

func (a *budgetLimitedAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Get agent name
	agentName := a.limiter.agentNameOverride
	if agentName == "" {
		agentName = a.agent.Name()
	}

	// Extract session_id from message metadata
	sessionID := "default"
	if message.Metadata != nil {
		if sid, ok := message.Metadata["session_id"].(string); ok {
			sessionID = sid
		}
	}

	// Check budgets before processing
	if err := a.limiter.checkBudgets(ctx, sessionID, agentName); err != nil {
		return nil, err
	}

	// Process message
	response, err := a.agent.Process(ctx, message)
	if err != nil {
		return nil, err
	}

	// Record cost after processing
	if err := a.limiter.recordCost(ctx, sessionID, agentName, *response); err != nil {
		log.Printf("WARNING: Failed to record cost: %v", err)
	}

	return response, nil
}

func (l *BudgetLimiter) checkBudgets(ctx context.Context, sessionID, agentName string) error {
	// Check session budget
	if l.sessionBudget != nil {
		currentCost, err := l.tracker.GetSessionCost(ctx, sessionID, nil, nil)
		if err != nil {
			return err
		}
		if currentCost >= *l.sessionBudget {
			return l.handleBudgetExceeded(
				fmt.Sprintf("Session budget $%.2f exceeded (current: $%.2f)", *l.sessionBudget, currentCost),
				sessionID,
				"",
			)
		}
	}

	// Check agent budget
	if l.agentBudget != nil {
		currentCost, err := l.tracker.GetAgentCost(ctx, agentName, nil, nil)
		if err != nil {
			return err
		}
		if currentCost >= *l.agentBudget {
			return l.handleBudgetExceeded(
				fmt.Sprintf("Agent '%s' budget $%.2f exceeded (current: $%.2f)", agentName, *l.agentBudget, currentCost),
				"",
				agentName,
			)
		}
	}

	// Check global budget
	if l.globalBudget != nil {
		currentCost, err := l.tracker.GetGlobalCost(ctx, nil, nil)
		if err != nil {
			return err
		}
		if currentCost >= *l.globalBudget {
			return l.handleBudgetExceeded(
				fmt.Sprintf("Global budget $%.2f exceeded (current: $%.2f)", *l.globalBudget, currentCost),
				"",
				"",
			)
		}
	}

	return nil
}

func (l *BudgetLimiter) handleBudgetExceeded(message, sessionID, agentName string) error {
	switch l.action {
	case "error":
		return &BudgetExceededError{Message: message}
	case "warning":
		log.Printf("WARNING: Budget exceeded: %s", message)
		return nil
	case "switch_model":
		log.Printf("INFO: Budget threshold reached: %s", message)
		return nil
	default:
		return fmt.Errorf("unknown action: %s", l.action)
	}
}

func (l *BudgetLimiter) recordCost(ctx context.Context, sessionID, agentName string, response agenkit.Message) error {
	// Check if response has usage metadata
	if response.Metadata == nil {
		return nil
	}

	usage, ok := response.Metadata["usage"].(map[string]interface{})
	if !ok {
		log.Printf("DEBUG: No usage metadata in response, skipping cost recording")
		return nil
	}

	model := "unknown"
	if m, ok := response.Metadata["model"].(string); ok {
		model = m
	}

	// Extract token counts
	promptTokens := 0
	completionTokens := 0

	if pt, ok := usage["prompt_tokens"].(int); ok {
		promptTokens = pt
	} else if pt, ok := usage["prompt_tokens"].(float64); ok {
		promptTokens = int(pt)
	}

	if ct, ok := usage["completion_tokens"].(int); ok {
		completionTokens = ct
	} else if ct, ok := usage["completion_tokens"].(float64); ok {
		completionTokens = int(ct)
	}

	// Record cost
	metadata := map[string]interface{}{
		"model": model,
	}
	if msgID, ok := response.Metadata["message_id"]; ok {
		metadata["message_id"] = msgID
	}

	_, err := l.tracker.RecordCost(ctx, sessionID, agentName, model, promptTokens, completionTokens, metadata)
	return err
}

// GetRemainingBudget returns remaining budget(s).
//
// Args:
//
//	ctx: Context
//	sessionID: Session identifier for session budget
//	agentName: Agent name for agent budget
//
// Returns:
//
//	Map with remaining budgets (nil = unlimited)
//
// Example:
//
//	remaining, _ := limiter.GetRemainingBudget(ctx, "session-1", "")
//	// map[session:8.50 agent:<nil> global:<nil>]
func (l *BudgetLimiter) GetRemainingBudget(ctx context.Context, sessionID, agentName string) (map[string]*float64, error) {
	remaining := map[string]*float64{
		"session": nil,
		"agent":   nil,
		"global":  nil,
	}

	// Session budget
	if l.sessionBudget != nil && sessionID != "" {
		current, err := l.tracker.GetSessionCost(ctx, sessionID, nil, nil)
		if err != nil {
			return nil, err
		}
		rem := max(0.0, *l.sessionBudget-current)
		remaining["session"] = &rem
	}

	// Agent budget
	if l.agentBudget != nil && agentName != "" {
		current, err := l.tracker.GetAgentCost(ctx, agentName, nil, nil)
		if err != nil {
			return nil, err
		}
		rem := max(0.0, *l.agentBudget-current)
		remaining["agent"] = &rem
	}

	// Global budget
	if l.globalBudget != nil {
		current, err := l.tracker.GetGlobalCost(ctx, nil, nil)
		if err != nil {
			return nil, err
		}
		rem := max(0.0, *l.globalBudget-current)
		remaining["global"] = &rem
	}

	return remaining, nil
}

// BudgetWarning is budget warning middleware (logs warnings at thresholds).
//
// Similar to BudgetLimiter but only warns at specified thresholds
// instead of stopping execution.
//
// Example:
//
//	warning := NewBudgetWarning(tracker, &BudgetWarningConfig{
//	    SessionBudget:      pointerTo(10.0),
//	    WarningThresholds: []float64{0.5, 0.75, 0.9}, // Warn at 50%, 75%, 90%
//	})
type BudgetWarning struct {
	tracker           *CostTracker
	sessionBudget     *float64
	agentBudget       *float64
	globalBudget      *float64
	warningThresholds []float64
	agentNameOverride string
	mu                sync.RWMutex
	sessionWarnings   map[string]map[float64]bool
	agentWarnings     map[string]map[float64]bool
	globalWarnings    map[float64]bool
}

// BudgetWarningConfig specifies configuration for budget warning.
type BudgetWarningConfig struct {
	SessionBudget     *float64
	AgentBudget       *float64
	GlobalBudget      *float64
	WarningThresholds []float64 // [0.5, 0.75, 0.9]
	AgentName         string
}

// NewBudgetWarning creates a new budget warning middleware.
func NewBudgetWarning(tracker *CostTracker, config *BudgetWarningConfig) *BudgetWarning {
	thresholds := config.WarningThresholds
	if thresholds == nil {
		thresholds = []float64{0.5, 0.75, 0.9}
	}

	return &BudgetWarning{
		tracker:           tracker,
		sessionBudget:     config.SessionBudget,
		agentBudget:       config.AgentBudget,
		globalBudget:      config.GlobalBudget,
		warningThresholds: thresholds,
		agentNameOverride: config.AgentName,
		sessionWarnings:   make(map[string]map[float64]bool),
		agentWarnings:     make(map[string]map[float64]bool),
		globalWarnings:    make(map[float64]bool),
	}
}

// Wrap wraps an agent with budget warnings.
func (w *BudgetWarning) Wrap(agent agenkit.Agent) agenkit.Agent {
	return &budgetWarnedAgent{
		agent:   agent,
		warning: w,
	}
}

type budgetWarnedAgent struct {
	agent   agenkit.Agent
	warning *BudgetWarning
}

func (a *budgetWarnedAgent) Name() string {
	return a.agent.Name()
}

func (a *budgetWarnedAgent) Capabilities() []string {
	return a.agent.Capabilities()
}

func (a *budgetWarnedAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Get agent name
	agentName := a.warning.agentNameOverride
	if agentName == "" {
		agentName = a.agent.Name()
	}

	// Extract session_id
	sessionID := "default"
	if message.Metadata != nil {
		if sid, ok := message.Metadata["session_id"].(string); ok {
			sessionID = sid
		}
	}

	// Check and log warnings
	if err := a.warning.checkWarnings(ctx, sessionID, agentName); err != nil {
		log.Printf("WARNING: Failed to check budget warnings: %v", err)
	}

	// Process
	response, err := a.agent.Process(ctx, message)
	if err != nil {
		return nil, err
	}

	// Record cost
	if response.Metadata != nil {
		if usage, ok := response.Metadata["usage"].(map[string]interface{}); ok {
			model := "unknown"
			if m, ok := response.Metadata["model"].(string); ok {
				model = m
			}

			promptTokens := 0
			completionTokens := 0

			if pt, ok := usage["prompt_tokens"].(int); ok {
				promptTokens = pt
			} else if pt, ok := usage["prompt_tokens"].(float64); ok {
				promptTokens = int(pt)
			}

			if ct, ok := usage["completion_tokens"].(int); ok {
				completionTokens = ct
			} else if ct, ok := usage["completion_tokens"].(float64); ok {
				completionTokens = int(ct)
			}

			if _, err := a.warning.tracker.RecordCost(ctx, sessionID, agentName, model, promptTokens, completionTokens, nil); err != nil {
				log.Printf("WARNING: Failed to record cost: %v", err)
			}
		}
	}

	return response, nil
}

func (w *BudgetWarning) checkWarnings(ctx context.Context, sessionID, agentName string) error {
	w.mu.Lock()
	defer w.mu.Unlock()

	// Session warnings
	if w.sessionBudget != nil {
		current, err := w.tracker.GetSessionCost(ctx, sessionID, nil, nil)
		if err != nil {
			return err
		}
		usagePct := current / *w.sessionBudget

		if _, exists := w.sessionWarnings[sessionID]; !exists {
			w.sessionWarnings[sessionID] = make(map[float64]bool)
		}

		for _, threshold := range w.warningThresholds {
			if usagePct >= threshold && !w.sessionWarnings[sessionID][threshold] {
				log.Printf("WARNING: Session %s at %.0f%% of budget ($%.2f / $%.2f)",
					sessionID, usagePct*100, current, *w.sessionBudget)
				w.sessionWarnings[sessionID][threshold] = true
			}
		}
	}

	// Agent warnings
	if w.agentBudget != nil {
		current, err := w.tracker.GetAgentCost(ctx, agentName, nil, nil)
		if err != nil {
			return err
		}
		usagePct := current / *w.agentBudget

		if _, exists := w.agentWarnings[agentName]; !exists {
			w.agentWarnings[agentName] = make(map[float64]bool)
		}

		for _, threshold := range w.warningThresholds {
			if usagePct >= threshold && !w.agentWarnings[agentName][threshold] {
				log.Printf("WARNING: Agent %s at %.0f%% of budget ($%.2f / $%.2f)",
					agentName, usagePct*100, current, *w.agentBudget)
				w.agentWarnings[agentName][threshold] = true
			}
		}
	}

	// Global warnings
	if w.globalBudget != nil {
		current, err := w.tracker.GetGlobalCost(ctx, nil, nil)
		if err != nil {
			return err
		}
		usagePct := current / *w.globalBudget

		for _, threshold := range w.warningThresholds {
			if usagePct >= threshold && !w.globalWarnings[threshold] {
				log.Printf("WARNING: Global cost at %.0f%% of budget ($%.2f / $%.2f)",
					usagePct*100, current, *w.globalBudget)
				w.globalWarnings[threshold] = true
			}
		}
	}

	return nil
}

func max(a, b float64) float64 {
	if a > b {
		return a
	}
	return b
}
