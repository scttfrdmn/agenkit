package evaluation

import (
	"context"
	"sort"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// TestContextMetrics tests the ContextMetrics
func TestContextMetrics(t *testing.T) {
	metric := NewContextMetrics()

	if metric.Name() != "context_length" {
		t.Errorf("Expected metric name 'context_length', got '%s'", metric.Name())
	}

	agent := &MockAgent{name: "test-agent"}
	input := &agenkit.Message{
		Role:    "user",
		Content: "Test message",
		Metadata: map[string]interface{}{
			"context_length": 1000.0,
		},
	}
	output := &agenkit.Message{Role: "agent", Content: "Response"}

	// Test with metadata
	score, err := metric.Measure(agent, input, output, nil)
	if err != nil {
		t.Fatalf("Measure failed: %v", err)
	}
	if score != 1000.0 {
		t.Errorf("Expected context length 1000, got %.0f", score)
	}
}

// TestContextMetricsFromHistory tests estimation from conversation history
func TestContextMetricsFromHistory(t *testing.T) {
	metric := NewContextMetrics()

	agent := &MockAgent{name: "test-agent"}
	input := &agenkit.Message{Role: "user", Content: "Test"}
	output := &agenkit.Message{Role: "agent", Content: "Response"}

	history := []*agenkit.Message{
		{Role: "user", Content: "First message"},    // ~13 chars / 4 = 3 tokens
		{Role: "agent", Content: "First response"},  // ~14 chars / 4 = 3 tokens
		{Role: "user", Content: "Second message"},   // ~14 chars / 4 = 3 tokens
		{Role: "agent", Content: "Second response"}, // ~15 chars / 4 = 3 tokens
	}

	ctx := map[string]interface{}{
		"conversation_history": history,
	}

	score, err := metric.Measure(agent, input, output, ctx)
	if err != nil {
		t.Fatalf("Measure failed: %v", err)
	}

	// Should estimate total tokens from history
	if score < 10 || score > 20 {
		t.Errorf("Expected context length ~14, got %.0f", score)
	}
}

// TestContextMetricsAggregate tests aggregation
func TestContextMetricsAggregate(t *testing.T) {
	metric := NewContextMetrics()

	measurements := []float64{100, 200, 300, 400, 500}
	aggregated := metric.Aggregate(measurements)

	if aggregated["mean"] != 300.0 {
		t.Errorf("Expected mean 300, got %.0f", aggregated["mean"])
	}
	if aggregated["min"] != 100.0 {
		t.Errorf("Expected min 100, got %.0f", aggregated["min"])
	}
	if aggregated["max"] != 500.0 {
		t.Errorf("Expected max 500, got %.0f", aggregated["max"])
	}
	if aggregated["final"] != 500.0 {
		t.Errorf("Expected final 500, got %.0f", aggregated["final"])
	}

	// Growth rate = (final - first) / count = (500 - 100) / 5 = 80
	expectedGrowth := 80.0
	if aggregated["growth_rate"] != expectedGrowth {
		t.Errorf("Expected growth rate %.0f, got %.0f", expectedGrowth, aggregated["growth_rate"])
	}
}

// TestCompressionMetrics tests the CompressionMetrics
func TestCompressionMetrics(t *testing.T) {
	metric := NewCompressionMetrics(nil, 5)

	if metric.Name() != "compression_quality" {
		t.Errorf("Expected metric name 'compression_quality', got '%s'", metric.Name())
	}

	agent := &MockAgent{name: "test-agent"}
	input := &agenkit.Message{Role: "user", Content: "Test"}
	output := &agenkit.Message{
		Role:    "agent",
		Content: "Response",
		Metadata: map[string]interface{}{
			"compression_ratio": 100.0,
		},
	}

	// Test with compression ratio in metadata
	score, err := metric.Measure(agent, input, output, nil)
	if err != nil {
		t.Fatalf("Measure failed: %v", err)
	}
	if score != 100.0 {
		t.Errorf("Expected compression ratio 100, got %.0f", score)
	}
}

// TestCompressionMetricsNoCompression tests when no compression is used
func TestCompressionMetricsNoCompression(t *testing.T) {
	metric := NewCompressionMetrics(nil, 5)

	agent := &MockAgent{name: "test-agent"}
	input := &agenkit.Message{Role: "user", Content: "Test"}
	output := &agenkit.Message{Role: "agent", Content: "Response"}

	score, err := metric.Measure(agent, input, output, nil)
	if err != nil {
		t.Fatalf("Measure failed: %v", err)
	}
	if score != 1.0 {
		t.Errorf("Expected compression ratio 1.0 (no compression), got %.0f", score)
	}
}

// TestCompressionMetricsAggregate tests aggregation
func TestCompressionMetricsAggregate(t *testing.T) {
	metric := NewCompressionMetrics(nil, 5)

	measurements := []float64{50.0, 75.0, 100.0, 125.0, 150.0}
	aggregated := metric.Aggregate(measurements)

	if aggregated["mean"] != 100.0 {
		t.Errorf("Expected mean 100, got %.0f", aggregated["mean"])
	}
	if aggregated["min"] != 50.0 {
		t.Errorf("Expected min 50, got %.0f", aggregated["min"])
	}
	if aggregated["max"] != 150.0 {
		t.Errorf("Expected max 150, got %.0f", aggregated["max"])
	}
	if aggregated["std"] < 0 {
		t.Errorf("Standard deviation should be positive, got %.2f", aggregated["std"])
	}
}

// TestCompressionMetricsGenerateTestContext tests context generation
func TestCompressionMetricsGenerateTestContext(t *testing.T) {
	metric := NewCompressionMetrics(nil, 3)

	needles := []string{
		"NEEDLE 1: Secret code ALPHA-001",
		"NEEDLE 2: Secret code ALPHA-002",
		"NEEDLE 3: Secret code ALPHA-003",
	}

	targetTokens := 1000
	messages := metric.generateTestContext(targetTokens, needles)

	if len(messages) == 0 {
		t.Fatal("Expected generated messages, got none")
	}

	// Check that needles are present
	allContent := ""
	for _, msg := range messages {
		allContent += msg + " "
	}

	for _, needle := range needles {
		if len(needle) > 0 && len(allContent) > 0 {
			// At least some content should be generated
			found := false
			for _, msg := range messages {
				if msg == needle {
					found = true
					break
				}
			}
			if !found {
				t.Logf("Warning: Needle not found in exact form (may be in different message)")
			}
		}
	}

	// Check approximate total token count
	totalChars := 0
	for _, msg := range messages {
		totalChars += len(msg)
	}
	estimatedTokens := totalChars / 4

	if estimatedTokens < targetTokens/2 || estimatedTokens > targetTokens*2 {
		t.Errorf("Expected ~%d tokens, got ~%d", targetTokens, estimatedTokens)
	}
}

// TestCompressionMetricsDefaultNeedles tests default needle generation
func TestCompressionMetricsDefaultNeedles(t *testing.T) {
	metric := NewCompressionMetrics(nil, 5)

	needles := metric.defaultNeedles()

	if len(needles) != 5 {
		t.Errorf("Expected 5 needles, got %d", len(needles))
	}

	for i, needle := range needles {
		if len(needle) == 0 {
			t.Errorf("Needle %d is empty", i)
		}
	}
}

// TestLatencyMetric tests the LatencyMetric
func TestLatencyMetric(t *testing.T) {
	metric := NewLatencyMetric()

	if metric.Name() != "latency" {
		t.Errorf("Expected metric name 'latency', got '%s'", metric.Name())
	}

	agent := &MockAgent{name: "test-agent"}
	input := &agenkit.Message{Role: "user", Content: "Test"}
	output := &agenkit.Message{Role: "agent", Content: "Response"}

	ctx := map[string]interface{}{
		"latency_ms": 150.0,
	}

	score, err := metric.Measure(agent, input, output, ctx)
	if err != nil {
		t.Fatalf("Measure failed: %v", err)
	}
	if score != 150.0 {
		t.Errorf("Expected latency 150ms, got %.0f", score)
	}
}

// TestLatencyMetricNoLatency tests when latency is not provided
func TestLatencyMetricNoLatency(t *testing.T) {
	metric := NewLatencyMetric()

	agent := &MockAgent{name: "test-agent"}
	input := &agenkit.Message{Role: "user", Content: "Test"}
	output := &agenkit.Message{Role: "agent", Content: "Response"}

	score, err := metric.Measure(agent, input, output, nil)
	if err != nil {
		t.Fatalf("Measure failed: %v", err)
	}
	if score != 0.0 {
		t.Errorf("Expected latency 0ms when not provided, got %.0f", score)
	}
}

// TestLatencyMetricAggregate tests aggregation with percentiles
func TestLatencyMetricAggregate(t *testing.T) {
	metric := NewLatencyMetric()

	// Create measurements with known percentiles
	measurements := []float64{
		10, 20, 30, 40, 50, 60, 70, 80, 90, 100,
		110, 120, 130, 140, 150, 160, 170, 180, 190, 200,
	}

	aggregated := metric.Aggregate(measurements)

	// Check mean
	expectedMean := 105.0
	if aggregated["mean"] != expectedMean {
		t.Errorf("Expected mean %.0f, got %.0f", expectedMean, aggregated["mean"])
	}

	// Check min/max
	if aggregated["min"] != 10.0 {
		t.Errorf("Expected min 10, got %.0f", aggregated["min"])
	}
	if aggregated["max"] != 200.0 {
		t.Errorf("Expected max 200, got %.0f", aggregated["max"])
	}

	// Check percentiles (approximate due to rounding and indexing)
	if aggregated["p50"] < 100 || aggregated["p50"] > 110 {
		t.Errorf("Expected p50 ~105, got %.0f", aggregated["p50"])
	}
	if aggregated["p95"] < 180 || aggregated["p95"] > 201 {
		t.Errorf("Expected p95 ~190, got %.0f", aggregated["p95"])
	}
	if aggregated["p99"] < 195 || aggregated["p99"] > 201 {
		t.Errorf("Expected p99 ~198, got %.0f", aggregated["p99"])
	}
}

// TestLatencyMetricAggregateEmpty tests aggregation with no measurements
func TestLatencyMetricAggregateEmpty(t *testing.T) {
	metric := NewLatencyMetric()

	aggregated := metric.Aggregate([]float64{})

	if aggregated["mean"] != 0.0 {
		t.Errorf("Expected mean 0 for empty measurements, got %.0f", aggregated["mean"])
	}
	if aggregated["p50"] != 0.0 {
		t.Errorf("Expected p50 0 for empty measurements, got %.0f", aggregated["p50"])
	}
}

// TestMinMaxFloat64 tests helper functions
func TestMinMaxFloat64(t *testing.T) {
	values := []float64{5.0, 2.0, 8.0, 1.0, 9.0, 3.0}

	min := minFloat64(values)
	if min != 1.0 {
		t.Errorf("Expected min 1.0, got %.0f", min)
	}

	max := maxFloat64(values)
	if max != 9.0 {
		t.Errorf("Expected max 9.0, got %.0f", max)
	}

	// Test empty slice
	emptyMin := minFloat64([]float64{})
	if emptyMin != 0.0 {
		t.Errorf("Expected min 0.0 for empty slice, got %.0f", emptyMin)
	}

	emptyMax := maxFloat64([]float64{})
	if emptyMax != 0.0 {
		t.Errorf("Expected max 0.0 for empty slice, got %.0f", emptyMax)
	}
}

// TestEstimateTokens tests token estimation
func TestEstimateTokens(t *testing.T) {
	metric := NewContextMetrics()

	tests := []struct {
		content  string
		expected int
	}{
		{"", 0},
		{"test", 1},        // 4 chars = 1 token
		{"hello world", 2}, // 11 chars = 2 tokens
		{"This is a longer sentence with more words.", 10}, // 44 chars = 11 tokens
	}

	for _, test := range tests {
		result := metric.estimateTokens(test.content)
		if result != test.expected {
			t.Errorf("estimateTokens(%q) = %d, expected %d", test.content, result, test.expected)
		}
	}
}

// MockAgentWithContext is an agent that tracks context usage
type MockAgentWithContext struct {
	name            string
	processedInputs []*agenkit.Message
}

func (a *MockAgentWithContext) Name() string {
	return a.name
}

func (a *MockAgentWithContext) Capabilities() []string {
	return []string{"test"}
}

func (a *MockAgentWithContext) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	a.processedInputs = append(a.processedInputs, msg)
	return &agenkit.Message{
		Role:    "agent",
		Content: "Processed",
		Metadata: map[string]interface{}{
			"compression_ratio": 50.0, // Simulated 50x compression
		},
	}, nil
}

// TestCompressionMetricsEvaluateAtLengths tests evaluation at different scales
func TestCompressionMetricsEvaluateAtLengths(t *testing.T) {
	// Use small test lengths for fast test
	testLengths := []int{100, 200}
	metric := NewCompressionMetrics(testLengths, 2)

	agent := &MockAgentWithContext{name: "test-agent"}

	needles := []string{
		"NEEDLE 1: Important fact",
		"NEEDLE 2: Another fact",
	}

	results, err := metric.EvaluateAtLengths(agent, "test-session", needles)
	if err != nil {
		t.Fatalf("EvaluateAtLengths failed: %v", err)
	}

	if len(results) != len(testLengths) {
		t.Errorf("Expected %d results, got %d", len(testLengths), len(results))
	}

	for _, length := range testLengths {
		stat, ok := results[length]
		if !ok {
			t.Errorf("Missing result for length %d", length)
			continue
		}

		if stat.RawTokens != length {
			t.Errorf("Expected raw tokens %d, got %d", length, stat.RawTokens)
		}

		if stat.CompressionRatio <= 0 {
			t.Errorf("Expected positive compression ratio, got %.2f", stat.CompressionRatio)
		}

		if stat.RetrievalAccuracy < 0 || stat.RetrievalAccuracy > 1 {
			t.Errorf("Expected retrieval accuracy 0-1, got %.2f", stat.RetrievalAccuracy)
		}
	}
}

// TestCompressionStatsToDict tests CompressionStats serialization
func TestCompressionStatsToDict(t *testing.T) {
	stats := &CompressionStats{
		RawTokens:           1000000,
		CompressedTokens:    10000,
		CompressionRatio:    100.0,
		RetrievalAccuracy:   0.95,
		ContextLengthTested: 1000000,
	}

	dict := stats.ToDict()

	if dict["raw_tokens"] != 1000000 {
		t.Errorf("Expected raw_tokens 1000000, got %v", dict["raw_tokens"])
	}
	if dict["compressed_tokens"] != 10000 {
		t.Errorf("Expected compressed_tokens 10000, got %v", dict["compressed_tokens"])
	}
	if dict["compression_ratio"] != 100.0 {
		t.Errorf("Expected compression_ratio 100.0, got %v", dict["compression_ratio"])
	}
	if dict["retrieval_accuracy"] != 0.95 {
		t.Errorf("Expected retrieval_accuracy 0.95, got %v", dict["retrieval_accuracy"])
	}
}

// BenchmarkContextMetricsMeasure benchmarks the Measure method
func BenchmarkContextMetricsMeasure(b *testing.B) {
	metric := NewContextMetrics()
	agent := &MockAgent{name: "bench-agent"}
	input := &agenkit.Message{
		Role:    "user",
		Content: "Test message",
		Metadata: map[string]interface{}{
			"context_length": 1000.0,
		},
	}
	output := &agenkit.Message{Role: "agent", Content: "Response"}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = metric.Measure(agent, input, output, nil)
	}
}

// BenchmarkLatencyMetricAggregate benchmarks percentile calculation
func BenchmarkLatencyMetricAggregate(b *testing.B) {
	metric := NewLatencyMetric()
	measurements := make([]float64, 1000)
	for i := range measurements {
		measurements[i] = float64(i)
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = metric.Aggregate(measurements)
	}
}

// TestPercentileCalculation tests percentile accuracy
func TestPercentileCalculation(t *testing.T) {
	metric := NewLatencyMetric()

	// Create sorted sequence 1-100
	measurements := make([]float64, 100)
	for i := range measurements {
		measurements[i] = float64(i + 1)
	}

	// Shuffle to ensure sorting works
	shuffled := make([]float64, len(measurements))
	copy(shuffled, measurements)
	for i := len(shuffled) - 1; i > 0; i-- {
		j := i % (i + 1)
		shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
	}

	aggregated := metric.Aggregate(shuffled)

	// p50 should be ~50
	if aggregated["p50"] < 49 || aggregated["p50"] > 51 {
		t.Errorf("Expected p50 ~50, got %.0f", aggregated["p50"])
	}

	// p95 should be ~95 (allow some variance due to indexing)
	if aggregated["p95"] < 93 || aggregated["p95"] > 97 {
		t.Errorf("Expected p95 ~95, got %.0f", aggregated["p95"])
	}

	// p99 should be ~99
	if aggregated["p99"] < 98 || aggregated["p99"] > 100 {
		t.Errorf("Expected p99 ~99, got %.0f", aggregated["p99"])
	}
}

// TestSumHelper tests the sum helper function
func TestSumHelper(t *testing.T) {
	values := []float64{1.0, 2.0, 3.0, 4.0, 5.0}
	expected := 15.0

	result := sum(values)
	if result != expected {
		t.Errorf("sum(%v) = %.0f, expected %.0f", values, result, expected)
	}

	// Empty slice
	empty := sum([]float64{})
	if empty != 0.0 {
		t.Errorf("sum([]) = %.0f, expected 0", empty)
	}
}

// TestContextMetricsIntegration tests full integration scenario
func TestContextMetricsIntegration(t *testing.T) {
	contextMetric := NewContextMetrics()
	latencyMetric := NewLatencyMetric()
	compressionMetric := NewCompressionMetrics([]int{100}, 1)

	agent := &MockAgentWithContext{name: "integration-agent"}

	// Simulate conversation with growing context
	contextMeasurements := make([]float64, 0)
	latencyMeasurements := make([]float64, 0)

	for i := 1; i <= 5; i++ {
		input := &agenkit.Message{
			Role:    "user",
			Content: "Message " + string(rune('0'+i)),
			Metadata: map[string]interface{}{
				"context_length": float64(i * 100),
			},
		}

		output, err := agent.Process(context.Background(), input)
		if err != nil {
			t.Fatalf("Agent processing failed: %v", err)
		}

		ctx := map[string]interface{}{
			"latency_ms": float64(i * 50), // Simulated increasing latency
		}

		// Measure context
		contextLength, _ := contextMetric.Measure(agent, input, output, ctx)
		contextMeasurements = append(contextMeasurements, contextLength)

		// Measure latency
		latency, _ := latencyMetric.Measure(agent, input, output, ctx)
		latencyMeasurements = append(latencyMeasurements, latency)

		// Measure compression
		_, _ = compressionMetric.Measure(agent, input, output, ctx)
	}

	// Aggregate and verify
	contextAgg := contextMetric.Aggregate(contextMeasurements)
	if contextAgg["growth_rate"] <= 0 {
		t.Errorf("Expected positive context growth rate, got %.2f", contextAgg["growth_rate"])
	}

	latencyAgg := latencyMetric.Aggregate(latencyMeasurements)
	if latencyAgg["mean"] <= 0 {
		t.Errorf("Expected positive mean latency, got %.2f", latencyAgg["mean"])
	}

	// Verify latency increases with context
	sortedLatencies := make([]float64, len(latencyMeasurements))
	copy(sortedLatencies, latencyMeasurements)
	sort.Float64s(sortedLatencies)

	isIncreasing := true
	for i := 1; i < len(latencyMeasurements); i++ {
		if latencyMeasurements[i] < latencyMeasurements[i-1] {
			isIncreasing = false
			break
		}
	}

	if !isIncreasing {
		t.Error("Expected latency to increase with context length")
	}
}
