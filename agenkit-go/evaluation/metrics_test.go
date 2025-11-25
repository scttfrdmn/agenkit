package evaluation

import (
	"testing"
	"time"
)

func TestNewMetricMeasurement(t *testing.T) {
	measurement := NewMetricMeasurement("accuracy", 0.95, MetricTypeSuccessRate)

	if measurement.Name != "accuracy" {
		t.Errorf("Expected name 'accuracy', got %q", measurement.Name)
	}

	if measurement.Value != 0.95 {
		t.Errorf("Expected value 0.95, got %.2f", measurement.Value)
	}

	if measurement.Type != MetricTypeSuccessRate {
		t.Errorf("Expected type %q, got %q", MetricTypeSuccessRate, measurement.Type)
	}

	if measurement.Timestamp == "" {
		t.Error("Expected timestamp to be set")
	}

	// Verify timestamp is valid RFC3339
	_, err := time.Parse(time.RFC3339, measurement.Timestamp)
	if err != nil {
		t.Errorf("Expected valid RFC3339 timestamp, got error: %v", err)
	}
}

func TestNewErrorRecord(t *testing.T) {
	details := map[string]interface{}{
		"code":    500,
		"message": "Internal error",
	}

	record := NewErrorRecord("timeout", "Request timed out", details)

	if record.Type != "timeout" {
		t.Errorf("Expected type 'timeout', got %q", record.Type)
	}

	if record.Message != "Request timed out" {
		t.Errorf("Expected message 'Request timed out', got %q", record.Message)
	}

	if len(record.Details) != 2 {
		t.Errorf("Expected 2 details, got %d", len(record.Details))
	}

	if record.Timestamp == "" {
		t.Error("Expected timestamp to be set")
	}
}

func TestNewSessionResult(t *testing.T) {
	result := NewSessionResult("session-123", "test-agent")

	if result.SessionID != "session-123" {
		t.Errorf("Expected session ID 'session-123', got %q", result.SessionID)
	}

	if result.AgentName != "test-agent" {
		t.Errorf("Expected agent name 'test-agent', got %q", result.AgentName)
	}

	if result.Status != SessionStatusRunning {
		t.Errorf("Expected status %q, got %q", SessionStatusRunning, result.Status)
	}

	if result.StartTime == "" {
		t.Error("Expected start time to be set")
	}

	if result.EndTime != nil {
		t.Error("Expected end time to be nil for new session")
	}

	if len(result.Measurements) != 0 {
		t.Errorf("Expected 0 measurements, got %d", len(result.Measurements))
	}

	if len(result.Errors) != 0 {
		t.Errorf("Expected 0 errors, got %d", len(result.Errors))
	}
}

func TestSessionResult_AddMetricMeasurement(t *testing.T) {
	result := NewSessionResult("session-1", "agent-1")

	measurement := NewMetricMeasurement("latency", 123.45, MetricTypeDuration)
	result.AddMetricMeasurement(measurement)

	if len(result.Measurements) != 1 {
		t.Fatalf("Expected 1 measurement, got %d", len(result.Measurements))
	}

	if result.Measurements[0].Name != "latency" {
		t.Errorf("Expected measurement name 'latency', got %q", result.Measurements[0].Name)
	}
}

func TestSessionResult_AddError(t *testing.T) {
	result := NewSessionResult("session-1", "agent-1")

	details := map[string]interface{}{"code": 404}
	result.AddError("not_found", "Resource not found", details)

	if len(result.Errors) != 1 {
		t.Fatalf("Expected 1 error, got %d", len(result.Errors))
	}

	if result.Errors[0].Type != "not_found" {
		t.Errorf("Expected error type 'not_found', got %q", result.Errors[0].Type)
	}

	if result.Errors[0].Message != "Resource not found" {
		t.Errorf("Expected error message 'Resource not found', got %q", result.Errors[0].Message)
	}
}

func TestSessionResult_SetStatus(t *testing.T) {
	result := NewSessionResult("session-1", "agent-1")

	// Initially running
	if result.Status != SessionStatusRunning {
		t.Errorf("Expected initial status %q, got %q", SessionStatusRunning, result.Status)
	}

	if result.EndTime != nil {
		t.Error("Expected end time to be nil initially")
	}

	// Set to completed
	result.SetStatus(SessionStatusCompleted)

	if result.Status != SessionStatusCompleted {
		t.Errorf("Expected status %q, got %q", SessionStatusCompleted, result.Status)
	}

	if result.EndTime == nil {
		t.Error("Expected end time to be set after status change")
	}
}

func TestSessionResult_SetStatusIdempotent(t *testing.T) {
	result := NewSessionResult("session-1", "agent-1")

	result.SetStatus(SessionStatusCompleted)
	firstEndTime := result.EndTime

	// Wait a bit
	time.Sleep(10 * time.Millisecond)

	// Set again - should not update end time
	result.SetStatus(SessionStatusFailed)

	if result.Status != SessionStatusFailed {
		t.Errorf("Expected status %q, got %q", SessionStatusFailed, result.Status)
	}

	// End time should be the same
	if result.EndTime != firstEndTime {
		t.Error("Expected end time to remain unchanged")
	}
}

func TestSessionResult_GetMetric(t *testing.T) {
	result := NewSessionResult("session-1", "agent-1")

	result.AddMetricMeasurement(NewMetricMeasurement("accuracy", 0.9, MetricTypeSuccessRate))
	result.AddMetricMeasurement(NewMetricMeasurement("latency", 100.0, MetricTypeDuration))

	// Get existing metric
	metric := result.GetMetric("accuracy")
	if metric == nil {
		t.Fatal("Expected to find 'accuracy' metric")
	}

	if metric.Value != 0.9 {
		t.Errorf("Expected accuracy value 0.9, got %.2f", metric.Value)
	}

	// Get non-existent metric
	metric = result.GetMetric("non_existent")
	if metric != nil {
		t.Error("Expected nil for non-existent metric")
	}
}

func TestSessionResult_GetMetricsByType(t *testing.T) {
	result := NewSessionResult("session-1", "agent-1")

	result.AddMetricMeasurement(NewMetricMeasurement("accuracy", 0.9, MetricTypeSuccessRate))
	result.AddMetricMeasurement(NewMetricMeasurement("precision", 0.85, MetricTypeQualityScore))
	result.AddMetricMeasurement(NewMetricMeasurement("recall", 0.88, MetricTypeSuccessRate))
	result.AddMetricMeasurement(NewMetricMeasurement("latency", 100.0, MetricTypeDuration))

	// Get success rate metrics
	successMetrics := result.GetMetricsByType(MetricTypeSuccessRate)
	if len(successMetrics) != 2 {
		t.Errorf("Expected 2 success rate metrics, got %d", len(successMetrics))
	}

	// Get quality metrics
	qualityMetrics := result.GetMetricsByType(MetricTypeQualityScore)
	if len(qualityMetrics) != 1 {
		t.Errorf("Expected 1 quality metric, got %d", len(qualityMetrics))
	}

	// Get non-existent type
	customMetrics := result.GetMetricsByType(MetricTypeCustom)
	if len(customMetrics) != 0 {
		t.Errorf("Expected 0 custom metrics, got %d", len(customMetrics))
	}
}

func TestSessionResult_DurationSeconds(t *testing.T) {
	result := NewSessionResult("session-1", "agent-1")

	// Initially nil (session not ended)
	duration := result.DurationSeconds()
	if duration != nil {
		t.Error("Expected nil duration for running session")
	}

	// Complete the session
	result.SetStatus(SessionStatusCompleted)

	// Should have duration now
	duration = result.DurationSeconds()
	if duration == nil {
		t.Fatal("Expected non-nil duration after session completion")
	}

	// Duration should be very small (just created)
	if *duration < 0 || *duration > 1.0 {
		t.Errorf("Expected duration between 0 and 1 second, got %.3f", *duration)
	}
}

func TestSessionResult_ToJSON(t *testing.T) {
	result := NewSessionResult("session-1", "agent-1")
	result.AddMetricMeasurement(NewMetricMeasurement("accuracy", 0.95, MetricTypeSuccessRate))
	result.AddError("timeout", "Request timed out", nil)
	result.SetStatus(SessionStatusCompleted)

	jsonStr, err := result.ToJSON()
	if err != nil {
		t.Fatalf("ToJSON failed: %v", err)
	}

	if jsonStr == "" {
		t.Error("Expected non-empty JSON string")
	}

	// Verify we can parse it back
	parsed, err := FromJSON(jsonStr)
	if err != nil {
		t.Fatalf("FromJSON failed: %v", err)
	}

	if parsed.SessionID != "session-1" {
		t.Errorf("Expected session ID 'session-1', got %q", parsed.SessionID)
	}

	if len(parsed.Measurements) != 1 {
		t.Errorf("Expected 1 measurement, got %d", len(parsed.Measurements))
	}

	if len(parsed.Errors) != 1 {
		t.Errorf("Expected 1 error, got %d", len(parsed.Errors))
	}
}

func TestFromJSON_Invalid(t *testing.T) {
	_, err := FromJSON("invalid json")
	if err == nil {
		t.Error("Expected error for invalid JSON")
	}
}

func TestNewMetricsCollector(t *testing.T) {
	collector := NewMetricsCollector()

	if collector == nil {
		t.Fatal("Expected non-nil collector")
	}

	if len(collector.results) != 0 {
		t.Errorf("Expected 0 results, got %d", len(collector.results))
	}
}

func TestMetricsCollector_AddResult(t *testing.T) {
	collector := NewMetricsCollector()

	result1 := NewSessionResult("session-1", "agent-1")
	result2 := NewSessionResult("session-2", "agent-2")

	collector.AddResult(result1)
	collector.AddResult(result2)

	if len(collector.results) != 2 {
		t.Errorf("Expected 2 results, got %d", len(collector.results))
	}
}

func TestMetricsCollector_GetStatistics(t *testing.T) {
	collector := NewMetricsCollector()

	// Add completed session
	result1 := NewSessionResult("session-1", "agent-1")
	result1.SetStatus(SessionStatusCompleted)
	collector.AddResult(result1)

	// Add failed session
	result2 := NewSessionResult("session-2", "agent-2")
	result2.AddError("error1", "First error", nil)
	result2.AddError("error2", "Second error", nil)
	result2.SetStatus(SessionStatusFailed)
	collector.AddResult(result2)

	// Add another completed session
	result3 := NewSessionResult("session-3", "agent-3")
	result3.SetStatus(SessionStatusCompleted)
	collector.AddResult(result3)

	stats := collector.GetStatistics()

	if stats["session_count"] != 3 {
		t.Errorf("Expected session_count 3, got %v", stats["session_count"])
	}

	if stats["completed_count"] != 2 {
		t.Errorf("Expected completed_count 2, got %v", stats["completed_count"])
	}

	if stats["failed_count"] != 1 {
		t.Errorf("Expected failed_count 1, got %v", stats["failed_count"])
	}

	successRate := stats["success_rate"].(float64)
	if successRate < 0.66 || successRate > 0.67 {
		t.Errorf("Expected success_rate ~0.67, got %.2f", successRate)
	}

	if stats["total_errors"] != 2 {
		t.Errorf("Expected total_errors 2, got %v", stats["total_errors"])
	}

	avgErrors := stats["avg_errors_per_session"].(float64)
	if avgErrors < 0.66 || avgErrors > 0.67 {
		t.Errorf("Expected avg_errors_per_session ~0.67, got %.2f", avgErrors)
	}
}

func TestMetricsCollector_GetStatisticsEmpty(t *testing.T) {
	collector := NewMetricsCollector()

	stats := collector.GetStatistics()

	if stats["session_count"] != 0 {
		t.Errorf("Expected session_count 0, got %v", stats["session_count"])
	}

	// Should only have session_count for empty collector
	if len(stats) != 1 {
		t.Errorf("Expected 1 stat key, got %d", len(stats))
	}
}

func TestMetricsCollector_GetMetricAggregates(t *testing.T) {
	collector := NewMetricsCollector()

	// Add sessions with accuracy metrics
	result1 := NewSessionResult("session-1", "agent-1")
	result1.AddMetricMeasurement(NewMetricMeasurement("accuracy", 0.9, MetricTypeSuccessRate))
	collector.AddResult(result1)

	result2 := NewSessionResult("session-2", "agent-2")
	result2.AddMetricMeasurement(NewMetricMeasurement("accuracy", 0.8, MetricTypeSuccessRate))
	collector.AddResult(result2)

	result3 := NewSessionResult("session-3", "agent-3")
	result3.AddMetricMeasurement(NewMetricMeasurement("accuracy", 1.0, MetricTypeSuccessRate))
	collector.AddResult(result3)

	aggregates := collector.GetMetricAggregates("accuracy")

	if aggregates["count"] != 3 {
		t.Errorf("Expected count 3, got %v", aggregates["count"])
	}

	if aggregates["min"].(float64) != 0.8 {
		t.Errorf("Expected min 0.8, got %v", aggregates["min"])
	}

	if aggregates["max"].(float64) != 1.0 {
		t.Errorf("Expected max 1.0, got %v", aggregates["max"])
	}

	mean := aggregates["mean"].(float64)
	if mean < 0.89 || mean > 0.91 {
		t.Errorf("Expected mean ~0.9, got %.2f", mean)
	}

	sum := aggregates["sum"].(float64)
	if sum < 2.69 || sum > 2.71 {
		t.Errorf("Expected sum ~2.7, got %.2f", sum)
	}
}

func TestMetricsCollector_GetMetricAggregatesEmpty(t *testing.T) {
	collector := NewMetricsCollector()

	aggregates := collector.GetMetricAggregates("accuracy")

	if aggregates["count"] != 0 {
		t.Errorf("Expected count 0, got %v", aggregates["count"])
	}

	// Should only have count for empty aggregates
	if len(aggregates) != 1 {
		t.Errorf("Expected 1 key, got %d", len(aggregates))
	}
}

func TestMetricsCollector_GetResults(t *testing.T) {
	collector := NewMetricsCollector()

	result1 := NewSessionResult("session-1", "agent-1")
	result2 := NewSessionResult("session-2", "agent-2")

	collector.AddResult(result1)
	collector.AddResult(result2)

	results := collector.GetResults()

	if len(results) != 2 {
		t.Errorf("Expected 2 results, got %d", len(results))
	}
}

func TestMetricsCollector_Clear(t *testing.T) {
	collector := NewMetricsCollector()

	result1 := NewSessionResult("session-1", "agent-1")
	collector.AddResult(result1)

	if len(collector.results) != 1 {
		t.Fatalf("Expected 1 result before clear, got %d", len(collector.results))
	}

	collector.Clear()

	if len(collector.results) != 0 {
		t.Errorf("Expected 0 results after clear, got %d", len(collector.results))
	}
}
