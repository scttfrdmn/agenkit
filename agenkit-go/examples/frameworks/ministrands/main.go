//go:build ignore

// ministrands demonstrates AWS Strands-equivalent graph-based agent routing
// using Agenkit.
//
// AWS Strands popularised the "graph" abstraction: nodes that process a message
// and edges that route the result to the next node based on conditions. The
// graph executes step-by-step, following edges until a terminal node (one with
// no matching outbound edge) is reached.
//
//	Node       → a processing step (LLM call or pure function)
//	Edge       → a conditional or unconditional transition between nodes
//	Graph      → the wiring of nodes and edges with a designated start node
//	GraphExecutor → drives execution, enforcing a max-steps safety limit
//
// This file implements lightweight inline versions of each type to make the
// mapping explicit, then demonstrates a 4-node research graph:
//
//	classify  → routes to "technical" or "general" based on input keywords
//	technical → handles technical questions, then routes to "summarize"
//	general   → handles general questions, then routes to "summarize"
//	summarize → produces the final answer (terminal node, no outbound edges)
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
// EdgeCondition — predicate that decides whether to follow an edge
// ---------------------------------------------------------------------------

// EdgeCondition is a predicate evaluated against the output message of a node.
// A nil EdgeCondition means "always follow this edge".
// Equivalent to Strands' conditional edge functions.
type EdgeCondition func(msg *agenkit.Message) bool

// ---------------------------------------------------------------------------
// Edge — directed link between two nodes
// ---------------------------------------------------------------------------

// Edge represents a directed link from one node to another.
// Condition is tested against the source node's output; if nil, the edge is
// always followed. Edges are evaluated in the order they were added.
type Edge struct {
	ToNode    string
	Condition EdgeCondition // nil means always match
}

// ---------------------------------------------------------------------------
// Node — a single processing step in the graph
// ---------------------------------------------------------------------------

// Node is a named processing step. fn receives the accumulated message and
// returns a new message; edges describe which node to visit next.
// Equivalent to Strands' @node decorator.
type Node struct {
	ID    string
	fn    func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error)
	edges []Edge
}

// ---------------------------------------------------------------------------
// Graph — wiring of nodes and edges
// ---------------------------------------------------------------------------

// Graph holds the full node-edge topology for a Strands-style workflow.
// Nodes are identified by string IDs; the executor starts at startNode.
type Graph struct {
	nodes     map[string]*Node
	startNode string
}

// NewGraph creates an empty graph with the given start node ID.
func NewGraph(startNode string) *Graph {
	return &Graph{
		nodes:     make(map[string]*Node),
		startNode: startNode,
	}
}

// AddNode registers a processing function under the given ID and returns g for
// fluent chaining. Panics if a duplicate ID is provided.
func (g *Graph) AddNode(id string, fn func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error)) *Graph {
	if _, exists := g.nodes[id]; exists {
		panic(fmt.Sprintf("ministrands: duplicate node id %q", id))
	}
	g.nodes[id] = &Node{ID: id, fn: fn}
	return g
}

// AddEdge adds an outbound edge from node `from` to node `to`.
// A nil cond means the edge is unconditional. Returns g for fluent chaining.
func (g *Graph) AddEdge(from, to string, cond EdgeCondition) *Graph {
	node, ok := g.nodes[from]
	if !ok {
		panic(fmt.Sprintf("ministrands: unknown source node %q", from))
	}
	node.edges = append(node.edges, Edge{ToNode: to, Condition: cond})
	return g
}

// ---------------------------------------------------------------------------
// GraphExecutor — drives execution through the graph
// ---------------------------------------------------------------------------

// GraphExecutor runs a Graph to completion given an initial string input.
// It enforces a maxSteps limit to prevent infinite loops.
// Equivalent to Strands' graph.run() driver.
type GraphExecutor struct {
	graph    *Graph
	maxSteps int
}

// NewGraphExecutor creates an executor for the given graph with a step limit.
func NewGraphExecutor(graph *Graph, maxSteps int) *GraphExecutor {
	return &GraphExecutor{graph: graph, maxSteps: maxSteps}
}

// Execute starts execution at the graph's start node, routing through edges
// until a terminal node (no matching outbound edge) is reached or maxSteps is
// exhausted. Returns the final node's output message.
func (e *GraphExecutor) Execute(ctx context.Context, input string) (*agenkit.Message, error) {
	current := agenkit.NewMessage("user", input)
	nodeID := e.graph.startNode

	for step := 0; step < e.maxSteps; step++ {
		node, ok := e.graph.nodes[nodeID]
		if !ok {
			return nil, fmt.Errorf("node %q not found in graph", nodeID)
		}

		fmt.Printf("  [graph] step %d → node %q\n", step+1, nodeID)

		out, err := node.fn(ctx, current)
		if err != nil {
			return nil, fmt.Errorf("node %q failed: %w", nodeID, err)
		}
		current = out

		// Find the first matching outbound edge.
		next := ""
		for _, edge := range node.edges {
			if edge.Condition == nil || edge.Condition(current) {
				next = edge.ToNode
				break
			}
		}

		if next == "" {
			// Terminal node — no outbound edge matched.
			fmt.Printf("  [graph] terminal node reached at %q\n", nodeID)
			return current, nil
		}

		nodeID = next
	}

	return nil, fmt.Errorf("graph execution exceeded %d steps", e.maxSteps)
}

// ---------------------------------------------------------------------------
// Node function helpers
// ---------------------------------------------------------------------------

// callLLM sends a single user message to the LLM. On connection errors it
// logs a notice and returns a mock response so the demo can continue.
func callLLM(ctx context.Context, client llm.LLM, prompt string, nodeID string) string {
	resp, err := client.Complete(ctx, []*agenkit.Message{
		agenkit.NewMessage("user", prompt),
	})
	if err != nil {
		if strings.Contains(err.Error(), "connection refused") ||
			strings.Contains(err.Error(), "no such host") {
			fmt.Println("  [LLM not running — returning mock response]")
			return mockResponse(nodeID)
		}
		fmt.Fprintf(os.Stderr, "LLM error in node %q: %v\n", nodeID, err)
		return mockResponse(nodeID)
	}
	return resp.ContentString()
}

// mockResponse returns a canned reply keyed by node ID so the graph can run
// end-to-end without a live LLM.
func mockResponse(nodeID string) string {
	switch nodeID {
	case "classify":
		return "technical"
	case "technical":
		return "This is a technical answer about APIs and code architecture."
	case "general":
		return "This is a general answer covering the topic broadly."
	case "summarize":
		return "Summary: the question has been answered above."
	default:
		return "[mock response]"
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

	ollamaLLM := llm.NewOpenAICompatibleLLM(
		"http://localhost:11434/v1",
		"llama3.2",
		"ollama",
		"", // no API key required for local servers
	)

	fmt.Println("MiniStrands — AWS Strands graph-based routing with Agenkit")
	fmt.Println("Graph: classify → technical|general → summarize")

	// ------------------------------------------------------------------
	// Build the 4-node research graph
	// ------------------------------------------------------------------

	// classify — determines whether the input is technical or general.
	// Routes to "technical" when the LLM response contains "technical";
	// otherwise falls through to "general".
	classifyFn := func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
		prompt := fmt.Sprintf(
			`Classify this question as either "technical" or "general". `+
				`Reply with one word only.\n\nQuestion: %s`,
			msg.ContentString(),
		)
		reply := callLLM(ctx, ollamaLLM, prompt, "classify")
		return agenkit.NewMessage("assistant", reply), nil
	}

	// technical — handles technical questions.
	technicalFn := func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
		prompt := fmt.Sprintf(
			"Answer this technical question concisely: %s",
			msg.ContentString(),
		)
		reply := callLLM(ctx, ollamaLLM, prompt, "technical")
		return agenkit.NewMessage("assistant", reply), nil
	}

	// general — handles general questions.
	generalFn := func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
		prompt := fmt.Sprintf(
			"Answer this general question helpfully: %s",
			msg.ContentString(),
		)
		reply := callLLM(ctx, ollamaLLM, prompt, "general")
		return agenkit.NewMessage("assistant", reply), nil
	}

	// summarize — terminal node, produces the final polished answer.
	summarizeFn := func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
		prompt := fmt.Sprintf(
			"Summarize this answer in one clear sentence: %s",
			msg.ContentString(),
		)
		reply := callLLM(ctx, ollamaLLM, prompt, "summarize")
		return agenkit.NewMessage("assistant", reply), nil
	}

	graph := NewGraph("classify").
		AddNode("classify", classifyFn).
		AddNode("technical", technicalFn).
		AddNode("general", generalFn).
		AddNode("summarize", summarizeFn).
		// classify → technical when the output contains "technical"
		AddEdge("classify", "technical", func(msg *agenkit.Message) bool {
			return strings.Contains(strings.ToLower(msg.ContentString()), "technical")
		}).
		// classify → general otherwise (unconditional fallback)
		AddEdge("classify", "general", nil).
		// both specialist nodes route unconditionally to the summarizer
		AddEdge("technical", "summarize", nil).
		AddEdge("general", "summarize", nil)
	// summarize has no outbound edges → terminal node

	executor := NewGraphExecutor(graph, 10)

	// ------------------------------------------------------------------
	// Run two queries through the graph
	// ------------------------------------------------------------------
	queries := []struct {
		label string
		input string
	}{
		{"technical query", "How do I fix a connection refused error when calling an API?"},
		{"general query", "What is the history of the Go programming language?"},
	}

	for _, q := range queries {
		printSection(fmt.Sprintf("Query (%s)", q.label))
		fmt.Printf("Input : %s\n", q.input)

		result, err := executor.Execute(ctx, q.input)
		if err != nil {
			fmt.Fprintf(os.Stderr, "execution error: %v\n", err)
			continue
		}

		fmt.Printf("Result: %s\n", result.ContentString())
	}

	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("MiniStrands demo complete.")
	fmt.Println()
	fmt.Println("Key takeaways:")
	fmt.Println("  Node         → named function: context + message → message")
	fmt.Println("  Edge         → conditional or unconditional link between nodes")
	fmt.Println("  EdgeCondition → predicate on the source node's output message")
	fmt.Println("  GraphExecutor → drives execution, enforces step limit")
	fmt.Println("  Terminal node → no matching outbound edge → execution ends")
}
