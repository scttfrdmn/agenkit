// Package evaluation provides detailed metrics tracking for agent evaluation.
//
// This module extends core evaluation with enhanced metric tracking including:
// - Session status tracking (running, completed, failed, etc.)
// - Error collection and analysis
// - Metric type categorization
// - Cross-session aggregation
//
// Key use case: "How do you know a long-running agent succeeded?"
//
// Example:
//
//	result := evaluation.NewSessionResult("session-123", "my-agent")
//	result.AddMetricMeasurement(evaluation.NewMetricMeasurement(
//	    "accuracy",
//	    0.95,
//	    evaluation.MetricTypeSuccessRate,
//	))
//	result.SetStatus(evaluation.SessionStatusCompleted)
package evaluation

import (
	"encoding/json"
	"fmt"
	"sync"
	"time"
)

// SessionStatus represents the status of an evaluation session.
type SessionStatus string

const (
	// SessionStatusRunning indicates session is currently running
	SessionStatusRunning SessionStatus = "running"
	// SessionStatusCompleted indicates session completed successfully
	SessionStatusCompleted SessionStatus = "completed"
	// SessionStatusFailed indicates session failed
	SessionStatusFailed SessionStatus = "failed"
	// SessionStatusTimeout indicates session timed out
	SessionStatusTimeout SessionStatus = "timeout"
	// SessionStatusCancelled indicates session was cancelled
	SessionStatusCancelled SessionStatus = "cancelled"
)

// MetricType categorizes different types of metrics.
type MetricType string

const (
	// MetricTypeSuccessRate measures success/failure rates
	MetricTypeSuccessRate MetricType = "success_rate"
	// MetricTypeQualityScore measures output quality
	MetricTypeQualityScore MetricType = "quality_score"
	// MetricTypeCost measures token/API costs
	MetricTypeCost MetricType = "cost"
	// MetricTypeDuration measures time taken
	MetricTypeDuration MetricType = "duration"
	// MetricTypeErrorRate measures error frequency
	MetricTypeErrorRate MetricType = "error_rate"
	// MetricTypeTaskCompletion measures task completion
	MetricTypeTaskCompletion MetricType = "task_completion"
	// MetricTypeCustom for custom metrics
	MetricTypeCustom MetricType = "custom"
)

// MetricMeasurement represents a single metric measurement.
//
// Note: This is distinct from the Metric interface in core.go.
// Metric interface defines how to measure, MetricMeasurement stores the measurement.
type MetricMeasurement struct {
	// Name of the metric
	Name string `json:"name"`
	// Value of the measurement
	Value float64 `json:"value"`
	// Type categorizes the metric
	Type MetricType `json:"type"`
	// Timestamp when measurement was taken (RFC3339 format)
	Timestamp string `json:"timestamp"`
	// Metadata for additional context
	Metadata map[string]interface{} `json:"metadata,omitempty"`
}

// NewMetricMeasurement creates a new metric measurement with current timestamp.
func NewMetricMeasurement(name string, value float64, metricType MetricType) *MetricMeasurement {
	return &MetricMeasurement{
		Name:      name,
		Value:     value,
		Type:      metricType,
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Metadata:  make(map[string]interface{}),
	}
}

// ErrorRecord represents an error that occurred during evaluation.
type ErrorRecord struct {
	// Type of error
	Type string `json:"type"`
	// Error message
	Message string `json:"message"`
	// Additional details
	Details map[string]interface{} `json:"details,omitempty"`
	// Timestamp when error occurred (RFC3339 format)
	Timestamp string `json:"timestamp"`
}

// NewErrorRecord creates a new error record with current timestamp.
func NewErrorRecord(errorType string, message string, details map[string]interface{}) *ErrorRecord {
	if details == nil {
		details = make(map[string]interface{})
	}
	return &ErrorRecord{
		Type:      errorType,
		Message:   message,
		Details:   details,
		Timestamp: time.Now().UTC().Format(time.RFC3339),
	}
}

// SessionResult contains results from evaluating an agent session with enhanced tracking.
//
// This extends the core EvaluationResult with session status, error tracking,
// and richer metadata for long-running agent evaluations.
type SessionResult struct {
	// SessionID uniquely identifies this session
	SessionID string `json:"session_id"`
	// AgentName identifies the agent being evaluated
	AgentName string `json:"agent_name"`
	// Status of the session
	Status SessionStatus `json:"status"`
	// StartTime when session started (RFC3339 format)
	StartTime string `json:"start_time"`
	// EndTime when session ended (RFC3339 format, nil if still running)
	EndTime *string `json:"end_time,omitempty"`
	// Measurements collected during session
	Measurements []MetricMeasurement `json:"measurements"`
	// Errors that occurred during session
	Errors []ErrorRecord `json:"errors"`
	// Metadata for additional context
	Metadata map[string]interface{} `json:"metadata,omitempty"`
}

// NewSessionResult creates a new session result.
func NewSessionResult(sessionID string, agentName string) *SessionResult {
	return &SessionResult{
		SessionID:    sessionID,
		AgentName:    agentName,
		Status:       SessionStatusRunning,
		StartTime:    time.Now().UTC().Format(time.RFC3339),
		Measurements: make([]MetricMeasurement, 0),
		Errors:       make([]ErrorRecord, 0),
		Metadata:     make(map[string]interface{}),
	}
}

// AddMetricMeasurement adds a metric measurement to this session.
func (sr *SessionResult) AddMetricMeasurement(measurement *MetricMeasurement) {
	sr.Measurements = append(sr.Measurements, *measurement)
}

// AddError records an error that occurred during the session.
func (sr *SessionResult) AddError(errorType string, message string, details map[string]interface{}) {
	sr.Errors = append(sr.Errors, *NewErrorRecord(errorType, message, details))
}

// SetStatus updates the session status.
func (sr *SessionResult) SetStatus(status SessionStatus) {
	sr.Status = status
	if status != SessionStatusRunning && sr.EndTime == nil {
		endTime := time.Now().UTC().Format(time.RFC3339)
		sr.EndTime = &endTime
	}
}

// GetMetric retrieves a specific metric measurement by name (returns first match).
func (sr *SessionResult) GetMetric(name string) *MetricMeasurement {
	for i := range sr.Measurements {
		if sr.Measurements[i].Name == name {
			return &sr.Measurements[i]
		}
	}
	return nil
}

// GetMetricsByType retrieves all measurements of a specific type.
func (sr *SessionResult) GetMetricsByType(metricType MetricType) []MetricMeasurement {
	result := make([]MetricMeasurement, 0)
	for _, m := range sr.Measurements {
		if m.Type == metricType {
			result = append(result, m)
		}
	}
	return result
}

// DurationSeconds calculates session duration in seconds.
//
// Returns nil if session hasn't ended yet.
func (sr *SessionResult) DurationSeconds() *float64 {
	if sr.EndTime == nil {
		return nil
	}

	start, err := time.Parse(time.RFC3339, sr.StartTime)
	if err != nil {
		return nil
	}

	end, err := time.Parse(time.RFC3339, *sr.EndTime)
	if err != nil {
		return nil
	}

	duration := end.Sub(start).Seconds()
	return &duration
}

// ToJSON serializes the session result to JSON.
func (sr *SessionResult) ToJSON() (string, error) {
	bytes, err := json.MarshalIndent(sr, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to marshal to JSON: %w", err)
	}
	return string(bytes), nil
}

// FromJSON deserializes a session result from JSON.
func FromJSON(jsonStr string) (*SessionResult, error) {
	var result SessionResult
	err := json.Unmarshal([]byte(jsonStr), &result)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal from JSON: %w", err)
	}
	return &result, nil
}

// MetricsCollector aggregates metrics across multiple evaluation sessions.
//
// Useful for analyzing agent performance over time and across different scenarios.
// Thread-safe for concurrent access.
//
// Example:
//
//	collector := evaluation.NewMetricsCollector()
//	collector.AddResult(result1)
//	collector.AddResult(result2)
//	stats := collector.GetStatistics()
//	fmt.Printf("Success rate: %.2f%%\n", stats["success_rate"]*100)
type MetricsCollector struct {
	mu      sync.RWMutex
	results []SessionResult
}

// NewMetricsCollector creates a new metrics collector.
func NewMetricsCollector() *MetricsCollector {
	return &MetricsCollector{
		results: make([]SessionResult, 0),
	}
}

// AddResult adds a session result to the collector.
// Thread-safe for concurrent access.
func (mc *MetricsCollector) AddResult(result *SessionResult) {
	mc.mu.Lock()
	defer mc.mu.Unlock()
	mc.results = append(mc.results, *result)
}

// GetStatistics computes aggregated statistics across all collected results.
// Thread-safe for concurrent access.
//
// Returns a map with statistics including:
//   - session_count: Total number of sessions
//   - completed_count: Number of completed sessions
//   - failed_count: Number of failed sessions
//   - success_rate: Ratio of completed to total sessions
//   - avg_duration: Average session duration in seconds
//   - total_errors: Total number of errors across all sessions
//   - avg_errors_per_session: Average errors per session
func (mc *MetricsCollector) GetStatistics() map[string]interface{} {
	mc.mu.RLock()
	defer mc.mu.RUnlock()

	stats := make(map[string]interface{})

	totalSessions := len(mc.results)
	stats["session_count"] = totalSessions

	if totalSessions == 0 {
		return stats
	}

	completedCount := 0
	failedCount := 0
	totalDuration := 0.0
	durationCount := 0
	totalErrors := 0

	for _, result := range mc.results {
		switch result.Status {
		case SessionStatusCompleted:
			completedCount++
		case SessionStatusFailed, SessionStatusTimeout, SessionStatusCancelled:
			failedCount++
		}

		if duration := result.DurationSeconds(); duration != nil {
			totalDuration += *duration
			durationCount++
		}

		totalErrors += len(result.Errors)
	}

	stats["completed_count"] = completedCount
	stats["failed_count"] = failedCount
	stats["success_rate"] = float64(completedCount) / float64(totalSessions)

	if durationCount > 0 {
		stats["avg_duration"] = totalDuration / float64(durationCount)
	}

	stats["total_errors"] = totalErrors
	stats["avg_errors_per_session"] = float64(totalErrors) / float64(totalSessions)

	return stats
}

// GetMetricAggregates computes aggregated statistics for a specific metric across all sessions.
// Thread-safe for concurrent access.
//
// Args:
//
//	metricName: Name of the metric to aggregate
//
// Returns:
//
//	Map with statistics: count, sum, mean, min, max
func (mc *MetricsCollector) GetMetricAggregates(metricName string) map[string]interface{} {
	mc.mu.RLock()
	defer mc.mu.RUnlock()

	values := make([]float64, 0)

	for _, result := range mc.results {
		for _, measurement := range result.Measurements {
			if measurement.Name == metricName {
				values = append(values, measurement.Value)
			}
		}
	}

	if len(values) == 0 {
		return map[string]interface{}{
			"count": 0,
		}
	}

	sum := 0.0
	min := values[0]
	max := values[0]

	for _, v := range values {
		sum += v
		if v < min {
			min = v
		}
		if v > max {
			max = v
		}
	}

	return map[string]interface{}{
		"count": len(values),
		"sum":   sum,
		"mean":  sum / float64(len(values)),
		"min":   min,
		"max":   max,
	}
}

// GetResults returns all collected session results.
// Thread-safe for concurrent access.
func (mc *MetricsCollector) GetResults() []SessionResult {
	mc.mu.RLock()
	defer mc.mu.RUnlock()
	// Return a copy to prevent external mutation
	results := make([]SessionResult, len(mc.results))
	copy(results, mc.results)
	return results
}

// Clear removes all collected results.
// Thread-safe for concurrent access.
func (mc *MetricsCollector) Clear() {
	mc.mu.Lock()
	defer mc.mu.Unlock()
	mc.results = make([]SessionResult, 0)
}

// CreateQualityMetric creates a quality score metric measurement.
//
// Helper to create a quality score metric with normalized score (0.0-1.0).
//
// Args:
//
//	name: Metric name
//	score: Raw score
//	maxScore: Maximum possible score (default: 10.0)
//	metadata: Additional metadata
//
// Returns:
//
//	Metric measurement with normalized score
//
// Example:
//
//	metric := evaluation.CreateQualityMetric("response_quality", 8.5, 10.0, nil)
func CreateQualityMetric(name string, score, maxScore float64, metadata map[string]interface{}) *MetricMeasurement {
	normalizedScore := score / maxScore
	if normalizedScore > 1.0 {
		normalizedScore = 1.0
	}

	if metadata == nil {
		metadata = make(map[string]interface{})
	}
	metadata["raw_score"] = score
	metadata["max_score"] = maxScore

	m := NewMetricMeasurement(name, normalizedScore, MetricTypeQualityScore)
	m.Metadata = metadata
	return m
}

// CreateCostMetric creates a cost metric measurement.
//
// Helper to create a cost metric with currency information.
//
// Args:
//
//	cost: Cost amount
//	currency: Currency code (default: "USD")
//	metadata: Additional metadata
//
// Returns:
//
//	Cost metric measurement
//
// Example:
//
//	metric := evaluation.CreateCostMetric(0.0042, "USD", nil)
func CreateCostMetric(cost float64, currency string, metadata map[string]interface{}) *MetricMeasurement {
	if currency == "" {
		currency = "USD"
	}

	if metadata == nil {
		metadata = make(map[string]interface{})
	}
	metadata["currency"] = currency

	m := NewMetricMeasurement("total_cost", cost, MetricTypeCost)
	m.Metadata = metadata
	return m
}

// CreateDurationMetric creates a duration metric measurement.
//
// Helper to create a duration metric with hours conversion.
//
// Args:
//
//	durationSeconds: Duration in seconds
//	metadata: Additional metadata
//
// Returns:
//
//	Duration metric measurement
//
// Example:
//
//	metric := evaluation.CreateDurationMetric(125.5, nil)
func CreateDurationMetric(durationSeconds float64, metadata map[string]interface{}) *MetricMeasurement {
	if metadata == nil {
		metadata = make(map[string]interface{})
	}
	metadata["duration_hours"] = durationSeconds / 3600

	m := NewMetricMeasurement("duration", durationSeconds, MetricTypeDuration)
	m.Metadata = metadata
	return m
}
