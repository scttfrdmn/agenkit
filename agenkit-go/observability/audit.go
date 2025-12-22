// Package observability provides audit logging for security and compliance.
package observability

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"sync"
	"time"

	"go.opentelemetry.io/otel/trace"
)

// AuditEventType represents the type of audit event.
type AuditEventType string

const (
	AuthAttempt         AuditEventType = "auth_attempt"
	AuthSuccess         AuditEventType = "auth_success"
	AuthFailure         AuditEventType = "auth_failure"
	Authorization       AuditEventType = "authorization"
	RateLimitExceeded   AuditEventType = "rate_limit_exceeded"
	ValidationFailure   AuditEventType = "validation_failure"
	ConfigurationChange AuditEventType = "configuration_change"
	SecurityViolation   AuditEventType = "security_violation"
	SuspiciousActivity  AuditEventType = "suspicious_activity"
	AgentRequest        AuditEventType = "agent_request"
	AgentResponse       AuditEventType = "agent_response"
	AgentError          AuditEventType = "agent_error"
)

// AuditSeverity represents the severity level of an audit event.
type AuditSeverity string

const (
	SeverityDebug    AuditSeverity = "debug"
	SeverityInfo     AuditSeverity = "info"
	SeverityWarning  AuditSeverity = "warning"
	SeverityError    AuditSeverity = "error"
	SeverityCritical AuditSeverity = "critical"
)

// AuditEvent represents a structured audit event.
type AuditEvent struct {
	EventType AuditEventType         `json:"event_type"`
	Severity  AuditSeverity          `json:"severity"`
	Message   string                 `json:"message"`
	Timestamp time.Time              `json:"timestamp"`
	Actor     string                 `json:"actor,omitempty"`
	Resource  string                 `json:"resource,omitempty"`
	Action    string                 `json:"action,omitempty"`
	Result    string                 `json:"result,omitempty"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
	TraceID   string                 `json:"trace_id,omitempty"`
	SpanID    string                 `json:"span_id,omitempty"`
}

// NewAuditEvent creates a new audit event with trace context.
func NewAuditEvent(eventType AuditEventType, severity AuditSeverity, message string) *AuditEvent {
	event := &AuditEvent{
		EventType: eventType,
		Severity:  severity,
		Message:   message,
		Timestamp: time.Now().UTC(),
		Metadata:  make(map[string]interface{}),
	}

	// Add trace context if available
	span := trace.SpanFromContext(context.TODO())
	if span.SpanContext().IsValid() {
		event.TraceID = span.SpanContext().TraceID().String()
		event.SpanID = span.SpanContext().SpanID().String()
	}

	return event
}

// AuditAdapter is the interface for audit log adapters.
type AuditAdapter interface {
	LogEvent(event *AuditEvent) error
}

// ConsoleAuditAdapter logs audit events to console.
type ConsoleAuditAdapter struct {
	UseColors bool
	mu        sync.Mutex
}

// NewConsoleAuditAdapter creates a new console adapter.
func NewConsoleAuditAdapter(useColors bool) *ConsoleAuditAdapter {
	return &ConsoleAuditAdapter{
		UseColors: useColors,
	}
}

// LogEvent logs an event to console.
func (a *ConsoleAuditAdapter) LogEvent(event *AuditEvent) error {
	a.mu.Lock()
	defer a.mu.Unlock()

	// ANSI color codes
	colors := map[AuditSeverity]string{
		SeverityDebug:    "\033[36m", // Cyan
		SeverityInfo:     "\033[32m", // Green
		SeverityWarning:  "\033[33m", // Yellow
		SeverityError:    "\033[31m", // Red
		SeverityCritical: "\033[35m", // Magenta
	}
	reset := "\033[0m"

	color := ""
	if a.UseColors {
		color = colors[event.Severity]
	}

	// Build message
	parts := []string{
		event.Timestamp.Format(time.RFC3339),
		fmt.Sprintf("%s%s%s", color, string(event.Severity), reset),
		fmt.Sprintf("[%s]", event.EventType),
	}

	if event.Actor != "" {
		parts = append(parts, fmt.Sprintf("actor=%s", event.Actor))
	}
	if event.Resource != "" {
		parts = append(parts, fmt.Sprintf("resource=%s", event.Resource))
	}
	if event.Action != "" {
		parts = append(parts, fmt.Sprintf("action=%s", event.Action))
	}
	if event.Result != "" {
		parts = append(parts, fmt.Sprintf("result=%s", event.Result))
	}

	parts = append(parts, event.Message)

	if event.TraceID != "" {
		parts = append(parts, fmt.Sprintf("trace_id=%s", event.TraceID))
	}

	// Write to appropriate stream
	stream := os.Stdout
	if event.Severity == SeverityError || event.Severity == SeverityCritical {
		stream = os.Stderr
	}

	for i, part := range parts {
		if i > 0 {
			if _, err := fmt.Fprint(stream, " "); err != nil {
				return fmt.Errorf("failed to write separator: %w", err)
			}
		}
		if _, err := fmt.Fprint(stream, part); err != nil {
			return fmt.Errorf("failed to write part: %w", err)
		}
	}
	if _, err := fmt.Fprintln(stream); err != nil {
		return fmt.Errorf("failed to write newline: %w", err)
	}

	return nil
}

// StructuredAuditAdapter logs audit events as JSON.
type StructuredAuditAdapter struct {
	Writer io.Writer
	mu     sync.Mutex
}

// NewStructuredAuditAdapter creates a new structured adapter.
func NewStructuredAuditAdapter(writer io.Writer) *StructuredAuditAdapter {
	if writer == nil {
		writer = os.Stdout
	}
	return &StructuredAuditAdapter{
		Writer: writer,
	}
}

// LogEvent logs an event as JSON.
func (a *StructuredAuditAdapter) LogEvent(event *AuditEvent) error {
	a.mu.Lock()
	defer a.mu.Unlock()

	data, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("failed to marshal audit event: %w", err)
	}

	_, err = fmt.Fprintln(a.Writer, string(data))
	return err
}

// FileAuditAdapter logs audit events to a file.
type FileAuditAdapter struct {
	FilePath   string
	Structured bool
	file       *os.File
	mu         sync.Mutex
}

// NewFileAuditAdapter creates a new file adapter.
func NewFileAuditAdapter(filePath string, structured bool) (*FileAuditAdapter, error) {
	// Create parent directory if needed
	// Note: In production, you'd want to use a proper rotating file writer

	file, err := os.OpenFile(filePath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0600)
	if err != nil {
		return nil, fmt.Errorf("failed to open audit log file: %w", err)
	}

	return &FileAuditAdapter{
		FilePath:   filePath,
		Structured: structured,
		file:       file,
	}, nil
}

// LogEvent logs an event to file.
func (a *FileAuditAdapter) LogEvent(event *AuditEvent) error {
	a.mu.Lock()
	defer a.mu.Unlock()

	var message string
	if a.Structured {
		data, err := json.Marshal(event)
		if err != nil {
			return fmt.Errorf("failed to marshal audit event: %w", err)
		}
		message = string(data)
	} else {
		// Human-readable format
		parts := []string{
			event.Timestamp.Format(time.RFC3339),
			fmt.Sprintf("[%s]", event.EventType),
			fmt.Sprintf("severity=%s", event.Severity),
		}
		if event.Actor != "" {
			parts = append(parts, fmt.Sprintf("actor=%s", event.Actor))
		}
		if event.Resource != "" {
			parts = append(parts, fmt.Sprintf("resource=%s", event.Resource))
		}
		if event.Result != "" {
			parts = append(parts, fmt.Sprintf("result=%s", event.Result))
		}
		parts = append(parts, event.Message)

		message = ""
		for i, part := range parts {
			if i > 0 {
				message += " "
			}
			message += part
		}
	}

	_, err := fmt.Fprintln(a.file, message)
	return err
}

// Close closes the file adapter.
func (a *FileAuditAdapter) Close() error {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.file.Close()
}

// AuditLogger is the main audit logger with pluggable adapters.
type AuditLogger struct {
	adapters []AuditAdapter
	mu       sync.RWMutex
}

// NewAuditLogger creates a new audit logger.
func NewAuditLogger(adapters ...AuditAdapter) *AuditLogger {
	if len(adapters) == 0 {
		adapters = []AuditAdapter{NewConsoleAuditAdapter(true)}
	}
	return &AuditLogger{
		adapters: adapters,
	}
}

// LogEvent logs an audit event to all adapters.
func (l *AuditLogger) LogEvent(event *AuditEvent) {
	l.mu.RLock()
	defer l.mu.RUnlock()

	for _, adapter := range l.adapters {
		if err := adapter.LogEvent(event); err != nil {
			// Don't let adapter failures break the application
			fmt.Fprintf(os.Stderr, "Audit adapter error: %v\n", err)
		}
	}
}

// LogAuthAttempt logs an authentication attempt.
func (l *AuditLogger) LogAuthAttempt(userID string, success bool, method, ipAddress, reason string, metadata map[string]interface{}) {
	var eventType AuditEventType
	var severity AuditSeverity
	var result string

	if success {
		eventType = AuthSuccess
		severity = SeverityInfo
		result = "success"
	} else {
		eventType = AuthFailure
		severity = SeverityWarning
		result = "failure"
	}

	message := fmt.Sprintf("Authentication %s for user %s", result, userID)
	if method != "" {
		message += fmt.Sprintf(" using %s", method)
	}
	if !success && reason != "" {
		message += fmt.Sprintf(": %s", reason)
	}

	event := NewAuditEvent(eventType, severity, message)
	event.Actor = userID
	event.Action = "authenticate"
	event.Result = result
	event.Metadata = metadata
	if event.Metadata == nil {
		event.Metadata = make(map[string]interface{})
	}
	event.Metadata["method"] = method
	event.Metadata["ip_address"] = ipAddress

	l.LogEvent(event)
}

// LogAuthorization logs an authorization decision.
func (l *AuditLogger) LogAuthorization(userID, resource, action string, allowed bool, reason string, metadata map[string]interface{}) {
	severity := SeverityInfo
	if !allowed {
		severity = SeverityWarning
	}

	result := "allowed"
	if !allowed {
		result = "denied"
	}

	message := fmt.Sprintf("Authorization %s for user %s to %s %s", result, userID, action, resource)
	if !allowed && reason != "" {
		message += fmt.Sprintf(": %s", reason)
	}

	event := NewAuditEvent(Authorization, severity, message)
	event.Actor = userID
	event.Resource = resource
	event.Action = action
	event.Result = result
	event.Metadata = metadata
	if event.Metadata == nil {
		event.Metadata = make(map[string]interface{})
	}
	event.Metadata["reason"] = reason

	l.LogEvent(event)
}

// LogRateLimitExceeded logs a rate limit violation.
func (l *AuditLogger) LogRateLimitExceeded(clientID, endpoint string, limit int, window string, metadata map[string]interface{}) {
	message := fmt.Sprintf("Rate limit exceeded for %s on %s (%d requests per %s)", clientID, endpoint, limit, window)

	event := NewAuditEvent(RateLimitExceeded, SeverityWarning, message)
	event.Actor = clientID
	event.Resource = endpoint
	event.Action = "request"
	event.Result = "rate_limited"
	event.Metadata = metadata
	if event.Metadata == nil {
		event.Metadata = make(map[string]interface{})
	}
	event.Metadata["limit"] = limit
	event.Metadata["window"] = window

	l.LogEvent(event)
}

// LogValidationFailure logs an input validation failure.
func (l *AuditLogger) LogValidationFailure(messageID, reason, field string, value interface{}, metadata map[string]interface{}) {
	message := fmt.Sprintf("Validation failure for message %s: %s", messageID, reason)
	if field != "" {
		message += fmt.Sprintf(" (field: %s)", field)
	}

	event := NewAuditEvent(ValidationFailure, SeverityWarning, message)
	event.Resource = messageID
	event.Action = "validate"
	event.Result = "failure"
	event.Metadata = metadata
	if event.Metadata == nil {
		event.Metadata = make(map[string]interface{})
	}
	event.Metadata["reason"] = reason
	event.Metadata["field"] = field
	event.Metadata["value"] = value

	l.LogEvent(event)
}

// LogConfigurationChange logs a configuration change.
func (l *AuditLogger) LogConfigurationChange(userID, component, parameter string, oldValue, newValue interface{}, metadata map[string]interface{}) {
	message := fmt.Sprintf("Configuration changed: %s.%s changed from %v to %v", component, parameter, oldValue, newValue)

	event := NewAuditEvent(ConfigurationChange, SeverityInfo, message)
	event.Actor = userID
	event.Resource = fmt.Sprintf("%s.%s", component, parameter)
	event.Action = "configure"
	event.Result = "success"
	event.Metadata = metadata
	if event.Metadata == nil {
		event.Metadata = make(map[string]interface{})
	}
	event.Metadata["old_value"] = oldValue
	event.Metadata["new_value"] = newValue

	l.LogEvent(event)
}

// LogSecurityViolation logs a security violation.
func (l *AuditLogger) LogSecurityViolation(clientID, violationType, description string, severity AuditSeverity, metadata map[string]interface{}) {
	message := fmt.Sprintf("Security violation (%s): %s", violationType, description)

	event := NewAuditEvent(SecurityViolation, severity, message)
	event.Actor = clientID
	event.Action = violationType
	event.Result = "violation"
	event.Metadata = metadata

	l.LogEvent(event)
}

// LogSuspiciousActivity logs suspicious activity.
func (l *AuditLogger) LogSuspiciousActivity(clientID, activityType, description string, indicators []string, metadata map[string]interface{}) {
	message := fmt.Sprintf("Suspicious activity detected (%s): %s", activityType, description)

	event := NewAuditEvent(SuspiciousActivity, SeverityWarning, message)
	event.Actor = clientID
	event.Action = activityType
	event.Result = "suspicious"
	event.Metadata = metadata
	if event.Metadata == nil {
		event.Metadata = make(map[string]interface{})
	}
	event.Metadata["indicators"] = indicators

	l.LogEvent(event)
}
