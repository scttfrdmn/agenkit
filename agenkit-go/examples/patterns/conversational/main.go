// Package main demonstrates the Conversational pattern for maintaining context.
//
// The Conversational pattern enables agents to maintain context across multiple
// turns of conversation with automatic history management, pruning, and persistence.
//
// This example shows:
//   - Creating conversational agents with history tracking
//   - Multi-turn conversations with context retention
//   - History pruning and capacity management
//   - Exporting and importing conversation history
//   - Clearing history while preserving system prompts
//
// Run with: go run conversational_pattern.go
package main

import (
	"context"
	"fmt"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// MockLLMAgent simulates an LLM that responds contextually based on conversation history
type MockLLMAgent struct {
	scenario string
}

func (m *MockLLMAgent) Name() string {
	return "MockLLM"
}

func (m *MockLLMAgent) Capabilities() []string {
	return []string{"chat"}
}

func (m *MockLLMAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	content := message.Content

	var response string

	// Parse conversation history from context
	if strings.Contains(content, "My name is Alice") && strings.Contains(content, "What's my name?") {
		response = "Your name is Alice, as you mentioned earlier!"
	} else if strings.Contains(content, "My name is Alice") {
		response = "Nice to meet you, Alice! How can I help you today?"
	} else if strings.Contains(content, "What's my name?") {
		response = "I don't recall you mentioning your name. Could you tell me?"
	} else if strings.Contains(content, "I like pizza") && strings.Contains(content, "What's my favorite food?") {
		response = "Based on our conversation, your favorite food is pizza!"
	} else if strings.Contains(content, "I like pizza") {
		response = "Pizza is delicious! Do you have a favorite type?"
	} else if strings.Contains(content, "favorite color") && strings.Contains(content, "blue") {
		response = "Blue is a great color! Is there anything else you'd like to talk about?"
	} else if strings.Contains(content, "What did we talk about") {
		if strings.Contains(content, "color") && strings.Contains(content, "pizza") {
			response = "We talked about your favorite food (pizza) and your favorite color (blue)."
		} else if strings.Contains(content, "pizza") {
			response = "We talked about your favorite food, which is pizza."
		} else {
			response = "We haven't talked about much yet. What would you like to discuss?"
		}
	} else if strings.Contains(content, "capital of France") {
		response = "The capital of France is Paris."
	} else if strings.Contains(content, "Who was the first president") {
		response = "The first President of the United States was George Washington."
	} else if strings.Contains(content, "previous question") || strings.Contains(content, "asked before") {
		if strings.Contains(content, "France") {
			response = "You asked about the capital of France, which is Paris."
		} else if strings.Contains(content, "president") {
			response = "You asked about the first President of the United States, which was George Washington."
		} else {
			response = "I remember your previous questions from our conversation."
		}
	} else if m.scenario == "customer_support" {
		if strings.Contains(content, "order") && strings.Contains(content, "123") {
			response = "I found your order #123. It's currently being processed and should ship tomorrow."
		} else if strings.Contains(content, "shipping") {
			response = "Based on your order #123, shipping will take 3-5 business days."
		} else {
			response = "I'm here to help! What can I assist you with today?"
		}
	} else {
		response = "I understand. What else would you like to know?"
	}

	return agenkit.NewMessage("assistant", response), nil
}

// Example 1: Basic conversation with name memory
// TODO: Uncomment when ConversationalAgent is implemented
/*
func exampleBasicConversation() error {
	fmt.Println("\n=== Example 1: Basic Conversation with Memory ===")

	llm := &MockLLMAgent{scenario: "general"}

	config := patterns.ConversationalConfig{
		LLM:           llm,
		MaxHistory:    10,
		SystemPrompt:  "You are a friendly assistant that remembers context.",
		IncludeSystem: true,
	}

	agent, err := patterns.NewConversationalAgent(config)
	if err != nil {
		return err
	}

	fmt.Println("User: My name is Alice")
	response1, err := agent.Process(context.Background(), agenkit.NewMessage("user", "My name is Alice"))
	if err != nil {
		return err
	}
	fmt.Printf("Assistant: %s\n\n", response1.Content)

	fmt.Println("User: What's my name?")
	response2, err := agent.Process(context.Background(), agenkit.NewMessage("user", "What's my name?"))
	if err != nil {
		return err
	}
	fmt.Printf("Assistant: %s\n\n", response2.Content)

	fmt.Printf("History length: %d messages\n", agent.HistoryLength())

	return nil
}

// Example 2: Multi-topic conversation tracking
func exampleMultiTopic() error {
	fmt.Println("\n=== Example 2: Multi-Topic Conversation ===")

	llm := &MockLLMAgent{scenario: "general"}

	config := patterns.ConversationalConfig{
		LLM:           llm,
		MaxHistory:    20,
		SystemPrompt:  "You are a helpful assistant.",
		IncludeSystem: true,
	}

	agent, err := patterns.NewConversationalAgent(config)
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
		fmt.Printf("Assistant: %s\n\n", response.Content)
	}

	fmt.Printf("Current history length: %d\n", agent.HistoryLength())

	return nil
}

// Example 3: History pruning demonstration
func exampleHistoryPruning() error {
	fmt.Println("\n=== Example 3: History Pruning ===")

	llm := &MockLLMAgent{scenario: "general"}

	config := patterns.ConversationalConfig{
		LLM:           llm,
		MaxHistory:    5, // Small history to demonstrate pruning
		SystemPrompt:  "System prompt",
		IncludeSystem: true,
	}

	agent, err := patterns.NewConversationalAgent(config)
	if err != nil {
		return err
	}

	fmt.Println("Max history: 5 messages")
	fmt.Printf("Initial history (with system): %d\n\n", agent.HistoryLength())

	// Add several messages
	for i := 1; i <= 4; i++ {
		fmt.Printf("Turn %d: Sending message...\n", i)
		_, err := agent.Process(context.Background(), agenkit.NewMessage("user", fmt.Sprintf("Message %d", i)))
		if err != nil {
			return err
		}
		fmt.Printf("History length: %d\n\n", agent.HistoryLength())
	}

	fmt.Println("Final history:")
	history := agent.GetHistory()
	for i, msg := range history {
		content := msg.Content
		if len(content) > 50 {
			content = content[:50] + "..."
		}
		fmt.Printf("  [%d] %s: %s\n", i, msg.Role, content)
	}

	return nil
}

// Example 4: Export and import history
func exampleExportImport() error {
	fmt.Println("\n=== Example 4: Export and Import History ===")

	llm := &MockLLMAgent{scenario: "general"}

	// First agent
	config1 := patterns.ConversationalConfig{
		LLM:           llm,
		MaxHistory:    10,
		IncludeSystem: false,
	}

	agent1, err := patterns.NewConversationalAgent(config1)
	if err != nil {
		return err
	}

	fmt.Println("Agent 1: Starting conversation...")
	_, err = agent1.Process(context.Background(), agenkit.NewMessage("user", "What's the capital of France?"))
	if err != nil {
		return err
	}
	_, err = agent1.Process(context.Background(), agenkit.NewMessage("user", "Who was the first president of the US?"))
	if err != nil {
		return err
	}

	fmt.Printf("Agent 1: History length: %d\n", agent1.HistoryLength())

	// Export history
	exported := agent1.ExportHistory()
	fmt.Printf("Exported %d messages\n\n", len(exported))

	// Second agent - import history
	config2 := patterns.ConversationalConfig{
		LLM:           llm,
		MaxHistory:    10,
		IncludeSystem: false,
	}

	agent2, err := patterns.NewConversationalAgent(config2)
	if err != nil {
		return err
	}

	if err := agent2.ImportHistory(exported); err != nil {
		return err
	}
	fmt.Println("Agent 2: Imported history")
	fmt.Printf("Agent 2: History length: %d\n", agent2.HistoryLength())

	// Continue conversation on agent2
	fmt.Println("\nAgent 2: Continuing conversation...")
	fmt.Println("User: What was my previous question about France?")
	response, err := agent2.Process(context.Background(), agenkit.NewMessage("user", "What was my previous question about France?"))
	if err != nil {
		return err
	}
	fmt.Printf("Assistant: %s\n\n", response.Content)

	return nil
}

// Example 5: Customer support conversation
func exampleCustomerSupport() error {
	fmt.Println("\n=== Example 5: Customer Support Scenario ===")

	llm := &MockLLMAgent{scenario: "customer_support"}

	config := patterns.ConversationalConfig{
		LLM:           llm,
		MaxHistory:    15,
		SystemPrompt:  "You are a customer support agent. Be helpful and remember order details.",
		IncludeSystem: true,
	}

	agent, err := patterns.NewConversationalAgent(config)
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
		fmt.Printf("Support: %s\n\n", response.Content)

		if i == 1 {
			fmt.Println("[Agent remembered order number from context]")
		}
	}

	return nil
}

// Example 6: Clear history demonstration
func exampleClearHistory() error {
	fmt.Println("\n=== Example 6: Clear History ===")

	llm := &MockLLMAgent{scenario: "general"}

	config := patterns.ConversationalConfig{
		LLM:           llm,
		MaxHistory:    10,
		SystemPrompt:  "You are a helpful assistant.",
		IncludeSystem: true,
	}

	agent, err := patterns.NewConversationalAgent(config)
	if err != nil {
		return err
	}

	// Build up some history
	_, err = agent.Process(context.Background(), agenkit.NewMessage("user", "My name is Bob"))
	if err != nil {
		return err
	}
	_, err = agent.Process(context.Background(), agenkit.NewMessage("user", "I like coffee"))
	if err != nil {
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
	fmt.Printf("Assistant: %s\n\n", response.Content)
	fmt.Println("[Agent doesn't remember because history was cleared]")

	return nil
}
*/

func main() {
	fmt.Println("Conversational Pattern Examples")
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("\n⚠ This example requires ConversationalAgent pattern implementation.")
	fmt.Println("See Python implementation for reference.")

	// TODO: Uncomment when ConversationalAgent is implemented in Go
	// // Run all examples
	// if err := exampleBasicConversation(); err != nil {
	// 	log.Fatalf("Example 1 failed: %v", err)
	// }
	// if err := exampleClearHistory(); err != nil {
	// 	log.Fatalf("Example 6 failed: %v", err)
	// }
	//
	// fmt.Println("\n" + strings.Repeat("=", 60))
	// fmt.Println("✓ All examples completed successfully!")
}
