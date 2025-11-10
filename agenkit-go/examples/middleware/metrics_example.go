/*
Metrics Middleware Example

WHY USE METRICS MIDDLEWARE?
---------------------------
1. Observability: Understand system behavior in production
2. Debugging: Quickly identify bottlenecks and performance issues
3. Capacity Planning: Know when to scale based on real usage
4. SLA Tracking: Ensure you're meeting latency and reliability targets

WHEN TO USE:
- Production systems (always!)
- Load testing and benchmarking
- Debugging performance issues
- Multi-tenant systems (per-tenant metrics)

WHEN NOT TO USE:
- Early prototyping (adds cognitive overhead)
- Single-use scripts

TRADE-OFFS:
- Small overhead (~1-2% latency) vs critical visibility
- Memory usage (metrics storage) vs historical data

Run with: go run agenkit-go/examples/middleware/metrics_example.go
*/

package main

import (
	"context"
	"fmt"
	"math/rand"
	"strings"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
	"github.com/agenkit/agenkit-go/middleware"
)

// LLMAgent simulates an LLM API with variable latency
type LLMAgent struct {
	name        string
	meanLatency time.Duration
	errorRate   float64
}

func NewLLMAgent(name string, meanLatency time.Duration, errorRate float64) *LLMAgent {
	return &LLMAgent{
		name:        name,
		meanLatency: meanLatency,
		errorRate:   errorRate,
	}
}

func (a *LLMAgent) Name() string {
	return a.name
}

func (a *LLMAgent) Capabilities() []string {
	return []string{"text_generation"}
}

func (a *LLMAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Simulate realistic latency distribution
	jitter := time.Duration(rand.NormFloat64() * float64(a.meanLatency) * 0.3)
	latency := a.meanLatency + jitter
	if latency < 0 {
		latency = a.meanLatency / 2
	}
	time.Sleep(latency)

	// Simulate occasional failures
	if rand.Float64() < a.errorRate {
		return nil, fmt.Errorf("LLM API Error: Rate limit exceeded (429)")
	}

	return agenkit.NewMessage("agent", fmt.Sprintf("Response from %s", a.name)).
		WithMetadata("model", a.name).
		WithMetadata("tokens", 150), nil
}

// Example 1: Basic metrics collection
func example1BasicMetrics() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 1: Basic Metrics Collection")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nUse case: Monitor LLM API latency and error rates")

	// Create agent and wrap with metrics
	agent := NewLLMAgent("gpt-4", 100*time.Millisecond, 0.1)
	monitored := middleware.NewMetricsDecorator(agent)

	// Simulate production traffic
	fmt.Println("\nSimulating 20 API calls...")
	ctx := context.Background()

	for i := 0; i < 20; i++ {
		_, _ = monitored.Process(ctx, agenkit.NewMessage("user", fmt.Sprintf("Request %d", i+1)))
	}

	// Analyze metrics
	metrics := monitored.GetMetrics().Snapshot()
	fmt.Println("\nMetrics Report:")
	fmt.Printf("  Total Requests:   %d\n", metrics.TotalRequests)
	fmt.Printf("  Successful:       %d\n", metrics.SuccessRequests)
	fmt.Printf("  Failed:           %d\n", metrics.ErrorRequests)
	fmt.Printf("  Error Rate:       %.1f%%\n", metrics.ErrorRate()*100)
	fmt.Printf("  Avg Latency:      %v\n", metrics.AverageLatency().Round(time.Millisecond))
	fmt.Printf("  Min Latency:      %v\n", metrics.MinLatency.Round(time.Millisecond))
	fmt.Printf("  Max Latency:      %v\n", metrics.MaxLatency.Round(time.Millisecond))

	fmt.Println("\nKEY INSIGHT:")
	fmt.Println("  Track these metrics over time to detect:")
	fmt.Println("  - Gradual latency increases (capacity issues)")
	fmt.Println("  - Error rate spikes (service degradation)")
	fmt.Println("  - Unusual traffic patterns (potential attacks)")
}

// Example 2: Performance comparison
func example2PerformanceComparison() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 2: Performance Comparison")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nUse case: A/B test different LLM providers")

	// Create agents for different providers
	agents := map[string]*middleware.MetricsDecorator{
		"GPT-4":      middleware.NewMetricsDecorator(NewLLMAgent("gpt-4", 300*time.Millisecond, 0.02)),
		"Claude-3":   middleware.NewMetricsDecorator(NewLLMAgent("claude-3", 200*time.Millisecond, 0.01)),
		"Gemini Pro": middleware.NewMetricsDecorator(NewLLMAgent("gemini-pro", 150*time.Millisecond, 0.05)),
	}

	// Run same workload on all agents
	fmt.Println("\nRunning 10 requests on each provider...")
	ctx := context.Background()

	for name, agent := range agents {
		for i := 0; i < 10; i++ {
			_, _ = agent.Process(ctx, agenkit.NewMessage("user", fmt.Sprintf("Test query %d", i+1)))
		}
		fmt.Printf("  Completed: %s\n", name)
	}

	// Compare metrics
	fmt.Println("\nPerformance Comparison:")
	fmt.Printf("%-15s %-18s %-18s\n", "Provider", "Latency (avg)", "Error Rate")
	fmt.Println(strings.Repeat("-", 51))

	for name, agent := range agents {
		metrics := agent.GetMetrics().Snapshot()
		fmt.Printf("%-15s %-18v %-18.1f%%\n",
			name,
			metrics.AverageLatency().Round(time.Millisecond),
			metrics.ErrorRate()*100)
	}

	fmt.Println("\nDECISION FRAMEWORK:")
	fmt.Println("  - Gemini Pro: Fastest but highest error rate")
	fmt.Println("  - Claude-3: Best balance of speed and reliability")
	fmt.Println("  - GPT-4: Slowest but most reliable")
	fmt.Println("  Choose based on your SLA requirements!")
}

// Example 3: Multi-agent pipeline monitoring
func example3PipelineMonitoring() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 3: Multi-Agent Pipeline Monitoring")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nUse case: Monitor a pipeline with multiple stages")

	// Create a pipeline of agents
	validator := middleware.NewMetricsDecorator(NewLLMAgent("validator", 50*time.Millisecond, 0))
	processor := middleware.NewMetricsDecorator(NewLLMAgent("processor", 200*time.Millisecond, 0))
	formatter := middleware.NewMetricsDecorator(NewLLMAgent("formatter", 30*time.Millisecond, 0))

	// Run requests through the pipeline
	fmt.Println("\nProcessing 10 requests through 3-stage pipeline...")
	ctx := context.Background()

	for i := 0; i < 10; i++ {
		msg := agenkit.NewMessage("user", fmt.Sprintf("Request %d", i))
		msg, _ = validator.Process(ctx, msg)
		msg, _ = processor.Process(ctx, msg)
		_, _ = formatter.Process(ctx, msg)
	}

	// Analyze each stage
	stages := []struct {
		name  string
		agent *middleware.MetricsDecorator
	}{
		{"Validator", validator},
		{"Processor", processor},
		{"Formatter", formatter},
	}

	var totalLatency time.Duration
	for _, stage := range stages {
		totalLatency += stage.agent.GetMetrics().AverageLatency()
	}

	fmt.Println("\nPipeline Performance Analysis:")
	fmt.Printf("%-15s %-15s %-15s\n", "Stage", "Avg Latency", "% of Total")
	fmt.Println(strings.Repeat("-", 45))

	for _, stage := range stages {
		metrics := stage.agent.GetMetrics().Snapshot()
		pct := float64(metrics.AverageLatency()) / float64(totalLatency) * 100
		fmt.Printf("%-15s %-15v %-15.1f%%\n",
			stage.name,
			metrics.AverageLatency().Round(time.Millisecond),
			pct)
	}

	fmt.Printf("\nTotal Pipeline Latency: %v\n", totalLatency.Round(time.Millisecond))

	fmt.Println("\nOPTIMIZATION STRATEGY:")
	fmt.Println("  1. Focus on the slowest stage (Processor = ~71% of latency)")
	fmt.Println("  2. Consider caching for repeated requests")
	fmt.Println("  3. Parallelize independent stages when possible")
}

func main() {
	// Seed random for demonstration
	rand.Seed(time.Now().UnixNano())

	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("METRICS MIDDLEWARE EXAMPLES FOR AGENKIT-GO")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nMetrics are the foundation of observable, reliable systems.")
	fmt.Println("These examples show why and how to instrument your agents.")

	// Run examples
	example1BasicMetrics()
	example2PerformanceComparison()
	example3PipelineMonitoring()

	// Summary
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("KEY TAKEAWAYS")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println(`
1. ALWAYS instrument production agents - metrics pay for themselves

2. Track the 4 golden signals:
   - Latency: How fast are requests?
   - Traffic: How many requests?
   - Errors: What's failing?
   - Saturation: How loaded is the system?

3. Use metrics for:
   - Real-time monitoring and alerting
   - Capacity planning and scaling decisions
   - Performance optimization (measure before and after)
   - Cost attribution in multi-tenant systems

4. Set up alerts based on:
   - Absolute thresholds (e.g., latency > 1s)
   - Rate of change (e.g., error rate up 50%)
   - Statistical anomalies (e.g., > 3 standard deviations)

5. Real-world tips:
   - Metrics add ~1-2% overhead but save 100x in debugging time
   - Use percentiles (P50, P95, P99) not just averages
   - Export metrics to monitoring systems (Prometheus, Datadog)
   - Set up dashboards before you need them

REMEMBER: You can't optimize what you don't measure!

Next steps:
- See retry_example.go for resilience patterns
- See composition examples for multi-agent patterns
	`)
}
