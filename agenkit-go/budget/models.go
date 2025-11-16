// Package budget provides cost tracking and budget management for LLM usage.
//
// This package provides tools for tracking LLM costs and enforcing budgets,
// essential for managing expenses in long-running autonomous agents.
//
// Components:
//   - ModelPricing: Pricing data for LLM models (November 2025 rates)
//   - Cost: Single cost record
//   - CostTracker: Track costs per session, agent, and globally
//   - BudgetLimiter: Middleware for enforcing cost budgets
//   - ModelOptimizer: Route queries to models based on complexity/cost
package budget

import (
	"fmt"
	"log"
	"sync"
)

// ModelPricing provides pricing data for LLM models (as of November 2025).
//
// All prices are per 1 million tokens (input and output separately).
//
// Example:
//
//	pricing := NewModelPricing()
//	cost := pricing.Calculate("claude-sonnet-4", 10000, "input")
//	fmt.Printf("Cost: $%.4f\n", cost) // Cost: $0.0300
type ModelPricing struct {
	mu      sync.RWMutex
	pricing map[string]map[string]float64
}

// NewModelPricing creates a new ModelPricing instance with default rates.
func NewModelPricing() *ModelPricing {
	return &ModelPricing{
		pricing: map[string]map[string]float64{
			// OpenAI
			"gpt-4o":        {"input": 2.50, "output": 10.00},
			"gpt-4-turbo":   {"input": 10.00, "output": 30.00},
			"gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
			"o3":            {"input": 5.00, "output": 15.00},
			"o3-mini":       {"input": 1.00, "output": 3.00},

			// Anthropic
			"claude-opus-4":     {"input": 15.00, "output": 75.00},
			"claude-sonnet-4":   {"input": 3.00, "output": 15.00},
			"claude-sonnet-4.5": {"input": 3.00, "output": 15.00},
			"claude-haiku-3":    {"input": 0.25, "output": 1.25},

			// Google
			"gemini-2.0-flash-exp": {"input": 0.00, "output": 0.00}, // Free tier
			"gemini-pro":           {"input": 0.50, "output": 1.50},

			// Generic fallback
			"default": {"input": 0.01, "output": 0.01},
		},
	}
}

// Calculate computes the cost for a given number of tokens.
//
// Args:
//
//	model: Model identifier (e.g., "claude-sonnet-4")
//	tokens: Number of tokens
//	direction: "input" or "output"
//
// Returns:
//
//	Cost in dollars
//
// Example:
//
//	pricing := NewModelPricing()
//	cost := pricing.Calculate("claude-opus-4", 100000, "input")
//	fmt.Printf("$%.2f\n", cost) // $1.50
func (m *ModelPricing) Calculate(model string, tokens int, direction string) (float64, error) {
	if direction != "input" && direction != "output" {
		return 0, fmt.Errorf("direction must be 'input' or 'output', got: %s", direction)
	}

	m.mu.RLock()
	defer m.mu.RUnlock()

	modelPricing, exists := m.pricing[model]
	if !exists {
		log.Printf("WARNING: Unknown model '%s', using default pricing", model)
		modelPricing = m.pricing["default"]
	}

	pricePerMillion := modelPricing[direction]
	return (float64(tokens) / 1_000_000) * pricePerMillion, nil
}

// GetModelPricing returns pricing for a specific model.
//
// Args:
//
//	model: Model identifier
//
// Returns:
//
//	Map with "input" and "output" prices per 1M tokens, or nil if not found
//
// Example:
//
//	pricing := NewModelPricing()
//	rates := pricing.GetModelPricing("claude-sonnet-4")
//	fmt.Println(rates) // map[input:3.00 output:15.00]
func (m *ModelPricing) GetModelPricing(model string) map[string]float64 {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if pricing, exists := m.pricing[model]; exists {
		// Return a copy to prevent modification
		result := make(map[string]float64)
		for k, v := range pricing {
			result[k] = v
		}
		return result
	}
	return nil
}

// ListModels returns all supported model identifiers.
//
// Returns:
//
//	List of model identifiers (excluding "default")
//
// Example:
//
//	pricing := NewModelPricing()
//	models := pricing.ListModels()
//	fmt.Println(len(models)) // 12
func (m *ModelPricing) ListModels() []string {
	m.mu.RLock()
	defer m.mu.RUnlock()

	models := make([]string, 0, len(m.pricing))
	for model := range m.pricing {
		if model != "default" {
			models = append(models, model)
		}
	}
	return models
}

// UpdatePricing updates pricing for a model (for testing or custom deployments).
//
// Args:
//
//	model: Model identifier
//	inputPrice: Price per 1M input tokens
//	outputPrice: Price per 1M output tokens
//
// Example:
//
//	pricing := NewModelPricing()
//	pricing.UpdatePricing("custom-model", 1.0, 5.0)
//	cost, _ := pricing.Calculate("custom-model", 1000000, "output")
//	fmt.Printf("$%.2f\n", cost) // $5.00
func (m *ModelPricing) UpdatePricing(model string, inputPrice, outputPrice float64) {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.pricing[model] = map[string]float64{
		"input":  inputPrice,
		"output": outputPrice,
	}
	log.Printf("Updated pricing for %s: $%.2f/M input, $%.2f/M output", model, inputPrice, outputPrice)
}

// EstimateConversationCost estimates the cost for a multi-turn conversation.
//
// Args:
//
//	model: Model identifier
//	numTurns: Number of conversation turns
//	avgInputTokens: Average input tokens per turn
//	avgOutputTokens: Average output tokens per turn
//
// Returns:
//
//	Estimated total cost in dollars
//
// Example:
//
//	pricing := NewModelPricing()
//	cost, _ := pricing.EstimateConversationCost(
//	    "claude-sonnet-4",
//	    100,  // 100 turns
//	    1000, // 1000 input tokens per turn
//	    500,  // 500 output tokens per turn
//	)
//	fmt.Printf("Estimated: $%.2f\n", cost) // Estimated: $1.05
func (m *ModelPricing) EstimateConversationCost(model string, numTurns, avgInputTokens, avgOutputTokens int) (float64, error) {
	totalInput := numTurns * avgInputTokens
	totalOutput := numTurns * avgOutputTokens

	inputCost, err := m.Calculate(model, totalInput, "input")
	if err != nil {
		return 0, err
	}

	outputCost, err := m.Calculate(model, totalOutput, "output")
	if err != nil {
		return 0, err
	}

	return inputCost + outputCost, nil
}

// CompareModels compares costs across different models.
//
// Args:
//
//	models: List of model identifiers
//	inputTokens: Number of input tokens
//	outputTokens: Number of output tokens
//
// Returns:
//
//	Map from model to total cost
//
// Example:
//
//	pricing := NewModelPricing()
//	comparison, _ := pricing.CompareModels(
//	    []string{"claude-haiku-3", "claude-sonnet-4", "claude-opus-4"},
//	    100000, // input tokens
//	    50000,  // output tokens
//	)
//	// Returns: map[claude-haiku-3:0.09 claude-sonnet-4:1.05 claude-opus-4:5.25]
func (m *ModelPricing) CompareModels(models []string, inputTokens, outputTokens int) (map[string]float64, error) {
	costs := make(map[string]float64)

	for _, model := range models {
		inputCost, err := m.Calculate(model, inputTokens, "input")
		if err != nil {
			return nil, err
		}

		outputCost, err := m.Calculate(model, outputTokens, "output")
		if err != nil {
			return nil, err
		}

		costs[model] = inputCost + outputCost
	}

	return costs, nil
}
