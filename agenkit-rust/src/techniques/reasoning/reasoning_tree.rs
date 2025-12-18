// Reasoning Tree Data Structure for Tree-of-Thought
//
// Provides a tree structure for exploring multiple reasoning paths with
// branching, evaluation, pruning, and backtracking capabilities.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// State of a reasoning node in the tree.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NodeState {
    /// Node created but not yet explored
    Open,
    /// Node currently being explored
    Active,
    /// Node has been scored but not yet pruned/terminated
    Evaluated,
    /// Node pruned due to low score
    Pruned,
    /// Node is a leaf/endpoint
    Terminal,
}

/// Individual node in the reasoning tree.
#[derive(Debug, Clone)]
pub struct ReasoningNode {
    pub id: usize,
    pub content: String,
    pub parent_id: Option<usize>,
    pub children_ids: Vec<usize>,
    pub depth: usize,
    pub score: f64,
    pub state: NodeState,
    pub metadata: HashMap<String, serde_json::Value>,
}

impl ReasoningNode {
    /// Check if this is a leaf node.
    pub fn is_leaf(&self) -> bool {
        self.children_ids.is_empty()
    }

    /// Check if this is the root node.
    pub fn is_root(&self) -> bool {
        self.parent_id.is_none()
    }

    /// Add a child to this node.
    pub fn add_child(&mut self, child_id: usize) {
        self.children_ids.push(child_id);
    }
}

/// Statistics about the reasoning tree.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TreeStatistics {
    pub total_nodes: usize,
    pub max_depth: usize,
    pub num_leaves: usize,
    pub num_pruned: usize,
    pub best_score: f64,
    pub avg_score: f64,
}

/// Tree structure for multi-path reasoning exploration.
///
/// ReasoningTree manages a tree of reasoning nodes with support for:
/// - Creating root and adding children
/// - Path retrieval and text generation
/// - Finding best leaf nodes
/// - Pruning low-quality branches
/// - Collecting tree statistics
pub struct ReasoningTree {
    nodes: HashMap<usize, ReasoningNode>,
    root_id: Option<usize>,
    next_id: usize,
    max_depth: usize,
}

impl ReasoningTree {
    /// Create a new empty reasoning tree.
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
            root_id: None,
            next_id: 0,
            max_depth: 0,
        }
    }

    /// Create the root node of the tree.
    pub fn create_root(&mut self, content: String) -> usize {
        let node_id = self.next_id;
        self.next_id += 1;

        let node = ReasoningNode {
            id: node_id,
            content,
            parent_id: None,
            children_ids: Vec::new(),
            depth: 0,
            score: 0.0,
            state: NodeState::Open,
            metadata: HashMap::new(),
        };

        self.nodes.insert(node_id, node);
        self.root_id = Some(node_id);
        self.max_depth = 0;

        node_id
    }

    /// Add a child node to a parent.
    pub fn add_child(&mut self, parent_id: usize, content: String, score: f64) -> Result<usize, String> {
        let parent_depth = {
            let parent = self.nodes.get(&parent_id)
                .ok_or_else(|| format!("Parent node {} not found", parent_id))?;
            parent.depth
        };

        let child_id = self.next_id;
        self.next_id += 1;

        let child = ReasoningNode {
            id: child_id,
            content,
            parent_id: Some(parent_id),
            children_ids: Vec::new(),
            depth: parent_depth + 1,
            score,
            state: NodeState::Open,
            metadata: HashMap::new(),
        };

        if child.depth > self.max_depth {
            self.max_depth = child.depth;
        }

        self.nodes.insert(child_id, child);

        // Add child to parent's children list
        if let Some(parent) = self.nodes.get_mut(&parent_id) {
            parent.add_child(child_id);
        }

        Ok(child_id)
    }

    /// Get a node by ID.
    pub fn get_node(&self, node_id: usize) -> Option<&ReasoningNode> {
        self.nodes.get(&node_id)
    }

    /// Get a mutable node by ID.
    pub fn get_node_mut(&mut self, node_id: usize) -> Option<&mut ReasoningNode> {
        self.nodes.get_mut(&node_id)
    }

    /// Get the path from root to a specific node.
    pub fn get_path(&self, node_id: usize) -> Vec<&ReasoningNode> {
        let mut path = Vec::new();
        let mut current_id = Some(node_id);

        while let Some(id) = current_id {
            if let Some(node) = self.nodes.get(&id) {
                path.push(node);
                current_id = node.parent_id;
            } else {
                break;
            }
        }

        path.reverse();
        path
    }

    /// Get path content as concatenated text.
    pub fn get_path_text(&self, node_id: usize, delimiter: &str) -> String {
        let path = self.get_path(node_id);
        path.iter()
            .map(|node| node.content.as_str())
            .collect::<Vec<_>>()
            .join(delimiter)
    }

    /// Find the best leaf node (highest score).
    pub fn get_best_leaf(&self) -> Option<&ReasoningNode> {
        self.nodes
            .values()
            .filter(|node| node.is_leaf() && node.state != NodeState::Pruned)
            .max_by(|a, b| a.score.partial_cmp(&b.score).unwrap_or(std::cmp::Ordering::Equal))
    }

    /// Prune a node and all its descendants.
    pub fn prune_node(&mut self, node_id: usize) {
        self.prune_recursive(node_id);
    }

    /// Recursively prune a node and its descendants.
    fn prune_recursive(&mut self, node_id: usize) {
        if let Some(node) = self.nodes.get(&node_id) {
            let children_ids = node.children_ids.clone();

            // Mark this node as pruned
            if let Some(node) = self.nodes.get_mut(&node_id) {
                node.state = NodeState::Pruned;
            }

            // Recursively prune all children
            for child_id in children_ids {
                self.prune_recursive(child_id);
            }
        }
    }

    /// Get statistics about the tree.
    pub fn get_statistics(&self) -> TreeStatistics {
        let mut num_leaves = 0;
        let mut num_pruned = 0;
        let mut best_score = 0.0;
        let mut sum_scores = 0.0;
        let mut scored_nodes = 0;

        for node in self.nodes.values() {
            if node.is_leaf() {
                num_leaves += 1;
            }

            if node.state == NodeState::Pruned {
                num_pruned += 1;
            }

            // Track scores (exclude root which has score 0.0)
            if !node.is_root() {
                sum_scores += node.score;
                scored_nodes += 1;
                if node.score > best_score {
                    best_score = node.score;
                }
            }
        }

        let avg_score = if scored_nodes > 0 {
            sum_scores / scored_nodes as f64
        } else {
            0.0
        };

        TreeStatistics {
            total_nodes: self.nodes.len(),
            max_depth: self.max_depth,
            num_leaves,
            num_pruned,
            best_score,
            avg_score,
        }
    }

    /// Get the maximum depth of the tree.
    pub fn max_depth(&self) -> usize {
        self.max_depth
    }

    /// Get the root node ID.
    pub fn root_id(&self) -> Option<usize> {
        self.root_id
    }
}

impl Default for ReasoningTree {
    fn default() -> Self {
        Self::new()
    }
}
