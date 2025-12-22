// Package main demonstrates quality scoring for agent evaluation.
//
// Quality scoring measures how well an agent performs across multiple dimensions:
//   - Accuracy: Does it give correct answers?
//   - Relevance: Are responses on-topic?
//   - Completeness: Does it answer all parts of the question?
//   - Coherence: Is the response well-structured?
//
// This example shows how to use AccuracyMetric, QualityMetrics, and
// PrecisionRecallMetric to comprehensively evaluate agent quality.
//
// Run with: go run quality_scoring_example.go
package main

import (
	"context"
	"fmt"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/evaluation"
)

// QuizAgent simulates an agent that answers quiz questions.
type QuizAgent struct{}

func (a *QuizAgent) Name() string {
	return "quiz-agent"
}

func (a *QuizAgent) Capabilities() []string {
	return []string{"qa"}
}

func (a *QuizAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    a.Name(),
		Capabilities: a.Capabilities(),
	}
}

func (a *QuizAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Simple rule-based responses for demo
	query := strings.ToLower(message.Content)
	var response string

	switch {
	case strings.Contains(query, "capital of france"):
		response = "The capital of France is Paris, a beautiful city known for its art, culture, and the Eiffel Tower."
	case strings.Contains(query, "2+2"):
		response = "2+2 equals 4."
	case strings.Contains(query, "largest ocean"):
		response = "The Pacific Ocean is the largest ocean on Earth, covering more than 63 million square miles."
	case strings.Contains(query, "python language"):
		response = "Python is a high-level programming language created by Guido van Rossum. It's known for its simplicity and readability."
	case strings.Contains(query, "photosynthesis"):
		response = "Photosynthesis is the process by which plants convert light energy into chemical energy, producing oxygen as a byproduct."
	default:
		response = "I'm not sure about that. Could you rephrase the question?"
	}

	return &agenkit.Message{
		Role:    "assistant",
		Content: response,
	}, nil
}

func main() {
	fmt.Println("Quality Scoring Example")
	fmt.Println("=======================")

	// Step 1: Create agent and metrics
	fmt.Println("Step 1: Setting Up Evaluation")
	fmt.Println("------------------------------")
	agent := &QuizAgent{}

	accuracyMetric := evaluation.NewAccuracyMetric(nil, false)
	qualityMetric := evaluation.NewQualityMetrics(false, "", nil)
	precisionRecallMetric := evaluation.NewPrecisionRecallMetric()

	evaluator := evaluation.NewEvaluator(
		agent,
		[]evaluation.Metric{accuracyMetric, qualityMetric, precisionRecallMetric},
		"quality-eval",
	)

	fmt.Println("✓ Agent created: quiz-agent")
	fmt.Println("✓ Metrics configured: accuracy, quality, precision/recall")

	// Step 2: Define test cases
	fmt.Println("Step 2: Defining Test Cases")
	fmt.Println("----------------------------")
	testCases := []map[string]interface{}{
		{
			"input":           "What is the capital of France?",
			"expected":        "Paris",
			"true_label":      true,
			"predicted_label": true,
		},
		{
			"input":           "What is 2+2?",
			"expected":        "4",
			"true_label":      true,
			"predicted_label": true,
		},
		{
			"input":           "What is the largest ocean?",
			"expected":        "Pacific",
			"true_label":      true,
			"predicted_label": true,
		},
		{
			"input":           "Tell me about the Python programming language",
			"expected":        "Python",
			"true_label":      true,
			"predicted_label": true,
		},
		{
			"input":           "Explain photosynthesis",
			"expected":        "photosynthesis",
			"true_label":      true,
			"predicted_label": true,
		},
		{
			"input":           "What is the meaning of life?",
			"expected":        "42", // Agent will fail this
			"true_label":      false,
			"predicted_label": false,
		},
	}

	fmt.Printf("Test cases defined: %d\n\n", len(testCases))

	// Step 3: Run evaluation
	fmt.Println("Step 3: Running Evaluation")
	fmt.Println("---------------------------")
	result, err := evaluator.Evaluate(testCases, "quality-eval-001")
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}

	fmt.Printf("✓ Evaluation complete\n")
	fmt.Printf("  Tests Run: %d\n", result.TotalTests)
	fmt.Printf("  Passed: %d\n", result.PassedTests)
	fmt.Printf("  Failed: %d\n\n", result.FailedTests)

	// Step 4: Analyze accuracy results
	fmt.Println("Step 4: Accuracy Analysis")
	fmt.Println("-------------------------")
	if accuracyStats, ok := result.AggregatedMetrics["accuracy"]; ok {
		fmt.Printf("Overall Accuracy: %.1f%%\n", accuracyStats["accuracy"]*100)
		fmt.Printf("Correct: %.0f\n", accuracyStats["correct"])
		fmt.Printf("Incorrect: %.0f\n", accuracyStats["incorrect"])
		fmt.Printf("Total: %.0f\n\n", accuracyStats["total"])
	}

	// Step 5: Analyze quality scores
	fmt.Println("Step 5: Quality Analysis")
	fmt.Println("------------------------")
	if qualityStats, ok := result.AggregatedMetrics["quality"]; ok {
		fmt.Printf("Quality Metrics:\n")
		fmt.Printf("  Mean Quality Score: %.3f (0.0-1.0 scale)\n", qualityStats["mean"])
		fmt.Printf("  Min Score: %.3f\n", qualityStats["min"])
		fmt.Printf("  Max Score: %.3f\n", qualityStats["max"])
		fmt.Printf("  Std Deviation: %.3f\n\n", qualityStats["std"])

		// Interpretation
		meanQuality := qualityStats["mean"]
		fmt.Println("Interpretation:")
		switch {
		case meanQuality >= 0.8:
			fmt.Println("  ✓ Excellent: Agent responses are high quality")
		case meanQuality >= 0.6:
			fmt.Println("  ⚠ Good: Agent responses are acceptable but could improve")
		case meanQuality >= 0.4:
			fmt.Println("  ⚠ Fair: Agent responses need significant improvement")
		default:
			fmt.Println("  ✗ Poor: Agent responses are low quality")
		}
		fmt.Println()
	}

	// Step 6: Analyze precision/recall
	fmt.Println("Step 6: Precision/Recall Analysis")
	fmt.Println("----------------------------------")
	if prStats, ok := result.AggregatedMetrics["precision_recall"]; ok {
		fmt.Printf("Classification Metrics:\n")
		fmt.Printf("  Precision: %.3f\n", prStats["precision"])
		fmt.Printf("  Recall: %.3f\n", prStats["recall"])
		fmt.Printf("  F1 Score: %.3f\n\n", prStats["f1_score"])

		fmt.Printf("Confusion Matrix:\n")
		fmt.Printf("  True Positives: %.0f\n", prStats["true_positives"])
		fmt.Printf("  False Positives: %.0f\n", prStats["false_positives"])
		fmt.Printf("  True Negatives: %.0f\n", prStats["true_negatives"])
		fmt.Printf("  False Negatives: %.0f\n\n", prStats["false_negatives"])
	}

	// Step 7: Individual test case analysis
	fmt.Println("Step 7: Individual Test Case Analysis")
	fmt.Println("--------------------------------------")
	fmt.Println("\nDetailed Results for Each Test Case:")

	accuracyMeasurements := result.Metrics["accuracy"]
	qualityMeasurements := result.Metrics["quality"]

	for i, testCase := range testCases {
		input := testCase["input"].(string)
		expected := testCase["expected"].(string)

		fmt.Printf("%d. Input: %s\n", i+1, input)
		fmt.Printf("   Expected: %s\n", expected)

		if i < len(accuracyMeasurements) {
			accuracy := accuracyMeasurements[i]
			status := "✗ Incorrect"
			if accuracy == 1.0 {
				status = "✓ Correct"
			}
			fmt.Printf("   Accuracy: %s\n", status)
		}

		if i < len(qualityMeasurements) {
			quality := qualityMeasurements[i]
			fmt.Printf("   Quality Score: %.3f\n", quality)
		}
		fmt.Println()
	}

	// Summary
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println("Summary: Quality Scoring")
	fmt.Println(strings.Repeat("=", 70))

	fmt.Println("\nMetrics Available:")
	fmt.Println("1. AccuracyMetric: Binary correct/incorrect classification")
	fmt.Println("   - Use for: Factual QA, math problems, classification tasks")
	fmt.Println("   - Output: 0.0 (incorrect) or 1.0 (correct)")

	fmt.Println("\n2. QualityMetrics: Multi-dimensional quality assessment")
	fmt.Println("   - Relevance: Does response address the query?")
	fmt.Println("   - Completeness: Is the answer complete?")
	fmt.Println("   - Coherence: Is it well-structured?")
	fmt.Println("   - Accuracy: Is it factually correct?")
	fmt.Println("   - Output: 0.0-1.0 weighted score")

	fmt.Println("\n3. PrecisionRecallMetric: Classification performance")
	fmt.Println("   - Precision: Of predicted positives, how many were correct?")
	fmt.Println("   - Recall: Of actual positives, how many were found?")
	fmt.Println("   - F1 Score: Harmonic mean of precision and recall")
	fmt.Println("   - Use for: Binary classification tasks")

	fmt.Println("\nCustom Validators:")
	fmt.Println("AccuracyMetric supports custom validation functions:")
	fmt.Println("  customValidator := func(expected, actual string) bool {")
	fmt.Println("      // Your custom logic here")
	fmt.Println("      return strings.Contains(actual, expected)")
	fmt.Println("  }")
	fmt.Println("  metric := NewAccuracyMetric(customValidator, false)")

	fmt.Println("\nBest Practices:")
	fmt.Println("1. Use multiple metrics for comprehensive evaluation")
	fmt.Println("2. Combine accuracy (correctness) with quality (completeness)")
	fmt.Println("3. Set realistic expectations (80% accuracy is often good)")
	fmt.Println("4. Analyze failures to identify patterns")
	fmt.Println("5. Track metrics over time to detect regressions")
	fmt.Println("6. Use precision/recall for imbalanced datasets")

	fmt.Println("\nReal-World Applications:")
	fmt.Println("- Customer Service: Measure response relevance and completeness")
	fmt.Println("- QA Systems: Verify factual accuracy of answers")
	fmt.Println("- Classification: Precision/recall for filtering tasks")
	fmt.Println("- Content Generation: Quality scoring for generated text")
	fmt.Println("- Code Generation: Accuracy for syntax, quality for style")
}
