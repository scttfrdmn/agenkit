package checkpointing

import (
	"context"
	"fmt"
	"log"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// DurableAgent wraps agent with automatic checkpointing and resume capability.
//
// Features:
//   - Automatic checkpointing (every N steps or on demand)
//   - Resume from latest checkpoint on startup
//   - State persistence across restarts
//   - Error recovery with checkpoint rollback
//
// Example:
//
//	storage, _ := NewFileStorage("./checkpoints")
//	durable := NewDurableAgent(
//	    myAgent,
//	    storage,
//	    10,  // Checkpoint every 10 steps
//	    true, // Auto-resume
//	    "",
//	)
//
//	// Use agent (automatically checkpoints)
//	response, _ := durable.Process(ctx, message, "session-1")
//
//	// Resume from checkpoint
//	state, _ := durable.Resume(ctx, "session-1", "")
type DurableAgent struct {
	agent              agenkit.Agent
	agentName          string
	checkpointInterval int
	autoResume         bool
	manager            *CheckpointManager

	// Track state per session
	sessionState    map[string]map[string]interface{}
	sessionSteps    map[string]int
	sessionMessages map[string][]agenkit.Message
	sessionResumed  map[string]bool
}

// NewDurableAgent creates a new durable agent.
//
// Args:
//
//	agent: Agent to wrap
//	storage: Checkpoint storage (nil = in-memory)
//	checkpointInterval: Checkpoint every N steps
//	autoResume: Automatically resume from latest checkpoint on first call
//	agentName: Override agent name (empty = use agent.Name())
//
// Example:
//
//	storage, _ := NewFileStorage("./checkpoints")
//	durable := NewDurableAgent(myAgent, storage, 10, true, "")
func NewDurableAgent(
	agent agenkit.Agent,
	storage CheckpointStorage,
	checkpointInterval int,
	autoResume bool,
	agentName string,
) *DurableAgent {
	if agentName == "" {
		agentName = agent.Name()
	}

	manager := NewCheckpointManager(storage, checkpointInterval)

	return &DurableAgent{
		agent:              agent,
		agentName:          agentName,
		checkpointInterval: checkpointInterval,
		autoResume:         autoResume,
		manager:            manager,
		sessionState:       make(map[string]map[string]interface{}),
		sessionSteps:       make(map[string]int),
		sessionMessages:    make(map[string][]agenkit.Message),
		sessionResumed:     make(map[string]bool),
	}
}

// Process processes message with automatic checkpointing.
//
// Args:
//
//	ctx: Context
//	message: Input message
//	sessionID: Session identifier
//
// Returns:
//
//	Response message
//
// Example:
//
//	response, _ := durable.Process(ctx, message, "session-1")
func (d *DurableAgent) Process(ctx context.Context, message *agenkit.Message, sessionID string) (*agenkit.Message, error) {
	// Auto-resume on first call if enabled
	if d.autoResume && !d.sessionResumed[sessionID] {
		_, err := d.Resume(ctx, sessionID, "")
		if err != nil {
			log.Printf("WARNING: Failed to auto-resume: %v", err)
		}
		d.sessionResumed[sessionID] = true
	}

	// Initialize session if needed
	if _, ok := d.sessionState[sessionID]; !ok {
		d.sessionState[sessionID] = make(map[string]interface{})
		d.sessionSteps[sessionID] = 0
		d.sessionMessages[sessionID] = make([]agenkit.Message, 0)
	}

	// Increment step
	d.sessionSteps[sessionID]++
	currentStep := d.sessionSteps[sessionID]

	// Add message to history
	d.sessionMessages[sessionID] = append(d.sessionMessages[sessionID], *message)

	// Process message
	response, err := d.agent.Process(ctx, message)
	if err != nil {
		log.Printf("ERROR: Error processing message at step %d: %v", currentStep, err)

		// Try to rollback to last checkpoint
		latest, loadErr := d.manager.GetLatest(ctx, sessionID)
		if loadErr == nil && latest != nil {
			log.Printf("INFO: Rolling back to checkpoint at step %d", latest.StepNumber)
			_, resumeErr := d.Resume(ctx, sessionID, latest.CheckpointID)
			if resumeErr != nil {
				log.Printf("WARNING: Failed to rollback: %v", resumeErr)
			}
		}

		return nil, err
	}

	// Add response to history
	d.sessionMessages[sessionID] = append(d.sessionMessages[sessionID], *response)

	// Update state
	d.updateState(sessionID, message, response)

	// Checkpoint if needed
	if d.manager.ShouldCheckpoint(sessionID, currentStep) {
		_, err := d.Checkpoint(ctx, sessionID, nil)
		if err != nil {
			log.Printf("WARNING: Failed to create checkpoint: %v", err)
		}
	}

	return response, nil
}

// Checkpoint creates checkpoint for current state.
//
// Args:
//
//	ctx: Context
//	sessionID: Session identifier
//	metadata: Optional metadata to attach
//
// Returns:
//
//	checkpointID: Unique checkpoint identifier
//
// Example:
//
//	checkpointID, _ := durable.Checkpoint(ctx, "session-1", nil)
func (d *DurableAgent) Checkpoint(ctx context.Context, sessionID string, metadata map[string]interface{}) (string, error) {
	currentStep := d.sessionSteps[sessionID]
	state := d.sessionState[sessionID]
	messages := d.sessionMessages[sessionID]

	checkpointID, err := d.manager.CreateCheckpoint(
		ctx,
		sessionID,
		d.agentName,
		currentStep,
		state,
		messages,
		metadata,
		nil,
	)
	if err != nil {
		return "", err
	}

	log.Printf("INFO: Checkpointed session %s at step %d", sessionID, currentStep)

	return checkpointID, nil
}

// Resume resumes from checkpoint.
//
// Args:
//
//	ctx: Context
//	sessionID: Session identifier
//	checkpointID: Specific checkpoint to resume from (empty = latest)
//
// Returns:
//
//	Restored state or nil if no checkpoint found
//
// Example:
//
//	state, _ := durable.Resume(ctx, "session-1", "")
func (d *DurableAgent) Resume(ctx context.Context, sessionID string, checkpointID string) (map[string]interface{}, error) {
	var checkpoint *Checkpoint
	var err error

	// Load checkpoint
	if checkpointID != "" {
		checkpoint, err = d.manager.LoadCheckpoint(ctx, checkpointID)
	} else {
		checkpoint, err = d.manager.GetLatest(ctx, sessionID)
	}

	if err != nil {
		return nil, err
	}

	if checkpoint == nil {
		log.Printf("INFO: No checkpoint found for %s, starting fresh", sessionID)
		return nil, nil
	}

	// Restore state
	d.sessionState[sessionID] = make(map[string]interface{})
	for k, v := range checkpoint.State {
		d.sessionState[sessionID][k] = v
	}

	d.sessionSteps[sessionID] = checkpoint.StepNumber

	d.sessionMessages[sessionID] = make([]agenkit.Message, len(checkpoint.Messages))
	copy(d.sessionMessages[sessionID], checkpoint.Messages)

	log.Printf("INFO: Resumed session %s from checkpoint at step %d",
		sessionID, checkpoint.StepNumber)

	return d.sessionState[sessionID], nil
}

// GetState gets current state for session.
//
// Args:
//
//	sessionID: Session identifier
//
// Returns:
//
//	Copy of current state
func (d *DurableAgent) GetState(sessionID string) map[string]interface{} {
	state, ok := d.sessionState[sessionID]
	if !ok {
		return make(map[string]interface{})
	}

	// Return copy
	copy := make(map[string]interface{})
	for k, v := range state {
		copy[k] = v
	}

	return copy
}

// SetState sets state for session.
//
// Args:
//
//	sessionID: Session identifier
//	state: New state
func (d *DurableAgent) SetState(sessionID string, state map[string]interface{}) {
	d.sessionState[sessionID] = make(map[string]interface{})
	for k, v := range state {
		d.sessionState[sessionID][k] = v
	}
}

// GetMessages gets message history for session.
//
// Args:
//
//	sessionID: Session identifier
//
// Returns:
//
//	Copy of message history
func (d *DurableAgent) GetMessages(sessionID string) []agenkit.Message {
	messages, ok := d.sessionMessages[sessionID]
	if !ok {
		return make([]agenkit.Message, 0)
	}

	// Return copy
	copy := make([]agenkit.Message, len(messages))
	copyCount := copyMessages(copy, messages)
	return copy[:copyCount]
}

// ResetSession resets session (clear state and messages).
//
// Args:
//
//	sessionID: Session identifier
func (d *DurableAgent) ResetSession(sessionID string) {
	delete(d.sessionState, sessionID)
	delete(d.sessionSteps, sessionID)
	delete(d.sessionMessages, sessionID)
	delete(d.sessionResumed, sessionID)
}

// updateState updates session state (can be overridden for custom state tracking).
//
// Default implementation tracks message count and last message.
func (d *DurableAgent) updateState(sessionID string, inputMessage, outputMessage *agenkit.Message) {
	state := d.sessionState[sessionID]

	// Update basic stats
	messageCount, ok := state["message_count"].(int)
	if !ok {
		messageCount = 0
	}
	state["message_count"] = messageCount + 1
	state["last_input"] = inputMessage.Content
	state["last_output"] = outputMessage.Content

	// Track any metadata from response
	if outputMessage.Metadata != nil {
		state["last_metadata"] = outputMessage.Metadata
	}
}

// ListCheckpoints lists checkpoints for session.
//
// Args:
//
//	ctx: Context
//	sessionID: Session identifier
//	limit: Optional limit on number of checkpoints (0 = no limit)
//
// Returns:
//
//	List of checkpoints
func (d *DurableAgent) ListCheckpoints(ctx context.Context, sessionID string, limit int) ([]*Checkpoint, error) {
	return d.manager.ListCheckpoints(ctx, sessionID, limit)
}

// DeleteCheckpoints deletes all checkpoints for session.
//
// Args:
//
//	ctx: Context
//	sessionID: Session identifier
//
// Returns:
//
//	Number of checkpoints deleted
func (d *DurableAgent) DeleteCheckpoints(ctx context.Context, sessionID string) (int, error) {
	count, err := d.manager.DeleteSession(ctx, sessionID)
	if err != nil {
		return 0, err
	}

	d.ResetSession(sessionID)

	return count, nil
}

// GetSessionStats gets statistics for session.
//
// Args:
//
//	ctx: Context
//	sessionID: Session identifier
//
// Returns:
//
//	Map with statistics
func (d *DurableAgent) GetSessionStats(ctx context.Context, sessionID string) (map[string]interface{}, error) {
	checkpointStats, err := d.manager.GetSessionStats(ctx, sessionID)
	if err != nil {
		return nil, err
	}

	stats := make(map[string]interface{})
	for k, v := range checkpointStats {
		stats[k] = v
	}

	stats["current_step"] = d.sessionSteps[sessionID]
	stats["message_count"] = len(d.sessionMessages[sessionID])
	stats["state_size"] = len(d.sessionState[sessionID])

	return stats, nil
}

// Name returns the agent name.
func (d *DurableAgent) Name() string {
	return d.agentName
}

// Capabilities returns the agent capabilities.
func (d *DurableAgent) Capabilities() []string {
	return d.agent.Capabilities()
}

// Helper function to copy messages
func copyMessages(dst, src []agenkit.Message) int {
	n := len(src)
	if len(dst) < n {
		n = len(dst)
	}
	for i := 0; i < n; i++ {
		dst[i] = src[i]
	}
	return n
}

// MakeDurable is a convenience function to make an agent durable.
//
// Args:
//
//	agent: Agent to make durable
//	checkpointDir: Directory for checkpoints
//	checkpointInterval: Checkpoint every N steps
//	agentName: Override agent name (empty = use agent.Name())
//
// Returns:
//
//	DurableAgent wrapping the original agent
//
// Example:
//
//	durableAgent, _ := MakeDurable(
//	    myAgent,
//	    "./checkpoints",
//	    5,  // Checkpoint every 5 steps
//	    "",
//	)
//
//	// Use like normal agent
//	response, _ := durableAgent.Process(ctx, message, "session-1")
func MakeDurable(agent agenkit.Agent, checkpointDir string, checkpointInterval int, agentName string) (*DurableAgent, error) {
	storage, err := NewFileStorage(checkpointDir)
	if err != nil {
		return nil, fmt.Errorf("failed to create checkpoint storage: %w", err)
	}

	return NewDurableAgent(
		agent,
		storage,
		checkpointInterval,
		true, // auto-resume
		agentName,
	), nil
}
