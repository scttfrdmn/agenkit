//go:build ignore

// minillamaindex demonstrates LlamaIndex-equivalent agent workflow patterns
// using Agenkit.
//
// LlamaIndex (llama-index) focuses on RAG (Retrieval-Augmented Generation) and
// agent workflows built around document stores. Its key abstractions are:
//
//	VectorStoreIndex  → document store with similarity search
//	QueryEngine       → wraps an index; answers questions using retrieved docs
//	QueryEngineTool   → exposes a QueryEngine as a callable agent tool
//	FunctionAgent     → LLM-backed agent that can call tools and hand off control
//	ReActAgent        → reason-act loop variant of FunctionAgent
//	AgentWorkflow     → orchestrates multiple FunctionAgents with routing
//
// This file implements lightweight inline versions of each concept to make the
// mapping explicit, then demonstrates all three layers in a single main() run.
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
// Document — the atomic unit stored in a VectorStoreIndex
// ---------------------------------------------------------------------------

// Document holds a piece of text content that can be indexed and retrieved.
// Equivalent to LlamaIndex's Document(doc_id=…, text=…).
type Document struct {
	ID      string
	Title   string
	Content string
}

// ---------------------------------------------------------------------------
// VectorStoreIndex — document store with similarity search
// ---------------------------------------------------------------------------

// VectorStoreIndex stores a collection of Documents and supports similarity
// search via keyword overlap. In production LlamaIndex uses real vector
// embeddings; we use a simple word-count heuristic to make the example
// self-contained.
// Equivalent to LlamaIndex's VectorStoreIndex.from_documents(docs).
type VectorStoreIndex struct {
	docs []Document
}

// NewVectorStoreIndex creates a VectorStoreIndex loaded with the provided
// documents. Equivalent to VectorStoreIndex.from_documents(docs).
func NewVectorStoreIndex(docs []Document) *VectorStoreIndex {
	return &VectorStoreIndex{docs: docs}
}

// SimilaritySearch returns the topK documents most relevant to query using
// keyword overlap as a stand-in for cosine similarity on real embeddings.
func (v *VectorStoreIndex) SimilaritySearch(query string, topK int) []Document {
	type scored struct {
		doc   Document
		score int
	}
	queryWords := strings.Fields(strings.ToLower(query))
	scores := make([]scored, len(v.docs))
	for i, doc := range v.docs {
		docText := strings.ToLower(doc.Title + " " + doc.Content)
		var count int
		for _, w := range queryWords {
			if strings.Contains(docText, w) {
				count++
			}
		}
		scores[i] = scored{doc: doc, score: count}
	}
	// Simple selection sort for topK — doc sets are small.
	for i := 0; i < len(scores)-1; i++ {
		for j := i + 1; j < len(scores); j++ {
			if scores[j].score > scores[i].score {
				scores[i], scores[j] = scores[j], scores[i]
			}
		}
	}
	if topK > len(scores) {
		topK = len(scores)
	}
	result := make([]Document, topK)
	for i := 0; i < topK; i++ {
		result[i] = scores[i].doc
	}
	return result
}

// AsQueryEngine wraps the index with an LLM to answer natural-language
// questions. Equivalent to index.as_query_engine().
func (v *VectorStoreIndex) AsQueryEngine(llmClient llm.LLM) *QueryEngine {
	return &QueryEngine{index: v, llmClient: llmClient}
}

// ---------------------------------------------------------------------------
// QueryEngine — retrieves relevant docs then asks the LLM to answer
// ---------------------------------------------------------------------------

// QueryEngine answers questions by first retrieving the topK relevant
// documents from the index and then passing them as context to the LLM.
// Equivalent to LlamaIndex's RetrieverQueryEngine.
type QueryEngine struct {
	index     *VectorStoreIndex
	llmClient llm.LLM
}

// Query retrieves relevant documents and uses the LLM to synthesise an answer.
func (q *QueryEngine) Query(ctx context.Context, question string) (string, error) {
	retrieved := q.index.SimilaritySearch(question, 2)

	var contextBuilder strings.Builder
	contextBuilder.WriteString("Relevant documents:\n")
	for _, doc := range retrieved {
		contextBuilder.WriteString(fmt.Sprintf("\n[%s] %s\n%s\n", doc.ID, doc.Title, doc.Content))
	}

	prompt := fmt.Sprintf("%s\nQuestion: %s\nAnswer concisely based on the documents above.", contextBuilder.String(), question)
	msgs := []*agenkit.Message{
		agenkit.NewMessage("user", prompt),
	}

	resp, err := q.llmClient.Complete(ctx, msgs)
	if err != nil {
		if strings.Contains(err.Error(), "connection refused") ||
			strings.Contains(err.Error(), "no such host") {
			return "[LLM not running — showing structure only]", nil
		}
		return "", fmt.Errorf("query engine LLM call failed: %w", err)
	}
	return resp.ContentString(), nil
}

// ---------------------------------------------------------------------------
// LITool — a callable tool that can be registered with a FunctionAgent
// ---------------------------------------------------------------------------

// LITool is a named, described function that a FunctionAgent can call.
// Equivalent to LlamaIndex's FunctionTool or QueryEngineTool.
type LITool struct {
	name string
	desc string
	fn   func(args map[string]string) (string, error)
}

// Name returns the tool's identifier.
func (t *LITool) Name() string { return t.name }

// Call invokes the tool with the given argument map and returns the result.
func (t *LITool) Call(args map[string]string) (string, error) { return t.fn(args) }

// ---------------------------------------------------------------------------
// FunctionAgent — LLM-backed agent with a tool roster
// ---------------------------------------------------------------------------

// FunctionAgent is an LLM-backed agent that can invoke tools to complete a
// task. It simulates a single ReAct step: build a system prompt describing
// available tools, call the LLM, then check whether the response requests a
// tool call and execute it.
// Equivalent to LlamaIndex's FunctionCallingAgent / ReActAgent.
type FunctionAgent struct {
	name      string
	systemMsg string
	llmClient llm.LLM
	tools     []*LITool
}

// NewFunctionAgent creates a FunctionAgent with the given name, LLM, and
// system message. Add tools with AddTool before calling Run.
func NewFunctionAgent(name string, llmClient llm.LLM, systemMsg string) *FunctionAgent {
	return &FunctionAgent{name: name, systemMsg: systemMsg, llmClient: llmClient}
}

// AddTool registers a tool with the agent.
func (a *FunctionAgent) AddTool(t *LITool) { a.tools = append(a.tools, t) }

// Run executes the agent on the given task. It includes tool descriptions in
// the system prompt and, if the LLM response contains "TOOL:", parses the
// tool name and query and calls the matching tool.
func (a *FunctionAgent) Run(ctx context.Context, task string) (string, error) {
	// Build a tool manifest for the system prompt.
	var toolDesc strings.Builder
	if len(a.tools) > 0 {
		toolDesc.WriteString("\nAvailable tools (respond with TOOL:<name> QUERY:<query> to use one):\n")
		for _, t := range a.tools {
			toolDesc.WriteString(fmt.Sprintf("  %s: %s\n", t.name, t.desc))
		}
	}

	msgs := []*agenkit.Message{
		agenkit.NewMessage("system", a.systemMsg+toolDesc.String()),
		agenkit.NewMessage("user", task),
	}

	resp, err := a.llmClient.Complete(ctx, msgs)
	if err != nil {
		if strings.Contains(err.Error(), "connection refused") ||
			strings.Contains(err.Error(), "no such host") {
			return "[LLM not running — showing structure only]", nil
		}
		return "", fmt.Errorf("agent %s LLM call failed: %w", a.name, err)
	}

	content := resp.ContentString()

	// Simple tool-call detection: look for "TOOL:<name> QUERY:<query>".
	if idx := strings.Index(content, "TOOL:"); idx != -1 {
		rest := content[idx+5:]
		parts := strings.SplitN(rest, "QUERY:", 2)
		if len(parts) == 2 {
			toolName := strings.TrimSpace(parts[0])
			query := strings.TrimSpace(parts[1])
			for _, t := range a.tools {
				if strings.EqualFold(t.name, toolName) {
					fmt.Printf("  [%s] calling tool %q with query %q\n", a.name, toolName, query)
					toolResult, toolErr := t.Call(map[string]string{"query": query})
					if toolErr != nil {
						return "", fmt.Errorf("tool %q failed: %w", toolName, toolErr)
					}
					// Feed the tool result back for a final LLM synthesis.
					msgs2 := append(msgs,
						agenkit.NewMessage("assistant", content),
						agenkit.NewMessage("user", "Tool result: "+toolResult+"\nNow answer the original question."),
					)
					resp2, err2 := a.llmClient.Complete(ctx, msgs2)
					if err2 != nil {
						if strings.Contains(err2.Error(), "connection refused") ||
							strings.Contains(err2.Error(), "no such host") {
							return toolResult, nil
						}
						return "", fmt.Errorf("agent %s synthesis call failed: %w", a.name, err2)
					}
					return resp2.ContentString(), nil
				}
			}
		}
	}

	return content, nil
}

// ---------------------------------------------------------------------------
// AgentWorkflow — orchestrates multiple FunctionAgents with routing
// ---------------------------------------------------------------------------

// AgentWorkflow manages a named set of FunctionAgents and routes tasks to the
// root agent. The root agent can in turn hand off to other agents by including
// "HANDOFF:<agent-name>" in its response.
// Equivalent to LlamaIndex's AgentWorkflow(agents=[…], root_agent=…).
type AgentWorkflow struct {
	agents    map[string]*FunctionAgent
	rootAgent string
}

// NewAgentWorkflow creates an AgentWorkflow with the named root agent.
func NewAgentWorkflow(rootAgent string) *AgentWorkflow {
	return &AgentWorkflow{agents: make(map[string]*FunctionAgent), rootAgent: rootAgent}
}

// AddAgent registers a FunctionAgent under its name.
func (w *AgentWorkflow) AddAgent(a *FunctionAgent) { w.agents[a.name] = a }

// Run executes the workflow starting from the root agent. If the root agent's
// response contains "HANDOFF:<name>", the task is forwarded to that agent.
func (w *AgentWorkflow) Run(ctx context.Context, task string) (string, error) {
	agent, ok := w.agents[w.rootAgent]
	if !ok {
		return "", fmt.Errorf("root agent %q not registered", w.rootAgent)
	}

	result, err := agent.Run(ctx, task)
	if err != nil {
		return "", err
	}

	// Check for handoff directive.
	if idx := strings.Index(result, "HANDOFF:"); idx != -1 {
		targetName := strings.TrimSpace(strings.SplitN(result[idx+8:], "\n", 2)[0])
		if target, found := w.agents[targetName]; found {
			fmt.Printf("  [workflow] handoff from %q to %q\n", w.rootAgent, targetName)
			return target.Run(ctx, task)
		}
	}

	return result, nil
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

	fmt.Println("MiniLlamaIndex — LlamaIndex patterns with Agenkit")
	fmt.Println("Mapping: VectorStoreIndex / QueryEngine / FunctionAgent / AgentWorkflow")

	// ------------------------------------------------------------------
	// 1. VectorStoreIndex + QueryEngine
	// ------------------------------------------------------------------
	printSection("1. VectorStoreIndex + QueryEngine  (RAG pipeline)")
	fmt.Println("LlamaIndex equivalent: VectorStoreIndex.from_documents(docs).as_query_engine()")
	fmt.Println()

	docs := []Document{
		{
			ID:      "doc1",
			Title:   "Introduction to Agenkit",
			Content: "Agenkit is a cross-language AI agent toolkit supporting Python, Go, TypeScript, Rust, C++, and Zig with 100% feature parity across all languages.",
		},
		{
			ID:      "doc2",
			Title:   "Agenkit Architecture",
			Content: "Agenkit follows a layered architecture: core primitives (Message, Agent), adapters (LLM providers), patterns (Sequential, Parallel, Router), and observability hooks.",
		},
		{
			ID:      "doc3",
			Title:   "Multi-Agent Patterns",
			Content: "Agenkit supports orchestration patterns including SequentialAgent, ParallelAgent, RouterAgent, and SupervisorAgent for building complex multi-agent workflows.",
		},
	}

	index := NewVectorStoreIndex(docs)
	queryEngine := index.AsQueryEngine(ollamaLLM)

	question := "What languages does Agenkit support?"
	fmt.Printf("Query  : %s\n", question)

	retrieved := index.SimilaritySearch(question, 2)
	fmt.Printf("Retrieved %d docs: ", len(retrieved))
	for i, d := range retrieved {
		if i > 0 {
			fmt.Print(", ")
		}
		fmt.Printf("[%s]", d.ID)
	}
	fmt.Println()

	answer, err := queryEngine.Query(ctx, question)
	if err != nil {
		fmt.Fprintf(os.Stderr, "query failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Answer : %s\n", answer)

	// ------------------------------------------------------------------
	// 2. FunctionAgent with a QueryEngineTool
	// ------------------------------------------------------------------
	printSection("2. FunctionAgent with QueryEngineTool")
	fmt.Println("LlamaIndex equivalent: FunctionCallingAgent(tools=[QueryEngineTool(query_engine)])")
	fmt.Println()

	// Wrap the QueryEngine as a LITool.
	qeTool := &LITool{
		name: "knowledge_base",
		desc: "search the Agenkit knowledge base",
		fn: func(args map[string]string) (string, error) {
			return queryEngine.Query(ctx, args["query"])
		},
	}

	agent := NewFunctionAgent(
		"ResearchAgent",
		ollamaLLM,
		"You are a research assistant. Use the knowledge_base tool to answer questions about Agenkit.",
	)
	agent.AddTool(qeTool)

	task1 := "What are the multi-agent patterns supported by Agenkit?"
	fmt.Printf("Task  : %s\n", task1)
	result1, err := agent.Run(ctx, task1)
	if err != nil {
		fmt.Fprintf(os.Stderr, "agent run failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Result: %s\n", result1)

	// ------------------------------------------------------------------
	// 3. AgentWorkflow — researcher + writer with handoff
	// ------------------------------------------------------------------
	printSection("3. AgentWorkflow  (multi-agent routing)")
	fmt.Println("LlamaIndex equivalent: AgentWorkflow(agents=[researcher, writer], root_agent='researcher')")
	fmt.Println()

	searchTool := &LITool{
		name: "search",
		desc: "search for information on a topic",
		fn: func(args map[string]string) (string, error) {
			results := index.SimilaritySearch(args["query"], 2)
			var sb strings.Builder
			for _, d := range results {
				sb.WriteString(fmt.Sprintf("[%s] %s: %s\n", d.ID, d.Title, d.Content))
			}
			return sb.String(), nil
		},
	}

	formatTool := &LITool{
		name: "format",
		desc: "format raw research into a polished summary",
		fn: func(args map[string]string) (string, error) {
			return "Formatted: " + args["query"], nil
		},
	}

	researcher := NewFunctionAgent(
		"researcher",
		ollamaLLM,
		"You are a researcher. Use the search tool to gather information, then respond with your findings. If a writing task is needed, respond with HANDOFF:writer.",
	)
	researcher.AddTool(searchTool)

	writer := NewFunctionAgent(
		"writer",
		ollamaLLM,
		"You are a technical writer. Use the format tool to produce a polished summary of the given research.",
	)
	writer.AddTool(formatTool)

	workflow := NewAgentWorkflow("researcher")
	workflow.AddAgent(researcher)
	workflow.AddAgent(writer)

	task2 := "Research and summarise the architecture of Agenkit."
	fmt.Printf("Task   : %s\n", task2)
	result2, err := workflow.Run(ctx, task2)
	if err != nil {
		fmt.Fprintf(os.Stderr, "workflow run failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Result : %s\n", result2)

	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("MiniLlamaIndex demo complete.")
	fmt.Println()
	fmt.Println("Key takeaways:")
	fmt.Println("  VectorStoreIndex → keyword-overlap retrieval (swap for real embeddings)")
	fmt.Println("  QueryEngine      → retrieve + LLM synthesis = RAG in two lines")
	fmt.Println("  FunctionAgent    → TOOL: directive parsed for single ReAct step")
	fmt.Println("  AgentWorkflow    → HANDOFF: directive routes between named agents")
	fmt.Println()
	fmt.Println("For production use, pair with a real vector DB (pgvector, Weaviate, Qdrant)")
	fmt.Println("and use patterns.NewSequentialAgent for multi-step pipelines.")
}
