package evaluation

import (
	"time"
)

// Severity represents regression severity levels.
type Severity string

const (
	SeverityNone     Severity = "none"
	SeverityMinor    Severity = "minor"    // <10% degradation
	SeverityModerate Severity = "moderate" // 10-20% degradation
	SeverityMajor    Severity = "major"    // 20-50% degradation
	SeverityCritical Severity = "critical" // >50% degradation
)

// Regression represents a detected regression in agent performance.
//
// Contains information about what degraded and by how much.
type Regression struct {
	MetricName         string
	BaselineValue      float64
	CurrentValue       float64
	DegradationPercent float64
	Severity           Severity
	Timestamp          time.Time
	Context            map[string]interface{}
}

// IsRegression checks if this is a real regression (not improvement).
func (r *Regression) IsRegression() bool {
	return r.DegradationPercent > 0
}

// ToDict converts regression to dictionary.
func (r *Regression) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"metric_name":         r.MetricName,
		"baseline_value":      r.BaselineValue,
		"current_value":       r.CurrentValue,
		"degradation_percent": r.DegradationPercent,
		"severity":            string(r.Severity),
		"timestamp":           r.Timestamp.Format(time.RFC3339),
		"context":             r.Context,
	}
}

// RegressionDetector detects performance regressions by comparing results.
//
// Monitors agent quality over time and alerts when performance
// degrades beyond acceptable thresholds.
//
// Example:
//
//	detector := NewRegressionDetector(nil, nil)
//	detector.SetBaseline(baselineResult)
//
//	// Later, after changes
//	regressions := detector.Detect(currentResult, true)
//	if len(regressions) > 0 {
//	    fmt.Printf("Found %d regressions!\n", len(regressions))
//	    for _, r := range regressions {
//	        fmt.Printf("  %s: %.1f%% worse\n", r.MetricName, r.DegradationPercent)
//	    }
//	}
type RegressionDetector struct {
	thresholds map[string]float64
	baseline   *EvaluationResult
	history    []*EvaluationResult
}

// NewRegressionDetector creates a new regression detector.
//
// Args:
//
//	thresholds: Acceptable degradation per metric (default 10%)
//	baseline: Baseline evaluation result to compare against
//
// Example:
//
//	detector := NewRegressionDetector(nil, baselineResult)
func NewRegressionDetector(thresholds map[string]float64, baseline *EvaluationResult) *RegressionDetector {
	if thresholds == nil {
		thresholds = map[string]float64{
			"accuracy":       0.10, // 10% degradation threshold
			"quality":        0.10,
			"latency":        0.20, // 20% slower acceptable
			"context_length": 0.30, // 30% larger context acceptable
		}
	}

	return &RegressionDetector{
		thresholds: thresholds,
		baseline:   baseline,
		history:    make([]*EvaluationResult, 0),
	}
}

// SetBaseline sets baseline for comparison.
//
// Args:
//
//	result: Evaluation result to use as baseline
func (d *RegressionDetector) SetBaseline(result *EvaluationResult) {
	d.baseline = result
}

// Detect detects regressions in evaluation result.
//
// Compares current result to baseline and identifies metrics
// that have degraded beyond acceptable thresholds.
//
// Args:
//
//	result: Current evaluation result
//	storeHistory: Whether to store result in history
//
// Returns:
//
//	List of detected regressions (empty if no regressions)
func (d *RegressionDetector) Detect(result *EvaluationResult, storeHistory bool) []*Regression {
	if storeHistory {
		d.history = append(d.history, result)
	}

	if d.baseline == nil {
		// No baseline = no regressions
		return []*Regression{}
	}

	regressions := make([]*Regression, 0)

	// Check accuracy
	if result.Accuracy != nil && d.baseline.Accuracy != nil {
		if reg := d.checkMetric("accuracy", *d.baseline.Accuracy, *result.Accuracy, true); reg != nil {
			regressions = append(regressions, reg)
		}
	}

	// Check quality_score
	if result.QualityScore != nil && d.baseline.QualityScore != nil {
		if reg := d.checkMetric("quality", *d.baseline.QualityScore, *result.QualityScore, true); reg != nil {
			regressions = append(regressions, reg)
		}
	}

	// Check latency (lower is better)
	if result.AvgLatencyMs != nil && d.baseline.AvgLatencyMs != nil {
		if reg := d.checkMetric("latency", *d.baseline.AvgLatencyMs, *result.AvgLatencyMs, false); reg != nil {
			regressions = append(regressions, reg)
		}
	}

	// Check context length
	if result.ContextLength != nil && d.baseline.ContextLength != nil {
		if reg := d.checkMetric("context_length", float64(*d.baseline.ContextLength), float64(*result.ContextLength), false); reg != nil {
			regressions = append(regressions, reg)
		}
	}

	// Check compression ratio (higher is better)
	if result.CompressionRatio != nil && d.baseline.CompressionRatio != nil {
		if reg := d.checkMetric("compression_ratio", *d.baseline.CompressionRatio, *result.CompressionRatio, true); reg != nil {
			regressions = append(regressions, reg)
		}
	}

	return regressions
}

// checkMetric checks single metric for regression.
//
// Args:
//
//	name: Metric name
//	baseline: Baseline value
//	current: Current value
//	higherIsBetter: Whether higher values are better
//
// Returns:
//
//	Regression if detected, nil otherwise
func (d *RegressionDetector) checkMetric(name string, baseline, current float64, higherIsBetter bool) *Regression {
	var degradation float64

	if baseline == 0 {
		// Avoid division by zero
		if current == 0 {
			return nil
		}
		if higherIsBetter {
			degradation = 1.0
		} else {
			degradation = -1.0
		}
	} else {
		if higherIsBetter {
			// For accuracy, quality: lower is worse
			degradation = (baseline - current) / baseline
		} else {
			// For latency, context_length: higher is worse
			degradation = (current - baseline) / baseline
		}
	}

	// Check if exceeds threshold
	threshold, ok := d.thresholds[name]
	if !ok {
		threshold = 0.10
	}

	if degradation > threshold {
		severity := d.calculateSeverity(degradation)
		return &Regression{
			MetricName:         name,
			BaselineValue:      baseline,
			CurrentValue:       current,
			DegradationPercent: degradation * 100,
			Severity:           severity,
			Timestamp:          time.Now().UTC(),
			Context: map[string]interface{}{
				"threshold_percent": threshold * 100,
				"higher_is_better":  higherIsBetter,
			},
		}
	}

	return nil
}

// calculateSeverity calculates severity based on degradation amount.
//
// Args:
//
//	degradation: Degradation as fraction (0.1 = 10%)
//
// Returns:
//
//	Severity level
func (d *RegressionDetector) calculateSeverity(degradation float64) Severity {
	if degradation < 0.10 {
		return SeverityNone
	} else if degradation < 0.20 {
		return SeverityMinor
	} else if degradation < 0.50 {
		return SeverityModerate
	} else {
		return SeverityCritical
	}
}

// GetTrend gets trend for metric over recent history.
//
// Args:
//
//	metricName: Metric to analyze
//	window: Number of recent results to analyze
//
// Returns:
//
//	Trend statistics (slope, direction, variance)
func (d *RegressionDetector) GetTrend(metricName string, window int) map[string]interface{} {
	if len(d.history) < 2 {
		return nil
	}

	// Get recent results
	start := len(d.history) - window
	if start < 0 {
		start = 0
	}
	recent := d.history[start:]

	// Extract metric values
	values := make([]float64, 0)
	for _, result := range recent {
		switch metricName {
		case "accuracy":
			if result.Accuracy != nil {
				values = append(values, *result.Accuracy)
			}
		case "quality":
			if result.QualityScore != nil {
				values = append(values, *result.QualityScore)
			}
		case "latency":
			if result.AvgLatencyMs != nil {
				values = append(values, *result.AvgLatencyMs)
			}
		case "context_length":
			if result.ContextLength != nil {
				values = append(values, float64(*result.ContextLength))
			}
		}
	}

	if len(values) < 2 {
		return nil
	}

	// Calculate trend
	n := float64(len(values))
	x := make([]float64, len(values))
	for i := range x {
		x[i] = float64(i)
	}

	xMean := sum(x) / n
	yMean := sum(values) / n

	// Linear regression slope
	numerator := 0.0
	denominator := 0.0
	for i := range values {
		numerator += (x[i] - xMean) * (values[i] - yMean)
		denominator += (x[i] - xMean) * (x[i] - xMean)
	}

	slope := 0.0
	if denominator != 0 {
		slope = numerator / denominator
	}

	// Variance
	variance := 0.0
	for _, v := range values {
		variance += (v - yMean) * (v - yMean)
	}
	variance /= n

	direction := "stable"
	if slope > 0 {
		direction = "improving"
	} else if slope < 0 {
		direction = "degrading"
	}

	return map[string]interface{}{
		"metric":      metricName,
		"slope":       slope,
		"direction":   direction,
		"variance":    variance,
		"current":     values[len(values)-1],
		"mean":        yMean,
		"window_size": len(values),
	}
}

// CompareResults compares two evaluation results.
//
// Args:
//
//	resultA: First result (baseline)
//	resultB: Second result (comparison)
//
// Returns:
//
//	Dictionary of metric comparisons
func (d *RegressionDetector) CompareResults(resultA, resultB *EvaluationResult) map[string]map[string]float64 {
	comparisons := make(map[string]map[string]float64)

	// Compare accuracy
	if resultA.Accuracy != nil && resultB.Accuracy != nil {
		change := *resultB.Accuracy - *resultA.Accuracy
		changePercent := 0.0
		if *resultA.Accuracy != 0 {
			changePercent = change / *resultA.Accuracy * 100
		}
		comparisons["accuracy"] = map[string]float64{
			"baseline":       *resultA.Accuracy,
			"current":        *resultB.Accuracy,
			"change":         change,
			"change_percent": changePercent,
		}
	}

	// Compare quality
	if resultA.QualityScore != nil && resultB.QualityScore != nil {
		change := *resultB.QualityScore - *resultA.QualityScore
		changePercent := 0.0
		if *resultA.QualityScore != 0 {
			changePercent = change / *resultA.QualityScore * 100
		}
		comparisons["quality"] = map[string]float64{
			"baseline":       *resultA.QualityScore,
			"current":        *resultB.QualityScore,
			"change":         change,
			"change_percent": changePercent,
		}
	}

	// Compare latency
	if resultA.AvgLatencyMs != nil && resultB.AvgLatencyMs != nil {
		change := *resultB.AvgLatencyMs - *resultA.AvgLatencyMs
		changePercent := 0.0
		if *resultA.AvgLatencyMs != 0 {
			changePercent = change / *resultA.AvgLatencyMs * 100
		}
		comparisons["latency"] = map[string]float64{
			"baseline":       *resultA.AvgLatencyMs,
			"current":        *resultB.AvgLatencyMs,
			"change":         change,
			"change_percent": changePercent,
		}
	}

	return comparisons
}

// ClearHistory clears evaluation history.
func (d *RegressionDetector) ClearHistory() {
	d.history = make([]*EvaluationResult, 0)
}

// GetSummary gets summary of detector state.
//
// Returns:
//
//	Summary with baseline info and history count
func (d *RegressionDetector) GetSummary() map[string]interface{} {
	hasBaseline := d.baseline != nil
	var baselineID string
	if hasBaseline {
		baselineID = d.baseline.EvaluationID
	}

	return map[string]interface{}{
		"has_baseline":  hasBaseline,
		"baseline_id":   baselineID,
		"history_count": len(d.history),
		"thresholds":    d.thresholds,
	}
}
