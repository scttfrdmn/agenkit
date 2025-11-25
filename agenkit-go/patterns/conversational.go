// Package patterns provides the Conversational Agent pattern.
//
// A conversational agent maintains context across multiple turns of conversation,
// managing message history and ensuring responses take into account previous exchanges.
//
// Key features:
//   - Message history management
//   - Context window limiting
//   - Automatic history pruning
//   - Support for system prompts
//
// Example:
//
//	agent := patterns.NewConversationalAgent(&patterns.ConversationalAgentConfig{
//	    LLMClient: myLLMClient,
//	    MaxHistory: 10,
//	    SystemPrompt: "You are a helpful assistant.",
//	})
//
//	// First turn
//	response1, _ := agent.Process(ctx, &agenkit.Message{
//	    Role: "user",
//	    Content: "My name is Alice",
//	})
//
//	// Second turn - agent remembers the name
//	response2, _ := agent.Process(ctx, &agenkit.Message{
//	    Role: "user",
//	    Content: "What's my name?",
//	})
//	// Response: "Your name is Alice."
//
// Performance characteristics:
//   - O(1) message append
//   - O(n) history pruning (only when limit exceeded)
//   - Memory: O(maxHistory) messages
package patterns

import (
	"context"
	"fmt"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// LLMClient is the interface for conversational agents.
//
// Implementations must provide a Chat method that accepts a conversation
// history and returns a response.
type LLMClient interface {
	// Chat generates a response given a conversation history.
	Chat(ctx context.Context, messages []*agenkit.Message) (*agenkit.Message, error)
}

// ConversationalAgentConfig configures a ConversationalAgent.
type ConversationalAgentConfig struct {
	// LLMClient that implements the chat interface
	LLMClient LLMClient
	// MaxHistory is the maximum number of messages to retain (default: 10)
	MaxHistory int
	// SystemPrompt is an optional system prompt to prepend to conversations
	SystemPrompt string
	// IncludeSystem determines whether to include system prompt in history count (default: true)
	IncludeSystem bool
}

// ConversationalAgent maintains conversation history for context-aware responses.
//
// This agent stores previous messages and includes them when processing new messages,
// allowing the LLM to maintain context across multiple turns.
//
// History Management:
//   - Messages are pruned when history exceeds MaxHistory
//   - System messages are always preserved
//   - Oldest user/assistant messages are removed first
//   - Both input and response messages are added to history
type ConversationalAgent struct {
	name          string
	llmClient     LLMClient
	maxHistory    int
	systemPrompt  string
	includeSystem bool
	history       []*agenkit.Message
}

// NewConversationalAgent creates a new conversational agent.
func NewConversationalAgent(config *ConversationalAgentConfig) (*ConversationalAgent, error) {
	if config == nil {
		return nil, fmt.Errorf("config is required")
	}
	if config.LLMClient == nil {
		return nil, fmt.Errorf("llmClient is required")
	}

	maxHistory := config.MaxHistory
	if maxHistory == 0 {
		maxHistory = 10
	}

	includeSystem := config.IncludeSystem
	// Default to true if not explicitly set
	if !config.IncludeSystem && config.MaxHistory == 0 && config.SystemPrompt == "" {
		includeSystem = true
	}

	agent := &ConversationalAgent{
		name:          "ConversationalAgent",
		llmClient:     config.LLMClient,
		maxHistory:    maxHistory,
		systemPrompt:  config.SystemPrompt,
		includeSystem: includeSystem,
		history:       make([]*agenkit.Message, 0),
	}

	// Add system prompt to history if provided
	if config.SystemPrompt != "" && includeSystem {
		agent.history = append(agent.history, &agenkit.Message{
			Role:    "system",
			Content: config.SystemPrompt,
		})
	}

	return agent, nil
}

// Name returns the agent name.
func (c *ConversationalAgent) Name() string {
	return c.name
}

// Capabilities returns the agent's capabilities.
func (c *ConversationalAgent) Capabilities() []string {
	return []string{"conversational", "history-management"}
}

// Process processes a message with full conversation context.
//
// The message is added to history, and the LLM generates a response
// considering all previous messages within the history limit.
//
// Note:
// Both the input message and the response are added to history.
// If history exceeds maxHistory, oldest non-system messages are removed.
func (c *ConversationalAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Add user message to history
	c.history = append(c.history, message)

	// Prune history if needed (keep system prompt if present)
	c.pruneHistory()

	// Generate response with full context
	// Create a copy of history to pass to client
	historyCopy := make([]*agenkit.Message, len(c.history))
	copy(historyCopy, c.history)

	response, err := c.llmClient.Chat(ctx, historyCopy)
	if err != nil {
		return nil, fmt.Errorf("llm chat failed: %w", err)
	}

	// Add response to history
	c.history = append(c.history, response)

	// Prune again after adding response
	c.pruneHistory()

	return response, nil
}

// pruneHistory prunes history to stay within maxHistory limit.
//
// System messages are preserved, and oldest user/assistant messages
// are removed first.
func (c *ConversationalAgent) pruneHistory() {
	if len(c.history) <= c.maxHistory {
		return
	}

	// Separate system messages from conversation
	systemMessages := make([]*agenkit.Message, 0)
	conversationMessages := make([]*agenkit.Message, 0)

	for _, msg := range c.history {
		if msg.Role == "system" {
			systemMessages = append(systemMessages, msg)
		} else {
			conversationMessages = append(conversationMessages, msg)
		}
	}

	// Keep only the most recent conversation messages
	messagesToKeep := c.maxHistory - len(systemMessages)
	var keptConversation []*agenkit.Message
	if messagesToKeep > 0 && len(conversationMessages) > messagesToKeep {
		// Keep the last messagesToKeep messages
		keptConversation = conversationMessages[len(conversationMessages)-messagesToKeep:]
	} else if messagesToKeep > 0 {
		keptConversation = conversationMessages
	} else {
		keptConversation = make([]*agenkit.Message, 0)
	}

	// Rebuild history with system messages first
	c.history = append(systemMessages, keptConversation...)
}

// ClearHistory clears conversation history.
//
// keepSystem determines whether to preserve system prompt (default: true).
func (c *ConversationalAgent) ClearHistory(keepSystem bool) {
	if keepSystem && c.systemPrompt != "" && c.includeSystem {
		c.history = []*agenkit.Message{
			{
				Role:    "system",
				Content: c.systemPrompt,
			},
		}
	} else {
		c.history = make([]*agenkit.Message, 0)
	}
}

// GetHistory returns a copy of current conversation history.
func (c *ConversationalAgent) GetHistory() []*agenkit.Message {
	historyCopy := make([]*agenkit.Message, len(c.history))
	for i, msg := range c.history {
		// Deep copy each message
		msgCopy := &agenkit.Message{
			Role:    msg.Role,
			Content: msg.Content,
		}
		if msg.Metadata != nil {
			msgCopy.Metadata = make(map[string]interface{})
			for k, v := range msg.Metadata {
				msgCopy.Metadata[k] = v
			}
		}
		historyCopy[i] = msgCopy
	}
	return historyCopy
}

// HistoryLength returns the number of messages in history.
func (c *ConversationalAgent) HistoryLength() int {
	return len(c.history)
}

// SetMaxHistory sets maximum history size.
//
// If new max is smaller than current history, history will be pruned immediately.
func (c *ConversationalAgent) SetMaxHistory(max int) {
	c.maxHistory = max
	c.pruneHistory()
}
