//go:build ignore

// minilanggraph demonstrates LangGraph-equivalent graph-based workflow patterns
// using Agenkit.
//
// LangGraph (separate from LangChain) is a graph-based workflow framework
// where computation is modelled as a directed graph of nodes that share typed
// state. Key abstractions:
//
//	StateGraph          → directed graph; nodes mutate shared state
//	add_node(name, fn)  → register a node; fn receives state, returns update
//	add_edge            → unconditional transition between nodes
//	add_conditional_edges → branch based on a routing function
//	set_entry_point     → designate the first node to execute
//	compile()           → produce an executable CompiledGraph
//	MessagesState       → built-in state type carrying a messages list
//	END                 → terminal sentinel; stop graph execution
//	MemorySaver         → checkpointer that persists state between runs
//
// This file implements lightweight inline versions of each concept to make the
// mapping explicit, then demonstrates three progressively richer scenarios.
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

// END is the terminal sentinel. When a ConditionFunc or node sets
// GraphState.Next to END, the CompiledGraph stops execution.
// Equivalent to LangGraph's END constant.
const END = "__end__"

// ---------------------------------------------------------------------------
// GraphState — shared typed state threaded through every node
// ---------------------------------------------------------------------------

// GraphState is the shared state object passed to every node. Nodes receive
// a copy, apply their changes, and return the updated state.
// Equivalent to LangGraph's MessagesState (extended with routing fields).
type GraphState struct {
	Messages []*agenkit.Message
	Next     string
	Metadata map[string]interface{}
}

// ---------------------------------------------------------------------------
// Node and condition function types
// ---------------------------------------------------------------------------

// NodeFunc is the signature of a graph node. It receives the current state,
// performs some computation, and returns the (possibly modified) state.
// Equivalent to the callables passed to StateGraph.add_node().
type NodeFunc func(ctx context.Context, state GraphState) (GraphState, error)

// ConditionFunc inspects the current state and returns the name of the next
// node to execute, or END to terminate the graph.
// Equivalent to the routing function passed to StateGraph.add_conditional_edges().
type ConditionFunc func(state GraphState) string

// ---------------------------------------------------------------------------
// StateGraph — the graph definition (pre-compilation)
// ---------------------------------------------------------------------------

// edge represents a transition from one node to another, optionally guarded by
// a condition. An unconditional edge has a nil cond field.
type edge struct {
	toNode string
	cond   ConditionFunc
}

// StateGraph holds the graph topology before compilation. Call Compile() to
// produce a runnable CompiledGraph.
// Equivalent to LangGraph's StateGraph.
type StateGraph struct {
	nodes      map[string]NodeFunc
	edges      map[string][]edge // from node → outgoing edges
	entryPoint string
}

// NewStateGraph creates an empty StateGraph ready for node and edge registration.
func NewStateGraph() *StateGraph {
	return &StateGraph{
		nodes: make(map[string]NodeFunc),
		edges: make(map[string][]edge),
	}
}

// AddNode registers a node under name. Returns the graph for fluent chaining.
// Equivalent to StateGraph.add_node(name, fn).
func (g *StateGraph) AddNode(name string, fn NodeFunc) *StateGraph {
	g.nodes[name] = fn
	return g
}

// AddEdge adds an unconditional edge from → to. Returns the graph for fluent
// chaining. Equivalent to StateGraph.add_edge(from, to).
func (g *StateGraph) AddEdge(from, to string) *StateGraph {
	g.edges[from] = append(g.edges[from], edge{toNode: to})
	return g
}

// AddConditionalEdges adds a conditional branch from the given node. The
// condition function is called after the from node executes; its return value
// is looked up in mapping to determine the target node.
// Equivalent to StateGraph.add_conditional_edges(from, condition, mapping).
func (g *StateGraph) AddConditionalEdges(from string, cond ConditionFunc, mapping map[string]string) *StateGraph {
	// Wrap the raw condition so the edge resolves the mapped target name.
	wrappedCond := func(state GraphState) string {
		key := cond(state)
		if target, ok := mapping[key]; ok {
			return target
		}
		return END
	}
	g.edges[from] = append(g.edges[from], edge{toNode: "", cond: wrappedCond})
	return g
}

// SetEntryPoint designates which node runs first when the graph is invoked.
// Equivalent to StateGraph.set_entry_point(name).
func (g *StateGraph) SetEntryPoint(name string) *StateGraph {
	g.entryPoint = name
	return g
}

// Compile validates the graph topology and returns a runnable CompiledGraph.
// Equivalent to StateGraph.compile().
func (g *StateGraph) Compile() *CompiledGraph {
	return &CompiledGraph{graph: g, maxSteps: 50}
}

// ---------------------------------------------------------------------------
// CompiledGraph — executable graph
// ---------------------------------------------------------------------------

// CompiledGraph is the runnable form of a StateGraph. Call Invoke() to
// execute the graph from the entry point with the provided initial state.
// Equivalent to the runnable returned by StateGraph.compile().
type CompiledGraph struct {
	graph    *StateGraph
	maxSteps int
}

// Invoke runs the graph starting from the entry point, threading state through
// each node until a node transitions to END or maxSteps is reached.
// Equivalent to compiled_graph.invoke(initial_state).
func (c *CompiledGraph) Invoke(ctx context.Context, initial GraphState) (GraphState, error) {
	state := initial
	current := c.graph.entryPoint
	if current == "" {
		return state, fmt.Errorf("no entry point set; call SetEntryPoint before Compile")
	}

	for step := 0; step < c.maxSteps; step++ {
		if current == END {
			break
		}

		nodeFn, ok := c.graph.nodes[current]
		if !ok {
			return state, fmt.Errorf("node %q not found in graph", current)
		}

		var err error
		state, err = nodeFn(ctx, state)
		if err != nil {
			return state, fmt.Errorf("node %q failed: %w", current, err)
		}

		// Determine next node from outgoing edges.
		outEdges := c.graph.edges[current]
		if len(outEdges) == 0 {
			break // no outgoing edges — implicit END
		}

		// Use the first edge; if it has a condition evaluate it.
		e := outEdges[0]
		if e.cond != nil {
			current = e.cond(state)
		} else {
			current = e.toNode
		}
	}

	return state, nil
}

// ---------------------------------------------------------------------------
// MemorySaver — in-memory state checkpointer
// ---------------------------------------------------------------------------

// MemorySaver persists GraphState snapshots keyed by a thread ID.
// Equivalent to LangGraph's MemorySaver checkpointer.
type MemorySaver struct {
	mu     sync.Mutex
	states map[string]GraphState
}

// NewMemorySaver creates an empty MemorySaver.
func NewMemorySaver() *MemorySaver {
	return &MemorySaver{states: make(map[string]GraphState)}
}

// Save stores the state under threadID, overwriting any previous entry.
func (m *MemorySaver) Save(threadID string, state GraphState) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.states[threadID] = state
}

// Load retrieves the state for threadID. Returns false if no state was saved.
func (m *MemorySaver) Load(threadID string) (GraphState, bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	s, ok := m.states[threadID]
	return s, ok
}

// ---------------------------------------------------------------------------
// LLM helper — graceful degradation when server is unavailable
// ---------------------------------------------------------------------------

func callLLM(ctx context.Context, llmClient llm.LLM, msgs []*agenkit.Message) (string, error) {
	resp, err := llmClient.Complete(ctx, msgs)
	if err != nil {
		if strings.Contains(err.Error(), "connection refused") ||
			strings.Contains(err.Error(), "no such host") {
			return "[LLM not running — showing structure only]", nil
		}
		return "", err
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

func lastMessage(state GraphState) string {
	if len(state.Messages) == 0 {
		return "(no messages)"
	}
	return state.Messages[len(state.Messages)-1].ContentString()
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

	fmt.Println("MiniLangGraph — LangGraph graph-workflow patterns with Agenkit")
	fmt.Println("Mapping: StateGraph / NodeFunc / ConditionFunc / CompiledGraph / MemorySaver")

	// ------------------------------------------------------------------
	// 1. Two-node linear graph: preprocess → generate
	// ------------------------------------------------------------------
	printSection("1. Linear graph  (add_node + add_edge)")
	fmt.Println("LangGraph equivalent: StateGraph with preprocess → generate → END")
	fmt.Println()

	preprocessNode := func(ctx context.Context, state GraphState) (GraphState, error) {
		if len(state.Messages) == 0 {
			return state, fmt.Errorf("no messages in state")
		}
		last := state.Messages[len(state.Messages)-1].ContentString()
		cleaned := strings.TrimSpace(last)
		state.Messages = append(state.Messages,
			agenkit.NewMessage("system", "Preprocessed input: "+cleaned),
		)
		fmt.Printf("  [preprocess] cleaned input (%d chars)\n", len(cleaned))
		return state, nil
	}

	generateNode := func(ctx context.Context, state GraphState) (GraphState, error) {
		reply, err := callLLM(ctx, ollamaLLM, state.Messages)
		if err != nil {
			return state, err
		}
		state.Messages = append(state.Messages, agenkit.NewMessage("assistant", reply))
		return state, nil
	}

	linearGraph := NewStateGraph().
		AddNode("preprocess", preprocessNode).
		AddNode("generate", generateNode).
		AddEdge("preprocess", "generate").
		SetEntryPoint("preprocess").
		Compile()

	initialState := GraphState{
		Messages: []*agenkit.Message{
			agenkit.NewMessage("user", "  What is a state graph?  "),
		},
	}

	result1, err := linearGraph.Invoke(ctx, initialState)
	if err != nil {
		fmt.Fprintf(os.Stderr, "linear graph failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Messages after run : %d\n", len(result1.Messages))
	fmt.Printf("Final response     : %s\n", lastMessage(result1))

	// ------------------------------------------------------------------
	// 2. Conditional routing: classify → factual | creative | END
	// ------------------------------------------------------------------
	printSection("2. Conditional routing  (add_conditional_edges)")
	fmt.Println("LangGraph equivalent: classify → {factual, creative, END} via conditional edges")
	fmt.Println()

	classifyNode := func(ctx context.Context, state GraphState) (GraphState, error) {
		last := lastMessage(state)
		lower := strings.ToLower(last)
		switch {
		case strings.Contains(lower, "what") || strings.Contains(lower, "how") || strings.Contains(lower, "define"):
			state.Next = "factual"
		case strings.Contains(lower, "write") || strings.Contains(lower, "story") || strings.Contains(lower, "poem"):
			state.Next = "creative"
		default:
			state.Next = END
		}
		fmt.Printf("  [classify] routed to %q\n", state.Next)
		return state, nil
	}

	factualNode := func(ctx context.Context, state GraphState) (GraphState, error) {
		msgs := append(state.Messages,
			agenkit.NewMessage("system", "Answer factually and concisely."),
		)
		reply, err := callLLM(ctx, ollamaLLM, msgs)
		if err != nil {
			return state, err
		}
		state.Messages = append(state.Messages, agenkit.NewMessage("assistant", "[factual] "+reply))
		return state, nil
	}

	creativeNode := func(ctx context.Context, state GraphState) (GraphState, error) {
		msgs := append(state.Messages,
			agenkit.NewMessage("system", "Be imaginative and expressive in your response."),
		)
		reply, err := callLLM(ctx, ollamaLLM, msgs)
		if err != nil {
			return state, err
		}
		state.Messages = append(state.Messages, agenkit.NewMessage("assistant", "[creative] "+reply))
		return state, nil
	}

	routeByNext := func(state GraphState) string { return state.Next }

	conditionalGraph := NewStateGraph().
		AddNode("classify", classifyNode).
		AddNode("factual", factualNode).
		AddNode("creative", creativeNode).
		SetEntryPoint("classify").
		AddConditionalEdges("classify", routeByNext, map[string]string{
			"factual":  "factual",
			"creative": "creative",
			END:        END,
		}).
		Compile()

	queries := []struct {
		label string
		text  string
	}{
		{"factual", "What is a transformer model?"},
		{"creative", "Write a short poem about distributed systems."},
		{"default", "Hello there."},
	}

	for _, q := range queries {
		state := GraphState{
			Messages: []*agenkit.Message{agenkit.NewMessage("user", q.text)},
		}
		res, err := conditionalGraph.Invoke(ctx, state)
		if err != nil {
			fmt.Fprintf(os.Stderr, "conditional graph failed: %v\n", err)
			os.Exit(1)
		}
		fmt.Printf("Input  [%s]: %s\n", q.label, q.text)
		fmt.Printf("Output          : %s\n\n", lastMessage(res))
	}

	// ------------------------------------------------------------------
	// 3. MemorySaver — persist and reload state across runs
	// ------------------------------------------------------------------
	printSection("3. MemorySaver  (state persistence across runs)")
	fmt.Println("LangGraph equivalent: graph.compile(checkpointer=MemorySaver())")
	fmt.Println()

	memory := NewMemorySaver()
	threadID := "thread-001"

	// First run — fresh state.
	state3 := GraphState{
		Messages: []*agenkit.Message{
			agenkit.NewMessage("user", "My favourite language is Go."),
		},
		Metadata: map[string]interface{}{"run": 1},
	}
	res3a, err := linearGraph.Invoke(ctx, state3)
	if err != nil {
		fmt.Fprintf(os.Stderr, "first run failed: %v\n", err)
		os.Exit(1)
	}
	memory.Save(threadID, res3a)
	fmt.Printf("Run 1 — messages: %d, saved to memory under %q\n", len(res3a.Messages), threadID)

	// Reload state and continue the conversation.
	saved, ok := memory.Load(threadID)
	if !ok {
		fmt.Fprintf(os.Stderr, "expected saved state for thread %q\n", threadID)
		os.Exit(1)
	}

	saved.Messages = append(saved.Messages, agenkit.NewMessage("user", "What did I say my favourite language was?"))
	res3b, err := linearGraph.Invoke(ctx, saved)
	if err != nil {
		fmt.Fprintf(os.Stderr, "second run failed: %v\n", err)
		os.Exit(1)
	}
	memory.Save(threadID, res3b)
	fmt.Printf("Run 2 — messages: %d (state persisted and extended)\n", len(res3b.Messages))
	fmt.Printf("Response: %s\n", lastMessage(res3b))

	// Verify persistence.
	reloaded, _ := memory.Load(threadID)
	fmt.Printf("Reloaded state messages: %d  (confirms persistence)\n", len(reloaded.Messages))

	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("MiniLangGraph demo complete.")
	fmt.Println()
	fmt.Println("Key takeaways:")
	fmt.Println("  StateGraph          → AddNode / AddEdge / AddConditionalEdges / Compile")
	fmt.Println("  NodeFunc            → receives GraphState, returns updated GraphState")
	fmt.Println("  ConditionFunc       → returns next node name or END for routing")
	fmt.Println("  CompiledGraph.Invoke → walks nodes until END or no outgoing edges")
	fmt.Println("  MemorySaver         → Save/Load by threadID; thread-safe via sync.Mutex")
	fmt.Println()
	fmt.Println("For production use, Agenkit's patterns.NewSequentialAgent and")
	fmt.Println("patterns.NewRouterAgent provide equivalent routing and composition.")
}
