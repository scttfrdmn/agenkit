// Least-to-Most Prompting Technique
//
// Breaks complex problems into simpler subproblems, solves them sequentially
// from simplest to most complex, using solutions to build up to the final answer.
//
// This technique is particularly effective for compositional reasoning where
// complex problems can be decomposed into manageable pieces.
//
// Reference: "Least-to-Most Prompting Enables Complex Reasoning in Large Language Models"
// Zhou et al., 2022 - https://arxiv.org/abs/2205.10625

use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use regex::Regex;
use serde_json::json;
use std::sync::Arc;

/// Represents a subproblem in the decomposition.
#[derive(Debug, Clone)]
pub struct Subproblem {
    /// The content/description of the subproblem
    pub content: String,

    /// Difficulty level (0 = easiest)
    pub difficulty: usize,

    /// Indices of subproblems this depends on
    pub dependencies: Vec<usize>,
}

/// Type alias for custom decomposer function.
pub type DecomposerFn = Arc<dyn Fn(&str) -> Result<Vec<String>, AgentError> + Send + Sync>;

/// Configuration for Least-to-Most.
pub struct LeastToMostConfig {
    /// Custom function to decompose problems into subproblems.
    /// If None, uses LLM to decompose.
    pub decomposer: Option<DecomposerFn>,

    /// Maximum number of subproblems to generate (default: 5)
    pub max_subproblems: usize,

    /// Whether to use previous subproblem solutions as context
    /// when solving harder problems (default: true)
    pub compose_solutions: bool,
}

impl Default for LeastToMostConfig {
    fn default() -> Self {
        Self {
            decomposer: None,
            max_subproblems: 5,
            compose_solutions: true,
        }
    }
}

/// Least-to-Most agent that wraps a base agent.
///
/// Decomposes complex problems into simpler subproblems, solves them
/// sequentially from easiest to hardest, using previous solutions as
/// context for solving harder problems.
///
/// This technique is particularly effective for:
/// - Compositional reasoning tasks
/// - Multi-step math problems
/// - Problems that naturally decompose into stages
/// - Tasks where simpler subtasks inform harder ones
///
/// # Example
///
/// ```no_run
/// use agenkit::techniques::reasoning::{LeastToMostAgent, LeastToMostConfig};
/// use std::sync::Arc;
///
/// let base_agent = Arc::new(my_agent);
/// let config = LeastToMostConfig {
///     max_subproblems: 5,
///     compose_solutions: true,
///     ..Default::default()
/// };
///
/// let ltm = LeastToMostAgent::new(base_agent, config);
/// let response = ltm.process(message).await?;
/// // Access subproblems and solutions from metadata
/// ```
pub struct LeastToMostAgent {
    agent: Arc<dyn Agent>,
    decomposer: Option<DecomposerFn>,
    max_subproblems: usize,
    compose_solutions: bool,
}

impl LeastToMostAgent {
    /// Create a new Least-to-Most agent.
    pub fn new(agent: Arc<dyn Agent>, config: LeastToMostConfig) -> Self {
        Self {
            agent,
            decomposer: config.decomposer,
            max_subproblems: config.max_subproblems,
            compose_solutions: config.compose_solutions,
        }
    }

    /// Decompose problem into subproblems.
    ///
    /// Uses custom decomposer if provided, otherwise uses LLM.
    async fn decompose(&self, problem: &str) -> Result<Vec<Subproblem>, AgentError> {
        if let Some(decomposer) = &self.decomposer {
            // Use custom decomposer
            let subproblem_texts = decomposer(problem)?;
            let mut subproblems = Vec::new();

            for (i, text) in subproblem_texts.iter().enumerate() {
                if i >= self.max_subproblems {
                    break;
                }
                subproblems.push(Subproblem {
                    content: text.clone(),
                    difficulty: i,
                    dependencies: Vec::new(),
                });
            }

            return Ok(subproblems);
        }

        // Use LLM to decompose
        let decomposition_prompt = format!(
            "Break down this problem into simpler subproblems, ordered from easiest to hardest.\n\
            List each subproblem on a separate line, numbered 1, 2, 3, etc.\n\n\
            Problem: {}\n\n\
            Subproblems (from simplest to most complex):",
            problem
        );

        let prompt_message = Message::with_text("user", decomposition_prompt);
        let response = self
            .agent
            .process(prompt_message)
            .await
            .map_err(|e| AgentError::Internal(format!("Decomposition failed: {}", e)))?;

        // Parse subproblems from response
        let response_text = response.content_as_str().unwrap_or("");
        let subproblems = self.parse_subproblems(response_text, problem);

        Ok(subproblems)
    }

    /// Parse subproblems from LLM response.
    fn parse_subproblems(&self, response_text: &str, original_problem: &str) -> Vec<Subproblem> {
        let mut subproblems = Vec::new();
        let lines = response_text.trim().split('\n');

        // Regex to match numbered lines (1., 1), etc.)
        let numbered_regex = Regex::new(r"^\d+[.)]").unwrap();
        let cleanup_regex = Regex::new(r"^\d+[.)]\s*").unwrap();

        for (i, line) in lines.enumerate() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }

            // Only match lines that START with a number followed by . or )
            if !numbered_regex.is_match(line) {
                continue;
            }

            // Remove numbering
            let cleaned = cleanup_regex.replace(line, "").to_string();

            if !cleaned.is_empty() && subproblems.len() < self.max_subproblems {
                subproblems.push(Subproblem {
                    content: cleaned,
                    difficulty: i,
                    dependencies: Vec::new(),
                });
            }
        }

        // If decomposition failed or no valid numbered steps found, treat as atomic problem
        if subproblems.is_empty() {
            subproblems.push(Subproblem {
                content: original_problem.to_string(),
                difficulty: 0,
                dependencies: Vec::new(),
            });
        }

        subproblems
    }

    /// Solve one subproblem, optionally using previous solutions as context.
    async fn solve_subproblem(
        &self,
        subproblem: &Subproblem,
        previous_solutions: &[String],
    ) -> Result<String, AgentError> {
        let prompt = if self.compose_solutions && !previous_solutions.is_empty() {
            // Include previous solutions as context
            let context = previous_solutions
                .iter()
                .enumerate()
                .map(|(i, sol)| format!("Previous solution {}: {}", i + 1, sol))
                .collect::<Vec<_>>()
                .join("\n");

            format!(
                "Given these previous solutions to simpler subproblems:\n\n{}\n\n\
                Now solve this subproblem:\n{}\n\nSolution:",
                context, subproblem.content
            )
        } else {
            // Solve without context
            format!(
                "Solve this subproblem:\n\n{}\n\nSolution:",
                subproblem.content
            )
        };

        let prompt_message = Message::with_text("user", prompt);
        let response = self.agent.process(prompt_message).await.map_err(|e| {
            AgentError::Internal(format!("Subproblem solving failed: {}", e))
        })?;

        Ok(response
            .content_as_str()
            .unwrap_or("")
            .trim()
            .to_string())
    }
}

#[async_trait]
impl Agent for LeastToMostAgent {
    fn name(&self) -> &str {
        "least_to_most"
    }

    fn capabilities(&self) -> Vec<String> {
        vec![
            "reasoning".to_string(),
            "decomposition".to_string(),
            "compositional_reasoning".to_string(),
            "least_to_most".to_string(),
            "sequential_solving".to_string(),
        ]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let problem = message.content_as_str().unwrap_or("").to_string();

        // Step 1: Decompose problem
        let subproblems = self.decompose(&problem).await?;

        // Step 2: Solve subproblems sequentially
        let mut solutions = Vec::new();
        for subproblem in &subproblems {
            let solution = self.solve_subproblem(subproblem, &solutions).await?;
            solutions.push(solution);
        }

        // Step 3: Final solution is the last one (hardest problem)
        let final_solution = solutions.last().cloned().unwrap_or_default();

        // Build subproblem texts for metadata
        let subproblem_texts: Vec<String> =
            subproblems.iter().map(|sp| sp.content.clone()).collect();

        let mut result = Message::with_text("assistant", final_solution);
        result
            .metadata
            .insert("technique".to_string(), json!("least_to_most"));
        result
            .metadata
            .insert("num_subproblems".to_string(), json!(subproblems.len()));
        result
            .metadata
            .insert("subproblems".to_string(), json!(subproblem_texts));
        result
            .metadata
            .insert("subproblem_solutions".to_string(), json!(solutions));
        result
            .metadata
            .insert("compose_solutions".to_string(), json!(self.compose_solutions));

        Ok(result)
    }
}
