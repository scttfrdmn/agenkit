// Package main demonstrates regression detection for agent quality monitoring.
//
// Regression detection compares current agent performance to a baseline,
// alerting when quality degrades beyond acceptable thresholds.
//
// Run with: go run regression_detection_example.go
package main

import (
	"fmt"
	"strings"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/evaluation"
)

func createEvaluationResult(id string, accuracy, quality, latency float64) *evaluation.EvaluationResult {
	result := &evaluation.EvaluationResult{
		EvaluationID: id,
		AgentName:    "production-agent",
		Timestamp:    time.Now(),
		TotalTests:   100,
		PassedTests:  int(accuracy * 100),
		FailedTests:  int((1 - accuracy) * 100),
	}
	result.Accuracy = &accuracy
	result.QualityScore = &quality
	result.AvgLatencyMs = &latency
	return result
}

func main() {
	fmt.Println("Regression Detection Example")
	fmt.Println("============================")

	// Step 1: Establish baseline
	fmt.Println("Step 1: Establishing Baseline Performance")
	fmt.Println("------------------------------------------")
	baseline := createEvaluationResult("baseline-001", 0.95, 0.92, 150.0)

	fmt.Printf("Baseline Metrics:\n")
	fmt.Printf("  Accuracy: %.1f%%\n", *baseline.Accuracy*100)
	fmt.Printf("  Quality: %.3f\n", *baseline.QualityScore)
	fmt.Printf("  Latency: %.0fms\n\n", *baseline.AvgLatencyMs)

	// Step 2: Create detector
	fmt.Println("Step 2: Creating Regression Detector")
	fmt.Println("-------------------------------------")
	detector := evaluation.NewRegressionDetector(nil, baseline)

	fmt.Println("✓ Detector created with default thresholds:")
	fmt.Println("  Accuracy: 10% degradation")
	fmt.Println("  Quality: 10% degradation")
	fmt.Println("  Latency: 20% increase")

	// Step 3: Simulate good performance (no regression)
	fmt.Println("Step 3: Testing Good Performance (No Regression)")
	fmt.Println("------------------------------------------------")
	goodResult := createEvaluationResult("eval-002", 0.94, 0.91, 155.0)
	regressions := detector.Detect(goodResult, true)

	fmt.Printf("Current Performance:\n")
	fmt.Printf("  Accuracy: %.1f%%\n", *goodResult.Accuracy*100)
	fmt.Printf("  Quality: %.3f\n", *goodResult.QualityScore)
	fmt.Printf("  Latency: %.0fms\n", *goodResult.AvgLatencyMs)
	fmt.Printf("\nRegressions Detected: %d\n", len(regressions))
	if len(regressions) == 0 {
		fmt.Println("✓ Performance within acceptable range")
	}

	// Step 4: Simulate moderate regression
	fmt.Println("Step 4: Testing Moderate Degradation")
	fmt.Println("-------------------------------------")
	moderateResult := createEvaluationResult("eval-003", 0.83, 0.81, 190.0)
	regressions = detector.Detect(moderateResult, true)

	fmt.Printf("Current Performance:\n")
	fmt.Printf("  Accuracy: %.1f%%\n", *moderateResult.Accuracy*100)
	fmt.Printf("  Quality: %.3f\n", *moderateResult.QualityScore)
	fmt.Printf("  Latency: %.0fms\n", *moderateResult.AvgLatencyMs)
	fmt.Printf("\n⚠ Regressions Detected: %d\n\n", len(regressions))

	for _, reg := range regressions {
		fmt.Printf("Regression: %s\n", reg.MetricName)
		fmt.Printf("  Baseline: %.3f\n", reg.BaselineValue)
		fmt.Printf("  Current: %.3f\n", reg.CurrentValue)
		fmt.Printf("  Degradation: %.1f%%\n", reg.DegradationPercent)
		fmt.Printf("  Severity: %s\n\n", reg.Severity)
	}

	// Step 5: Simulate critical regression
	fmt.Println("Step 5: Testing Critical Degradation")
	fmt.Println("-------------------------------------")
	criticalResult := createEvaluationResult("eval-004", 0.45, 0.42, 350.0)
	regressions = detector.Detect(criticalResult, true)

	fmt.Printf("Current Performance:\n")
	fmt.Printf("  Accuracy: %.1f%%\n", *criticalResult.Accuracy*100)
	fmt.Printf("  Quality: %.3f\n", *criticalResult.QualityScore)
	fmt.Printf("  Latency: %.0fms\n", *criticalResult.AvgLatencyMs)
	fmt.Printf("\n✗ CRITICAL Regressions Detected: %d\n\n", len(regressions))

	for _, reg := range regressions {
		fmt.Printf("Regression: %s\n", reg.MetricName)
		fmt.Printf("  Baseline: %.3f\n", reg.BaselineValue)
		fmt.Printf("  Current: %.3f\n", reg.CurrentValue)
		fmt.Printf("  Degradation: %.1f%%\n", reg.DegradationPercent)
		fmt.Printf("  Severity: %s\n\n", reg.Severity)
	}

	// Step 6: Trend analysis
	fmt.Println("Step 6: Analyzing Performance Trends")
	fmt.Println("-------------------------------------")

	// Add more historical data
	for i := 0; i < 10; i++ {
		accuracy := 0.95 - float64(i)*0.03 // Declining trend
		quality := 0.92 - float64(i)*0.025
		latency := 150.0 + float64(i)*15.0

		result := createEvaluationResult(fmt.Sprintf("eval-%03d", i+5), accuracy, quality, latency)
		detector.Detect(result, true)
	}

	trend := detector.GetTrend("accuracy", 10)
	if trend != nil {
		fmt.Printf("Accuracy Trend (last 10 evaluations):\n")
		fmt.Printf("  Direction: %s\n", trend["direction"])
		fmt.Printf("  Slope: %.6f\n", trend["slope"])
		fmt.Printf("  Current: %.3f\n", trend["current"])
		fmt.Printf("  Mean: %.3f\n", trend["mean"])
		fmt.Printf("  Variance: %.6f\n\n", trend["variance"])

		if trend["direction"] == "degrading" {
			fmt.Println("⚠ Warning: Accuracy is trending downward")
		}
	}

	// Summary
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println("Summary: Regression Detection")
	fmt.Println(strings.Repeat("=", 70))

	fmt.Println("\nSeverity Levels:")
	fmt.Println("- None: <10% degradation (within normal variance)")
	fmt.Println("- Minor: 10-20% degradation (monitor closely)")
	fmt.Println("- Moderate: 20-50% degradation (investigate)")
	fmt.Println("- Critical: >50% degradation (immediate action)")

	fmt.Println("\nBest Practices:")
	fmt.Println("1. Establish baseline from production data, not test data")
	fmt.Println("2. Set thresholds based on business requirements")
	fmt.Println("3. Run detection after every deployment")
	fmt.Println("4. Track trends over time, not just point-in-time")
	fmt.Println("5. Alert on-call engineers for critical regressions")
	fmt.Println("6. Update baseline periodically as agent improves")

	fmt.Println("\nIntegration with CI/CD:")
	fmt.Println("if regressions := detector.Detect(result, true); len(regressions) > 0 {")
	fmt.Println("    for _, reg := range regressions {")
	fmt.Println("        if reg.Severity == evaluation.SeverityCritical {")
	fmt.Println("            log.Fatal(\"Critical regression detected, blocking deployment\")")
	fmt.Println("        }")
	fmt.Println("    }")
	fmt.Println("}")
}
