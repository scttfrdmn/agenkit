// Package main demonstrates the Conversational pattern for maintaining context.
//
// The Conversational pattern enables agents to maintain context across multiple
// turns of conversation with automatic history management, pruning, and persistence.
//
// This example shows:
//   - Creating conversational agents with history tracking
//   - Multi-turn conversations with context retention
//   - History pruning and capacity management
//   - Inspecting conversation history with GetHistory()
//   - Clearing history while preserving system prompts
//
// Run with: go run main.go
package main

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// MockLLMClient simulates an LLM that responds contextually based on conversation history.
//
// Complete has the same signature as every shipped adapter (adapter/llm), so
// swapping this for llm.NewAnthropicLLM(...) is a one-line change.
type MockLLMClient struct {
	scenario string
}

func (m *MockLLMClient) Complete(
	_ context.Context,
	messages []*agenkit.Message,
	_ ...agenkit.CallOption,
) (*agenkit.Message, error) {
	// Collect all message content for scenario detection
	var combined strings.Builder
	for _, msg := range messages {
		combined.WriteString(msg.ContentString())
		combined.WriteString(" ")
	}
	content := combined.String()

	var response string

	switch {
	case strings.Contains(content, "My name is Alice") && strings.Contains(content, "What's my name?"):
		response = "Your name is Alice, as you mentioned earlier!"
	case strings.Contains(content, "My name is Alice"):
		response = "Nice to meet you, Alice! How can I help you today?"
	case strings.Contains(content, "What's my name?"):
		response = "I don't recall you mentioning your name. Could you tell me?"
	case strings.Contains(content, "I like pizza") && strings.Contains(content, "What's my favorite food?"):
		response = "Based on our conversation, your favorite food is pizza!"
	case strings.Contains(content, "I like pizza"):
		response = "Pizza is delicious! Do you have a favorite type?"
	case strings.Contains(content, "favorite color") && strings.Contains(content, "blue"):
		response = "Blue is a great color! Is there anything else you'd like to talk about?"
	case strings.Contains(content, "What did we talk about"):
		switch {
		case strings.Contains(content, "color") && strings.Contains(content, "pizza"):
			response = "We talked about your favorite food (pizza) and your favorite color (blue)."
		case strings.Contains(content, "pizza"):
			response = "We talked about your favorite food, which is pizza."
		default:
			response = "We haven't talked about much yet. What would you like to discuss?"
		}
	case strings.Contains(content, "capital of France"):
		response = "The capital of France is Paris."
	case strings.Contains(content, "Who was the first president"):
		response = "The first President of the United States was George Washington."
	case strings.Contains(content, "previous question") || strings.Contains(content, "asked before"):
		switch {
		case strings.Contains(content, "France"):
			response = "You asked about the capital of France, which is Paris."
		case strings.Contains(content, "president"):
			response = "You asked about the first President of the United States, which was George Washington."
		default:
			response = "I remember your previous questions from our conversation."
		}
	case m.scenario == "customer_support":
		switch {
		case strings.Contains(content, "order") && strings.Contains(content, "123"):
			response = "I found your order #123. It's currently being processed and should ship tomorrow."
		case strings.Contains(content, "shipping"):
			response = "Based on your order #123, shipping will take 3-5 business days."
		default:
			response = "I'm here to help! What can I assist you with today?"
		}
	default:
		response = "I understand. What else would you like to know?"
	}

	return agenkit.NewMessage("assistant", response), nil
}

// Example 1: Basic conversation with name memory.
func exampleBasicConversation() error {
	fmt.Println("\n=== Example 1: Basic Conversation with Memory ===")

	llm := &MockLLMClient{scenario: "general"}

	agent, err := patterns.NewConversationalAgent(&patterns.ConversationalAgentConfig{
		LLMClient:     llm,
		MaxHistory:    10,
		SystemPrompt:  "You are a friendly assistant that remembers context.",
		IncludeSystem: true,
	})
	if err != nil {
		return err
	}

	fmt.Println("User: My name is Alice")
	response1, err := agent.Process(context.Background(), agenkit.NewMessage("user", "My name is Alice"))
	if err != nil {
		return err
	}
	fmt.Printf("Assistant: %s\n\n", response1.ContentString())

	fmt.Println("User: What's my name?")
	response2, err := agent.Process(context.Background(), agenkit.NewMessage("user", "What's my name?"))
	if err != nil {
		return err
	}
	fmt.Printf("Assistant: %s\n\n", response2.ContentString())

	fmt.Printf("History length: %d messages\n", agent.HistoryLength())

	return nil
}

// Example 2: Multi-topic conversation tracking.
func exampleMultiTopic() error {
	fmt.Println("\n=== Example 2: Multi-Topic Conversation ===")

	llm := &MockLLMClient{scenario: "general"}

	agent, err := patterns.NewConversationalAgent(&patterns.ConversationalAgentConfig{
		LLMClient:     llm,
		MaxHistory:    20,
		SystemPrompt:  "You are a helpful assistant.",
		IncludeSystem: true,
	})
	if err != nil {
		return err
	}

	turns := []string{
		"I like pizza",
		"My favorite color is blue",
		"What's my favorite food?",
		"What did we talk about so far?",
	}

	for _, userInput := range turns {
		fmt.Printf("User: %s\n", userInput)
		response, err := agent.Process(context.Background(), agenkit.NewMessage("user", userInput))
		if err != nil {
			return err
		}
		fmt.Printf("Assistant: %s\n\n", response.ContentString())
	}

	fmt.Printf("Current history length: %d\n", agent.HistoryLength())

	return nil
}

// Example 3: History pruning demonstration.
func exampleHistoryPruning() error {
	fmt.Println("\n=== Example 3: History Pruning ===")

	llm := &MockLLMClient{scenario: "general"}

	agent, err := patterns.NewConversationalAgent(&patterns.ConversationalAgentConfig{
		LLMClient:     llm,
		MaxHistory:    5, // Small history to demonstrate pruning
		SystemPrompt:  "System prompt",
		IncludeSystem: true,
	})
	if err != nil {
		return err
	}

	fmt.Println("Max history: 5 messages")
	fmt.Printf("Initial history (with system): %d\n\n", agent.HistoryLength())

	// Add several messages
	for i := 1; i <= 4; i++ {
		fmt.Printf("Turn %d: Sending message...\n", i)
		if _, err := agent.Process(context.Background(), agenkit.NewMessage("user", fmt.Sprintf("Message %d", i))); err != nil {
			return err
		}
		fmt.Printf("History length: %d\n\n", agent.HistoryLength())
	}

	fmt.Println("Final history:")
	history := agent.GetHistory()
	for i, msg := range history {
		content := msg.ContentString()
		if len(content) > 50 {
			content = content[:50] + "..."
		}
		fmt.Printf("  [%d] %s: %s\n", i, msg.Role, content)
	}

	return nil
}

// Example 4: History inspection demo using GetHistory().
func exampleHistoryInspection() error {
	fmt.Println("\n=== Example 4: History Inspection ===")

	llm := &MockLLMClient{scenario: "general"}

	agent, err := patterns.NewConversationalAgent(&patterns.ConversationalAgentConfig{
		LLMClient:     llm,
		MaxHistory:    10,
		IncludeSystem: false,
	})
	if err != nil {
		return err
	}

	fmt.Println("Starting conversation...")
	if _, err := agent.Process(context.Background(), agenkit.NewMessage("user", "What's the capital of France?")); err != nil {
		return err
	}
	if _, err := agent.Process(context.Background(), agenkit.NewMessage("user", "Who was the first president of the US?")); err != nil {
		return err
	}

	fmt.Printf("History length: %d\n\n", agent.HistoryLength())

	fmt.Println("Full conversation history:")
	history := agent.GetHistory()
	for i, msg := range history {
		content := msg.ContentString()
		if len(content) > 60 {
			content = content[:60] + "..."
		}
		fmt.Printf("  [%d] %s: %s\n", i, msg.Role, content)
	}

	return nil
}

// Example 5: Customer support conversation.
func exampleCustomerSupport() error {
	fmt.Println("\n=== Example 5: Customer Support Scenario ===")

	llm := &MockLLMClient{scenario: "customer_support"}

	agent, err := patterns.NewConversationalAgent(&patterns.ConversationalAgentConfig{
		LLMClient:     llm,
		MaxHistory:    15,
		SystemPrompt:  "You are a customer support agent. Be helpful and remember order details.",
		IncludeSystem: true,
	})
	if err != nil {
		return err
	}

	conversation := []string{
		"I need help with my order",
		"The order number is 123",
		"When will it ship?",
		"Thank you!",
	}

	for i, userInput := range conversation {
		fmt.Printf("User: %s\n", userInput)
		response, err := agent.Process(context.Background(), agenkit.NewMessage("user", userInput))
		if err != nil {
			return err
		}
		fmt.Printf("Support: %s\n\n", response.ContentString())

		if i == 1 {
			fmt.Println("[Agent remembered order number from context]")
		}
	}

	return nil
}

// Example 6: Clear history demonstration.
func exampleClearHistory() error {
	fmt.Println("\n=== Example 6: Clear History ===")

	llm := &MockLLMClient{scenario: "general"}

	agent, err := patterns.NewConversationalAgent(&patterns.ConversationalAgentConfig{
		LLMClient:     llm,
		MaxHistory:    10,
		SystemPrompt:  "You are a helpful assistant.",
		IncludeSystem: true,
	})
	if err != nil {
		return err
	}

	// Build up some history
	if _, err := agent.Process(context.Background(), agenkit.NewMessage("user", "My name is Bob")); err != nil {
		return err
	}
	if _, err := agent.Process(context.Background(), agenkit.NewMessage("user", "I like coffee")); err != nil {
		return err
	}

	fmt.Println("After conversation:")
	fmt.Printf("History length: %d\n\n", agent.HistoryLength())

	// Clear history but keep system prompt
	agent.ClearHistory(true)
	fmt.Println("After ClearHistory(keepSystem=true):")
	fmt.Printf("History length: %d (system prompt preserved)\n\n", agent.HistoryLength())

	// Try asking about previous context
	fmt.Println("User: What's my name?")
	response, err := agent.Process(context.Background(), agenkit.NewMessage("user", "What's my name?"))
	if err != nil {
		return err
	}
	fmt.Printf("Assistant: %s\n\n", response.ContentString())
	fmt.Println("[Agent doesn't remember because history was cleared]")

	return nil
}

func main() {
	fmt.Println("Conversational Pattern Examples")
	fmt.Println(strings.Repeat("=", 60))

	// Run all examples
	if err := exampleBasicConversation(); err != nil {
		log.Fatalf("Example 1 failed: %v", err)
	}

	if err := exampleMultiTopic(); err != nil {
		log.Fatalf("Example 2 failed: %v", err)
	}

	if err := exampleHistoryPruning(); err != nil {
		log.Fatalf("Example 3 failed: %v", err)
	}

	if err := exampleHistoryInspection(); err != nil {
		log.Fatalf("Example 4 failed: %v", err)
	}

	if err := exampleCustomerSupport(); err != nil {
		log.Fatalf("Example 5 failed: %v", err)
	}

	if err := exampleClearHistory(); err != nil {
		log.Fatalf("Example 6 failed: %v", err)
	}

	fmt.Println("\n" + strings.Repeat("=", 60))
	fmt.Println("All examples completed successfully!")
}
