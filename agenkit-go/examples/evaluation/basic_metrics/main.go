// Package main demonstrates basic metrics collection and aggregation.
//
// This example shows how to use the evaluation framework to:
//   - Create SessionResult instances to track agent sessions
//   - Add metric measurements (quality, cost, duration)
//   - Collect multiple session results
//   - Compute aggregate statistics across sessions
//
// This is the foundation for monitoring agent performance over time,
// tracking success rates, detecting issues, and measuring improvements.
//
// Run with: go run basic_metrics_example.go
package main

import (
	"fmt"
	"math/rand"
	"strings"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/evaluation"
)

// simulateAgentSession simulates running an agent session and collecting metrics.
func simulateAgentSession(sessionID string, agentName string) *evaluation.SessionResult {
	result := evaluation.NewSessionResult(sessionID, agentName)

	// Simulate some processing time
	time.Sleep(time.Duration(10+rand.Intn(50)) * time.Millisecond)

	// Add quality metrics
	qualityScore := 0.7 + rand.Float64()*0.3 // 0.7-1.0
	result.AddMetricMeasurement(evaluation.CreateQualityMetric(
		"response_quality",
		qualityScore*10,
		10.0,
		map[string]interface{}{
			"evaluator": "rule_based",
		},
	))

	// Add cost metrics
	tokensUsed := 100 + rand.Intn(400)
	costPerToken := 0.00001
	totalCost := float64(tokensUsed) * costPerToken
	result.AddMetricMeasurement(evaluation.CreateCostMetric(
		totalCost,
		"USD",
		map[string]interface{}{
			"tokens": tokensUsed,
		},
	))

	// Add duration metrics
	durationSeconds := 0.5 + rand.Float64()*2.0 // 0.5-2.5 seconds
	result.AddMetricMeasurement(evaluation.CreateDurationMetric(
		durationSeconds,
		nil,
	))

	// Add custom success rate metric
	success := rand.Float64() > 0.2 // 80% success rate
	successValue := 0.0
	if success {
		successValue = 1.0
		result.SetStatus(evaluation.SessionStatusCompleted)
	} else {
		result.SetStatus(evaluation.SessionStatusFailed)
		result.AddError("processing_error", "Failed to complete task", map[string]interface{}{
			"reason": "timeout",
		})
	}

	result.AddMetricMeasurement(evaluation.NewMetricMeasurement(
		"success",
		successValue,
		evaluation.MetricTypeSuccessRate,
	))

	return result
}

func main() {
	fmt.Println("Basic Metrics Collection Example")
	fmt.Println("=================================")

	// Step 1: Create metrics collector
	fmt.Println("Step 1: Creating Metrics Collector")
	fmt.Println("-----------------------------------")
	collector := evaluation.NewMetricsCollector()
	fmt.Println("✓ Metrics collector created")

	// Step 2: Simulate multiple agent sessions
	fmt.Println("Step 2: Simulating Agent Sessions")
	fmt.Println("----------------------------------")
	numSessions := 20
	fmt.Printf("Running %d simulated agent sessions...\n\n", numSessions)

	for i := 0; i < numSessions; i++ {
		sessionID := fmt.Sprintf("session-%03d", i+1)
		agentName := "example-agent"

		result := simulateAgentSession(sessionID, agentName)
		collector.AddResult(result)

		// Print progress
		status := "✓"
		if result.Status != evaluation.SessionStatusCompleted {
			status = "✗"
		}
		fmt.Printf("  %s Session %d: %s\n", status, i+1, result.Status)
	}
	fmt.Println()

	// Step 3: Compute aggregate statistics
	fmt.Println("Step 3: Computing Aggregate Statistics")
	fmt.Println("---------------------------------------")
	stats := collector.GetStatistics()

	fmt.Printf("Total Sessions: %d\n", stats["session_count"])
	fmt.Printf("Completed: %d\n", stats["completed_count"])
	fmt.Printf("Failed: %d\n", stats["failed_count"])
	fmt.Printf("Success Rate: %.1f%%\n", stats["success_rate"].(float64)*100)
	fmt.Printf("Average Duration: %.2fs\n", stats["avg_duration"])
	fmt.Printf("Total Errors: %d\n", stats["total_errors"])
	fmt.Printf("Avg Errors/Session: %.2f\n\n", stats["avg_errors_per_session"])

	// Step 4: Analyze specific metrics
	fmt.Println("Step 4: Analyzing Specific Metrics")
	fmt.Println("-----------------------------------")

	// Quality metrics
	qualityStats := collector.GetMetricAggregates("response_quality")
	if qualityStats["count"].(int) > 0 {
		fmt.Printf("\nQuality Metrics:\n")
		fmt.Printf("  Count: %d\n", qualityStats["count"])
		fmt.Printf("  Mean: %.3f\n", qualityStats["mean"])
		fmt.Printf("  Min: %.3f\n", qualityStats["min"])
		fmt.Printf("  Max: %.3f\n", qualityStats["max"])
	}

	// Cost metrics
	costStats := collector.GetMetricAggregates("total_cost")
	if costStats["count"].(int) > 0 {
		fmt.Printf("\nCost Metrics:\n")
		fmt.Printf("  Count: %d\n", costStats["count"])
		fmt.Printf("  Total Cost: $%.4f\n", costStats["sum"])
		fmt.Printf("  Average Cost/Session: $%.4f\n", costStats["mean"])
		fmt.Printf("  Min Cost: $%.4f\n", costStats["min"])
		fmt.Printf("  Max Cost: $%.4f\n", costStats["max"])
	}

	// Duration metrics
	durationStats := collector.GetMetricAggregates("duration")
	if durationStats["count"].(int) > 0 {
		fmt.Printf("\nDuration Metrics:\n")
		fmt.Printf("  Count: %d\n", durationStats["count"])
		fmt.Printf("  Total Duration: %.2fs\n", durationStats["sum"])
		fmt.Printf("  Average Duration: %.2fs\n", durationStats["mean"])
		fmt.Printf("  Min Duration: %.2fs\n", durationStats["min"])
		fmt.Printf("  Max Duration: %.2fs\n", durationStats["max"])
	}

	// Success rate metrics
	successStats := collector.GetMetricAggregates("success")
	if successStats["count"].(int) > 0 {
		fmt.Printf("\nSuccess Rate Metrics:\n")
		fmt.Printf("  Count: %d\n", successStats["count"])
		fmt.Printf("  Success Rate: %.1f%%\n", successStats["mean"].(float64)*100)
	}

	// Step 5: Examine individual session results
	fmt.Println("\n\nStep 5: Examining Individual Sessions")
	fmt.Println("--------------------------------------")
	results := collector.GetResults()

	fmt.Println("\nTop 3 Highest Quality Sessions:")
	fmt.Println(strings.Repeat("-", 70))

	// Sort by quality
	type sessionWithQuality struct {
		result  evaluation.SessionResult
		quality float64
	}
	sessionsWithQuality := make([]sessionWithQuality, 0)
	for _, result := range results {
		if metric := result.GetMetric("response_quality"); metric != nil {
			sessionsWithQuality = append(sessionsWithQuality, sessionWithQuality{
				result:  result,
				quality: metric.Value,
			})
		}
	}

	// Simple bubble sort for top 3
	for i := 0; i < len(sessionsWithQuality); i++ {
		for j := i + 1; j < len(sessionsWithQuality); j++ {
			if sessionsWithQuality[j].quality > sessionsWithQuality[i].quality {
				sessionsWithQuality[i], sessionsWithQuality[j] = sessionsWithQuality[j], sessionsWithQuality[i]
			}
		}
	}

	for i := 0; i < 3 && i < len(sessionsWithQuality); i++ {
		sw := sessionsWithQuality[i]
		costMetric := sw.result.GetMetric("total_cost")
		durationMetric := sw.result.GetMetric("duration")

		fmt.Printf("%d. Session: %s\n", i+1, sw.result.SessionID)
		fmt.Printf("   Quality: %.3f\n", sw.quality)
		if costMetric != nil {
			fmt.Printf("   Cost: $%.4f\n", costMetric.Value)
		}
		if durationMetric != nil {
			fmt.Printf("   Duration: %.2fs\n", durationMetric.Value)
		}
		fmt.Printf("   Status: %s\n\n", sw.result.Status)
	}

	// Step 6: Summary and best practices
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println("Summary: Basic Metrics Collection")
	fmt.Println(strings.Repeat("=", 70))

	fmt.Println("\nKey Capabilities:")
	fmt.Println("1. SessionResult: Track individual agent session metrics")
	fmt.Println("2. MetricsCollector: Aggregate metrics across multiple sessions")
	fmt.Println("3. Metric Types: Quality, cost, duration, success rate, custom")
	fmt.Println("4. Statistics: Success rate, averages, min/max, error rates")

	fmt.Println("\nMetric Types Available:")
	fmt.Println("- MetricTypeSuccessRate: Binary success/failure tracking")
	fmt.Println("- MetricTypeQualityScore: Normalized quality scores (0.0-1.0)")
	fmt.Println("- MetricTypeCost: Token costs and API expenses")
	fmt.Println("- MetricTypeDuration: Execution time tracking")
	fmt.Println("- MetricTypeErrorRate: Error frequency analysis")
	fmt.Println("- MetricTypeTaskCompletion: Task completion tracking")
	fmt.Println("- MetricTypeCustom: Domain-specific metrics")

	fmt.Println("\nThread Safety:")
	fmt.Println("MetricsCollector is thread-safe and can be used concurrently")
	fmt.Println("from multiple goroutines without additional synchronization.")

	fmt.Println("\nBest Practices:")
	fmt.Println("1. Create one SessionResult per agent invocation")
	fmt.Println("2. Add measurements as they occur (streaming metrics)")
	fmt.Println("3. Set final status (completed/failed) when session ends")
	fmt.Println("4. Use helper functions (CreateQualityMetric, CreateCostMetric)")
	fmt.Println("5. Collect across many sessions for statistical significance")
	fmt.Println("6. Export to JSON for long-term storage and analysis")

	fmt.Println("\nReal-World Applications:")
	fmt.Println("- Monitor agent success rates over time")
	fmt.Println("- Track API costs and token usage")
	fmt.Println("- Identify slow or expensive sessions")
	fmt.Println("- Detect quality degradation")
	fmt.Println("- A/B test different agent configurations")
	fmt.Println("- Generate performance reports and dashboards")
}
