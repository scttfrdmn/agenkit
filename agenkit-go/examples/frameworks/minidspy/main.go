//go:build ignore

// minidspy demonstrates DSPy-equivalent declarative LM programming patterns
// using Agenkit.
//
// DSPy (dspy-ai, Stanford NLP) introduces a declarative paradigm for language
// model programming. Key abstractions:
//
//	Signature    → typed declaration of task inputs and outputs (like a typed prompt)
//	Predict      → executes a Signature once; returns structured output map
//	ChainOfThought → Predict variant that injects an implicit "reasoning" field
//	ReAct        → iterative Reason-Act-Observe tool-calling loop
//	Module       → composable DSPy program; override Forward() to wire sub-modules
//	LM           → the language model backend (here replaced by Agenkit LLM)
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

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/llm"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ---------------------------------------------------------------------------
// Signature — mirrors DSPy.Signature
// ---------------------------------------------------------------------------

// Signature declares the input and output fields of a language model task.
// Equivalent to a dspy.Signature subclass with InputField/OutputField annotations.
type Signature struct {
	InputFields  []string
	OutputFields []string
	Instructions string
}

// ToPrompt renders a prompt string from the signature and caller-supplied inputs.
func (s *Signature) ToPrompt(inputs map[string]string) string {
	var parts []string
	if s.Instructions != "" {
		parts = append(parts, s.Instructions)
	}
	for _, key := range s.InputFields {
		parts = append(parts, key+": "+inputs[key])
	}
	parts = append(parts, "")
	parts = append(parts, "Produce the following output fields (one per line, key: value):")
	for _, key := range s.OutputFields {
		parts = append(parts, "  "+key+":")
	}
	return strings.Join(parts, "\n")
}

// ParseOutput extracts output field values from a raw LLM response.
func ParseOutput(text string, outputFields []string) map[string]string {
	result := make(map[string]string, len(outputFields))
	lines := strings.Split(strings.TrimSpace(text), "\n")
	for _, field := range outputFields {
		fieldLower := strings.ToLower(field)
		for _, line := range lines {
			if strings.HasPrefix(strings.ToLower(line), fieldLower+":") {
				result[field] = strings.TrimSpace(strings.SplitN(line, ":", 2)[1])
				break
			}
		}
		if _, ok := result[field]; !ok {
			// Fallback: first non-empty line.
			for _, line := range lines {
				if strings.TrimSpace(line) != "" {
					result[field] = strings.TrimSpace(line)
					break
				}
			}
		}
	}
	return result
}

// ---------------------------------------------------------------------------
// Predict — mirrors DSPy.Predict
// ---------------------------------------------------------------------------

// Predict runs a Signature once against a language model and returns the
// structured output. Equivalent to dspy.Predict(MySignature).
type Predict struct {
	Sig *Signature
	LLM llm.LLM
}

// Call executes the Predict module with the provided input field values.
// Returns a map of output field names to generated values.
// Equivalent to predict(question="...") in DSPy.
func (p *Predict) Call(ctx context.Context, inputs map[string]string) (map[string]string, error) {
	prompt := p.Sig.ToPrompt(inputs)
	resp, err := p.LLM.Complete(ctx, []*agenkit.Message{
		agenkit.NewMessage("user", prompt),
	})
	if err != nil {
		if strings.Contains(err.Error(), "connection refused") ||
			strings.Contains(err.Error(), "no such host") {
			// Graceful degradation when LLM is unavailable.
			result := make(map[string]string, len(p.Sig.OutputFields))
			for _, f := range p.Sig.OutputFields {
				result[f] = "[LLM not running — showing structure only]"
			}
			return result, nil
		}
		return nil, fmt.Errorf("Predict.Call failed: %w", err)
	}
	return ParseOutput(resp.ContentString(), p.Sig.OutputFields), nil
}

// ---------------------------------------------------------------------------
// ChainOfThought — mirrors DSPy.ChainOfThought
// ---------------------------------------------------------------------------

// ChainOfThought extends Predict by injecting a "reasoning" output field before
// the declared outputs. Equivalent to dspy.ChainOfThought(MySignature).
type ChainOfThought struct {
	Predict
}

// NewChainOfThought creates a ChainOfThought module from a base Signature.
// The "reasoning" field is injected at position 0 of OutputFields.
func NewChainOfThought(sig *Signature, llmClient llm.LLM) *ChainOfThought {
	cotSig := &Signature{
		InputFields:  sig.InputFields,
		OutputFields: append([]string{"reasoning"}, sig.OutputFields...),
		Instructions: sig.Instructions +
			"\nThink step by step. First produce a 'reasoning' field, then your answer.",
	}
	return &ChainOfThought{Predict: Predict{Sig: cotSig, LLM: llmClient}}
}

// ---------------------------------------------------------------------------
// DSPyTool — lightweight tool used by ReAct
// ---------------------------------------------------------------------------

// DSPyTool wraps a plain Go function for use inside the ReAct loop.
type DSPyTool struct {
	Name        string
	Description string
	Fn          func(arg string) string
}

// ---------------------------------------------------------------------------
// ReAct — mirrors DSPy.ReAct
// ---------------------------------------------------------------------------

// ReAct runs an iterative Reason-Act-Observe loop until the LLM produces a
// "Finish:" answer or MaxIters is reached.
// Equivalent to dspy.ReAct(MySignature, tools=[...]).
type ReAct struct {
	Sig      *Signature
	Tools    map[string]*DSPyTool
	LLM      llm.LLM
	MaxIters int
}

// NewReAct creates a ReAct module.
func NewReAct(sig *Signature, tools []*DSPyTool, llmClient llm.LLM, maxIters int) *ReAct {
	toolMap := make(map[string]*DSPyTool, len(tools))
	for _, t := range tools {
		toolMap[t.Name] = t
	}
	return &ReAct{Sig: sig, Tools: toolMap, LLM: llmClient, MaxIters: maxIters}
}

// Call runs the ReAct loop with the provided input field values.
func (r *ReAct) Call(ctx context.Context, inputs map[string]string) (map[string]string, error) {
	var toolDescs []string
	for _, t := range r.Tools {
		toolDescs = append(toolDescs, t.Name+": "+t.Description)
	}

	system := r.Sig.Instructions + "\n\n" +
		"Available tools: " + strings.Join(toolDescs, "; ") + "\n\n" +
		"Format each step as:\n" +
		"Thought: <reasoning>\n" +
		"Action: <tool_name> Input: <argument>\n" +
		"... (repeat until done)\n" +
		"Finish: <final answer>"

	task := r.Sig.ToPrompt(inputs)
	messages := []*agenkit.Message{
		agenkit.NewMessage("system", system),
		agenkit.NewMessage("user", task),
	}
	var trace []string

	for i := 0; i < r.MaxIters; i++ {
		resp, err := r.LLM.Complete(ctx, messages)
		if err != nil {
			if strings.Contains(err.Error(), "connection refused") ||
				strings.Contains(err.Error(), "no such host") {
				result := make(map[string]string, len(r.Sig.OutputFields))
				for _, f := range r.Sig.OutputFields {
					result[f] = "[LLM not running — showing structure only]"
				}
				result["trace"] = "[no trace — LLM unavailable]"
				return result, nil
			}
			return nil, fmt.Errorf("ReAct.Call LLM failed at step %d: %w", i, err)
		}

		reply := resp.ContentString()
		messages = append(messages, agenkit.NewMessage("assistant", reply))
		trace = append(trace, reply)

		if idx := strings.Index(reply, "Finish:"); idx >= 0 {
			answer := strings.TrimSpace(strings.SplitN(reply[idx+7:], "\n", 2)[0])
			result := make(map[string]string, len(r.Sig.OutputFields))
			for _, f := range r.Sig.OutputFields {
				result[f] = answer
			}
			result["trace"] = strings.Join(trace, "\n---\n")
			return result, nil
		}

		if idx := strings.Index(reply, "Action:"); idx >= 0 {
			actionLine := strings.SplitN(reply[idx+7:], "\n", 2)[0]
			parts := strings.SplitN(actionLine, " Input:", 2)
			toolName := strings.TrimSpace(parts[0])
			toolInput := ""
			if len(parts) > 1 {
				toolInput = strings.TrimSpace(parts[1])
			}
			if t, ok := r.Tools[toolName]; ok {
				observation := t.Fn(toolInput)
				messages = append(messages, agenkit.NewMessage("user", "Observation: "+observation))
			}
		}
	}

	// Fallback after max iterations.
	last := ""
	if len(messages) > 0 {
		last = messages[len(messages)-1].ContentString()
	}
	result := make(map[string]string, len(r.Sig.OutputFields))
	for _, f := range r.Sig.OutputFields {
		result[f] = last
	}
	result["trace"] = strings.Join(trace, "\n---\n")
	return result, nil
}

// ---------------------------------------------------------------------------
// Module — mirrors DSPy.Module
// ---------------------------------------------------------------------------

// Module is the base interface for composable DSPy programs.
// Equivalent to dspy.Module; subclasses override Forward().
type Module interface {
	Forward(ctx context.Context, inputs map[string]string) (map[string]string, error)
}

// ---------------------------------------------------------------------------
// MultiHopQA — example Module composition
// ---------------------------------------------------------------------------

// MultiHopQA is a composable Module that decomposes a question into sub-questions,
// answers each, then synthesizes a final answer. Mirrors DSPy multi-hop RAG pipelines.
type MultiHopQA struct {
	decompose  *Predict
	answerSub  *Predict
	synthesize *Predict
}

// NewMultiHopQA creates the pipeline with three Predict sub-modules.
func NewMultiHopQA(llmClient llm.LLM) *MultiHopQA {
	return &MultiHopQA{
		decompose: &Predict{
			Sig: &Signature{
				InputFields:  []string{"question"},
				OutputFields: []string{"sub_question_1", "sub_question_2"},
				Instructions: "Decompose the question into two simpler sub-questions.",
			},
			LLM: llmClient,
		},
		answerSub: &Predict{
			Sig: &Signature{
				InputFields:  []string{"question"},
				OutputFields: []string{"answer"},
				Instructions: "Answer this specific question.",
			},
			LLM: llmClient,
		},
		synthesize: &Predict{
			Sig: &Signature{
				InputFields:  []string{"context", "question"},
				OutputFields: []string{"answer"},
				Instructions: "Synthesize the context to answer the original question.",
			},
			LLM: llmClient,
		},
	}
}

// Forward implements Module: decompose → answer sub-questions → synthesize.
func (m *MultiHopQA) Forward(ctx context.Context, inputs map[string]string) (map[string]string, error) {
	question := inputs["question"]

	// Step 1: decompose.
	decomposed, err := m.decompose.Call(ctx, map[string]string{"question": question})
	if err != nil {
		return nil, fmt.Errorf("decompose failed: %w", err)
	}
	sq1 := decomposed["sub_question_1"]
	sq2 := decomposed["sub_question_2"]

	// Step 2: answer each sub-question.
	ans1, err := m.answerSub.Call(ctx, map[string]string{"question": sq1})
	if err != nil {
		return nil, fmt.Errorf("answer sub-question 1 failed: %w", err)
	}
	ans2 := map[string]string{"answer": ""}
	if sq2 != "" {
		ans2, err = m.answerSub.Call(ctx, map[string]string{"question": sq2})
		if err != nil {
			return nil, fmt.Errorf("answer sub-question 2 failed: %w", err)
		}
	}

	// Step 3: synthesize.
	context := fmt.Sprintf("Q1: %s\nA1: %s\nQ2: %s\nA2: %s",
		sq1, ans1["answer"], sq2, ans2["answer"])
	return m.synthesize.Call(ctx, map[string]string{
		"context":  context,
		"question": question,
	})
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

	fmt.Println("MiniDSPy — DSPy declarative LM programming patterns with Agenkit")
	fmt.Println("Mapping: Signature / Predict / ChainOfThought / ReAct / Module")

	// ------------------------------------------------------------------
	// 1. Predict — simple Q&A with structured output
	// ------------------------------------------------------------------
	printSection("1. Predict  (structured Q&A)")
	fmt.Println("DSPy equivalent: dspy.Predict(QASignature)")
	fmt.Println()

	qaSig := &Signature{
		InputFields:  []string{"question"},
		OutputFields: []string{"answer"},
		Instructions: "Answer the question clearly and concisely.",
	}
	predict := &Predict{Sig: qaSig, LLM: ollamaLLM}

	result1, err := predict.Call(ctx, map[string]string{"question": "What is a language model?"})
	if err != nil {
		fmt.Fprintf(os.Stderr, "Predict.Call failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Input  → question: 'What is a language model?'\n")
	answer := result1["answer"]
	if len(answer) > 80 {
		answer = answer[:80] + "..."
	}
	fmt.Printf("Output → answer: %s\n", answer)
	fmt.Println("Pattern: DSPy.Predict → Agenkit LLM.Complete() + field parsing")

	// ------------------------------------------------------------------
	// 2. ChainOfThought — reasoning before answering
	// ------------------------------------------------------------------
	printSection("2. ChainOfThought  (reason then answer)")
	fmt.Println("DSPy equivalent: dspy.ChainOfThought(QASignature)  — adds 'reasoning' field")
	fmt.Println()

	cotSig := &Signature{
		InputFields:  []string{"question"},
		OutputFields: []string{"answer"},
		Instructions: "Answer complex questions.",
	}
	cot := NewChainOfThought(cotSig, ollamaLLM)
	fmt.Printf("Output fields after ChainOfThought injection: %v\n", cot.Sig.OutputFields)

	result2, err := cot.Call(ctx, map[string]string{"question": "Why does ice float on water?"})
	if err != nil {
		fmt.Fprintf(os.Stderr, "ChainOfThought.Call failed: %v\n", err)
		os.Exit(1)
	}
	reasoning := result2["reasoning"]
	if len(reasoning) > 60 {
		reasoning = reasoning[:60] + "..."
	}
	answer2 := result2["answer"]
	if len(answer2) > 60 {
		answer2 = answer2[:60] + "..."
	}
	fmt.Printf("reasoning: %s\n", reasoning)
	fmt.Printf("answer:    %s\n", answer2)
	fmt.Println("Pattern: DSPy.ChainOfThought → Predict + implicit reasoning field injection")

	// ------------------------------------------------------------------
	// 3. ReAct — multi-step tool-calling loop
	// ------------------------------------------------------------------
	printSection("3. ReAct  (Reason + Act + Observe loop)")
	fmt.Println("DSPy equivalent: dspy.ReAct(TaskSignature, tools=[search, calculate])")
	fmt.Println()

	searchTool := &DSPyTool{
		Name:        "search",
		Description: "Search the web for a fact",
		Fn:          func(q string) string { return "[search result for '" + q + "': relevant information]" },
	}
	calcTool := &DSPyTool{
		Name:        "calculate",
		Description: "Evaluate a math expression",
		Fn: func(expr string) string {
			// Simplified: only handle constant expressions for safety.
			return "[calculated: " + expr + " ≈ 36]"
		},
	}

	reactSig := &Signature{
		InputFields:  []string{"question"},
		OutputFields: []string{"answer"},
		Instructions: "Answer multi-step questions using available tools.",
	}
	react := NewReAct(reactSig, []*DSPyTool{searchTool, calcTool}, ollamaLLM, 4)

	result3, err := react.Call(ctx, map[string]string{"question": "What is 15 percent of 240?"})
	if err != nil {
		fmt.Fprintf(os.Stderr, "ReAct.Call failed: %v\n", err)
		os.Exit(1)
	}
	answer3 := result3["answer"]
	if len(answer3) > 80 {
		answer3 = answer3[:80] + "..."
	}
	fmt.Printf("answer: %s\n", answer3)
	steps := len(strings.Split(result3["trace"], "---"))
	fmt.Printf("steps : %d reasoning step(s)\n", steps)
	fmt.Println("Pattern: DSPy.ReAct → Agenkit ReActAgent (iterative tool loop)")

	// ------------------------------------------------------------------
	// 4. Module composition — multi-hop Q&A pipeline
	// ------------------------------------------------------------------
	printSection("4. Module Composition  (multi-hop Q&A)")
	fmt.Println("DSPy equivalent: class MultiHopQA(dspy.Module): def forward(self, question): ...")
	fmt.Println()

	pipeline := NewMultiHopQA(ollamaLLM)
	result4, err := pipeline.Forward(ctx, map[string]string{
		"question": "How do neural networks learn from data?",
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "MultiHopQA.Forward failed: %v\n", err)
		os.Exit(1)
	}
	answer4 := result4["answer"]
	if len(answer4) > 80 {
		answer4 = answer4[:80] + "..."
	}
	fmt.Printf("Final answer : %s\n", answer4)
	fmt.Println("Pipeline     : decompose → answer sub-questions → synthesize")
	fmt.Println("Pattern      : DSPy.Module.forward() → Agenkit SequentialAgent / custom composition")

	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("MiniDSPy demo complete.")
	fmt.Println()
	fmt.Println("Key takeaways:")
	fmt.Println("  Signature        → InputFields, OutputFields, Instructions; ToPrompt() renders the prompt")
	fmt.Println("  Predict.Call()   → LLM.Complete() + ParseOutput() field extraction")
	fmt.Println("  ChainOfThought   → prepends 'reasoning' to OutputFields; same Call() API")
	fmt.Println("  ReAct.Call()     → Thought→Action→Observation loop until 'Finish:' or MaxIters")
	fmt.Println("  Module.Forward() → composable pipeline; MultiHopQA chains 3 Predict modules")
	fmt.Println()
	fmt.Println("For production use, Agenkit's ReActAgent and SequentialAgent provide")
	fmt.Println("equivalent tool-calling and compositional patterns.")
}
