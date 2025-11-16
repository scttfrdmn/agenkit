package evaluation

import (
	"context"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// MockAgent for testing
type MockAgent struct {
	name         string
	capabilities []string
}

func (a *MockAgent) Name() string {
	return a.name
}

func (a *MockAgent) Capabilities() []string {
	return a.capabilities
}

func (a *MockAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	return &agenkit.Message{
		Role:    "agent",
		Content: "Test response",
	}, nil
}

// TestAccuracyMetric tests the AccuracyMetric
func TestAccuracyMetric(t *testing.T) {
	metric := NewAccuracyMetric(nil, false)

	if metric.Name() != "accuracy" {
		t.Errorf("Expected metric name 'accuracy', got '%s'", metric.Name())
	}

	agent := &MockAgent{name: "test-agent"}
	input := &agenkit.Message{Role: "user", Content: "What is the capital of France?"}
	output := &agenkit.Message{Role: "agent", Content: "The capital of France is Paris."}

	// Test with correct answer
	ctx := map[string]interface{}{"expected": "Paris"}
	score, err := metric.Measure(agent, input, output, ctx)
	if err != nil {
		t.Fatalf("Measure failed: %v", err)
	}
	if score != 1.0 {
		t.Errorf("Expected score 1.0 for correct answer, got %.2f", score)
	}

	// Test with incorrect answer
	output2 := &agenkit.Message{Role: "agent", Content: "The capital of France is London."}
	score2, err := metric.Measure(agent, input, output2, ctx)
	if err != nil {
		t.Fatalf("Measure failed: %v", err)
	}
	if score2 != 0.0 {
		t.Errorf("Expected score 0.0 for incorrect answer, got %.2f", score2)
	}

	// Test case insensitive matching
	output3 := &agenkit.Message{Role: "agent", Content: "The answer is paris."}
	score3, err := metric.Measure(agent, input, output3, ctx)
	if err != nil {
		t.Fatalf("Measure failed: %v", err)
	}
	if score3 != 1.0 {
		t.Errorf("Expected score 1.0 for case-insensitive match, got %.2f", score3)
	}
}

// TestAccuracyMetricCaseSensitive tests case-sensitive matching
func TestAccuracyMetricCaseSensitive(t *testing.T) {
	metric := NewAccuracyMetric(nil, true)

	agent := &MockAgent{name: "test-agent"}
	input := &agenkit.Message{Role: "user", Content: "Test"}
	output := &agenkit.Message{Role: "agent", Content: "The answer is paris."}

	ctx := map[string]interface{}{"expected": "Paris"}
	score, err := metric.Measure(agent, input, output, ctx)
	if err != nil {
		t.Fatalf("Measure failed: %v", err)
	}
	if score != 0.0 {
		t.Errorf("Expected score 0.0 for case-sensitive mismatch, got %.2f", score)
	}
}

// TestAccuracyMetricCustomValidator tests custom validator
func TestAccuracyMetricCustomValidator(t *testing.T) {
	validator := func(expected, actual string) bool {
		// Custom logic: check if actual contains any word from expected
		return len(actual) > len(expected)
	}

	metric := NewAccuracyMetric(validator, false)

	agent := &MockAgent{name: "test-agent"}
	input := &agenkit.Message{Role: "user", Content: "Test"}
	output := &agenkit.Message{Role: "agent", Content: "This is a long response"}

	ctx := map[string]interface{}{"expected": "short"}
	score, err := metric.Measure(agent, input, output, ctx)
	if err != nil {
		t.Fatalf("Measure failed: %v", err)
	}
	if score != 1.0 {
		t.Errorf("Expected score 1.0 from custom validator, got %.2f", score)
	}
}

// TestAccuracyMetricAggregate tests aggregation
func TestAccuracyMetricAggregate(t *testing.T) {
	metric := NewAccuracyMetric(nil, false)

	measurements := []float64{1.0, 1.0, 0.0, 1.0, 0.0}
	aggregated := metric.Aggregate(measurements)

	if aggregated["accuracy"] != 0.6 {
		t.Errorf("Expected accuracy 0.6, got %.2f", aggregated["accuracy"])
	}
	if aggregated["total"] != 5.0 {
		t.Errorf("Expected total 5, got %.0f", aggregated["total"])
	}
	if aggregated["correct"] != 3.0 {
		t.Errorf("Expected correct 3, got %.0f", aggregated["correct"])
	}
	if aggregated["incorrect"] != 2.0 {
		t.Errorf("Expected incorrect 2, got %.0f", aggregated["incorrect"])
	}
}

// TestQualityMetrics tests the QualityMetrics
func TestQualityMetrics(t *testing.T) {
	metric := NewQualityMetrics(false, "", nil)

	if metric.Name() != "quality" {
		t.Errorf("Expected metric name 'quality', got '%s'", metric.Name())
	}

	agent := &MockAgent{name: "test-agent"}
	input := &agenkit.Message{
		Role:    "user",
		Content: "What is machine learning?",
	}
	output := &agenkit.Message{
		Role: "agent",
		Content: "Machine learning is a subset of artificial intelligence that enables " +
			"systems to learn and improve from experience without being explicitly programmed. " +
			"It focuses on developing computer programs that can access data and use it to learn for themselves.",
	}

	score, err := metric.Measure(agent, input, output, nil)
	if err != nil {
		t.Fatalf("Measure failed: %v", err)
	}

	// Quality score should be > 0 for reasonable response
	if score <= 0 {
		t.Errorf("Expected positive quality score, got %.2f", score)
	}
	if score > 1.0 {
		t.Errorf("Quality score should be <= 1.0, got %.2f", score)
	}
}

// TestQualityMetricsWithExpected tests quality with expected output
func TestQualityMetricsWithExpected(t *testing.T) {
	metric := NewQualityMetrics(false, "", nil)

	agent := &MockAgent{name: "test-agent"}
	input := &agenkit.Message{Role: "user", Content: "What is the capital?"}
	output := &agenkit.Message{
		Role:    "agent",
		Content: "The capital is Paris, which is known for the Eiffel Tower.",
	}

	ctx := map[string]interface{}{"expected": "Paris"}
	score, err := metric.Measure(agent, input, output, ctx)
	if err != nil {
		t.Fatalf("Measure failed: %v", err)
	}

	// Should have high quality score with correct answer
	if score < 0.5 {
		t.Errorf("Expected quality score >= 0.5 with correct answer, got %.2f", score)
	}
}

// TestQualityMetricsLowQuality tests low quality responses
func TestQualityMetricsLowQuality(t *testing.T) {
	metric := NewQualityMetrics(false, "", nil)

	agent := &MockAgent{name: "test-agent"}
	input := &agenkit.Message{Role: "user", Content: "Explain quantum computing in detail"}
	output := &agenkit.Message{Role: "agent", Content: "Yes."}

	score, err := metric.Measure(agent, input, output, nil)
	if err != nil {
		t.Fatalf("Measure failed: %v", err)
	}

	// Short, incomplete response should have low quality
	if score > 0.5 {
		t.Errorf("Expected low quality score for incomplete response, got %.2f", score)
	}
}

// TestQualityMetricsAggregate tests aggregation
func TestQualityMetricsAggregate(t *testing.T) {
	metric := NewQualityMetrics(false, "", nil)

	measurements := []float64{0.8, 0.7, 0.9, 0.6, 0.8}
	aggregated := metric.Aggregate(measurements)

	expectedMean := 0.76
	if diff := aggregated["mean"] - expectedMean; diff < -0.01 || diff > 0.01 {
		t.Errorf("Expected mean ~%.2f, got %.2f", expectedMean, aggregated["mean"])
	}

	if aggregated["min"] != 0.6 {
		t.Errorf("Expected min 0.6, got %.2f", aggregated["min"])
	}

	if aggregated["max"] != 0.9 {
		t.Errorf("Expected max 0.9, got %.2f", aggregated["max"])
	}

	if aggregated["std"] < 0 {
		t.Errorf("Standard deviation should be positive, got %.2f", aggregated["std"])
	}
}

// TestPrecisionRecallMetric tests the PrecisionRecallMetric
func TestPrecisionRecallMetric(t *testing.T) {
	metric := NewPrecisionRecallMetric()

	if metric.Name() != "precision_recall" {
		t.Errorf("Expected metric name 'precision_recall', got '%s'", metric.Name())
	}

	agent := &MockAgent{name: "test-agent"}
	input := &agenkit.Message{Role: "user", Content: "Classify this"}
	output := &agenkit.Message{Role: "agent", Content: "Positive"}

	// True Positive
	ctx1 := map[string]interface{}{
		"true_label":      true,
		"predicted_label": true,
	}
	score1, err := metric.Measure(agent, input, output, ctx1)
	if err != nil {
		t.Fatalf("Measure failed: %v", err)
	}
	if score1 != 1.0 {
		t.Errorf("Expected score 1.0 for TP, got %.2f", score1)
	}

	// False Positive
	ctx2 := map[string]interface{}{
		"true_label":      false,
		"predicted_label": true,
	}
	score2, err := metric.Measure(agent, input, output, ctx2)
	if err != nil {
		t.Fatalf("Measure failed: %v", err)
	}
	if score2 != 0.0 {
		t.Errorf("Expected score 0.0 for FP, got %.2f", score2)
	}

	// False Negative
	ctx3 := map[string]interface{}{
		"true_label":      true,
		"predicted_label": false,
	}
	score3, err := metric.Measure(agent, input, output, ctx3)
	if err != nil {
		t.Fatalf("Measure failed: %v", err)
	}
	if score3 != 0.0 {
		t.Errorf("Expected score 0.0 for FN, got %.2f", score3)
	}

	// True Negative
	ctx4 := map[string]interface{}{
		"true_label":      false,
		"predicted_label": false,
	}
	score4, err := metric.Measure(agent, input, output, ctx4)
	if err != nil {
		t.Fatalf("Measure failed: %v", err)
	}
	if score4 != 1.0 {
		t.Errorf("Expected score 1.0 for TN, got %.2f", score4)
	}
}

// TestPrecisionRecallMetricAggregate tests aggregation
func TestPrecisionRecallMetricAggregate(t *testing.T) {
	metric := NewPrecisionRecallMetric()

	agent := &MockAgent{name: "test-agent"}
	input := &agenkit.Message{Role: "user", Content: "Test"}
	output := &agenkit.Message{Role: "agent", Content: "Result"}

	// Simulate classification results: 2 TP, 1 FP, 1 FN, 1 TN
	testCases := []map[string]interface{}{
		{"true_label": true, "predicted_label": true},   // TP
		{"true_label": true, "predicted_label": true},   // TP
		{"true_label": false, "predicted_label": true},  // FP
		{"true_label": true, "predicted_label": false},  // FN
		{"true_label": false, "predicted_label": false}, // TN
	}

	measurements := make([]float64, 0)
	for _, ctx := range testCases {
		score, err := metric.Measure(agent, input, output, ctx)
		if err != nil {
			t.Fatalf("Measure failed: %v", err)
		}
		measurements = append(measurements, score)
	}

	aggregated := metric.Aggregate(measurements)

	// Expected: TP=2, FP=1, FN=1, TN=1
	if aggregated["true_positives"] != 2.0 {
		t.Errorf("Expected 2 TP, got %.0f", aggregated["true_positives"])
	}
	if aggregated["false_positives"] != 1.0 {
		t.Errorf("Expected 1 FP, got %.0f", aggregated["false_positives"])
	}
	if aggregated["false_negatives"] != 1.0 {
		t.Errorf("Expected 1 FN, got %.0f", aggregated["false_negatives"])
	}
	if aggregated["true_negatives"] != 1.0 {
		t.Errorf("Expected 1 TN, got %.0f", aggregated["true_negatives"])
	}

	// Precision = TP / (TP + FP) = 2 / 3 = 0.6667
	expectedPrecision := 2.0 / 3.0
	if diff := aggregated["precision"] - expectedPrecision; diff < -0.01 || diff > 0.01 {
		t.Errorf("Expected precision %.4f, got %.4f", expectedPrecision, aggregated["precision"])
	}

	// Recall = TP / (TP + FN) = 2 / 3 = 0.6667
	expectedRecall := 2.0 / 3.0
	if diff := aggregated["recall"] - expectedRecall; diff < -0.01 || diff > 0.01 {
		t.Errorf("Expected recall %.4f, got %.4f", expectedRecall, aggregated["recall"])
	}

	// F1 = 2 * (P * R) / (P + R) = 2 * 0.6667 * 0.6667 / 1.3334 = 0.6667
	if aggregated["f1_score"] < 0.65 || aggregated["f1_score"] > 0.68 {
		t.Errorf("Expected F1 score ~0.67, got %.4f", aggregated["f1_score"])
	}
}

// TestPrecisionRecallMetricReset tests reset functionality
func TestPrecisionRecallMetricReset(t *testing.T) {
	metric := NewPrecisionRecallMetric()

	agent := &MockAgent{name: "test-agent"}
	input := &agenkit.Message{Role: "user", Content: "Test"}
	output := &agenkit.Message{Role: "agent", Content: "Result"}

	// Add some measurements
	ctx := map[string]interface{}{
		"true_label":      true,
		"predicted_label": true,
	}
	_, _ = metric.Measure(agent, input, output, ctx)

	// Reset
	metric.Reset()

	// Check aggregation after reset
	aggregated := metric.Aggregate([]float64{})
	if aggregated["true_positives"] != 0.0 {
		t.Errorf("Expected 0 TP after reset, got %.0f", aggregated["true_positives"])
	}
}

// TestToBool tests the toBool helper function
func TestToBool(t *testing.T) {
	tests := []struct {
		input    interface{}
		expected bool
	}{
		{true, true},
		{false, false},
		{1, true},
		{0, false},
		{42, true},
		{1.0, true},
		{0.0, false},
		{"true", true},
		{"True", true},
		{"1", true},
		{"false", false},
		{"anything", false},
		{nil, false},
	}

	for _, test := range tests {
		result := toBool(test.input)
		if result != test.expected {
			t.Errorf("toBool(%v) = %v, expected %v", test.input, result, test.expected)
		}
	}
}
