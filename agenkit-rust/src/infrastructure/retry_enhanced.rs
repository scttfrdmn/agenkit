// Enhanced retry logic with:
// - Multiple jitter types (Full, Equal, Decorrelated)
// - Per-error-type retry strategies
// - Budget awareness (cost and count limits)
// - Backpressure detection
// - Detailed metrics

use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use rand::Rng;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;

/// Jitter types for retry backoff.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum JitterType {
    None,
    Full,
    Equal,
    Decorrelated,
}

/// Error classification for retry strategies.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ErrorClass {
    Transient,
    RateLimit,
    Timeout,
    ServerError,
    ClientError,
    Unknown,
}

impl ErrorClass {
    pub fn as_str(&self) -> &str {
        match self {
            ErrorClass::Transient => "transient",
            ErrorClass::RateLimit => "rate_limit",
            ErrorClass::Timeout => "timeout",
            ErrorClass::ServerError => "server_error",
            ErrorClass::ClientError => "client_error",
            ErrorClass::Unknown => "unknown",
        }
    }
}

/// Retry strategy for specific error class.
#[derive(Debug, Clone)]
pub struct ErrorStrategy {
    pub error_class: ErrorClass,
    pub max_attempts: usize,
    pub initial_backoff: Duration,
    pub max_backoff: Duration,
    pub backoff_multiplier: f64,
    pub should_retry: bool,
}

/// Retry budget to limit costs.
#[derive(Debug, Clone)]
pub struct RetryBudget {
    pub max_cost: f64,
    pub current_cost: f64,
    pub max_retries_per_hour: u64,
    pub retry_count: u64,
    pub window_start: Instant,
}

/// Enhanced retry configuration.
#[derive(Debug, Clone)]
pub struct EnhancedRetryConfig {
    // Basic retry settings
    pub max_attempts: usize,
    pub initial_backoff: Duration,
    pub max_backoff: Duration,
    pub backoff_multiplier: f64,

    // Jitter settings
    pub jitter_type: JitterType,
    pub jitter_min_ratio: f64,

    // Error-specific strategies
    pub error_strategies: HashMap<ErrorClass, ErrorStrategy>,

    // Budget settings
    pub enable_budget: bool,
    pub max_cost_per_hour: f64,
    pub max_retries_per_hour: u64,

    // Backpressure detection
    pub enable_backpressure: bool,
    pub backpressure_threshold: f64,
    pub backpressure_window: usize,
}

impl Default for EnhancedRetryConfig {
    fn default() -> Self {
        let mut error_strategies = HashMap::new();

        error_strategies.insert(
            ErrorClass::Transient,
            ErrorStrategy {
                error_class: ErrorClass::Transient,
                max_attempts: 5,
                initial_backoff: Duration::from_millis(100),
                max_backoff: Duration::from_secs(5),
                backoff_multiplier: 2.0,
                should_retry: true,
            },
        );

        error_strategies.insert(
            ErrorClass::RateLimit,
            ErrorStrategy {
                error_class: ErrorClass::RateLimit,
                max_attempts: 10,
                initial_backoff: Duration::from_secs(60),
                max_backoff: Duration::from_secs(300),
                backoff_multiplier: 1.5,
                should_retry: true,
            },
        );

        error_strategies.insert(
            ErrorClass::Timeout,
            ErrorStrategy {
                error_class: ErrorClass::Timeout,
                max_attempts: 3,
                initial_backoff: Duration::from_secs(2),
                max_backoff: Duration::from_secs(30),
                backoff_multiplier: 2.0,
                should_retry: true,
            },
        );

        error_strategies.insert(
            ErrorClass::ServerError,
            ErrorStrategy {
                error_class: ErrorClass::ServerError,
                max_attempts: 3,
                initial_backoff: Duration::from_secs(5),
                max_backoff: Duration::from_secs(60),
                backoff_multiplier: 2.0,
                should_retry: true,
            },
        );

        error_strategies.insert(
            ErrorClass::ClientError,
            ErrorStrategy {
                error_class: ErrorClass::ClientError,
                max_attempts: 1,
                initial_backoff: Duration::from_secs(0),
                max_backoff: Duration::from_secs(0),
                backoff_multiplier: 1.0,
                should_retry: false,
            },
        );

        Self {
            max_attempts: 3,
            initial_backoff: Duration::from_secs(1),
            max_backoff: Duration::from_secs(30),
            backoff_multiplier: 2.0,
            jitter_type: JitterType::Full,
            jitter_min_ratio: 0.5,
            error_strategies,
            enable_budget: false,
            max_cost_per_hour: 100.0,
            max_retries_per_hour: 1000,
            enable_backpressure: true,
            backpressure_threshold: 0.5,
            backpressure_window: 100,
        }
    }
}

/// Enhanced retry metrics.
#[derive(Debug, Clone, Default)]
pub struct EnhancedRetryMetrics {
    pub total_attempts: u64,
    pub successful_first_attempt: u64,
    pub successful_on_retry: u64,
    pub failed_after_retries: u64,
    pub total_retries: u64,
    pub total_jitter_added: f64,
    pub budget_exceeded_count: u64,
    pub backpressure_detected: u64,
    pub error_class_counts: HashMap<ErrorClass, u64>,
    pub recent_results: Vec<bool>,
}

/// Enhanced retry decorator wraps an agent with enhanced retry logic.
pub struct EnhancedRetryDecorator {
    agent: Arc<dyn Agent>,
    config: EnhancedRetryConfig,
    metrics: Arc<RwLock<EnhancedRetryMetrics>>,
    budget: Arc<RwLock<RetryBudget>>,
}

impl EnhancedRetryDecorator {
    /// Create a new enhanced retry decorator.
    pub fn new(agent: Arc<dyn Agent>, config: EnhancedRetryConfig) -> Self {
        let budget = RetryBudget {
            max_cost: config.max_cost_per_hour,
            current_cost: 0.0,
            max_retries_per_hour: config.max_retries_per_hour,
            retry_count: 0,
            window_start: Instant::now(),
        };

        Self {
            agent,
            config,
            metrics: Arc::new(RwLock::new(EnhancedRetryMetrics::default())),
            budget: Arc::new(RwLock::new(budget)),
        }
    }

    fn classify_error(&self, error: &AgentError) -> ErrorClass {
        let err_str = error.to_string().to_lowercase();

        if err_str.contains("rate limit") || err_str.contains("429") {
            ErrorClass::RateLimit
        } else if err_str.contains("timeout") || err_str.contains("timed out") {
            ErrorClass::Timeout
        } else if err_str.contains("500") || err_str.contains("502") || err_str.contains("503") {
            ErrorClass::ServerError
        } else if err_str.contains("400")
            || err_str.contains("401")
            || err_str.contains("403")
            || err_str.contains("404")
        {
            ErrorClass::ClientError
        } else {
            ErrorClass::Unknown
        }
    }

    fn get_strategy(&self, error_class: ErrorClass) -> ErrorStrategy {
        self.config
            .error_strategies
            .get(&error_class)
            .cloned()
            .unwrap_or_else(|| ErrorStrategy {
                error_class,
                max_attempts: self.config.max_attempts,
                initial_backoff: self.config.initial_backoff,
                max_backoff: self.config.max_backoff,
                backoff_multiplier: self.config.backoff_multiplier,
                should_retry: true,
            })
    }

    fn calculate_backoff(&self, base_backoff: Duration, attempt: usize) -> Duration {
        let base_ms = base_backoff.as_millis() as f64;
        let mut rng = rand::thread_rng();

        let jittered_ms = match self.config.jitter_type {
            JitterType::None => base_ms,
            JitterType::Full => {
                let jittered = rng.gen::<f64>() * base_ms;
                jittered
            }
            JitterType::Equal => {
                let min_backoff = base_ms * self.config.jitter_min_ratio;
                min_backoff + rng.gen::<f64>() * (base_ms - min_backoff)
            }
            JitterType::Decorrelated => {
                if attempt == 1 {
                    base_ms
                } else {
                    let previous = self.calculate_backoff(base_backoff, attempt - 1);
                    let previous_ms = previous.as_millis() as f64;
                    let jittered = rng.gen::<f64>() * previous_ms * 3.0 + base_ms;
                    let max_ms = self.config.max_backoff.as_millis() as f64;
                    if jittered > max_ms {
                        max_ms
                    } else {
                        jittered
                    }
                }
            }
        };

        Duration::from_millis(jittered_ms as u64)
    }

    async fn check_budget(&self, _cost: f64) -> bool {
        if !self.config.enable_budget {
            return true;
        }

        let mut budget = self.budget.write().await;

        // Reset window if hour has passed
        if budget.window_start.elapsed() > Duration::from_secs(3600) {
            budget.current_cost = 0.0;
            budget.retry_count = 0;
            budget.window_start = Instant::now();
        }

        // Check cost budget
        if budget.current_cost + _cost > budget.max_cost {
            let mut metrics = self.metrics.write().await;
            metrics.budget_exceeded_count += 1;
            return false;
        }

        // Check retry count budget
        if budget.retry_count >= budget.max_retries_per_hour {
            let mut metrics = self.metrics.write().await;
            metrics.budget_exceeded_count += 1;
            return false;
        }

        true
    }

    async fn check_backpressure(&self) -> bool {
        if !self.config.enable_backpressure {
            return false;
        }

        let metrics = self.metrics.read().await;
        if metrics.recent_results.len() < self.config.backpressure_window {
            return false;
        }

        // Calculate failure rate
        let failures = metrics.recent_results.iter().filter(|&&success| !success).count();
        let failure_rate = failures as f64 / metrics.recent_results.len() as f64;

        failure_rate > self.config.backpressure_threshold
    }

    /// Get current metrics.
    pub async fn get_metrics(&self) -> EnhancedRetryMetrics {
        self.metrics.read().await.clone()
    }
}

#[async_trait]
impl Agent for EnhancedRetryDecorator {
    fn name(&self) -> String {
        self.agent.name()
    }

    fn capabilities(&self) -> Vec<String> {
        self.agent.capabilities()
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let mut last_error: Option<AgentError> = None;
        let mut error_class = ErrorClass::Unknown;
        let mut strategy = self.get_strategy(error_class);

        for attempt in 1..=self.config.max_attempts {
            {
                let mut metrics = self.metrics.write().await;
                metrics.total_attempts += 1;
            }

            // Check budget before attempt
            if self.config.enable_budget {
                if !self.check_budget(0.0).await {
                    return Err(AgentError::ExecutionError(
                        "Retry budget exceeded".to_string(),
                    ));
                }
            }

            // Check backpressure
            if self.check_backpressure().await {
                tokio::time::sleep(Duration::from_secs(5)).await;
            }

            // Process message
            match self.agent.process(message.clone()).await {
                Ok(response) => {
                    // Success
                    let mut metrics = self.metrics.write().await;
                    if attempt == 1 {
                        metrics.successful_first_attempt += 1;
                    } else {
                        metrics.successful_on_retry += 1;
                    }
                    metrics.recent_results.push(true);
                    if metrics.recent_results.len() > self.config.backpressure_window {
                        metrics.recent_results.remove(0);
                    }

                    return Ok(response);
                }
                Err(error) => {
                    // Failure
                    last_error = Some(error.clone());

                    // Track failure for backpressure
                    {
                        let mut metrics = self.metrics.write().await;
                        metrics.recent_results.push(false);
                        if metrics.recent_results.len() > self.config.backpressure_window {
                            metrics.recent_results.remove(0);
                        }
                    }

                    // Classify error
                    error_class = self.classify_error(&error);
                    {
                        let mut metrics = self.metrics.write().await;
                        *metrics.error_class_counts.entry(error_class).or_insert(0) += 1;
                    }

                    // Get strategy for error class
                    strategy = self.get_strategy(error_class);

                    // Check if should retry
                    if !strategy.should_retry {
                        let mut metrics = self.metrics.write().await;
                        metrics.failed_after_retries += 1;
                        return Err(AgentError::ExecutionError(format!(
                            "Non-retryable error ({}): {}",
                            error_class.as_str(),
                            error
                        )));
                    }

                    // Check if exceeded max attempts for this error class
                    if attempt >= strategy.max_attempts {
                        break;
                    }

                    // Track retry
                    {
                        let mut metrics = self.metrics.write().await;
                        metrics.total_retries += 1;
                    }

                    {
                        let mut budget = self.budget.write().await;
                        budget.retry_count += 1;
                    }

                    // Calculate backoff with jitter
                    let base_backoff_ms =
                        strategy.initial_backoff.as_millis() as f64 * strategy.backoff_multiplier.powi(attempt as i32 - 1);
                    let mut base_backoff = Duration::from_millis(base_backoff_ms as u64);
                    if base_backoff > strategy.max_backoff {
                        base_backoff = strategy.max_backoff;
                    }
                    let backoff = self.calculate_backoff(base_backoff, attempt);

                    // Sleep with backoff
                    tokio::time::sleep(backoff).await;
                }
            }
        }

        // All attempts failed
        {
            let mut metrics = self.metrics.write().await;
            metrics.failed_after_retries += 1;
        }

        Err(AgentError::ExecutionError(format!(
            "Max retry attempts ({}) exceeded for {}: {}",
            strategy.max_attempts,
            error_class.as_str(),
            last_error.unwrap_or_else(|| AgentError::ExecutionError("Unknown error".to_string()))
        )))
    }
}
