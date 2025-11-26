//! Prompt Optimization Framework
//!
//! Automatically improve prompts through systematic variation and testing.
//!
//! Supports multiple optimization strategies:
//! - Grid search: Exhaustive evaluation of all combinations
//! - Random search: Random sampling of combinations
//! - Genetic algorithm: Evolutionary optimization
//!
//! # Example
//!
//! ```no_run
//! use agenkit::evaluation::prompt_optimizer::{PromptOptimizer, OptimizationStrategy};
//! use agenkit::core::Agent;
//! use std::sync::Arc;
//! use std::collections::HashMap;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // Define template with {variable} placeholders
//! let template = "You are a {role}.\n{instructions}";
//!
//! // Define variations for each variable
//! let mut variations = HashMap::new();
//! variations.insert("role".to_string(), vec![
//!     "helpful assistant".to_string(),
//!     "expert advisor".to_string(),
//! ]);
//! variations.insert("instructions".to_string(), vec![
//!     "Be concise.".to_string(),
//!     "Be detailed.".to_string(),
//! ]);
//!
//! // Create agent factory
//! let factory = |prompt: String| -> Arc<dyn Agent> {
//!     // Return agent configured with prompt
//!     # todo!()
//! };
//!
//! // Create optimizer
//! let optimizer = PromptOptimizer::new(
//!     template,
//!     variations,
//!     Box::new(factory),
//!     vec!["accuracy".to_string()],
//!     None,
//! );
//!
//! // Optimize using grid search
//! let test_cases = vec![]; // Your test cases
//! let result = optimizer.optimize_grid(test_cases).await?;
//! println!("Best prompt: {}", result.best_prompt);
//! # Ok(())
//! # }
//! ```

use crate::core::{Agent, Message, AgentError};
use std::collections::HashMap;
use std::sync::Arc;
use std::pin::Pin;
use std::future::Future;
use serde::{Serialize, Deserialize};
use chrono::Utc;
use rand::Rng;

/// Optimization strategy for prompt search.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OptimizationStrategy {
    /// Exhaustive grid search
    Grid,
    /// Random sampling
    Random,
    /// Genetic algorithm
    Genetic,
}

impl OptimizationStrategy {
    /// Returns string representation.
    pub fn as_str(&self) -> &str {
        match self {
            Self::Grid => "grid",
            Self::Random => "random",
            Self::Genetic => "genetic",
        }
    }
}

/// Single prompt evaluation result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PromptEvaluation {
    /// Generated prompt
    pub prompt: String,
    /// Variable configuration used
    pub config: HashMap<String, String>,
    /// Metric scores achieved
    pub scores: HashMap<String, f64>,
}

/// Result from prompt optimization.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PromptOptimizationResult {
    /// Best prompt found
    pub best_prompt: String,
    /// Best configuration found
    pub best_config: HashMap<String, String>,
    /// Best scores achieved
    pub best_scores: HashMap<String, f64>,
    /// All evaluations performed
    pub history: Vec<PromptEvaluation>,
    /// Number of prompts evaluated
    pub n_evaluated: usize,
    /// Strategy used
    pub strategy: String,
    /// Start time (milliseconds)
    pub start_time: i64,
    /// End time (milliseconds)
    pub end_time: i64,
}

impl PromptOptimizationResult {
    /// Returns duration in seconds.
    pub fn duration_seconds(&self) -> f64 {
        (self.end_time - self.start_time) as f64 / 1000.0
    }

    /// Converts to dictionary representation.
    pub fn to_dict(&self) -> HashMap<String, serde_json::Value> {
        let mut result = HashMap::new();
        result.insert("best_prompt".to_string(), serde_json::json!(self.best_prompt));
        result.insert("best_config".to_string(), serde_json::json!(self.best_config));
        result.insert("best_scores".to_string(), serde_json::json!(self.best_scores));
        result.insert("n_evaluated".to_string(), serde_json::json!(self.n_evaluated));
        result.insert("strategy".to_string(), serde_json::json!(self.strategy));
        result.insert("duration_seconds".to_string(), serde_json::json!(self.duration_seconds()));
        result.insert("start_time".to_string(), serde_json::json!(self.start_time));
        result.insert("end_time".to_string(), serde_json::json!(self.end_time));
        result
    }
}

/// Factory function for creating agents from prompts.
pub type AgentFactory = Box<dyn Fn(String) -> Arc<dyn Agent> + Send + Sync>;

/// Evaluator function for scoring prompts on test cases.
pub type PromptEvaluatorFunc = Box<
    dyn Fn(Arc<dyn Agent>, Vec<HashMap<String, serde_json::Value>>)
        -> Pin<Box<dyn Future<Output = Result<HashMap<String, f64>, AgentError>> + Send>>
        + Send
        + Sync
>;

/// Prompt optimizer that systematically varies and tests prompts.
///
/// Uses template-based generation with multiple optimization strategies.
pub struct PromptOptimizer {
    template: String,
    variations: HashMap<String, Vec<String>>,
    agent_factory: AgentFactory,
    metrics: Vec<String>,
    objective_metric: String,
    maximize: bool,
    history: Vec<PromptEvaluation>,
    evaluator: Option<PromptEvaluatorFunc>,
}

impl PromptOptimizer {
    /// Creates a new prompt optimizer.
    ///
    /// # Arguments
    ///
    /// * `template` - Prompt template with {variable} placeholders
    /// * `variations` - Map of variable names to possible values
    /// * `agent_factory` - Function that creates agent from prompt string
    /// * `metrics` - List of metrics to evaluate
    /// * `objective_metric` - Primary metric for optimization (None = first metric)
    pub fn new(
        template: impl Into<String>,
        variations: HashMap<String, Vec<String>>,
        agent_factory: AgentFactory,
        metrics: Vec<String>,
        objective_metric: Option<String>,
    ) -> Self {
        let objective = objective_metric.unwrap_or_else(|| {
            metrics.first().cloned().unwrap_or_else(|| "accuracy".to_string())
        });

        Self {
            template: template.into(),
            variations,
            agent_factory,
            metrics,
            objective_metric: objective,
            maximize: true,
            history: Vec::new(),
            evaluator: None,
        }
    }

    /// Sets whether to maximize (true) or minimize (false) the objective.
    pub fn set_maximize(&mut self, maximize: bool) {
        self.maximize = maximize;
    }

    /// Sets custom evaluator function.
    pub fn set_evaluator(&mut self, evaluator: PromptEvaluatorFunc) {
        self.evaluator = Some(evaluator);
    }

    /// Fills template with configuration values.
    fn fill_template(&self, config: &HashMap<String, String>) -> String {
        let mut result = self.template.clone();
        for (key, value) in config {
            let placeholder = format!("{{{}}}", key);
            result = result.replace(&placeholder, value);
        }
        result
    }

    /// Generates all possible configurations (Cartesian product).
    fn generate_all_configs(&self) -> Vec<HashMap<String, String>> {
        let keys: Vec<String> = self.variations.keys().cloned().collect();
        let value_lists: Vec<Vec<String>> = keys.iter()
            .map(|k| self.variations[k].clone())
            .collect();

        self.cartesian_product(&keys, &value_lists, 0, HashMap::new())
    }

    /// Generates Cartesian product recursively.
    fn cartesian_product(
        &self,
        keys: &[String],
        value_lists: &[Vec<String>],
        index: usize,
        current: HashMap<String, String>,
    ) -> Vec<HashMap<String, String>> {
        if index == keys.len() {
            // Base case: return copy of current config
            return vec![current];
        }

        let mut results = Vec::new();
        for value in &value_lists[index] {
            let mut new_config = current.clone();
            new_config.insert(keys[index].clone(), value.clone());
            let configs = self.cartesian_product(keys, value_lists, index + 1, new_config);
            results.extend(configs);
        }

        results
    }

    /// Samples a random configuration.
    fn sample_config(&self) -> HashMap<String, String> {
        let mut rng = rand::thread_rng();
        let mut config = HashMap::new();

        for (key, values) in &self.variations {
            let idx = rng.gen_range(0..values.len());
            config.insert(key.clone(), values[idx].clone());
        }

        config
    }

    /// Evaluates a prompt on test cases.
    async fn evaluate_prompt(
        &self,
        prompt: String,
        test_cases: &[HashMap<String, serde_json::Value>],
    ) -> Result<HashMap<String, f64>, AgentError> {
        // Create agent with prompt
        let agent = (self.agent_factory)(prompt);

        // Use custom evaluator if provided
        if let Some(ref evaluator) = self.evaluator {
            return evaluator(agent, test_cases.to_vec()).await;
        }

        // Default evaluation: run agent and collect basic metrics
        let mut total_latency = 0.0;
        let mut success_count = 0;

        for test_case in test_cases {
            let input = match test_case.get("input") {
                Some(serde_json::Value::String(s)) => s.clone(),
                _ => continue,
            };

            let start_time = Utc::now();
            let message = Message::new("user", serde_json::json!(input));

            let result = agent.process(message).await;
            let end_time = Utc::now();
            let latency = (end_time - start_time).num_milliseconds() as f64;

            total_latency += latency;
            if result.is_ok() {
                success_count += 1;
            }
        }

        let mut scores = HashMap::new();
        if !test_cases.is_empty() {
            scores.insert("accuracy".to_string(), success_count as f64 / test_cases.len() as f64);
            scores.insert("latency_ms".to_string(), total_latency / test_cases.len() as f64);
        }

        Ok(scores)
    }

    /// Gets objective score from metric scores.
    fn get_objective_score(&self, scores: &HashMap<String, f64>) -> f64 {
        let score = scores.get(&self.objective_metric).copied().unwrap_or(0.0);

        // Invert if minimizing
        if self.maximize {
            score
        } else {
            -score
        }
    }

    /// Performs grid search by evaluating all possible combinations.
    pub async fn optimize_grid(
        &mut self,
        test_cases: Vec<HashMap<String, serde_json::Value>>,
    ) -> Result<PromptOptimizationResult, AgentError> {
        let start_time = Utc::now().timestamp_millis();
        self.history.clear();

        // Generate all configs
        let configs = self.generate_all_configs();

        let mut best_prompt = String::new();
        let mut best_config = HashMap::new();
        let mut best_scores = HashMap::new();
        let mut best_objective = -1e9;

        // Evaluate each configuration
        for config in &configs {
            let prompt = self.fill_template(config);
            let scores = self.evaluate_prompt(prompt.clone(), &test_cases).await?;
            let objective_score = self.get_objective_score(&scores);

            self.history.push(PromptEvaluation {
                prompt: prompt.clone(),
                config: config.clone(),
                scores: scores.clone(),
            });

            if objective_score > best_objective {
                best_objective = objective_score;
                best_prompt = prompt;
                best_config = config.clone();
                best_scores = scores;
            }
        }

        let end_time = Utc::now().timestamp_millis();

        Ok(PromptOptimizationResult {
            best_prompt,
            best_config,
            best_scores,
            history: self.history.clone(),
            n_evaluated: configs.len(),
            strategy: OptimizationStrategy::Grid.as_str().to_string(),
            start_time,
            end_time,
        })
    }

    /// Performs random search by sampling random combinations.
    pub async fn optimize_random(
        &mut self,
        test_cases: Vec<HashMap<String, serde_json::Value>>,
        n_samples: usize,
    ) -> Result<PromptOptimizationResult, AgentError> {
        let start_time = Utc::now().timestamp_millis();
        self.history.clear();

        let mut best_prompt = String::new();
        let mut best_config = HashMap::new();
        let mut best_scores = HashMap::new();
        let mut best_objective = -1e9;

        // Sample and evaluate random configurations
        for _ in 0..n_samples {
            let config = self.sample_config();
            let prompt = self.fill_template(&config);
            let scores = self.evaluate_prompt(prompt.clone(), &test_cases).await?;
            let objective_score = self.get_objective_score(&scores);

            self.history.push(PromptEvaluation {
                prompt: prompt.clone(),
                config: config.clone(),
                scores: scores.clone(),
            });

            if objective_score > best_objective {
                best_objective = objective_score;
                best_prompt = prompt;
                best_config = config;
                best_scores = scores;
            }
        }

        let end_time = Utc::now().timestamp_millis();

        Ok(PromptOptimizationResult {
            best_prompt,
            best_config,
            best_scores,
            history: self.history.clone(),
            n_evaluated: n_samples,
            strategy: OptimizationStrategy::Random.as_str().to_string(),
            start_time,
            end_time,
        })
    }

    /// Performs genetic algorithm optimization.
    pub async fn optimize_genetic(
        &mut self,
        test_cases: Vec<HashMap<String, serde_json::Value>>,
        population_size: usize,
        n_generations: usize,
        mutation_rate: f64,
    ) -> Result<PromptOptimizationResult, AgentError> {
        let start_time = Utc::now().timestamp_millis();
        self.history.clear();

        let mut rng = rand::thread_rng();

        // Initialize population with random configurations
        let mut population: Vec<HashMap<String, String>> = (0..population_size)
            .map(|_| self.sample_config())
            .collect();

        let mut fitness_scores = vec![0.0; population_size];

        // Evaluate initial population
        for (i, config) in population.iter().enumerate() {
            let prompt = self.fill_template(config);
            let scores = self.evaluate_prompt(prompt.clone(), &test_cases).await?;
            let objective_score = self.get_objective_score(&scores);
            fitness_scores[i] = objective_score;

            self.history.push(PromptEvaluation {
                prompt,
                config: config.clone(),
                scores,
            });
        }

        // Evolution loop
        for _ in 0..n_generations {
            // Selection: Tournament selection
            let mut new_population = Vec::new();
            for _ in 0..population_size {
                let idx1 = rng.gen_range(0..population_size);
                let mut idx2 = rng.gen_range(0..population_size);
                while idx2 == idx1 {
                    idx2 = rng.gen_range(0..population_size);
                }

                // Choose fitter one
                let winner_idx = if fitness_scores[idx2] > fitness_scores[idx1] {
                    idx2
                } else {
                    idx1
                };

                new_population.push(population[winner_idx].clone());
            }

            // Mutation
            for config in &mut new_population {
                for key in config.clone().keys() {
                    if rng.gen::<f64>() < mutation_rate {
                        let values = &self.variations[key];
                        let idx = rng.gen_range(0..values.len());
                        config.insert(key.clone(), values[idx].clone());
                    }
                }
            }

            // Evaluate new population
            population = new_population;
            fitness_scores = vec![0.0; population_size];

            for (i, config) in population.iter().enumerate() {
                let prompt = self.fill_template(config);
                let scores = self.evaluate_prompt(prompt.clone(), &test_cases).await?;
                let objective_score = self.get_objective_score(&scores);
                fitness_scores[i] = objective_score;

                self.history.push(PromptEvaluation {
                    prompt,
                    config: config.clone(),
                    scores,
                });
            }
        }

        // Find best from all history
        let mut best_idx = 0;
        let mut best_objective = self.get_objective_score(&self.history[0].scores);
        for (i, eval) in self.history.iter().enumerate().skip(1) {
            let obj_score = self.get_objective_score(&eval.scores);
            if obj_score > best_objective {
                best_objective = obj_score;
                best_idx = i;
            }
        }

        let best_eval = &self.history[best_idx];
        let end_time = Utc::now().timestamp_millis();

        Ok(PromptOptimizationResult {
            best_prompt: best_eval.prompt.clone(),
            best_config: best_eval.config.clone(),
            best_scores: best_eval.scores.clone(),
            history: self.history.clone(),
            n_evaluated: self.history.len(),
            strategy: OptimizationStrategy::Genetic.as_str().to_string(),
            start_time,
            end_time,
        })
    }

    /// Runs prompt optimization with the specified strategy.
    ///
    /// # Arguments
    ///
    /// * `test_cases` - Test cases for evaluation
    /// * `strategy` - Optimization strategy
    /// * `options` - Strategy-specific options
    pub async fn optimize(
        &mut self,
        test_cases: Vec<HashMap<String, serde_json::Value>>,
        strategy: OptimizationStrategy,
        options: HashMap<String, serde_json::Value>,
    ) -> Result<PromptOptimizationResult, AgentError> {
        match strategy {
            OptimizationStrategy::Grid => {
                self.optimize_grid(test_cases).await
            }

            OptimizationStrategy::Random => {
                let n_samples = options.get("n_samples")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(20) as usize;
                self.optimize_random(test_cases, n_samples).await
            }

            OptimizationStrategy::Genetic => {
                let population_size = options.get("population_size")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(10) as usize;
                let n_generations = options.get("n_generations")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(5) as usize;
                let mutation_rate = options.get("mutation_rate")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(0.2);

                self.optimize_genetic(test_cases, population_size, n_generations, mutation_rate).await
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Mock agent for testing
    struct MockAgent {
        _prompt: String,
    }

    #[async_trait::async_trait]
    impl Agent for MockAgent {
        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Ok(Message::new("assistant", serde_json::json!("response")))
        }

        fn name(&self) -> &str {
            "mock"
        }
    }

    fn create_test_optimizer() -> PromptOptimizer {
        let template = "You are a {role}. {instruction}";
        let mut variations = HashMap::new();
        variations.insert("role".to_string(), vec!["assistant".to_string(), "expert".to_string()]);
        variations.insert("instruction".to_string(), vec!["Be brief.".to_string(), "Be detailed.".to_string()]);

        let factory = Box::new(|prompt: String| -> Arc<dyn Agent> {
            Arc::new(MockAgent { _prompt: prompt })
        });

        PromptOptimizer::new(
            template,
            variations,
            factory,
            vec!["accuracy".to_string()],
            None,
        )
    }

    #[test]
    fn test_fill_template() {
        let optimizer = create_test_optimizer();
        let mut config = HashMap::new();
        config.insert("role".to_string(), "assistant".to_string());
        config.insert("instruction".to_string(), "Be brief.".to_string());

        let prompt = optimizer.fill_template(&config);
        assert_eq!(prompt, "You are a assistant. Be brief.");
    }

    #[test]
    fn test_generate_all_configs() {
        let optimizer = create_test_optimizer();
        let configs = optimizer.generate_all_configs();

        // 2 roles × 2 instructions = 4 configs
        assert_eq!(configs.len(), 4);

        // Check all combinations are present
        let mut found_combinations = std::collections::HashSet::new();
        for config in &configs {
            let key = format!("{}:{}", config.get("role").unwrap(), config.get("instruction").unwrap());
            found_combinations.insert(key);
        }

        assert_eq!(found_combinations.len(), 4);
    }

    #[test]
    fn test_sample_config() {
        let optimizer = create_test_optimizer();
        let config = optimizer.sample_config();

        // Should have both keys
        assert!(config.contains_key("role"));
        assert!(config.contains_key("instruction"));

        // Values should be from variations
        let role = config.get("role").unwrap();
        assert!(role == "assistant" || role == "expert");
    }

    #[tokio::test]
    async fn test_optimize_grid() {
        let mut optimizer = create_test_optimizer();
        let test_cases = vec![
            {
                let mut tc = HashMap::new();
                tc.insert("input".to_string(), serde_json::json!("test"));
                tc
            }
        ];

        let result = optimizer.optimize_grid(test_cases).await.unwrap();

        assert_eq!(result.n_evaluated, 4); // 2x2 grid
        assert_eq!(result.strategy, "grid");
        assert_eq!(result.history.len(), 4);
        assert!(!result.best_prompt.is_empty());
    }

    #[tokio::test]
    async fn test_optimize_random() {
        let mut optimizer = create_test_optimizer();
        let test_cases = vec![
            {
                let mut tc = HashMap::new();
                tc.insert("input".to_string(), serde_json::json!("test"));
                tc
            }
        ];

        let result = optimizer.optimize_random(test_cases, 10).await.unwrap();

        assert_eq!(result.n_evaluated, 10);
        assert_eq!(result.strategy, "random");
        assert_eq!(result.history.len(), 10);
        assert!(!result.best_prompt.is_empty());
    }

    #[tokio::test]
    async fn test_optimize_genetic() {
        let mut optimizer = create_test_optimizer();
        let test_cases = vec![
            {
                let mut tc = HashMap::new();
                tc.insert("input".to_string(), serde_json::json!("test"));
                tc
            }
        ];

        let result = optimizer.optimize_genetic(test_cases, 4, 2, 0.2).await.unwrap();

        assert_eq!(result.strategy, "genetic");
        // Initial population (4) + 2 generations × 4 population = 12 total evaluations
        assert_eq!(result.n_evaluated, 12);
        assert!(!result.best_prompt.is_empty());
    }

    #[tokio::test]
    async fn test_optimize_with_strategy() {
        let mut optimizer = create_test_optimizer();
        let test_cases = vec![
            {
                let mut tc = HashMap::new();
                tc.insert("input".to_string(), serde_json::json!("test"));
                tc
            }
        ];

        let options = HashMap::new();
        let result = optimizer.optimize(test_cases, OptimizationStrategy::Grid, options).await.unwrap();

        assert_eq!(result.strategy, "grid");
        assert_eq!(result.n_evaluated, 4);
    }

    #[test]
    fn test_set_maximize() {
        let mut optimizer = create_test_optimizer();
        assert!(optimizer.maximize);

        optimizer.set_maximize(false);
        assert!(!optimizer.maximize);
    }

    #[test]
    fn test_get_objective_score() {
        let optimizer = create_test_optimizer();
        let mut scores = HashMap::new();
        scores.insert("accuracy".to_string(), 0.8);

        let score = optimizer.get_objective_score(&scores);
        assert!((score - 0.8).abs() < 0.001);

        // Test minimization
        let mut optimizer = create_test_optimizer();
        optimizer.set_maximize(false);
        let score = optimizer.get_objective_score(&scores);
        assert!((score + 0.8).abs() < 0.001);
    }

    #[test]
    fn test_result_duration_seconds() {
        let result = PromptOptimizationResult {
            best_prompt: "test".to_string(),
            best_config: HashMap::new(),
            best_scores: HashMap::new(),
            history: Vec::new(),
            n_evaluated: 0,
            strategy: "grid".to_string(),
            start_time: 1000,
            end_time: 3500,
        };

        assert!((result.duration_seconds() - 2.5).abs() < 0.001);
    }

    #[test]
    fn test_result_to_dict() {
        let result = PromptOptimizationResult {
            best_prompt: "test prompt".to_string(),
            best_config: HashMap::new(),
            best_scores: HashMap::new(),
            history: Vec::new(),
            n_evaluated: 10,
            strategy: "random".to_string(),
            start_time: 1000,
            end_time: 2000,
        };

        let dict = result.to_dict();
        assert_eq!(dict.get("best_prompt").unwrap().as_str().unwrap(), "test prompt");
        assert_eq!(dict.get("n_evaluated").unwrap().as_u64().unwrap(), 10);
        assert_eq!(dict.get("strategy").unwrap().as_str().unwrap(), "random");
    }

    #[test]
    fn test_cartesian_product() {
        let optimizer = create_test_optimizer();
        let keys = vec!["a".to_string(), "b".to_string()];
        let values = vec![
            vec!["1".to_string(), "2".to_string()],
            vec!["x".to_string(), "y".to_string()],
        ];

        let configs = optimizer.cartesian_product(&keys, &values, 0, HashMap::new());
        assert_eq!(configs.len(), 4);

        // Verify all combinations present
        let combos: Vec<String> = configs.iter()
            .map(|c| format!("{},{}", c.get("a").unwrap(), c.get("b").unwrap()))
            .collect();
        assert!(combos.contains(&"1,x".to_string()));
        assert!(combos.contains(&"1,y".to_string()));
        assert!(combos.contains(&"2,x".to_string()));
        assert!(combos.contains(&"2,y".to_string()));
    }
}
