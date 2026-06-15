// Package reasoning provides reasoning data structures for Graph-of-Thought.
package reasoning

import (
	"fmt"
)

// NodeType represents the type of a thought node in the reasoning graph.
type NodeType string

const (
	// NodeTypePremise is a starting assumption or fact.
	NodeTypePremise NodeType = "premise"
	// NodeTypeIntermediate is an intermediate conclusion.
	NodeTypeIntermediate NodeType = "intermediate"
	// NodeTypeConclusion is a final conclusion.
	NodeTypeConclusion NodeType = "conclusion"
)

// EdgeType represents the type of logical connection between nodes.
type EdgeType string

const (
	// EdgeTypeSupports indicates the node supports another.
	EdgeTypeSupports EdgeType = "supports"
	// EdgeTypeDependsOn indicates the node depends on another.
	EdgeTypeDependsOn EdgeType = "depends_on"
	// EdgeTypeContradicts indicates the node contradicts another.
	EdgeTypeContradicts EdgeType = "contradicts"
	// EdgeTypeRefines indicates the node refines/improves another.
	EdgeTypeRefines EdgeType = "refines"
)

// ThoughtNode represents a single thought or conclusion in the reasoning graph.
type ThoughtNode struct {
	// ID is the unique node identifier.
	ID int
	// Content is the thought/conclusion text.
	Content string
	// NodeType is the type of node.
	NodeType NodeType
	// Confidence is the confidence score (0.0-1.0).
	Confidence float64
	// Metadata contains additional node-specific data.
	Metadata map[string]interface{}
}

// LogicalEdge represents a logical connection between two thoughts.
type LogicalEdge struct {
	// FromNode is the source node ID.
	FromNode int
	// ToNode is the target node ID.
	ToNode int
	// EdgeType is the type of logical connection.
	EdgeType EdgeType
	// Strength is the connection strength (0.0-1.0).
	Strength float64
	// Metadata contains additional edge-specific data.
	Metadata map[string]interface{}
}

// ReasoningGraph is a directed graph for representing reasoning structures.
//
// Nodes represent thoughts, conclusions, or premises.
// Edges represent logical connections and dependencies.
//
// Supports:
// - Adding nodes and edges
// - Path finding between nodes
// - Cycle detection
// - Topological sorting
// - Graph statistics
type ReasoningGraph struct {
	// nodes maps node ID to ThoughtNode.
	nodes map[int]*ThoughtNode
	// edges contains all logical edges.
	edges []*LogicalEdge
	// nextID is the next available node ID.
	nextID int
	// outgoing maps node ID to list of target node IDs.
	outgoing map[int][]int
	// incoming maps node ID to list of source node IDs.
	incoming map[int][]int
}

// NewReasoningGraph creates a new empty reasoning graph.
func NewReasoningGraph() *ReasoningGraph {
	return &ReasoningGraph{
		nodes:    make(map[int]*ThoughtNode),
		edges:    []*LogicalEdge{},
		nextID:   0,
		outgoing: make(map[int][]int),
		incoming: make(map[int][]int),
	}
}

// AddNode adds a thought node to the graph and returns its ID.
func (g *ReasoningGraph) AddNode(content string, nodeType NodeType, confidence float64, metadata map[string]interface{}) int {
	nodeID := g.nextID
	g.nextID++

	if metadata == nil {
		metadata = make(map[string]interface{})
	}

	node := &ThoughtNode{
		ID:         nodeID,
		Content:    content,
		NodeType:   nodeType,
		Confidence: confidence,
		Metadata:   metadata,
	}

	g.nodes[nodeID] = node
	g.outgoing[nodeID] = []int{}
	g.incoming[nodeID] = []int{}

	return nodeID
}

// AddEdge adds a logical edge between two nodes.
func (g *ReasoningGraph) AddEdge(fromNode, toNode int, edgeType EdgeType, strength float64, metadata map[string]interface{}) error {
	if _, exists := g.nodes[fromNode]; !exists {
		return fmt.Errorf("source node %d not found", fromNode)
	}
	if _, exists := g.nodes[toNode]; !exists {
		return fmt.Errorf("target node %d not found", toNode)
	}

	if metadata == nil {
		metadata = make(map[string]interface{})
	}

	edge := &LogicalEdge{
		FromNode: fromNode,
		ToNode:   toNode,
		EdgeType: edgeType,
		Strength: strength,
		Metadata: metadata,
	}

	g.edges = append(g.edges, edge)
	g.outgoing[fromNode] = append(g.outgoing[fromNode], toNode)
	g.incoming[toNode] = append(g.incoming[toNode], fromNode)

	return nil
}

// GetNode returns the node with the given ID, or nil if not found.
func (g *ReasoningGraph) GetNode(nodeID int) *ThoughtNode {
	return g.nodes[nodeID]
}

// GetOutgoingEdges returns all edges originating from the node.
func (g *ReasoningGraph) GetOutgoingEdges(nodeID int) []*LogicalEdge {
	result := []*LogicalEdge{}
	for _, edge := range g.edges {
		if edge.FromNode == nodeID {
			result = append(result, edge)
		}
	}
	return result
}

// GetIncomingEdges returns all edges pointing to the node.
func (g *ReasoningGraph) GetIncomingEdges(nodeID int) []*LogicalEdge {
	result := []*LogicalEdge{}
	for _, edge := range g.edges {
		if edge.ToNode == nodeID {
			result = append(result, edge)
		}
	}
	return result
}

// FindPaths finds all paths from start node to end node.
//
// Returns a list of paths, where each path is a list of node IDs.
func (g *ReasoningGraph) FindPaths(start, end int, maxLength int) [][]int {
	if _, exists := g.nodes[start]; !exists {
		return [][]int{}
	}
	if _, exists := g.nodes[end]; !exists {
		return [][]int{}
	}

	paths := [][]int{}
	visited := make(map[int]bool)
	visited[start] = true

	var dfs func(current int, path []int)
	dfs = func(current int, path []int) {
		if current == end {
			// Found a path - make a copy
			pathCopy := make([]int, len(path))
			copy(pathCopy, path)
			paths = append(paths, pathCopy)
			return
		}

		if maxLength > 0 && len(path) >= maxLength {
			return
		}

		for _, nextNode := range g.outgoing[current] {
			if !visited[nextNode] {
				visited[nextNode] = true
				dfs(nextNode, append(path, nextNode))
				delete(visited, nextNode)
			}
		}
	}

	dfs(start, []int{start})
	return paths
}

// HasCycle checks if the graph contains any cycles.
func (g *ReasoningGraph) HasCycle() bool {
	const (
		white = 0 // Not visited
		gray  = 1 // Being processed
		black = 2 // Fully processed
	)

	color := make(map[int]int)
	for nodeID := range g.nodes {
		color[nodeID] = white
	}

	var visit func(nodeID int) bool
	visit = func(nodeID int) bool {
		color[nodeID] = gray

		for _, nextNode := range g.outgoing[nodeID] {
			if color[nextNode] == gray {
				// Back edge found - cycle detected
				return true
			}
			if color[nextNode] == white && visit(nextNode) {
				return true
			}
		}

		color[nodeID] = black
		return false
	}

	for nodeID := range g.nodes {
		if color[nodeID] == white && visit(nodeID) {
			return true
		}
	}

	return false
}

// FindCycles finds all cycles in the graph.
func (g *ReasoningGraph) FindCycles() [][]int {
	cycles := [][]int{}
	visited := make(map[int]bool)
	recStack := []int{}

	var dfs func(nodeID int)
	dfs = func(nodeID int) {
		visited[nodeID] = true
		recStack = append(recStack, nodeID)

		for _, nextNode := range g.outgoing[nodeID] {
			if !visited[nextNode] {
				dfs(nextNode)
			} else {
				// Check if nextNode is in recursion stack
				for i, stackNode := range recStack {
					if stackNode == nextNode {
						// Found cycle
						cycle := make([]int, len(recStack)-i)
						copy(cycle, recStack[i:])
						cycle = append(cycle, nextNode)
						cycles = append(cycles, cycle)
						break
					}
				}
			}
		}

		recStack = recStack[:len(recStack)-1]
	}

	for nodeID := range g.nodes {
		if !visited[nodeID] {
			dfs(nodeID)
		}
	}

	return cycles
}

// TopologicalSort returns nodes in topological order if the graph is acyclic.
//
// Returns nil if the graph has cycles.
func (g *ReasoningGraph) TopologicalSort() []int {
	if g.HasCycle() {
		return nil
	}

	inDegree := make(map[int]int)
	for nodeID := range g.nodes {
		inDegree[nodeID] = len(g.incoming[nodeID])
	}

	queue := []int{}
	for nodeID, degree := range inDegree {
		if degree == 0 {
			queue = append(queue, nodeID)
		}
	}

	result := []int{}
	for len(queue) > 0 {
		nodeID := queue[0]
		queue = queue[1:]
		result = append(result, nodeID)

		for _, nextNode := range g.outgoing[nodeID] {
			inDegree[nextNode]--
			if inDegree[nextNode] == 0 {
				queue = append(queue, nextNode)
			}
		}
	}

	if len(result) != len(g.nodes) {
		return nil
	}
	return result
}

// GetPremises returns all premise nodes.
func (g *ReasoningGraph) GetPremises() []*ThoughtNode {
	premises := []*ThoughtNode{}
	for _, node := range g.nodes {
		if node.NodeType == NodeTypePremise {
			premises = append(premises, node)
		}
	}
	return premises
}

// GetConclusions returns all conclusion nodes.
func (g *ReasoningGraph) GetConclusions() []*ThoughtNode {
	conclusions := []*ThoughtNode{}
	for _, node := range g.nodes {
		if node.NodeType == NodeTypeConclusion {
			conclusions = append(conclusions, node)
		}
	}
	return conclusions
}

// GetPathScore calculates the score for a reasoning path.
//
// Combines node confidence and edge strength.
func (g *ReasoningGraph) GetPathScore(path []int) float64 {
	if len(path) == 0 {
		return 0.0
	}

	// Average node confidences
	totalConfidence := 0.0
	for _, nodeID := range path {
		if node, exists := g.nodes[nodeID]; exists {
			totalConfidence += node.Confidence
		}
	}
	avgNodeScore := totalConfidence / float64(len(path))

	// Average edge strengths
	if len(path) < 2 {
		return avgNodeScore
	}

	totalStrength := 0.0
	edgeCount := 0
	for i := 0; i < len(path)-1; i++ {
		for _, edge := range g.edges {
			if edge.FromNode == path[i] && edge.ToNode == path[i+1] {
				totalStrength += edge.Strength
				edgeCount++
				break
			}
		}
	}

	avgEdgeScore := 1.0
	if edgeCount > 0 {
		avgEdgeScore = totalStrength / float64(edgeCount)
	}

	// Combine scores
	return (avgNodeScore + avgEdgeScore) / 2.0
}

// GraphStatistics contains statistics about the reasoning graph.
type GraphStatistics struct {
	NumNodes      int
	NumEdges      int
	NodeTypes     map[string]int
	EdgeTypes     map[string]int
	HasCycles     bool
	AvgConfidence float64
}

// Statistics returns statistics about the graph.
func (g *ReasoningGraph) Statistics() GraphStatistics {
	nodeTypes := make(map[string]int)
	for _, node := range g.nodes {
		nodeTypes[string(node.NodeType)]++
	}

	edgeTypes := make(map[string]int)
	for _, edge := range g.edges {
		edgeTypes[string(edge.EdgeType)]++
	}

	totalConfidence := 0.0
	for _, node := range g.nodes {
		totalConfidence += node.Confidence
	}
	avgConfidence := 0.0
	if len(g.nodes) > 0 {
		avgConfidence = totalConfidence / float64(len(g.nodes))
	}

	return GraphStatistics{
		NumNodes:      len(g.nodes),
		NumEdges:      len(g.edges),
		NodeTypes:     nodeTypes,
		EdgeTypes:     edgeTypes,
		HasCycles:     g.HasCycle(),
		AvgConfidence: avgConfidence,
	}
}
