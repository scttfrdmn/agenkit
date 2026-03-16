//go:build ignore

// minisemantickernel demonstrates Microsoft Semantic Kernel-equivalent patterns
// using Agenkit.
//
// Semantic Kernel (SK) is Microsoft's SDK for integrating LLMs into
// applications. Its key abstractions are:
//
//	Kernel             → central object; registers plugins and services
//	KernelPlugin       → named collection of KernelFunctions
//	KernelFunction     → semantic (LLM prompt) or native (Go code) function
//	KernelArguments    → typed argument map passed to functions
//	kernel.Invoke()    → call a registered KernelFunction
//	kernel.InvokePrompt() → render a {{$var}} template and call the LLM
//	ChatHistory        → conversation history with system message
//
// This file implements lightweight inline versions of each concept to make the
// mapping explicit, then demonstrates four scenarios:
//  1. Native functions (MathPlugin — pure Go arithmetic)
//  2. Semantic functions (SummarizePlugin — LLM via InvokePrompt)
//  3. Multi-turn ChatHistory conversation
//  4. Sequential "planner" chaining three functions in order
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
// KernelArguments — typed argument map
// ---------------------------------------------------------------------------

// KernelArguments is the argument container passed to every KernelFunction.
// Equivalent to SK's KernelArguments dictionary.
type KernelArguments map[string]interface{}

// String is a convenience accessor that returns the string value for key, or
// the empty string when the key is absent or the value is not a string.
func (a KernelArguments) String(key string) string {
	v, ok := a[key]
	if !ok {
		return ""
	}
	s, _ := v.(string)
	return s
}

// ---------------------------------------------------------------------------
// KernelFunction — semantic or native callable unit
// ---------------------------------------------------------------------------

// KernelFunction is the atomic callable unit in Semantic Kernel. It can wrap
// a Go function (native) or trigger an LLM call (semantic). Production SK
// distinguishes the two via decorators; here both are represented by the same
// struct with a Go function field.
// Equivalent to SK's KernelFunction.
type KernelFunction struct {
	Name        string
	Description string
	PluginName  string
	fn          func(ctx context.Context, args KernelArguments) (string, error)
}

// Invoke calls the function with the given arguments.
func (f *KernelFunction) Invoke(ctx context.Context, args KernelArguments) (string, error) {
	return f.fn(ctx, args)
}

// ---------------------------------------------------------------------------
// KernelPlugin — named collection of KernelFunctions
// ---------------------------------------------------------------------------

// KernelPlugin groups related KernelFunctions under a shared name.
// Equivalent to SK's KernelPlugin / IKernelPlugin.
type KernelPlugin struct {
	name      string
	functions map[string]*KernelFunction
}

// NewKernelPlugin creates an empty KernelPlugin with the given name.
func NewKernelPlugin(name string) *KernelPlugin {
	return &KernelPlugin{name: name, functions: make(map[string]*KernelFunction)}
}

// AddFunction registers a KernelFunction with the plugin. Sets the
// PluginName on the function. Returns the plugin for fluent chaining.
func (p *KernelPlugin) AddFunction(f *KernelFunction) *KernelPlugin {
	f.PluginName = p.name
	p.functions[f.Name] = f
	return p
}

// GetFunction looks up a function by name.
func (p *KernelPlugin) GetFunction(name string) (*KernelFunction, bool) {
	f, ok := p.functions[name]
	return f, ok
}

// ---------------------------------------------------------------------------
// ChatHistory — conversation history with optional system message
// ---------------------------------------------------------------------------

// ChatHistory tracks a multi-turn conversation. The system message (if set)
// is prepended to every ToMessages() call.
// Equivalent to SK's ChatHistory.
type ChatHistory struct {
	systemMsg string
	messages  []*agenkit.Message
}

// NewChatHistory creates a ChatHistory with the given system message.
func NewChatHistory(systemMsg string) *ChatHistory {
	return &ChatHistory{systemMsg: systemMsg}
}

// AddUserMessage appends a user turn.
func (h *ChatHistory) AddUserMessage(content string) {
	h.messages = append(h.messages, agenkit.NewMessage("user", content))
}

// AddAssistantMessage appends an assistant turn.
func (h *ChatHistory) AddAssistantMessage(content string) {
	h.messages = append(h.messages, agenkit.NewMessage("assistant", content))
}

// ToMessages returns the full message slice for an LLM call. The system
// message is prepended when non-empty.
func (h *ChatHistory) ToMessages() []*agenkit.Message {
	if h.systemMsg == "" {
		return h.messages
	}
	out := make([]*agenkit.Message, 0, len(h.messages)+1)
	out = append(out, agenkit.NewMessage("system", h.systemMsg))
	out = append(out, h.messages...)
	return out
}

// ---------------------------------------------------------------------------
// Kernel — central orchestrator
// ---------------------------------------------------------------------------

// Kernel is the central Semantic Kernel object. It holds the LLM service and
// a registry of plugins. Functions are invoked through the kernel so that
// middleware (logging, caching, etc.) can be applied centrally.
// Equivalent to SK's Kernel.
type Kernel struct {
	llmClient llm.LLM
	plugins   map[string]*KernelPlugin
}

// NewKernel creates an empty Kernel.
func NewKernel() *Kernel {
	return &Kernel{plugins: make(map[string]*KernelPlugin)}
}

// AddService registers an LLM client as the kernel's AI service.
// Returns the kernel for fluent chaining.
// Equivalent to SK's kernel.add_service(AzureChatCompletion(…)) / builder.AddOpenAIChatCompletion().
func (k *Kernel) AddService(llmClient llm.LLM) *Kernel {
	k.llmClient = llmClient
	return k
}

// AddPlugin registers a KernelPlugin. Returns the kernel for fluent chaining.
// Equivalent to SK's kernel.add_plugin(plugin, plugin_name).
func (k *Kernel) AddPlugin(p *KernelPlugin) *Kernel {
	k.plugins[p.name] = p
	return k
}

// Invoke calls a KernelFunction with the provided arguments.
// Equivalent to SK's await kernel.invoke(function, KernelArguments(…)).
func (k *Kernel) Invoke(ctx context.Context, fn *KernelFunction, args KernelArguments) (string, error) {
	return fn.Invoke(ctx, args)
}

// InvokePrompt renders a prompt template by substituting {{$varname}} placeholders
// with values from args, then calls the LLM and returns the response text.
// Equivalent to SK's await kernel.invoke_prompt(template, KernelArguments(…)).
func (k *Kernel) InvokePrompt(ctx context.Context, template string, args KernelArguments) (string, error) {
	if k.llmClient == nil {
		return "", fmt.Errorf("no LLM service registered; call AddService first")
	}

	// Substitute {{$varname}} placeholders.
	rendered := template
	for key, val := range args {
		placeholder := "{{$" + key + "}}"
		rendered = strings.ReplaceAll(rendered, placeholder, fmt.Sprintf("%v", val))
	}

	msgs := []*agenkit.Message{
		agenkit.NewMessage("user", rendered),
	}

	resp, err := k.llmClient.Complete(ctx, msgs)
	if err != nil {
		if strings.Contains(err.Error(), "connection refused") ||
			strings.Contains(err.Error(), "no such host") {
			return "[LLM not running — showing structure only]", nil
		}
		return "", fmt.Errorf("invoke prompt LLM call failed: %w", err)
	}
	return resp.ContentString(), nil
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

func mustInvoke(ctx context.Context, k *Kernel, fn *KernelFunction, args KernelArguments) string {
	result, err := k.Invoke(ctx, fn, args)
	if err != nil {
		fmt.Fprintf(os.Stderr, "invoke %s failed: %v\n", fn.Name, err)
		return "[error]"
	}
	return result
}

func mustPrompt(ctx context.Context, k *Kernel, template string, args KernelArguments) string {
	result, err := k.InvokePrompt(ctx, template, args)
	if err != nil {
		fmt.Fprintf(os.Stderr, "invoke prompt failed: %v\n", err)
		return "[error]"
	}
	return result
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

	kernel := NewKernel().AddService(ollamaLLM)

	fmt.Println("MiniSemanticKernel — Microsoft Semantic Kernel patterns with Agenkit")
	fmt.Println("Mapping: Kernel / KernelPlugin / KernelFunction / ChatHistory / InvokePrompt")

	// ------------------------------------------------------------------
	// 1. MathPlugin — native functions (pure Go arithmetic)
	// ------------------------------------------------------------------
	printSection("1. MathPlugin  (native KernelFunctions)")
	fmt.Println("SK equivalent: kernel.add_plugin(MathPlugin(), plugin_name='Math')")
	fmt.Println()

	addFn := &KernelFunction{
		Name:        "Add",
		Description: "add two numbers",
		fn: func(_ context.Context, args KernelArguments) (string, error) {
			var a, b float64
			fmt.Sscanf(args.String("a"), "%f", &a)
			fmt.Sscanf(args.String("b"), "%f", &b)
			return fmt.Sprintf("%.0f", a+b), nil
		},
	}

	multiplyFn := &KernelFunction{
		Name:        "Multiply",
		Description: "multiply two numbers",
		fn: func(_ context.Context, args KernelArguments) (string, error) {
			var a, b float64
			fmt.Sscanf(args.String("a"), "%f", &a)
			fmt.Sscanf(args.String("b"), "%f", &b)
			return fmt.Sprintf("%.0f", a*b), nil
		},
	}

	mathPlugin := NewKernelPlugin("Math").
		AddFunction(addFn).
		AddFunction(multiplyFn)
	kernel.AddPlugin(mathPlugin)

	sum := mustInvoke(ctx, kernel, addFn, KernelArguments{"a": "12", "b": "7"})
	fmt.Printf("Math.Add(12, 7)       = %s\n", sum)

	product := mustInvoke(ctx, kernel, multiplyFn, KernelArguments{"a": "6", "b": "8"})
	fmt.Printf("Math.Multiply(6, 8)   = %s\n", product)

	// ------------------------------------------------------------------
	// 2. SummarizePlugin — semantic function via InvokePrompt
	// ------------------------------------------------------------------
	printSection("2. SummarizePlugin  (semantic KernelFunction via InvokePrompt)")
	fmt.Println("SK equivalent: KernelFunction with prompt template + kernel.invoke_prompt()")
	fmt.Println()

	summarizeTemplate := "Summarize the following text in one sentence:\n\n{{$input}}"
	translateTemplate := "Translate the following text to {{$language}}:\n\n{{$input}}"

	text := "Agenkit is a cross-language AI agent toolkit that achieves 100% feature parity " +
		"across Python, Go, TypeScript, Rust, C++, and Zig, enabling developers to build " +
		"production-grade AI agents in their preferred language."

	fmt.Printf("Input text (%d chars)\n", len(text))

	summary := mustPrompt(ctx, kernel, summarizeTemplate, KernelArguments{"input": text})
	fmt.Printf("Summary    : %s\n", summary)

	translation := mustPrompt(ctx, kernel, translateTemplate, KernelArguments{
		"input":    summary,
		"language": "French",
	})
	fmt.Printf("Translation: %s\n", translation)

	// ------------------------------------------------------------------
	// 3. ChatHistory — multi-turn conversation
	// ------------------------------------------------------------------
	printSection("3. ChatHistory  (multi-turn conversation)")
	fmt.Println("SK equivalent: ChatHistory + IChatCompletionService.get_chat_message_contents()")
	fmt.Println()

	history := NewChatHistory("You are a knowledgeable assistant. Keep answers brief.")

	turns := []string{
		"What programming languages does Agenkit support?",
		"Which of those was added most recently?",
	}

	for _, turn := range turns {
		history.AddUserMessage(turn)
		fmt.Printf("User  : %s\n", turn)

		msgs := history.ToMessages()
		resp, err := ollamaLLM.Complete(ctx, msgs)
		if err != nil {
			if strings.Contains(err.Error(), "connection refused") ||
				strings.Contains(err.Error(), "no such host") {
				reply := "[LLM not running — showing structure only]"
				history.AddAssistantMessage(reply)
				fmt.Printf("Agent : %s\n\n", reply)
				continue
			}
			fmt.Fprintf(os.Stderr, "LLM call failed: %v\n", err)
			os.Exit(1)
		}

		reply := resp.ContentString()
		history.AddAssistantMessage(reply)
		fmt.Printf("Agent : %s\n\n", reply)
	}
	fmt.Printf("(history length: %d messages)\n", len(history.messages))

	// ------------------------------------------------------------------
	// 4. Sequential planner — chain three KernelFunctions in order
	// ------------------------------------------------------------------
	printSection("4. Sequential planner  (function chaining)")
	fmt.Println("SK equivalent: FunctionChoiceBehavior / Handlebars planner — explicit chain")
	fmt.Println()

	// Step 1: extract keywords (native).
	extractFn := &KernelFunction{
		Name:        "ExtractKeywords",
		Description: "extract comma-separated keywords from text",
		fn: func(_ context.Context, args KernelArguments) (string, error) {
			words := strings.Fields(args.String("input"))
			// Keep every third word as a naive "keyword extraction".
			var kws []string
			for i, w := range words {
				if i%3 == 0 && len(w) > 3 {
					kws = append(kws, strings.Trim(w, ".,;:"))
				}
			}
			if len(kws) == 0 {
				return "agenkit,AI,agents", nil
			}
			return strings.Join(kws, ","), nil
		},
	}

	// Step 2: expand keywords into a topic sentence (semantic).
	expandTemplate := "Write one sentence introducing these topics: {{$keywords}}"

	// Step 3: format as a bullet list (native).
	bulletFn := &KernelFunction{
		Name:        "BulletFormat",
		Description: "convert newline-separated lines into a markdown bullet list",
		fn: func(_ context.Context, args KernelArguments) (string, error) {
			lines := strings.Split(strings.TrimSpace(args.String("input")), "\n")
			var sb strings.Builder
			for _, line := range lines {
				line = strings.TrimSpace(line)
				if line != "" {
					sb.WriteString("• " + line + "\n")
				}
			}
			return sb.String(), nil
		},
	}

	utilPlugin := NewKernelPlugin("Util").
		AddFunction(extractFn).
		AddFunction(bulletFn)
	kernel.AddPlugin(utilPlugin)

	planInput := "Agenkit provides sequential, parallel, and router agent patterns that enable " +
		"complex multi-agent workflows across six programming languages."

	fmt.Printf("Plan input: %s\n\n", planInput)

	// Chain the three steps.
	step1 := mustInvoke(ctx, kernel, extractFn, KernelArguments{"input": planInput})
	fmt.Printf("Step 1 — ExtractKeywords : %s\n", step1)

	step2 := mustPrompt(ctx, kernel, expandTemplate, KernelArguments{"keywords": step1})
	fmt.Printf("Step 2 — ExpandTopics    : %s\n", step2)

	step3 := mustInvoke(ctx, kernel, bulletFn, KernelArguments{"input": step2})
	fmt.Printf("Step 3 — BulletFormat    :\n%s", step3)

	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("MiniSemanticKernel demo complete.")
	fmt.Println()
	fmt.Println("Key takeaways:")
	fmt.Println("  KernelFunction (native)  → wrap any Go func(ctx, KernelArguments)")
	fmt.Println("  KernelFunction (semantic)→ InvokePrompt with {{$var}} templates")
	fmt.Println("  KernelPlugin             → group related functions under one name")
	fmt.Println("  Kernel.Invoke            → central dispatch; easy to add middleware")
	fmt.Println("  ChatHistory.ToMessages() → prepend system msg + full turn history")
	fmt.Println("  Sequential planner       → explicit chain: extract → expand → format")
	fmt.Println()
	fmt.Println("For production use, pair with Agenkit's patterns.NewSequentialAgent")
	fmt.Println("for multi-step pipelines and native observability hooks.")
}
