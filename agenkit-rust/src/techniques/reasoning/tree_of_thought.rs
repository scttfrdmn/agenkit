// Tree-of-Thought Reasoning Technique
//
// Tree-of-Thought explores multiple reasoning paths simultaneously through
// tree search with branching, evaluation, pruning, and backtracking.
//
// Reference: "Tree of Thoughts: Deliberate Problem Solving with Large Language Models"
// Yao et al., 2023 - https://arxiv.org/abs/2305.10601

use crate::core::{Agent, AgentError, Message};
use crate::techniques::reasoning::reasoning_tree::{NodeState, ReasoningTree};
use async_trait::async_trait;
use regex::Regex;
use serde_json::json;
use std::collections::{BinaryHeap, VecDeque};
use std::sync::Arc;

/// Search strategy for tree exploration.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SearchStrategy {
    /// Breadth-first search (level by level)
    BFS,
    /// Depth-first search (explore deeply first)
    DFS,
    /// Best-first search (greedy, highest score first)
    BestFirst,
}

/// Function type for evaluating reasoning quality.
pub type EvaluatorFunc = Arc<dyn Fn(&str) -> f64 + Send + Sync>;

/// Configuration for Tree-of-Thought.
pub struct TreeOfThoughtConfig {
    /// Number of branches to generate at each step (default: 3)
    pub branching_factor: usize,

    /// Maximum tree depth to explore (default: 5)
    pub max_depth: usize,

    /// Evaluator function for scoring reasoning paths (default: length-based)
    pub evaluator: Option<EvaluatorFunc>,

    /// Search strategy to use (default: BestFirst)
    pub strategy: SearchStrategy,

    /// Score threshold below which nodes are pruned (default: 0.3)
    pub prune_threshold: f64,
}

impl Default for TreeOfThoughtConfig {
    fn default() -> Self {
        Self {
            branching_factor: 3,
            max_depth: 5,
            evaluator: None,
            strategy: SearchStrategy::BestFirst,
            prune_threshold: 0.3,
        }
    }
}

/// Default evaluator based on text length and structure.
///
/// Scores text based on:
/// - Length (longer is better, up to a point)
/// - Structure (numbered steps, bullet points get bonus)
/// - Normalized to 0.0-1.0 range
pub fn default_evaluator(text: &str) -> f64 {
    if text.is_empty() {
        return 0.0;
    }

    // Base score on length (normalized)
    let length_score = (text.len() as f64 / 500.0).min(1.0);

    // Bonus for structured content (numbered steps, bullet points)
    let numbered_regex = Regex::new(r"(?m)^\d+[.)]").unwrap();
    let bullet_regex = Regex::new(r"(?m)^[•\-\*]").unwrap();

    let numbered_count = numbered_regex.find_iter(text).count();
    let bullet_count = bullet_regex.find_iter(text).count();

    let structure_bonus = if numbered_count >= 2 {
        0.2
    } else if bullet_count >= 2 {
        0.15
    } else {
        0.0
    };

    // Final score (capped at 1.0)
    (length_score + structure_bonus).min(1.0)
}

/// Scored node for priority queue (used in best-first search).
#[derive(Debug, Clone)]
struct ScoredNode {
    node_id: usize,
    score: f64,
}

impl PartialEq for ScoredNode {
    fn eq(&self, other: &Self) -> bool {
        self.score == other.score
    }
}

impl Eq for ScoredNode {}

impl PartialOrd for ScoredNode {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        self.score.partial_cmp(&other.score)
    }
}

impl Ord for ScoredNode {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        self.partial_cmp(other).unwrap_or(std::cmp::Ordering::Equal)
    }
}

/// Tree-of-Thought agent that wraps a base agent.
///
/// This technique explores multiple reasoning paths by building a tree of
/// possibilities, evaluating each path, and selecting the best solution.
///
/// Particularly effective for:
/// - Complex planning and decision-making
/// - Multi-step reasoning with backtracking
/// - Exploring alternative approaches
/// - Creative problem-solving
pub struct TreeOfThoughtAgent {
    agent: Arc<dyn Agent>,
    branching_factor: usize,
    max_depth: usize,
    evaluator: EvaluatorFunc,
    strategy: SearchStrategy,
    prune_threshold: f64,
}

impl TreeOfThoughtAgent {
    /// Create a new Tree-of-Thought agent.
    pub fn new(agent: Arc<dyn Agent>, config: TreeOfThoughtConfig) -> Self {
        let evaluator = config
            .evaluator
            .unwrap_or_else(|| Arc::new(default_evaluator));

        Self {
            agent,
            branching_factor: config.branching_factor,
            max_depth: config.max_depth,
            evaluator,
            strategy: config.strategy,
            prune_threshold: config.prune_threshold,
        }
    }

    /// Generate N varied reasoning branches for a prompt.
    async fn generate_branches(&self, prompt: &str, n: usize) -> Result<Vec<String>, AgentError> {
        let mut branches = Vec::new();

        #[cfg(feature = "native")]
        {
            // Generate branches in parallel using tokio
            let mut handles = Vec::new();

            for i in 0..n {
                let agent = Arc::clone(&self.agent);
                let varied_prompt = format!("{}\n\nAlternative approach #{}:", prompt, i + 1);

                let handle = tokio::spawn(async move {
                    let msg = Message::with_text("user", varied_prompt);
                    let response = agent.process(msg).await?;
                    Ok::<String, AgentError>(response.content_as_str().unwrap_or("").to_string())
                });

                handles.push(handle);
            }

            // Collect results
            for handle in handles {
                match handle.await {
                    Ok(Ok(branch)) => branches.push(branch),
                    Ok(Err(e)) => return Err(e),
                    Err(e) => {
                        return Err(AgentError::Internal(format!(
                            "Branch generation failed: {}",
                            e
                        )))
                    }
                }
            }
        }

        #[cfg(feature = "wasm")]
        {
            // Generate branches sequentially in WASM
            for i in 0..n {
                let varied_prompt = format!("{}\n\nAlternative approach #{}:", prompt, i + 1);
                let msg = Message::with_text("user", varied_prompt);
                let response = self.agent.process(msg).await?;
                branches.push(response.content_as_str().unwrap_or("").to_string());
            }
        }

        Ok(branches)
    }

    /// Expand a tree node by generating and adding children.
    async fn expand_node(
        &self,
        tree: &mut ReasoningTree,
        node_id: usize,
    ) -> Result<Vec<usize>, AgentError> {
        let node = tree
            .get_node(node_id)
            .ok_or_else(|| AgentError::Internal(format!("Node {} not found", node_id)))?;

        // Don't expand pruned nodes
        if node.state == NodeState::Pruned {
            return Ok(Vec::new());
        }

        // Mark as active
        if let Some(node) = tree.get_node_mut(node_id) {
            node.state = NodeState::Active;
        }

        // Generate branches
        let prompt = tree.get_path_text(node_id, "\n");
        let branches = self
            .generate_branches(&prompt, self.branching_factor)
            .await?;

        let mut child_ids = Vec::new();

        for branch in branches {
            // Score the branch
            let score = (self.evaluator)(&branch);

            // Prune if below threshold
            if score < self.prune_threshold {
                continue;
            }

            // Add child to tree
            let child_id = tree
                .add_child(node_id, branch, score)
                .map_err(|e| AgentError::Internal(e))?;
            child_ids.push(child_id);

            if let Some(child) = tree.get_node_mut(child_id) {
                child.state = NodeState::Evaluated;
            }
        }

        // Mark node as evaluated
        if let Some(node) = tree.get_node_mut(node_id) {
            node.state = NodeState::Evaluated;
        }

        Ok(child_ids)
    }

    /// Perform breadth-first search on the tree.
    async fn search_bfs(&self, tree: &mut ReasoningTree, root_id: usize) -> Result<(), AgentError> {
        let mut queue = VecDeque::new();
        queue.push_back(root_id);

        while let Some(node_id) = queue.pop_front() {
            let node = tree
                .get_node(node_id)
                .ok_or_else(|| AgentError::Internal(format!("Node {} not found", node_id)))?;

            // Stop at max depth
            if node.depth >= self.max_depth {
                if let Some(node) = tree.get_node_mut(node_id) {
                    node.state = NodeState::Terminal;
                }
                continue;
            }

            // Expand node
            let children = self.expand_node(tree, node_id).await?;

            // Add children to queue
            for child_id in children {
                queue.push_back(child_id);
            }
        }

        Ok(())
    }

    /// Perform depth-first search on the tree.
    async fn search_dfs(&self, tree: &mut ReasoningTree, root_id: usize) -> Result<(), AgentError> {
        let mut stack = vec![root_id];

        while let Some(node_id) = stack.pop() {
            let node = tree
                .get_node(node_id)
                .ok_or_else(|| AgentError::Internal(format!("Node {} not found", node_id)))?;

            // Stop at max depth
            if node.depth >= self.max_depth {
                if let Some(node) = tree.get_node_mut(node_id) {
                    node.state = NodeState::Terminal;
                }
                continue;
            }

            // Expand node
            let children = self.expand_node(tree, node_id).await?;

            // Add children to stack (reverse order for left-to-right DFS)
            for child_id in children.into_iter().rev() {
                stack.push(child_id);
            }
        }

        Ok(())
    }

    /// Perform best-first search on the tree.
    async fn search_best_first(
        &self,
        tree: &mut ReasoningTree,
        root_id: usize,
    ) -> Result<(), AgentError> {
        let mut pq = BinaryHeap::new();
        pq.push(ScoredNode {
            node_id: root_id,
            score: 0.0,
        });

        while let Some(scored) = pq.pop() {
            let node = tree.get_node(scored.node_id).ok_or_else(|| {
                AgentError::Internal(format!("Node {} not found", scored.node_id))
            })?;

            // Stop at max depth
            if node.depth >= self.max_depth {
                if let Some(node) = tree.get_node_mut(scored.node_id) {
                    node.state = NodeState::Terminal;
                }
                continue;
            }

            // Expand node
            let children = self.expand_node(tree, scored.node_id).await?;

            // Add children to priority queue
            for child_id in children {
                if let Some(child) = tree.get_node(child_id) {
                    pq.push(ScoredNode {
                        node_id: child_id,
                        score: child.score,
                    });
                }
            }
        }

        Ok(())
    }

    /// Convert SearchStrategy enum to string.
    fn strategy_to_string(&self) -> &'static str {
        match self.strategy {
            SearchStrategy::BFS => "bfs",
            SearchStrategy::DFS => "dfs",
            SearchStrategy::BestFirst => "best-first",
        }
    }
}

#[async_trait]
impl Agent for TreeOfThoughtAgent {
    fn name(&self) -> &str {
        "tree_of_thought"
    }

    fn capabilities(&self) -> Vec<String> {
        vec![
            "reasoning".to_string(),
            "tree_search".to_string(),
            "multi_path_exploration".to_string(),
            "backtracking".to_string(),
            "tree_of_thought".to_string(),
            "planning".to_string(),
        ]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let query = message.content_as_str().unwrap_or("").to_string();

        // Create reasoning tree
        let mut tree = ReasoningTree::new();
        let root_id = tree.create_root(query.clone());

        // Perform search based on strategy
        match self.strategy {
            SearchStrategy::BFS => self.search_bfs(&mut tree, root_id).await?,
            SearchStrategy::DFS => self.search_dfs(&mut tree, root_id).await?,
            SearchStrategy::BestFirst => self.search_best_first(&mut tree, root_id).await?,
        }

        // Get best leaf node
        let best_leaf = tree
            .get_best_leaf()
            .ok_or_else(|| AgentError::Internal("No valid reasoning paths found".to_string()))?;

        // Build response with best path
        let path = tree.get_path(best_leaf.id);
        let path_steps: Vec<String> = path.iter().map(|node| node.content.clone()).collect();

        let best_path_text = tree.get_path_text(best_leaf.id, "\n");
        let stats = tree.get_statistics();

        // Create response message
        let mut response = Message::with_text("assistant", best_path_text);
        response
            .metadata
            .insert("technique".to_string(), json!("tree_of_thought"));
        response.metadata.insert(
            "search_strategy".to_string(),
            json!(self.strategy_to_string()),
        );
        response
            .metadata
            .insert("reasoning_path".to_string(), json!(path_steps));
        response
            .metadata
            .insert("num_steps".to_string(), json!(path_steps.len()));
        response
            .metadata
            .insert("best_score".to_string(), json!(best_leaf.score));
        response
            .metadata
            .insert("reasoning_tree_stats".to_string(), json!(stats));

        Ok(response)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    struct MockAgent {
        response: String,
        call_count: Mutex<usize>,
    }

    impl MockAgent {
        fn new(response: impl Into<String>) -> Arc<Self> {
            Arc::new(Self {
                response: response.into(),
                call_count: Mutex::new(0),
            })
        }
    }

    #[async_trait]
    impl Agent for MockAgent {
        fn name(&self) -> &str {
            "mock"
        }

        fn capabilities(&self) -> Vec<String> {
            vec![]
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            *self.call_count.lock().unwrap() += 1;
            Ok(Message::with_text("assistant", self.response.clone()))
        }
    }

    #[test]
    fn test_default_config() {
        let config = TreeOfThoughtConfig::default();
        assert!(config.branching_factor > 0);
        assert!(config.max_depth > 0);
        assert!(config.prune_threshold >= 0.0 && config.prune_threshold <= 1.0);
    }

    #[test]
    fn test_agent_name_and_capabilities() {
        let agent = TreeOfThoughtAgent::new(MockAgent::new("ok"), TreeOfThoughtConfig::default());
        assert_eq!(agent.name(), "tree_of_thought");
        let caps = agent.capabilities();
        assert!(caps.contains(&"tree_of_thought".to_string()));
        assert!(caps.contains(&"reasoning".to_string()));
    }

    #[test]
    fn test_default_evaluator_structured_text() {
        // Structured text with numbered items should score higher
        let structured = "1. Step one\n2. Step two\n3. Step three\nConclusion";
        let plain = "just some text";
        assert!(default_evaluator(structured) > default_evaluator(plain));
    }

    #[test]
    fn test_default_evaluator_score_range() {
        let score = default_evaluator("some text here");
        assert!(score >= 0.0 && score <= 1.0);
    }

    #[test]
    fn test_default_evaluator_empty() {
        let score = default_evaluator("");
        assert!(score >= 0.0);
    }

    #[test]
    fn test_search_strategy_variants() {
        let _bfs = SearchStrategy::BFS;
        let _dfs = SearchStrategy::DFS;
        let _best = SearchStrategy::BestFirst;
    }

    #[test]
    fn test_custom_evaluator() {
        let config = TreeOfThoughtConfig {
            evaluator: Some(Arc::new(|_text: &str| 0.99)),
            ..Default::default()
        };
        let evaluator = config.evaluator.unwrap();
        assert_eq!(evaluator("anything"), 0.99);
    }

    #[tokio::test]
    async fn test_process_adds_metadata() {
        let agent = TreeOfThoughtAgent::new(
            MockAgent::new("1. Think about this\n2. Consider that\n3. Conclude"),
            TreeOfThoughtConfig {
                branching_factor: 2,
                max_depth: 2,
                ..Default::default()
            },
        );
        let msg = Message::with_text("user", "What is the best approach?");
        let result = agent.process(msg).await.unwrap();
        assert_eq!(result.metadata["technique"], "tree_of_thought");
        assert!(result.metadata.contains_key("search_strategy"));
        assert!(result.metadata.contains_key("best_score"));
    }

    #[tokio::test]
    async fn test_process_bfs_strategy() {
        let config = TreeOfThoughtConfig {
            strategy: SearchStrategy::BFS,
            branching_factor: 2,
            max_depth: 2,
            ..Default::default()
        };
        let agent = TreeOfThoughtAgent::new(MockAgent::new("response text"), config);
        let msg = Message::with_text("user", "test");
        let result = agent.process(msg).await.unwrap();
        assert_eq!(result.metadata["search_strategy"], "bfs");
    }

    #[tokio::test]
    async fn test_process_dfs_strategy() {
        let config = TreeOfThoughtConfig {
            strategy: SearchStrategy::DFS,
            branching_factor: 2,
            max_depth: 2,
            ..Default::default()
        };
        let agent = TreeOfThoughtAgent::new(MockAgent::new("response text"), config);
        let msg = Message::with_text("user", "test");
        let result = agent.process(msg).await.unwrap();
        assert_eq!(result.metadata["search_strategy"], "dfs");
    }
}
