//go:build ignore

// miniopenaiagents demonstrates OpenAI Agents SDK-equivalent patterns using
// Agenkit.
//
// The OpenAI Agents SDK (openai-agents package, January 2026) is the most
// widely adopted new agent framework in Q1 2026. Key abstractions:
//
//	Agent          → named agent with instructions, tools, and handoffs list
//	FunctionTool   → wraps a Go function as a callable tool (mirrors @function_tool)
//	Handoff        → routing object pointing to a target agent
//	RunResult      → holds FinalOutput string and all Messages from the run
//	RunSync()      → synchronous execution (blocks until complete)
//	Run()          → streaming execution (returns channel of string chunks)
//
// This file implements lightweight inline versions of each concept to make the
// mapping explicit, then demonstrates three scenarios.
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
// FunctionTool — mirrors OAI @function_tool decorator
// ---------------------------------------------------------------------------

// FunctionTool wraps a plain Go function as a callable tool.
// Equivalent to the @function_tool decorator in the OpenAI Agents SDK.
type FunctionTool struct {
	Name        string
	Description string
	Fn          func(args map[string]string) (string, error)
}

// Call executes the tool with the provided argument map.
func (f *FunctionTool) Call(args map[string]string) (string, error) {
	return f.Fn(args)
}

// ---------------------------------------------------------------------------
// Handoff — mirrors OAI handoff()
// ---------------------------------------------------------------------------

// Handoff routes execution from one agent to a target agent.
// Equivalent to handoff(agent) in the OpenAI Agents SDK.
type Handoff struct {
	Agent *OAIAgent
}

// ---------------------------------------------------------------------------
// RunResult — mirrors OAI RunResult
// ---------------------------------------------------------------------------

// RunResult holds the outcome of RunSync() or Run().
// Equivalent to the RunResult object returned by the OpenAI Agents SDK Runner.
type RunResult struct {
	FinalOutput string
	Messages    []*agenkit.Message
}

// ---------------------------------------------------------------------------
// OAIAgent — mirrors OAI Agent
// ---------------------------------------------------------------------------

// OAIAgent is a named agent with instructions, tools, and optional handoff targets.
// Equivalent to openai_agents.Agent(name=..., instructions=..., tools=..., handoffs=...).
type OAIAgent struct {
	Name         string
	Instructions string
	LLM          llm.LLM
	Tools        []*FunctionTool
	Handoffs     []*Handoff
}

// toolMap returns a lookup map of tool name → FunctionTool.
func (a *OAIAgent) toolMap() map[string]*FunctionTool {
	m := make(map[string]*FunctionTool, len(a.Tools))
	for _, t := range a.Tools {
		m[t.Name] = t
	}
	return m
}

// handoffMap returns a lookup map of target agent name → OAIAgent.
func (a *OAIAgent) handoffMap() map[string]*OAIAgent {
	m := make(map[string]*OAIAgent, len(a.Handoffs))
	for _, h := range a.Handoffs {
		m[h.Agent.Name] = h.Agent
	}
	return m
}

// ---------------------------------------------------------------------------
// execute — core loop shared by RunSync and Run
// ---------------------------------------------------------------------------

// execute runs the agent loop: LLM call → tool dispatch or handoff → final answer.
func execute(ctx context.Context, agent *OAIAgent, input string) (*RunResult, error) {
	messages := []*agenkit.Message{
		agenkit.NewMessage("user", input),
	}
	current := agent
	maxSteps := 10

	for step := 0; step < maxSteps; step++ {
		// Build system context listing tools and handoffs.
		var toolNames, handoffNames []string
		for _, t := range current.Tools {
			toolNames = append(toolNames, t.Name)
		}
		for _, h := range current.Handoffs {
			handoffNames = append(handoffNames, h.Agent.Name)
		}

		systemParts := []string{current.Instructions}
		if len(toolNames) > 0 {
			systemParts = append(systemParts,
				"Available tools: "+strings.Join(toolNames, ", ")+
					". Call a tool with: TOOL: <name> ARGS: <value>",
			)
		}
		if len(handoffNames) > 0 {
			systemParts = append(systemParts,
				"Available handoffs: "+strings.Join(handoffNames, ", ")+
					". Hand off with: HANDOFF: <agent_name>",
			)
		}

		promptMsgs := append(
			[]*agenkit.Message{agenkit.NewMessage("system", strings.Join(systemParts, "\n"))},
			messages...,
		)

		resp, err := current.LLM.Complete(ctx, promptMsgs)
		if err != nil {
			if strings.Contains(err.Error(), "connection refused") ||
				strings.Contains(err.Error(), "no such host") {
				reply := "[LLM not running — showing structure only]"
				messages = append(messages, agenkit.NewMessage("assistant", reply))
				return &RunResult{FinalOutput: reply, Messages: messages}, nil
			}
			return nil, fmt.Errorf("LLM call failed at step %d: %w", step, err)
		}

		reply := resp.ContentString()
		messages = append(messages, agenkit.NewMessage("assistant", reply))

		// Check for TOOL: call.
		if idx := strings.Index(reply, "TOOL:"); idx >= 0 {
			line := strings.SplitN(reply[idx+5:], "\n", 2)[0]
			fields := strings.SplitN(line, " ARGS:", 2)
			toolName := strings.TrimSpace(fields[0])
			argsVal := ""
			if len(fields) > 1 {
				argsVal = strings.TrimSpace(fields[1])
			}
			if t, ok := current.toolMap()[toolName]; ok {
				result, err := t.Call(map[string]string{"input": argsVal})
				if err != nil {
					return nil, fmt.Errorf("tool %q failed: %w", toolName, err)
				}
				messages = append(messages, agenkit.NewMessage("tool", "["+toolName+"] "+result))
				continue
			}
		}

		// Check for HANDOFF: routing.
		if idx := strings.Index(reply, "HANDOFF:"); idx >= 0 {
			targetName := strings.TrimSpace(strings.SplitN(reply[idx+8:], "\n", 2)[0])
			if target, ok := current.handoffMap()[targetName]; ok {
				fmt.Printf("  → Handing off to: %s\n", target.Name)
				current = target
				continue
			}
		}

		// No markers — final answer.
		return &RunResult{FinalOutput: reply, Messages: messages}, nil
	}

	last := ""
	if len(messages) > 0 {
		last = messages[len(messages)-1].ContentString()
	}
	return &RunResult{FinalOutput: last, Messages: messages}, nil
}

// ---------------------------------------------------------------------------
// RunSync — mirrors OAI Runner.run_sync()
// ---------------------------------------------------------------------------

// RunSync executes the agent and blocks until a RunResult is ready.
// Equivalent to Runner.run_sync(agent, input) in the OpenAI Agents SDK.
func RunSync(ctx context.Context, agent *OAIAgent, input string) (*RunResult, error) {
	return execute(ctx, agent, input)
}

// ---------------------------------------------------------------------------
// Run — mirrors OAI Runner.run() (streaming)
// ---------------------------------------------------------------------------

// Run executes the agent and streams output tokens via a channel.
// Equivalent to the async streaming Runner.run() in the OpenAI Agents SDK.
// The channel is closed when the agent finishes.
func Run(ctx context.Context, agent *OAIAgent, input string) (<-chan string, error) {
	ch := make(chan string, 32)
	go func() {
		defer close(ch)
		result, err := execute(ctx, agent, input)
		if err != nil {
			ch <- "[error: " + err.Error() + "]"
			return
		}
		// Simulate token streaming by sending words one by one.
		for _, word := range strings.Fields(result.FinalOutput) {
			select {
			case ch <- word + " ":
			case <-ctx.Done():
				return
			}
		}
	}()
	return ch, nil
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
		"",
	)

	fmt.Println("MiniOpenAIAgents — OpenAI Agents SDK patterns with Agenkit")
	fmt.Println("Mapping: OAIAgent / FunctionTool / Handoff / RunSync / Run")

	// ------------------------------------------------------------------
	// 1. Triage agent hands off to specialist agents
	// ------------------------------------------------------------------
	printSection("1. Triage Agent + Handoff  (billing vs tech support)")
	fmt.Println("SDK equivalent: Agent(handoffs=[handoff(billing), handoff(tech)])")
	fmt.Println()

	billingAgent := &OAIAgent{
		Name:         "billing",
		Instructions: "You are a billing specialist. Help with invoices, payments, and subscriptions.",
		LLM:          ollamaLLM,
	}

	techAgent := &OAIAgent{
		Name:         "tech_support",
		Instructions: "You are a technical support specialist. Help with bugs, errors, and API questions.",
		LLM:          ollamaLLM,
	}

	triageAgent := &OAIAgent{
		Name: "triage",
		Instructions: "You are a triage agent. Route requests to the right specialist:\n" +
			"- billing: for payment, invoice, subscription questions\n" +
			"- tech_support: for technical issues, bugs, API questions\n" +
			"Always start your response with: HANDOFF: <agent_name>",
		LLM: ollamaLLM,
		Handoffs: []*Handoff{
			{Agent: billingAgent},
			{Agent: techAgent},
		},
	}

	result1, err := RunSync(ctx, triageAgent, "I keep getting a 401 error on the API.")
	if err != nil {
		fmt.Fprintf(os.Stderr, "RunSync failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Messages exchanged : %d\n", len(result1.Messages))
	if len(result1.FinalOutput) > 80 {
		fmt.Printf("Final output       : %s...\n", result1.FinalOutput[:80])
	} else {
		fmt.Printf("Final output       : %s\n", result1.FinalOutput)
	}
	fmt.Println("Pattern: OAI.Agent + handoff() → Agenkit RouterAgent / conditional dispatch")

	// ------------------------------------------------------------------
	// 2. FunctionTool for mock order DB lookup
	// ------------------------------------------------------------------
	printSection("2. FunctionTool  (mock order DB lookup)")
	fmt.Println("SDK equivalent: @function_tool decorator → FunctionTool struct")
	fmt.Println()

	lookupOrder := &FunctionTool{
		Name:        "lookup_order",
		Description: "Look up an order status by order ID.",
		Fn: func(args map[string]string) (string, error) {
			orders := map[string]string{
				"ORD-001": "Shipped — arrives 2026-03-20",
				"ORD-002": "Processing — payment pending",
				"ORD-003": "Delivered — 2026-03-10",
			}
			id := strings.TrimSpace(args["input"])
			if status, ok := orders[id]; ok {
				return status, nil
			}
			return fmt.Sprintf("Order %q not found", id), nil
		},
	}

	getBalance := &FunctionTool{
		Name:        "get_account_balance",
		Description: "Retrieve the account balance for a customer email.",
		Fn: func(args map[string]string) (string, error) {
			return fmt.Sprintf("Account balance for %s: $142.50", args["input"]), nil
		},
	}

	supportAgent := &OAIAgent{
		Name: "support",
		Instructions: "You are a helpful support agent. Use tools when needed.\n" +
			"To call a tool: TOOL: <name> ARGS: <argument>",
		LLM:   ollamaLLM,
		Tools: []*FunctionTool{lookupOrder, getBalance},
	}

	result2, err := RunSync(ctx, supportAgent, "Where is my order ORD-001?")
	if err != nil {
		fmt.Fprintf(os.Stderr, "RunSync failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Tool available     : %s — %s\n", lookupOrder.Name, lookupOrder.Description)
	fmt.Printf("Messages exchanged : %d\n", len(result2.Messages))
	if len(result2.FinalOutput) > 80 {
		fmt.Printf("Final output       : %s...\n", result2.FinalOutput[:80])
	} else {
		fmt.Printf("Final output       : %s\n", result2.FinalOutput)
	}
	fmt.Println("Pattern: FunctionTool{} → Agenkit Tool class")

	// ------------------------------------------------------------------
	// 3. Streaming via Run()
	// ------------------------------------------------------------------
	printSection("3. Streaming  (Run — token channel)")
	fmt.Println("SDK equivalent: async for event in Runner.run(agent, input)")
	fmt.Println()

	simpleAgent := &OAIAgent{
		Name:         "assistant",
		Instructions: "You are a helpful assistant. Be concise.",
		LLM:          ollamaLLM,
	}

	streamCh, err := Run(ctx, simpleAgent, "Explain Agenkit in one sentence.")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Run failed: %v\n", err)
		os.Exit(1)
	}

	fmt.Print("Streaming output : ")
	for chunk := range streamCh {
		fmt.Print(chunk)
	}
	fmt.Println()
	fmt.Println("Pattern: Run() → goroutine + channel (streaming) → Agenkit process_stream()")

	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("MiniOpenAIAgents demo complete.")
	fmt.Println()
	fmt.Println("Key takeaways:")
	fmt.Println("  OAIAgent      → Name, Instructions, Tools, Handoffs")
	fmt.Println("  FunctionTool  → Name, Description, Fn(args map[string]string) (string, error)")
	fmt.Println("  Handoff       → routes to target OAIAgent on HANDOFF: marker")
	fmt.Println("  RunSync()     → blocking execution, returns *RunResult")
	fmt.Println("  Run()         → streaming via <-chan string, goroutine-backed")
	fmt.Println()
	fmt.Println("For production use, Agenkit's patterns.NewRouterAgent provides")
	fmt.Println("equivalent multi-agent routing and handoff composition.")
}
