package checkpointing

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"sync"
)

// InMemoryStorage provides in-memory checkpoint storage.
//
// Good for:
//   - Testing
//   - Development
//   - Short-lived sessions
//
// Not suitable for:
//   - Production (no persistence)
//   - Long-running agents (lost on restart)
//
// Example:
//
//	storage := NewInMemoryStorage()
//	err := storage.Save(ctx, checkpoint)
type InMemoryStorage struct {
	mu                 sync.RWMutex
	checkpoints        map[string]*Checkpoint // checkpoint_id -> Checkpoint
	sessionCheckpoints map[string][]string    // session_id -> list of checkpoint_ids
}

// NewInMemoryStorage creates a new in-memory checkpoint storage.
func NewInMemoryStorage() *InMemoryStorage {
	return &InMemoryStorage{
		checkpoints:        make(map[string]*Checkpoint),
		sessionCheckpoints: make(map[string][]string),
	}
}

// Save saves checkpoint to memory.
func (s *InMemoryStorage) Save(ctx context.Context, checkpoint *Checkpoint) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.checkpoints[checkpoint.CheckpointID] = checkpoint

	// Add to session index
	sessionID := checkpoint.SessionID
	found := false
	for _, cid := range s.sessionCheckpoints[sessionID] {
		if cid == checkpoint.CheckpointID {
			found = true
			break
		}
	}

	if !found {
		s.sessionCheckpoints[sessionID] = append(s.sessionCheckpoints[sessionID], checkpoint.CheckpointID)

		// Sort by timestamp (most recent first)
		sort.Slice(s.sessionCheckpoints[sessionID], func(i, j int) bool {
			cid1 := s.sessionCheckpoints[sessionID][i]
			cid2 := s.sessionCheckpoints[sessionID][j]
			return s.checkpoints[cid1].Timestamp.After(s.checkpoints[cid2].Timestamp)
		})
	}

	return nil
}

// Load loads checkpoint from memory.
func (s *InMemoryStorage) Load(ctx context.Context, checkpointID string) (*Checkpoint, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	checkpoint, ok := s.checkpoints[checkpointID]
	if !ok {
		return nil, nil
	}
	return checkpoint, nil
}

// ListCheckpoints lists checkpoints for session.
func (s *InMemoryStorage) ListCheckpoints(ctx context.Context, sessionID string, limit int) ([]*Checkpoint, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	checkpointIDs, ok := s.sessionCheckpoints[sessionID]
	if !ok {
		return []*Checkpoint{}, nil
	}

	if limit > 0 && len(checkpointIDs) > limit {
		checkpointIDs = checkpointIDs[:limit]
	}

	checkpoints := make([]*Checkpoint, 0, len(checkpointIDs))
	for _, cid := range checkpointIDs {
		if checkpoint, ok := s.checkpoints[cid]; ok {
			checkpoints = append(checkpoints, checkpoint)
		}
	}

	return checkpoints, nil
}

// GetLatest gets latest checkpoint for session.
func (s *InMemoryStorage) GetLatest(ctx context.Context, sessionID string) (*Checkpoint, error) {
	checkpoints, err := s.ListCheckpoints(ctx, sessionID, 1)
	if err != nil {
		return nil, err
	}

	if len(checkpoints) == 0 {
		return nil, nil
	}

	return checkpoints[0], nil
}

// Delete deletes checkpoint.
func (s *InMemoryStorage) Delete(ctx context.Context, checkpointID string) (bool, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	checkpoint, ok := s.checkpoints[checkpointID]
	if !ok {
		return false, nil
	}

	delete(s.checkpoints, checkpointID)

	// Remove from session index
	sessionID := checkpoint.SessionID
	for i, cid := range s.sessionCheckpoints[sessionID] {
		if cid == checkpointID {
			s.sessionCheckpoints[sessionID] = append(
				s.sessionCheckpoints[sessionID][:i],
				s.sessionCheckpoints[sessionID][i+1:]...,
			)
			break
		}
	}

	return true, nil
}

// DeleteSession deletes all checkpoints for session.
func (s *InMemoryStorage) DeleteSession(ctx context.Context, sessionID string) (int, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	checkpointIDs, ok := s.sessionCheckpoints[sessionID]
	if !ok {
		return 0, nil
	}

	count := len(checkpointIDs)

	for _, checkpointID := range checkpointIDs {
		delete(s.checkpoints, checkpointID)
	}

	delete(s.sessionCheckpoints, sessionID)

	return count, nil
}

// GetCheckpointHistory gets checkpoint history by following parent links.
func (s *InMemoryStorage) GetCheckpointHistory(ctx context.Context, checkpointID string, maxDepth int) ([]*Checkpoint, error) {
	history := make([]*Checkpoint, 0)
	currentID := checkpointID

	for i := 0; i < maxDepth; i++ {
		checkpoint, err := s.Load(ctx, currentID)
		if err != nil {
			return nil, err
		}
		if checkpoint == nil {
			break
		}

		history = append(history, checkpoint)

		if checkpoint.ParentCheckpointID == nil {
			break
		}

		currentID = *checkpoint.ParentCheckpointID
	}

	return history, nil
}

// GetStats returns storage statistics.
func (s *InMemoryStorage) GetStats() map[string]interface{} {
	s.mu.RLock()
	defer s.mu.RUnlock()

	checkpointsPerSession := make(map[string]int)
	for sessionID, checkpointIDs := range s.sessionCheckpoints {
		checkpointsPerSession[sessionID] = len(checkpointIDs)
	}

	return map[string]interface{}{
		"total_checkpoints":       len(s.checkpoints),
		"total_sessions":          len(s.sessionCheckpoints),
		"checkpoints_per_session": checkpointsPerSession,
	}
}

// FileStorage provides file-based checkpoint storage.
//
// Stores each checkpoint as a JSON file on disk for persistence.
//
// Directory structure:
//
//	checkpoint_dir/
//	  {session_id}/
//	    {checkpoint_id}.json
//	    {checkpoint_id}.json
//	    ...
//
// Good for:
//   - Production (persistent)
//   - Single-machine deployments
//   - Development with persistence
//
// Example:
//
//	storage := NewFileStorage("./checkpoints")
//	err := storage.Save(ctx, checkpoint)
type FileStorage struct {
	checkpointDir string
}

// NewFileStorage creates a new file-based checkpoint storage.
//
// Args:
//
//	checkpointDir: Directory to store checkpoints
//
// Example:
//
//	storage := NewFileStorage("./checkpoints")
func NewFileStorage(checkpointDir string) (*FileStorage, error) {
	// Create directory if it doesn't exist
	if err := os.MkdirAll(checkpointDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create checkpoint directory: %w", err)
	}

	return &FileStorage{
		checkpointDir: checkpointDir,
	}, nil
}

// getSessionDir gets directory for session checkpoints.
func (s *FileStorage) getSessionDir(sessionID string) string {
	return filepath.Join(s.checkpointDir, sessionID)
}

// getCheckpointPath gets file path for checkpoint.
func (s *FileStorage) getCheckpointPath(sessionID, checkpointID string) string {
	return filepath.Join(s.getSessionDir(sessionID), checkpointID+".json")
}

// Save saves checkpoint to file.
func (s *FileStorage) Save(ctx context.Context, checkpoint *Checkpoint) error {
	// Create session directory
	sessionDir := s.getSessionDir(checkpoint.SessionID)
	if err := os.MkdirAll(sessionDir, 0755); err != nil {
		return fmt.Errorf("failed to create session directory: %w", err)
	}

	// Serialize checkpoint
	jsonData, err := checkpoint.ToJSON()
	if err != nil {
		return fmt.Errorf("failed to serialize checkpoint: %w", err)
	}

	// Write to file
	checkpointPath := s.getCheckpointPath(checkpoint.SessionID, checkpoint.CheckpointID)
	if err := os.WriteFile(checkpointPath, []byte(jsonData), 0644); err != nil {
		return fmt.Errorf("failed to write checkpoint file: %w", err)
	}

	return nil
}

// Load loads checkpoint from file.
func (s *FileStorage) Load(ctx context.Context, checkpointID string) (*Checkpoint, error) {
	// Search through session directories
	entries, err := os.ReadDir(s.checkpointDir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to read checkpoint directory: %w", err)
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		checkpointPath := filepath.Join(s.checkpointDir, entry.Name(), checkpointID+".json")
		if _, err := os.Stat(checkpointPath); err == nil {
			data, err := os.ReadFile(checkpointPath)
			if err != nil {
				return nil, fmt.Errorf("failed to read checkpoint file: %w", err)
			}

			checkpoint, err := FromJSON(string(data))
			if err != nil {
				return nil, fmt.Errorf("failed to deserialize checkpoint: %w", err)
			}

			return checkpoint, nil
		}
	}

	return nil, nil
}

// ListCheckpoints lists checkpoints for session.
func (s *FileStorage) ListCheckpoints(ctx context.Context, sessionID string, limit int) ([]*Checkpoint, error) {
	sessionDir := s.getSessionDir(sessionID)

	entries, err := os.ReadDir(sessionDir)
	if err != nil {
		if os.IsNotExist(err) {
			return []*Checkpoint{}, nil
		}
		return nil, fmt.Errorf("failed to read session directory: %w", err)
	}

	// Load all checkpoints
	checkpoints := make([]*Checkpoint, 0)
	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".json" {
			continue
		}

		checkpointPath := filepath.Join(sessionDir, entry.Name())
		data, err := os.ReadFile(checkpointPath)
		if err != nil {
			continue // Skip malformed files
		}

		checkpoint, err := FromJSON(string(data))
		if err != nil {
			continue // Skip malformed checkpoints
		}

		checkpoints = append(checkpoints, checkpoint)
	}

	// Sort by timestamp (most recent first)
	sort.Slice(checkpoints, func(i, j int) bool {
		return checkpoints[i].Timestamp.After(checkpoints[j].Timestamp)
	})

	// Apply limit
	if limit > 0 && len(checkpoints) > limit {
		checkpoints = checkpoints[:limit]
	}

	return checkpoints, nil
}

// GetLatest gets latest checkpoint for session.
func (s *FileStorage) GetLatest(ctx context.Context, sessionID string) (*Checkpoint, error) {
	checkpoints, err := s.ListCheckpoints(ctx, sessionID, 1)
	if err != nil {
		return nil, err
	}

	if len(checkpoints) == 0 {
		return nil, nil
	}

	return checkpoints[0], nil
}

// Delete deletes checkpoint file.
func (s *FileStorage) Delete(ctx context.Context, checkpointID string) (bool, error) {
	// Search through session directories
	entries, err := os.ReadDir(s.checkpointDir)
	if err != nil {
		if os.IsNotExist(err) {
			return false, nil
		}
		return false, fmt.Errorf("failed to read checkpoint directory: %w", err)
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		checkpointPath := filepath.Join(s.checkpointDir, entry.Name(), checkpointID+".json")
		if _, err := os.Stat(checkpointPath); err == nil {
			if err := os.Remove(checkpointPath); err != nil {
				return false, fmt.Errorf("failed to delete checkpoint file: %w", err)
			}
			return true, nil
		}
	}

	return false, nil
}

// DeleteSession deletes all checkpoints for session.
func (s *FileStorage) DeleteSession(ctx context.Context, sessionID string) (int, error) {
	sessionDir := s.getSessionDir(sessionID)

	entries, err := os.ReadDir(sessionDir)
	if err != nil {
		if os.IsNotExist(err) {
			return 0, nil
		}
		return 0, fmt.Errorf("failed to read session directory: %w", err)
	}

	// Count and delete checkpoint files
	count := 0
	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".json" {
			continue
		}

		checkpointPath := filepath.Join(sessionDir, entry.Name())
		if err := os.Remove(checkpointPath); err != nil {
			continue
		}
		count++
	}

	// Try to remove session directory if empty
	_ = os.Remove(sessionDir) // Ignore error if directory not empty

	return count, nil
}

// GetCheckpointHistory gets checkpoint history by following parent links.
func (s *FileStorage) GetCheckpointHistory(ctx context.Context, checkpointID string, maxDepth int) ([]*Checkpoint, error) {
	history := make([]*Checkpoint, 0)
	currentID := checkpointID

	for i := 0; i < maxDepth; i++ {
		checkpoint, err := s.Load(ctx, currentID)
		if err != nil {
			return nil, err
		}
		if checkpoint == nil {
			break
		}

		history = append(history, checkpoint)

		if checkpoint.ParentCheckpointID == nil {
			break
		}

		currentID = *checkpoint.ParentCheckpointID
	}

	return history, nil
}

// GetStats returns storage statistics.
func (s *FileStorage) GetStats() (map[string]interface{}, error) {
	stats := map[string]interface{}{
		"total_sessions":    0,
		"total_checkpoints": 0,
		"checkpoint_dir":    s.checkpointDir,
		"disk_usage_bytes":  int64(0),
	}

	entries, err := os.ReadDir(s.checkpointDir)
	if err != nil {
		if os.IsNotExist(err) {
			return stats, nil
		}
		return nil, fmt.Errorf("failed to read checkpoint directory: %w", err)
	}

	totalSessions := 0
	totalCheckpoints := 0
	var totalSize int64

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		totalSessions++

		sessionDir := filepath.Join(s.checkpointDir, entry.Name())
		sessionEntries, err := os.ReadDir(sessionDir)
		if err != nil {
			continue
		}

		for _, sessionEntry := range sessionEntries {
			if sessionEntry.IsDir() || filepath.Ext(sessionEntry.Name()) != ".json" {
				continue
			}

			totalCheckpoints++

			info, err := sessionEntry.Info()
			if err == nil {
				totalSize += info.Size()
			}
		}
	}

	stats["total_sessions"] = totalSessions
	stats["total_checkpoints"] = totalCheckpoints
	stats["disk_usage_bytes"] = totalSize

	return stats, nil
}
