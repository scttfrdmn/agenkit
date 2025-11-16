package budget

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ComplexityDetector is the interface for detecting query complexity.
//
// Implementations analyze conversation messages to determine if a query is:
//   - "simple": Basic questions, greetings, short requests
//   - "medium": Standard questions requiring some thought
//   - "complex": Deep analysis, reasoning, multi-step problems
type ComplexityDetector interface {
	// Detect analyzes messages and returns complexity level.
	//
	// Args:
	//   ctx: Context
	//   messages: Conversation messages
	//
	// Returns:
	//   Complexity level: "simple", "medium", or "complex"
	Detect(ctx context.Context, messages []agenkit.Message) (string, error)
}

// HeuristicComplexityDetector detects complexity using heuristics.
//
// Factors:
//   - Query length (longer = more complex)
//   - Keywords (reasoning, analysis, comparison = complex)
//   - History length (more context = more complex)
//
// Example:
//
//	detector := NewHeuristicComplexityDetector(500, 10)
//	complexity, _ := detector.Detect(ctx, messages)
//	fmt.Println(complexity) // "simple", "medium", or "complex"
type HeuristicComplexityDetector struct {
	longQueryThreshold   int
	longHistoryThreshold int
}

var complexKeywords = []string{
	"analyze", "compare", "reasoning", "explain why",
	"step by step", "think through", "evaluate",
	"pros and cons", "trade-offs", "implications",
	"in detail", "comprehensive", "thorough",
}

// NewHeuristicComplexityDetector creates a new heuristic-based detector.
//
// Args:
//
//	longQueryThreshold: Character count threshold for long queries (default: 500)
//	longHistoryThreshold: Message count threshold for long history (default: 10)
//
// Example:
//
//	detector := NewHeuristicComplexityDetector(500, 10)
func NewHeuristicComplexityDetector(longQueryThreshold, longHistoryThreshold int) *HeuristicComplexityDetector {
	return &HeuristicComplexityDetector{
		longQueryThreshold:   longQueryThreshold,
		longHistoryThreshold: longHistoryThreshold,
	}
}

// Detect analyzes messages using heuristics to determine complexity.
func (h *HeuristicComplexityDetector) Detect(ctx context.Context, messages []agenkit.Message) (string, error) {
	if len(messages) == 0 {
		return "simple", nil
	}

	latest := messages[len(messages)-1].Content
	latestLower := strings.ToLower(latest)

	// Check for complex keywords
	hasComplexKeywords := false
	for _, keyword := range complexKeywords {
		if strings.Contains(latestLower, keyword) {
			hasComplexKeywords = true
			break
		}
	}

	// Check query length
	isLongQuery := len(latest) > h.longQueryThreshold

	// Check history length
	isLongHistory := len(messages) > h.longHistoryThreshold

	// Determine complexity
	if isLongQuery || hasComplexKeywords {
		return "complex", nil
	} else if isLongHistory {
		return "medium", nil
	}

	return "simple", nil
}

// LLMClient is the interface for LLM clients used by complexity detection.
type LLMClient interface {
	Complete(ctx context.Context, messages []agenkit.Message, kwargs map[string]interface{}) (*agenkit.Message, error)
}

// LLMBasedComplexityDetector uses an LLM to analyze query complexity.
//
// More accurate than heuristics but adds latency and cost.
// Uses a cheap LLM (like Haiku or GPT-3.5) to classify complexity.
//
// Example:
//
//	detector := NewLLMBasedComplexityDetector(cheapLLMClient)
//	complexity, _ := detector.Detect(ctx, messages)
type LLMBasedComplexityDetector struct {
	llm LLMClient
}

// NewLLMBasedComplexityDetector creates a new LLM-based detector.
//
// Args:
//
//	llm: LLM client with Complete() method
//
// Example:
//
//	detector := NewLLMBasedComplexityDetector(haikuClient)
func NewLLMBasedComplexityDetector(llm LLMClient) *LLMBasedComplexityDetector {
	return &LLMBasedComplexityDetector{
		llm: llm,
	}
}

// Detect analyzes messages using an LLM to determine complexity.
func (l *LLMBasedComplexityDetector) Detect(ctx context.Context, messages []agenkit.Message) (string, error) {
	if len(messages) == 0 {
		return "simple", nil
	}

	latest := messages[len(messages)-1].Content

	prompt := fmt.Sprintf(`Analyze the following query and classify its complexity:

Query: "%s"

Classify as:
- "simple": Basic questions, greetings, short requests
- "medium": Standard questions requiring some thought
- "complex": Deep analysis, reasoning, multi-step problems

Respond with only one word: simple, medium, or complex.`, latest)

	response, err := l.llm.Complete(ctx, []agenkit.Message{{Role: "user", Content: prompt}}, nil)
	if err != nil {
		return "medium", err
	}

	complexity := strings.ToLower(strings.TrimSpace(response.Content))

	if complexity != "simple" && complexity != "medium" && complexity != "complex" {
		log.Printf("WARNING: Invalid complexity from LLM: %s, defaulting to medium", complexity)
		return "medium", nil
	}

	return complexity, nil
}

// ModelOptimizer intelligently routes requests to models based on complexity.
//
// Strategy:
//   - Simple queries → Cheap model (Haiku, GPT-3.5)
//   - Medium queries → Mid-tier (Sonnet 4, GPT-4)
//   - Complex queries → Expensive (Opus 4, o3)
//
// Example:
//
//	optimizer := NewModelOptimizer(
//	    "claude-haiku-3",
//	    "claude-sonnet-4",
//	    "claude-opus-4",
//	    map[string]LLMClient{
//	        "claude-haiku-3": haikuClient,
//	        "claude-sonnet-4": sonnetClient,
//	        "claude-opus-4": opusClient,
//	    },
//	    nil, // Uses heuristic detector
//	)
//	response, _ := optimizer.Complete(ctx, messages, nil)
//	fmt.Println(response.Metadata["selected_model"])
type ModelOptimizer struct {
	cheapModel     string
	mediumModel    string
	expensiveModel string
	llmClients     map[string]LLMClient
	detector       ComplexityDetector
}

// NewModelOptimizer creates a new model optimizer.
//
// Args:
//
//	cheapModel: Model for simple queries (e.g., "claude-haiku-3")
//	mediumModel: Model for medium queries (e.g., "claude-sonnet-4")
//	expensiveModel: Model for complex queries (e.g., "claude-opus-4")
//	llmClients: Map from model names to LLM clients
//	detector: Complexity detector (nil = use heuristic detector)
//
// Example:
//
//	optimizer := NewModelOptimizer(
//	    "claude-haiku-3",
//	    "claude-sonnet-4",
//	    "claude-opus-4",
//	    map[string]LLMClient{...},
//	    nil,
//	)
func NewModelOptimizer(
	cheapModel, mediumModel, expensiveModel string,
	llmClients map[string]LLMClient,
	detector ComplexityDetector,
) (*ModelOptimizer, error) {
	// Validate clients
	for _, model := range []string{cheapModel, mediumModel, expensiveModel} {
		if _, ok := llmClients[model]; !ok {
			return nil, fmt.Errorf("LLM client for %s not provided", model)
		}
	}

	// Use heuristic detector if none provided
	if detector == nil {
		detector = NewHeuristicComplexityDetector(500, 10)
	}

	return &ModelOptimizer{
		cheapModel:     cheapModel,
		mediumModel:    mediumModel,
		expensiveModel: expensiveModel,
		llmClients:     llmClients,
		detector:       detector,
	}, nil
}

// Complete routes to appropriate model based on complexity.
//
// Args:
//
//	ctx: Context
//	messages: Conversation messages
//	kwargs: Additional arguments for LLM
//
// Returns:
//
//	Response message with metadata:
//	  - selected_model: Model that was used
//	  - complexity: Detected complexity level
//	  - routing_reason: Why this model was selected
//
// Example:
//
//	response, _ := optimizer.Complete(ctx, messages, nil)
//	fmt.Printf("Used %s for %s query\n",
//	    response.Metadata["selected_model"],
//	    response.Metadata["complexity"])
func (m *ModelOptimizer) Complete(ctx context.Context, messages []agenkit.Message, kwargs map[string]interface{}) (*agenkit.Message, error) {
	// Detect complexity
	complexity, err := m.detector.Detect(ctx, messages)
	if err != nil {
		log.Printf("WARNING: Complexity detection failed: %v, defaulting to medium", err)
		complexity = "medium"
	}

	// Select model
	var modelName string
	var reason string

	switch complexity {
	case "simple":
		modelName = m.cheapModel
		reason = "Simple query, using cheap model"
	case "medium":
		modelName = m.mediumModel
		reason = "Medium complexity, using mid-tier model"
	case "complex":
		modelName = m.expensiveModel
		reason = "Complex query, using expensive model"
	default:
		modelName = m.mediumModel
		reason = "Unknown complexity, using mid-tier model"
	}

	log.Printf("INFO: Routing to %s: %s", modelName, reason)

	// Get LLM client
	llm := m.llmClients[modelName]

	// Complete
	response, err := llm.Complete(ctx, messages, kwargs)
	if err != nil {
		return nil, err
	}

	// Add routing metadata
	if response.Metadata == nil {
		response.Metadata = make(map[string]interface{})
	}
	response.Metadata["selected_model"] = modelName
	response.Metadata["complexity"] = complexity
	response.Metadata["routing_reason"] = reason

	return response, nil
}

// CompleteWithFallback completes with automatic fallback to cheaper models.
//
// Tries expensive → medium → cheap until successful.
//
// Args:
//
//	ctx: Context
//	messages: Conversation messages
//	maxAttempts: Maximum fallback attempts
//	kwargs: Additional arguments
//
// Returns:
//
//	Response message
//
// Example:
//
//	response, _ := optimizer.CompleteWithFallback(ctx, messages, 3, nil)
func (m *ModelOptimizer) CompleteWithFallback(ctx context.Context, messages []agenkit.Message, maxAttempts int, kwargs map[string]interface{}) (*agenkit.Message, error) {
	// Detect complexity
	complexity, err := m.detector.Detect(ctx, messages)
	if err != nil {
		log.Printf("WARNING: Complexity detection failed: %v, defaulting to medium", err)
		complexity = "medium"
	}

	// Determine fallback order based on complexity
	var models []string
	switch complexity {
	case "complex":
		models = []string{m.expensiveModel, m.mediumModel, m.cheapModel}
	case "medium":
		models = []string{m.mediumModel, m.cheapModel}
	case "simple":
		models = []string{m.cheapModel}
	default:
		models = []string{m.mediumModel, m.cheapModel}
	}

	var lastError error

	for i, modelName := range models {
		if i >= maxAttempts {
			break
		}

		llm, ok := m.llmClients[modelName]
		if !ok {
			continue
		}

		response, err := llm.Complete(ctx, messages, kwargs)
		if err != nil {
			log.Printf("WARNING: Failed with %s: %v", modelName, err)
			lastError = err
			continue
		}

		// Add metadata
		if response.Metadata == nil {
			response.Metadata = make(map[string]interface{})
		}
		response.Metadata["selected_model"] = modelName
		response.Metadata["complexity"] = complexity
		response.Metadata["fallback_attempt"] = i + 1
		if i > 0 {
			response.Metadata["fallback_reason"] = "Budget constraint or error"
		}

		return response, nil
	}

	// All models failed
	if lastError != nil {
		return nil, lastError
	}
	return nil, fmt.Errorf("all model attempts failed")
}

// GetModelForComplexity returns the model name for a given complexity level.
//
// Args:
//
//	complexity: "simple", "medium", or "complex"
//
// Returns:
//
//	Model name
//
// Example:
//
//	model := optimizer.GetModelForComplexity("complex")
//	fmt.Println(model) // "claude-opus-4"
func (m *ModelOptimizer) GetModelForComplexity(complexity string) (string, error) {
	switch complexity {
	case "simple":
		return m.cheapModel, nil
	case "medium":
		return m.mediumModel, nil
	case "complex":
		return m.expensiveModel, nil
	default:
		return "", fmt.Errorf("unknown complexity: %s", complexity)
	}
}

// EstimateCost estimates cost for different models.
//
// Args:
//
//	ctx: Context
//	messages: Conversation messages (for complexity detection)
//	inputTokens: Estimated input tokens
//	outputTokens: Estimated output tokens
//
// Returns:
//
//	Map from model name to estimated cost
//
// Example:
//
//	estimates, _ := optimizer.EstimateCost(ctx, messages, 1000, 500)
//	for model, cost := range estimates {
//	    fmt.Printf("%s: $%.4f\n", model, cost)
//	}
func (m *ModelOptimizer) EstimateCost(ctx context.Context, messages []agenkit.Message, inputTokens, outputTokens int) (map[string]float64, error) {
	pricing := NewModelPricing()

	estimates := make(map[string]float64)

	for _, modelName := range []string{m.cheapModel, m.mediumModel, m.expensiveModel} {
		inputCost, err := pricing.Calculate(modelName, inputTokens, "input")
		if err != nil {
			return nil, err
		}

		outputCost, err := pricing.Calculate(modelName, outputTokens, "output")
		if err != nil {
			return nil, err
		}

		estimates[modelName] = inputCost + outputCost
	}

	return estimates, nil
}
