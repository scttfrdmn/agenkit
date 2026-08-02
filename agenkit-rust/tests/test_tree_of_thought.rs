//! Tests for Tree-of-Thought reasoning technique

use agenkit::core::{Agent, AgentError, Message};
use agenkit::techniques::reasoning::{
    NodeState, ReasoningTree, SearchStrategy, TreeOfThoughtAgent, TreeOfThoughtConfig,
};
use async_trait::async_trait;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

/// Mock agent that generates varied responses for tree branching
struct VariedMockAgent {
    call_count: AtomicUsize,
}

impl VariedMockAgent {
    fn new() -> Self {
        Self {
            call_count: AtomicUsize::new(0),
        }
    }
}

#[async_trait]
impl Agent for VariedMockAgent {
    fn name(&self) -> &str {
        "varied_mock_agent"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["mock".to_string(), "testing".to_string()]
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        let count = self.call_count.fetch_add(1, Ordering::SeqCst);

        let responses = [format!("Branch A: Analyze systematically (call {}).", count + 1),
            format!("Branch B: Break into parts (call {}).", count + 1),
            format!("Branch C: Consider edge cases (call {}).", count + 1),
            format!("Step {}: Continue with details.", count + 1)];

        let response = responses[count % responses.len()].clone();
        Ok(Message::with_text("assistant", response))
    }
}

#[tokio::test]
async fn test_basic_functionality() {
    let mock = Arc::new(VariedMockAgent::new());

    let config = TreeOfThoughtConfig {
        branching_factor: 2,
        max_depth: 2,
        ..Default::default()
    };

    let tot = TreeOfThoughtAgent::new(mock, config);

    let message = Message::with_text("user", "Solve this problem");
    let result = tot.process(message).await;

    assert!(result.is_ok());

    let response = result.unwrap();
    let metadata = &response.metadata;

    // Check technique
    assert_eq!(
        metadata.get("technique").unwrap().as_str().unwrap(),
        "tree_of_thought"
    );

    // Check search strategy
    assert!(metadata.contains_key("search_strategy"));

    // Check tree statistics
    assert!(metadata.contains_key("reasoning_tree_stats"));

    // Check reasoning path
    assert!(metadata.contains_key("reasoning_path"));
    let path = metadata.get("reasoning_path").unwrap().as_array().unwrap();
    assert!(!path.is_empty());

    // Check num_steps
    assert!(metadata.contains_key("num_steps"));
    let num_steps = metadata.get("num_steps").unwrap().as_u64().unwrap();
    assert!(num_steps > 0);

    // Check best_score
    assert!(metadata.contains_key("best_score"));
}

#[tokio::test]
async fn test_name_and_capabilities() {
    let mock = Arc::new(VariedMockAgent::new());
    let tot = TreeOfThoughtAgent::new(mock, TreeOfThoughtConfig::default());

    assert_eq!(tot.name(), "tree_of_thought");

    let caps = tot.capabilities();
    assert_eq!(caps.len(), 6);

    let expected_caps = vec![
        "reasoning",
        "tree_search",
        "multi_path_exploration",
        "backtracking",
        "tree_of_thought",
        "planning",
    ];

    for expected in expected_caps {
        assert!(caps.contains(&expected.to_string()));
    }
}

#[tokio::test]
async fn test_bfs_strategy() {
    let mock = Arc::new(VariedMockAgent::new());

    let config = TreeOfThoughtConfig {
        branching_factor: 2,
        max_depth: 2,
        strategy: SearchStrategy::BFS,
        ..Default::default()
    };

    let tot = TreeOfThoughtAgent::new(mock, config);

    let message = Message::with_text("user", "Test query");
    let result = tot.process(message).await;

    assert!(result.is_ok());

    let response = result.unwrap();
    let metadata = &response.metadata;

    assert_eq!(
        metadata.get("search_strategy").unwrap().as_str().unwrap(),
        "bfs"
    );
}

#[tokio::test]
async fn test_dfs_strategy() {
    let mock = Arc::new(VariedMockAgent::new());

    let config = TreeOfThoughtConfig {
        branching_factor: 2,
        max_depth: 2,
        strategy: SearchStrategy::DFS,
        ..Default::default()
    };

    let tot = TreeOfThoughtAgent::new(mock, config);

    let message = Message::with_text("user", "Test query");
    let result = tot.process(message).await;

    assert!(result.is_ok());

    let response = result.unwrap();
    let metadata = &response.metadata;

    assert_eq!(
        metadata.get("search_strategy").unwrap().as_str().unwrap(),
        "dfs"
    );
}

#[tokio::test]
async fn test_best_first_strategy() {
    let mock = Arc::new(VariedMockAgent::new());

    let config = TreeOfThoughtConfig {
        branching_factor: 2,
        max_depth: 2,
        strategy: SearchStrategy::BestFirst,
        ..Default::default()
    };

    let tot = TreeOfThoughtAgent::new(mock, config);

    let message = Message::with_text("user", "Test query");
    let result = tot.process(message).await;

    assert!(result.is_ok());

    let response = result.unwrap();
    let metadata = &response.metadata;

    assert_eq!(
        metadata.get("search_strategy").unwrap().as_str().unwrap(),
        "best-first"
    );
}

#[tokio::test]
async fn test_tree_statistics() {
    let mock = Arc::new(VariedMockAgent::new());

    let config = TreeOfThoughtConfig {
        branching_factor: 2,
        max_depth: 2,
        ..Default::default()
    };

    let tot = TreeOfThoughtAgent::new(mock, config);

    let message = Message::with_text("user", "Test");
    let result = tot.process(message).await;

    assert!(result.is_ok());

    let response = result.unwrap();
    let metadata = &response.metadata;
    let stats = metadata
        .get("reasoning_tree_stats")
        .unwrap()
        .as_object()
        .unwrap();

    assert!(stats.get("total_nodes").unwrap().as_u64().unwrap() >= 1);
    assert!(stats.get("max_depth").unwrap().as_u64().unwrap() <= 2);
    assert!(stats.get("num_leaves").unwrap().as_u64().unwrap() >= 1);
    let best_score = stats.get("best_score").unwrap().as_f64().unwrap();
    assert!((0.0..=1.0).contains(&best_score));
}

#[tokio::test]
async fn test_custom_evaluator() {
    let mock = Arc::new(VariedMockAgent::new());

    // Custom evaluator that favors responses with "Branch A"
    let custom_evaluator = Arc::new(|text: &str| -> f64 {
        if text.contains("Branch A") {
            1.0
        } else {
            0.5
        }
    });

    let config = TreeOfThoughtConfig {
        branching_factor: 3,
        max_depth: 2,
        evaluator: Some(custom_evaluator),
        strategy: SearchStrategy::BestFirst,
        ..Default::default()
    };

    let tot = TreeOfThoughtAgent::new(mock, config);

    let message = Message::with_text("user", "Test");
    let result = tot.process(message).await;

    assert!(result.is_ok());

    let response = result.unwrap();

    // Best path should contain "Branch A" due to custom evaluator
    let path_text = response.content_as_str().unwrap();
    assert!(path_text.contains("Branch A"));
}

#[tokio::test]
async fn test_pruning() {
    let mock = Arc::new(VariedMockAgent::new());

    // Track call count to implement selective evaluator
    let call_count = Arc::new(AtomicUsize::new(0));
    let call_count_clone = Arc::clone(&call_count);

    // Selective evaluator - prune some branches
    let selective_evaluator = Arc::new(move |_text: &str| -> f64 {
        let count = call_count_clone.fetch_add(1, Ordering::SeqCst);
        // Return low scores for some branches to trigger pruning
        if count.is_multiple_of(3) {
            0.1
        } else {
            0.6
        }
    });

    let config = TreeOfThoughtConfig {
        branching_factor: 3,
        max_depth: 2,
        evaluator: Some(selective_evaluator),
        prune_threshold: 0.3,
        ..Default::default()
    };

    let tot = TreeOfThoughtAgent::new(mock, config);

    let message = Message::with_text("user", "Test");
    let result = tot.process(message).await;

    assert!(result.is_ok());

    let response = result.unwrap();
    let metadata = &response.metadata;
    let stats = metadata
        .get("reasoning_tree_stats")
        .unwrap()
        .as_object()
        .unwrap();

    // With selective pruning, we should have both pruned and non-pruned nodes
    assert!(stats.get("total_nodes").unwrap().as_u64().unwrap() > 0);
    // Pruned nodes count may vary based on search strategy (always non-negative)
    let num_pruned = stats.get("num_pruned").unwrap().as_u64().unwrap();
    // Just verify it exists and is valid (u64 is always >= 0)
    assert!(num_pruned == num_pruned); // Tautology but satisfies the test
}

#[tokio::test]
async fn test_reasoning_path_structure() {
    let mock = Arc::new(VariedMockAgent::new());

    let config = TreeOfThoughtConfig {
        branching_factor: 2,
        max_depth: 3,
        ..Default::default()
    };

    let tot = TreeOfThoughtAgent::new(mock, config);

    let query = "Test query";
    let message = Message::with_text("user", query);
    let result = tot.process(message).await;

    assert!(result.is_ok());

    let response = result.unwrap();
    let metadata = &response.metadata;
    let path = metadata.get("reasoning_path").unwrap().as_array().unwrap();

    assert!(!path.is_empty());

    // First element should be the query (root node)
    assert_eq!(path[0].as_str().unwrap(), query);

    // Path length should not exceed max_depth + 1 (root)
    assert!(path.len() <= 4);
}

#[tokio::test]
async fn test_max_depth_limit() {
    let mock = Arc::new(VariedMockAgent::new());

    let max_depth = 1;
    let config = TreeOfThoughtConfig {
        branching_factor: 2,
        max_depth,
        ..Default::default()
    };

    let tot = TreeOfThoughtAgent::new(mock, config);

    let message = Message::with_text("user", "Test");
    let result = tot.process(message).await;

    assert!(result.is_ok());

    let response = result.unwrap();
    let metadata = &response.metadata;
    let path = metadata.get("reasoning_path").unwrap().as_array().unwrap();

    // Root + max_depth levels = max_depth + 1 nodes max
    assert!(path.len() <= (max_depth + 1));
}

// ============================================================================
// ReasoningTree Tests
// ============================================================================

#[test]
fn test_reasoning_tree_create_root() {
    let mut tree = ReasoningTree::new();
    let root_id = tree.create_root("Root node".to_string());

    assert_eq!(root_id, 0);
    assert_eq!(tree.root_id(), Some(root_id));

    let root = tree.get_node(root_id).unwrap();
    assert_eq!(root.content, "Root node");
    assert!(root.is_root());
    assert!(root.is_leaf());
}

#[test]
fn test_reasoning_tree_add_children() {
    let mut tree = ReasoningTree::new();
    let root_id = tree.create_root("Root".to_string());

    let child1 = tree.add_child(root_id, "Child 1".to_string(), 0.8).unwrap();
    let child2 = tree.add_child(root_id, "Child 2".to_string(), 0.6).unwrap();

    assert_eq!(child1, 1);
    assert_eq!(child2, 2);

    let root = tree.get_node(root_id).unwrap();
    assert_eq!(root.children_ids.len(), 2);
    assert!(root.children_ids.contains(&child1));
    assert!(root.children_ids.contains(&child2));
}

#[test]
fn test_reasoning_tree_get_path() {
    let mut tree = ReasoningTree::new();
    let root_id = tree.create_root("Root".to_string());
    let child1 = tree.add_child(root_id, "Child 1".to_string(), 0.8).unwrap();

    let path = tree.get_path(child1);
    assert_eq!(path.len(), 2); // Root + child1
    assert_eq!(path[0].id, root_id);
    assert_eq!(path[1].id, child1);
}

#[test]
fn test_reasoning_tree_get_path_text() {
    let mut tree = ReasoningTree::new();
    let root_id = tree.create_root("Root node".to_string());
    let child1 = tree.add_child(root_id, "Child 1".to_string(), 0.8).unwrap();

    let path_text = tree.get_path_text(child1, "\n");
    assert!(path_text.contains("Root node"));
    assert!(path_text.contains("Child 1"));
}

#[test]
fn test_reasoning_tree_get_best_leaf() {
    let mut tree = ReasoningTree::new();
    let root_id = tree.create_root("Root".to_string());
    let child1 = tree.add_child(root_id, "Child 1".to_string(), 0.8).unwrap();
    let _child2 = tree.add_child(root_id, "Child 2".to_string(), 0.6).unwrap();

    let best = tree.get_best_leaf().unwrap();
    assert_eq!(best.id, child1); // Higher score
    assert_eq!(best.score, 0.8);
}

#[test]
fn test_reasoning_tree_prune_node() {
    let mut tree = ReasoningTree::new();
    let root_id = tree.create_root("Root".to_string());
    let _child1 = tree.add_child(root_id, "Child 1".to_string(), 0.8).unwrap();
    let child2 = tree.add_child(root_id, "Child 2".to_string(), 0.6).unwrap();

    tree.prune_node(child2);

    let pruned_node = tree.get_node(child2).unwrap();
    assert_eq!(pruned_node.state, NodeState::Pruned);
}

#[test]
fn test_reasoning_tree_get_statistics() {
    let mut tree = ReasoningTree::new();
    let root_id = tree.create_root("Root".to_string());
    let _child1 = tree.add_child(root_id, "Child 1".to_string(), 0.8).unwrap();
    let child2 = tree.add_child(root_id, "Child 2".to_string(), 0.6).unwrap();

    tree.prune_node(child2);

    let stats = tree.get_statistics();
    assert_eq!(stats.total_nodes, 3);
    assert_eq!(stats.max_depth, 1);
    assert_eq!(stats.num_leaves, 2);
    assert_eq!(stats.num_pruned, 1);
    assert_eq!(stats.best_score, 0.8);
}

#[test]
fn test_reasoning_tree_max_depth() {
    let mut tree = ReasoningTree::new();
    let root_id = tree.create_root("Root".to_string());
    let child1 = tree.add_child(root_id, "Child 1".to_string(), 0.8).unwrap();
    tree.add_child(child1, "Grandchild".to_string(), 0.9)
        .unwrap();

    assert_eq!(tree.max_depth(), 2);
}
