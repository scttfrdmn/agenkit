//go:build ignore

// minismolagents demonstrates SmoLAgents-equivalent agentic patterns using Agenkit.
//
// Hugging Face SmoLAgents defines two primary agent types:
//
//   - ToolCallingAgent: the LLM emits structured tool-call requests; the
//     agent executes them and feeds results back until the LLM produces a
//     final answer with no tool request.
//   - CodeAgent: the LLM generates code (or pseudocode) that the agent
//     evaluates to derive an answer.
//
// Agenkit maps these ideas onto its core primitives:
//
//	Tool interface          → any callable with Name/Description/Execute
//	FunctionTool            → Tool backed by a plain Go function
//	ToolCallingAgent        → llm.LLM + tool registry + parse-and-execute loop
//	CodeAgent               → llm.LLM + simple expression evaluator
//
// This file implements lightweight inline versions to make the mapping explicit.
// Production code should use the native Agenkit pattern types.
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
	"strconv"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/llm"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ---------------------------------------------------------------------------
// Tool interface — the SmoLAgents tool abstraction
// ---------------------------------------------------------------------------

// Tool is the minimal interface for any capability the agent can invoke.
// Equivalent to SmoLAgents' Tool base class.
type Tool interface {
	Name() string
	Description() string
	Execute(args map[string]string) (string, error)
}

// ---------------------------------------------------------------------------
// FunctionTool — Tool backed by a plain Go function
// ---------------------------------------------------------------------------

// FunctionTool wraps an arbitrary function as a Tool.
// Equivalent to SmoLAgents' @tool decorator / FunctionTool.
type FunctionTool struct {
	name string
	desc string
	fn   func(map[string]string) (string, error)
}

// Name returns the tool's identifier used in LLM responses.
func (t *FunctionTool) Name() string { return t.name }

// Description returns a natural-language description for the LLM's system prompt.
func (t *FunctionTool) Description() string { return t.desc }

// Execute calls the underlying function with the provided arguments.
func (t *FunctionTool) Execute(args map[string]string) (string, error) {
	return t.fn(args)
}

// ---------------------------------------------------------------------------
// ToolCallingAgent — parse-and-execute loop
// ---------------------------------------------------------------------------

// ToolCallingAgent sends a task to the LLM along with tool descriptions,
// parses "TOOL: <name>\nARGS: key=val,key2=val2" responses, executes the
// named tool, and feeds the result back. The loop continues until the LLM
// produces a final answer that does not start with "TOOL:".
// Equivalent to SmoLAgents' ToolCallingAgent.
type ToolCallingAgent struct {
	llmClient llm.LLM
	tools     []Tool
	maxIter   int
}

// toolByName looks up a tool by its registered name. Returns nil if not found.
func (a *ToolCallingAgent) toolByName(name string) Tool {
	for _, t := range a.tools {
		if t.Name() == name {
			return t
		}
	}
	return nil
}

// buildSystemPrompt returns a system message listing all available tools.
func (a *ToolCallingAgent) buildSystemPrompt() string {
	var sb strings.Builder
	sb.WriteString("You are an AI assistant with access to the following tools:\n\n")
	for _, t := range a.tools {
		fmt.Fprintf(&sb, "- %s: %s\n", t.Name(), t.Description())
	}
	sb.WriteString(`
To use a tool, respond with EXACTLY this format (nothing else before the tool call):

TOOL: <tool_name>
ARGS: key1=value1,key2=value2

When you have a final answer, respond with plain text only (no TOOL: prefix).
`)
	return sb.String()
}

// parseToolCall extracts the tool name and arguments from an LLM response that
// starts with "TOOL:". Returns empty strings if the format is not recognised.
func parseToolCall(response string) (name string, args map[string]string) {
	lines := strings.SplitN(strings.TrimSpace(response), "\n", 3)
	if len(lines) < 1 {
		return "", nil
	}

	toolLine := strings.TrimSpace(lines[0])
	if !strings.HasPrefix(toolLine, "TOOL:") {
		return "", nil
	}
	name = strings.TrimSpace(strings.TrimPrefix(toolLine, "TOOL:"))

	args = make(map[string]string)
	for _, line := range lines[1:] {
		line = strings.TrimSpace(line)
		if !strings.HasPrefix(line, "ARGS:") {
			continue
		}
		pairs := strings.Split(strings.TrimPrefix(line, "ARGS:"), ",")
		for _, pair := range pairs {
			kv := strings.SplitN(strings.TrimSpace(pair), "=", 2)
			if len(kv) == 2 {
				args[strings.TrimSpace(kv[0])] = strings.TrimSpace(kv[1])
			}
		}
	}
	return name, args
}

// Process sends the task to the LLM and drives the tool-call loop. Returns the
// LLM's final plain-text answer. If the LLM server is unavailable, the method
// returns a demo string so the rest of the example can continue.
func (a *ToolCallingAgent) Process(ctx context.Context, task string) (string, error) {
	msgs := []*agenkit.Message{
		agenkit.NewMessage("system", a.buildSystemPrompt()),
		agenkit.NewMessage("user", task),
	}

	for iter := range a.maxIter {
		resp, err := a.llmClient.Complete(ctx, msgs)
		if err != nil {
			if strings.Contains(err.Error(), "connection refused") ||
				strings.Contains(err.Error(), "no such host") {
				fmt.Println("  [LLM not running — showing structure only]")
				return "[demo: LLM not available — tool-calling loop structure demonstrated]", nil
			}
			return "", fmt.Errorf("iteration %d: %w", iter+1, err)
		}

		content := resp.ContentString()
		fmt.Printf("  [iter %d] LLM: %s\n", iter+1, firstLine(content))

		if !strings.HasPrefix(strings.TrimSpace(content), "TOOL:") {
			// Final answer — no tool call requested.
			return content, nil
		}

		toolName, args := parseToolCall(content)
		if toolName == "" {
			return content, nil
		}

		tool := a.toolByName(toolName)
		if tool == nil {
			toolResult := fmt.Sprintf("error: unknown tool %q", toolName)
			fmt.Printf("  [iter %d] tool %q not found\n", iter+1, toolName)
			msgs = append(msgs,
				agenkit.NewMessage("assistant", content),
				agenkit.NewMessage("user", "Tool result: "+toolResult),
			)
			continue
		}

		fmt.Printf("  [iter %d] calling tool %q with args %v\n", iter+1, toolName, args)
		result, err := tool.Execute(args)
		if err != nil {
			result = fmt.Sprintf("error: %v", err)
		}
		fmt.Printf("  [iter %d] tool result: %s\n", iter+1, result)

		msgs = append(msgs,
			agenkit.NewMessage("assistant", content),
			agenkit.NewMessage("user", "Tool result: "+result+"\n\nNow provide your final answer."),
		)
	}

	return "[max iterations reached]", nil
}

// firstLine returns the first non-empty line of s (truncated to 80 chars).
func firstLine(s string) string {
	for _, line := range strings.Split(s, "\n") {
		line = strings.TrimSpace(line)
		if line != "" {
			if len(line) > 80 {
				return line[:80] + "…"
			}
			return line
		}
	}
	return s
}

// ---------------------------------------------------------------------------
// CodeAgent — LLM generates solution steps; demo evaluates simple arithmetic
// ---------------------------------------------------------------------------

// CodeAgent asks the LLM to reason through a task step by step. For numeric
// tasks, a simple expression evaluator extracts the result from the LLM's
// response or from the task directly when the LLM is unavailable.
// Equivalent to SmoLAgents' CodeAgent.
type CodeAgent struct {
	llmClient llm.LLM
	maxIter   int
}

// Process sends the task to the LLM requesting a step-by-step solution and
// returns the result. Falls back to a local arithmetic evaluator when the LLM
// is unreachable.
func (a *CodeAgent) Process(ctx context.Context, task string) (string, error) {
	systemPrompt := `You are a precise problem-solving assistant. When given a task:
1. Break it into clear numbered steps.
2. Show your reasoning for each step.
3. Conclude with a line that starts with "Result: " followed by the final answer only.`

	msgs := []*agenkit.Message{
		agenkit.NewMessage("system", systemPrompt),
		agenkit.NewMessage("user", task),
	}

	resp, err := a.llmClient.Complete(ctx, msgs)
	if err != nil {
		if strings.Contains(err.Error(), "connection refused") ||
			strings.Contains(err.Error(), "no such host") {
			fmt.Println("  [LLM not running — showing structure only]")
			return evalFallback(task), nil
		}
		return "", fmt.Errorf("code agent failed: %w", err)
	}

	return resp.ContentString(), nil
}

// evalFallback performs a minimal local evaluation for simple arithmetic
// expressions of the form "a * b + c" so the demo produces a real result even
// when the LLM is unavailable.
func evalFallback(task string) string {
	// Extract all integers from the task.
	var nums []int64
	for _, field := range strings.FieldsFunc(task, func(r rune) bool {
		return !(r >= '0' && r <= '9')
	}) {
		if n, err := strconv.ParseInt(field, 10, 64); err == nil {
			nums = append(nums, n)
		}
	}

	lower := strings.ToLower(task)
	switch {
	case len(nums) == 3 && strings.Contains(lower, "*") && strings.Contains(lower, "+"):
		result := nums[0]*nums[1] + nums[2]
		return fmt.Sprintf("Step 1: %d × %d = %d\nStep 2: %d + %d = %d\nResult: %d",
			nums[0], nums[1], nums[0]*nums[1], nums[0]*nums[1], nums[2], result, result)
	case len(nums) == 2 && strings.Contains(lower, "*"):
		result := nums[0] * nums[1]
		return fmt.Sprintf("Step 1: %d × %d = %d\nResult: %d", nums[0], nums[1], result, result)
	case len(nums) == 2 && strings.Contains(lower, "+"):
		result := nums[0] + nums[1]
		return fmt.Sprintf("Step 1: %d + %d = %d\nResult: %d", nums[0], nums[1], result, result)
	default:
		return "[demo: LLM not available — code agent structure demonstrated]"
	}
}

// ---------------------------------------------------------------------------
// Demo tools
// ---------------------------------------------------------------------------

// newSearchTool returns a mock web-search tool that returns pre-scripted results
// based on keywords in the query.
func newSearchTool() Tool {
	return &FunctionTool{
		name: "search",
		desc: "Search the web for information. Args: query=<search query>",
		fn: func(args map[string]string) (string, error) {
			query := args["query"]
			if query == "" {
				return "", fmt.Errorf("search requires a 'query' argument")
			}
			lower := strings.ToLower(query)
			switch {
			case strings.Contains(lower, "paris") && strings.Contains(lower, "population"):
				return "Paris population (2024): approximately 2.1 million in the city proper, 11 million in the metropolitan area.", nil
			case strings.Contains(lower, "paris"):
				return "Paris is the capital of France, known for the Eiffel Tower, Louvre Museum, and rich cultural heritage.", nil
			default:
				return fmt.Sprintf("Search results for %q: [mock result — no specific data available for this query]", query), nil
			}
		},
	}
}

// newCalculatorTool returns a tool that evaluates simple arithmetic expressions.
// Supported operations: add, subtract, multiply (via expression string or
// explicit operator/a/b args).
func newCalculatorTool() Tool {
	return &FunctionTool{
		name: "calculator",
		desc: "Perform arithmetic calculations. Args: expression=<math expression, e.g. '2100000 * 2'>",
		fn: func(args map[string]string) (string, error) {
			expr := strings.TrimSpace(args["expression"])
			if expr == "" {
				return "", fmt.Errorf("calculator requires an 'expression' argument")
			}

			// Support: a * b, a + b, a - b
			for _, op := range []string{"*", "+", "-"} {
				parts := strings.SplitN(expr, op, 2)
				if len(parts) != 2 {
					continue
				}
				aVal, err1 := strconv.ParseFloat(strings.TrimSpace(parts[0]), 64)
				bVal, err2 := strconv.ParseFloat(strings.TrimSpace(parts[1]), 64)
				if err1 != nil || err2 != nil {
					continue
				}
				var result float64
				switch op {
				case "*":
					result = aVal * bVal
				case "+":
					result = aVal + bVal
				case "-":
					result = aVal - bVal
				}
				return fmt.Sprintf("%g %s %g = %g", aVal, op, bVal, result), nil
			}

			return "", fmt.Errorf("unsupported expression format: %q (use 'a * b', 'a + b', or 'a - b')", expr)
		},
	}
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

	// Single Ollama-backed LLM shared across both agents.
	// NewOpenAICompatibleLLM works with Ollama, vLLM, llama.cpp, LM Studio — any
	// server that exposes the OpenAI /v1/chat/completions endpoint.
	ollamaLLM := llm.NewOpenAICompatibleLLM(
		"http://localhost:11434/v1",
		"llama3.2",
		"ollama",
		"", // no API key required for local servers
	)

	fmt.Println("MiniSmoLAgents — SmoLAgents patterns with Agenkit")
	fmt.Println("Mapping: Tool / FunctionTool / ToolCallingAgent / CodeAgent")

	// ------------------------------------------------------------------
	// 1. ToolCallingAgent — multi-step search + calculation
	// ------------------------------------------------------------------
	printSection("1. ToolCallingAgent  (search + calculator)")
	fmt.Println("SmoLAgents equivalent: ToolCallingAgent(tools=[search, calculator])")
	fmt.Println()

	searchTool := newSearchTool()
	calcTool := newCalculatorTool()

	toolAgent := &ToolCallingAgent{
		llmClient: ollamaLLM,
		tools:     []Tool{searchTool, calcTool},
		maxIter:   5,
	}

	task1 := "What is the population of Paris multiplied by 2?"
	fmt.Printf("Task: %s\n\n", task1)

	answer1, err := toolAgent.Process(ctx, task1)
	if err != nil {
		fmt.Fprintf(os.Stderr, "tool calling agent failed: %v\n", err)
		os.Exit(1)
	}

	printSection("ToolCallingAgent — Final Answer")
	fmt.Println(answer1)

	// ------------------------------------------------------------------
	// 2. CodeAgent — step-by-step arithmetic reasoning
	// ------------------------------------------------------------------
	printSection("2. CodeAgent  (step-by-step reasoning)")
	fmt.Println("SmoLAgents equivalent: CodeAgent with step-by-step solution generation")
	fmt.Println()

	codeAgent := &CodeAgent{
		llmClient: ollamaLLM,
		maxIter:   3,
	}

	task2 := "Calculate 15 * 7 + 3"
	fmt.Printf("Task: %s\n\n", task2)

	answer2, err := codeAgent.Process(ctx, task2)
	if err != nil {
		fmt.Fprintf(os.Stderr, "code agent failed: %v\n", err)
		os.Exit(1)
	}

	printSection("CodeAgent — Solution")
	fmt.Println(answer2)

	// ------------------------------------------------------------------
	// Tool registry summary
	// ------------------------------------------------------------------
	printSection("Tool Registry")
	tools := []Tool{searchTool, calcTool}
	for _, t := range tools {
		fmt.Printf("  %-12s — %s\n", t.Name(), t.Description())
	}

	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("MiniSmoLAgents demo complete.")
	fmt.Println()
	fmt.Println("Key takeaways:")
	fmt.Println("  Tool            → interface: Name / Description / Execute(map[string]string)")
	fmt.Println("  FunctionTool    → wrap any Go func as a Tool (like @tool decorator)")
	fmt.Println("  ToolCallingAgent → LLM emits 'TOOL: name\\nARGS: k=v'; agent executes + loops")
	fmt.Println("  CodeAgent       → LLM reasons step-by-step; local evaluator as fallback")
	fmt.Println()
	fmt.Println("For production use, prefer the native Agenkit pattern types:")
	fmt.Println("  patterns.NewReActAgent, patterns.NewPlanningAgent — same concepts,")
	fmt.Println("  with built-in tool registries and observability hooks.")
}
