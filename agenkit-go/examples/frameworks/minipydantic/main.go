//go:build ignore

// minipydantic demonstrates Pydantic AI-equivalent type-safe tool calling
// using Agenkit.
//
// Pydantic AI popularised attaching strongly-typed Python functions as "tools"
// to an agent, with automatic JSON schema generation from the function's type
// annotations. Go achieves the same effect with generics + reflect:
//
//	TypeSafeTool[I, O]   → generic wrapper that captures input/output types
//	NewTypeSafeTool      → constructor that stores reflect.Type for I
//	InputSchema()        → generates a JSON schema map via reflection
//	TypeSafeAgent        → coordinator that lists tool schemas and dispatches
//
// Two concrete tools are demonstrated:
//
//	add    — adds two integers            (AddInput  → AddOutput)
//	format — replaces {value} in template (FormatInput → FormatOutput)
//
// The agent sends the tool catalogue to the LLM and parses a "TOOL: <name>"
// directive from the response to dispatch. If the LLM is unavailable the demo
// runs entirely with mock dispatch.
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
	"encoding/json"
	"fmt"
	"os"
	"reflect"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/llm"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ---------------------------------------------------------------------------
// TypeSafeTool — reflect-backed generic tool wrapper
// ---------------------------------------------------------------------------

// TypeSafeTool wraps a typed Go function so the input struct can be inspected
// via reflection to produce a JSON schema, and the function can be called with
// an untyped interface{} value at runtime.
// Equivalent to Pydantic AI's @agent.tool decorator.
type TypeSafeTool struct {
	name      string
	desc      string
	inputType reflect.Type // concrete struct type for inputs
	fn        func(interface{}) (interface{}, error)
}

// NewTypeSafeTool creates a TypeSafeTool from a generic function fn.
// I is the input struct type; O is the output type.
// The constructor captures reflect.TypeOf(I) so InputSchema can enumerate
// fields without requiring a concrete value at schema-generation time.
func NewTypeSafeTool[I, O any](name, desc string, fn func(I) (O, error)) *TypeSafeTool {
	return &TypeSafeTool{
		name:      name,
		desc:      desc,
		inputType: reflect.TypeOf((*I)(nil)).Elem(),
		fn: func(input interface{}) (interface{}, error) {
			typed, ok := input.(I)
			if !ok {
				return nil, fmt.Errorf("invalid input type: expected %T, got %T", (*I)(nil), input)
			}
			return fn(typed)
		},
	}
}

// Name returns the tool's registered name.
func (t *TypeSafeTool) Name() string { return t.name }

// Desc returns the tool's human-readable description.
func (t *TypeSafeTool) Desc() string { return t.desc }

// InputSchema generates a JSON schema map from the input struct using
// reflection. Each exported field becomes a property whose type is derived
// from its Go kind.
func (t *TypeSafeTool) InputSchema() map[string]interface{} {
	props := make(map[string]interface{})
	required := make([]string, 0, t.inputType.NumField())

	for i := range t.inputType.NumField() {
		field := t.inputType.Field(i)
		if !field.IsExported() {
			continue
		}
		props[field.Name] = map[string]interface{}{
			"type": goTypeToJSONType(field.Type),
		}
		required = append(required, field.Name)
	}

	return map[string]interface{}{
		"type":       "object",
		"properties": props,
		"required":   required,
	}
}

// Call invokes the underlying function with the provided input value.
func (t *TypeSafeTool) Call(input interface{}) (interface{}, error) {
	return t.fn(input)
}

// goTypeToJSONType converts a Go reflect.Kind to the corresponding JSON schema
// type string.
func goTypeToJSONType(t reflect.Type) string {
	switch t.Kind() {
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64,
		reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64,
		reflect.Float32, reflect.Float64:
		return "number"
	case reflect.Bool:
		return "boolean"
	default:
		return "string"
	}
}

// ---------------------------------------------------------------------------
// Tool input/output structs
// ---------------------------------------------------------------------------

// AddInput holds the operands for the add tool.
type AddInput struct {
	A int
	B int
}

// AddOutput holds the result and a human-readable formula.
type AddOutput struct {
	Result  int
	Formula string
}

// FormatInput holds a template string and a substitution value.
type FormatInput struct {
	Template string
	Value    string
}

// FormatOutput holds the formatted string.
type FormatOutput struct {
	Result string
}

// ---------------------------------------------------------------------------
// TypeSafeAgent — LLM-backed agent that dispatches to typed tools
// ---------------------------------------------------------------------------

// TypeSafeAgent presents a catalogue of TypeSafeTools to an LLM and uses a
// simple "TOOL: <name>" protocol to dispatch tool calls. This maps to
// Pydantic AI's agent-with-tools pattern.
type TypeSafeAgent struct {
	llmClient llm.LLM
	tools     []*TypeSafeTool
}

// NewTypeSafeAgent creates an agent backed by the given LLM.
func NewTypeSafeAgent(llmClient llm.LLM) *TypeSafeAgent {
	return &TypeSafeAgent{llmClient: llmClient}
}

// AddTool registers a tool with the agent.
func (a *TypeSafeAgent) AddTool(t *TypeSafeTool) {
	a.tools = append(a.tools, t)
}

// buildToolCatalogue formats all registered tools as a compact JSON summary
// suitable for inclusion in an LLM prompt.
func (a *TypeSafeAgent) buildToolCatalogue() string {
	type entry struct {
		Name   string                 `json:"name"`
		Desc   string                 `json:"description"`
		Schema map[string]interface{} `json:"schema"`
	}

	entries := make([]entry, 0, len(a.tools))
	for _, t := range a.tools {
		entries = append(entries, entry{
			Name:   t.Name(),
			Desc:   t.Desc(),
			Schema: t.InputSchema(),
		})
	}

	data, err := json.MarshalIndent(entries, "", "  ")
	if err != nil {
		return "[schema error]"
	}
	return string(data)
}

// Process asks the LLM which tool to call for a task, then dispatches to that
// tool with demo input values. Returns the tool's output or the LLM response.
func (a *TypeSafeAgent) Process(ctx context.Context, task string) (interface{}, error) {
	catalogue := a.buildToolCatalogue()
	prompt := fmt.Sprintf(
		"You have the following tools:\n%s\n\n"+
			"For the task below, reply with exactly: TOOL: <name>\n\n"+
			"Task: %s",
		catalogue, task,
	)

	msgs := []*agenkit.Message{agenkit.NewMessage("user", prompt)}
	resp, err := a.llmClient.Complete(ctx, msgs)

	var replyText string
	if err != nil {
		if strings.Contains(err.Error(), "connection refused") ||
			strings.Contains(err.Error(), "no such host") {
			fmt.Println("  [LLM not running — inferring tool from task keywords]")
			replyText = inferToolFromTask(task, a.tools)
		} else {
			return nil, fmt.Errorf("LLM call failed: %w", err)
		}
	} else {
		replyText = resp.ContentString()
	}

	fmt.Printf("  LLM reply: %q\n", replyText)

	// Parse "TOOL: <name>" directive.
	toolName := parseToolDirective(replyText)
	if toolName == "" {
		return replyText, nil // LLM answered directly, no tool call.
	}

	return a.dispatch(toolName, task)
}

// parseToolDirective extracts the tool name from "TOOL: <name>" in reply.
func parseToolDirective(reply string) string {
	for _, line := range strings.Split(reply, "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(strings.ToUpper(line), "TOOL:") {
			return strings.TrimSpace(line[5:])
		}
	}
	return ""
}

// inferToolFromTask provides a keyword-based fallback when the LLM is offline.
func inferToolFromTask(task string, tools []*TypeSafeTool) string {
	lower := strings.ToLower(task)
	for _, t := range tools {
		if strings.Contains(lower, t.Name()) {
			return fmt.Sprintf("TOOL: %s", t.Name())
		}
	}
	if len(tools) > 0 {
		return fmt.Sprintf("TOOL: %s", tools[0].Name())
	}
	return ""
}

// dispatch finds the named tool and calls it with hard-coded demo inputs.
func (a *TypeSafeAgent) dispatch(name, task string) (interface{}, error) {
	for _, t := range a.tools {
		if t.Name() == name {
			input := demoInputFor(name, task)
			fmt.Printf("  dispatching to %q with input %+v\n", name, input)
			return t.Call(input)
		}
	}
	return nil, fmt.Errorf("unknown tool %q", name)
}

// demoInputFor returns a concrete demo input value for each known tool.
func demoInputFor(toolName, task string) interface{} {
	switch toolName {
	case "add":
		return AddInput{A: 7, B: 15}
	case "format":
		return FormatInput{Template: "Hello, {value}!", Value: "World"}
	default:
		return nil
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

func printSchema(t *TypeSafeTool) {
	schema := t.InputSchema()
	data, err := json.MarshalIndent(schema, "  ", "  ")
	if err != nil {
		fmt.Printf("  (schema error: %v)\n", err)
		return
	}
	fmt.Printf("  %s\n", string(data))
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

	fmt.Println("MiniPydantic — Pydantic AI type-safe tool calling with Agenkit")
	fmt.Println("Pattern: NewTypeSafeTool[I,O] + reflect-based schema + TypeSafeAgent")

	// ------------------------------------------------------------------
	// 1. Define typed tools
	// ------------------------------------------------------------------
	addTool := NewTypeSafeTool("add", "Add two integers and return the result with formula",
		func(in AddInput) (AddOutput, error) {
			result := in.A + in.B
			return AddOutput{
				Result:  result,
				Formula: fmt.Sprintf("%d + %d = %d", in.A, in.B, result),
			}, nil
		})

	formatTool := NewTypeSafeTool("format", "Format a string template by replacing {value} with a given value",
		func(in FormatInput) (FormatOutput, error) {
			return FormatOutput{
				Result: strings.ReplaceAll(in.Template, "{value}", in.Value),
			}, nil
		})

	// ------------------------------------------------------------------
	// 2. Print reflect-generated schemas
	// ------------------------------------------------------------------
	printSection("1. Reflect-generated JSON schemas")
	fmt.Printf("Tool %q schema:\n", addTool.Name())
	printSchema(addTool)
	fmt.Println()
	fmt.Printf("Tool %q schema:\n", formatTool.Name())
	printSchema(formatTool)

	// ------------------------------------------------------------------
	// 3. Direct tool execution (no LLM)
	// ------------------------------------------------------------------
	printSection("2. Direct tool execution")

	addIn := AddInput{A: 7, B: 15}
	fmt.Printf("Calling %q with %+v\n", addTool.Name(), addIn)
	addOut, err := addTool.Call(addIn)
	if err != nil {
		fmt.Fprintf(os.Stderr, "add tool error: %v\n", err)
	} else {
		fmt.Printf("Result: %+v\n", addOut)
	}

	fmtIn := FormatInput{Template: "Hello, {value}!", Value: "World"}
	fmt.Printf("\nCalling %q with %+v\n", formatTool.Name(), fmtIn)
	fmtOut, err := formatTool.Call(fmtIn)
	if err != nil {
		fmt.Fprintf(os.Stderr, "format tool error: %v\n", err)
	} else {
		fmt.Printf("Result: %+v\n", fmtOut)
	}

	// ------------------------------------------------------------------
	// 4. TypeSafeAgent with LLM-driven tool selection
	// ------------------------------------------------------------------
	printSection("3. TypeSafeAgent — LLM-driven tool dispatch")

	agent := NewTypeSafeAgent(ollamaLLM)
	agent.AddTool(addTool)
	agent.AddTool(formatTool)

	task := "What is 7 + 15?"
	fmt.Printf("Task: %s\n", task)
	result, err := agent.Process(ctx, task)
	if err != nil {
		fmt.Fprintf(os.Stderr, "agent error: %v\n", err)
	} else {
		fmt.Printf("Output: %+v\n", result)
	}

	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("MiniPydantic demo complete.")
	fmt.Println()
	fmt.Println("Key takeaways:")
	fmt.Println("  NewTypeSafeTool[I,O]  → captures reflect.Type at construction time")
	fmt.Println("  InputSchema()         → generates JSON schema via reflect field iteration")
	fmt.Println("  goTypeToJSONType()    → maps Go reflect.Kind to JSON Schema type string")
	fmt.Println("  TypeSafeAgent        → sends tool catalogue to LLM, parses TOOL: directive")
	fmt.Println("  Direct Call()        → invoke tool without LLM for unit testing")
}
