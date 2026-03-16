//go:build ignore

// miniautogen demonstrates AutoGen-equivalent multi-agent conversation patterns
// using Agenkit.
//
// Microsoft AutoGen popularised the "conversable agent" abstraction: LLM-backed
// agents that chat with each other in a shared conversation thread. A
// GroupChatManager orchestrates round-robin turn-taking until one agent emits a
// TERMINATE signal. Agenkit's core primitives map cleanly onto these ideas:
//
//	ConversableAgent (history-aware LLM chat)  → llm.LLM + []*agenkit.Message history
//	AssistantAgent (default helpful role)      → ConversableAgent with preset system prompt
//	UserProxyAgent (scripted user turns)       → deterministic response list
//	GroupChat (shared message thread)          → []*agenkit.Message + agent roster
//	GroupChatManager (round-robin driver)      → sequential dispatch with TERMINATE check
//
// This file implements lightweight inline versions of each type to make the
// mapping explicit. Production code should use the native Agenkit pattern types.
//
// Prerequisites (optional — demo degrades gracefully if unavailable):
//
//	ollama serve && ollama pull llama3.2
//
// Run with:
//
//	go run main.go
package main

import (
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/llm"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ---------------------------------------------------------------------------
// ConversableAgent — history-aware LLM-backed agent
// ---------------------------------------------------------------------------

// ConversableAgent maintains a per-agent message history and sends the full
// context to the LLM on every turn.
// Equivalent to AutoGen's ConversableAgent(name=…, system_message=…, llm_config=…).
type ConversableAgent struct {
	name      string
	systemMsg string
	llmClient llm.LLM
	history   []*agenkit.Message
}

// Name returns the agent's display name.
func (a *ConversableAgent) Name() string { return a.name }

// Chat appends the user message to the agent's history, calls the LLM with
// the full conversation context (system prompt + history), appends the reply,
// and returns the reply text.
// If the LLM server is unreachable it returns a placeholder so the rest of
// the demo can continue.
func (a *ConversableAgent) Chat(ctx context.Context, msg string) (string, error) {
	a.history = append(a.history, agenkit.NewMessage("user", msg))

	var msgs []*agenkit.Message
	if a.systemMsg != "" {
		msgs = append(msgs, agenkit.NewMessage("system", a.systemMsg))
	}
	msgs = append(msgs, a.history...)

	resp, err := a.llmClient.Complete(ctx, msgs)
	if err != nil {
		if strings.Contains(err.Error(), "connection refused") ||
			strings.Contains(err.Error(), "no such host") {
			fmt.Printf("  [LLM not running — %s showing structure only]\n", a.name)
			placeholder := fmt.Sprintf("[demo: %s — LLM not available]", a.name)
			a.history = append(a.history, agenkit.NewMessage("assistant", placeholder))
			return placeholder, nil
		}
		return "", fmt.Errorf("%s chat failed: %w", a.name, err)
	}

	reply := resp.ContentString()
	a.history = append(a.history, agenkit.NewMessage("assistant", reply))
	return reply, nil
}

// ---------------------------------------------------------------------------
// AssistantAgent — ConversableAgent with a default helpful system prompt
// ---------------------------------------------------------------------------

// AssistantAgent is a ConversableAgent pre-configured with a "helpful assistant"
// system message.
// Equivalent to AutoGen's AssistantAgent(name=…, llm_config=…).
type AssistantAgent struct {
	ConversableAgent
}

// NewAssistantAgent creates an AssistantAgent with the canonical system prompt.
func NewAssistantAgent(name string, llmClient llm.LLM) *AssistantAgent {
	return &AssistantAgent{
		ConversableAgent: ConversableAgent{
			name:      name,
			systemMsg: "You are a helpful assistant. Be concise and constructive.",
			llmClient: llmClient,
		},
	}
}

// ---------------------------------------------------------------------------
// UserProxyAgent — deterministic scripted responses
// ---------------------------------------------------------------------------

// UserProxyAgent returns pre-scripted responses in order, simulating a human
// participant without requiring an LLM. Once all responses are exhausted it
// returns "TERMINATE" to signal the end of the conversation.
// Equivalent to AutoGen's UserProxyAgent with human_input_mode="NEVER" and a
// fixed list of replies.
type UserProxyAgent struct {
	name      string
	responses []string
	idx       int
}

// Name returns the proxy's display name.
func (u *UserProxyAgent) Name() string { return u.name }

// NextResponse returns the next scripted response, or "TERMINATE" when the
// list is exhausted.
func (u *UserProxyAgent) NextResponse() string {
	if u.idx >= len(u.responses) {
		return "TERMINATE"
	}
	r := u.responses[u.idx]
	u.idx++
	return r
}

// ---------------------------------------------------------------------------
// GroupChat — shared message thread and agent roster
// ---------------------------------------------------------------------------

// GroupChat holds the shared conversation history and the list of agents
// participating in the group discussion.
// Equivalent to AutoGen's GroupChat(agents=[…], messages=[…], max_round=…).
type GroupChat struct {
	agents   []*ConversableAgent
	messages []*agenkit.Message
}

// ---------------------------------------------------------------------------
// GroupChatManager — round-robin orchestrator
// ---------------------------------------------------------------------------

// GroupChatManager drives a GroupChat in round-robin order until the active
// agent's response contains "TERMINATE" or maxRounds is reached.
// Equivalent to AutoGen's GroupChatManager(groupchat=…, llm_config=…).
type GroupChatManager struct {
	chat      *GroupChat
	llmClient llm.LLM
	maxRounds int
}

// Run starts the group conversation with an initial message and iterates
// through the agent roster in order. Each agent receives the last message in
// the shared thread and its reply is appended to that thread. Returns the
// last non-TERMINATE response.
func (m *GroupChatManager) Run(ctx context.Context, initial string) (string, error) {
	m.chat.messages = append(m.chat.messages, agenkit.NewMessage("user", initial))
	fmt.Printf("  [manager] initial message: %s\n\n", initial)

	lastReply := initial
	agentCount := len(m.chat.agents)

	for round := range m.maxRounds {
		agent := m.chat.agents[round%agentCount]
		lastMsg := m.chat.messages[len(m.chat.messages)-1].ContentString()

		fmt.Printf("  [round %d] %s is responding...\n", round+1, agent.Name())
		reply, err := agent.Chat(ctx, lastMsg)
		if err != nil {
			return "", fmt.Errorf("round %d agent %s: %w", round+1, agent.Name(), err)
		}

		fmt.Printf("  %s: %s\n\n", agent.Name(), reply)
		m.chat.messages = append(m.chat.messages, agenkit.NewMessage("assistant", reply))

		if strings.Contains(reply, "TERMINATE") {
			fmt.Println("  [manager] TERMINATE signal received — stopping.")
			return lastReply, nil
		}
		lastReply = reply
	}

	return lastReply, nil
}

// ---------------------------------------------------------------------------
// Demo helpers
// ---------------------------------------------------------------------------

func printSection(title string) {
	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println(title)
	fmt.Println(strings.Repeat("=", 60))
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

func main() {
	ctx := context.Background()

	// Single Ollama-backed LLM shared across all agents.
	// NewOpenAICompatibleLLM works with Ollama, vLLM, llama.cpp, LM Studio — any
	// server that exposes the OpenAI /v1/chat/completions endpoint.
	ollamaLLM := llm.NewOpenAICompatibleLLM(
		"http://localhost:11434/v1",
		"llama3.2",
		"ollama",
		"", // no API key required for local servers
	)

	fmt.Println("MiniAutoGen — AutoGen patterns with Agenkit")
	fmt.Println("Mapping: ConversableAgent / AssistantAgent / UserProxyAgent / GroupChat / GroupChatManager")

	// ------------------------------------------------------------------
	// 1. Two-agent conversation — AssistantAgent + UserProxyAgent
	// ------------------------------------------------------------------
	printSection("1. Two-Agent Conversation  (AssistantAgent + UserProxyAgent)")
	fmt.Println("AutoGen equivalent: AssistantAgent + UserProxyAgent with scripted replies")
	fmt.Println()

	assistant := NewAssistantAgent("assistant", ollamaLLM)
	userProxy := &UserProxyAgent{
		name: "user",
		responses: []string{
			"What are the key principles of clean code?",
			"Can you give a concrete example in Go?",
		},
	}

	for range 2 {
		userMsg := userProxy.NextResponse()
		if userMsg == "TERMINATE" {
			break
		}
		fmt.Printf("  %s: %s\n", userProxy.Name(), userMsg)

		reply, err := assistant.Chat(ctx, userMsg)
		if err != nil {
			fmt.Fprintf(os.Stderr, "chat error: %v\n", err)
			os.Exit(1)
		}
		fmt.Printf("  %s: %s\n\n", assistant.Name(), reply)
	}

	fmt.Printf("(assistant history length: %d messages)\n", len(assistant.history))

	// ------------------------------------------------------------------
	// 2. Group chat — three ConversableAgents in round-robin
	// ------------------------------------------------------------------
	printSection("2. GroupChat  (GroupChat + GroupChatManager)")
	fmt.Println("AutoGen equivalent: GroupChat(agents=[…], max_round=9) + GroupChatManager")
	fmt.Println()

	agentDefs := []struct {
		name   string
		system string
	}{
		{
			name:   "assistant",
			system: "You are a helpful assistant. Give constructive, practical advice. Be concise.",
		},
		{
			name:   "critic",
			system: "You are a critical reviewer. Identify weaknesses and suggest improvements. Be specific. Be concise.",
		},
		{
			name:   "summarizer",
			system: "You are a concise summarizer. Distill the key points from the discussion into 2-3 bullet points.",
		},
	}

	agents := make([]*ConversableAgent, 0, len(agentDefs))
	for _, def := range agentDefs {
		agents = append(agents, &ConversableAgent{
			name:      def.name,
			systemMsg: def.system,
			llmClient: ollamaLLM,
		})
	}

	groupChat := &GroupChat{
		agents: agents,
	}

	manager := &GroupChatManager{
		chat:      groupChat,
		llmClient: ollamaLLM,
		maxRounds: 3,
	}

	topic := "How can we improve code review processes?"
	fmt.Printf("Topic: %s\n\n", topic)

	finalReply, err := manager.Run(ctx, topic)
	if err != nil {
		fmt.Fprintf(os.Stderr, "group chat failed: %v\n", err)
		os.Exit(1)
	}

	printSection("Final Output")
	fmt.Println(finalReply)

	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("MiniAutoGen demo complete.")
	fmt.Println()
	fmt.Println("Key takeaways:")
	fmt.Println("  ConversableAgent  → llm.LLM + []*agenkit.Message history per agent")
	fmt.Println("  AssistantAgent    → ConversableAgent with preset helpful system prompt")
	fmt.Println("  UserProxyAgent    → scripted response list; returns TERMINATE when done")
	fmt.Println("  GroupChat         → shared []*agenkit.Message thread + agent roster")
	fmt.Println("  GroupChatManager  → round-robin dispatch with TERMINATE detection")
	fmt.Println()
	fmt.Println("For production use, prefer the native Agenkit pattern types:")
	fmt.Println("  patterns.NewConversationalAgent, patterns.NewSequentialAgent —")
	fmt.Println("  same concepts with built-in observability and error handling.")
}
