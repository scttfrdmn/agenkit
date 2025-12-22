// Package main demonstrates production monitoring setup.
//
// Shows how to integrate evaluation framework into production systems
// for continuous monitoring of agent performance.
//
// Run with: go run production_monitoring_example.go
package main

import (
	"context"
	"fmt"
	"math/rand"
	"strings"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/evaluation"
)

// ProductionAgent simulates a production agent
type ProductionAgent struct{}

func (a *ProductionAgent) Name() string {
	return "production-agent"
}

func (a *ProductionAgent) Capabilities() []string {
	return []string{"chat"}
}

func (a *ProductionAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    a.Name(),
		Capabilities: a.Capabilities(),
	}
}

func (a *ProductionAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Simulate processing
	time.Sleep(time.Duration(50+rand.Intn(200)) * time.Millisecond)
	return &agenkit.Message{
		Role:    "assistant",
		Content: "Response to: " + message.Content,
	}, nil
}

func main() {
	fmt.Println("Production Monitoring Example")
	fmt.Println("=============================")

	// Step 1: Initialize monitoring infrastructure
	fmt.Println("Step 1: Initializing Monitoring Infrastructure")
	fmt.Println("-----------------------------------------------")

	// Create metrics collector (thread-safe for concurrent access)
	collector := evaluation.NewMetricsCollector()

	// Create session recorder with file storage
	recorder := evaluation.NewSessionRecorder(
		evaluation.NewFileRecordingStorage("./production_recordings"),
	)

	// Create regression detector with baseline
	baseline := &evaluation.EvaluationResult{
		EvaluationID: "baseline",
		AgentName:    "production-agent",
		Timestamp:    time.Now(),
	}
	accuracy := 0.95
	quality := 0.90
	latency := 150.0
	baseline.Accuracy = &accuracy
	baseline.QualityScore = &quality
	baseline.AvgLatencyMs = &latency

	detector := evaluation.NewRegressionDetector(nil, baseline)

	fmt.Println("✓ MetricsCollector initialized (thread-safe)")
	fmt.Println("✓ SessionRecorder configured with file storage")
	fmt.Println("✓ RegressionDetector configured with baseline")

	// Step 2: Wrap agent for automatic monitoring
	fmt.Println("Step 2: Wrapping Agent for Monitoring")
	fmt.Println("--------------------------------------")
	agent := &ProductionAgent{}
	monitoredAgent := recorder.Wrap(agent)

	fmt.Println("✓ Agent wrapped - all interactions will be recorded")

	// Step 3: Simulate production traffic
	fmt.Println("Step 3: Simulating Production Traffic")
	fmt.Println("--------------------------------------")
	fmt.Println("Processing 50 user requests...")

	for i := 0; i < 50; i++ {
		sessionID := fmt.Sprintf("prod-session-%03d", i+1)

		// Create session result
		result := evaluation.NewSessionResult(sessionID, agent.Name())

		// Process message
		message := &agenkit.Message{
			Role:    "user",
			Content: fmt.Sprintf("User query %d", i+1),
			Metadata: map[string]interface{}{
				"session_id": sessionID,
			},
		}

		start := time.Now()
		_, err := monitoredAgent.Process(context.Background(), message)
		duration := time.Since(start).Seconds()

		// Record metrics
		if err != nil {
			result.SetStatus(evaluation.SessionStatusFailed)
			result.AddError("processing_error", err.Error(), nil)
		} else {
			result.SetStatus(evaluation.SessionStatusCompleted)

			// Add quality metric
			qualityScore := 0.85 + rand.Float64()*0.15
			result.AddMetricMeasurement(evaluation.CreateQualityMetric(
				"response_quality",
				qualityScore*10,
				10.0,
				nil,
			))

			// Add duration metric
			result.AddMetricMeasurement(evaluation.CreateDurationMetric(duration, nil))

			// Add cost metric (simulate token usage)
			tokens := 100 + rand.Intn(300)
			cost := float64(tokens) * 0.00001
			result.AddMetricMeasurement(evaluation.CreateCostMetric(cost, "USD", map[string]interface{}{
				"tokens": tokens,
			}))
		}

		collector.AddResult(result)

		// Print progress every 10 requests
		if (i+1)%10 == 0 {
			fmt.Printf("  Processed %d requests\n", i+1)
		}
	}

	fmt.Println("\n✓ Processing complete")

	// Step 4: Real-time statistics
	fmt.Println("Step 4: Real-time Performance Statistics")
	fmt.Println("-----------------------------------------")
	stats := collector.GetStatistics()

	fmt.Printf("Session Statistics:\n")
	fmt.Printf("  Total Sessions: %d\n", stats["session_count"])
	fmt.Printf("  Success Rate: %.1f%%\n", stats["success_rate"].(float64)*100)
	fmt.Printf("  Avg Duration: %.3fs\n", stats["avg_duration"])
	fmt.Printf("  Total Errors: %d\n\n", stats["total_errors"])

	qualityStats := collector.GetMetricAggregates("response_quality")
	if qualityStats["count"].(int) > 0 {
		fmt.Printf("Quality Metrics:\n")
		fmt.Printf("  Mean Quality: %.3f\n", qualityStats["mean"])
		fmt.Printf("  Min Quality: %.3f\n", qualityStats["min"])
		fmt.Printf("  Max Quality: %.3f\n\n", qualityStats["max"])
	}

	costStats := collector.GetMetricAggregates("total_cost")
	if costStats["count"].(int) > 0 {
		fmt.Printf("Cost Metrics:\n")
		fmt.Printf("  Total Cost: $%.4f\n", costStats["sum"])
		fmt.Printf("  Avg Cost/Request: $%.4f\n\n", costStats["mean"])
	}

	// Step 5: Check for regressions
	fmt.Println("Step 5: Regression Detection")
	fmt.Println("-----------------------------")

	currentEvaluation := &evaluation.EvaluationResult{
		EvaluationID: "current",
		AgentName:    "production-agent",
		Timestamp:    time.Now(),
	}

	// Calculate current metrics from collector stats
	currentAccuracy := stats["success_rate"].(float64)
	currentQuality := qualityStats["mean"].(float64)
	currentLatency := stats["avg_duration"].(float64) * 1000 // convert to ms

	currentEvaluation.Accuracy = &currentAccuracy
	currentEvaluation.QualityScore = &currentQuality
	currentEvaluation.AvgLatencyMs = &currentLatency

	regressions := detector.Detect(currentEvaluation, true)

	if len(regressions) == 0 {
		fmt.Println("✓ No regressions detected - performance is stable")
	} else {
		fmt.Printf("⚠ %d regressions detected:\n\n", len(regressions))
		for _, reg := range regressions {
			fmt.Printf("  %s:\n", reg.MetricName)
			fmt.Printf("    Baseline: %.3f\n", reg.BaselineValue)
			fmt.Printf("    Current: %.3f\n", reg.CurrentValue)
			fmt.Printf("    Degradation: %.1f%%\n", reg.DegradationPercent)
			fmt.Printf("    Severity: %s\n\n", reg.Severity)
		}
	}

	// Summary
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println("Summary: Production Monitoring")
	fmt.Println(strings.Repeat("=", 70))

	fmt.Println("\nMonitoring Components:")
	fmt.Println("1. MetricsCollector: Aggregate statistics across sessions")
	fmt.Println("2. SessionRecorder: Capture interactions for debugging")
	fmt.Println("3. RegressionDetector: Alert on performance degradation")

	fmt.Println("\nRecommended Architecture:")
	fmt.Println("┌─────────────┐")
	fmt.Println("│   Request   │")
	fmt.Println("└──────┬──────┘")
	fmt.Println("       │")
	fmt.Println("       ▼")
	fmt.Println("┌─────────────────────┐")
	fmt.Println("│  Monitoring Wrapper │ (Recorder)")
	fmt.Println("└──────┬──────────────┘")
	fmt.Println("       │")
	fmt.Println("       ▼")
	fmt.Println("┌─────────────────┐")
	fmt.Println("│  Agent Process  │")
	fmt.Println("└──────┬──────────┘")
	fmt.Println("       │")
	fmt.Println("       ▼")
	fmt.Println("┌────────────────────┐")
	fmt.Println("│  Metrics Collector │ (Thread-safe)")
	fmt.Println("└────────────────────┘")

	fmt.Println("\nBest Practices:")
	fmt.Println("1. Record all production interactions (storage is cheap)")
	fmt.Println("2. Compute statistics in real-time (streaming metrics)")
	fmt.Println("3. Run regression detection hourly or per-deployment")
	fmt.Println("4. Export metrics to monitoring systems (Prometheus, DataDog)")
	fmt.Println("5. Set up alerts for critical regressions")
	fmt.Println("6. Review failed sessions daily for patterns")

	fmt.Println("\nPerformance Considerations:")
	fmt.Println("- Recording overhead: <1ms per request")
	fmt.Println("- Thread-safe collector: No locking contention")
	fmt.Println("- File storage: Async I/O recommended for high throughput")
	fmt.Println("- Memory usage: ~1KB per session result")
}
