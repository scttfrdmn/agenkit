// Reasoning Graph Data Structure for Graph-of-Thought
//
// Provides a directed graph structure for representing reasoning as nodes
// (thoughts/conclusions) connected by edges (logical relationships).
//
// This is more flexible than tree-based approaches, allowing for:
// - Multiple reasoning paths
// - Complex dependencies
// - Cycle detection for circular reasoning
// - Path aggregation
//
// Reference: Graph-of-Thought paper: https://arxiv.org/abs/2308.09687

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

/// Type of thought node in the graph.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum NodeType {
    /// Starting assumption or fact
    Premise,
    /// Intermediate conclusion
    Intermediate,
    /// Final conclusion
    Conclusion,
}

/// Type of logical connection between nodes.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum EdgeType {
    /// Node supports another
    Supports,
    /// Node depends on another
    DependsOn,
    /// Node contradicts another
    Contradicts,
    /// Node refines/improves another
    Refines,
}

/// A single thought or conclusion in the reasoning graph.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThoughtNode {
    /// Unique node identifier
    pub id: usize,
    /// Thought/conclusion text
    pub content: String,
    /// Type of node
    pub node_type: NodeType,
    /// Confidence score (0.0-1.0)
    pub confidence: f64,
    /// Additional node-specific data
    #[serde(skip_serializing_if = "HashMap::is_empty", default)]
    pub metadata: HashMap<String, String>,
}

/// A logical connection between two thoughts.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogicalEdge {
    /// Source node ID
    pub from_node: usize,
    /// Target node ID
    pub to_node: usize,
    /// Type of logical connection
    pub edge_type: EdgeType,
    /// Connection strength (0.0-1.0)
    pub strength: f64,
    /// Additional edge-specific data
    #[serde(skip_serializing_if = "HashMap::is_empty", default)]
    pub metadata: HashMap<String, String>,
}

/// Graph statistics for analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphStatistics {
    /// Number of nodes in graph
    pub num_nodes: usize,
    /// Number of edges in graph
    pub num_edges: usize,
    /// Whether graph contains cycles
    pub has_cycles: bool,
    /// Count of each node type
    pub node_types: HashMap<String, usize>,
    /// Count of each edge type
    pub edge_types: HashMap<String, usize>,
}

/// Directed graph for representing reasoning structures.
///
/// Nodes represent thoughts, conclusions, or premises.
/// Edges represent logical connections and dependencies.
///
/// Supports:
/// - Adding nodes and edges
/// - Path finding between nodes
/// - Cycle detection
/// - Graph statistics
pub struct ReasoningGraph {
    nodes: HashMap<usize, ThoughtNode>,
    edges: Vec<LogicalEdge>,
    next_id: usize,
    // Adjacency lists for efficient traversal
    outgoing: HashMap<usize, Vec<usize>>,
    incoming: HashMap<usize, Vec<usize>>,
}

impl ReasoningGraph {
    /// Create a new empty reasoning graph.
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
            edges: Vec::new(),
            next_id: 0,
            outgoing: HashMap::new(),
            incoming: HashMap::new(),
        }
    }

    /// Add a thought node to the graph.
    ///
    /// # Arguments
    /// * `content` - The thought/conclusion content
    /// * `node_type` - Type of node (premise, intermediate, conclusion)
    /// * `confidence` - Confidence score 0.0 to 1.0
    ///
    /// # Returns
    /// Node ID
    pub fn add_node(&mut self, content: String, node_type: NodeType, confidence: f64) -> usize {
        let node_id = self.next_id;
        self.next_id += 1;

        let node = ThoughtNode {
            id: node_id,
            content,
            node_type,
            confidence,
            metadata: HashMap::new(),
        };

        self.nodes.insert(node_id, node);
        self.outgoing.insert(node_id, Vec::new());
        self.incoming.insert(node_id, Vec::new());

        node_id
    }

    /// Add a logical edge between two nodes.
    ///
    /// # Arguments
    /// * `from_node` - Source node ID
    /// * `to_node` - Target node ID
    /// * `edge_type` - Type of logical connection
    /// * `strength` - Connection strength 0.0 to 1.0
    ///
    /// # Errors
    /// Returns an error if either node doesn't exist
    pub fn add_edge(
        &mut self,
        from_node: usize,
        to_node: usize,
        edge_type: EdgeType,
        strength: f64,
    ) -> Result<(), String> {
        if !self.nodes.contains_key(&from_node) || !self.nodes.contains_key(&to_node) {
            return Err("Both nodes must exist in graph".to_string());
        }

        let edge = LogicalEdge {
            from_node,
            to_node,
            edge_type,
            strength,
            metadata: HashMap::new(),
        };

        self.edges.push(edge);
        self.outgoing.get_mut(&from_node).unwrap().push(to_node);
        self.incoming.get_mut(&to_node).unwrap().push(from_node);

        Ok(())
    }

    /// Get node by ID.
    pub fn get_node(&self, node_id: usize) -> Option<&ThoughtNode> {
        self.nodes.get(&node_id)
    }

    /// Get all premise nodes.
    pub fn get_premises(&self) -> Vec<&ThoughtNode> {
        self.nodes
            .values()
            .filter(|n| n.node_type == NodeType::Premise)
            .collect()
    }

    /// Get all conclusion nodes.
    pub fn get_conclusions(&self) -> Vec<&ThoughtNode> {
        self.nodes
            .values()
            .filter(|n| n.node_type == NodeType::Conclusion)
            .collect()
    }

    /// Find all paths from start to end node.
    ///
    /// # Arguments
    /// * `start` - Start node ID
    /// * `end` - End node ID
    /// * `max_length` - Maximum path length
    ///
    /// # Returns
    /// Array of paths (each path is array of node IDs)
    pub fn find_paths(&self, start: usize, end: usize, max_length: usize) -> Vec<Vec<usize>> {
        let mut paths = Vec::new();
        let mut visited = HashSet::new();
        let mut current_path = Vec::new();

        self.dfs_paths(
            start,
            end,
            max_length,
            &mut visited,
            &mut current_path,
            &mut paths,
        );

        paths
    }

    fn dfs_paths(
        &self,
        current: usize,
        end: usize,
        max_length: usize,
        visited: &mut HashSet<usize>,
        path: &mut Vec<usize>,
        paths: &mut Vec<Vec<usize>>,
    ) {
        if path.len() > max_length {
            return;
        }

        if current == end {
            let mut complete_path = path.clone();
            complete_path.push(current);
            paths.push(complete_path);
            return;
        }

        if visited.contains(&current) {
            return;
        }

        visited.insert(current);
        path.push(current);

        if let Some(neighbors) = self.outgoing.get(&current) {
            for &neighbor in neighbors {
                self.dfs_paths(neighbor, end, max_length, visited, path, paths);
            }
        }

        path.pop();
        visited.remove(&current);
    }

    /// Check if graph contains cycles.
    pub fn has_cycle(&self) -> bool {
        let mut visited = HashSet::new();
        let mut rec_stack = HashSet::new();

        for &node_id in self.nodes.keys() {
            if !visited.contains(&node_id)
                && self.has_cycle_dfs(node_id, &mut visited, &mut rec_stack)
            {
                return true;
            }
        }

        false
    }

    fn has_cycle_dfs(
        &self,
        node_id: usize,
        visited: &mut HashSet<usize>,
        rec_stack: &mut HashSet<usize>,
    ) -> bool {
        visited.insert(node_id);
        rec_stack.insert(node_id);

        if let Some(neighbors) = self.outgoing.get(&node_id) {
            for &neighbor in neighbors {
                if !visited.contains(&neighbor) {
                    if self.has_cycle_dfs(neighbor, visited, rec_stack) {
                        return true;
                    }
                } else if rec_stack.contains(&neighbor) {
                    return true;
                }
            }
        }

        rec_stack.remove(&node_id);
        false
    }

    /// Calculate score for a reasoning path.
    ///
    /// # Arguments
    /// * `path` - Array of node IDs
    ///
    /// # Returns
    /// Path score (higher is better)
    pub fn get_path_score(&self, path: &[usize]) -> f64 {
        let mut score = 0.0;

        // Add confidence scores
        for &node_id in path {
            if let Some(node) = self.nodes.get(&node_id) {
                score += node.confidence;
            }
        }

        // Add edge strengths
        for i in 0..path.len().saturating_sub(1) {
            let from_node = path[i];
            let to_node = path[i + 1];

            if let Some(edge) = self
                .edges
                .iter()
                .find(|e| e.from_node == from_node && e.to_node == to_node)
            {
                score += edge.strength;
            }
        }

        score
    }

    /// Get graph statistics for analysis.
    pub fn statistics(&self) -> GraphStatistics {
        let mut node_types = HashMap::new();
        node_types.insert("premise".to_string(), 0);
        node_types.insert("intermediate".to_string(), 0);
        node_types.insert("conclusion".to_string(), 0);

        for node in self.nodes.values() {
            let key = match node.node_type {
                NodeType::Premise => "premise",
                NodeType::Intermediate => "intermediate",
                NodeType::Conclusion => "conclusion",
            };
            *node_types.get_mut(key).unwrap() += 1;
        }

        let mut edge_types = HashMap::new();
        edge_types.insert("supports".to_string(), 0);
        edge_types.insert("depends_on".to_string(), 0);
        edge_types.insert("contradicts".to_string(), 0);
        edge_types.insert("refines".to_string(), 0);

        for edge in &self.edges {
            let key = match edge.edge_type {
                EdgeType::Supports => "supports",
                EdgeType::DependsOn => "depends_on",
                EdgeType::Contradicts => "contradicts",
                EdgeType::Refines => "refines",
            };
            *edge_types.get_mut(key).unwrap() += 1;
        }

        GraphStatistics {
            num_nodes: self.nodes.len(),
            num_edges: self.edges.len(),
            has_cycles: self.has_cycle(),
            node_types,
            edge_types,
        }
    }

    /// Get all nodes in the graph.
    pub fn get_nodes(&self) -> Vec<&ThoughtNode> {
        self.nodes.values().collect()
    }

    /// Get all edges in the graph.
    pub fn get_edges(&self) -> &[LogicalEdge] {
        &self.edges
    }
}

impl Default for ReasoningGraph {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add_node() {
        let mut graph = ReasoningGraph::new();
        let id = graph.add_node("Test node".to_string(), NodeType::Premise, 0.9);
        assert_eq!(id, 0);
        assert_eq!(graph.get_nodes().len(), 1);
    }

    #[test]
    fn test_add_edge() {
        let mut graph = ReasoningGraph::new();
        let id1 = graph.add_node("Node 1".to_string(), NodeType::Premise, 0.9);
        let id2 = graph.add_node("Node 2".to_string(), NodeType::Intermediate, 0.8);

        let result = graph.add_edge(id1, id2, EdgeType::Supports, 0.9);
        assert!(result.is_ok());
        assert_eq!(graph.get_edges().len(), 1);
    }

    #[test]
    fn test_add_edge_invalid_nodes() {
        let mut graph = ReasoningGraph::new();
        let result = graph.add_edge(0, 1, EdgeType::Supports, 0.9);
        assert!(result.is_err());
    }

    #[test]
    fn test_get_premises_and_conclusions() {
        let mut graph = ReasoningGraph::new();
        graph.add_node("Premise".to_string(), NodeType::Premise, 0.9);
        graph.add_node("Intermediate".to_string(), NodeType::Intermediate, 0.8);
        graph.add_node("Conclusion".to_string(), NodeType::Conclusion, 0.7);

        assert_eq!(graph.get_premises().len(), 1);
        assert_eq!(graph.get_conclusions().len(), 1);
    }

    #[test]
    fn test_has_cycle_false() {
        let mut graph = ReasoningGraph::new();
        let id1 = graph.add_node("Node 1".to_string(), NodeType::Premise, 0.9);
        let id2 = graph.add_node("Node 2".to_string(), NodeType::Intermediate, 0.8);
        let id3 = graph.add_node("Node 3".to_string(), NodeType::Conclusion, 0.7);

        graph.add_edge(id1, id2, EdgeType::Supports, 0.9).unwrap();
        graph.add_edge(id2, id3, EdgeType::Supports, 0.9).unwrap();

        assert!(!graph.has_cycle());
    }

    #[test]
    fn test_has_cycle_true() {
        let mut graph = ReasoningGraph::new();
        let id1 = graph.add_node("Node 1".to_string(), NodeType::Premise, 0.9);
        let id2 = graph.add_node("Node 2".to_string(), NodeType::Intermediate, 0.8);

        graph.add_edge(id1, id2, EdgeType::Supports, 0.9).unwrap();
        graph.add_edge(id2, id1, EdgeType::Refines, 0.8).unwrap();

        assert!(graph.has_cycle());
    }

    #[test]
    fn test_path_score() {
        let mut graph = ReasoningGraph::new();
        let id1 = graph.add_node("Node 1".to_string(), NodeType::Premise, 0.9);
        let id2 = graph.add_node("Node 2".to_string(), NodeType::Intermediate, 0.8);

        graph.add_edge(id1, id2, EdgeType::Supports, 0.7).unwrap();

        let path = vec![id1, id2];
        let score = graph.get_path_score(&path);
        assert!((score - (0.9 + 0.8 + 0.7)).abs() < 0.001);
    }

    #[test]
    fn test_statistics() {
        let mut graph = ReasoningGraph::new();
        let id1 = graph.add_node("Premise".to_string(), NodeType::Premise, 0.9);
        let id2 = graph.add_node("Intermediate".to_string(), NodeType::Intermediate, 0.8);
        let id3 = graph.add_node("Conclusion".to_string(), NodeType::Conclusion, 0.7);

        graph.add_edge(id1, id2, EdgeType::Supports, 0.9).unwrap();
        graph.add_edge(id2, id3, EdgeType::DependsOn, 0.8).unwrap();

        let stats = graph.statistics();
        assert_eq!(stats.num_nodes, 3);
        assert_eq!(stats.num_edges, 2);
        assert_eq!(stats.node_types.get("premise"), Some(&1));
        assert_eq!(stats.edge_types.get("supports"), Some(&1));
    }
}
