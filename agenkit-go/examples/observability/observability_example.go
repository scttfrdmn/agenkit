// Example demonstrating OpenTelemetry observability features in Agenkit Go.
//
// Shows distributed tracing, metrics collection, and structured logging
// with trace correlation across multiple agents.
package main

import (
	"context"
	"fmt"
	"log/slog"
	"time"

	"github.com/agenkit/agenkit-go/observability"
)

// SimpleAgent is a simple agent for demonstration.
type SimpleAgent struct {
	name   string
	logger *slog.Logger
}

// NewSimpleAgent creates a new simple agent.
func NewSimpleAgent(name string) *SimpleAgent {
	return &SimpleAgent{
		name:   name,
		logger: observability.GetLoggerWithTrace(),
	}
}

// Name returns the agent name.
func (a *SimpleAgent) Name() string {
	return a.name
}

// Capabilities returns the agent capabilities.
func (a *SimpleAgent) Capabilities() []string {
	return []string{"process"}
}

// Process processes a message.
func (a *SimpleAgent) Process(ctx context.Context, message *observability.Message) (*observability.Message, error) {
	a.logger.InfoContext(ctx, fmt.Sprintf("Agent %s processing message", a.name),
		slog.String("agent", a.name),
		slog.Int("content_length", len(message.Content)),
	)

	// Simulate some processing
	time.Sleep(100 * time.Millisecond)

	responseContent := fmt.Sprintf("Processed by %s: %s", a.name, message.Content)

	a.logger.InfoContext(ctx, fmt.Sprintf("Agent %s completed processing", a.name),
		slog.String("agent", a.name),
		slog.Int("response_length", len(responseContent)),
	)

	return &observability.Message{
		Role:    "agent",
		Content: responseContent,
		Metadata: map[string]interface{}{
			"processed_by": a.name,
		},
	}, nil
}

func main() {
	fmt.Println("=== Agenkit Go Observability Example ===\n")

	// Initialize OpenTelemetry
	fmt.Println("1. Initializing OpenTelemetry...")
	tp, err := observability.InitTracing(
		"agenkit-go-example",
		"",   // No OTLP endpoint for demo
		true, // Export traces to console
	)
	if err != nil {
		panic(err)
	}
	defer func() {
		if err := observability.Shutdown(context.Background()); err != nil {
			fmt.Printf("Error shutting down tracer: %v\n", err)
		}
	}()

	mp, err := observability.InitMetrics(
		"agenkit-go-example",
		8002, // Prometheus metrics on port 8002
	)
	if err != nil {
		panic(err)
	}
	defer func() {
		if err := observability.ShutdownMetrics(context.Background()); err != nil {
			fmt.Printf("Error shutting down metrics: %v\n", err)
		}
	}()

	// Configure structured logging
	observability.ConfigureLogging(
		slog.LevelInfo,
		true, // Structured JSON logging
		true, // Include trace context
	)

	fmt.Println("✓ Tracing, metrics, and logging initialized\n")
	fmt.Printf("  TracerProvider: %T\n", tp)
	fmt.Printf("  MeterProvider: %T\n\n", mp)

	// Create agents with observability
	fmt.Println("2. Creating agents with tracing and metrics...")
	baseAgent1 := NewSimpleAgent("agent-1")
	baseAgent2 := NewSimpleAgent("agent-2")

	// Wrap with tracing
	tracedAgent1 := observability.NewTracingMiddleware(baseAgent1, "")
	tracedAgent2 := observability.NewTracingMiddleware(baseAgent2, "")

	// Wrap with metrics
	agent1, err := observability.NewMetricsMiddleware(tracedAgent1)
	if err != nil {
		panic(err)
	}
	agent2, err := observability.NewMetricsMiddleware(tracedAgent2)
	if err != nil {
		panic(err)
	}

	fmt.Println("✓ Agents wrapped with observability middleware\n")

	// Process messages through agent chain
	fmt.Println("3. Processing messages through agents...")
	ctx := context.Background()
	message := &observability.Message{
		Role:    "user",
		Content: "Hello from the Go observability example!",
	}

	// Process through agent1
	fmt.Printf("   → Sending to %s...\n", agent1.Name())
	response1, err := agent1.Process(ctx, message)
	if err != nil {
		panic(err)
	}

	// Process through agent2 with propagated trace context
	fmt.Printf("   → Sending to %s...\n", agent2.Name())
	response2, err := agent2.Process(ctx, response1)
	if err != nil {
		panic(err)
	}

	fmt.Printf("\n   ✓ Final response: %s\n\n", response2.Content)

	// Show observability features
	fmt.Println("4. Observability Features:")
	fmt.Println("   • Distributed traces: Check console output above")
	fmt.Println("   • Trace context propagated across agents")
	fmt.Println("   • Structured logs include trace_id and span_id")
	fmt.Println("   • Metrics collected for requests, errors, and latency")
	fmt.Println("   • Prometheus metrics available at http://localhost:8002/metrics\n")

	fmt.Println("5. View Traces and Metrics:")
	fmt.Println("   • Traces exported to console (see above)")
	fmt.Println("   • Metrics: curl http://localhost:8002/metrics")
	fmt.Println("   • Logs: Check structured JSON logs above\n")

	fmt.Println("=== Example Complete ===")

	// Wait a moment for exporters to flush
	time.Sleep(2 * time.Second)
}
