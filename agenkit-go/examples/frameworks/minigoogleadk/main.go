//go:build ignore

// minigoogleadk demonstrates Google Agent Development Kit (ADK)-equivalent
// patterns using Agenkit.
//
// Google ADK is an open-source framework for building multi-agent systems with
// first-class support for composition and session management. Key abstractions:
//
//	Agent              → base LLM-backed agent with name, instruction, tools
//	SequentialAgent    → runs sub-agents in order; each output feeds the next
//	ParallelAgent      → runs sub-agents concurrently; results are combined
//	LoopAgent          → repeats a single agent until STOP or max_iterations
//	Content / Part     → message format (ADK's equivalent of agenkit.Message)
//	Runner             → executes agents with session management
//	InMemorySessionService → session persistence for multi-turn interactions
//
// This file implements lightweight inline versions of each concept to make the
// mapping explicit, then demonstrates four scenarios.
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
	"sync"

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/llm"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ---------------------------------------------------------------------------
// Part / Content — ADK message format
// ---------------------------------------------------------------------------

// Part is a single piece of content within a Content object.
// Equivalent to ADK's Part(text=…).
type Part struct {
	Text string
}

// Content is the ADK message envelope, holding a role and one or more Parts.
// Equivalent to ADK's Content(role=…, parts=[Part(text=…)]).
type Content struct {
	Role  string
	Parts []Part
}

// NewContent creates a Content with a single text Part.
func NewContent(role, text string) *Content {
	return &Content{Role: role, Parts: []Part{{Text: text}}}
}

// Text joins all Part texts and returns them as a single string.
func (c *Content) Text() string {
	var sb strings.Builder
	for i, p := range c.Parts {
		if i > 0 {
			sb.WriteString(" ")
		}
		sb.WriteString(p.Text)
	}
	return sb.String()
}

// toMessage converts a Content into an agenkit.Message for LLM calls.
func (c *Content) toMessage() *agenkit.Message {
	return agenkit.NewMessage(c.Role, c.Text())
}

// ---------------------------------------------------------------------------
// ADKTool — a callable tool registered with an ADKAgent
// ---------------------------------------------------------------------------

// ADKTool is a named, described function that an ADKAgent can invoke.
// Equivalent to ADK's FunctionTool.
type ADKTool struct {
	name string
	desc string
	fn   func(args map[string]string) (string, error)
}

// ---------------------------------------------------------------------------
// ADKAgent — base LLM-backed agent with instruction and tools
// ---------------------------------------------------------------------------

// ADKAgent is the fundamental building block: an LLM agent with a name,
// instruction (system prompt), and an optional set of tools.
// Equivalent to ADK's Agent(name=…, model=…, instruction=…, tools=[…]).
type ADKAgent struct {
	name        string
	instruction string
	llmClient   llm.LLM
	tools       []*ADKTool
}

// NewADKAgent creates an ADKAgent with the given name, LLM, and instruction.
func NewADKAgent(name string, llmClient llm.LLM, instruction string) *ADKAgent {
	return &ADKAgent{name: name, instruction: instruction, llmClient: llmClient}
}

// AddTool registers a tool with the agent.
func (a *ADKAgent) AddTool(t *ADKTool) { a.tools = append(a.tools, t) }

// Run processes the content and returns the agent's response as a Content.
// If tools are registered their descriptions are included in the system prompt;
// a "TOOL:<name> ARGS:<value>" directive in the LLM response triggers a call.
func (a *ADKAgent) Run(ctx context.Context, content *Content) (*Content, error) {
	// Build tool manifest.
	var toolDesc strings.Builder
	if len(a.tools) > 0 {
		toolDesc.WriteString("\nAvailable tools (use TOOL:<name> ARGS:<value> to call):\n")
		for _, t := range a.tools {
			toolDesc.WriteString(fmt.Sprintf("  %s: %s\n", t.name, t.desc))
		}
	}

	msgs := []*agenkit.Message{
		agenkit.NewMessage("system", a.instruction+toolDesc.String()),
		content.toMessage(),
	}

	resp, err := a.llmClient.Complete(ctx, msgs)
	if err != nil {
		if strings.Contains(err.Error(), "connection refused") ||
			strings.Contains(err.Error(), "no such host") {
			return NewContent("model", "[LLM not running — showing structure only]"), nil
		}
		return nil, fmt.Errorf("agent %q LLM call failed: %w", a.name, err)
	}

	text := resp.ContentString()

	// Simple tool-call detection.
	if idx := strings.Index(text, "TOOL:"); idx != -1 {
		rest := text[idx+5:]
		parts := strings.SplitN(rest, "ARGS:", 2)
		if len(parts) == 2 {
			toolName := strings.TrimSpace(parts[0])
			argVal := strings.TrimSpace(strings.SplitN(parts[1], "\n", 2)[0])
			for _, t := range a.tools {
				if strings.EqualFold(t.name, toolName) {
					fmt.Printf("  [%s] calling tool %q args=%q\n", a.name, toolName, argVal)
					toolResult, toolErr := t.fn(map[string]string{"input": argVal})
					if toolErr != nil {
						return nil, fmt.Errorf("tool %q failed: %w", toolName, toolErr)
					}
					// Re-call the LLM with the tool result.
					msgs2 := append(msgs,
						agenkit.NewMessage("assistant", text),
						agenkit.NewMessage("user", "Tool result: "+toolResult+"\nProvide your final answer."),
					)
					resp2, err2 := a.llmClient.Complete(ctx, msgs2)
					if err2 != nil {
						if strings.Contains(err2.Error(), "connection refused") ||
							strings.Contains(err2.Error(), "no such host") {
							return NewContent("model", toolResult), nil
						}
						return nil, fmt.Errorf("agent %q synthesis call failed: %w", a.name, err2)
					}
					return NewContent("model", resp2.ContentString()), nil
				}
			}
		}
	}

	return NewContent("model", text), nil
}

// ---------------------------------------------------------------------------
// SequentialADKAgent — runs sub-agents in order, chaining outputs
// ---------------------------------------------------------------------------

// SequentialADKAgent runs its sub-agents one after another. Each agent
// receives the previous agent's output as its input.
// Equivalent to ADK's SequentialAgent(sub_agents=[…]).
type SequentialADKAgent struct {
	name   string
	agents []*ADKAgent
}

// Run passes content through each sub-agent in sequence. The output of agent N
// becomes the input of agent N+1.
func (s *SequentialADKAgent) Run(ctx context.Context, content *Content) (*Content, error) {
	current := content
	for i, agent := range s.agents {
		fmt.Printf("  [sequential] step %d/%d — agent %q\n", i+1, len(s.agents), agent.name)
		out, err := agent.Run(ctx, current)
		if err != nil {
			return nil, fmt.Errorf("sequential step %d (%q) failed: %w", i+1, agent.name, err)
		}
		// Wrap the output as user content for the next agent.
		current = NewContent("user", out.Text())
	}
	return current, nil
}

// ---------------------------------------------------------------------------
// parallelResult holds one agent's result plus any error
// ---------------------------------------------------------------------------
type parallelResult struct {
	agentName string
	content   *Content
	err       error
}

// ---------------------------------------------------------------------------
// ParallelADKAgent — runs sub-agents concurrently and combines results
// ---------------------------------------------------------------------------

// ParallelADKAgent runs all sub-agents with the same input simultaneously
// using goroutines and collects results via a channel.
// Equivalent to ADK's ParallelAgent(sub_agents=[…]).
type ParallelADKAgent struct {
	name   string
	agents []*ADKAgent
}

// Run launches each sub-agent in its own goroutine, waits for all to complete,
// then concatenates their outputs into a single Content.
func (p *ParallelADKAgent) Run(ctx context.Context, content *Content) (*Content, error) {
	results := make(chan parallelResult, len(p.agents))

	for _, agent := range p.agents {
		agent := agent // capture loop variable
		go func() {
			out, err := agent.Run(ctx, content)
			results <- parallelResult{agentName: agent.name, content: out, err: err}
		}()
	}

	var combined strings.Builder
	combined.WriteString(fmt.Sprintf("[parallel results from %d agents]\n\n", len(p.agents)))

	for range p.agents {
		r := <-results
		if r.err != nil {
			return nil, fmt.Errorf("parallel agent %q failed: %w", r.agentName, r.err)
		}
		combined.WriteString(fmt.Sprintf("— %s:\n%s\n\n", r.agentName, r.content.Text()))
	}

	return NewContent("model", combined.String()), nil
}

// ---------------------------------------------------------------------------
// LoopADKAgent — repeats a single agent until STOP or max iterations
// ---------------------------------------------------------------------------

// LoopADKAgent repeatedly calls its sub-agent until the response contains
// "STOP" or maxIterations is reached.
// Equivalent to ADK's LoopAgent(sub_agent=…, max_iterations=…).
type LoopADKAgent struct {
	name          string
	agent         *ADKAgent
	maxIterations int
}

// Run iterates the sub-agent, passing each response back as the next input.
// Stops early when the response contains "STOP".
func (l *LoopADKAgent) Run(ctx context.Context, content *Content) (*Content, error) {
	current := content
	for i := 0; i < l.maxIterations; i++ {
		fmt.Printf("  [loop] iteration %d/%d — agent %q\n", i+1, l.maxIterations, l.agent.name)
		out, err := l.agent.Run(ctx, current)
		if err != nil {
			return nil, fmt.Errorf("loop iteration %d failed: %w", i+1, err)
		}
		if strings.Contains(out.Text(), "STOP") {
			fmt.Printf("  [loop] STOP signal received after %d iteration(s)\n", i+1)
			return out, nil
		}
		current = NewContent("user", out.Text())
	}
	fmt.Printf("  [loop] reached max iterations (%d)\n", l.maxIterations)
	return current, nil
}

// ---------------------------------------------------------------------------
// InMemorySessionService — session persistence
// ---------------------------------------------------------------------------

// InMemorySessionService stores per-session Content histories in memory.
// Equivalent to ADK's InMemorySessionService.
type InMemorySessionService struct {
	mu       sync.Mutex
	sessions map[string][]*Content
}

// NewInMemorySessionService creates an empty InMemorySessionService.
func NewInMemorySessionService() *InMemorySessionService {
	return &InMemorySessionService{sessions: make(map[string][]*Content)}
}

// Append adds a Content to the session identified by sessionID.
func (s *InMemorySessionService) Append(sessionID string, c *Content) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.sessions[sessionID] = append(s.sessions[sessionID], c)
}

// GetHistory returns all Content entries for the session.
func (s *InMemorySessionService) GetHistory(sessionID string) []*Content {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.sessions[sessionID]
}

// ---------------------------------------------------------------------------
// Runner — executes an agent with session management
// ---------------------------------------------------------------------------

// agentRunner is the interface satisfied by all ADK agent types that can be
// driven by a Runner.
type agentRunner interface {
	Run(ctx context.Context, content *Content) (*Content, error)
}

// Runner pairs an agent with a session service. Each call to Run records the
// user message and the agent response in the session history.
// Equivalent to ADK's Runner(agent=…, session_service=…).
type Runner struct {
	agent    agentRunner
	sessions *InMemorySessionService
}

// NewRunner creates a Runner wrapping the given agent and session service.
func NewRunner(agent agentRunner, sessions *InMemorySessionService) *Runner {
	return &Runner{agent: agent, sessions: sessions}
}

// Run executes the agent for the given user/session pair, persisting both the
// input and the output to the session history.
func (r *Runner) Run(ctx context.Context, userID, sessionID string, msg *Content) (*Content, error) {
	key := userID + "/" + sessionID
	r.sessions.Append(key, msg)

	out, err := r.agent.Run(ctx, msg)
	if err != nil {
		return nil, err
	}

	r.sessions.Append(key, out)
	return out, nil
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

	ollamaLLM := llm.NewOpenAICompatibleLLM(
		"http://localhost:11434/v1",
		"llama3.2",
		"ollama",
		"", // no API key required for local servers
	)

	fmt.Println("MiniGoogleADK — Google ADK patterns with Agenkit")
	fmt.Println("Mapping: ADKAgent / SequentialADKAgent / ParallelADKAgent / LoopADKAgent / Runner")

	sessions := NewInMemorySessionService()

	// ------------------------------------------------------------------
	// 1. Single ADKAgent with a search tool
	// ------------------------------------------------------------------
	printSection("1. Single ADKAgent with tool")
	fmt.Println("ADK equivalent: Agent(name='assistant', model=…, tools=[search_tool])")
	fmt.Println()

	searchTool := &ADKTool{
		name: "search",
		desc: "search for information about a topic",
		fn: func(args map[string]string) (string, error) {
			topic := args["input"]
			// Simulated search result.
			return fmt.Sprintf("Search results for %q: Agenkit supports %s with production-grade patterns.", topic, topic), nil
		},
	}

	singleAgent := NewADKAgent(
		"assistant",
		ollamaLLM,
		"You are a helpful assistant. Use the search tool to find information when needed.",
	)
	singleAgent.AddTool(searchTool)

	runner1 := NewRunner(singleAgent, sessions)

	q1 := NewContent("user", "What are the multi-agent capabilities of Agenkit?")
	fmt.Printf("User  : %s\n", q1.Text())

	resp1, err := runner1.Run(ctx, "user1", "session1", q1)
	if err != nil {
		fmt.Fprintf(os.Stderr, "runner run failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Agent : %s\n", resp1.Text())
	fmt.Printf("Session history: %d entries\n", len(sessions.GetHistory("user1/session1")))

	// ------------------------------------------------------------------
	// 2. SequentialADKAgent: researcher → writer
	// ------------------------------------------------------------------
	printSection("2. SequentialADKAgent  (researcher → writer)")
	fmt.Println("ADK equivalent: SequentialAgent(sub_agents=[researcher, writer])")
	fmt.Println()

	researcher := NewADKAgent(
		"researcher",
		ollamaLLM,
		"You are a researcher. Summarise the key facts about the given topic in 2-3 sentences.",
	)

	writer := NewADKAgent(
		"writer",
		ollamaLLM,
		"You are a technical writer. Take the research notes provided and rewrite them as a single polished paragraph suitable for a blog post.",
	)

	seqAgent := &SequentialADKAgent{
		name:   "research_pipeline",
		agents: []*ADKAgent{researcher, writer},
	}
	runner2 := NewRunner(seqAgent, sessions)

	task2 := NewContent("user", "Describe the architecture of Agenkit.")
	fmt.Printf("Task  : %s\n", task2.Text())

	resp2, err := runner2.Run(ctx, "user1", "session2", task2)
	if err != nil {
		fmt.Fprintf(os.Stderr, "sequential run failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Result: %s\n", resp2.Text())

	// ------------------------------------------------------------------
	// 3. ParallelADKAgent: three specialists run simultaneously
	// ------------------------------------------------------------------
	printSection("3. ParallelADKAgent  (three specialists in parallel)")
	fmt.Println("ADK equivalent: ParallelAgent(sub_agents=[tech, business, ux])")
	fmt.Println()

	techAgent := NewADKAgent(
		"tech_specialist",
		ollamaLLM,
		"You are a software engineer. Analyse the technical aspects of the given topic in one sentence.",
	)
	bizAgent := NewADKAgent(
		"business_specialist",
		ollamaLLM,
		"You are a business analyst. Describe the business value of the given topic in one sentence.",
	)
	uxAgent := NewADKAgent(
		"ux_specialist",
		ollamaLLM,
		"You are a UX designer. Describe the user experience implications of the given topic in one sentence.",
	)

	parallelAgent := &ParallelADKAgent{
		name:   "specialist_panel",
		agents: []*ADKAgent{techAgent, bizAgent, uxAgent},
	}
	runner3 := NewRunner(parallelAgent, sessions)

	task3 := NewContent("user", "Evaluate Agenkit as a platform for building AI products.")
	fmt.Printf("Task  : %s\n", task3.Text())

	resp3, err := runner3.Run(ctx, "user1", "session3", task3)
	if err != nil {
		fmt.Fprintf(os.Stderr, "parallel run failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Combined result:\n%s\n", resp3.Text())

	// ------------------------------------------------------------------
	// 4. LoopADKAgent: iterative refinement (capped at 2 iterations)
	// ------------------------------------------------------------------
	printSection("4. LoopADKAgent  (iterative refinement)")
	fmt.Println("ADK equivalent: LoopAgent(sub_agent=refiner, max_iterations=2)")
	fmt.Println()

	refiner := NewADKAgent(
		"refiner",
		ollamaLLM,
		"You are an iterative editor. Improve the given text by one step. "+
			"If the text is already polished and ready to publish, respond with STOP followed by the final text. "+
			"Otherwise, make one small improvement and return the revised text.",
	)

	loopAgent := &LoopADKAgent{
		name:          "refinement_loop",
		agent:         refiner,
		maxIterations: 2,
	}
	runner4 := NewRunner(loopAgent, sessions)

	draft := NewContent("user", "Agenkit is a toolkit. It supports many languages. It is good for AI work.")
	fmt.Printf("Draft : %s\n", draft.Text())

	resp4, err := runner4.Run(ctx, "user1", "session4", draft)
	if err != nil {
		fmt.Fprintf(os.Stderr, "loop run failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Refined: %s\n", resp4.Text())
	fmt.Printf("Session histories: session1=%d session2=%d session3=%d session4=%d entries\n",
		len(sessions.GetHistory("user1/session1")),
		len(sessions.GetHistory("user1/session2")),
		len(sessions.GetHistory("user1/session3")),
		len(sessions.GetHistory("user1/session4")),
	)

	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("MiniGoogleADK demo complete.")
	fmt.Println()
	fmt.Println("Key takeaways:")
	fmt.Println("  ADKAgent          → instruction + tools; TOOL: directive triggers calls")
	fmt.Println("  SequentialADKAgent→ output N becomes input N+1 (pipeline pattern)")
	fmt.Println("  ParallelADKAgent  → goroutines + channel; results joined into one Content")
	fmt.Println("  LoopADKAgent      → iterate until STOP or maxIterations")
	fmt.Println("  InMemorySessionService → per-session Content history; thread-safe")
	fmt.Println("  Runner            → wires agent + sessions; records all turns")
	fmt.Println()
	fmt.Println("For production use, Agenkit's patterns.NewSequentialAgent,")
	fmt.Println("patterns.NewParallelAgent, and patterns.NewRouterAgent provide")
	fmt.Println("equivalent composition with built-in observability hooks.")
}
