package checkpointing

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/google/uuid"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// CheckpointManager manages checkpoints for long-running agents.
//
// Features:
//   - Create checkpoints at key points
//   - Resume from latest checkpoint
//   - Replay from specific checkpoint
//   - Time-travel debugging
//   - Automatic checkpoint creation (every N steps)
//
// Example:
//
//	manager := NewCheckpointManager(nil, 0)
//
//	// Create checkpoint
//	checkpointID, _ := manager.CreateCheckpoint(ctx,
//	    "session-1",
//	    "assistant",
//	    10,
//	    map[string]interface{}{"counter": 10},
//	    conversationHistory,
//	    nil,
//	    nil,
//	)
//
//	// Resume from latest
//	checkpoint, _ := manager.GetLatest(ctx, "session-1")
//	restoredState := checkpoint.State
type CheckpointManager struct {
	storage                CheckpointStorage
	autoCheckpointInterval int
	sessionSteps           map[string]int
	sessionLastCheckpoint  map[string]string
}

// NewCheckpointManager creates a new checkpoint manager.
//
// Args:
//
//	storage: Checkpoint storage backend (nil = in-memory)
//	autoCheckpointInterval: Automatically checkpoint every N steps (0 = manual only)
//
// Example:
//
//	manager := NewCheckpointManager(nil, 10) // In-memory, auto-checkpoint every 10 steps
func NewCheckpointManager(storage CheckpointStorage, autoCheckpointInterval int) *CheckpointManager {
	if storage == nil {
		storage = NewInMemoryStorage()
	}

	return &CheckpointManager{
		storage:                storage,
		autoCheckpointInterval: autoCheckpointInterval,
		sessionSteps:           make(map[string]int),
		sessionLastCheckpoint:  make(map[string]string),
	}
}

// CreateCheckpoint creates a new checkpoint.
//
// Args:
//
//	ctx: Context
//	sessionID: Session identifier
//	agentName: Agent name
//	stepNumber: Sequential step number
//	state: Agent state to save
//	messages: Conversation messages
//	metadata: Optional metadata
//	parentCheckpointID: ID of previous checkpoint
//
// Returns:
//
//	checkpointID: Unique identifier for this checkpoint
//
// Example:
//
//	checkpointID, _ := manager.CreateCheckpoint(ctx,
//	    "session-1",
//	    "assistant",
//	    5,
//	    map[string]interface{}{"counter": 5},
//	    []agenkit.Message{msg1, msg2},
//	    nil,
//	    nil,
//	)
func (m *CheckpointManager) CreateCheckpoint(
	ctx context.Context,
	sessionID string,
	agentName string,
	stepNumber int,
	state map[string]interface{},
	messages []agenkit.Message,
	metadata map[string]interface{},
	parentCheckpointID *string,
) (string, error) {
	checkpointID := uuid.New().String()

	// Use last checkpoint as parent if not specified
	if parentCheckpointID == nil {
		if lastID, ok := m.sessionLastCheckpoint[sessionID]; ok {
			parentCheckpointID = &lastID
		}
	}

	if metadata == nil {
		metadata = make(map[string]interface{})
	}

	checkpoint := &Checkpoint{
		CheckpointID:       checkpointID,
		SessionID:          sessionID,
		AgentName:          agentName,
		Timestamp:          time.Now().UTC(),
		StepNumber:         stepNumber,
		State:              state,
		Messages:           messages,
		Metadata:           metadata,
		ParentCheckpointID: parentCheckpointID,
	}

	if err := m.storage.Save(ctx, checkpoint); err != nil {
		return "", err
	}

	// Update tracking
	m.sessionLastCheckpoint[sessionID] = checkpointID
	m.sessionSteps[sessionID] = stepNumber

	log.Printf("INFO: Created checkpoint %s for %s at step %d", checkpointID, sessionID, stepNumber)

	return checkpointID, nil
}

// ShouldCheckpoint determines if checkpoint should be created (for auto-checkpointing).
//
// Args:
//
//	sessionID: Session identifier
//	stepNumber: Current step number
//
// Returns:
//
//	true if checkpoint should be created
func (m *CheckpointManager) ShouldCheckpoint(sessionID string, stepNumber int) bool {
	if m.autoCheckpointInterval == 0 {
		return false
	}

	lastStep, ok := m.sessionSteps[sessionID]
	if !ok {
		lastStep = 0
	}

	stepsSinceCheckpoint := stepNumber - lastStep

	return stepsSinceCheckpoint >= m.autoCheckpointInterval
}

// GetLatest gets latest checkpoint for session.
//
// Args:
//
//	ctx: Context
//	sessionID: Session identifier
//
// Returns:
//
//	Latest checkpoint or nil
func (m *CheckpointManager) GetLatest(ctx context.Context, sessionID string) (*Checkpoint, error) {
	return m.storage.GetLatest(ctx, sessionID)
}

// LoadCheckpoint loads specific checkpoint.
//
// Args:
//
//	ctx: Context
//	checkpointID: Checkpoint identifier
//
// Returns:
//
//	Checkpoint or nil if not found
func (m *CheckpointManager) LoadCheckpoint(ctx context.Context, checkpointID string) (*Checkpoint, error) {
	return m.storage.Load(ctx, checkpointID)
}

// ListCheckpoints lists all checkpoints for session.
//
// Args:
//
//	ctx: Context
//	sessionID: Session identifier
//	limit: Optional limit on number of checkpoints (0 = no limit)
//
// Returns:
//
//	List of checkpoints (most recent first)
func (m *CheckpointManager) ListCheckpoints(ctx context.Context, sessionID string, limit int) ([]*Checkpoint, error) {
	return m.storage.ListCheckpoints(ctx, sessionID, limit)
}

// RestoreState restores agent state from checkpoint.
//
// Args:
//
//	checkpoint: Checkpoint to restore from
//
// Returns:
//
//	Restored state dictionary
func (m *CheckpointManager) RestoreState(checkpoint *Checkpoint) map[string]interface{} {
	log.Printf("INFO: Restoring state from checkpoint %s (step %d)",
		checkpoint.CheckpointID, checkpoint.StepNumber)

	// Make a copy of the state
	state := make(map[string]interface{})
	for k, v := range checkpoint.State {
		state[k] = v
	}

	return state
}

// GetCheckpointHistory gets checkpoint history by following parent links.
//
// Args:
//
//	ctx: Context
//	checkpointID: Starting checkpoint
//	maxDepth: Maximum number of parents to follow
//
// Returns:
//
//	List of checkpoints from most recent to oldest
func (m *CheckpointManager) GetCheckpointHistory(ctx context.Context, checkpointID string, maxDepth int) ([]*Checkpoint, error) {
	return m.storage.GetCheckpointHistory(ctx, checkpointID, maxDepth)
}

// ReplayFunc is the function signature for replay operations.
type ReplayFunc func(ctx context.Context, checkpoint *Checkpoint, state map[string]interface{}) (interface{}, error)

// ReplayFromCheckpoint replays execution from checkpoint.
//
// Args:
//
//	ctx: Context
//	checkpointID: Starting checkpoint
//	replayFn: Function to execute for each step
//	upToStep: Optional step number to replay up to (0 = all)
//
// Returns:
//
//	List of results from replay function
//
// Example:
//
//	results, _ := manager.ReplayFromCheckpoint(ctx,
//	    "checkpoint-id",
//	    func(ctx context.Context, checkpoint *Checkpoint, state map[string]interface{}) (interface{}, error) {
//	        fmt.Printf("Replaying step %d\n", checkpoint.StepNumber)
//	        return processMessages(checkpoint.Messages), nil
//	    },
//	    0,
//	)
func (m *CheckpointManager) ReplayFromCheckpoint(
	ctx context.Context,
	checkpointID string,
	replayFn ReplayFunc,
	upToStep int,
) ([]interface{}, error) {
	// Get checkpoint history
	history, err := m.GetCheckpointHistory(ctx, checkpointID, 100)
	if err != nil {
		return nil, err
	}

	// Reverse to get oldest to newest
	for i, j := 0, len(history)-1; i < j; i, j = i+1, j-1 {
		history[i], history[j] = history[j], history[i]
	}

	results := make([]interface{}, 0)

	for _, checkpoint := range history {
		// Stop if we've reached the target step
		if upToStep > 0 && checkpoint.StepNumber > upToStep {
			break
		}

		// Execute replay function
		result, err := replayFn(ctx, checkpoint, checkpoint.State)
		if err != nil {
			return nil, fmt.Errorf("replay failed at step %d: %w", checkpoint.StepNumber, err)
		}

		results = append(results, result)

		log.Printf("DEBUG: Replayed step %d", checkpoint.StepNumber)
	}

	return results, nil
}

// DeleteCheckpoint deletes specific checkpoint.
//
// Args:
//
//	ctx: Context
//	checkpointID: Checkpoint identifier
//
// Returns:
//
//	true if deleted, false if not found
func (m *CheckpointManager) DeleteCheckpoint(ctx context.Context, checkpointID string) (bool, error) {
	return m.storage.Delete(ctx, checkpointID)
}

// DeleteSession deletes all checkpoints for session.
//
// Args:
//
//	ctx: Context
//	sessionID: Session identifier
//
// Returns:
//
//	Number of checkpoints deleted
func (m *CheckpointManager) DeleteSession(ctx context.Context, sessionID string) (int, error) {
	count, err := m.storage.DeleteSession(ctx, sessionID)
	if err != nil {
		return 0, err
	}

	// Clean up tracking
	delete(m.sessionSteps, sessionID)
	delete(m.sessionLastCheckpoint, sessionID)

	return count, nil
}

// GetSessionStats gets statistics for session checkpoints.
//
// Args:
//
//	ctx: Context
//	sessionID: Session identifier
//
// Returns:
//
//	Map with statistics
func (m *CheckpointManager) GetSessionStats(ctx context.Context, sessionID string) (map[string]interface{}, error) {
	checkpoints, err := m.ListCheckpoints(ctx, sessionID, 0)
	if err != nil {
		return nil, err
	}

	if len(checkpoints) == 0 {
		return map[string]interface{}{
			"total_checkpoints": 0,
			"first_checkpoint":  nil,
			"latest_checkpoint": nil,
			"steps_covered":     0,
		}, nil
	}

	firstCheckpoint := checkpoints[len(checkpoints)-1]
	latestCheckpoint := checkpoints[0]

	return map[string]interface{}{
		"total_checkpoints": len(checkpoints),
		"first_checkpoint":  firstCheckpoint.CheckpointID,
		"latest_checkpoint": latestCheckpoint.CheckpointID,
		"first_step":        firstCheckpoint.StepNumber,
		"latest_step":       latestCheckpoint.StepNumber,
		"steps_covered":     latestCheckpoint.StepNumber - firstCheckpoint.StepNumber,
		"time_span":         latestCheckpoint.Timestamp.Sub(firstCheckpoint.Timestamp).Seconds(),
	}, nil
}

// PruneOldCheckpoints prunes old checkpoints, keeping only the most recent N.
//
// Args:
//
//	ctx: Context
//	sessionID: Session identifier
//	keepLast: Number of most recent checkpoints to keep
//
// Returns:
//
//	Number of checkpoints deleted
//
// Example:
//
//	// Keep only last 10 checkpoints
//	deleted, _ := manager.PruneOldCheckpoints(ctx, "session-1", 10)
//	fmt.Printf("Deleted %d old checkpoints\n", deleted)
func (m *CheckpointManager) PruneOldCheckpoints(ctx context.Context, sessionID string, keepLast int) (int, error) {
	checkpoints, err := m.ListCheckpoints(ctx, sessionID, 0)
	if err != nil {
		return 0, err
	}

	if len(checkpoints) <= keepLast {
		return 0, nil
	}

	// Delete old checkpoints
	toDelete := checkpoints[keepLast:]
	deletedCount := 0

	for _, checkpoint := range toDelete {
		deleted, err := m.storage.Delete(ctx, checkpoint.CheckpointID)
		if err != nil {
			continue
		}
		if deleted {
			deletedCount++
		}
	}

	log.Printf("INFO: Pruned %d old checkpoints for %s, kept %d most recent",
		deletedCount, sessionID, keepLast)

	return deletedCount, nil
}
