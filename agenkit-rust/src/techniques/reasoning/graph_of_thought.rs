// Graph-of-Thought Reasoning Technique
//
// Represents reasoning as a directed graph where nodes are thoughts/conclusions
// and edges represent logical connections. More flexible than tree-based
// approaches, allows for complex multi-hop reasoning and thought combination.
//
// This technique is particularly effective for:
// - Multi-hop reasoning problems
// - Problems with multiple interconnected concepts
// - Situations requiring synthesis of multiple reasoning chains
//
// Reference:
// - Paper: https://arxiv.org/abs/2308.09687
// - "Graph of Thoughts: Solving Elaborate Problems with Large Language Models"

use crate::core::{Agent, AgentError, Message};
use crate::techniques::reasoning::reasoning_graph::{EdgeType, NodeType, ReasoningGraph};
use async_trait::async_trait;
use serde_json::json;
use std::sync::Arc;

/// Aggregation strategy for combining reasoning paths.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AggregatorType {
    /// Evaluate complete paths, choose best path
    PathBased,
    /// Aggregate individual nodes across paths
    NodeBased,
}

/// Configuration options for GraphOfThought agent.
pub struct GraphOfThoughtConfig {
    /// Maximum number of nodes in reasoning graph
    pub max_nodes: usize,
    /// Maximum number of edges in reasoning graph
    pub max_edges: usize,
    /// Aggregation strategy for combining paths
    pub aggregator: AggregatorType,
    /// Whether to allow cycles in reasoning graph
    pub allow_cycles: bool,
}

impl Default for GraphOfThoughtConfig {
    fn default() -> Self {
        Self {
            max_nodes: 20,
            max_edges: 40,
            aggregator: AggregatorType::PathBased,
            allow_cycles: false,
        }
    }
}

/// Graph-of-Thought reasoning technique.
///
/// Builds a directed graph of reasoning steps, explores connections,
/// and aggregates multiple reasoning paths to reach conclusions.
///
/// This technique is particularly effective for:
/// - Multi-hop reasoning with complex dependencies
/// - Problems requiring synthesis of multiple chains of thought
/// - Situations where thoughts may support, contradict, or refine each other
/// - Complex knowledge integration tasks
///
/// # Example
///
/// ```no_run
/// use agenkit::techniques::reasoning::{GraphOfThoughtAgent, GraphOfThoughtConfig, AggregatorType};
/// use agenkit::core::{Agent, Message};
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), agenkit::core::AgentError> {
/// # struct MyAgent;
/// # #[async_trait::async_trait]
/// # impl Agent for MyAgent {
/// #     fn name(&self) -> &str { "base" }
/// #     async fn process(&self, msg: Message) -> Result<Message, agenkit::core::AgentError> {
/// #         Ok(Message::with_text("assistant", "ok"))
/// #     }
/// # }
/// let base_agent = Arc::new(MyAgent);
/// let config = GraphOfThoughtConfig {
///     max_nodes: 20,
///     max_edges: 40,
///     aggregator: AggregatorType::PathBased,
///     ..Default::default()
/// };
///
/// let got = GraphOfThoughtAgent::new(base_agent, config);
/// let message = Message::with_text("user", "Plan a trip.");
/// let response = got.process(message).await?;
/// // Access reasoning graph and paths from metadata
/// # Ok(())
/// # }
/// ```
pub struct GraphOfThoughtAgent {
    agent: Arc<dyn Agent>,
    max_nodes: usize,
    max_edges: usize,
    aggregator: AggregatorType,
    allow_cycles: bool,
}

impl GraphOfThoughtAgent {
    /// Create a new GraphOfThought agent.
    pub fn new(agent: Arc<dyn Agent>, config: GraphOfThoughtConfig) -> Self {
        Self {
            agent,
            max_nodes: config.max_nodes,
            max_edges: config.max_edges,
            aggregator: config.aggregator,
            allow_cycles: config.allow_cycles,
        }
    }

    /// Call LLM with prompt.
    async fn llm_call(&self, prompt: &str) -> Result<String, AgentError> {
        let message = Message::new("user", serde_json::Value::String(prompt.to_string()));
        let response = self.agent.process(message).await?;

        // Extract string from content
        match response.content {
            serde_json::Value::String(s) => Ok(s),
            other => Ok(other.to_string()),
        }
    }

    /// Generate initial premises/facts for the problem.
    async fn generate_premises(&self, problem: &str) -> Result<Vec<String>, AgentError> {
        let prompt = format!(
            "Identify the key facts and premises for this problem.\n\
             List 2-4 foundational facts or assumptions, one per line.\n\n\
             Problem: {}\n\n\
             Premises:",
            problem
        );

        let response = self.llm_call(&prompt).await?;

        // Parse premises
        let premises: Vec<String> = response
            .trim()
            .lines()
            .filter_map(|line| {
                let trimmed = line.trim();
                if !trimmed.is_empty() && !trimmed.starts_with('#') {
                    // Remove numbering and bullets
                    let cleaned = trimmed
                        .trim_start_matches(|c: char| {
                            c.is_numeric() || c == '.' || c == '-' || c == '*' || c == '•'
                        })
                        .trim();
                    if !cleaned.is_empty() {
                        Some(cleaned.to_string())
                    } else {
                        None
                    }
                } else {
                    None
                }
            })
            .take(4) // Limit to 4 premises
            .collect();

        Ok(premises)
    }

    /// Generate new intermediate thoughts based on existing ones.
    async fn generate_thoughts(
        &self,
        problem: &str,
        existing_thoughts: &[String],
        max_new: usize,
    ) -> Result<Vec<String>, AgentError> {
        let prompt = if !existing_thoughts.is_empty() {
            let context = existing_thoughts
                .iter()
                .map(|t| format!("- {}", t))
                .collect::<Vec<_>>()
                .join("\n");

            format!(
                "Given this problem and existing thoughts, generate {} new insights or conclusions.\n\n\
                 Problem: {}\n\n\
                 Existing thoughts:\n{}\n\n\
                 New thoughts (one per line):",
                max_new, problem, context
            )
        } else {
            format!(
                "Generate {} initial thoughts or insights about this problem.\n\n\
                 Problem: {}\n\n\
                 Thoughts (one per line):",
                max_new, problem
            )
        };

        let response = self.llm_call(&prompt).await?;

        // Parse new thoughts
        let thoughts: Vec<String> = response
            .trim()
            .lines()
            .filter_map(|line| {
                let trimmed = line.trim();
                if !trimmed.is_empty() && !trimmed.starts_with('#') {
                    let cleaned = trimmed
                        .trim_start_matches(|c: char| {
                            c.is_numeric() || c == '.' || c == '-' || c == '*' || c == '•'
                        })
                        .trim();
                    if !cleaned.is_empty() {
                        Some(cleaned.to_string())
                    } else {
                        None
                    }
                } else {
                    None
                }
            })
            .take(max_new)
            .collect();

        Ok(thoughts)
    }

    /// Identify logical connection between two thoughts.
    async fn identify_connection(
        &self,
        thought1: &str,
        thought2: &str,
    ) -> Result<Option<EdgeType>, AgentError> {
        let prompt = format!(
            "Analyze the logical relationship between these two statements.\n\n\
             Statement 1: {}\n\n\
             Statement 2: {}\n\n\
             Does statement 2:\n\
             - SUPPORT statement 1 (provides evidence or reasoning for it)\n\
             - DEPEND on statement 1 (requires it to be true)\n\
             - CONTRADICT statement 1 (conflicts with it)\n\
             - REFINE statement 1 (improves or clarifies it)\n\
             - NO_RELATION (no clear logical connection)\n\n\
             Answer with one word: SUPPORT, DEPEND, CONTRADICT, REFINE, or NO_RELATION",
            thought1, thought2
        );

        let response = self.llm_call(&prompt).await?;
        let response_upper = response.trim().to_uppercase();

        if response_upper.contains("SUPPORT") {
            Ok(Some(EdgeType::Supports))
        } else if response_upper.contains("DEPEND") {
            Ok(Some(EdgeType::DependsOn))
        } else if response_upper.contains("CONTRADICT") {
            Ok(Some(EdgeType::Contradicts))
        } else if response_upper.contains("REFINE") {
            Ok(Some(EdgeType::Refines))
        } else {
            Ok(None)
        }
    }

    /// Build reasoning graph for the problem.
    async fn build_graph(&self, problem: &str) -> Result<ReasoningGraph, AgentError> {
        let mut graph = ReasoningGraph::new();

        // Step 1: Generate premises
        let premises = self.generate_premises(problem).await?;
        let mut premise_ids = Vec::new();
        for premise in &premises {
            let node_id = graph.add_node(premise.clone(), NodeType::Premise, 0.9);
            premise_ids.push(node_id);
        }

        // Step 2: Generate intermediate thoughts
        let mut all_thoughts = premises.clone();
        let mut node_ids = premise_ids.clone();

        while graph.get_nodes().len() < self.max_nodes {
            let max_new = (self.max_nodes - graph.get_nodes().len()).min(3);
            if max_new == 0 {
                break;
            }

            let new_thoughts = self
                .generate_thoughts(problem, &all_thoughts, max_new)
                .await?;

            if new_thoughts.is_empty() {
                break;
            }

            // Add new thoughts as intermediate nodes
            for thought in new_thoughts {
                if graph.get_nodes().len() >= self.max_nodes {
                    break;
                }

                let node_id = graph.add_node(thought.clone(), NodeType::Intermediate, 0.7);
                all_thoughts.push(thought);
                node_ids.push(node_id);
            }
        }

        // Step 3: Identify connections between thoughts
        let mut edge_count = 0;
        for i in 0..node_ids.len() {
            if edge_count >= self.max_edges {
                break;
            }

            for j in (i + 1)..node_ids.len() {
                if edge_count >= self.max_edges {
                    break;
                }

                let node1_id = node_ids[i];
                let node2_id = node_ids[j];

                let thought1 = &graph.get_node(node1_id).unwrap().content;
                let thought2 = &graph.get_node(node2_id).unwrap().content;

                // Check connection from node1 to node2
                if let Some(edge_type) = self.identify_connection(thought1, thought2).await? {
                    graph
                        .add_edge(node1_id, node2_id, edge_type, 0.8)
                        .map_err(AgentError::ProcessingError)?;
                    edge_count += 1;
                }
            }
        }

        // Step 4: Generate final conclusion
        if graph.get_nodes().len() < self.max_nodes {
            let thoughts_list = all_thoughts
                .iter()
                .map(|t| format!("- {}", t))
                .collect::<Vec<_>>()
                .join("\n");

            let conclusion_prompt = format!(
                "Based on all these thoughts, what is the final conclusion?\n\n\
                 Problem: {}\n\n\
                 Thoughts:\n{}\n\n\
                 Final conclusion:",
                problem, thoughts_list
            );

            let conclusion = self.llm_call(&conclusion_prompt).await?;
            let conclusion_id =
                graph.add_node(conclusion.trim().to_string(), NodeType::Conclusion, 0.8);

            // Connect conclusion to recent thoughts
            let recent_ids: Vec<usize> = node_ids.iter().rev().take(3).copied().collect();
            for recent_id in recent_ids {
                if edge_count < self.max_edges {
                    graph
                        .add_edge(recent_id, conclusion_id, EdgeType::Supports, 0.9)
                        .map_err(AgentError::ProcessingError)?;
                    edge_count += 1;
                }
            }
        }

        Ok(graph)
    }

    /// Find reasoning paths from premises to conclusions.
    fn find_reasoning_paths(&self, graph: &ReasoningGraph) -> Vec<Vec<usize>> {
        let premises: Vec<usize> = graph.get_premises().iter().map(|n| n.id).collect();
        let conclusions: Vec<usize> = graph.get_conclusions().iter().map(|n| n.id).collect();

        let mut all_paths = Vec::new();
        for premise_id in premises {
            for conclusion_id in &conclusions {
                let paths = graph.find_paths(premise_id, *conclusion_id, 6);
                all_paths.extend(paths);
            }
        }

        all_paths
    }

    /// Aggregate multiple reasoning paths into final answer.
    fn aggregate_paths(&self, graph: &ReasoningGraph, paths: &[Vec<usize>]) -> String {
        if paths.is_empty() {
            // No paths found - use conclusion nodes directly
            let conclusions = graph.get_conclusions();
            if !conclusions.is_empty() {
                return conclusions[0].content.clone();
            }
            // Fallback to any node
            let nodes = graph.get_nodes();
            if !nodes.is_empty() {
                return nodes[nodes.len() - 1].content.clone();
            }
            return "Unable to reach conclusion".to_string();
        }

        match self.aggregator {
            AggregatorType::PathBased => {
                // Find highest scoring path
                let best_path = paths
                    .iter()
                    .max_by(|a, b| {
                        let score_a = graph.get_path_score(a);
                        let score_b = graph.get_path_score(b);
                        score_a.partial_cmp(&score_b).unwrap()
                    })
                    .unwrap();

                // Get conclusion from best path
                let conclusion_node = graph.get_node(best_path[best_path.len() - 1]).unwrap();
                conclusion_node.content.clone()
            }
            AggregatorType::NodeBased => {
                // Count node appearances across paths
                let mut node_counts = std::collections::HashMap::new();
                for path in paths {
                    for &node_id in path {
                        *node_counts.entry(node_id).or_insert(0) += 1;
                    }
                }

                // Weight by confidence
                let mut best_node_id = 0;
                let mut best_score = -1.0;
                for (node_id, count) in node_counts {
                    let node = graph.get_node(node_id).unwrap();
                    let score = (count as f64) * node.confidence;
                    if score > best_score {
                        best_score = score;
                        best_node_id = node_id;
                    }
                }

                graph.get_node(best_node_id).unwrap().content.clone()
            }
        }
    }
}

#[async_trait]
impl Agent for GraphOfThoughtAgent {
    fn name(&self) -> &str {
        "graph_of_thought"
    }

    fn capabilities(&self) -> Vec<String> {
        vec![
            "reasoning".to_string(),
            "graph_reasoning".to_string(),
            "multi_hop".to_string(),
            "path_aggregation".to_string(),
            "graph_of_thought".to_string(),
        ]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Extract problem string from content
        let problem = match &message.content {
            serde_json::Value::String(s) => s.clone(),
            other => other.to_string(),
        };

        // Step 1: Build reasoning graph
        let graph = self.build_graph(&problem).await?;

        // Step 2: Check for cycles (if not allowed)
        if !self.allow_cycles && graph.has_cycle() {
            // For now, just continue - cycles detected but not removed
            // Could implement cycle removal in future
        }

        // Step 3: Find reasoning paths
        let reasoning_paths = self.find_reasoning_paths(&graph);

        // Step 4: Aggregate paths to final answer
        let final_answer = self.aggregate_paths(&graph, &reasoning_paths);

        // Get statistics
        let stats = graph.statistics();

        let mut metadata = std::collections::HashMap::new();
        metadata.insert("technique".to_string(), json!("graph_of_thought"));
        metadata.insert("num_nodes".to_string(), json!(stats.num_nodes));
        metadata.insert("num_edges".to_string(), json!(stats.num_edges));
        metadata.insert("has_cycles".to_string(), json!(stats.has_cycles));
        metadata.insert("node_types".to_string(), json!(stats.node_types));
        metadata.insert("edge_types".to_string(), json!(stats.edge_types));
        metadata.insert(
            "num_reasoning_paths".to_string(),
            json!(reasoning_paths.len()),
        );
        metadata.insert(
            "aggregator".to_string(),
            json!(match self.aggregator {
                AggregatorType::PathBased => "path_based",
                AggregatorType::NodeBased => "node_based",
            }),
        );
        metadata.insert("allow_cycles".to_string(), json!(self.allow_cycles));

        let mut message = Message::new("assistant", serde_json::Value::String(final_answer));
        message.metadata = metadata;
        Ok(message)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    struct MockAgent {
        responses: Mutex<Vec<String>>,
        call_count: Mutex<usize>,
    }

    impl MockAgent {
        fn new(responses: Vec<String>) -> Self {
            Self {
                responses: Mutex::new(responses),
                call_count: Mutex::new(0),
            }
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
            let mut count = self.call_count.lock().unwrap();
            let responses = self.responses.lock().unwrap();
            let response = responses[*count % responses.len()].clone();
            *count += 1;

            Ok(Message::new(
                "assistant",
                serde_json::Value::String(response),
            ))
        }
    }

    #[tokio::test]
    async fn test_create_agent_default_config() {
        let mock = Arc::new(MockAgent::new(vec![]));
        let agent = GraphOfThoughtAgent::new(mock, GraphOfThoughtConfig::default());
        assert_eq!(agent.name(), "graph_of_thought");
    }

    #[tokio::test]
    async fn test_create_agent_custom_config() {
        let mock = Arc::new(MockAgent::new(vec![]));
        let config = GraphOfThoughtConfig {
            max_nodes: 15,
            max_edges: 30,
            aggregator: AggregatorType::NodeBased,
            allow_cycles: true,
        };
        let agent = GraphOfThoughtAgent::new(mock, config);
        assert_eq!(agent.max_nodes, 15);
        assert_eq!(agent.max_edges, 30);
        assert_eq!(agent.aggregator, AggregatorType::NodeBased);
        assert!(agent.allow_cycles);
    }

    #[tokio::test]
    async fn test_capabilities() {
        let mock = Arc::new(MockAgent::new(vec![]));
        let agent = GraphOfThoughtAgent::new(mock, GraphOfThoughtConfig::default());
        let caps = agent.capabilities();
        assert!(caps.contains(&"graph_reasoning".to_string()));
        assert!(caps.contains(&"multi_hop".to_string()));
    }

    #[tokio::test]
    async fn test_generate_premises() {
        let mock = Arc::new(MockAgent::new(vec![
            "1. Premise A\n2. Premise B".to_string()
        ]));
        let agent = GraphOfThoughtAgent::new(mock, GraphOfThoughtConfig::default());

        let premises = agent.generate_premises("Test problem").await.unwrap();
        assert_eq!(premises.len(), 2);
        assert_eq!(premises[0], "Premise A");
        assert_eq!(premises[1], "Premise B");
    }

    #[tokio::test]
    async fn test_generate_thoughts() {
        let mock = Arc::new(MockAgent::new(vec![
            "1. Thought 1\n2. Thought 2".to_string()
        ]));
        let agent = GraphOfThoughtAgent::new(mock, GraphOfThoughtConfig::default());

        let existing = vec!["Premise A".to_string()];
        let thoughts = agent.generate_thoughts("Test", &existing, 3).await.unwrap();
        assert_eq!(thoughts.len(), 2);
        assert_eq!(thoughts[0], "Thought 1");
    }

    #[tokio::test]
    async fn test_identify_connection() {
        let mock = Arc::new(MockAgent::new(vec!["SUPPORT".to_string()]));
        let agent = GraphOfThoughtAgent::new(mock, GraphOfThoughtConfig::default());

        let edge = agent
            .identify_connection("Thought 1", "Thought 2")
            .await
            .unwrap();
        assert_eq!(edge, Some(EdgeType::Supports));
    }

    #[tokio::test]
    async fn test_complete_workflow() {
        let mock = Arc::new(MockAgent::new(vec![
            "1. Premise A\n2. Premise B".to_string(),
            "1. Thought 1".to_string(),
            "".to_string(),
            "SUPPORT".to_string(),
            "Final conclusion".to_string(),
        ]));
        let config = GraphOfThoughtConfig {
            max_nodes: 5,
            ..Default::default()
        };
        let agent = GraphOfThoughtAgent::new(mock, config);

        let message = Message::new(
            "user",
            serde_json::Value::String("Test problem".to_string()),
        );

        let response = agent.process(message).await.unwrap();
        assert_eq!(response.role, "assistant");
        assert!(matches!(response.content, serde_json::Value::String(_)));
        assert!(!response.metadata.is_empty());
        assert!(response.metadata.contains_key("technique"));
    }

    // Additional comprehensive tests

    #[tokio::test]
    async fn test_max_nodes_limit() {
        let mock = Arc::new(MockAgent::new(vec![
            "1. Premise A\n2. Premise B".to_string(),
            "1. Thought 1".to_string(),
            "".to_string(),
            "SUPPORT".to_string(),
            "Final conclusion".to_string(),
        ]));
        let config = GraphOfThoughtConfig {
            max_nodes: 3,
            ..Default::default()
        };
        let agent = GraphOfThoughtAgent::new(mock, config);

        let message = Message::new("user", serde_json::Value::String("Test".to_string()));
        let response = agent.process(message).await.unwrap();

        let num_nodes = response.metadata["num_nodes"].as_u64().unwrap();
        assert!(num_nodes <= 3);
    }

    #[tokio::test]
    async fn test_max_edges_limit() {
        let mock = Arc::new(MockAgent::new(vec![
            "1. Premise A".to_string(),
            "1. Thought 1".to_string(),
            "".to_string(),
            "SUPPORT".to_string(),
            "Final conclusion".to_string(),
        ]));
        let config = GraphOfThoughtConfig {
            max_nodes: 10,
            max_edges: 2,
            ..Default::default()
        };
        let agent = GraphOfThoughtAgent::new(mock, config);

        let message = Message::new("user", serde_json::Value::String("Test".to_string()));
        let response = agent.process(message).await.unwrap();

        let num_edges = response.metadata["num_edges"].as_u64().unwrap();
        assert!(num_edges <= 2);
    }

    #[tokio::test]
    async fn test_path_based_aggregation() {
        let mock = Arc::new(MockAgent::new(vec![
            "1. Premise A".to_string(),
            "1. Thought 1".to_string(),
            "".to_string(),
            "SUPPORT".to_string(),
            "Final conclusion".to_string(),
        ]));
        let config = GraphOfThoughtConfig {
            aggregator: AggregatorType::PathBased,
            ..Default::default()
        };
        let agent = GraphOfThoughtAgent::new(mock, config);

        let message = Message::new("user", serde_json::Value::String("Test".to_string()));
        let response = agent.process(message).await.unwrap();

        assert_eq!(
            response.metadata["aggregator"].as_str().unwrap(),
            "path_based"
        );
        assert!(matches!(response.content, serde_json::Value::String(_)));
    }

    #[tokio::test]
    async fn test_node_based_aggregation() {
        let mock = Arc::new(MockAgent::new(vec![
            "1. Premise A".to_string(),
            "1. Thought 1".to_string(),
            "".to_string(),
            "SUPPORT".to_string(),
            "Final conclusion".to_string(),
        ]));
        let config = GraphOfThoughtConfig {
            aggregator: AggregatorType::NodeBased,
            ..Default::default()
        };
        let agent = GraphOfThoughtAgent::new(mock, config);

        let message = Message::new("user", serde_json::Value::String("Test".to_string()));
        let response = agent.process(message).await.unwrap();

        assert_eq!(
            response.metadata["aggregator"].as_str().unwrap(),
            "node_based"
        );
        assert!(matches!(response.content, serde_json::Value::String(_)));
    }

    #[tokio::test]
    async fn test_metadata_completeness() {
        let mock = Arc::new(MockAgent::new(vec![
            "1. Premise A".to_string(),
            "1. Thought 1".to_string(),
            "".to_string(),
            "SUPPORT".to_string(),
            "Final conclusion".to_string(),
        ]));
        let agent = GraphOfThoughtAgent::new(mock, GraphOfThoughtConfig::default());

        let message = Message::new("user", serde_json::Value::String("Test".to_string()));
        let response = agent.process(message).await.unwrap();

        // Check all required metadata fields
        assert!(response.metadata.contains_key("technique"));
        assert_eq!(
            response.metadata["technique"].as_str().unwrap(),
            "graph_of_thought"
        );
        assert!(response.metadata.contains_key("num_nodes"));
        assert!(response.metadata.contains_key("num_edges"));
        assert!(response.metadata.contains_key("has_cycles"));
        assert!(response.metadata.contains_key("aggregator"));
        assert!(response.metadata.contains_key("allow_cycles"));
    }

    #[tokio::test]
    async fn test_allow_cycles_true() {
        let mock = Arc::new(MockAgent::new(vec![
            "1. Premise A".to_string(),
            "1. Thought 1".to_string(),
            "".to_string(),
            "SUPPORT".to_string(),
            "Final conclusion".to_string(),
        ]));
        let config = GraphOfThoughtConfig {
            allow_cycles: true,
            ..Default::default()
        };
        let agent = GraphOfThoughtAgent::new(mock, config);

        let message = Message::new("user", serde_json::Value::String("Test".to_string()));
        let response = agent.process(message).await.unwrap();

        assert_eq!(response.metadata["allow_cycles"].as_bool().unwrap(), true);
    }

    #[tokio::test]
    async fn test_allow_cycles_false() {
        let mock = Arc::new(MockAgent::new(vec![
            "1. Premise A".to_string(),
            "1. Thought 1".to_string(),
            "".to_string(),
            "SUPPORT".to_string(),
            "Final conclusion".to_string(),
        ]));
        let config = GraphOfThoughtConfig {
            allow_cycles: false,
            ..Default::default()
        };
        let agent = GraphOfThoughtAgent::new(mock, config);

        let message = Message::new("user", serde_json::Value::String("Test".to_string()));
        let response = agent.process(message).await.unwrap();

        assert_eq!(response.metadata["allow_cycles"].as_bool().unwrap(), false);
    }

    #[tokio::test]
    async fn test_aggregator_type_equality() {
        assert_eq!(AggregatorType::PathBased, AggregatorType::PathBased);
        assert_eq!(AggregatorType::NodeBased, AggregatorType::NodeBased);
        assert_ne!(AggregatorType::PathBased, AggregatorType::NodeBased);
    }

    #[tokio::test]
    async fn test_edge_type_identify_support() {
        let mock = Arc::new(MockAgent::new(vec!["SUPPORT".to_string()]));
        let agent = GraphOfThoughtAgent::new(mock, GraphOfThoughtConfig::default());

        let edge = agent.identify_connection("A", "B").await.unwrap();
        assert_eq!(edge, Some(EdgeType::Supports));
    }

    #[tokio::test]
    async fn test_edge_type_identify_depends() {
        let mock = Arc::new(MockAgent::new(vec!["DEPEND".to_string()]));
        let agent = GraphOfThoughtAgent::new(mock, GraphOfThoughtConfig::default());

        let edge = agent.identify_connection("A", "B").await.unwrap();
        assert_eq!(edge, Some(EdgeType::DependsOn));
    }

    #[tokio::test]
    async fn test_edge_type_identify_contradicts() {
        let mock = Arc::new(MockAgent::new(vec!["CONTRADICT".to_string()]));
        let agent = GraphOfThoughtAgent::new(mock, GraphOfThoughtConfig::default());

        let edge = agent.identify_connection("A", "B").await.unwrap();
        assert_eq!(edge, Some(EdgeType::Contradicts));
    }

    #[tokio::test]
    async fn test_edge_type_identify_refines() {
        let mock = Arc::new(MockAgent::new(vec!["REFINE".to_string()]));
        let agent = GraphOfThoughtAgent::new(mock, GraphOfThoughtConfig::default());

        let edge = agent.identify_connection("A", "B").await.unwrap();
        assert_eq!(edge, Some(EdgeType::Refines));
    }

    #[tokio::test]
    async fn test_edge_type_identify_none() {
        let mock = Arc::new(MockAgent::new(vec!["UNKNOWN".to_string()]));
        let agent = GraphOfThoughtAgent::new(mock, GraphOfThoughtConfig::default());

        let edge = agent.identify_connection("A", "B").await.unwrap();
        assert_eq!(edge, None);
    }

    #[tokio::test]
    async fn test_generate_thoughts_with_limit() {
        let mock = Arc::new(MockAgent::new(vec![
            "1. Thought 1\n2. Thought 2\n3. Thought 3\n4. Thought 4".to_string(),
        ]));
        let agent = GraphOfThoughtAgent::new(mock, GraphOfThoughtConfig::default());

        let existing = vec!["Premise".to_string()];
        let thoughts = agent.generate_thoughts("Test", &existing, 2).await.unwrap();

        // Should respect max_new limit
        assert!(thoughts.len() <= 2);
    }

    #[tokio::test]
    async fn test_response_role() {
        let mock = Arc::new(MockAgent::new(vec![
            "1. Premise A".to_string(),
            "1. Thought 1".to_string(),
            "".to_string(),
            "SUPPORT".to_string(),
            "Final conclusion".to_string(),
        ]));
        let agent = GraphOfThoughtAgent::new(mock, GraphOfThoughtConfig::default());

        let message = Message::new("user", serde_json::Value::String("Test".to_string()));
        let response = agent.process(message).await.unwrap();

        assert_eq!(response.role, "assistant");
    }

    #[tokio::test]
    async fn test_default_config_values() {
        let config = GraphOfThoughtConfig::default();
        assert_eq!(config.max_nodes, 20);
        assert_eq!(config.max_edges, 40);
        assert_eq!(config.aggregator, AggregatorType::PathBased);
        assert_eq!(config.allow_cycles, false);
    }
}
