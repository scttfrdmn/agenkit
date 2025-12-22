package observability

import (
	"bytes"
	"encoding/json"
	"os"
	"testing"
)

func TestNewAuditEvent(t *testing.T) {
	event := NewAuditEvent(AuthSuccess, SeverityInfo, "User authenticated")

	if event.EventType != AuthSuccess {
		t.Errorf("Expected event type %s, got %s", AuthSuccess, event.EventType)
	}
	if event.Severity != SeverityInfo {
		t.Errorf("Expected severity %s, got %s", SeverityInfo, event.Severity)
	}
	if event.Message != "User authenticated" {
		t.Errorf("Expected message 'User authenticated', got %s", event.Message)
	}
	if event.Timestamp.IsZero() {
		t.Error("Expected non-zero timestamp")
	}
}

func TestConsoleAuditAdapter(t *testing.T) {
	adapter := NewConsoleAuditAdapter(false)

	event := NewAuditEvent(Authorization, SeverityInfo, "Access granted")
	event.Actor = "user123"
	event.Resource = "document456"
	event.Action = "read"
	event.Result = "allowed"

	err := adapter.LogEvent(event)
	if err != nil {
		t.Errorf("Failed to log event: %v", err)
	}
}

func TestStructuredAuditAdapter(t *testing.T) {
	var buf bytes.Buffer
	adapter := NewStructuredAuditAdapter(&buf)

	event := NewAuditEvent(RateLimitExceeded, SeverityWarning, "Rate limit exceeded")
	event.Actor = "client123"
	event.Resource = "/api/process"

	err := adapter.LogEvent(event)
	if err != nil {
		t.Errorf("Failed to log event: %v", err)
	}

	var logged map[string]interface{}
	if err := json.Unmarshal(buf.Bytes(), &logged); err != nil {
		t.Fatalf("Failed to parse logged JSON: %v", err)
	}

	if logged["event_type"] != string(RateLimitExceeded) {
		t.Errorf("Expected event_type %s, got %v", RateLimitExceeded, logged["event_type"])
	}
	if logged["actor"] != "client123" {
		t.Errorf("Expected actor 'client123', got %v", logged["actor"])
	}
}

func TestFileAuditAdapter(t *testing.T) {
	tmpFile, err := os.CreateTemp("", "audit-*.log")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	defer func() { _ = os.Remove(tmpFile.Name()) }()
	if err := tmpFile.Close(); err != nil {
		t.Fatalf("Failed to close temp file: %v", err)
	}

	adapter, err := NewFileAuditAdapter(tmpFile.Name(), true)
	if err != nil {
		t.Fatalf("Failed to create file adapter: %v", err)
	}
	defer func() { _ = adapter.Close() }()

	event := NewAuditEvent(ConfigurationChange, SeverityInfo, "Configuration updated")
	event.Actor = "admin"
	event.Resource = "timeout.max_duration"

	err = adapter.LogEvent(event)
	if err != nil {
		t.Errorf("Failed to log event: %v", err)
	}

	// Read and verify
	content, err := os.ReadFile(tmpFile.Name())
	if err != nil {
		t.Fatalf("Failed to read log file: %v", err)
	}

	var logged map[string]interface{}
	if err := json.Unmarshal(content, &logged); err != nil {
		t.Fatalf("Failed to parse logged JSON: %v", err)
	}

	if logged["event_type"] != string(ConfigurationChange) {
		t.Errorf("Expected event_type %s, got %v", ConfigurationChange, logged["event_type"])
	}
}

func TestAuditLoggerLogAuthAttempt(t *testing.T) {
	var buf bytes.Buffer
	adapter := NewStructuredAuditAdapter(&buf)
	logger := NewAuditLogger(adapter)

	logger.LogAuthAttempt("user123", true, "password", "192.168.1.1", "", nil)

	var logged map[string]interface{}
	if err := json.Unmarshal(buf.Bytes(), &logged); err != nil {
		t.Fatalf("Failed to parse logged JSON: %v", err)
	}

	if logged["event_type"] != string(AuthSuccess) {
		t.Errorf("Expected event_type %s, got %v", AuthSuccess, logged["event_type"])
	}
	if logged["actor"] != "user123" {
		t.Errorf("Expected actor 'user123', got %v", logged["actor"])
	}
}

func TestAuditLoggerLogAuthorization(t *testing.T) {
	var buf bytes.Buffer
	adapter := NewStructuredAuditAdapter(&buf)
	logger := NewAuditLogger(adapter)

	logger.LogAuthorization("user456", "document789", "delete", false, "insufficient_permissions", nil)

	var logged map[string]interface{}
	if err := json.Unmarshal(buf.Bytes(), &logged); err != nil {
		t.Fatalf("Failed to parse logged JSON: %v", err)
	}

	if logged["event_type"] != string(Authorization) {
		t.Errorf("Expected event_type %s, got %v", Authorization, logged["event_type"])
	}
	if logged["severity"] != string(SeverityWarning) {
		t.Errorf("Expected severity %s, got %v", SeverityWarning, logged["severity"])
	}
	if logged["result"] != "denied" {
		t.Errorf("Expected result 'denied', got %v", logged["result"])
	}
}

func TestAuditLoggerLogRateLimitExceeded(t *testing.T) {
	var buf bytes.Buffer
	adapter := NewStructuredAuditAdapter(&buf)
	logger := NewAuditLogger(adapter)

	logger.LogRateLimitExceeded("client123", "/api/process", 100, "1m", nil)

	var logged map[string]interface{}
	if err := json.Unmarshal(buf.Bytes(), &logged); err != nil {
		t.Fatalf("Failed to parse logged JSON: %v", err)
	}

	if logged["event_type"] != string(RateLimitExceeded) {
		t.Errorf("Expected event_type %s, got %v", RateLimitExceeded, logged["event_type"])
	}

	metadata := logged["metadata"].(map[string]interface{})
	if metadata["limit"] != float64(100) {
		t.Errorf("Expected limit 100, got %v", metadata["limit"])
	}
}

func TestAuditLoggerLogValidationFailure(t *testing.T) {
	var buf bytes.Buffer
	adapter := NewStructuredAuditAdapter(&buf)
	logger := NewAuditLogger(adapter)

	logger.LogValidationFailure("msg123", "field_required", "email", nil, nil)

	var logged map[string]interface{}
	if err := json.Unmarshal(buf.Bytes(), &logged); err != nil {
		t.Fatalf("Failed to parse logged JSON: %v", err)
	}

	if logged["event_type"] != string(ValidationFailure) {
		t.Errorf("Expected event_type %s, got %v", ValidationFailure, logged["event_type"])
	}
	if logged["resource"] != "msg123" {
		t.Errorf("Expected resource 'msg123', got %v", logged["resource"])
	}
}

func TestAuditLoggerLogConfigurationChange(t *testing.T) {
	var buf bytes.Buffer
	adapter := NewStructuredAuditAdapter(&buf)
	logger := NewAuditLogger(adapter)

	logger.LogConfigurationChange("admin", "timeout_middleware", "max_duration", 30, 60, nil)

	var logged map[string]interface{}
	if err := json.Unmarshal(buf.Bytes(), &logged); err != nil {
		t.Fatalf("Failed to parse logged JSON: %v", err)
	}

	if logged["event_type"] != string(ConfigurationChange) {
		t.Errorf("Expected event_type %s, got %v", ConfigurationChange, logged["event_type"])
	}
	if logged["actor"] != "admin" {
		t.Errorf("Expected actor 'admin', got %v", logged["actor"])
	}
}

func TestAuditLoggerLogSecurityViolation(t *testing.T) {
	var buf bytes.Buffer
	adapter := NewStructuredAuditAdapter(&buf)
	logger := NewAuditLogger(adapter)

	logger.LogSecurityViolation("attacker", "sql_injection", "Attempted SQL injection", SeverityCritical, nil)

	var logged map[string]interface{}
	if err := json.Unmarshal(buf.Bytes(), &logged); err != nil {
		t.Fatalf("Failed to parse logged JSON: %v", err)
	}

	if logged["event_type"] != string(SecurityViolation) {
		t.Errorf("Expected event_type %s, got %v", SecurityViolation, logged["event_type"])
	}
	if logged["severity"] != string(SeverityCritical) {
		t.Errorf("Expected severity %s, got %v", SeverityCritical, logged["severity"])
	}
}

func TestAuditLoggerLogSuspiciousActivity(t *testing.T) {
	var buf bytes.Buffer
	adapter := NewStructuredAuditAdapter(&buf)
	logger := NewAuditLogger(adapter)

	indicators := []string{"10_failed_logins_1min", "different_user_agents"}
	logger.LogSuspiciousActivity("192.168.1.200", "brute_force", "Multiple failed login attempts", indicators, nil)

	var logged map[string]interface{}
	if err := json.Unmarshal(buf.Bytes(), &logged); err != nil {
		t.Fatalf("Failed to parse logged JSON: %v", err)
	}

	if logged["event_type"] != string(SuspiciousActivity) {
		t.Errorf("Expected event_type %s, got %v", SuspiciousActivity, logged["event_type"])
	}
}

func TestAuditLoggerDefaultAdapter(t *testing.T) {
	// Should use console adapter by default
	logger := NewAuditLogger()

	logger.LogAuthAttempt("user789", true, "", "", "", nil)

	// If we get here without panicking, the default adapter works
}
