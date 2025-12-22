package patterns

import (
	"context"
	"errors"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// mockClassifier implements ClassifierAgent for testing
type mockClassifier struct {
	name         string
	category     string
	classifyErr  error
	capabilities []string
}

func (m *mockClassifier) Name() string {
	return m.name
}

func (m *mockClassifier) Capabilities() []string {
	if m.capabilities != nil {
		return m.capabilities
	}
	return []string{"classification"}
}

func (m *mockClassifier) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *mockClassifier) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return agenkit.NewMessage("assistant", "classifier response"), nil
}

func (m *mockClassifier) Classify(ctx context.Context, message *agenkit.Message) (string, error) {
	if m.classifyErr != nil {
		return "", m.classifyErr
	}
	return m.category, nil
}

// TestRouterAgent_Constructor tests valid construction
func TestRouterAgent_Constructor(t *testing.T) {
	classifier := &mockClassifier{name: "classifier"}
	agents := map[string]agenkit.Agent{
		"billing":   &extendedMockAgent{name: "billing", response: "billing response"},
		"technical": &extendedMockAgent{name: "technical", response: "tech response"},
	}

	config := &RouterConfig{
		Classifier: classifier,
		Agents:     agents,
	}

	router, err := NewRouterAgent(config)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if router == nil {
		t.Fatal("expected non-nil RouterAgent")
	}
	if router.Name() != "RouterAgent" {
		t.Errorf("expected name 'RouterAgent', got '%s'", router.Name())
	}
}

// TestRouterAgent_ConstructorNilConfig tests error case with nil config
func TestRouterAgent_ConstructorNilConfig(t *testing.T) {
	_, err := NewRouterAgent(nil)
	if err == nil {
		t.Fatal("expected error for nil config")
	}
	if !strings.Contains(err.Error(), "config") {
		t.Errorf("expected 'config' error, got %v", err)
	}
}

// TestRouterAgent_ConstructorNilClassifier tests error case with nil classifier
func TestRouterAgent_ConstructorNilClassifier(t *testing.T) {
	config := &RouterConfig{
		Classifier: nil,
		Agents: map[string]agenkit.Agent{
			"agent": &extendedMockAgent{name: "agent"},
		},
	}

	_, err := NewRouterAgent(config)
	if err == nil {
		t.Fatal("expected error for nil classifier")
	}
	if !strings.Contains(err.Error(), "classifier") {
		t.Errorf("expected 'classifier' error, got %v", err)
	}
}

// TestRouterAgent_ConstructorEmptyAgents tests error case with no agents
func TestRouterAgent_ConstructorEmptyAgents(t *testing.T) {
	config := &RouterConfig{
		Classifier: &mockClassifier{name: "classifier"},
		Agents:     map[string]agenkit.Agent{},
	}

	_, err := NewRouterAgent(config)
	if err == nil {
		t.Fatal("expected error for empty agents")
	}
	if !strings.Contains(err.Error(), "at least one agent") {
		t.Errorf("expected 'at least one agent' error, got %v", err)
	}
}

// TestRouterAgent_ConstructorInvalidDefaultKey tests error case with invalid default key
func TestRouterAgent_ConstructorInvalidDefaultKey(t *testing.T) {
	config := &RouterConfig{
		Classifier: &mockClassifier{name: "classifier"},
		Agents: map[string]agenkit.Agent{
			"agent1": &extendedMockAgent{name: "agent1"},
		},
		DefaultKey: "nonexistent",
	}

	_, err := NewRouterAgent(config)
	if err == nil {
		t.Fatal("expected error for invalid default key")
	}
	if !strings.Contains(err.Error(), "default key") || !strings.Contains(err.Error(), "not found") {
		t.Errorf("expected 'default key not found' error, got %v", err)
	}
}

// TestRouterAgent_BasicProcess tests simple success case
func TestRouterAgent_BasicProcess(t *testing.T) {
	classifier := &mockClassifier{
		name:     "classifier",
		category: "billing",
	}

	agents := map[string]agenkit.Agent{
		"billing":   &extendedMockAgent{name: "billing", response: "billing handled"},
		"technical": &extendedMockAgent{name: "technical", response: "tech handled"},
	}

	config := &RouterConfig{
		Classifier: classifier,
		Agents:     agents,
	}

	router, err := NewRouterAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "I have a billing question")
	result, err := router.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Content != "billing handled" {
		t.Errorf("expected 'billing handled', got '%s'", result.Content)
	}
}

// TestRouterAgent_RoutingMetadata tests metadata tracking
func TestRouterAgent_RoutingMetadata(t *testing.T) {
	classifier := &mockClassifier{
		name:     "classifier",
		category: "support",
	}

	agents := map[string]agenkit.Agent{
		"support": &extendedMockAgent{name: "support_agent", response: "support response"},
		"sales":   &extendedMockAgent{name: "sales_agent", response: "sales response"},
	}

	config := &RouterConfig{
		Classifier: classifier,
		Agents:     agents,
	}

	router, err := NewRouterAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "help me")
	result, err := router.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Check routing metadata
	if result.Metadata["routed_category"] != "support" {
		t.Errorf("expected routed_category='support', got %v", result.Metadata["routed_category"])
	}
	if result.Metadata["routed_agent"] != "support_agent" {
		t.Errorf("expected routed_agent='support_agent', got %v", result.Metadata["routed_agent"])
	}
	if result.Metadata["available_routes"] != 2 {
		t.Errorf("expected available_routes=2, got %v", result.Metadata["available_routes"])
	}
}

// TestRouterAgent_ClassificationError tests error in classification
func TestRouterAgent_ClassificationError(t *testing.T) {
	classifier := &mockClassifier{
		name:        "classifier",
		classifyErr: errors.New("classification failed"),
	}

	agents := map[string]agenkit.Agent{
		"agent": &extendedMockAgent{name: "agent"},
	}

	config := &RouterConfig{
		Classifier: classifier,
		Agents:     agents,
	}

	router, err := NewRouterAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	_, err = router.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("expected error from classification failure")
	}
	if !strings.Contains(err.Error(), "classification failed") {
		t.Errorf("expected classification error, got: %v", err)
	}
}

// TestRouterAgent_UnknownCategoryNoDefault tests unknown category without default
func TestRouterAgent_UnknownCategoryNoDefault(t *testing.T) {
	classifier := &mockClassifier{
		name:     "classifier",
		category: "unknown_category",
	}

	agents := map[string]agenkit.Agent{
		"known1": &extendedMockAgent{name: "known1"},
		"known2": &extendedMockAgent{name: "known2"},
	}

	config := &RouterConfig{
		Classifier: classifier,
		Agents:     agents,
	}

	router, err := NewRouterAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	_, err = router.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("expected error for unknown category")
	}
	if !strings.Contains(err.Error(), "no agent found") {
		t.Errorf("expected 'no agent found' error, got: %v", err)
	}
	if !strings.Contains(err.Error(), "unknown_category") {
		t.Errorf("expected error to mention unknown_category, got: %v", err)
	}
}

// TestRouterAgent_UnknownCategoryWithDefault tests fallback to default agent
func TestRouterAgent_UnknownCategoryWithDefault(t *testing.T) {
	classifier := &mockClassifier{
		name:     "classifier",
		category: "unknown_category",
	}

	agents := map[string]agenkit.Agent{
		"specific": &extendedMockAgent{name: "specific", response: "specific response"},
		"default":  &extendedMockAgent{name: "default", response: "default response"},
	}

	config := &RouterConfig{
		Classifier: classifier,
		Agents:     agents,
		DefaultKey: "default",
	}

	router, err := NewRouterAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	result, err := router.Process(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should use default agent
	if result.Content != "default response" {
		t.Errorf("expected 'default response', got '%s'", result.Content)
	}

	// Metadata should reflect default routing
	if result.Metadata["routed_category"] != "default" {
		t.Errorf("expected routed_category='default', got %v", result.Metadata["routed_category"])
	}
}

// TestRouterAgent_AgentError tests error from routed agent
func TestRouterAgent_AgentError(t *testing.T) {
	classifier := &mockClassifier{
		name:     "classifier",
		category: "failing",
	}

	agents := map[string]agenkit.Agent{
		"failing": &extendedMockAgent{name: "failing", err: errors.New("agent error")},
	}

	config := &RouterConfig{
		Classifier: classifier,
		Agents:     agents,
	}

	router, err := NewRouterAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	_, err = router.Process(context.Background(), msg)

	if err == nil {
		t.Fatal("expected error from agent")
	}
	if !strings.Contains(err.Error(), "agent error") {
		t.Errorf("expected agent error, got: %v", err)
	}
	if !strings.Contains(err.Error(), "failing") {
		t.Errorf("expected error to mention category, got: %v", err)
	}
}

// TestRouterAgent_NilMessage tests nil message handling
func TestRouterAgent_NilMessage(t *testing.T) {
	classifier := &mockClassifier{name: "classifier"}
	agents := map[string]agenkit.Agent{
		"agent": &extendedMockAgent{name: "agent"},
	}

	config := &RouterConfig{
		Classifier: classifier,
		Agents:     agents,
	}

	router, err := NewRouterAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	_, err = router.Process(context.Background(), nil)
	if err == nil {
		t.Fatal("expected error for nil message")
	}
	if !strings.Contains(err.Error(), "cannot be nil") {
		t.Errorf("expected 'cannot be nil' error, got: %v", err)
	}
}

// TestRouterAgent_Capabilities tests combined capabilities
func TestRouterAgent_Capabilities(t *testing.T) {
	classifier := &mockClassifier{
		name:         "classifier",
		capabilities: []string{"text-classification"},
	}

	agents := map[string]agenkit.Agent{
		"agent1": &extendedMockAgent{name: "agent1", capabilities: []string{"cap1"}},
		"agent2": &extendedMockAgent{name: "agent2", capabilities: []string{"cap2"}},
	}

	config := &RouterConfig{
		Classifier: classifier,
		Agents:     agents,
	}

	router, err := NewRouterAgent(config)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	caps := router.Capabilities()

	expectedCaps := map[string]bool{
		"text-classification": true,
		"cap1":                true,
		"cap2":                true,
		"router":              true,
		"conditional":         true,
		"classification":      true,
	}

	if len(caps) != len(expectedCaps) {
		t.Errorf("expected %d capabilities, got %d: %v", len(expectedCaps), len(caps), caps)
	}
}

// TestSimpleClassifier_KeywordMatching tests SimpleClassifier keyword matching
func TestSimpleClassifier_KeywordMatching(t *testing.T) {
	baseAgent := &extendedMockAgent{name: "base"}
	keywords := map[string][]string{
		"billing":   {"invoice", "payment", "bill"},
		"technical": {"error", "bug", "crash"},
		"sales":     {"price", "quote", "purchase"},
	}

	classifier := NewSimpleClassifier(baseAgent, keywords)

	tests := []struct {
		content  string
		expected string
	}{
		{"I have an invoice question", "billing"},
		{"System crashed with an error", "technical"},
		{"What is the price?", "sales"},
	}

	for _, tt := range tests {
		msg := agenkit.NewMessage("user", tt.content)
		category, err := classifier.Classify(context.Background(), msg)
		if err != nil {
			t.Errorf("unexpected error for '%s': %v", tt.content, err)
			continue
		}
		if category != tt.expected {
			t.Errorf("for '%s': expected category '%s', got '%s'", tt.content, tt.expected, category)
		}
	}
}

// TestSimpleClassifier_NoMatch tests SimpleClassifier with no keyword match
func TestSimpleClassifier_NoMatch(t *testing.T) {
	baseAgent := &extendedMockAgent{name: "base"}
	keywords := map[string][]string{
		"category1": {"keyword1"},
	}

	classifier := NewSimpleClassifier(baseAgent, keywords)

	msg := agenkit.NewMessage("user", "unrelated content")
	_, err := classifier.Classify(context.Background(), msg)

	if err == nil {
		t.Fatal("expected error for no keyword match")
	}
	if !strings.Contains(err.Error(), "unable to classify") {
		t.Errorf("expected 'unable to classify' error, got: %v", err)
	}
}

// TestSimpleClassifier_NilMessage tests SimpleClassifier with nil message
func TestSimpleClassifier_NilMessage(t *testing.T) {
	baseAgent := &extendedMockAgent{name: "base"}
	keywords := map[string][]string{"cat": {"key"}}

	classifier := NewSimpleClassifier(baseAgent, keywords)

	_, err := classifier.Classify(context.Background(), nil)
	if err == nil {
		t.Fatal("expected error for nil message")
	}
	if !strings.Contains(err.Error(), "cannot be nil") {
		t.Errorf("expected 'cannot be nil' error, got: %v", err)
	}
}

// TestLLMClassifier_BasicClassification tests LLMClassifier
func TestLLMClassifier_BasicClassification(t *testing.T) {
	// Mock LLM that returns a category
	llm := &extendedMockAgent{
		name:     "llm",
		response: "technical",
	}

	categories := []string{"billing", "technical", "sales"}
	classifier := NewLLMClassifier(llm, categories)

	msg := agenkit.NewMessage("user", "system error")
	category, err := classifier.Classify(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if category != "technical" {
		t.Errorf("expected 'technical', got '%s'", category)
	}
}

// TestLLMClassifier_InvalidCategory tests LLMClassifier with invalid response
func TestLLMClassifier_InvalidCategory(t *testing.T) {
	llm := &extendedMockAgent{
		name:     "llm",
		response: "invalid_category",
	}

	categories := []string{"cat1", "cat2"}
	classifier := NewLLMClassifier(llm, categories)

	msg := agenkit.NewMessage("user", "test")
	_, err := classifier.Classify(context.Background(), msg)

	if err == nil {
		t.Fatal("expected error for invalid category")
	}
	if !strings.Contains(err.Error(), "invalid category") {
		t.Errorf("expected 'invalid category' error, got: %v", err)
	}
}

// TestLLMClassifier_LLMError tests LLMClassifier with LLM error
func TestLLMClassifier_LLMError(t *testing.T) {
	llm := &extendedMockAgent{
		name: "llm",
		err:  errors.New("llm error"),
	}

	classifier := NewLLMClassifier(llm, []string{"cat1"})

	msg := agenkit.NewMessage("user", "test")
	_, err := classifier.Classify(context.Background(), msg)

	if err == nil {
		t.Fatal("expected error from LLM")
	}
	if !strings.Contains(err.Error(), "llm classification failed") {
		t.Errorf("expected LLM error, got: %v", err)
	}
}
