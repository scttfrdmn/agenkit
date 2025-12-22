// Package patterns provides reusable agent composition patterns.
//
// Router pattern implements conditional agent selection based on message
// classification. A classifier determines the intent/category, then routes
// the request to an appropriate specialist agent.
//
// Key concepts:
//   - Intent/category classification
//   - Conditional routing to specialists
//   - Single agent execution per request
//   - Dynamic agent selection based on input
//
// Performance characteristics:
//   - Time: O(classification + selected agent)
//   - Memory: O(1) - only one agent executes
//   - Efficient single-path execution
package patterns

import (
	"context"
	"fmt"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ClassifierAgent is responsible for determining routing decisions.
//
// The classifier analyzes the input message and returns a category/intent
// that determines which specialist agent should handle the request.
type ClassifierAgent interface {
	agenkit.Agent

	// Classify determines the category/intent for routing
	Classify(ctx context.Context, message *agenkit.Message) (string, error)
}

// RouterAgent routes messages to appropriate agents based on classification.
//
// The router uses a classifier to determine message intent/category, then
// delegates to the corresponding specialist agent. This enables efficient
// conditional processing without executing all agents.
//
// Example use cases:
//   - Customer service: route to billing, technical, account agents
//   - Content moderation: route to spam, abuse, quality agents
//   - Language routing: route to language-specific agents
//   - Skill-based routing: route to domain expert agents
//   - Intent-based chatbots: route to booking, info, support agents
//
// The router pattern is ideal when requests have clear categories and
// different agents handle different types of requests.
type RouterAgent struct {
	name       string
	classifier ClassifierAgent
	agents     map[string]agenkit.Agent
	defaultKey string
}

// RouterConfig configures a RouterAgent.
type RouterConfig struct {
	// Classifier determines which agent to route to
	Classifier ClassifierAgent
	// Agents maps categories to specialist agents
	Agents map[string]agenkit.Agent
	// DefaultKey specifies fallback agent when classification doesn't match (optional)
	DefaultKey string
}

// NewRouterAgent creates a new router agent.
//
// Parameters:
//   - config: Router configuration with classifier and agents
//
// The classifier's Classify method should return category strings that
// match keys in the agents map. If DefaultKey is specified, requests with
// unmatched categories will be routed to that agent instead of failing.
func NewRouterAgent(config *RouterConfig) (*RouterAgent, error) {
	if config == nil {
		return nil, fmt.Errorf("config is required")
	}
	if config.Classifier == nil {
		return nil, fmt.Errorf("classifier is required")
	}
	if len(config.Agents) == 0 {
		return nil, fmt.Errorf("at least one agent is required")
	}

	// Validate default key if provided
	if config.DefaultKey != "" {
		if _, ok := config.Agents[config.DefaultKey]; !ok {
			return nil, fmt.Errorf("default key '%s' not found in agents map", config.DefaultKey)
		}
	}

	return &RouterAgent{
		name:       "RouterAgent",
		classifier: config.Classifier,
		agents:     config.Agents,
		defaultKey: config.DefaultKey,
	}, nil
}

// Name returns the agent's identifier.
func (r *RouterAgent) Name() string {
	return r.name
}

// Capabilities returns the combined capabilities of all agents.
func (r *RouterAgent) Capabilities() []string {
	capMap := make(map[string]bool)

	// Add classifier capabilities
	for _, cap := range r.classifier.Capabilities() {
		capMap[cap] = true
	}

	// Add agent capabilities
	for _, agent := range r.agents {
		for _, cap := range agent.Capabilities() {
			capMap[cap] = true
		}
	}

	capabilities := make([]string, 0, len(capMap))
	for cap := range capMap {
		capabilities = append(capabilities, cap)
	}
	capabilities = append(capabilities, "router", "conditional", "classification")

	return capabilities
}

// Introspect returns introspection information for the router agent.
func (r *RouterAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    r.Name(),
		Capabilities: r.Capabilities(),
	}
}

// Process classifies the message and routes to appropriate agent.
//
// The process follows these steps:
//  1. Classification: Determine message category/intent
//  2. Route selection: Look up corresponding agent
//  3. Execution: Delegate to selected agent
//
// If classification fails, an error is returned. If the classified category
// doesn't match any agent and no default is configured, an error is returned.
//
// The final message includes metadata about the routing decision.
func (r *RouterAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if message == nil {
		return nil, fmt.Errorf("message cannot be nil")
	}

	// Step 1: Classify the message
	category, err := r.classifier.Classify(ctx, message)
	if err != nil {
		return nil, fmt.Errorf("classification failed: %w", err)
	}

	// Step 2: Select agent based on category
	agent, ok := r.agents[category]
	if !ok {
		// Try default agent if configured
		if r.defaultKey != "" {
			agent = r.agents[r.defaultKey]
			category = r.defaultKey // Update category to reflect actual routing
		} else {
			availableCategories := make([]string, 0, len(r.agents))
			for cat := range r.agents {
				availableCategories = append(availableCategories, cat)
			}
			return nil, fmt.Errorf("no agent found for category '%s' (available: %s)",
				category, strings.Join(availableCategories, ", "))
		}
	}

	// Step 3: Execute selected agent
	result, err := agent.Process(ctx, message)
	if err != nil {
		return nil, fmt.Errorf("agent '%s' (category: %s) failed: %w",
			agent.Name(), category, err)
	}

	// Add routing metadata
	if result.Metadata == nil {
		result.Metadata = make(map[string]interface{})
	}
	result.Metadata["routed_category"] = category
	result.Metadata["routed_agent"] = agent.Name()
	result.Metadata["available_routes"] = len(r.agents)

	return result, nil
}

// SimpleClassifier provides a basic classifier using keyword matching.
//
// This classifier uses simple string matching to determine categories.
// For production use, consider implementing a custom ClassifierAgent with
// ML-based classification or more sophisticated logic.
type SimpleClassifier struct {
	agent    agenkit.Agent
	keywords map[string][]string // category -> keywords
}

// NewSimpleClassifier creates a keyword-based classifier.
//
// Parameters:
//   - agent: Fallback agent for complex classifications
//   - keywords: Map of categories to keyword lists
func NewSimpleClassifier(agent agenkit.Agent, keywords map[string][]string) *SimpleClassifier {
	return &SimpleClassifier{
		agent:    agent,
		keywords: keywords,
	}
}

// Name returns the classifier's identifier.
func (c *SimpleClassifier) Name() string {
	return "SimpleClassifier"
}

// Capabilities returns the classifier's capabilities.
func (c *SimpleClassifier) Capabilities() []string {
	return append(c.agent.Capabilities(), "classification", "keyword-matching")
}

// Process handles direct message processing (delegates to underlying agent).
func (c *SimpleClassifier) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return c.agent.Process(ctx, message)
}

// Introspect returns introspection information for the classifier.
func (c *SimpleClassifier) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    c.Name(),
		Capabilities: c.Capabilities(),
	}
}

// Classify determines category using keyword matching.
func (c *SimpleClassifier) Classify(ctx context.Context, message *agenkit.Message) (string, error) {
	if message == nil {
		return "", fmt.Errorf("message cannot be nil")
	}

	content := strings.ToLower(message.Content)

	// Check each category's keywords
	maxMatches := 0
	bestCategory := ""

	for category, keywords := range c.keywords {
		matches := 0
		for _, keyword := range keywords {
			if strings.Contains(content, strings.ToLower(keyword)) {
				matches++
			}
		}

		if matches > maxMatches {
			maxMatches = matches
			bestCategory = category
		}
	}

	if bestCategory == "" {
		return "", fmt.Errorf("unable to classify message - no keyword matches found")
	}

	return bestCategory, nil
}

// LLMClassifier uses an LLM agent for classification.
//
// This classifier prompts an LLM to determine the category. The LLM is given
// a list of valid categories and must respond with one of them.
type LLMClassifier struct {
	agent      agenkit.Agent
	categories []string
	prompt     string
}

// NewLLMClassifier creates an LLM-based classifier.
//
// Parameters:
//   - agent: LLM agent for classification
//   - categories: List of valid category names
//   - prompt: Optional custom prompt template
func NewLLMClassifier(agent agenkit.Agent, categories []string) *LLMClassifier {
	if len(categories) == 0 {
		categories = []string{"general"}
	}

	prompt := fmt.Sprintf(`Classify the following message into one of these categories: %s

Reply with ONLY the category name, nothing else.

Message: `, strings.Join(categories, ", "))

	return &LLMClassifier{
		agent:      agent,
		categories: categories,
		prompt:     prompt,
	}
}

// Name returns the classifier's identifier.
func (c *LLMClassifier) Name() string {
	return "LLMClassifier"
}

// Capabilities returns the classifier's capabilities.
func (c *LLMClassifier) Capabilities() []string {
	return append(c.agent.Capabilities(), "classification", "llm-classification")
}

// Process handles direct message processing (delegates to underlying agent).
func (c *LLMClassifier) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return c.agent.Process(ctx, message)
}

// Introspect returns introspection information for the classifier.
func (c *LLMClassifier) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    c.Name(),
		Capabilities: c.Capabilities(),
	}
}

// Classify uses LLM to determine category.
func (c *LLMClassifier) Classify(ctx context.Context, message *agenkit.Message) (string, error) {
	if message == nil {
		return "", fmt.Errorf("message cannot be nil")
	}

	// Build classification prompt
	classificationMsg := agenkit.NewMessage("user", c.prompt+message.Content)

	// Get LLM classification
	result, err := c.agent.Process(ctx, classificationMsg)
	if err != nil {
		return "", fmt.Errorf("llm classification failed: %w", err)
	}

	category := strings.TrimSpace(result.Content)

	// Validate category is in allowed list
	for _, validCat := range c.categories {
		if strings.EqualFold(category, validCat) {
			return validCat, nil
		}
	}

	return "", fmt.Errorf("llm returned invalid category '%s' (valid: %s)",
		category, strings.Join(c.categories, ", "))
}
