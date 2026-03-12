package checkpointing

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// NFSStorage implements SharedCheckpointStorage backed by an NFS mount.
//
// Files are written atomically (write-to-temp → rename) to avoid partial reads
// from concurrent hosts.
//
// Directory layout mirrors LocalStorage:
//
//	{mountPath}/{sessionID}/{checkpointID}.json
//
// Example:
//
//	storage, err := NewNFSStorage("/mnt/nfs/checkpoints", "nas01.local", "/exports/checkpoints")
//	if err != nil { log.Fatal(err) }
//	_ = storage.Save(ctx, checkpoint)
type NFSStorage struct {
	mountPath string
	nfsHost   string
	nfsExport string
}

// NewNFSStorage creates an NFSStorage rooted at mountPath.
//
// mountPath must already be mounted; this constructor only verifies that it is
// reachable via os.Stat.
func NewNFSStorage(mountPath, nfsHost, nfsExport string) (*NFSStorage, error) {
	if _, err := os.Stat(mountPath); err != nil {
		return nil, fmt.Errorf("nfs mount path unreachable: %w", err)
	}
	return &NFSStorage{
		mountPath: mountPath,
		nfsHost:   nfsHost,
		nfsExport: nfsExport,
	}, nil
}

// URI returns the canonical nfs:// URI for this storage.
func (s *NFSStorage) URI() string {
	return fmt.Sprintf("nfs://%s%s", s.nfsHost, s.nfsExport)
}

// Ping verifies that the mount path is accessible.
func (s *NFSStorage) Ping(_ context.Context) error {
	if _, err := os.Stat(s.mountPath); err != nil {
		return fmt.Errorf("nfs mount path unreachable: %w", err)
	}
	return nil
}

func (s *NFSStorage) sessionDir(sessionID string) string {
	return filepath.Join(s.mountPath, sessionID)
}

func (s *NFSStorage) checkpointPath(sessionID, checkpointID string) string {
	return filepath.Join(s.sessionDir(sessionID), checkpointID+".json")
}

// Save writes a checkpoint atomically using a temp-file rename.
func (s *NFSStorage) Save(_ context.Context, cp *Checkpoint) error {
	dir := s.sessionDir(cp.SessionID)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("failed to create session directory: %w", err)
	}

	data, err := json.MarshalIndent(cp, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to serialise checkpoint: %w", err)
	}

	dest := s.checkpointPath(cp.SessionID, cp.CheckpointID)
	tmp := dest + ".tmp"

	if err := os.WriteFile(tmp, data, 0644); err != nil {
		return fmt.Errorf("failed to write temp checkpoint: %w", err)
	}
	if err := os.Rename(tmp, dest); err != nil {
		_ = os.Remove(tmp)
		return fmt.Errorf("failed to rename checkpoint: %w", err)
	}
	return nil
}

// Load reads a checkpoint by ID. Returns nil, nil if not found.
func (s *NFSStorage) Load(_ context.Context, checkpointID string) (*Checkpoint, error) {
	entries, err := os.ReadDir(s.mountPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to read mount path: %w", err)
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		path := filepath.Join(s.mountPath, entry.Name(), checkpointID+".json")
		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		var cp Checkpoint
		if err := json.Unmarshal(data, &cp); err != nil {
			return nil, fmt.Errorf("failed to deserialise checkpoint: %w", err)
		}
		return &cp, nil
	}
	return nil, nil
}

// ListCheckpoints lists checkpoints for sessionID, most recent first.
func (s *NFSStorage) ListCheckpoints(_ context.Context, sessionID string, limit *int) ([]*Checkpoint, error) {
	dir := s.sessionDir(sessionID)
	entries, err := os.ReadDir(dir)
	if err != nil {
		if os.IsNotExist(err) {
			return []*Checkpoint{}, nil
		}
		return nil, fmt.Errorf("failed to read session directory: %w", err)
	}

	var checkpoints []*Checkpoint
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".json") {
			continue
		}
		data, err := os.ReadFile(filepath.Join(dir, entry.Name()))
		if err != nil {
			continue
		}
		var cp Checkpoint
		if err := json.Unmarshal(data, &cp); err != nil {
			continue
		}
		checkpoints = append(checkpoints, &cp)
	}

	sort.Slice(checkpoints, func(i, j int) bool {
		return checkpoints[i].Timestamp.After(checkpoints[j].Timestamp)
	})

	if limit != nil && len(checkpoints) > *limit {
		checkpoints = checkpoints[:*limit]
	}
	return checkpoints, nil
}

// GetLatest returns the most recent checkpoint for sessionID.
func (s *NFSStorage) GetLatest(ctx context.Context, sessionID string) (*Checkpoint, error) {
	one := 1
	cps, err := s.ListCheckpoints(ctx, sessionID, &one)
	if err != nil {
		return nil, err
	}
	if len(cps) == 0 {
		return nil, nil
	}
	return cps[0], nil
}

// Delete removes a checkpoint file.
func (s *NFSStorage) Delete(_ context.Context, checkpointID string) (bool, error) {
	entries, err := os.ReadDir(s.mountPath)
	if err != nil {
		if os.IsNotExist(err) {
			return false, nil
		}
		return false, fmt.Errorf("failed to read mount path: %w", err)
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		path := filepath.Join(s.mountPath, entry.Name(), checkpointID+".json")
		if _, err := os.Stat(path); err == nil {
			if err := os.Remove(path); err != nil {
				return false, fmt.Errorf("failed to delete checkpoint: %w", err)
			}
			return true, nil
		}
	}
	return false, nil
}

// DeleteSession removes all checkpoints for sessionID.
func (s *NFSStorage) DeleteSession(_ context.Context, sessionID string) (int, error) {
	dir := s.sessionDir(sessionID)
	entries, err := os.ReadDir(dir)
	if err != nil {
		if os.IsNotExist(err) {
			return 0, nil
		}
		return 0, fmt.Errorf("failed to read session directory: %w", err)
	}

	count := 0
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".json") {
			continue
		}
		if err := os.Remove(filepath.Join(dir, entry.Name())); err == nil {
			count++
		}
	}
	_ = os.Remove(dir) // remove dir if now empty (best-effort)
	return count, nil
}

// GetCheckpointHistory follows parent links to build a history chain.
func (s *NFSStorage) GetCheckpointHistory(ctx context.Context, checkpointID string, maxDepth int) ([]*Checkpoint, error) {
	var history []*Checkpoint
	currentID := checkpointID
	for i := 0; i < maxDepth; i++ {
		cp, err := s.Load(ctx, currentID)
		if err != nil {
			return nil, err
		}
		if cp == nil {
			break
		}
		history = append(history, cp)
		if cp.ParentCheckpointID == nil {
			break
		}
		currentID = *cp.ParentCheckpointID
	}
	return history, nil
}
