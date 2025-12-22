// Package main demonstrates the Orchestration pattern for coordinating agent workflows.
//
// The Orchestration pattern enables different execution strategies for multiple agents:
// Sequential (pipeline), Parallel (concurrent), and Delegate (supervisor-based).
//
// This example shows:
//   - Sequential orchestration for pipelines (validate → process → format)
//   - Parallel orchestration for concurrent execution
//   - Composed patterns (sequential + parallel combinations)
//   - Result aggregation and metadata handling
//
// Run with: go run orchestration_pattern.go
package main

import (
	"context"
	"fmt"
	"log"
	"strings"
	"time"

	"golang.org/x/text/cases"
	"golang.org/x/text/language"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// ValidatorAgent validates input data
type ValidatorAgent struct{}

func (v *ValidatorAgent) Name() string {
	return "Validator"
}

func (v *ValidatorAgent) Capabilities() []string {
	return []string{"validation"}
}

func (v *ValidatorAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    v.Name(),
		Capabilities: v.Capabilities(),
	}
}

func (v *ValidatorAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	content := message.Content
	fmt.Println("   🔍 Validator: Checking input...")
	time.Sleep(50 * time.Millisecond)
	validated := fmt.Sprintf("✓ Validated: %s", content)
	return agenkit.NewMessage("assistant", validated), nil
}

// ProcessorAgent processes data
type ProcessorAgent struct{}

func (p *ProcessorAgent) Name() string {
	return "Processor"
}

func (p *ProcessorAgent) Capabilities() []string {
	return []string{"processing"}
}

func (p *ProcessorAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    p.Name(),
		Capabilities: p.Capabilities(),
	}
}

func (p *ProcessorAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	content := message.Content
	fmt.Println("   ⚙️  Processor: Processing data...")
	time.Sleep(50 * time.Millisecond)
	processed := fmt.Sprintf("⚙️  Processed: %s", content)
	return agenkit.NewMessage("assistant", processed), nil
}

// FormatterAgent formats output
type FormatterAgent struct{}

func (f *FormatterAgent) Name() string {
	return "Formatter"
}

func (f *FormatterAgent) Capabilities() []string {
	return []string{"formatting"}
}

func (f *FormatterAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    f.Name(),
		Capabilities: f.Capabilities(),
	}
}

func (f *FormatterAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	content := message.Content
	fmt.Println("   📝 Formatter: Formatting output...")
	time.Sleep(50 * time.Millisecond)
	formatted := fmt.Sprintf("📄 Formatted:\n   %s", content)
	return agenkit.NewMessage("assistant", formatted), nil
}

// ReviewerAgent provides reviews from different perspectives
type ReviewerAgent struct {
	perspective string
	icon        string
}

func (r *ReviewerAgent) Name() string {
	return fmt.Sprintf("Reviewer-%s", r.perspective)
}

func (r *ReviewerAgent) Capabilities() []string {
	return []string{"review", r.perspective}
}

func (r *ReviewerAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    r.Name(),
		Capabilities: r.Capabilities(),
	}
}

func (r *ReviewerAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	content := message.Content
	fmt.Printf("   %s Reviewer: Analyzing from %s perspective...\n", r.icon, r.perspective)
	time.Sleep(50 * time.Millisecond)

	var assessment string
	switch r.perspective {
	case "security":
		assessment = "Looks secure, no vulnerabilities detected"
	case "performance":
		assessment = "Efficient, good performance characteristics"
	case "usability":
		assessment = "User-friendly, intuitive design"
	default:
		assessment = "Review complete"
	}

	review := fmt.Sprintf("%s %s Review:\nInput: %s\nAssessment: %s",
		r.icon, cases.Title(language.Und).String(r.perspective), content, assessment)
	return agenkit.NewMessage("assistant", review), nil
}

// Example 1: Sequential pattern (pipeline)
func exampleSequentialPattern() error {
	fmt.Println("\n" + strings.Repeat("=", 60))
	fmt.Println("📋 Sequential Pattern: validator → processor → formatter")
	fmt.Println(strings.Repeat("=", 60))

	validator := &ValidatorAgent{}
	processor := &ProcessorAgent{}
	formatter := &FormatterAgent{}

	pipeline, err := patterns.NewSequentialPattern([]agenkit.Agent{validator, processor, formatter}, nil)
	if err != nil {
		return err
	}

	fmt.Println("\n➡️  Input: User registration data")
	message := agenkit.NewMessage("user", "User registration data")
	result, err := pipeline.Process(context.Background(), message)
	if err != nil {
		return err
	}

	fmt.Printf("\n✅ Final Output:\n%s\n", result.Content)

	return nil
}

// Example 2: Parallel pattern
func exampleParallelPattern() error {
	fmt.Println("\n\n" + strings.Repeat("=", 60))
	fmt.Println("📋 Parallel Pattern: Multiple reviewers in parallel")
	fmt.Println(strings.Repeat("=", 60))

	reviewerA := &ReviewerAgent{perspective: "security", icon: "🔒"}
	reviewerB := &ReviewerAgent{perspective: "performance", icon: "⚡"}
	reviewerC := &ReviewerAgent{perspective: "usability", icon: "🎨"}

	// Aggregator that returns first result and stores all in metadata
	aggregator := func(messages []*agenkit.Message) *agenkit.Message {
		if len(messages) == 0 {
			return agenkit.NewMessage("agent", "No results")
		}
		result := messages[0]
		result.WithMetadata("parallel_results", messages)
		return result
	}

	parallel, err := patterns.NewParallelPattern([]agenkit.Agent{reviewerA, reviewerB, reviewerC}, aggregator, nil)
	if err != nil {
		return err
	}

	fmt.Println("\n➡️  Input: Code changes for review")
	message := agenkit.NewMessage("user", "Code changes for review")
	result, err := parallel.Process(context.Background(), message)
	if err != nil {
		return err
	}

	fmt.Printf("\n✅ Primary Result (first reviewer):\n%s\n", result.Content)

	// Show all parallel results from metadata
	if parallelResults, ok := result.Metadata["parallel_results"].([]interface{}); ok {
		fmt.Println("\n📊 All Parallel Results:")
		for i, res := range parallelResults {
			if msg, ok := res.(*agenkit.Message); ok {
				fmt.Printf("\n   Result %d:\n", i+1)
				for _, line := range strings.Split(msg.Content, "\n") {
					fmt.Printf("      %s\n", line)
				}
			}
		}
	}

	return nil
}

// Example 3: Composed patterns (sequential of parallel)
func exampleComposedPattern() error {
	fmt.Println("\n\n" + strings.Repeat("=", 60))
	fmt.Println("📋 Composed Pattern: Sequential pipeline with parallel review")
	fmt.Println(strings.Repeat("=", 60))

	// Stage 1: sequential validation and processing
	stage1Validator := &ValidatorAgent{}
	stage1Processor := &ProcessorAgent{}
	stage1, err := patterns.NewSequentialPattern(
		[]agenkit.Agent{stage1Validator, stage1Processor},
		&patterns.SequentialPatternConfig{Name: "stage1_prep"},
	)
	if err != nil {
		return err
	}

	// Stage 2: parallel review
	stage2ReviewerA := &ReviewerAgent{perspective: "security", icon: "🔒"}
	stage2ReviewerB := &ReviewerAgent{perspective: "performance", icon: "⚡"}
	stage2ReviewerC := &ReviewerAgent{perspective: "usability", icon: "🎨"}

	// Aggregator that returns first result and stores all in metadata
	aggregator := func(messages []*agenkit.Message) *agenkit.Message {
		if len(messages) == 0 {
			return agenkit.NewMessage("agent", "No results")
		}
		result := messages[0]
		result.WithMetadata("parallel_results", messages)
		return result
	}

	stage2, err := patterns.NewParallelPattern(
		[]agenkit.Agent{stage2ReviewerA, stage2ReviewerB, stage2ReviewerC},
		aggregator,
		&patterns.ParallelPatternConfig{Name: "stage2_review"},
	)
	if err != nil {
		return err
	}

	// Stage 3: final formatting
	stage3 := &FormatterAgent{}

	// Compose into final pipeline
	composedPipeline, err := patterns.NewSequentialPattern([]agenkit.Agent{
		stage1,
		stage2,
		stage3,
	}, nil)
	if err != nil {
		return err
	}

	fmt.Println("\n➡️  Input: Feature implementation")
	message := agenkit.NewMessage("user", "Feature implementation")
	result, err := composedPipeline.Process(context.Background(), message)
	if err != nil {
		return err
	}

	fmt.Printf("\n✅ Final Composed Output:\n%s\n", result.Content)

	return nil
}

// Example 4: Error handling in pipelines
func exampleErrorHandling() error {
	fmt.Println("\n\n" + strings.Repeat("=", 60))
	fmt.Println("📋 Error Handling: Pipeline with early termination")
	fmt.Println(strings.Repeat("=", 60))

	// Create a simple pipeline
	validator := &ValidatorAgent{}
	processor := &ProcessorAgent{}

	pipeline, err := patterns.NewSequentialPattern([]agenkit.Agent{validator, processor}, nil)
	if err != nil {
		return err
	}

	fmt.Println("\n➡️  Input: Valid data")
	message := agenkit.NewMessage("user", "Valid data")
	result, err := pipeline.Process(context.Background(), message)
	if err != nil {
		fmt.Printf("❌ Error (expected): %v\n", err)
		return nil
	}

	fmt.Printf("\n✅ Success:\n%s\n", result.Content)
	fmt.Println("\n💡 Note: Errors in any stage will terminate the pipeline")

	return nil
}

func main() {
	fmt.Println("🎭 Orchestration Pattern Example")

	// Run all examples
	if err := exampleSequentialPattern(); err != nil {
		log.Fatalf("Sequential example failed: %v", err)
	}

	if err := exampleParallelPattern(); err != nil {
		log.Fatalf("Parallel example failed: %v", err)
	}

	if err := exampleComposedPattern(); err != nil {
		log.Fatalf("Composed example failed: %v", err)
	}

	if err := exampleErrorHandling(); err != nil {
		log.Fatalf("Error handling example failed: %v", err)
	}

	// Summary
	fmt.Println("\n\n" + strings.Repeat("=", 60))
	fmt.Println("✨ Orchestration examples complete!")
	fmt.Println("\n💡 Key takeaways:")
	fmt.Println("   - Sequential: Simple pipelines, output → input chaining")
	fmt.Println("   - Parallel: Concurrent execution, aggregate results")
	fmt.Println("   - Composable: Patterns can contain other patterns")
	fmt.Println("   - Error handling: Failures propagate through pipeline")
	fmt.Println()
	fmt.Println("🎯 When to use Orchestration:")
	fmt.Println("   - Multi-stage data processing pipelines")
	fmt.Println("   - Concurrent operations on same input")
	fmt.Println("   - Complex workflows requiring composition")
	fmt.Println("   - Systems needing predictable execution order")
}
