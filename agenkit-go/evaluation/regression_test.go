package evaluation

import (
	"testing"
	"time"
)

// Helper to create test evaluation results
func createTestResult(accuracy, quality, latency float64, contextLength int) *EvaluationResult {
	return &EvaluationResult{
		EvaluationID:     "test-eval",
		AgentName:        "test-agent",
		Timestamp:        time.Now(),
		Accuracy:         &accuracy,
		QualityScore:     &quality,
		AvgLatencyMs:     &latency,
		ContextLength:    &contextLength,
		CompressionRatio: func() *float64 { ratio := 100.0; return &ratio }(),
	}
}

// TestRegressionDetectorCreation tests detector creation
func TestRegressionDetectorCreation(t *testing.T) {
	detector := NewRegressionDetector(nil, nil)

	if detector == nil {
		t.Fatal("Expected detector to be created")
	}

	// Check default thresholds
	if detector.thresholds["accuracy"] != 0.10 {
		t.Errorf("Expected accuracy threshold 0.10, got %.2f", detector.thresholds["accuracy"])
	}
	if detector.thresholds["latency"] != 0.20 {
		t.Errorf("Expected latency threshold 0.20, got %.2f", detector.thresholds["latency"])
	}
}

// TestRegressionDetectorCustomThresholds tests custom thresholds
func TestRegressionDetectorCustomThresholds(t *testing.T) {
	customThresholds := map[string]float64{
		"accuracy": 0.05,
		"latency":  0.15,
	}

	detector := NewRegressionDetector(customThresholds, nil)

	if detector.thresholds["accuracy"] != 0.05 {
		t.Errorf("Expected custom accuracy threshold 0.05, got %.2f", detector.thresholds["accuracy"])
	}
	if detector.thresholds["latency"] != 0.15 {
		t.Errorf("Expected custom latency threshold 0.15, got %.2f", detector.thresholds["latency"])
	}
}

// TestSetBaseline tests baseline setting
func TestSetBaseline(t *testing.T) {
	detector := NewRegressionDetector(nil, nil)
	baseline := createTestResult(0.95, 0.90, 100.0, 5000)

	detector.SetBaseline(baseline)

	if detector.baseline == nil {
		t.Fatal("Expected baseline to be set")
	}
	if *detector.baseline.Accuracy != 0.95 {
		t.Errorf("Expected baseline accuracy 0.95, got %.2f", *detector.baseline.Accuracy)
	}
}

// TestDetectNoBaseline tests detection without baseline
func TestDetectNoBaseline(t *testing.T) {
	detector := NewRegressionDetector(nil, nil)
	current := createTestResult(0.80, 0.85, 150.0, 6000)

	regressions := detector.Detect(current, false)

	if len(regressions) != 0 {
		t.Errorf("Expected no regressions without baseline, got %d", len(regressions))
	}
}

// TestDetectNoRegression tests when performance is maintained
func TestDetectNoRegression(t *testing.T) {
	baseline := createTestResult(0.95, 0.90, 100.0, 5000)
	detector := NewRegressionDetector(nil, baseline)

	// Current is similar to baseline
	current := createTestResult(0.94, 0.89, 105.0, 5100)

	regressions := detector.Detect(current, false)

	if len(regressions) != 0 {
		t.Errorf("Expected no regressions, got %d: %v", len(regressions), regressions)
	}
}

// TestDetectAccuracyRegression tests accuracy regression
func TestDetectAccuracyRegression(t *testing.T) {
	baseline := createTestResult(0.95, 0.90, 100.0, 5000)
	detector := NewRegressionDetector(nil, baseline)

	// Accuracy drops by 20% (0.95 -> 0.76)
	current := createTestResult(0.76, 0.90, 100.0, 5000)

	regressions := detector.Detect(current, false)

	if len(regressions) == 0 {
		t.Fatal("Expected accuracy regression to be detected")
	}

	found := false
	for _, reg := range regressions {
		if reg.MetricName == "accuracy" {
			found = true
			if reg.DegradationPercent < 15 {
				t.Errorf("Expected degradation ~20%%, got %.2f%%", reg.DegradationPercent)
			}
			// Severity should be at least minor for 15%+ degradation
			if reg.Severity == SeverityNone {
				t.Errorf("Expected at least minor severity, got %s", reg.Severity)
			}
		}
	}

	if !found {
		t.Error("Accuracy regression not found in results")
	}
}

// TestDetectQualityRegression tests quality regression
func TestDetectQualityRegression(t *testing.T) {
	baseline := createTestResult(0.95, 0.90, 100.0, 5000)
	detector := NewRegressionDetector(nil, baseline)

	// Quality drops by 15% (0.90 -> 0.765)
	current := createTestResult(0.95, 0.765, 100.0, 5000)

	regressions := detector.Detect(current, false)

	found := false
	for _, reg := range regressions {
		if reg.MetricName == "quality" {
			found = true
			if reg.DegradationPercent < 10 {
				t.Errorf("Expected degradation ~15%%, got %.2f%%", reg.DegradationPercent)
			}
		}
	}

	if !found {
		t.Error("Quality regression not found in results")
	}
}

// TestDetectLatencyRegression tests latency regression
func TestDetectLatencyRegression(t *testing.T) {
	baseline := createTestResult(0.95, 0.90, 100.0, 5000)
	detector := NewRegressionDetector(nil, baseline)

	// Latency increases by 30% (100 -> 130ms)
	current := createTestResult(0.95, 0.90, 130.0, 5000)

	regressions := detector.Detect(current, false)

	found := false
	for _, reg := range regressions {
		if reg.MetricName == "latency" {
			found = true
			if reg.DegradationPercent < 25 {
				t.Errorf("Expected degradation ~30%%, got %.2f%%", reg.DegradationPercent)
			}
		}
	}

	if !found {
		t.Error("Latency regression not found in results")
	}
}

// TestDetectMultipleRegressions tests multiple simultaneous regressions
func TestDetectMultipleRegressions(t *testing.T) {
	baseline := createTestResult(0.95, 0.90, 100.0, 5000)
	detector := NewRegressionDetector(nil, baseline)

	// Both accuracy and latency regress
	current := createTestResult(0.80, 0.90, 150.0, 5000)

	regressions := detector.Detect(current, false)

	if len(regressions) < 2 {
		t.Errorf("Expected at least 2 regressions, got %d", len(regressions))
	}

	metrics := make(map[string]bool)
	for _, reg := range regressions {
		metrics[reg.MetricName] = true
	}

	if !metrics["accuracy"] {
		t.Error("Expected accuracy regression")
	}
	if !metrics["latency"] {
		t.Error("Expected latency regression")
	}
}

// TestSeverityCalculation tests severity levels
func TestSeverityCalculation(t *testing.T) {
	detector := NewRegressionDetector(nil, nil)

	tests := []struct {
		degradation float64
		expected    Severity
	}{
		{0.05, SeverityNone},
		{0.08, SeverityNone},
		{0.12, SeverityMinor},
		{0.15, SeverityMinor},
		{0.25, SeverityModerate},
		{0.45, SeverityModerate},
		{0.60, SeverityCritical},
		{0.90, SeverityCritical},
	}

	for _, test := range tests {
		severity := detector.calculateSeverity(test.degradation)
		if severity != test.expected {
			t.Errorf("calculateSeverity(%.2f) = %s, expected %s",
				test.degradation, severity, test.expected)
		}
	}
}

// TestRegressionToDict tests regression serialization
func TestRegressionToDict(t *testing.T) {
	reg := &Regression{
		MetricName:         "accuracy",
		BaselineValue:      0.95,
		CurrentValue:       0.80,
		DegradationPercent: 15.79,
		Severity:           SeverityMinor,
		Timestamp:          time.Now(),
		Context: map[string]interface{}{
			"threshold_percent": 10.0,
			"higher_is_better":  true,
		},
	}

	dict := reg.ToDict()

	if dict["metric_name"] != "accuracy" {
		t.Errorf("Expected metric_name 'accuracy', got %v", dict["metric_name"])
	}
	if dict["baseline_value"] != 0.95 {
		t.Errorf("Expected baseline_value 0.95, got %v", dict["baseline_value"])
	}
	if dict["current_value"] != 0.80 {
		t.Errorf("Expected current_value 0.80, got %v", dict["current_value"])
	}
	if dict["severity"] != "minor" {
		t.Errorf("Expected severity 'minor', got %v", dict["severity"])
	}
}

// TestIsRegression tests regression detection
func TestIsRegression(t *testing.T) {
	// Actual regression (positive degradation)
	reg1 := &Regression{DegradationPercent: 15.0}
	if !reg1.IsRegression() {
		t.Error("Expected positive degradation to be regression")
	}

	// Improvement (negative degradation)
	reg2 := &Regression{DegradationPercent: -5.0}
	if reg2.IsRegression() {
		t.Error("Expected negative degradation to not be regression")
	}

	// No change
	reg3 := &Regression{DegradationPercent: 0.0}
	if reg3.IsRegression() {
		t.Error("Expected zero degradation to not be regression")
	}
}

// TestStoreHistory tests history storage
func TestStoreHistory(t *testing.T) {
	detector := NewRegressionDetector(nil, nil)

	result1 := createTestResult(0.95, 0.90, 100.0, 5000)
	result2 := createTestResult(0.93, 0.88, 110.0, 5100)

	detector.Detect(result1, true)
	detector.Detect(result2, true)

	if len(detector.history) != 2 {
		t.Errorf("Expected 2 results in history, got %d", len(detector.history))
	}
}

// TestGetTrend tests trend analysis
func TestGetTrend(t *testing.T) {
	detector := NewRegressionDetector(nil, nil)

	// Create degrading trend
	results := []*EvaluationResult{
		createTestResult(0.95, 0.90, 100.0, 5000),
		createTestResult(0.93, 0.88, 110.0, 5100),
		createTestResult(0.91, 0.86, 120.0, 5200),
		createTestResult(0.89, 0.84, 130.0, 5300),
		createTestResult(0.87, 0.82, 140.0, 5400),
	}

	for _, result := range results {
		detector.Detect(result, true)
	}

	trend := detector.GetTrend("accuracy", 5)

	if trend == nil {
		t.Fatal("Expected trend data, got nil")
	}

	if trend["metric"] != "accuracy" {
		t.Errorf("Expected metric 'accuracy', got %v", trend["metric"])
	}

	// Slope should be negative (degrading)
	slope, ok := trend["slope"].(float64)
	if !ok {
		t.Fatal("Expected slope to be float64")
	}
	if slope >= 0 {
		t.Errorf("Expected negative slope for degrading trend, got %.4f", slope)
	}

	if trend["direction"] != "degrading" {
		t.Errorf("Expected direction 'degrading', got %v", trend["direction"])
	}
}

// TestGetTrendImproving tests improving trend
func TestGetTrendImproving(t *testing.T) {
	detector := NewRegressionDetector(nil, nil)

	// Create improving trend
	results := []*EvaluationResult{
		createTestResult(0.80, 0.75, 150.0, 5000),
		createTestResult(0.82, 0.77, 145.0, 4900),
		createTestResult(0.84, 0.79, 140.0, 4800),
		createTestResult(0.86, 0.81, 135.0, 4700),
		createTestResult(0.88, 0.83, 130.0, 4600),
	}

	for _, result := range results {
		detector.Detect(result, true)
	}

	trend := detector.GetTrend("accuracy", 5)

	// Slope should be positive (improving)
	slope, ok := trend["slope"].(float64)
	if !ok {
		t.Fatal("Expected slope to be float64")
	}
	if slope <= 0 {
		t.Errorf("Expected positive slope for improving trend, got %.4f", slope)
	}

	if trend["direction"] != "improving" {
		t.Errorf("Expected direction 'improving', got %v", trend["direction"])
	}
}

// TestCompareResults tests result comparison
func TestCompareResults(t *testing.T) {
	detector := NewRegressionDetector(nil, nil)

	resultA := createTestResult(0.95, 0.90, 100.0, 5000)
	resultB := createTestResult(0.90, 0.85, 120.0, 5500)

	comparisons := detector.CompareResults(resultA, resultB)

	// Check accuracy comparison
	if acc, ok := comparisons["accuracy"]; ok {
		if acc["baseline"] != 0.95 {
			t.Errorf("Expected baseline accuracy 0.95, got %.2f", acc["baseline"])
		}
		if acc["current"] != 0.90 {
			t.Errorf("Expected current accuracy 0.90, got %.2f", acc["current"])
		}
		// Use tolerance for floating point comparison
		changeDiff := acc["change"] - (-0.05)
		if changeDiff < -0.001 || changeDiff > 0.001 {
			t.Errorf("Expected change -0.05, got %.4f", acc["change"])
		}
	} else {
		t.Error("Expected accuracy comparison")
	}

	// Check latency comparison
	if lat, ok := comparisons["latency"]; ok {
		if lat["baseline"] != 100.0 {
			t.Errorf("Expected baseline latency 100, got %.2f", lat["baseline"])
		}
		if lat["current"] != 120.0 {
			t.Errorf("Expected current latency 120, got %.2f", lat["current"])
		}
		if lat["change"] != 20.0 {
			t.Errorf("Expected change 20, got %.2f", lat["change"])
		}
	} else {
		t.Error("Expected latency comparison")
	}
}

// TestClearHistory tests history clearing
func TestClearHistory(t *testing.T) {
	detector := NewRegressionDetector(nil, nil)

	result := createTestResult(0.95, 0.90, 100.0, 5000)
	detector.Detect(result, true)

	if len(detector.history) != 1 {
		t.Fatal("Expected 1 result in history")
	}

	detector.ClearHistory()

	if len(detector.history) != 0 {
		t.Errorf("Expected empty history after clear, got %d items", len(detector.history))
	}
}

// TestGetSummary tests summary generation
func TestGetSummary(t *testing.T) {
	baseline := createTestResult(0.95, 0.90, 100.0, 5000)
	detector := NewRegressionDetector(nil, baseline)

	result := createTestResult(0.93, 0.88, 110.0, 5100)
	detector.Detect(result, true)

	summary := detector.GetSummary()

	if !summary["has_baseline"].(bool) {
		t.Error("Expected has_baseline to be true")
	}

	if summary["baseline_id"] != "test-eval" {
		t.Errorf("Expected baseline_id 'test-eval', got %v", summary["baseline_id"])
	}

	if summary["history_count"] != 1 {
		t.Errorf("Expected history_count 1, got %v", summary["history_count"])
	}

	thresholds, ok := summary["thresholds"].(map[string]float64)
	if !ok {
		t.Fatal("Expected thresholds to be map[string]float64")
	}

	if thresholds["accuracy"] != 0.10 {
		t.Errorf("Expected accuracy threshold 0.10, got %.2f", thresholds["accuracy"])
	}
}

// TestCheckMetricZeroBaseline tests handling of zero baseline
func TestCheckMetricZeroBaseline(t *testing.T) {
	detector := NewRegressionDetector(nil, nil)

	// Zero baseline, non-zero current (higher is better)
	reg := detector.checkMetric("test_metric", 0.0, 0.5, true)
	if reg == nil {
		t.Error("Expected regression for improvement from zero")
	}

	// Zero baseline, zero current
	reg2 := detector.checkMetric("test_metric", 0.0, 0.0, true)
	if reg2 != nil {
		t.Error("Expected no regression when both are zero")
	}
}

// TestContextLengthRegression tests context length regression
func TestContextLengthRegression(t *testing.T) {
	baseline := createTestResult(0.95, 0.90, 100.0, 5000)
	detector := NewRegressionDetector(nil, baseline)

	// Context grows by 40% (5000 -> 7000)
	current := createTestResult(0.95, 0.90, 100.0, 7000)

	regressions := detector.Detect(current, false)

	found := false
	for _, reg := range regressions {
		if reg.MetricName == "context_length" {
			found = true
			if reg.DegradationPercent < 35 {
				t.Errorf("Expected degradation ~40%%, got %.2f%%", reg.DegradationPercent)
			}
		}
	}

	if !found {
		t.Error("Context length regression not found in results")
	}
}

// TestCompressionRatioRegression tests compression ratio regression
func TestCompressionRatioRegression(t *testing.T) {
	baseline := createTestResult(0.95, 0.90, 100.0, 5000)
	detector := NewRegressionDetector(nil, baseline)

	// Compression ratio drops by 20% (100 -> 80)
	current := createTestResult(0.95, 0.90, 100.0, 5000)
	compressionRatio := 80.0
	current.CompressionRatio = &compressionRatio

	regressions := detector.Detect(current, false)

	found := false
	for _, reg := range regressions {
		if reg.MetricName == "compression_ratio" {
			found = true
			if reg.DegradationPercent < 15 {
				t.Errorf("Expected degradation ~20%%, got %.2f%%", reg.DegradationPercent)
			}
		}
	}

	if !found {
		t.Error("Compression ratio regression not found in results")
	}
}

// BenchmarkDetect benchmarks regression detection
func BenchmarkDetect(b *testing.B) {
	baseline := createTestResult(0.95, 0.90, 100.0, 5000)
	detector := NewRegressionDetector(nil, baseline)
	current := createTestResult(0.80, 0.85, 150.0, 6000)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = detector.Detect(current, false)
	}
}

// BenchmarkGetTrend benchmarks trend analysis
func BenchmarkGetTrend(b *testing.B) {
	detector := NewRegressionDetector(nil, nil)

	// Add 100 results to history
	for i := 0; i < 100; i++ {
		accuracy := 0.95 - float64(i)*0.001
		result := createTestResult(accuracy, 0.90, 100.0, 5000)
		detector.Detect(result, true)
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = detector.GetTrend("accuracy", 20)
	}
}

// TestRegressionIntegration tests full regression detection workflow
func TestRegressionIntegration(t *testing.T) {
	// Simulate a series of evaluations where performance degrades over time
	detector := NewRegressionDetector(nil, nil)

	// Set initial baseline
	baseline := createTestResult(0.95, 0.90, 100.0, 5000)
	detector.SetBaseline(baseline)

	// Performance stays stable
	for i := 0; i < 3; i++ {
		current := createTestResult(0.94, 0.89, 105.0, 5100)
		regressions := detector.Detect(current, true)
		if len(regressions) > 0 {
			t.Error("Expected no regressions during stable period")
		}
	}

	// Performance starts to degrade
	degraded := createTestResult(0.85, 0.80, 130.0, 6000)
	regressions := detector.Detect(degraded, true)

	if len(regressions) == 0 {
		t.Fatal("Expected regressions to be detected")
	}

	// Check that multiple metrics regressed
	hasAccuracyRegression := false
	hasQualityRegression := false
	hasLatencyRegression := false

	for _, reg := range regressions {
		switch reg.MetricName {
		case "accuracy":
			hasAccuracyRegression = true
		case "quality":
			hasQualityRegression = true
		case "latency":
			hasLatencyRegression = true
		}
	}

	if !hasAccuracyRegression {
		t.Error("Expected accuracy regression")
	}
	if !hasQualityRegression {
		t.Error("Expected quality regression")
	}
	if !hasLatencyRegression {
		t.Error("Expected latency regression")
	}

	// Check trend
	trend := detector.GetTrend("accuracy", 5)
	if trend["direction"] != "degrading" {
		t.Errorf("Expected degrading trend, got %v", trend["direction"])
	}

	// Check summary
	summary := detector.GetSummary()
	historyCount := summary["history_count"].(int)
	if historyCount != 4 {
		t.Errorf("Expected 4 items in history, got %d", historyCount)
	}
}
