/*
Parallel Composition Example

WHY USE PARALLEL COMPOSITION?
-----------------------------
1. Reduce Latency: Execute independent operations concurrently
2. Multiple Perspectives: Get diverse responses (ensemble, consensus)
3. A/B Testing: Compare different models/approaches simultaneously
4. Redundancy: Send same request to multiple services for reliability
5. Fan-out Search: Query multiple data sources simultaneously

WHEN TO USE:
- Independent operations (no data dependencies)
- Need consensus or voting from multiple agents
- A/B testing different models or prompts
- Querying multiple data sources (databases, APIs, search)
- Ensemble methods (combine multiple model outputs)

WHEN NOT TO USE:
- Operations have dependencies (use SequentialAgent)
- Need to preserve order of operations
- Resource constraints (limited API quota, memory, CPU)
- Single source of truth is required

TRADE-OFFS:
- Latency Reduction: Total time = slowest agent (not sum)
- Resource Usage: N agents = N× cost (API calls, memory, CPU)
- Complexity: Need aggregation logic, handle partial failures

Run with: go run agenkit-go/examples/composition/parallel_example.go
*/

package main

import (
	"context"
	"fmt"
	"math/rand"
	"strings"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
	"github.com/agenkit/agenkit-go/composition"
)

// SentimentAgent analyzes sentiment using a specific approach
type SentimentAgent struct {
	name     string
	approach string
}

func NewSentimentAgent(name, approach string) *SentimentAgent {
	return &SentimentAgent{name: name, approach: approach}
}

func (a *SentimentAgent) Name() string { return a.name }
func (a *SentimentAgent) Capabilities() []string { return []string{"sentiment_analysis"} }

func (a *SentimentAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Simulate different analysis latencies
	time.Sleep(time.Duration(50+rand.Intn(150)) * time.Millisecond)

	text := strings.ToLower(message.Content)
	var score float64
	var sentiment string

	// Different approaches give slightly different results
	switch a.approach {
	case "lexicon":
		// Keyword-based
		positive := strings.Count(text, "good") + strings.Count(text, "great") + strings.Count(text, "love")
		negative := strings.Count(text, "bad") + strings.Count(text, "hate") + strings.Count(text, "terrible")
		score = 0.5 + float64(positive-negative)/10.0
	case "ml_model":
		// Simulated ML model
		score = 0.5 + (rand.Float64()-0.5)*0.4
		if strings.Contains(text, "love") || strings.Contains(text, "great") {
			score += 0.3
		}
	default: // rule_based
		if strings.Contains(text, "!") {
			score = 0.8
		} else if strings.Contains(text, "?") {
			score = 0.5
		} else {
			score = 0.6
		}
	}

	if score > 0.6 {
		sentiment = "positive"
	} else if score < 0.4 {
		sentiment = "negative"
	} else {
		sentiment = "neutral"
	}

	return agenkit.NewMessage("agent", sentiment).
		WithMetadata("sentiment", sentiment).
		WithMetadata("score", score).
		WithMetadata("approach", a.approach), nil
}

// Example 1: Ensemble sentiment analysis with voting
func example1EnsembleVoting() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 1: Ensemble Voting")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nUse case: Combine multiple sentiment models for robust predictions")

	// Create ensemble of different approaches
	ensemble, _ := composition.NewParallelAgent("sentiment-ensemble",
		NewSentimentAgent("lexicon-analyzer", "lexicon"),
		NewSentimentAgent("ml-analyzer", "ml_model"),
		NewSentimentAgent("rule-analyzer", "rule_based"),
	)

	testTexts := []string{
		"I love this product! It's great!",
		"This is terrible. Very disappointed.",
		"It's okay, nothing special.",
	}

	ctx := context.Background()

	for _, text := range testTexts {
		fmt.Printf("\nText: '%s'\n", text)

		start := time.Now()
		result, err := ensemble.Process(ctx, agenkit.NewMessage("user", text))
		elapsed := time.Since(start)

		if err != nil {
			fmt.Printf("Error: %v\n", err)
			continue
		}

		fmt.Printf("Combined result (in %v):\n%s\n", elapsed.Round(time.Millisecond), result.Content)
	}

	fmt.Println("\nWHY PARALLEL ENSEMBLE?")
	fmt.Println("  - More robust than single model")
	fmt.Println("  - Reduces individual model bias")
	fmt.Println("  - Latency = slowest model (not sum of 3)")
	fmt.Println("  - Can detect when models disagree (low confidence)")
}

// SearchAgent searches a specific data source
type SearchAgent struct {
	name   string
	source string
}

func NewSearchAgent(name, source string) *SearchAgent {
	return &SearchAgent{name: name, source: source}
}

func (a *SearchAgent) Name() string { return a.name }
func (a *SearchAgent) Capabilities() []string { return []string{"search"} }

func (a *SearchAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Simulate different latencies per source
	latencies := map[string]time.Duration{
		"cache":    10 * time.Millisecond,
		"database": 50 * time.Millisecond,
		"api":      300 * time.Millisecond,
		"web":      500 * time.Millisecond,
	}
	time.Sleep(latencies[a.source])

	// Simulate search results
	resultCount := rand.Intn(4)
	results := make([]string, resultCount)
	for i := 0; i < resultCount; i++ {
		results[i] = fmt.Sprintf("%s result %d", strings.ToUpper(a.source), i+1)
	}

	content := fmt.Sprintf("Found %d results from %s", len(results), a.source)
	return agenkit.NewMessage("agent", content).
		WithMetadata("source", a.source).
		WithMetadata("results", results).
		WithMetadata("count", len(results)), nil
}

// Example 2: Multi-source search
func example2MultisourceSearch() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 2: Multi-Source Search")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nUse case: Fan-out search across multiple backends")

	// Create multi-source search
	search, _ := composition.NewParallelAgent("multi-search",
		NewSearchAgent("cache-search", "cache"),
		NewSearchAgent("db-search", "database"),
		NewSearchAgent("api-search", "api"),
		NewSearchAgent("web-search", "web"),
	)

	query := "agenkit framework"
	fmt.Printf("\nQuery: '%s'\n", query)
	fmt.Println("Searching: cache, database, API, web...")

	ctx := context.Background()
	start := time.Now()
	result, err := search.Process(ctx, agenkit.NewMessage("user", query))
	elapsed := time.Since(start)

	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}

	fmt.Printf("\nResult (completed in %v):\n%s\n", elapsed.Round(time.Millisecond), result.Content)

	fmt.Println("\nPERFORMANCE COMPARISON:")
	fmt.Printf("  Parallel:   %v (actual)\n", elapsed.Round(time.Millisecond))
	fmt.Printf("  Sequential: ~860ms (10 + 50 + 300 + 500)\n")
	fmt.Printf("  Speedup:    ~%.1fx faster\n", 860.0/float64(elapsed.Milliseconds()))
	fmt.Println("\n  Latency = max(all sources), not sum!")
}

// LLMAgent simulates an LLM with specific characteristics
type LLMAgent struct {
	name    string
	model   string
	latency time.Duration
	quality float64
}

func NewLLMAgent(name, model string, latency time.Duration, quality float64) *LLMAgent {
	return &LLMAgent{name: name, model: model, latency: latency, quality: quality}
}

func (a *LLMAgent) Name() string { return a.name }
func (a *LLMAgent) Capabilities() []string { return []string{"text_generation"} }

func (a *LLMAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(a.latency)

	var qualityDesc string
	if a.quality > 0.8 {
		qualityDesc = "(high quality, detailed)"
	} else if a.quality > 0.6 {
		qualityDesc = "(good quality)"
	} else {
		qualityDesc = "(basic quality)"
	}

	content := fmt.Sprintf("Response from %s %s", a.model, qualityDesc)
	return agenkit.NewMessage("agent", content).
		WithMetadata("model", a.model).
		WithMetadata("latency", a.latency).
		WithMetadata("quality", a.quality), nil
}

// Example 3: A/B testing different models
func example3ABTesting() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 3: A/B Testing Models")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nUse case: Compare different models simultaneously")

	// Test multiple models at once
	abTest, _ := composition.NewParallelAgent("ab-test",
		NewLLMAgent("gpt-4", "GPT-4", 500*time.Millisecond, 0.95),
		NewLLMAgent("gpt-3.5", "GPT-3.5-Turbo", 200*time.Millisecond, 0.75),
		NewLLMAgent("claude", "Claude-3", 300*time.Millisecond, 0.90),
		NewLLMAgent("llama", "Llama-3", 100*time.Millisecond, 0.70),
	)

	prompt := agenkit.NewMessage("user", "Explain quantum computing")

	fmt.Println("\nTesting 4 models in parallel...")
	ctx := context.Background()
	start := time.Now()
	result, err := abTest.Process(ctx, prompt)
	elapsed := time.Since(start)

	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}

	fmt.Printf("\nCompleted in %v (vs ~1.1s sequential)\n", elapsed.Round(time.Millisecond))
	fmt.Printf("\nCombined responses:\n%s\n", result.Content)

	fmt.Println("\nA/B TESTING BENEFITS:")
	fmt.Println("  - Get results from all models in parallel")
	fmt.Println("  - Compare quality, latency, cost simultaneously")
	fmt.Println("  - Make data-driven model selection decisions")
	fmt.Println("  - Can route production traffic based on results")
}

func main() {
	// Seed random for demonstration
	rand.Seed(time.Now().UnixNano())

	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("PARALLEL COMPOSITION EXAMPLES FOR AGENKIT-GO")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nParallel composition reduces latency and enables ensemble methods.")
	fmt.Println("Use it for independent operations that can run concurrently.")

	// Run examples
	example1EnsembleVoting()
	example2MultisourceSearch()
	example3ABTesting()

	// Summary
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("KEY TAKEAWAYS")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println(`
1. Use parallel composition when:
   - Operations are independent (no data dependencies)
   - Latency matters more than resource cost
   - Need consensus/voting from multiple sources
   - Comparing different approaches (A/B testing)
   - Redundancy improves reliability

2. Performance characteristics:
   - Latency = max(all agents), NOT sum
   - Resource usage = N× cost
   - Best speedup when agents have similar latency
   - Network I/O bound operations benefit most

3. Aggregation strategies:
   - Default: Combine all results
   - Custom: Implement voting, consensus, best-of-N
   - Handle partial failures gracefully

4. When NOT to use:
   - Operations have dependencies → SequentialAgent
   - Resource constraints (API quota, cost)
   - Serial execution is fast enough
   - Order matters

REAL-WORLD USE CASES:
✓ Multi-model ensemble for better accuracy
✓ Fan-out search across multiple databases
✓ A/B testing different models/prompts
✓ Redundant requests to unreliable services
✓ Parallel validation checks

TRADE-OFF SUMMARY:
✓ Pros: Lower latency, redundancy, consensus
✗ Cons: Higher resource cost, complexity
→ Choose when: Latency reduction > cost increase

Next steps:
- See sequential_example.go for pipeline patterns
- See fallback_example.go for reliability patterns
- See conditional_example.go for routing patterns
	`)
}
