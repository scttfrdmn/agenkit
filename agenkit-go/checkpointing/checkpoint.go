// Package checkpointing provides checkpointing functionality for durable agent execution.
//
// Checkpoints capture agent state at a point in time, enabling:
//   - Resume after crashes/restarts
//   - Time-travel debugging
//   - Durable execution for long-running agents
//
// Components:
//   - Checkpoint: Data structure capturing agent state
//   - CheckpointStorage: Interface for storage backends
//   - InMemoryStorage: In-memory storage implementation
//   - FileStorage: File-based persistent storage
//   - CheckpointManager: High-level checkpoint management
//   - DurableAgent: Agent wrapper with automatic checkpointing
package checkpointing

import (
	"context"
	"encoding/json"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// Checkpoint captures agent state at a point in time.
//
// Fields:
//   - CheckpointID: Unique checkpoint identifier
//   - SessionID: Session this checkpoint belongs to
//   - AgentName: Name of the agent
//   - Timestamp: When checkpoint was created
//   - StepNumber: Sequential step number in session
//   - State: Agent state (custom data)
//   - Messages: Conversation messages up to this point
//   - Metadata: Additional metadata (cost, tokens, etc.)
//   - ParentCheckpointID: ID of previous checkpoint (for history)
type Checkpoint struct {
	CheckpointID       string                 `json:"checkpoint_id"`
	SessionID          string                 `json:"session_id"`
	AgentName          string                 `json:"agent_name"`
	Timestamp          time.Time              `json:"timestamp"`
	StepNumber         int                    `json:"step_number"`
	State              map[string]interface{} `json:"state"`
	Messages           []agenkit.Message      `json:"messages"`
	Metadata           map[string]interface{} `json:"metadata"`
	ParentCheckpointID *string                `json:"parent_checkpoint_id,omitempty"`
}

// ToMap converts checkpoint to map for serialization.
func (c *Checkpoint) ToMap() map[string]interface{} {
	m := map[string]interface{}{
		"checkpoint_id": c.CheckpointID,
		"session_id":    c.SessionID,
		"agent_name":    c.AgentName,
		"timestamp":     c.Timestamp.Format(time.RFC3339),
		"step_number":   c.StepNumber,
		"state":         c.State,
		"messages":      c.Messages,
		"metadata":      c.Metadata,
	}

	if c.ParentCheckpointID != nil {
		m["parent_checkpoint_id"] = *c.ParentCheckpointID
	}

	return m
}

// ToJSON serializes checkpoint to JSON.
func (c *Checkpoint) ToJSON() (string, error) {
	data, err := json.MarshalIndent(c.ToMap(), "", "  ")
	if err != nil {
		return "", err
	}
	return string(data), nil
}

// FromJSON deserializes checkpoint from JSON.
func FromJSON(jsonStr string) (*Checkpoint, error) {
	var data map[string]interface{}
	if err := json.Unmarshal([]byte(jsonStr), &data); err != nil {
		return nil, err
	}

	checkpoint := &Checkpoint{
		CheckpointID: data["checkpoint_id"].(string),
		SessionID:    data["session_id"].(string),
		AgentName:    data["agent_name"].(string),
		StepNumber:   int(data["step_number"].(float64)),
		State:        make(map[string]interface{}),
		Messages:     make([]agenkit.Message, 0),
		Metadata:     make(map[string]interface{}),
	}

	// Parse timestamp
	if timestampStr, ok := data["timestamp"].(string); ok {
		timestamp, err := time.Parse(time.RFC3339, timestampStr)
		if err == nil {
			checkpoint.Timestamp = timestamp
		}
	}

	// Parse state
	if state, ok := data["state"].(map[string]interface{}); ok {
		checkpoint.State = state
	}

	// Parse metadata
	if metadata, ok := data["metadata"].(map[string]interface{}); ok {
		checkpoint.Metadata = metadata
	}

	// Parse messages
	if messages, ok := data["messages"].([]interface{}); ok {
		for _, msgData := range messages {
			if msgMap, ok := msgData.(map[string]interface{}); ok {
				msg := agenkit.Message{}
				if role, ok := msgMap["role"].(string); ok {
					msg.Role = role
				}
				if content, ok := msgMap["content"].(string); ok {
					msg.Content = content
				}
				if metadata, ok := msgMap["metadata"].(map[string]interface{}); ok {
					msg.Metadata = metadata
				}
				checkpoint.Messages = append(checkpoint.Messages, msg)
			}
		}
	}

	// Parse parent checkpoint ID
	if parentID, ok := data["parent_checkpoint_id"].(string); ok {
		checkpoint.ParentCheckpointID = &parentID
	}

	return checkpoint, nil
}

// CheckpointStorage is the interface for checkpoint storage backends.
//
// Implementations:
//   - InMemoryStorage: For testing/development
//   - FileStorage: For persistence to disk
//   - RedisStorage: For distributed systems
type CheckpointStorage interface {
	// Save saves checkpoint to storage.
	//
	// Args:
	//   ctx: Context
	//   checkpoint: Checkpoint to save
	Save(ctx context.Context, checkpoint *Checkpoint) error

	// Load loads checkpoint by ID.
	//
	// Args:
	//   ctx: Context
	//   checkpointID: Checkpoint identifier
	//
	// Returns:
	//   Checkpoint if found, nil otherwise
	Load(ctx context.Context, checkpointID string) (*Checkpoint, error)

	// ListCheckpoints lists checkpoints for session.
	//
	// Args:
	//   ctx: Context
	//   sessionID: Session identifier
	//   limit: Optional limit on number of checkpoints (0 = no limit)
	//
	// Returns:
	//   List of checkpoints (most recent first)
	ListCheckpoints(ctx context.Context, sessionID string, limit int) ([]*Checkpoint, error)

	// GetLatest gets latest checkpoint for session.
	//
	// Args:
	//   ctx: Context
	//   sessionID: Session identifier
	//
	// Returns:
	//   Latest checkpoint if exists, nil otherwise
	GetLatest(ctx context.Context, sessionID string) (*Checkpoint, error)

	// Delete deletes checkpoint.
	//
	// Args:
	//   ctx: Context
	//   checkpointID: Checkpoint identifier
	//
	// Returns:
	//   true if deleted, false if not found
	Delete(ctx context.Context, checkpointID string) (bool, error)

	// DeleteSession deletes all checkpoints for session.
	//
	// Args:
	//   ctx: Context
	//   sessionID: Session identifier
	//
	// Returns:
	//   Number of checkpoints deleted
	DeleteSession(ctx context.Context, sessionID string) (int, error)

	// GetCheckpointHistory gets checkpoint history by following parent links.
	//
	// Args:
	//   ctx: Context
	//   checkpointID: Starting checkpoint
	//   maxDepth: Maximum number of parents to follow
	//
	// Returns:
	//   List of checkpoints from most recent to oldest
	GetCheckpointHistory(ctx context.Context, checkpointID string, maxDepth int) ([]*Checkpoint, error)
}
