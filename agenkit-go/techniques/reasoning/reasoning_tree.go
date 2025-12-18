// Package reasoning provides reasoning techniques and supporting data structures.
package reasoning

import (
	"fmt"
	"strings"
)

// NodeState represents the state of a reasoning node during search.
type NodeState string

const (
	// NodeStateOpen indicates the node is not yet explored.
	NodeStateOpen NodeState = "open"
	// NodeStateActive indicates the node is currently being explored.
	NodeStateActive NodeState = "active"
	// NodeStateEvaluated indicates the node has been evaluated and may have children.
	NodeStateEvaluated NodeState = "evaluated"
	// NodeStatePruned indicates the node has been pruned from search.
	NodeStatePruned NodeState = "pruned"
	// NodeStateTerminal indicates the node is a leaf node (complete reasoning path).
	NodeStateTerminal NodeState = "terminal"
)

// ReasoningNode represents a single node in a reasoning tree.
//
// Each node contains a reasoning step and can branch into multiple child nodes.
type ReasoningNode struct {
	// ID is the unique node identifier.
	ID int
	// Content is the reasoning text for this step.
	Content string
	// ParentID is the ID of the parent node (nil for root).
	ParentID *int
	// ChildrenIDs contains the IDs of all child nodes.
	ChildrenIDs []int
	// Depth is the depth in the tree (0 for root).
	Depth int
	// Score is the evaluation score (0.0-1.0, higher is better).
	Score float64
	// State is the current state in the search process.
	State NodeState
	// Metadata contains additional node-specific data.
	Metadata map[string]interface{}
}

// IsLeaf returns true if this node has no children.
func (n *ReasoningNode) IsLeaf() bool {
	return len(n.ChildrenIDs) == 0
}

// IsRoot returns true if this node has no parent.
func (n *ReasoningNode) IsRoot() bool {
	return n.ParentID == nil
}

// AddChild adds a child node ID to this node.
func (n *ReasoningNode) AddChild(childID int) {
	// Check if already present
	for _, id := range n.ChildrenIDs {
		if id == childID {
			return
		}
	}
	n.ChildrenIDs = append(n.ChildrenIDs, childID)
}

// ReasoningTree represents a tree structure for branching reasoning paths.
//
// The tree manages nodes and provides methods for building, searching,
// and analyzing reasoning paths.
type ReasoningTree struct {
	// nodes maps node ID to ReasoningNode.
	nodes map[int]*ReasoningNode
	// rootID is the ID of the root node.
	rootID *int
	// nextID is the next available node ID.
	nextID int
	// MaxDepth is the maximum depth reached in the tree.
	MaxDepth int
}

// NewReasoningTree creates a new empty reasoning tree.
func NewReasoningTree() *ReasoningTree {
	return &ReasoningTree{
		nodes:    make(map[int]*ReasoningNode),
		rootID:   nil,
		nextID:   0,
		MaxDepth: 0,
	}
}

// CreateRoot creates a root node and returns its ID.
func (t *ReasoningTree) CreateRoot(content string, metadata map[string]interface{}) int {
	nodeID := t.nextID
	t.nextID++

	if metadata == nil {
		metadata = make(map[string]interface{})
	}

	node := &ReasoningNode{
		ID:          nodeID,
		Content:     content,
		ParentID:    nil,
		ChildrenIDs: []int{},
		Depth:       0,
		Score:       0.0,
		State:       NodeStateOpen,
		Metadata:    metadata,
	}

	t.nodes[nodeID] = node
	t.rootID = &nodeID
	return nodeID
}

// AddChild adds a child node to a parent and returns the child ID.
func (t *ReasoningTree) AddChild(parentID int, content string, score float64, metadata map[string]interface{}) (int, error) {
	parent, exists := t.nodes[parentID]
	if !exists {
		return 0, fmt.Errorf("parent node %d not found", parentID)
	}

	childID := t.nextID
	t.nextID++

	if metadata == nil {
		metadata = make(map[string]interface{})
	}

	child := &ReasoningNode{
		ID:          childID,
		Content:     content,
		ParentID:    &parentID,
		ChildrenIDs: []int{},
		Depth:       parent.Depth + 1,
		Score:       score,
		State:       NodeStateOpen,
		Metadata:    metadata,
	}

	t.nodes[childID] = child
	parent.AddChild(childID)

	// Update max depth
	if child.Depth > t.MaxDepth {
		t.MaxDepth = child.Depth
	}

	return childID, nil
}

// GetNode returns the node with the given ID, or nil if not found.
func (t *ReasoningTree) GetNode(nodeID int) *ReasoningNode {
	return t.nodes[nodeID]
}

// GetChildren returns all children of a node.
func (t *ReasoningTree) GetChildren(nodeID int) []*ReasoningNode {
	node := t.nodes[nodeID]
	if node == nil {
		return nil
	}

	children := make([]*ReasoningNode, 0, len(node.ChildrenIDs))
	for _, childID := range node.ChildrenIDs {
		if child, exists := t.nodes[childID]; exists {
			children = append(children, child)
		}
	}
	return children
}

// GetPath returns the path from root to the given node.
func (t *ReasoningTree) GetPath(nodeID int) []*ReasoningNode {
	path := []*ReasoningNode{}
	currentID := &nodeID

	for currentID != nil {
		node, exists := t.nodes[*currentID]
		if !exists {
			break
		}

		// Prepend to path (building from leaf to root)
		path = append([]*ReasoningNode{node}, path...)
		currentID = node.ParentID
	}

	return path
}

// GetPathText returns the concatenated text of the path from root to node.
func (t *ReasoningTree) GetPathText(nodeID int, delimiter string) string {
	path := t.GetPath(nodeID)
	texts := make([]string, len(path))
	for i, node := range path {
		texts[i] = node.Content
	}
	return strings.Join(texts, delimiter)
}

// GetLeaves returns all leaf nodes (nodes with no children).
func (t *ReasoningTree) GetLeaves() []*ReasoningNode {
	leaves := []*ReasoningNode{}
	for _, node := range t.nodes {
		if node.IsLeaf() {
			leaves = append(leaves, node)
		}
	}
	return leaves
}

// GetBestLeaf returns the leaf node with the highest score.
func (t *ReasoningTree) GetBestLeaf() *ReasoningNode {
	leaves := t.GetLeaves()
	if len(leaves) == 0 {
		return nil
	}

	best := leaves[0]
	for _, leaf := range leaves[1:] {
		if leaf.Score > best.Score {
			best = leaf
		}
	}
	return best
}

// PruneNode marks a node as pruned.
func (t *ReasoningTree) PruneNode(nodeID int) {
	if node, exists := t.nodes[nodeID]; exists {
		node.State = NodeStatePruned
	}
}

// TreeStatistics contains statistics about the reasoning tree.
type TreeStatistics struct {
	TotalNodes   int
	MaxDepth     int
	NumLeaves    int
	NumEvaluated int
	NumPruned    int
	AvgScore     float64
	BestScore    float64
}

// GetStatistics returns statistics about the tree.
func (t *ReasoningTree) GetStatistics() TreeStatistics {
	leaves := t.GetLeaves()

	evaluated := 0
	pruned := 0
	for _, node := range t.nodes {
		if node.State == NodeStateEvaluated {
			evaluated++
		}
		if node.State == NodeStatePruned {
			pruned++
		}
	}

	avgScore := 0.0
	bestScore := 0.0
	if len(leaves) > 0 {
		scoreSum := 0.0
		for _, leaf := range leaves {
			scoreSum += leaf.Score
			if leaf.Score > bestScore {
				bestScore = leaf.Score
			}
		}
		avgScore = scoreSum / float64(len(leaves))
	}

	return TreeStatistics{
		TotalNodes:   len(t.nodes),
		MaxDepth:     t.MaxDepth,
		NumLeaves:    len(leaves),
		NumEvaluated: evaluated,
		NumPruned:    pruned,
		AvgScore:     avgScore,
		BestScore:    bestScore,
	}
}

// Size returns the total number of nodes in the tree.
func (t *ReasoningTree) Size() int {
	return len(t.nodes)
}

// GetRootID returns the root node ID, or nil if the tree is empty.
func (t *ReasoningTree) GetRootID() *int {
	return t.rootID
}
