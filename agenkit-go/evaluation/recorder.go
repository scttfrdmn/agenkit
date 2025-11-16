package evaluation

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/google/uuid"
)

// InteractionRecord represents a record of single agent interaction.
//
// Contains input, output, timing, and metadata.
type InteractionRecord struct {
	InteractionID string
	SessionID     string
	InputMessage  map[string]interface{}
	OutputMessage map[string]interface{}
	Timestamp     time.Time
	LatencyMs     float64
	Metadata      map[string]interface{}
}

// ToDict converts record to dictionary.
func (r *InteractionRecord) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"interaction_id": r.InteractionID,
		"session_id":     r.SessionID,
		"input_message":  r.InputMessage,
		"output_message": r.OutputMessage,
		"timestamp":      r.Timestamp.Format(time.RFC3339),
		"latency_ms":     r.LatencyMs,
		"metadata":       r.Metadata,
	}
}

// InteractionRecordFromDict creates record from dictionary.
func InteractionRecordFromDict(data map[string]interface{}) (*InteractionRecord, error) {
	timestampStr, ok := data["timestamp"].(string)
	if !ok {
		return nil, fmt.Errorf("missing or invalid timestamp")
	}

	timestamp, err := time.Parse(time.RFC3339, timestampStr)
	if err != nil {
		return nil, err
	}

	return &InteractionRecord{
		InteractionID: data["interaction_id"].(string),
		SessionID:     data["session_id"].(string),
		InputMessage:  data["input_message"].(map[string]interface{}),
		OutputMessage: data["output_message"].(map[string]interface{}),
		Timestamp:     timestamp,
		LatencyMs:     data["latency_ms"].(float64),
		Metadata:      getMapOrEmpty(data, "metadata"),
	}, nil
}

// SessionRecording represents a recording of entire session.
//
// Contains all interactions and session metadata.
type SessionRecording struct {
	SessionID    string
	AgentName    string
	StartTime    time.Time
	EndTime      *time.Time
	Interactions []*InteractionRecord
	Metadata     map[string]interface{}
}

// DurationSeconds calculates session duration in seconds.
func (r *SessionRecording) DurationSeconds() float64 {
	if r.EndTime == nil {
		return 0.0
	}
	return r.EndTime.Sub(r.StartTime).Seconds()
}

// InteractionCount gets number of interactions.
func (r *SessionRecording) InteractionCount() int {
	return len(r.Interactions)
}

// TotalLatencyMs gets total latency across all interactions.
func (r *SessionRecording) TotalLatencyMs() float64 {
	total := 0.0
	for _, i := range r.Interactions {
		total += i.LatencyMs
	}
	return total
}

// ToDict converts recording to dictionary.
func (r *SessionRecording) ToDict() map[string]interface{} {
	interactions := make([]map[string]interface{}, len(r.Interactions))
	for i, interaction := range r.Interactions {
		interactions[i] = interaction.ToDict()
	}

	result := map[string]interface{}{
		"session_id":   r.SessionID,
		"agent_name":   r.AgentName,
		"start_time":   r.StartTime.Format(time.RFC3339),
		"interactions": interactions,
		"metadata":     r.Metadata,
	}

	if r.EndTime != nil {
		result["end_time"] = r.EndTime.Format(time.RFC3339)
	} else {
		result["end_time"] = nil
	}

	return result
}

// SessionRecordingFromDict creates recording from dictionary.
func SessionRecordingFromDict(data map[string]interface{}) (*SessionRecording, error) {
	startTimeStr, ok := data["start_time"].(string)
	if !ok {
		return nil, fmt.Errorf("missing or invalid start_time")
	}

	startTime, err := time.Parse(time.RFC3339, startTimeStr)
	if err != nil {
		return nil, err
	}

	var endTime *time.Time
	if endTimeStr, ok := data["end_time"].(string); ok && endTimeStr != "" {
		t, err := time.Parse(time.RFC3339, endTimeStr)
		if err == nil {
			endTime = &t
		}
	}

	// Parse interactions
	interactions := make([]*InteractionRecord, 0)
	if interactionsData, ok := data["interactions"].([]interface{}); ok {
		for _, iData := range interactionsData {
			if iMap, ok := iData.(map[string]interface{}); ok {
				interaction, err := InteractionRecordFromDict(iMap)
				if err == nil {
					interactions = append(interactions, interaction)
				}
			}
		}
	}

	return &SessionRecording{
		SessionID:    data["session_id"].(string),
		AgentName:    data["agent_name"].(string),
		StartTime:    startTime,
		EndTime:      endTime,
		Interactions: interactions,
		Metadata:     getMapOrEmpty(data, "metadata"),
	}, nil
}

// RecordingStorage is the interface for recording storage backends.
//
// Implement this to create custom storage (Redis, S3, Postgres, etc.).
type RecordingStorage interface {
	// SaveRecording saves recording.
	SaveRecording(recording *SessionRecording) error

	// LoadRecording loads recording by session ID.
	LoadRecording(sessionID string) (*SessionRecording, error)

	// ListRecordings lists recordings.
	ListRecordings(limit, offset int) ([]*SessionRecording, error)

	// DeleteRecording deletes recording.
	DeleteRecording(sessionID string) error
}

// FileRecordingStorage provides file-based recording storage.
//
// Stores recordings as JSON files on disk.
type FileRecordingStorage struct {
	recordingsDir string
}

// NewFileRecordingStorage creates a new file storage.
//
// Args:
//
//	recordingsDir: Directory to store recordings
//
// Example:
//
//	storage := NewFileRecordingStorage("./recordings")
func NewFileRecordingStorage(recordingsDir string) *FileRecordingStorage {
	if recordingsDir == "" {
		recordingsDir = "./recordings"
	}

	// Create directory if needed
	os.MkdirAll(recordingsDir, 0755)

	return &FileRecordingStorage{
		recordingsDir: recordingsDir,
	}
}

// SaveRecording saves recording to file.
func (s *FileRecordingStorage) SaveRecording(recording *SessionRecording) error {
	filePath := filepath.Join(s.recordingsDir, fmt.Sprintf("%s.json", recording.SessionID))

	file, err := os.Create(filePath)
	if err != nil {
		return err
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	return encoder.Encode(recording.ToDict())
}

// LoadRecording loads recording from file.
func (s *FileRecordingStorage) LoadRecording(sessionID string) (*SessionRecording, error) {
	filePath := filepath.Join(s.recordingsDir, fmt.Sprintf("%s.json", sessionID))

	file, err := os.Open(filePath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	defer file.Close()

	var data map[string]interface{}
	decoder := json.NewDecoder(file)
	if err := decoder.Decode(&data); err != nil {
		return nil, err
	}

	return SessionRecordingFromDict(data)
}

// ListRecordings lists all recordings.
func (s *FileRecordingStorage) ListRecordings(limit, offset int) ([]*SessionRecording, error) {
	recordings := make([]*SessionRecording, 0)

	// Find all JSON files
	files, err := filepath.Glob(filepath.Join(s.recordingsDir, "*.json"))
	if err != nil {
		return nil, err
	}

	// Sort by modification time (most recent first)
	type fileInfo struct {
		path    string
		modTime time.Time
	}

	fileInfos := make([]fileInfo, 0, len(files))
	for _, file := range files {
		info, err := os.Stat(file)
		if err != nil {
			continue
		}
		fileInfos = append(fileInfos, fileInfo{
			path:    file,
			modTime: info.ModTime(),
		})
	}

	sort.Slice(fileInfos, func(i, j int) bool {
		return fileInfos[i].modTime.After(fileInfos[j].modTime)
	})

	// Apply pagination
	start := offset
	end := offset + limit
	if start >= len(fileInfos) {
		return recordings, nil
	}
	if end > len(fileInfos) {
		end = len(fileInfos)
	}

	// Load recordings
	for _, fi := range fileInfos[start:end] {
		file, err := os.Open(fi.path)
		if err != nil {
			continue
		}

		var data map[string]interface{}
		decoder := json.NewDecoder(file)
		if err := decoder.Decode(&data); err != nil {
			file.Close()
			continue
		}
		file.Close()

		recording, err := SessionRecordingFromDict(data)
		if err != nil {
			continue
		}

		recordings = append(recordings, recording)
	}

	return recordings, nil
}

// DeleteRecording deletes recording file.
func (s *FileRecordingStorage) DeleteRecording(sessionID string) error {
	filePath := filepath.Join(s.recordingsDir, fmt.Sprintf("%s.json", sessionID))

	if _, err := os.Stat(filePath); err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}

	return os.Remove(filePath)
}

// InMemoryRecordingStorage provides in-memory recording storage for testing.
//
// Does not persist recordings across restarts.
type InMemoryRecordingStorage struct {
	recordings map[string]*SessionRecording
}

// NewInMemoryRecordingStorage creates a new in-memory storage.
func NewInMemoryRecordingStorage() *InMemoryRecordingStorage {
	return &InMemoryRecordingStorage{
		recordings: make(map[string]*SessionRecording),
	}
}

// SaveRecording saves recording to memory.
func (s *InMemoryRecordingStorage) SaveRecording(recording *SessionRecording) error {
	s.recordings[recording.SessionID] = recording
	return nil
}

// LoadRecording loads recording from memory.
func (s *InMemoryRecordingStorage) LoadRecording(sessionID string) (*SessionRecording, error) {
	recording, ok := s.recordings[sessionID]
	if !ok {
		return nil, nil
	}
	return recording, nil
}

// ListRecordings lists recordings from memory.
func (s *InMemoryRecordingStorage) ListRecordings(limit, offset int) ([]*SessionRecording, error) {
	recordings := make([]*SessionRecording, 0, len(s.recordings))
	for _, recording := range s.recordings {
		recordings = append(recordings, recording)
	}

	// Sort by start time (most recent first)
	sort.Slice(recordings, func(i, j int) bool {
		return recordings[i].StartTime.After(recordings[j].StartTime)
	})

	// Apply pagination
	start := offset
	end := offset + limit
	if start >= len(recordings) {
		return make([]*SessionRecording, 0), nil
	}
	if end > len(recordings) {
		end = len(recordings)
	}

	return recordings[start:end], nil
}

// DeleteRecording deletes recording from memory.
func (s *InMemoryRecordingStorage) DeleteRecording(sessionID string) error {
	delete(s.recordings, sessionID)
	return nil
}

// SessionRecorder records agent sessions for replay and analysis.
//
// Automatically records all interactions with an agent,
// storing inputs, outputs, timing, and metadata.
//
// Example:
//
//	recorder := NewSessionRecorder(NewFileRecordingStorage("./recordings"))
//	wrappedAgent := recorder.Wrap(agent)
//
//	// Use agent normally (automatically recorded)
//	response, _ := wrappedAgent.Process(ctx, message)
//
//	// Save recording
//	recorder.FinalizeSession("test-123")
type SessionRecorder struct {
	storage        RecordingStorage
	activeSessions map[string]*SessionRecording
}

// NewSessionRecorder creates a new session recorder.
//
// Args:
//
//	storage: Storage backend (nil = in-memory)
//
// Example:
//
//	recorder := NewSessionRecorder(nil)
func NewSessionRecorder(storage RecordingStorage) *SessionRecorder {
	if storage == nil {
		storage = NewInMemoryRecordingStorage()
	}

	return &SessionRecorder{
		storage:        storage,
		activeSessions: make(map[string]*SessionRecording),
	}
}

// Wrap wraps agent to record interactions.
//
// Args:
//
//	agent: Agent to wrap
//
// Returns:
//
//	Wrapped agent that records all interactions
func (r *SessionRecorder) Wrap(agent agenkit.Agent) agenkit.Agent {
	return &recordingWrapper{
		agent:    agent,
		recorder: r,
	}
}

// recordingWrapper wraps an agent to record interactions.
type recordingWrapper struct {
	agent    agenkit.Agent
	recorder *SessionRecorder
}

// Name returns the agent name.
func (w *recordingWrapper) Name() string {
	return w.agent.Name()
}

// Capabilities returns agent capabilities.
func (w *recordingWrapper) Capabilities() []string {
	return w.agent.Capabilities()
}

// Process processes message with recording.
func (w *recordingWrapper) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Extract session ID from metadata
	sessionID := "default"
	if message.Metadata != nil {
		if sid, ok := message.Metadata["session_id"].(string); ok {
			sessionID = sid
		}
	}

	// Start session if not already started
	if _, ok := w.recorder.activeSessions[sessionID]; !ok {
		w.recorder.StartSession(sessionID, w.agent.Name(), nil)
	}

	// Process with timing
	start := time.Now()
	output, err := w.agent.Process(ctx, message)
	latency := time.Since(start).Milliseconds()

	// Record interaction (even if error)
	w.recorder.RecordInteraction(sessionID, message, output, float64(latency), nil)

	return output, err
}

// StartSession starts recording session.
//
// Args:
//
//	sessionID: Session identifier
//	agentName: Name of agent being recorded
//	metadata: Optional session metadata
func (r *SessionRecorder) StartSession(sessionID, agentName string, metadata map[string]interface{}) {
	if metadata == nil {
		metadata = make(map[string]interface{})
	}

	r.activeSessions[sessionID] = &SessionRecording{
		SessionID:    sessionID,
		AgentName:    agentName,
		StartTime:    time.Now().UTC(),
		Interactions: make([]*InteractionRecord, 0),
		Metadata:     metadata,
	}
}

// RecordInteraction records single interaction.
//
// Args:
//
//	sessionID: Session identifier
//	inputMessage: Input to agent
//	outputMessage: Agent response
//	latencyMs: Processing time in milliseconds
//	metadata: Optional interaction metadata
func (r *SessionRecorder) RecordInteraction(sessionID string, inputMessage, outputMessage *agenkit.Message, latencyMs float64, metadata map[string]interface{}) {
	// Get or create session
	session, ok := r.activeSessions[sessionID]
	if !ok {
		r.StartSession(sessionID, "unknown", nil)
		session = r.activeSessions[sessionID]
	}

	if metadata == nil {
		metadata = make(map[string]interface{})
	}

	// Create interaction record
	record := &InteractionRecord{
		InteractionID: uuid.New().String(),
		SessionID:     sessionID,
		InputMessage:  messageToDict(inputMessage),
		OutputMessage: messageToDict(outputMessage),
		Timestamp:     time.Now().UTC(),
		LatencyMs:     latencyMs,
		Metadata:      metadata,
	}

	session.Interactions = append(session.Interactions, record)
}

// FinalizeSession finalizes and saves session recording.
//
// Args:
//
//	sessionID: Session to finalize
//
// Returns:
//
//	Session recording
func (r *SessionRecorder) FinalizeSession(sessionID string) (*SessionRecording, error) {
	session, ok := r.activeSessions[sessionID]
	if !ok {
		return nil, fmt.Errorf("no active session: %s", sessionID)
	}

	delete(r.activeSessions, sessionID)
	endTime := time.Now().UTC()
	session.EndTime = &endTime

	// Save to storage
	if err := r.storage.SaveRecording(session); err != nil {
		return nil, err
	}

	return session, nil
}

// LoadRecording loads recording from storage.
//
// Args:
//
//	sessionID: Session to load
//
// Returns:
//
//	Session recording if found
func (r *SessionRecorder) LoadRecording(sessionID string) (*SessionRecording, error) {
	return r.storage.LoadRecording(sessionID)
}

// ListRecordings lists all recordings.
func (r *SessionRecorder) ListRecordings(limit, offset int) ([]*SessionRecording, error) {
	return r.storage.ListRecordings(limit, offset)
}

// DeleteRecording deletes recording.
func (r *SessionRecorder) DeleteRecording(sessionID string) error {
	return r.storage.DeleteRecording(sessionID)
}

// SessionReplay replays recorded sessions for analysis and A/B testing.
//
// Takes recorded session and replays it through a (possibly different)
// agent to compare behavior.
//
// Example:
//
//	replay := NewSessionReplay()
//	recording, _ := recorder.LoadRecording("test-123")
//
//	// Replay with original agent
//	resultsA, _ := replay.Replay(recording, agentV1, "")
//
//	// Replay with new agent (A/B test)
//	resultsB, _ := replay.Replay(recording, agentV2, "")
//
//	// Compare
//	comparison := replay.Compare(resultsA, resultsB)
type SessionReplay struct{}

// NewSessionReplay creates a new session replay.
func NewSessionReplay() *SessionReplay {
	return &SessionReplay{}
}

// Replay replays session through agent.
//
// Args:
//
//	recording: Session recording to replay
//	agent: Agent to replay through
//	sessionID: Optional session ID (defaults to original)
//
// Returns:
//
//	Replay results with outputs and metrics
func (r *SessionReplay) Replay(recording *SessionRecording, agent agenkit.Agent, sessionID string) (map[string]interface{}, error) {
	if sessionID == "" {
		sessionID = recording.SessionID
	}

	results := map[string]interface{}{
		"session_id":          sessionID,
		"original_session_id": recording.SessionID,
		"interactions":        make([]map[string]interface{}, 0),
		"total_latency_ms":    0.0,
		"error_count":         0,
	}

	for _, interaction := range recording.Interactions {
		// Reconstruct input message
		inputMsg := &agenkit.Message{
			Role:     interaction.InputMessage["role"].(string),
			Content:  interaction.InputMessage["content"].(string),
			Metadata: getMapOrEmpty(interaction.InputMessage, "metadata"),
		}

		// Replay through agent
		start := time.Now()
		outputMsg, err := agent.Process(context.Background(), inputMsg)
		latency := time.Since(start).Milliseconds()

		if err != nil {
			results["error_count"] = results["error_count"].(int) + 1
			results["interactions"] = append(results["interactions"].([]map[string]interface{}), map[string]interface{}{
				"input":           interaction.InputMessage,
				"original_output": interaction.OutputMessage,
				"error":           err.Error(),
			})
		} else {
			results["interactions"] = append(results["interactions"].([]map[string]interface{}), map[string]interface{}{
				"input":               interaction.InputMessage,
				"original_output":     interaction.OutputMessage,
				"replay_output":       messageToDict(outputMsg),
				"original_latency_ms": interaction.LatencyMs,
				"replay_latency_ms":   float64(latency),
			})

			results["total_latency_ms"] = results["total_latency_ms"].(float64) + float64(latency)
		}
	}

	return results, nil
}

// Compare compares two replay results.
//
// Useful for A/B testing different agent versions.
//
// Args:
//
//	resultsA: First replay results
//	resultsB: Second replay results
//
// Returns:
//
//	Comparison metrics
func (r *SessionReplay) Compare(resultsA, resultsB map[string]interface{}) map[string]interface{} {
	interactionsA := resultsA["interactions"].([]map[string]interface{})
	interactionsB := resultsB["interactions"].([]map[string]interface{})

	latencyA := resultsA["total_latency_ms"].(float64)
	latencyB := resultsB["total_latency_ms"].(float64)

	latencyDiffPercent := 0.0
	if latencyA > 0 {
		latencyDiffPercent = (latencyB - latencyA) / latencyA * 100
	}

	comparison := map[string]interface{}{
		"interaction_count":    len(interactionsA),
		"latency_diff_ms":      latencyB - latencyA,
		"latency_diff_percent": latencyDiffPercent,
		"error_diff":           resultsB["error_count"].(int) - resultsA["error_count"].(int),
		"output_differences":   make([]map[string]interface{}, 0),
	}

	// Compare outputs
	for i := 0; i < len(interactionsA) && i < len(interactionsB); i++ {
		ia := interactionsA[i]
		ib := interactionsB[i]

		if _, hasErrorA := ia["error"]; hasErrorA {
			continue
		}
		if _, hasErrorB := ib["error"]; hasErrorB {
			continue
		}

		outputA := ia["replay_output"].(map[string]interface{})["content"].(string)
		outputB := ib["replay_output"].(map[string]interface{})["content"].(string)

		if outputA != outputB {
			comparison["output_differences"] = append(comparison["output_differences"].([]map[string]interface{}), map[string]interface{}{
				"interaction_index": i,
				"output_a":          outputA,
				"output_b":          outputB,
			})
		}
	}

	return comparison
}

// Helper functions

func messageToDict(message *agenkit.Message) map[string]interface{} {
	if message == nil {
		return map[string]interface{}{
			"role":     "",
			"content":  "",
			"metadata": make(map[string]interface{}),
		}
	}

	metadata := message.Metadata
	if metadata == nil {
		metadata = make(map[string]interface{})
	}

	return map[string]interface{}{
		"role":     message.Role,
		"content":  message.Content,
		"metadata": metadata,
	}
}

func getMapOrEmpty(data map[string]interface{}, key string) map[string]interface{} {
	if val, ok := data[key]; ok {
		if m, ok := val.(map[string]interface{}); ok {
			return m
		}
	}
	return make(map[string]interface{})
}
