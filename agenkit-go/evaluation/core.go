// Package evaluation provides comprehensive evaluation capabilities for autonomous agents.
//
// Designed for measuring agent quality and performance, with special focus on
// extreme-scale context evaluation (1M-25M+ tokens) for systems like endless.
//
// Example:
//
//	evaluator := evaluation.NewEvaluator(agent, nil, "")
//	testCases := []map[string]interface{}{
//	    {"input": "What is 2+2?", "expected": "4"},
//	}
//	result, _ := evaluator.Evaluate(testCases, "")
//	fmt.Printf("Accuracy: %.2f\n", result.Accuracy)
package evaluation

import (
	"context"
	"fmt"
	"sort"
	"time"

	"github.com/google/uuid"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// Metric is the interface for evaluation metrics.
//
// Metrics measure specific aspects of agent performance:
//   - Accuracy
//   - Latency
//   - Context usage
//   - Quality scores
//   - etc.
type Metric interface {
	// Name returns the metric name.
	Name() string

	// Measure measures metric for a single agent interaction.
	//
	// Args:
	//   agent: The agent being evaluated
	//   inputMessage: Input to the agent
	//   outputMessage: Agent's response
	//   ctx: Additional context (session history, etc.)
	//
	// Returns:
	//   Metric value (typically 0.0 to 1.0)
	Measure(agent agenkit.Agent, inputMessage, outputMessage *agenkit.Message, ctx map[string]interface{}) (float64, error)

	// Aggregate aggregates multiple measurements.
	//
	// Args:
	//   measurements: List of individual measurements
	//
	// Returns:
	//   Aggregated statistics (mean, std, min, max, etc.)
	Aggregate(measurements []float64) map[string]float64
}

// EvaluationResult contains results from an evaluation run.
//
// Includes metrics, metadata, and analysis.
type EvaluationResult struct {
	// Identification
	EvaluationID string
	AgentName    string
	Timestamp    time.Time

	// Metrics
	Metrics           map[string][]float64
	AggregatedMetrics map[string]map[string]float64

	// Context information
	ContextLength    *int
	CompressedLength *int
	CompressionRatio *float64

	// Quality scores
	Accuracy     *float64
	QualityScore *float64

	// Performance
	AvgLatencyMs *float64
	P95LatencyMs *float64

	// Test details
	TotalTests  int
	PassedTests int
	FailedTests int

	// Additional metadata
	Metadata map[string]interface{}
}

// SuccessRate calculates test success rate.
func (r *EvaluationResult) SuccessRate() float64 {
	if r.TotalTests == 0 {
		return 0.0
	}
	return float64(r.PassedTests) / float64(r.TotalTests)
}

// ToDict converts result to dictionary.
func (r *EvaluationResult) ToDict() map[string]interface{} {
	result := map[string]interface{}{
		"evaluation_id":      r.EvaluationID,
		"agent_name":         r.AgentName,
		"timestamp":          r.Timestamp.Format(time.RFC3339),
		"metrics":            r.Metrics,
		"aggregated_metrics": r.AggregatedMetrics,
		"total_tests":        r.TotalTests,
		"passed_tests":       r.PassedTests,
		"failed_tests":       r.FailedTests,
		"success_rate":       r.SuccessRate(),
		"metadata":           r.Metadata,
	}

	if r.ContextLength != nil {
		result["context_length"] = *r.ContextLength
	}
	if r.CompressedLength != nil {
		result["compressed_length"] = *r.CompressedLength
	}
	if r.CompressionRatio != nil {
		result["compression_ratio"] = *r.CompressionRatio
	}
	if r.Accuracy != nil {
		result["accuracy"] = *r.Accuracy
	}
	if r.QualityScore != nil {
		result["quality_score"] = *r.QualityScore
	}
	if r.AvgLatencyMs != nil {
		result["avg_latency_ms"] = *r.AvgLatencyMs
	}
	if r.P95LatencyMs != nil {
		result["p95_latency_ms"] = *r.P95LatencyMs
	}

	return result
}

// Evaluator is the core evaluation orchestrator.
//
// Runs benchmarks, collects metrics, and aggregates results.
//
// Example:
//
//	evaluator := NewEvaluator(agent, nil, "")
//	suite := BenchmarkSuiteStandard()
//	testCases, _ := suite.GenerateAllTestCases()
//	results, _ := evaluator.Evaluate(testCases, "")
//	fmt.Printf("Accuracy: %.2f\n", results.Accuracy)
type Evaluator struct {
	agent     agenkit.Agent
	metrics   []Metric
	sessionID string
}

// NewEvaluator creates a new evaluator.
//
// Args:
//
//	agent: Agent to evaluate
//	metrics: List of metrics to collect (defaults to empty)
//	sessionID: Optional session ID for context tracking
//
// Example:
//
//	evaluator := NewEvaluator(agent, []Metric{NewAccuracyMetric(nil, false)}, "eval-123")
func NewEvaluator(agent agenkit.Agent, metrics []Metric, sessionID string) *Evaluator {
	if sessionID == "" {
		sessionID = fmt.Sprintf("eval-%d", time.Now().Unix())
	}
	if metrics == nil {
		metrics = []Metric{}
	}

	return &Evaluator{
		agent:     agent,
		metrics:   metrics,
		sessionID: sessionID,
	}
}

// Evaluate evaluates agent on test cases.
//
// Args:
//
//	testCases: List of test cases, each with 'input' and 'expected' keys
//	evaluationID: Optional evaluation ID
//
// Returns:
//
//	EvaluationResult with metrics and analysis
//
// Example:
//
//	testCases := []map[string]interface{}{
//	    {"input": "What is 2+2?", "expected": "4"},
//	}
//	result, err := evaluator.Evaluate(testCases, "")
func (e *Evaluator) Evaluate(testCases []map[string]interface{}, evaluationID string) (*EvaluationResult, error) {
	if evaluationID == "" {
		evaluationID = uuid.New().String()
	}

	result := &EvaluationResult{
		EvaluationID:      evaluationID,
		AgentName:         e.agent.Name(),
		Timestamp:         time.Now().UTC(),
		TotalTests:        len(testCases),
		Metrics:           make(map[string][]float64),
		AggregatedMetrics: make(map[string]map[string]float64),
		Metadata:          make(map[string]interface{}),
	}

	// Run tests and collect metrics
	for _, testCase := range testCases {
		// Extract input
		inputContent, ok := testCase["input"].(string)
		if !ok {
			result.FailedTests++
			continue
		}

		inputMsg := &agenkit.Message{
			Role:    "user",
			Content: inputContent,
			Metadata: map[string]interface{}{
				"session_id": e.sessionID,
			},
		}

		// Run agent with timing
		start := time.Now()
		outputMsg, err := e.agent.Process(context.Background(), inputMsg)
		latency := time.Since(start).Milliseconds()

		if err != nil {
			result.FailedTests++
			if result.Metadata["errors"] == nil {
				result.Metadata["errors"] = []string{}
			}
			result.Metadata["errors"] = append(result.Metadata["errors"].([]string), err.Error())
			continue
		}

		// Build context for metrics
		ctx := map[string]interface{}{
			"expected":   testCase["expected"],
			"test_case":  testCase,
			"latency_ms": float64(latency),
		}

		// Check test
		testPassed := e.checkTest(outputMsg, testCase)
		if testPassed {
			result.PassedTests++
		} else {
			result.FailedTests++
		}

		// Store latency
		if result.Metadata["latencies"] == nil {
			result.Metadata["latencies"] = []float64{}
		}
		result.Metadata["latencies"] = append(result.Metadata["latencies"].([]float64), float64(latency))

		// Run metrics
		for _, metric := range e.metrics {
			value, err := metric.Measure(e.agent, inputMsg, outputMsg, ctx)
			if err != nil {
				continue
			}

			if result.Metrics[metric.Name()] == nil {
				result.Metrics[metric.Name()] = []float64{}
			}
			result.Metrics[metric.Name()] = append(result.Metrics[metric.Name()], value)
		}
	}

	// Aggregate metrics
	for _, metric := range e.metrics {
		if measurements, ok := result.Metrics[metric.Name()]; ok {
			result.AggregatedMetrics[metric.Name()] = metric.Aggregate(measurements)
		}
	}

	// Calculate aggregate statistics
	accuracy := result.SuccessRate()
	result.Accuracy = &accuracy

	if latencies, ok := result.Metadata["latencies"].([]float64); ok && len(latencies) > 0 {
		avgLatency := sum(latencies) / float64(len(latencies))
		result.AvgLatencyMs = &avgLatency

		sorted := make([]float64, len(latencies))
		copy(sorted, latencies)
		sort.Float64s(sorted)
		p95Latency := sorted[int(float64(len(sorted))*0.95)]
		result.P95LatencyMs = &p95Latency
	}

	return result, nil
}

// checkTest checks if output passes test case.
//
// Args:
//
//	output: Agent output
//	testCase: Test case with expected output
//
// Returns:
//
//	True if test passed
func (e *Evaluator) checkTest(output *agenkit.Message, testCase map[string]interface{}) bool {
	expected, ok := testCase["expected"]
	if !ok {
		return true
	}

	// Simple string matching
	if expectedStr, ok := expected.(string); ok {
		return contains(output.Content, expectedStr)
	}

	// Custom validator function (would need to support func type)
	// For now, return true
	return true
}

// EvaluateSingle evaluates single interaction.
//
// Args:
//
//	inputMessage: Input to agent
//	expectedOutput: Expected output (optional)
//
// Returns:
//
//	Dictionary of metric values
//
// Example:
//
//	inputMsg := &agenkit.Message{Role: "user", Content: "Hello"}
//	metrics, err := evaluator.EvaluateSingle(inputMsg, "Hi there")
func (e *Evaluator) EvaluateSingle(inputMessage *agenkit.Message, expectedOutput interface{}) (map[string]float64, error) {
	outputMessage, err := e.agent.Process(context.Background(), inputMessage)
	if err != nil {
		return nil, err
	}

	metricsResults := make(map[string]float64)
	ctx := map[string]interface{}{
		"expected": expectedOutput,
	}

	for _, metric := range e.metrics {
		value, err := metric.Measure(e.agent, inputMessage, outputMessage, ctx)
		if err != nil {
			continue
		}
		metricsResults[metric.Name()] = value
	}

	return metricsResults, nil
}

// Helper functions

func sum(values []float64) float64 {
	total := 0.0
	for _, v := range values {
		total += v
	}
	return total
}

func contains(haystack, needle string) bool {
	// Case-insensitive substring matching
	h := []rune(haystack)
	n := []rune(needle)

	if len(n) == 0 {
		return true
	}
	if len(h) < len(n) {
		return false
	}

	// Simple case-insensitive search
	for i := 0; i <= len(h)-len(n); i++ {
		match := true
		for j := 0; j < len(n); j++ {
			if toLower(h[i+j]) != toLower(n[j]) {
				match = false
				break
			}
		}
		if match {
			return true
		}
	}
	return false
}

func toLower(r rune) rune {
	if r >= 'A' && r <= 'Z' {
		return r + ('a' - 'A')
	}
	return r
}
