//go:build ignore

// minichain demonstrates LangChain/LangGraph-equivalent patterns using Agenkit.
//
// LangChain popularised the "chain" abstraction: composable steps that each
// receive an input string and produce an output string. Agenkit's native
// primitives map cleanly onto the same ideas:
//
//	LLMChain           → llm.LLM + string template (prompt formatting + completion)
//	SequentialChain    → patterns.SequentialAgent (pipeline: output → next input)
//	ConversationChain  → patterns.ConversationalAgent (history-aware chat)
//	RouterChain        → patterns.RouterAgent + SimpleClassifier (intent routing)
//
// This file implements lightweight inline versions of each chain type to make
// the mapping explicit, then demonstrates all four in a single main() run.
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
// Chain interface — the fundamental LangChain abstraction
// ---------------------------------------------------------------------------

// Chain is the minimal interface shared by all chain types.
// Each implementation receives a plain string input and returns a plain string
// output (or an error). This matches LangChain's BaseChain.run() contract.
type Chain interface {
	Run(ctx context.Context, input string) (string, error)
}

// ---------------------------------------------------------------------------
// LLMChain — prompt template + single LLM call
// ---------------------------------------------------------------------------

// LLMChain formats a prompt template and calls an LLM once.
// Template variables are expressed as {input} placeholders.
// Equivalent to LangChain's LLMChain(llm=…, prompt=PromptTemplate(…)).
type LLMChain struct {
	llmClient llm.LLM
	template  string // must contain the literal string "{input}"
}

// Run substitutes {input} in the template, calls the LLM, and returns the
// text of the response. If the LLM server is not reachable the method returns
// a placeholder string so the rest of the demo can continue.
func (c *LLMChain) Run(ctx context.Context, input string) (string, error) {
	prompt := strings.ReplaceAll(c.template, "{input}", input)
	msgs := []*agenkit.Message{
		agenkit.NewMessage("user", prompt),
	}
	resp, err := c.llmClient.Complete(ctx, msgs)
	if err != nil {
		if strings.Contains(err.Error(), "connection refused") ||
			strings.Contains(err.Error(), "no such host") {
			fmt.Println("  [LLM not running — showing structure only]")
			return "[demo: LLM not available]", nil
		}
		return "", err
	}
	return resp.ContentString(), nil
}

// ---------------------------------------------------------------------------
// SequentialChain — pipeline: output of step N becomes input of step N+1
// ---------------------------------------------------------------------------

// SequentialChain pipes the output of each chain as the input to the next.
// Equivalent to LangChain's SimpleSequentialChain.
type SequentialChain struct {
	chains []Chain
}

// Run executes each chain in order, threading the output of each step into
// the input of the next. Returns the final chain's output.
func (c *SequentialChain) Run(ctx context.Context, input string) (string, error) {
	current := input
	for i, ch := range c.chains {
		out, err := ch.Run(ctx, current)
		if err != nil {
			return "", fmt.Errorf("step %d failed: %w", i, err)
		}
		current = out
	}
	return current, nil
}

// ---------------------------------------------------------------------------
// ConversationChain — history-aware multi-turn dialogue
// ---------------------------------------------------------------------------

// ConversationChain maintains a running message history for multi-turn
// conversations. Each call appends the user message, calls the LLM with the
// full context, and stores the reply.
// Equivalent to LangChain's ConversationChain with ConversationBufferMemory.
type ConversationChain struct {
	llmClient    llm.LLM
	history      []*agenkit.Message
	systemPrompt string
}

// Run appends the user turn to history, calls the LLM with all previous
// context, appends the assistant reply to history, and returns the reply text.
func (c *ConversationChain) Run(ctx context.Context, input string) (string, error) {
	c.history = append(c.history, agenkit.NewMessage("user", input))

	// Build the full message list: system prompt (if set) + history
	var msgs []*agenkit.Message
	if c.systemPrompt != "" {
		msgs = append(msgs, agenkit.NewMessage("system", c.systemPrompt))
	}
	msgs = append(msgs, c.history...)

	resp, err := c.llmClient.Complete(ctx, msgs)
	if err != nil {
		if strings.Contains(err.Error(), "connection refused") ||
			strings.Contains(err.Error(), "no such host") {
			fmt.Println("  [LLM not running — showing structure only]")
			placeholder := "[demo: LLM not available]"
			c.history = append(c.history, agenkit.NewMessage("assistant", placeholder))
			return placeholder, nil
		}
		return "", err
	}

	reply := resp.ContentString()
	c.history = append(c.history, agenkit.NewMessage("assistant", reply))
	return reply, nil
}

// ---------------------------------------------------------------------------
// RouterChain — keyword-based intent routing
// ---------------------------------------------------------------------------

// RouterChain dispatches each input to one of several named chains based on
// keyword matching, falling back to a default chain when nothing matches.
// Equivalent to LangChain's MultiPromptChain / RouterChain with an
// EmbeddingRouterChain-style selector (but using simple keyword heuristics).
type RouterChain struct {
	routes     map[string]Chain    // route key → chain
	keywords   map[string][]string // route key → trigger keywords
	defaultKey string
}

// Run scans the input for route keywords (case-insensitive) and dispatches
// to the first matching route. Falls back to defaultKey when no keywords match.
func (c *RouterChain) Run(ctx context.Context, input string) (string, error) {
	lower := strings.ToLower(input)
	for key, kws := range c.keywords {
		for _, kw := range kws {
			if strings.Contains(lower, kw) {
				fmt.Printf("  [router] matched route %q on keyword %q\n", key, kw)
				return c.routes[key].Run(ctx, input)
			}
		}
	}
	fmt.Printf("  [router] no keywords matched, using default route %q\n", c.defaultKey)
	return c.routes[c.defaultKey].Run(ctx, input)
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

func mustRun(ctx context.Context, chain Chain, input string) string {
	out, err := chain.Run(ctx, input)
	if err != nil {
		fmt.Fprintf(os.Stderr, "chain error: %v\n", err)
		return "[error]"
	}
	return out
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

func main() {
	ctx := context.Background()

	// Single Ollama-backed LLM used across all demos.
	// NewOpenAICompatibleLLM works with Ollama, vLLM, llama.cpp, LM Studio — any
	// server that exposes the OpenAI /v1/chat/completions endpoint.
	ollamaLLM := llm.NewOpenAICompatibleLLM(
		"http://localhost:11434/v1",
		"llama3.2",
		"ollama",
		"", // no API key required for local servers
	)

	fmt.Println("MiniChain — LangChain patterns with Agenkit")
	fmt.Println("Mapping: LLMChain / SequentialChain / ConversationChain / RouterChain")

	// ------------------------------------------------------------------
	// 1. LLMChain — single prompt template + LLM call
	// ------------------------------------------------------------------
	printSection("1. LLMChain  (PromptTemplate + LLM)")
	fmt.Println("LangChain equivalent: LLMChain(llm=…, prompt=PromptTemplate(template=…))")
	fmt.Println()

	summarizer := &LLMChain{
		llmClient: ollamaLLM,
		template:  "Summarize in one sentence: {input}",
	}

	input1 := "Agenkit is a cross-language AI agent toolkit supporting Python, Go, TypeScript, Rust, C++, and Zig with 100% feature parity."
	fmt.Printf("Input : %s\n", input1)
	out1 := mustRun(ctx, summarizer, input1)
	fmt.Printf("Output: %s\n", out1)

	// ------------------------------------------------------------------
	// 2. SequentialChain — pipeline of chains
	// ------------------------------------------------------------------
	printSection("2. SequentialChain  (SimpleSequentialChain)")
	fmt.Println("LangChain equivalent: SimpleSequentialChain(chains=[summarizer, translator])")
	fmt.Println()

	translator := &LLMChain{
		llmClient: ollamaLLM,
		template:  "Translate the following text to Spanish: {input}",
	}

	pipeline := &SequentialChain{
		chains: []Chain{summarizer, translator},
	}

	input2 := "Machine learning models are trained on large datasets to recognise patterns and make predictions on new data."
	fmt.Printf("Input : %s\n", input2)
	fmt.Println("Stage 1 (summarize) → Stage 2 (translate to Spanish)")
	out2 := mustRun(ctx, pipeline, input2)
	fmt.Printf("Output: %s\n", out2)

	// ------------------------------------------------------------------
	// 3. ConversationChain — multi-turn history-aware chat
	// ------------------------------------------------------------------
	printSection("3. ConversationChain  (ConversationChain + ConversationBufferMemory)")
	fmt.Println("LangChain equivalent: ConversationChain(llm=…, memory=ConversationBufferMemory())")
	fmt.Println()

	conversation := &ConversationChain{
		llmClient:    ollamaLLM,
		systemPrompt: "You are a helpful assistant. Keep your answers brief.",
	}

	turn1 := "My name is Alice."
	fmt.Printf("User : %s\n", turn1)
	reply1 := mustRun(ctx, conversation, turn1)
	fmt.Printf("Agent: %s\n", reply1)

	turn2 := "What is my name?"
	fmt.Printf("User : %s\n", turn2)
	reply2 := mustRun(ctx, conversation, turn2)
	fmt.Printf("Agent: %s\n", reply2)

	fmt.Printf("\n(history length after 2 turns: %d messages)\n", len(conversation.history))

	// ------------------------------------------------------------------
	// 4. RouterChain — keyword-based intent routing
	// ------------------------------------------------------------------
	printSection("4. RouterChain  (MultiPromptChain / RouterChain)")
	fmt.Println("LangChain equivalent: RouterChain with destination chains per intent")
	fmt.Println()

	technicalChain := &LLMChain{
		llmClient: ollamaLLM,
		template:  "Answer this technical question concisely: {input}",
	}
	generalChain := &LLMChain{
		llmClient: ollamaLLM,
		template:  "Answer this general question helpfully: {input}",
	}

	router := &RouterChain{
		routes: map[string]Chain{
			"technical": technicalChain,
			"general":   generalChain,
		},
		keywords: map[string][]string{
			"technical": {"code", "api", "bug"},
			"general":   {"help", "what"},
		},
		defaultKey: "general",
	}

	queries := []string{
		"How do I fix this api bug in my code?",
		"What is the capital of France?",
		"Tell me something interesting.",
	}

	for _, q := range queries {
		fmt.Printf("Query : %s\n", q)
		out := mustRun(ctx, router, q)
		fmt.Printf("Answer: %s\n\n", out)
	}

	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("MiniChain demo complete.")
	fmt.Println()
	fmt.Println("Key takeaways:")
	fmt.Println("  LLMChain        → llm.LLM + strings.ReplaceAll for templates")
	fmt.Println("  SequentialChain → thread output of step N into step N+1")
	fmt.Println("  ConversationChain → append to []*agenkit.Message history")
	fmt.Println("  RouterChain     → keyword dispatch to specialised chains")
	fmt.Println()
	fmt.Println("For production use, prefer the native Agenkit pattern types:")
	fmt.Println("  patterns.NewSequentialAgent, patterns.NewConversationalAgent,")
	fmt.Println("  patterns.NewRouterAgent — same concepts, battle-tested implementation.")
}
