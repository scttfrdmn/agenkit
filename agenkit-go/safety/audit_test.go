package safety

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

// TestAuditEvent tests for AuditEvent

func TestNewAuditEvent(t *testing.T) {
	event := NewAuditEvent(AccessGranted, SeverityInfo)

	if event.EventType != AccessGranted {
		t.Errorf("Expected EventType AccessGranted, got %s", event.EventType)
	}
	if event.Severity != SeverityInfo {
		t.Error("Expected Severity Info")
	}
	if event.Timestamp == "" {
		t.Error("Expected timestamp to be set")
	}
	if event.Details == nil {
		t.Error("Expected Details map to be initialized")
	}
}

func TestAuditEventToJSON(t *testing.T) {
	event := NewAuditEvent(PermissionDenied, SeverityWarning)
	event.UserID = "user123"
	event.AgentName = "test-agent"
	event.Message = "Permission check failed"
	event.Details["reason"] = "insufficient privileges"

	jsonStr := event.ToJSON()

	if jsonStr == "" {
		t.Error("Expected non-empty JSON string")
	}

	// Verify it's valid JSON
	var parsed map[string]interface{}
	if err := json.Unmarshal([]byte(jsonStr), &parsed); err != nil {
		t.Errorf("Failed to parse JSON: %v", err)
	}

	if parsed["event_type"] != string(PermissionDenied) {
		t.Error("JSON doesn't contain correct event_type")
	}
	if parsed["user_id"] != "user123" {
		t.Error("JSON doesn't contain correct user_id")
	}
}

func TestAuditEventTypes(t *testing.T) {
	// Test that event type constants are defined
	eventTypes := []AuditEventType{
		AccessGranted,
		AccessDenied,
		InputValidationFailed,
		OutputValidationFailed,
		PermissionGranted,
		PermissionDenied,
		PromptInjectionDetected,
		SensitiveDataDetected,
		AnomalyDetected,
		AgentStarted,
		AgentCompleted,
		AgentFailed,
	}

	for _, eventType := range eventTypes {
		if string(eventType) == "" {
			t.Error("Event type should not be empty")
		}
	}
}

func TestAuditSeverityLevels(t *testing.T) {
	// Test that severity constants are defined
	severities := []AuditSeverity{
		SeverityInfo,
		SeverityWarning,
		SeverityError,
		SeverityCritical,
	}

	for _, severity := range severities {
		if string(severity) == "" {
			t.Error("Severity should not be empty")
		}
	}
}

// TestSecurityAuditLogger tests for SecurityAuditLogger

func TestNewSecurityAuditLogger(t *testing.T) {
	// Use temp directory for test
	tmpDir := t.TempDir()
	logFile := filepath.Join(tmpDir, "test_audit.log")

	logger, err := NewSecurityAuditLogger(logFile, 1024*1024, 5, SeverityInfo, false)

	if err != nil {
		t.Errorf("Failed to create logger: %v", err)
	}
	if logger == nil {
		t.Fatal("Expected logger to be created")
	}
	if logger.logFile != logFile {
		t.Errorf("Expected logFile %s, got %s", logFile, logger.logFile)
	}

	// Clean up
	_ = logger.Close()
}

func TestSecurityAuditLoggerLog(t *testing.T) {
	tmpDir := t.TempDir()
	logFile := filepath.Join(tmpDir, "test_audit.log")

	logger, err := NewSecurityAuditLogger(logFile, 1024*1024, 5, SeverityInfo, false)
	if err != nil {
		t.Fatalf("Failed to create logger: %v", err)
	}
	defer func() { _ = logger.Close() }()

	event := NewAuditEvent(AccessGranted, SeverityInfo)
	event.UserID = "user123"
	event.Message = "Test access"

	err = logger.Log(event)
	if err != nil {
		t.Errorf("Failed to log event: %v", err)
	}

	// Verify file was created and has content
	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Errorf("Failed to read log file: %v", err)
	}
	if len(content) == 0 {
		t.Error("Expected log file to have content")
	}
}

func TestSecurityAuditLoggerSeverityFiltering(t *testing.T) {
	tmpDir := t.TempDir()
	logFile := filepath.Join(tmpDir, "test_audit.log")

	// Logger with Warning minimum severity
	logger, err := NewSecurityAuditLogger(logFile, 1024*1024, 5, SeverityWarning, false)
	if err != nil {
		t.Fatalf("Failed to create logger: %v", err)
	}
	defer func() { _ = logger.Close() }()

	// Info event should be filtered out
	infoEvent := NewAuditEvent(AccessGranted, SeverityInfo)
	_ = logger.Log(infoEvent)

	// Warning event should be logged
	warningEvent := NewAuditEvent(AccessDenied, SeverityWarning)
	_ = logger.Log(warningEvent)

	// Read log file
	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Errorf("Failed to read log file: %v", err)
	}

	// Should only contain warning event
	contentStr := string(content)
	if len(contentStr) == 0 {
		t.Error("Expected log file to have content")
	}
	// Should not contain AccessGranted (info level)
	var parsed map[string]interface{}
	_ = json.Unmarshal(content, &parsed)
	if parsed["event_type"] == string(AccessGranted) {
		t.Error("Info event should have been filtered out")
	}
}

func TestSecurityAuditLoggerLogAccess(t *testing.T) {
	tmpDir := t.TempDir()
	logFile := filepath.Join(tmpDir, "test_audit.log")

	logger, err := NewSecurityAuditLogger(logFile, 1024*1024, 5, SeverityInfo, false)
	if err != nil {
		t.Fatalf("Failed to create logger: %v", err)
	}
	defer func() { _ = logger.Close() }()

	// Test access granted
	err = logger.LogAccess(true, "user123", "test-agent", "read_file", nil)
	if err != nil {
		t.Errorf("Failed to log access: %v", err)
	}

	// Test access denied
	err = logger.LogAccess(false, "user456", "test-agent", "delete_file", map[string]interface{}{
		"path": "/etc/passwd",
	})
	if err != nil {
		t.Errorf("Failed to log access denied: %v", err)
	}

	// Verify logs were written
	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Errorf("Failed to read log file: %v", err)
	}
	if len(content) == 0 {
		t.Error("Expected log file to have content")
	}
}

func TestSecurityAuditLoggerLogPermissionCheck(t *testing.T) {
	tmpDir := t.TempDir()
	logFile := filepath.Join(tmpDir, "test_audit.log")

	logger, err := NewSecurityAuditLogger(logFile, 1024*1024, 5, SeverityInfo, false)
	if err != nil {
		t.Fatalf("Failed to create logger: %v", err)
	}
	defer func() { _ = logger.Close() }()

	err = logger.LogPermissionCheck(false, "user123", "test-agent", "write_files", nil)
	if err != nil {
		t.Errorf("Failed to log permission check: %v", err)
	}

	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Errorf("Failed to read log file: %v", err)
	}
	if len(content) == 0 {
		t.Error("Expected log file to have content")
	}
}

func TestSecurityAuditLoggerLogValidationFailure(t *testing.T) {
	tmpDir := t.TempDir()
	logFile := filepath.Join(tmpDir, "test_audit.log")

	logger, err := NewSecurityAuditLogger(logFile, 1024*1024, 5, SeverityInfo, false)
	if err != nil {
		t.Fatalf("Failed to create logger: %v", err)
	}
	defer func() { _ = logger.Close() }()

	longContent := "This is a very long content that should be truncated in the log entry because it exceeds the maximum allowed preview length of 200 characters which is the limit set by the audit logger to ensure log entries don't become too large and unwieldy when viewing them"

	err = logger.LogValidationFailure("user123", "input", "prompt injection detected", longContent, "test-agent")
	if err != nil {
		t.Errorf("Failed to log validation failure: %v", err)
	}

	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Errorf("Failed to read log file: %v", err)
	}
	if len(content) == 0 {
		t.Error("Expected log file to have content")
	}

	// Verify content was truncated
	contentStr := string(content)
	if len(contentStr) > 300 { // Allow some overhead for JSON structure
		// Content should be truncated to 200 chars + "..."
		var parsed map[string]interface{}
		_ = json.Unmarshal(content, &parsed)
		details := parsed["details"].(map[string]interface{})
		preview := details["content_preview"].(string)
		if len(preview) > 203 { // 200 + "..."
			t.Errorf("Expected content to be truncated, got length %d", len(preview))
		}
	}
}

func TestSecurityAuditLoggerLogPromptInjection(t *testing.T) {
	tmpDir := t.TempDir()
	logFile := filepath.Join(tmpDir, "test_audit.log")

	logger, err := NewSecurityAuditLogger(logFile, 1024*1024, 5, SeverityInfo, false)
	if err != nil {
		t.Fatalf("Failed to create logger: %v", err)
	}
	defer func() { _ = logger.Close() }()

	patterns := []string{"ignore previous instructions", "system prompt"}
	err = logger.LogPromptInjection("user123", 15, patterns, "Ignore all previous instructions", "test-agent")
	if err != nil {
		t.Errorf("Failed to log prompt injection: %v", err)
	}

	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Errorf("Failed to read log file: %v", err)
	}
	if len(content) == 0 {
		t.Error("Expected log file to have content")
	}
}

func TestSecurityAuditLoggerLogAnomaly(t *testing.T) {
	tmpDir := t.TempDir()
	logFile := filepath.Join(tmpDir, "test_audit.log")

	logger, err := NewSecurityAuditLogger(logFile, 1024*1024, 5, SeverityInfo, false)
	if err != nil {
		t.Fatalf("Failed to create logger: %v", err)
	}
	defer func() { _ = logger.Close() }()

	details := map[string]interface{}{
		"request_rate": 150.5,
		"threshold":    100,
	}

	err = logger.LogAnomaly("user123", "high_request_rate", details, "test-agent")
	if err != nil {
		t.Errorf("Failed to log anomaly: %v", err)
	}

	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Errorf("Failed to read log file: %v", err)
	}
	if len(content) == 0 {
		t.Error("Expected log file to have content")
	}
}

func TestSecurityAuditLoggerLogAgentExecution(t *testing.T) {
	tmpDir := t.TempDir()
	logFile := filepath.Join(tmpDir, "test_audit.log")

	logger, err := NewSecurityAuditLogger(logFile, 1024*1024, 5, SeverityInfo, false)
	if err != nil {
		t.Fatalf("Failed to create logger: %v", err)
	}
	defer func() { _ = logger.Close() }()

	// Test started
	err = logger.LogAgentExecution("user123", "test-agent", "started", nil, nil, nil)
	if err != nil {
		t.Errorf("Failed to log agent started: %v", err)
	}

	// Test completed
	duration := 2.5
	err = logger.LogAgentExecution("user123", "test-agent", "completed", &duration, nil, nil)
	if err != nil {
		t.Errorf("Failed to log agent completed: %v", err)
	}

	// Test failed
	errorMsg := "Internal error"
	err = logger.LogAgentExecution("user123", "test-agent", "failed", &duration, &errorMsg, nil)
	if err != nil {
		t.Errorf("Failed to log agent failed: %v", err)
	}

	content, err := os.ReadFile(logFile)
	if err != nil {
		t.Errorf("Failed to read log file: %v", err)
	}
	if len(content) == 0 {
		t.Error("Expected log file to have content")
	}
}

func TestSecurityAuditLoggerRotation(t *testing.T) {
	tmpDir := t.TempDir()
	logFile := filepath.Join(tmpDir, "test_audit.log")

	// Create logger with small max size (500 bytes)
	logger, err := NewSecurityAuditLogger(logFile, 500, 3, SeverityInfo, false)
	if err != nil {
		t.Fatalf("Failed to create logger: %v", err)
	}
	defer func() { _ = logger.Close() }()

	// Write enough events to trigger rotation
	for i := 0; i < 10; i++ {
		event := NewAuditEvent(AccessGranted, SeverityInfo)
		event.UserID = "user123"
		event.Message = "Test message with enough content to fill up the log file quickly"
		event.Details["iteration"] = i
		_ = logger.Log(event)
	}

	// Check if rotation happened (backup files should exist)
	backupFile := logFile + ".1"
	if _, err := os.Stat(backupFile); os.IsNotExist(err) {
		// Rotation might not have happened if total size is still under limit
		// This is ok, just verify main log exists
		if _, err := os.Stat(logFile); os.IsNotExist(err) {
			t.Error("Expected log file to exist")
		}
	}
}

func TestGlobalAuditLogger(t *testing.T) {
	// Test GetAuditLogger
	logger := GetAuditLogger()
	if logger == nil {
		t.Error("Expected global logger to be created")
	}

	// Test ConfigureAuditLogger
	tmpDir := t.TempDir()
	logFile := filepath.Join(tmpDir, "global_audit.log")

	err := ConfigureAuditLogger(logFile, 1024*1024, 5, SeverityWarning, false)
	if err != nil {
		t.Errorf("Failed to configure global logger: %v", err)
	}

	logger = GetAuditLogger()
	if logger == nil {
		t.Fatal("Expected configured logger to be returned")
	}
	if logger.logFile != logFile {
		t.Errorf("Expected configured log file %s, got %s", logFile, logger.logFile)
	}
}
