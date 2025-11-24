package safety

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// AuditEventType represents types of audit events.
type AuditEventType string

const (
	// Access events
	AccessGranted AuditEventType = "access_granted"
	AccessDenied  AuditEventType = "access_denied"

	// Validation events
	InputValidationFailed  AuditEventType = "input_validation_failed"
	OutputValidationFailed AuditEventType = "output_validation_failed"

	// Permission events
	PermissionGranted AuditEventType = "permission_granted"
	PermissionDenied  AuditEventType = "permission_denied"

	// Security events
	PromptInjectionDetected AuditEventType = "prompt_injection_detected"
	SensitiveDataDetected   AuditEventType = "sensitive_data_detected"
	AnomalyDetected         AuditEventType = "anomaly_detected"

	// Operational events
	AgentStarted   AuditEventType = "agent_started"
	AgentCompleted AuditEventType = "agent_completed"
	AgentFailed    AuditEventType = "agent_failed"
)

// AuditSeverity represents severity levels for audit events.
type AuditSeverity string

const (
	SeverityInfo     AuditSeverity = "info"
	SeverityWarning  AuditSeverity = "warning"
	SeverityError    AuditSeverity = "error"
	SeverityCritical AuditSeverity = "critical"
)

// AuditEvent represents a structured audit event.
//
// Contains all information needed for security auditing and compliance.
type AuditEvent struct {
	EventType AuditEventType         `json:"event_type"`
	Severity  AuditSeverity          `json:"severity"`
	Timestamp string                 `json:"timestamp"`
	UserID    string                 `json:"user_id,omitempty"`
	AgentName string                 `json:"agent_name,omitempty"`
	Message   string                 `json:"message,omitempty"`
	Details   map[string]interface{} `json:"details,omitempty"`
}

// NewAuditEvent creates a new audit event.
func NewAuditEvent(eventType AuditEventType, severity AuditSeverity) *AuditEvent {
	return &AuditEvent{
		EventType: eventType,
		Severity:  severity,
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Details:   make(map[string]interface{}),
	}
}

// ToJSON converts audit event to JSON string.
func (e *AuditEvent) ToJSON() string {
	data, err := json.Marshal(e)
	if err != nil {
		return fmt.Sprintf("{\"error\": \"failed to serialize: %v\"}", err)
	}
	return string(data)
}

// SecurityAuditLogger provides security audit logging with structured logging.
//
// Features:
//   - Structured JSON logging
//   - Log rotation
//   - Severity-based filtering
//   - Multiple output targets
//   - Searchable audit trail
//
// Example:
//
//	logger := NewSecurityAuditLogger("security_audit.log", 100*1024*1024, 10, SeverityInfo, true)
//	event := NewAuditEvent(AccessGranted, SeverityInfo)
//	event.UserID = "user123"
//	event.Message = "User accessed resource"
//	logger.Log(event)
type SecurityAuditLogger struct {
	logFile          string
	maxBytes         int
	backupCount      int
	minSeverity      AuditSeverity
	alsoLogToConsole bool
	mu               sync.Mutex
	currentFile      *os.File
	currentBytes     int
	severityOrder    map[AuditSeverity]int
}

// NewSecurityAuditLogger creates a new security audit logger.
//
// Args:
//
//	logFile: Path to log file
//	maxBytes: Maximum log file size before rotation (100MB default)
//	backupCount: Number of backup files to keep
//	minSeverity: Minimum severity to log
//	alsoLogToConsole: Also output to console
//
// Example:
//
//	logger := NewSecurityAuditLogger("security_audit.log", 100*1024*1024, 10, SeverityInfo, true)
func NewSecurityAuditLogger(logFile string, maxBytes int, backupCount int, minSeverity AuditSeverity, alsoLogToConsole bool) (*SecurityAuditLogger, error) {
	logger := &SecurityAuditLogger{
		logFile:          logFile,
		maxBytes:         maxBytes,
		backupCount:      backupCount,
		minSeverity:      minSeverity,
		alsoLogToConsole: alsoLogToConsole,
		severityOrder: map[AuditSeverity]int{
			SeverityInfo:     0,
			SeverityWarning:  1,
			SeverityError:    2,
			SeverityCritical: 3,
		},
	}

	// Open initial log file
	if err := logger.openLogFile(); err != nil {
		return nil, err
	}

	return logger, nil
}

// openLogFile opens or reopens the log file.
func (l *SecurityAuditLogger) openLogFile() error {
	// Close existing file if open
	if l.currentFile != nil {
		_ = l.currentFile.Close()
	}

	// Create directory if needed
	dir := filepath.Dir(l.logFile)
	if dir != "." && dir != "" {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return fmt.Errorf("failed to create log directory: %w", err)
		}
	}

	// Open file in append mode
	file, err := os.OpenFile(l.logFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return fmt.Errorf("failed to open log file: %w", err)
	}

	// Get current file size
	info, err := file.Stat()
	if err != nil {
		_ = file.Close()
		return fmt.Errorf("failed to stat log file: %w", err)
	}

	l.currentFile = file
	l.currentBytes = int(info.Size())

	return nil
}

// rotateLogFile rotates the log file.
func (l *SecurityAuditLogger) rotateLogFile() error {
	// Close current file
	if l.currentFile != nil {
		_ = l.currentFile.Close()
		l.currentFile = nil
	}

	// Rotate backup files
	for i := l.backupCount - 1; i >= 0; i-- {
		oldName := l.logFile
		newName := fmt.Sprintf("%s.%d", l.logFile, i+1)
		if i > 0 {
			oldName = fmt.Sprintf("%s.%d", l.logFile, i)
		}

		if _, err := os.Stat(oldName); err == nil {
			_ = os.Rename(oldName, newName)
		}
	}

	// Open new file
	return l.openLogFile()
}

// shouldLog checks if event should be logged based on severity.
func (l *SecurityAuditLogger) shouldLog(severity AuditSeverity) bool {
	return l.severityOrder[severity] >= l.severityOrder[l.minSeverity]
}

// Log logs an audit event.
func (l *SecurityAuditLogger) Log(event *AuditEvent) error {
	if !l.shouldLog(event.Severity) {
		return nil
	}

	l.mu.Lock()
	defer l.mu.Unlock()

	// Convert to JSON
	jsonStr := event.ToJSON() + "\n"
	jsonBytes := []byte(jsonStr)

	// Check if rotation needed
	if l.currentBytes+len(jsonBytes) > l.maxBytes {
		if err := l.rotateLogFile(); err != nil {
			log.Printf("WARNING: Failed to rotate log file: %v", err)
		}
	}

	// Write to file
	if l.currentFile != nil {
		if _, err := l.currentFile.Write(jsonBytes); err != nil {
			return fmt.Errorf("failed to write to log file: %w", err)
		}
		l.currentBytes += len(jsonBytes)
	}

	// Also log to console if enabled
	if l.alsoLogToConsole {
		fmt.Print(jsonStr)
	}

	return nil
}

// LogAccess logs an access attempt.
func (l *SecurityAuditLogger) LogAccess(granted bool, userID, agentName, action string, details map[string]interface{}) error {
	eventType := AccessGranted
	severity := SeverityInfo
	message := fmt.Sprintf("Access granted for action: %s", action)

	if !granted {
		eventType = AccessDenied
		severity = SeverityWarning
		message = fmt.Sprintf("Access denied for action: %s", action)
	}

	event := NewAuditEvent(eventType, severity)
	event.UserID = userID
	event.AgentName = agentName
	event.Message = message
	if details != nil {
		event.Details = details
	}

	return l.Log(event)
}

// LogPermissionCheck logs a permission check.
func (l *SecurityAuditLogger) LogPermissionCheck(granted bool, userID, agentName, permission string, details map[string]interface{}) error {
	eventType := PermissionGranted
	severity := SeverityInfo
	message := fmt.Sprintf("Permission %s: granted", permission)

	if !granted {
		eventType = PermissionDenied
		severity = SeverityWarning
		message = fmt.Sprintf("Permission %s: denied", permission)
	}

	event := NewAuditEvent(eventType, severity)
	event.UserID = userID
	event.AgentName = agentName
	event.Message = message
	if details != nil {
		event.Details = details
	}

	return l.Log(event)
}

// LogValidationFailure logs a validation failure.
func (l *SecurityAuditLogger) LogValidationFailure(userID, validationType, reason string, contentPreview string, agentName string) error {
	// Truncate content preview
	if len(contentPreview) > 200 {
		contentPreview = contentPreview[:200] + "..."
	}

	eventType := InputValidationFailed
	if validationType == "output" {
		eventType = OutputValidationFailed
	}

	event := NewAuditEvent(eventType, SeverityError)
	event.UserID = userID
	event.AgentName = agentName
	event.Message = fmt.Sprintf("%s validation failed: %s", validationType, reason)
	event.Details = map[string]interface{}{
		"validation_type": validationType,
		"reason":          reason,
		"content_preview": contentPreview,
	}

	return l.Log(event)
}

// LogPromptInjection logs a prompt injection detection.
func (l *SecurityAuditLogger) LogPromptInjection(userID string, score int, matchedPatterns []string, contentPreview string, agentName string) error {
	// Truncate content preview
	if len(contentPreview) > 200 {
		contentPreview = contentPreview[:200] + "..."
	}

	event := NewAuditEvent(PromptInjectionDetected, SeverityError)
	event.UserID = userID
	event.AgentName = agentName
	event.Message = fmt.Sprintf("Prompt injection detected (score: %d, patterns: %d)", score, len(matchedPatterns))
	event.Details = map[string]interface{}{
		"score":            score,
		"matched_patterns": matchedPatterns,
		"content_preview":  contentPreview,
	}

	return l.Log(event)
}

// LogAnomaly logs an anomaly detection.
func (l *SecurityAuditLogger) LogAnomaly(userID, anomalyType string, details map[string]interface{}, agentName string) error {
	event := NewAuditEvent(AnomalyDetected, SeverityWarning)
	event.UserID = userID
	event.AgentName = agentName
	event.Message = fmt.Sprintf("Anomaly detected: %s", anomalyType)

	if details == nil {
		details = make(map[string]interface{})
	}
	details["anomaly_type"] = anomalyType
	event.Details = details

	return l.Log(event)
}

// LogAgentExecution logs agent execution.
func (l *SecurityAuditLogger) LogAgentExecution(userID, agentName, status string, duration *float64, errorMsg *string, details map[string]interface{}) error {
	eventTypeMap := map[string]AuditEventType{
		"started":   AgentStarted,
		"completed": AgentCompleted,
		"failed":    AgentFailed,
	}

	severityMap := map[string]AuditSeverity{
		"started":   SeverityInfo,
		"completed": SeverityInfo,
		"failed":    SeverityError,
	}

	eventType := eventTypeMap[status]
	severity := severityMap[status]

	message := fmt.Sprintf("Agent %s", status)
	if duration != nil {
		message += fmt.Sprintf(" (%.2fs)", *duration)
	}

	event := NewAuditEvent(eventType, severity)
	event.UserID = userID
	event.AgentName = agentName
	event.Message = message

	if details == nil {
		details = make(map[string]interface{})
	}
	if duration != nil {
		details["duration_seconds"] = *duration
	}
	if errorMsg != nil {
		details["error"] = *errorMsg
	}
	event.Details = details

	return l.Log(event)
}

// Close closes the audit logger.
func (l *SecurityAuditLogger) Close() error {
	l.mu.Lock()
	defer l.mu.Unlock()

	if l.currentFile != nil {
		return l.currentFile.Close()
	}
	return nil
}

// Global audit logger instance
var globalAuditLogger *SecurityAuditLogger
var globalAuditLoggerMu sync.Mutex

// GetAuditLogger returns the global audit logger instance.
func GetAuditLogger() *SecurityAuditLogger {
	globalAuditLoggerMu.Lock()
	defer globalAuditLoggerMu.Unlock()

	if globalAuditLogger == nil {
		logger, err := NewSecurityAuditLogger("security_audit.log", 100*1024*1024, 10, SeverityInfo, true)
		if err != nil {
			log.Printf("WARNING: Failed to create audit logger: %v", err)
			return nil
		}
		globalAuditLogger = logger
	}

	return globalAuditLogger
}

// ConfigureAuditLogger configures the global audit logger.
func ConfigureAuditLogger(logFile string, maxBytes int, backupCount int, minSeverity AuditSeverity, alsoLogToConsole bool) error {
	globalAuditLoggerMu.Lock()
	defer globalAuditLoggerMu.Unlock()

	logger, err := NewSecurityAuditLogger(logFile, maxBytes, backupCount, minSeverity, alsoLogToConsole)
	if err != nil {
		return err
	}

	// Close old logger if exists
	if globalAuditLogger != nil {
		_ = globalAuditLogger.Close()
	}

	globalAuditLogger = logger
	return nil
}
