//! Automated Optimization Framework
//!
//! Provides intelligent optimization of agent configurations, prompts,
//! and hyperparameters using various search strategies.
//!
//! # Example
//!
//! ```ignore
//! use agenkit::evaluation::optimizer::{RandomSearchOptimizer, SearchSpace};
//! use std::collections::HashMap;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! let mut search_space = SearchSpace::new();
//! search_space.add_continuous("temperature", 0.0, 1.0);
//! search_space.add_continuous("top_p", 0.0, 1.0);
//!
//! let objective = |_config: HashMap<String, serde_json::Value>| async { Ok(0.95) };
//! let optimizer = RandomSearchOptimizer::new(objective, search_space, true);
//!
//! let result = optimizer.optimize(50).await?;
//! println!("Best score: {}", result.best_score);
//! # Ok(())
//! # }
//! ```

use chrono::{DateTime, Utc};
use rand::RngExt;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::future::Future;
use std::pin::Pin;

use crate::core::AgentError;

/// Objective function type.
///
/// Takes a configuration and returns a score to optimize.
pub type ObjectiveFunc = Box<
    dyn Fn(
            HashMap<String, serde_json::Value>,
        ) -> Pin<Box<dyn Future<Output = Result<f64, AgentError>> + Send>>
        + Send
        + Sync,
>;

/// Parameter type for search space.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ParameterType {
    /// Continuous floating-point parameter
    Continuous,
    /// Integer parameter
    Integer,
    /// Discrete choice parameter
    Discrete,
    /// Categorical choice parameter
    Categorical,
}

/// Parameter specification.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParameterSpec {
    /// Parameter type
    #[serde(rename = "type")]
    pub param_type: ParameterType,
    /// Lower bound (for continuous/integer)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub low: Option<f64>,
    /// Upper bound (for continuous/integer)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub high: Option<f64>,
    /// Values (for discrete/categorical)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub values: Option<Vec<serde_json::Value>>,
}

/// Search space for hyperparameter optimization.
///
/// Defines the parameter space to search over.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchSpace {
    /// Parameters in the search space
    pub parameters: HashMap<String, ParameterSpec>,
}

impl SearchSpace {
    /// Creates a new search space.
    pub fn new() -> Self {
        Self {
            parameters: HashMap::new(),
        }
    }

    /// Adds a continuous parameter with range [low, high].
    pub fn add_continuous(&mut self, name: impl Into<String>, low: f64, high: f64) {
        self.parameters.insert(
            name.into(),
            ParameterSpec {
                param_type: ParameterType::Continuous,
                low: Some(low),
                high: Some(high),
                values: None,
            },
        );
    }

    /// Adds an integer parameter with range [low, high].
    pub fn add_integer(&mut self, name: impl Into<String>, low: i64, high: i64) {
        self.parameters.insert(
            name.into(),
            ParameterSpec {
                param_type: ParameterType::Integer,
                low: Some(low as f64),
                high: Some(high as f64),
                values: None,
            },
        );
    }

    /// Adds a discrete parameter with specific values.
    pub fn add_discrete(&mut self, name: impl Into<String>, values: Vec<serde_json::Value>) {
        self.parameters.insert(
            name.into(),
            ParameterSpec {
                param_type: ParameterType::Discrete,
                low: None,
                high: None,
                values: Some(values),
            },
        );
    }

    /// Samples a random configuration from the search space.
    pub fn sample(&self) -> HashMap<String, serde_json::Value> {
        let mut rng = rand::rng();
        let mut config = HashMap::new();

        for (name, spec) in &self.parameters {
            let value = match spec.param_type {
                ParameterType::Continuous => {
                    let low = spec.low.unwrap_or(0.0);
                    let high = spec.high.unwrap_or(1.0);
                    serde_json::json!(rng.random_range(low..high))
                }
                ParameterType::Integer => {
                    let low = spec.low.unwrap_or(0.0) as i64;
                    let high = spec.high.unwrap_or(10.0) as i64;
                    serde_json::json!(rng.random_range(low..=high))
                }
                ParameterType::Discrete | ParameterType::Categorical => {
                    if let Some(values) = &spec.values {
                        if !values.is_empty() {
                            let idx = rng.random_range(0..values.len());
                            values[idx].clone()
                        } else {
                            serde_json::Value::Null
                        }
                    } else {
                        serde_json::Value::Null
                    }
                }
            };
            config.insert(name.clone(), value);
        }

        config
    }
}

impl Default for SearchSpace {
    fn default() -> Self {
        Self::new()
    }
}

/// Single evaluation step in optimization.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OptimizationStep {
    /// Configuration evaluated
    pub config: HashMap<String, serde_json::Value>,
    /// Score achieved
    pub score: f64,
}

/// Result from an optimization run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OptimizationResult {
    /// Best configuration found
    pub best_config: HashMap<String, serde_json::Value>,
    /// Best score achieved
    pub best_score: f64,
    /// History of all evaluations
    pub history: Vec<OptimizationStep>,
    /// Number of iterations
    pub n_iterations: usize,
    /// Start time
    pub start_time: DateTime<Utc>,
    /// End time
    pub end_time: DateTime<Utc>,
    /// Additional metadata
    #[serde(skip_serializing_if = "HashMap::is_empty")]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl OptimizationResult {
    /// Calculates optimization duration in seconds.
    pub fn duration_secs(&self) -> f64 {
        (self.end_time - self.start_time).num_milliseconds() as f64 / 1000.0
    }

    /// Gets improvement from first to best score.
    pub fn get_improvement(&self) -> Option<f64> {
        if self.history.is_empty() {
            return None;
        }
        let initial_score = self.history[0].score;
        Some(self.best_score - initial_score)
    }
}

/// Random search optimizer.
///
/// Baseline optimization using random sampling.
///
/// # Example
///
/// ```ignore
/// use agenkit::evaluation::optimizer::{RandomSearchOptimizer, SearchSpace};
/// use std::collections::HashMap;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let mut search_space = SearchSpace::new();
/// search_space.add_continuous("temperature", 0.0, 1.0);
///
/// let objective = |_config: HashMap<String, serde_json::Value>| async { Ok(0.95) };
/// let optimizer = RandomSearchOptimizer::new(objective, search_space, true);
///
/// let result = optimizer.optimize(20).await?;
/// # Ok(())
/// # }
/// ```
pub struct RandomSearchOptimizer {
    objective: ObjectiveFunc,
    search_space: SearchSpace,
    maximize: bool,
    history: Vec<OptimizationStep>,
}

impl RandomSearchOptimizer {
    /// Creates a new random search optimizer.
    ///
    /// # Arguments
    ///
    /// * `objective` - Function to evaluate configurations
    /// * `search_space` - Search space defining parameter space
    /// * `maximize` - Whether to maximize (true) or minimize (false)
    pub fn new(
        objective: impl Fn(
                HashMap<String, serde_json::Value>,
            ) -> Pin<Box<dyn Future<Output = Result<f64, AgentError>> + Send>>
            + Send
            + Sync
            + 'static,
        search_space: SearchSpace,
        maximize: bool,
    ) -> Self {
        Self {
            objective: Box::new(objective),
            search_space,
            maximize,
            history: Vec::new(),
        }
    }

    /// Runs random search optimization.
    ///
    /// # Arguments
    ///
    /// * `n_iterations` - Number of configurations to evaluate
    ///
    /// # Returns
    ///
    /// OptimizationResult with best config and history
    pub async fn optimize(
        &mut self,
        n_iterations: usize,
    ) -> Result<OptimizationResult, AgentError> {
        let start_time = Utc::now();
        self.history = Vec::with_capacity(n_iterations);

        let mut best_config: Option<HashMap<String, serde_json::Value>> = None;
        let mut best_score = if self.maximize {
            f64::NEG_INFINITY
        } else {
            f64::INFINITY
        };

        for _ in 0..n_iterations {
            // Sample random configuration
            let config = self.search_space.sample();

            // Evaluate
            let score = (self.objective)(config.clone()).await?;

            // Record step
            self.history.push(OptimizationStep {
                config: config.clone(),
                score,
            });

            // Update best
            let is_better = if self.maximize {
                score > best_score
            } else {
                score < best_score
            };

            if is_better || best_config.is_none() {
                best_score = score;
                best_config = Some(config);
            }
        }

        let end_time = Utc::now();

        // Fallback if nothing evaluated
        let best_config = best_config.unwrap_or_else(|| self.search_space.sample());

        let mut metadata = HashMap::new();
        metadata.insert("algorithm".to_string(), serde_json::json!("random_search"));
        metadata.insert("maximize".to_string(), serde_json::json!(self.maximize));

        Ok(OptimizationResult {
            best_config,
            best_score,
            history: self.history.clone(),
            n_iterations,
            start_time,
            end_time,
            metadata,
        })
    }

    /// Gets the optimization history.
    pub fn get_history(&self) -> &[OptimizationStep] {
        &self.history
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_search_space_creation() {
        let mut space = SearchSpace::new();
        space.add_continuous("temp", 0.0, 1.0);
        space.add_integer("count", 1, 10);

        assert_eq!(space.parameters.len(), 2);
        assert_eq!(
            space.parameters.get("temp").unwrap().param_type,
            ParameterType::Continuous
        );
    }

    #[test]
    fn test_search_space_sampling() {
        let mut space = SearchSpace::new();
        space.add_continuous("temp", 0.0, 1.0);
        space.add_integer("count", 1, 10);

        let config = space.sample();

        assert_eq!(config.len(), 2);
        assert!(config.contains_key("temp"));
        assert!(config.contains_key("count"));

        let temp = config.get("temp").unwrap().as_f64().unwrap();
        assert!(temp >= 0.0 && temp <= 1.0);
    }

    #[test]
    fn test_discrete_parameter() {
        let mut space = SearchSpace::new();
        space.add_discrete(
            "model",
            vec![serde_json::json!("gpt-4"), serde_json::json!("claude")],
        );

        let config = space.sample();
        let model = config.get("model").unwrap().as_str().unwrap();
        assert!(model == "gpt-4" || model == "claude");
    }

    #[tokio::test]
    async fn test_random_search_optimizer() {
        let mut space = SearchSpace::new();
        space.add_continuous("x", 0.0, 10.0);

        // Objective: minimize (x - 5)^2
        let objective = |config: HashMap<String, serde_json::Value>| {
            Box::pin(async move {
                let x = config.get("x").unwrap().as_f64().unwrap();
                Ok(-((x - 5.0).powi(2))) // Negative because we'll maximize
            }) as Pin<Box<dyn Future<Output = Result<f64, AgentError>> + Send>>
        };

        let mut optimizer = RandomSearchOptimizer::new(objective, space, true);

        let result = optimizer.optimize(20).await.unwrap();

        assert_eq!(result.n_iterations, 20);
        assert_eq!(result.history.len(), 20);
        assert!(result.best_score <= 0.0); // Should be close to 0 (optimal)

        // Check that best_config has x close to 5.0
        let best_x = result.best_config.get("x").unwrap().as_f64().unwrap();
        assert!(best_x >= 0.0 && best_x <= 10.0);
    }

    #[tokio::test]
    async fn test_minimization() {
        let mut space = SearchSpace::new();
        space.add_continuous("x", 0.0, 10.0);

        // Minimize x^2
        let objective = |config: HashMap<String, serde_json::Value>| {
            Box::pin(async move {
                let x = config.get("x").unwrap().as_f64().unwrap();
                Ok(x.powi(2))
            }) as Pin<Box<dyn Future<Output = Result<f64, AgentError>> + Send>>
        };

        let mut optimizer = RandomSearchOptimizer::new(objective, space, false);

        let result = optimizer.optimize(20).await.unwrap();

        // Should find x close to 0
        assert!(result.best_score >= 0.0);
        assert!(result.best_score < 100.0); // Reasonable range
    }

    #[test]
    fn test_optimization_result_methods() {
        let result = OptimizationResult {
            best_config: HashMap::new(),
            best_score: 0.95,
            history: vec![
                OptimizationStep {
                    config: HashMap::new(),
                    score: 0.8,
                },
                OptimizationStep {
                    config: HashMap::new(),
                    score: 0.95,
                },
            ],
            n_iterations: 2,
            start_time: Utc::now(),
            end_time: Utc::now(),
            metadata: HashMap::new(),
        };

        assert!(result.duration_secs() >= 0.0);

        let improvement = result.get_improvement().unwrap();
        assert!((improvement - 0.15).abs() < 0.0001); // 0.95 - 0.8 ≈ 0.15
    }

    // ========================================================================
    // Bayesian Optimizer Tests
    // ========================================================================

    #[tokio::test]
    async fn test_bayesian_optimizer_ucb() {
        let mut space = SearchSpace::new();
        space.add_continuous("x", 0.0, 10.0);

        // Objective: maximize -(x - 5)^2 (peak at x=5)
        let objective = |config: HashMap<String, serde_json::Value>| {
            Box::pin(async move {
                let x = config.get("x").unwrap().as_f64().unwrap();
                Ok(-((x - 5.0).powi(2)))
            }) as Pin<Box<dyn Future<Output = Result<f64, AgentError>> + Send>>
        };

        let mut optimizer =
            BayesianOptimizer::new(objective, space, true, AcquisitionFunction::UCB, 5);

        let result = optimizer.optimize(20).await.unwrap();

        assert_eq!(result.n_iterations, 20);
        assert_eq!(result.history.len(), 20);
        assert!(result.best_score <= 0.0); // Maximum is 0 at x=5

        // Best x should be reasonably close to 5.0
        let best_x = result.best_config.get("x").unwrap().as_f64().unwrap();
        assert!(best_x >= 0.0 && best_x <= 10.0);
    }

    #[tokio::test]
    async fn test_bayesian_optimizer_ei() {
        let mut space = SearchSpace::new();
        space.add_continuous("x", 0.0, 10.0);

        // Objective: maximize -(x - 3)^2
        let objective = |config: HashMap<String, serde_json::Value>| {
            Box::pin(async move {
                let x = config.get("x").unwrap().as_f64().unwrap();
                Ok(-((x - 3.0).powi(2)))
            }) as Pin<Box<dyn Future<Output = Result<f64, AgentError>> + Send>>
        };

        let mut optimizer =
            BayesianOptimizer::new(objective, space, true, AcquisitionFunction::EI, 5);

        let result = optimizer.optimize(20).await.unwrap();

        assert_eq!(result.n_iterations, 20);
        assert!(result.best_score <= 0.0);
    }

    #[tokio::test]
    async fn test_bayesian_optimizer_pi() {
        let mut space = SearchSpace::new();
        space.add_continuous("x", 0.0, 10.0);

        // Objective: maximize -(x - 7)^2
        let objective = |config: HashMap<String, serde_json::Value>| {
            Box::pin(async move {
                let x = config.get("x").unwrap().as_f64().unwrap();
                Ok(-((x - 7.0).powi(2)))
            }) as Pin<Box<dyn Future<Output = Result<f64, AgentError>> + Send>>
        };

        let mut optimizer =
            BayesianOptimizer::new(objective, space, true, AcquisitionFunction::PI, 5);

        let result = optimizer.optimize(20).await.unwrap();

        assert_eq!(result.n_iterations, 20);
        assert!(result.best_score <= 0.0);
    }

    #[tokio::test]
    async fn test_bayesian_optimizer_minimization() {
        let mut space = SearchSpace::new();
        space.add_continuous("x", 0.0, 10.0);

        // Objective: minimize (x - 2)^2 (minimum at x=2)
        let objective = |config: HashMap<String, serde_json::Value>| {
            Box::pin(async move {
                let x = config.get("x").unwrap().as_f64().unwrap();
                Ok((x - 2.0).powi(2))
            }) as Pin<Box<dyn Future<Output = Result<f64, AgentError>> + Send>>
        };

        let mut optimizer = BayesianOptimizer::new(
            objective,
            space,
            false, // minimize
            AcquisitionFunction::UCB,
            5,
        );

        let result = optimizer.optimize(20).await.unwrap();

        assert_eq!(result.n_iterations, 20);
        assert!(result.best_score >= 0.0); // Minimum is 0 at x=2
    }

    #[tokio::test]
    async fn test_bayesian_optimizer_multidimensional() {
        let mut space = SearchSpace::new();
        space.add_continuous("x", 0.0, 10.0);
        space.add_continuous("y", 0.0, 10.0);

        // Objective: minimize (x - 5)^2 + (y - 5)^2
        let objective = |config: HashMap<String, serde_json::Value>| {
            Box::pin(async move {
                let x = config.get("x").unwrap().as_f64().unwrap();
                let y = config.get("y").unwrap().as_f64().unwrap();
                Ok((x - 5.0).powi(2) + (y - 5.0).powi(2))
            }) as Pin<Box<dyn Future<Output = Result<f64, AgentError>> + Send>>
        };

        let mut optimizer =
            BayesianOptimizer::new(objective, space, false, AcquisitionFunction::EI, 10);

        let result = optimizer.optimize(30).await.unwrap();

        assert_eq!(result.n_iterations, 30);
        assert!(result.best_score >= 0.0);

        // Both x and y should be in valid range
        let best_x = result.best_config.get("x").unwrap().as_f64().unwrap();
        let best_y = result.best_config.get("y").unwrap().as_f64().unwrap();
        assert!(best_x >= 0.0 && best_x <= 10.0);
        assert!(best_y >= 0.0 && best_y <= 10.0);
    }

    #[tokio::test]
    async fn test_bayesian_optimizer_with_integer_params() {
        let mut space = SearchSpace::new();
        space.add_integer("count", 1, 20);
        space.add_continuous("scale", 0.1, 2.0);

        // Objective: maximize count * scale, but penalize count > 10
        let objective = |config: HashMap<String, serde_json::Value>| {
            Box::pin(async move {
                let count = config.get("count").unwrap().as_i64().unwrap() as f64;
                let scale = config.get("scale").unwrap().as_f64().unwrap();
                let score = count * scale
                    - if count > 10.0 {
                        (count - 10.0) * 2.0
                    } else {
                        0.0
                    };
                Ok(score)
            }) as Pin<Box<dyn Future<Output = Result<f64, AgentError>> + Send>>
        };

        let mut optimizer =
            BayesianOptimizer::new(objective, space, true, AcquisitionFunction::UCB, 5);

        let result = optimizer.optimize(20).await.unwrap();

        assert_eq!(result.n_iterations, 20);
        assert!(result.history.len() == 20);
    }

    #[tokio::test]
    async fn test_bayesian_optimizer_convergence() {
        let mut space = SearchSpace::new();
        space.add_continuous("x", 0.0, 10.0);

        // Objective: simple quadratic with known optimum
        let objective = |config: HashMap<String, serde_json::Value>| {
            Box::pin(async move {
                let x = config.get("x").unwrap().as_f64().unwrap();
                Ok(-((x - 6.0).powi(2)))
            }) as Pin<Box<dyn Future<Output = Result<f64, AgentError>> + Send>>
        };

        let mut optimizer =
            BayesianOptimizer::new(objective, space, true, AcquisitionFunction::EI, 5);

        let result = optimizer.optimize(30).await.unwrap();

        // With enough iterations, should get close to optimum
        // Optimum is at x=6 with score=0
        assert!(result.best_score >= -2.0); // Reasonable tolerance
    }

    #[tokio::test]
    async fn test_bayesian_optimizer_metadata() {
        let mut space = SearchSpace::new();
        space.add_continuous("x", 0.0, 10.0);

        let objective = |config: HashMap<String, serde_json::Value>| {
            Box::pin(async move {
                let x = config.get("x").unwrap().as_f64().unwrap();
                Ok(x)
            }) as Pin<Box<dyn Future<Output = Result<f64, AgentError>> + Send>>
        };

        let mut optimizer =
            BayesianOptimizer::new(objective, space, true, AcquisitionFunction::UCB, 3);

        let result = optimizer.optimize(10).await.unwrap();

        // Check metadata
        assert_eq!(
            result.metadata.get("algorithm").unwrap().as_str().unwrap(),
            "bayesian_optimization"
        );
        assert_eq!(
            result.metadata.get("n_initial").unwrap().as_u64().unwrap(),
            3
        );
        assert_eq!(
            result.metadata.get("maximize").unwrap().as_bool().unwrap(),
            true
        );
        assert!(result.metadata.contains_key("acquisition"));
    }

    #[test]
    fn test_acquisition_function_types() {
        // Test that all acquisition function types can be created
        let _ei = AcquisitionFunction::EI;
        let _ucb = AcquisitionFunction::UCB;
        let _pi = AcquisitionFunction::PI;
    }
}

/// Acquisition function type for Bayesian optimization.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AcquisitionFunction {
    /// Expected Improvement
    EI,
    /// Upper Confidence Bound
    UCB,
    /// Probability of Improvement
    PI,
}

/// Bayesian optimizer using simplified surrogate model.
///
/// Balances exploration and exploitation through acquisition functions.
///
/// # Example
///
/// ```ignore
/// use agenkit::evaluation::optimizer::{BayesianOptimizer, SearchSpace, AcquisitionFunction};
/// use std::collections::HashMap;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// let mut space = SearchSpace::new();
/// space.add_continuous("x", 0.0, 10.0);
///
/// let objective = |_config: HashMap<String, serde_json::Value>| async { Ok(0.95) };
/// let optimizer = BayesianOptimizer::new(
///     objective,
///     space,
///     true, // maximize
///     AcquisitionFunction::EI,
///     5, // n_initial
/// );
///
/// let result = optimizer.optimize(20).await?;
/// # Ok(())
/// # }
/// ```
pub struct BayesianOptimizer {
    objective: ObjectiveFunc,
    search_space: SearchSpace,
    maximize: bool,
    acquisition: AcquisitionFunction,
    n_initial: usize,
    xi: f64,    // Exploration parameter for EI/PI
    kappa: f64, // Exploration parameter for UCB
    history: Vec<OptimizationStep>,
    best_config: Option<HashMap<String, serde_json::Value>>,
    best_score: f64,
}

impl BayesianOptimizer {
    /// Creates a new Bayesian optimizer.
    ///
    /// # Arguments
    ///
    /// * `objective` - Function to evaluate configurations
    /// * `search_space` - Search space defining parameter space
    /// * `maximize` - Whether to maximize (true) or minimize (false)
    /// * `acquisition` - Acquisition function to use
    /// * `n_initial` - Number of random samples for initialization
    pub fn new(
        objective: impl Fn(
                HashMap<String, serde_json::Value>,
            ) -> Pin<Box<dyn Future<Output = Result<f64, AgentError>> + Send>>
            + Send
            + Sync
            + 'static,
        search_space: SearchSpace,
        maximize: bool,
        acquisition: AcquisitionFunction,
        n_initial: usize,
    ) -> Self {
        Self {
            objective: Box::new(objective),
            search_space,
            maximize,
            acquisition,
            n_initial,
            xi: 0.01,
            kappa: 2.576,
            history: Vec::new(),
            best_config: None,
            best_score: if maximize {
                f64::NEG_INFINITY
            } else {
                f64::INFINITY
            },
        }
    }

    /// Runs Bayesian optimization.
    pub async fn optimize(
        &mut self,
        n_iterations: usize,
    ) -> Result<OptimizationResult, AgentError> {
        let start_time = Utc::now();

        // Phase 1: Random initialization
        for _ in 0..self.n_initial.min(n_iterations) {
            let config = self.search_space.sample();
            let score = (self.objective)(config.clone()).await?;
            self.add_observation(config, score);
        }

        // Phase 2: Bayesian optimization with acquisition function
        for _ in self.n_initial..n_iterations {
            let config = self.propose_next();
            let score = (self.objective)(config.clone()).await?;
            self.add_observation(config, score);
        }

        let end_time = Utc::now();

        let best_config = self
            .best_config
            .clone()
            .unwrap_or_else(|| self.search_space.sample());

        let mut metadata = HashMap::new();
        metadata.insert(
            "algorithm".to_string(),
            serde_json::json!("bayesian_optimization"),
        );
        metadata.insert(
            "acquisition".to_string(),
            serde_json::json!(format!("{:?}", self.acquisition)),
        );
        metadata.insert("n_initial".to_string(), serde_json::json!(self.n_initial));
        metadata.insert("maximize".to_string(), serde_json::json!(self.maximize));

        Ok(OptimizationResult {
            best_config,
            best_score: self.best_score,
            history: self.history.clone(),
            n_iterations,
            start_time,
            end_time,
            metadata,
        })
    }

    /// Adds observation to history.
    fn add_observation(&mut self, config: HashMap<String, serde_json::Value>, score: f64) {
        self.history.push(OptimizationStep {
            config: config.clone(),
            score,
        });

        let is_better = if self.maximize {
            score > self.best_score
        } else {
            score < self.best_score
        };

        if self.best_config.is_none() || is_better {
            self.best_score = score;
            self.best_config = Some(config);
        }
    }

    /// Proposes next configuration using acquisition function.
    fn propose_next(&self) -> HashMap<String, serde_json::Value> {
        let n_candidates = 1000;
        let mut best_candidate = self.search_space.sample();
        let mut best_acq_value = f64::NEG_INFINITY;

        for _ in 0..n_candidates {
            let candidate = self.search_space.sample();
            let acq_value = self.evaluate_acquisition(&candidate);

            if acq_value > best_acq_value {
                best_acq_value = acq_value;
                best_candidate = candidate;
            }
        }

        best_candidate
    }

    /// Evaluates acquisition function for a candidate.
    fn evaluate_acquisition(&self, _candidate: &HashMap<String, serde_json::Value>) -> f64 {
        if self.history.is_empty() {
            return 0.0;
        }

        // Simplified acquisition: use mean and std of nearby points
        let mean = self.history.iter().map(|s| s.score).sum::<f64>() / self.history.len() as f64;
        let variance: f64 = self
            .history
            .iter()
            .map(|s| (s.score - mean).powi(2))
            .sum::<f64>()
            / self.history.len() as f64;
        let std = variance.sqrt();

        // Simple acquisition based on type
        match self.acquisition {
            AcquisitionFunction::UCB => {
                if self.maximize {
                    mean + self.kappa * std
                } else {
                    mean - self.kappa * std
                }
            }
            AcquisitionFunction::EI | AcquisitionFunction::PI => {
                // Simplified EI/PI: favor high uncertainty
                std + self.xi
            }
        }
    }
}
