package evaluation_test

import (
	"context"
	"fmt"
	"log"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/evaluation"
)

// ExampleAgent is a simple agent for demonstration
type ExampleAgent struct {
	name string
}

func (a *ExampleAgent) Name() string {
	return a.name
}

func (a *ExampleAgent) Capabilities() []string {
	return []string{"question-answering"}
}

func (a *ExampleAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	// Simple Q&A logic
	content := msg.Content
	var response string

	switch content {
	case "What is the capital of France?":
		response = "The capital of France is Paris."
	case "What is 2+2?":
		response = "2+2 equals 4."
	default:
		response = "I don't know the answer to that question."
	}

	return &agenkit.Message{
		Role:    "agent",
		Content: response,
	}, nil
}

// ExampleEvaluator demonstrates basic evaluation
func Example_evaluator() {
	agent := &ExampleAgent{name: "qa-agent"}

	// Create evaluator with metrics
	metrics := []evaluation.Metric{
		evaluation.NewAccuracyMetric(nil, false),
		evaluation.NewQualityMetrics(false, "", nil),
	}

	evaluator := evaluation.NewEvaluator(agent, metrics, "session-123")

	// Define test cases
	testCases := []map[string]interface{}{
		{
			"input":    "What is the capital of France?",
			"expected": "Paris",
		},
		{
			"input":    "What is 2+2?",
			"expected": "4",
		},
	}

	// Run evaluation
	result, err := evaluator.Evaluate(testCases, "")
	if err != nil {
		log.Fatal(err)
	}

	// Print results
	fmt.Printf("Total Tests: %d\n", result.TotalTests)
	fmt.Printf("Passed: %d\n", result.PassedTests)
	if result.Accuracy != nil {
		fmt.Printf("Accuracy: %.2f\n", *result.Accuracy)
	}

	// Output:
	// Total Tests: 2
	// Passed: 2
	// Accuracy: 1.00
}

// Example_regressionDetector demonstrates regression detection
func Example_regressionDetector() {
	// Create baseline result
	accuracy := 0.95
	quality := 0.90
	latency := 100.0
	baseline := &evaluation.EvaluationResult{
		Accuracy:     &accuracy,
		QualityScore: &quality,
		AvgLatencyMs: &latency,
	}

	// Create detector with baseline
	detector := evaluation.NewRegressionDetector(nil, baseline)

	// Simulate degraded performance
	newAccuracy := 0.80
	newQuality := 0.85
	newLatency := 150.0
	current := &evaluation.EvaluationResult{
		Accuracy:     &newAccuracy,
		QualityScore: &newQuality,
		AvgLatencyMs: &newLatency,
	}

	// Detect regressions
	regressions := detector.Detect(current, true)

	fmt.Printf("Found %d regressions\n", len(regressions))

	// Output:
	// Found 3 regressions
}

// Example_contextMetrics demonstrates context tracking
func Example_contextMetrics() {
	metric := evaluation.NewContextMetrics()

	agent := &ExampleAgent{name: "test-agent"}
	input := &agenkit.Message{
		Role:    "user",
		Content: "Test query",
		Metadata: map[string]interface{}{
			"context_length": 1000.0,
		},
	}
	output := &agenkit.Message{
		Role:    "agent",
		Content: "Test response",
	}

	// Measure context length
	length, err := metric.Measure(agent, input, output, nil)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf("Context length: %.0f tokens\n", length)

	// Simulate growing context over time
	measurements := []float64{1000, 1200, 1400, 1600, 1800}
	aggregated := metric.Aggregate(measurements)

	fmt.Printf("Mean context: %.0f tokens\n", aggregated["mean"])
	fmt.Printf("Growth rate: %.0f tokens/interaction\n", aggregated["growth_rate"])

	// Output:
	// Context length: 1000 tokens
	// Mean context: 1400 tokens
	// Growth rate: 200 tokens/interaction
}

// Example_latencyMetric demonstrates latency tracking
func Example_latencyMetric() {
	metric := evaluation.NewLatencyMetric()

	// Simulate latency measurements
	measurements := []float64{
		95, 102, 98, 105, 110, 97, 103, 120, 99, 101,
		104, 108, 96, 100, 115, 102, 98, 105, 130, 99,
	}

	aggregated := metric.Aggregate(measurements)

	fmt.Printf("Latency Statistics:\n")
	fmt.Printf("Mean: %.0fms\n", aggregated["mean"])
	fmt.Printf("p50:  %.0fms\n", aggregated["p50"])
	fmt.Printf("p95:  %.0fms\n", aggregated["p95"])
	fmt.Printf("p99:  %.0fms\n", aggregated["p99"])

	// Output:
	// Latency Statistics:
	// Mean: 104ms
	// p50:  102ms
	// p95:  120ms
	// p99:  130ms
}

// Example_precisionRecallMetric demonstrates classification evaluation
func Example_precisionRecallMetric() {
	metric := evaluation.NewPrecisionRecallMetric()
	agent := &ExampleAgent{name: "classifier"}

	input := &agenkit.Message{Role: "user", Content: "Classify"}
	output := &agenkit.Message{Role: "agent", Content: "Positive"}

	// Simulate classification results
	testCases := []struct {
		trueLabel      bool
		predictedLabel bool
	}{
		{true, true},   // TP
		{true, true},   // TP
		{false, true},  // FP
		{true, false},  // FN
		{false, false}, // TN
	}

	measurements := make([]float64, 0)
	for _, tc := range testCases {
		ctx := map[string]interface{}{
			"true_label":      tc.trueLabel,
			"predicted_label": tc.predictedLabel,
		}
		score, _ := metric.Measure(agent, input, output, ctx)
		measurements = append(measurements, score)
	}

	results := metric.Aggregate(measurements)

	fmt.Printf("Precision: %.2f\n", results["precision"])
	fmt.Printf("Recall: %.2f\n", results["recall"])
	fmt.Printf("F1 Score: %.2f\n", results["f1_score"])

	// Output:
	// Precision: 0.67
	// Recall: 0.67
	// F1 Score: 0.67
}

// Example_benchmarkSuite demonstrates running benchmark suites
func Example_benchmarkSuite() {
	// Create standard benchmark suite
	suite := evaluation.BenchmarkSuiteStandard()

	// Generate all test cases
	testCases, err := suite.GenerateAllTestCases()
	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf("Generated %d test cases from standard suite\n", len(testCases))

	// Output:
	// Generated 28 test cases from standard suite
}

// Example_accuracyMetric demonstrates accuracy measurement
func Example_accuracyMetric() {
	metric := evaluation.NewAccuracyMetric(nil, false)
	agent := &ExampleAgent{name: "qa-agent"}

	input := &agenkit.Message{
		Role:    "user",
		Content: "What is the capital of France?",
	}
	output := &agenkit.Message{
		Role:    "agent",
		Content: "The capital of France is Paris.",
	}

	ctx := map[string]interface{}{
		"expected": "Paris",
	}

	score, err := metric.Measure(agent, input, output, ctx)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf("Accuracy score: %.0f\n", score)

	// Output:
	// Accuracy score: 1
}

// Example_qualityMetrics demonstrates quality scoring
func Example_qualityMetrics() {
	metric := evaluation.NewQualityMetrics(false, "", nil)
	agent := &ExampleAgent{name: "qa-agent"}

	input := &agenkit.Message{
		Role:    "user",
		Content: "Explain machine learning",
	}

	// Good response
	output1 := &agenkit.Message{
		Role: "agent",
		Content: "Machine learning is a branch of artificial intelligence that " +
			"enables systems to learn from data and improve their performance " +
			"over time without being explicitly programmed.",
	}

	score1, _ := metric.Measure(agent, input, output1, nil)
	fmt.Printf("Good response quality: %.2f\n", score1)

	// Poor response
	output2 := &agenkit.Message{
		Role:    "agent",
		Content: "Yes.",
	}

	score2, _ := metric.Measure(agent, input, output2, nil)
	fmt.Printf("Poor response quality: %.2f\n", score2)

	// Output:
	// Good response quality: 0.73
	// Poor response quality: 0.19
}

// Example_compressionMetrics demonstrates compression evaluation
func Example_compressionMetrics() {
	// Create metrics for small test lengths
	testLengths := []int{1000, 5000, 10000}
	metric := evaluation.NewCompressionMetrics(testLengths, 3)

	fmt.Printf("Metric name: %s\n", metric.Name())
	fmt.Printf("Testing %d scale points\n", len(testLengths))

	// Output:
	// Metric name: compression_quality
	// Testing 3 scale points
}

// Example_evaluatorContinuous demonstrates continuous evaluation
func Example_evaluatorContinuous() {
	agent := &ExampleAgent{name: "qa-agent"}
	metrics := []evaluation.Metric{
		evaluation.NewAccuracyMetric(nil, false),
	}

	evaluator := evaluation.NewEvaluator(agent, metrics, "continuous-session")

	// Set up regression detection
	detector := evaluation.NewRegressionDetector(nil, nil)

	// Baseline evaluation
	baselineTests := []map[string]interface{}{
		{
			"input":    "What is the capital of France?",
			"expected": "Paris",
		},
	}

	baselineResult, _ := evaluator.Evaluate(baselineTests, "")
	detector.SetBaseline(baselineResult)
	fmt.Println("Baseline established")

	// Current evaluation
	currentTests := baselineTests // Same tests
	currentResult, _ := evaluator.Evaluate(currentTests, "")

	// Detect regressions
	regressions := detector.Detect(currentResult, true)
	if len(regressions) > 0 {
		fmt.Printf("Detected %d regressions\n", len(regressions))
	} else {
		fmt.Println("No regressions detected")
	}

	// Output:
	// Baseline established
	// No regressions detected
}

// Example_sessionRecorder demonstrates session recording
func Example_sessionRecorder() {
	storage := evaluation.NewInMemoryRecordingStorage()
	recorder := evaluation.NewSessionRecorder(storage)

	// Start session
	recorder.StartSession("session-123", "qa-agent", nil)

	// Wrap agent to automatically record
	agent := &ExampleAgent{name: "qa-agent"}
	wrappedAgent := recorder.Wrap(agent)

	// Process message (automatically recorded)
	input := &agenkit.Message{
		Role:    "user",
		Content: "What is AI?",
		Metadata: map[string]interface{}{
			"session_id": "session-123",
		},
	}

	_, _ = wrappedAgent.Process(context.Background(), input)

	// Finalize session
	recording, err := recorder.FinalizeSession("session-123")
	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf("Session %s recorded\n", recording.SessionID)
	fmt.Printf("Interactions: %d\n", recording.InteractionCount())

	// Output:
	// Session session-123 recorded
	// Interactions: 1
}
