/*
Sequential Composition Example

WHY USE SEQUENTIAL COMPOSITION?
-------------------------------
1. Separation of Concerns: Each agent does one thing well
2. Data Pipelines: Natural fit for ETL, data transformation workflows
3. Modularity: Easy to add/remove/reorder stages
4. Testability: Test each stage independently
5. Clarity: Pipeline structure makes data flow obvious

WHEN TO USE:
- Data transformation pipelines (ETL)
- Multi-stage content processing (translate → summarize → classify)
- Validation → processing → formatting workflows
- Request/response transformation chains

WHEN NOT TO USE:
- Independent operations that can run in parallel (use ParallelAgent)
- Conditional logic based on input (use ConditionalAgent)
- When any stage can satisfy the request (use FallbackAgent)

TRADE-OFFS:
- Simplicity & Clarity vs Parallelism
- Sequential latency (sum of all stages) vs Code clarity
- Predictable behavior vs Maximum performance

Run with: go run agenkit-go/examples/composition/sequential_example.go
*/

package main

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
	"github.com/agenkit/agenkit-go/composition"
)

// TranslationAgent translates text to English
type TranslationAgent struct{}

func (a *TranslationAgent) Name() string { return "translator" }
func (a *TranslationAgent) Capabilities() []string { return []string{"translation"} }

func (a *TranslationAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(100 * time.Millisecond) // Simulate processing

	text := message.Content
	lang := "English"

	// Simple detection
	if strings.Contains(text, "bonjour") || strings.Contains(text, "Bonjour") {
		text = strings.ReplaceAll(text, "Bonjour", "Hello")
		text = strings.ReplaceAll(text, "bonjour", "hello")
		lang = "French"
	} else if strings.Contains(text, "hola") || strings.Contains(text, "Hola") {
		text = strings.ReplaceAll(text, "Hola", "Hello")
		text = strings.ReplaceAll(text, "hola", "hello")
		lang = "Spanish"
	}

	return agenkit.NewMessage("agent", text).
		WithMetadata("source_language", lang).
		WithMetadata("translated", lang != "English"), nil
}

// SummarizationAgent summarizes text
type SummarizationAgent struct{}

func (a *SummarizationAgent) Name() string { return "summarizer" }
func (a *SummarizationAgent) Capabilities() []string { return []string{"summarization"} }

func (a *SummarizationAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(200 * time.Millisecond) // Simulate processing

	text := message.Content
	sentences := strings.Split(text, ".")
	summary := fmt.Sprintf("Summary: %d sentences", len(sentences))

	result := agenkit.NewMessage("agent", summary)
	result.Metadata["original_length"] = len(text)
	result.Metadata["summary_length"] = len(summary)

	// Preserve upstream metadata
	for k, v := range message.Metadata {
		if _, exists := result.Metadata[k]; !exists {
			result.Metadata[k] = v
		}
	}

	return result, nil
}

// SentimentAgent analyzes sentiment
type SentimentAgent struct{}

func (a *SentimentAgent) Name() string { return "sentiment" }
func (a *SentimentAgent) Capabilities() []string { return []string{"sentiment_analysis"} }

func (a *SentimentAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(50 * time.Millisecond) // Simulate processing

	text := strings.ToLower(message.Content)

	// Simple sentiment detection
	positive := []string{"good", "great", "excellent", "amazing", "wonderful"}
	negative := []string{"bad", "terrible", "awful", "horrible", "poor"}

	posCount := 0
	for _, word := range positive {
		if strings.Contains(text, word) {
			posCount++
		}
	}

	negCount := 0
	for _, word := range negative {
		if strings.Contains(text, word) {
			negCount++
		}
	}

	sentiment := "neutral"
	if posCount > negCount {
		sentiment = "positive"
	} else if negCount > posCount {
		sentiment = "negative"
	}

	result := agenkit.NewMessage("agent", fmt.Sprintf("%s [Sentiment: %s]", message.Content, sentiment))
	result.Metadata["sentiment"] = sentiment

	// Preserve upstream metadata
	for k, v := range message.Metadata {
		if _, exists := result.Metadata[k]; !exists {
			result.Metadata[k] = v
		}
	}

	return result, nil
}

// Example 1: Content processing pipeline
func example1ContentPipeline() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 1: Content Processing Pipeline")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nUse case: Process multi-language customer feedback")
	fmt.Println("Pipeline: Translation → Summarization → Sentiment Analysis")

	// Build pipeline
	pipeline, err := composition.NewSequentialAgent("content-processor",
		&TranslationAgent{},
		&SummarizationAgent{},
		&SentimentAgent{},
	)
	if err != nil {
		fmt.Printf("Error creating pipeline: %v\n", err)
		return
	}

	// Test with French input
	input := agenkit.NewMessage("user", "Bonjour. This product is amazing! The quality is excellent.")

	fmt.Printf("\nInput (French): %s\n", input.Content)

	ctx := context.Background()
	result, err := pipeline.Process(ctx, input)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}

	fmt.Printf("\nOutput: %s\n", result.Content)
	fmt.Println("\nMetadata:")
	fmt.Printf("  Source Language: %v\n", result.Metadata["source_language"])
	fmt.Printf("  Sentiment: %v\n", result.Metadata["sentiment"])

	fmt.Println("\nWHY SEQUENTIAL?")
	fmt.Println("  - Must translate BEFORE summarizing (order matters)")
	fmt.Println("  - Each stage depends on previous stage's output")
	fmt.Println("  - Clear data flow: raw → translated → summarized → analyzed")
}

// ValidationAgent validates input data
type ValidationAgent struct{}

func (a *ValidationAgent) Name() string { return "validator" }
func (a *ValidationAgent) Capabilities() []string { return []string{"validation"} }

func (a *ValidationAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	text := message.Content
	var errors []string

	if len(text) < 10 {
		errors = append(errors, "Text too short (min 10 chars)")
	}
	if len(text) > 1000 {
		errors = append(errors, "Text too long (max 1000 chars)")
	}
	if !strings.ContainsAny(text, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") {
		errors = append(errors, "Must contain letters")
	}

	if len(errors) > 0 {
		return agenkit.NewMessage("agent", fmt.Sprintf("VALIDATION FAILED: %s", strings.Join(errors, "; "))).
			WithMetadata("valid", false).
			WithMetadata("errors", errors), nil
	}

	return agenkit.NewMessage("agent", text).WithMetadata("valid", true), nil
}

// NormalizationAgent normalizes text format
type NormalizationAgent struct{}

func (a *NormalizationAgent) Name() string { return "normalizer" }
func (a *NormalizationAgent) Capabilities() []string { return []string{"normalization"} }

func (a *NormalizationAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Short-circuit if validation failed
	if valid, ok := message.Metadata["valid"].(bool); ok && !valid {
		return message, nil
	}

	// Normalize whitespace
	text := strings.Join(strings.Fields(message.Content), " ")
	text = strings.ToLower(text)

	result := agenkit.NewMessage("agent", text)
	result.Metadata["normalized"] = true

	// Preserve upstream metadata
	for k, v := range message.Metadata {
		if _, exists := result.Metadata[k]; !exists {
			result.Metadata[k] = v
		}
	}

	return result, nil
}

// Example 2: Data validation pipeline
func example2ValidationPipeline() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 2: Validation Pipeline")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nUse case: ETL pipeline with validation and normalization")
	fmt.Println("Pipeline: Validate → Normalize")

	pipeline, _ := composition.NewSequentialAgent("etl-pipeline",
		&ValidationAgent{},
		&NormalizationAgent{},
	)

	// Test valid input
	fmt.Println("\nTest 1: Valid input")
	validInput := agenkit.NewMessage("user", "  This is   VALID input   with  extra   spaces.  ")
	result, _ := pipeline.Process(context.Background(), validInput)
	fmt.Printf("  Input:  '%s'\n", validInput.Content)
	fmt.Printf("  Output: '%s'\n", result.Content)
	fmt.Printf("  Valid:  %v\n", result.Metadata["valid"])

	// Test invalid input
	fmt.Println("\nTest 2: Invalid input (too short)")
	invalidInput := agenkit.NewMessage("user", "Hi")
	result, _ = pipeline.Process(context.Background(), invalidInput)
	fmt.Printf("  Input:  '%s'\n", invalidInput.Content)
	fmt.Printf("  Output: '%s'\n", result.Content)
	fmt.Printf("  Valid:  %v\n", result.Metadata["valid"])

	fmt.Println("\nWHY SEQUENTIAL?")
	fmt.Println("  - Validation must happen FIRST (fail fast)")
	fmt.Println("  - Don't waste resources on invalid data")
	fmt.Println("  - Each stage checks metadata to short-circuit")
	fmt.Println("  - Clear separation: validate → normalize")
}

func main() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("SEQUENTIAL COMPOSITION EXAMPLES FOR AGENKIT-GO")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nSequential composition is the foundation of data pipelines.")
	fmt.Println("Use it when stages depend on each other's output.")

	// Run examples
	example1ContentPipeline()
	example2ValidationPipeline()

	// Summary
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("KEY TAKEAWAYS")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println(`
1. Use sequential composition when:
   - Stages depend on previous stage's output
   - Order of operations matters
   - Building data transformation pipelines
   - Need clear, linear data flow

2. Design principles:
   - Each agent does ONE thing well
   - Validate early (fail fast on bad input)
   - Use metadata to pass context between stages
   - Short-circuit on errors to avoid wasted work

3. Performance considerations:
   - Total latency = sum of all stages
   - Optimize the slowest stage first
   - Consider caching for repeated inputs
   - Move validation/filtering earlier

4. When NOT to use:
   - Independent operations → Use ParallelAgent
   - Conditional routing → Use ConditionalAgent
   - Need fallback options → Use FallbackAgent

5. Real-world patterns:
   - ETL: Extract → Transform → Load
   - Content: Moderate → Process → Format
   - API: Authenticate → Authorize → Execute → Format
   - ML: Preprocess → Predict → Postprocess

TRADE-OFF SUMMARY:
✓ Pros: Simple, clear, testable, composable
✗ Cons: Sequential latency, no parallelism
→ Choose when: Clarity and correctness > maximum throughput

Next steps:
- See parallel_example.go for concurrent execution
- See fallback_example.go for reliability patterns
- See conditional_example.go for routing patterns
	`)
}
