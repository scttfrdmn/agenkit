// Package infrastructure provides production-grade infrastructure components.
//
// Load balancing for distributing requests across multiple agents with:
//   - Multiple strategies (round-robin, least-connections, weighted, random)
//   - Automatic health checking
//   - Failover support
//   - Real-time backend statistics
//   - Thread-safe for concurrent requests

use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use rand::RngExt;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::RwLock;
use tokio::time;

/// Load balancing strategy.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LoadBalancingStrategy {
    RoundRobin,
    LeastConnections,
    WeightedRoundRobin,
    Random,
}

/// Backend agent with metadata.
pub struct AgentBackend {
    pub agent: Arc<dyn Agent>,
    pub weight: usize,
    pub healthy: bool,
    pub active_connections: usize,
    pub total_requests: u64,
    pub total_failures: u64,
    pub last_health_check: time::Instant,
    pub consecutive_failures: usize,
}

/// Load balancer configuration.
#[derive(Debug, Clone)]
pub struct LoadBalancerConfig {
    pub strategy: LoadBalancingStrategy,
    pub health_check_interval: Duration,
    pub health_check_timeout: Duration,
    pub failure_threshold: usize,
    pub success_threshold: usize,
    pub enable_failover: bool,
}

impl Default for LoadBalancerConfig {
    fn default() -> Self {
        Self {
            strategy: LoadBalancingStrategy::RoundRobin,
            health_check_interval: Duration::from_secs(30),
            health_check_timeout: Duration::from_secs(5),
            failure_threshold: 3,
            success_threshold: 2,
            enable_failover: true,
        }
    }
}

/// Load balancer performance metrics.
#[derive(Debug, Default, Clone)]
pub struct LoadBalancerMetrics {
    pub total_requests: u64,
    pub successful_requests: u64,
    pub failed_requests: u64,
    pub failover_attempts: u64,
    pub backend_health_changes: HashMap<String, u64>,
}

/// Backend statistics.
#[derive(Debug, Clone)]
pub struct BackendStats {
    pub name: String,
    pub healthy: bool,
    pub weight: usize,
    pub active_connections: usize,
    pub total_requests: u64,
    pub total_failures: u64,
}

/// Load balancer distributes requests across multiple agents.
pub struct LoadBalancer {
    name: String,
    backends: Arc<RwLock<Vec<AgentBackend>>>,
    config: LoadBalancerConfig,
    metrics: Arc<RwLock<LoadBalancerMetrics>>,
    current_index: Arc<RwLock<usize>>,
}

impl LoadBalancer {
    /// Create a new load balancer.
    pub fn new(
        agents: Vec<Arc<dyn Agent>>,
        config: LoadBalancerConfig,
        weights: Option<Vec<usize>>,
    ) -> Result<Self, AgentError> {
        if agents.is_empty() {
            return Err(AgentError::ConfigurationError(
                "At least one agent required".to_string(),
            ));
        }

        // Default weights to 1 if not provided
        let final_weights = weights.unwrap_or_else(|| vec![1; agents.len()]);

        if final_weights.len() != agents.len() {
            return Err(AgentError::ConfigurationError(format!(
                "Weights length ({}) must match agents length ({})",
                final_weights.len(),
                agents.len()
            )));
        }

        // Create backends
        let backends: Vec<AgentBackend> = agents
            .into_iter()
            .zip(final_weights)
            .map(|(agent, weight)| AgentBackend {
                agent,
                weight,
                healthy: true,
                active_connections: 0,
                total_requests: 0,
                total_failures: 0,
                last_health_check: time::Instant::now(),
                consecutive_failures: 0,
            })
            .collect();

        let backend_count = backends.len();
        Ok(Self {
            name: format!("load-balancer-{}-backends", backend_count),
            backends: Arc::new(RwLock::new(backends)),
            config,
            metrics: Arc::new(RwLock::new(LoadBalancerMetrics::default())),
            current_index: Arc::new(RwLock::new(0)),
        })
    }

    /// Get statistics for all backends.
    pub async fn get_backend_stats(&self) -> Vec<BackendStats> {
        let backends = self.backends.read().await;
        backends
            .iter()
            .map(|backend| BackendStats {
                name: backend.agent.name().to_string(),
                healthy: backend.healthy,
                weight: backend.weight,
                active_connections: backend.active_connections,
                total_requests: backend.total_requests,
                total_failures: backend.total_failures,
            })
            .collect()
    }

    /// Start background health check tasks.
    pub fn start_health_checks(&self) {
        let backends = Arc::clone(&self.backends);
        let metrics = Arc::clone(&self.metrics);
        let config = self.config.clone();

        tokio::spawn(async move {
            let mut interval = time::interval(config.health_check_interval);
            loop {
                interval.tick().await;
                Self::perform_health_checks(
                    &backends,
                    &metrics,
                    config.health_check_timeout,
                    config.failure_threshold,
                )
                .await;
            }
        });
    }

    async fn perform_health_checks(
        backends: &Arc<RwLock<Vec<AgentBackend>>>,
        metrics: &Arc<RwLock<LoadBalancerMetrics>>,
        timeout: Duration,
        failure_threshold: usize,
    ) {
        let mut backends_write = backends.write().await;

        for backend in backends_write.iter_mut() {
            // Simple health check: test if agent responds
            let test_msg = Message::with_text("system", "health_check");

            let result = tokio::time::timeout(timeout, backend.agent.process(test_msg)).await;

            backend.last_health_check = time::Instant::now();

            match result {
                Ok(Ok(_)) => {
                    // Success
                    backend.consecutive_failures = 0;
                    if !backend.healthy && backend.consecutive_failures == 0 {
                        backend.healthy = true;
                        Self::track_health_change(metrics, backend.agent.name(), "recovered").await;
                    }
                }
                _ => {
                    // Failure
                    backend.consecutive_failures += 1;
                    backend.total_failures += 1;

                    if backend.healthy && backend.consecutive_failures >= failure_threshold {
                        backend.healthy = false;
                        Self::track_health_change(metrics, backend.agent.name(), "unhealthy").await;
                    }
                }
            }
        }
    }

    async fn track_health_change(
        metrics: &Arc<RwLock<LoadBalancerMetrics>>,
        agent_name: &str,
        change_type: &str,
    ) {
        let mut metrics_write = metrics.write().await;
        let key = format!("{}:{}", agent_name, change_type);
        *metrics_write.backend_health_changes.entry(key).or_insert(0) += 1;
    }

    async fn select_backend(&self) -> Result<usize, AgentError> {
        let backends = self.backends.read().await;
        let healthy_indices: Vec<usize> = backends
            .iter()
            .enumerate()
            .filter(|(_, b)| b.healthy)
            .map(|(i, _)| i)
            .collect();

        if healthy_indices.is_empty() {
            return Err(AgentError::ExecutionError(
                "All backends unhealthy".to_string(),
            ));
        }

        match self.config.strategy {
            LoadBalancingStrategy::RoundRobin => self.select_round_robin().await,
            LoadBalancingStrategy::LeastConnections => {
                self.select_least_connections(&healthy_indices).await
            }
            LoadBalancingStrategy::WeightedRoundRobin => {
                self.select_weighted_round_robin(&healthy_indices).await
            }
            LoadBalancingStrategy::Random => {
                let mut rng = rand::rng();
                let index = rng.random_range(0..healthy_indices.len());
                Ok(healthy_indices[index])
            }
        }
    }

    async fn select_round_robin(&self) -> Result<usize, AgentError> {
        let backends = self.backends.read().await;
        let mut current_index = self.current_index.write().await;

        // Find next healthy backend in rotation
        for _ in 0..backends.len() {
            *current_index = (*current_index + 1) % backends.len();
            if backends[*current_index].healthy {
                return Ok(*current_index);
            }
        }

        // Fallback to first healthy
        backends
            .iter()
            .position(|b| b.healthy)
            .ok_or_else(|| AgentError::ExecutionError("No healthy backends".to_string()))
    }

    async fn select_least_connections(
        &self,
        healthy_indices: &[usize],
    ) -> Result<usize, AgentError> {
        let backends = self.backends.read().await;

        healthy_indices
            .iter()
            .min_by_key(|&&i| backends[i].active_connections)
            .copied()
            .ok_or_else(|| AgentError::ExecutionError("No healthy backends".to_string()))
    }

    async fn select_weighted_round_robin(
        &self,
        healthy_indices: &[usize],
    ) -> Result<usize, AgentError> {
        let backends = self.backends.read().await;
        let mut current_index = self.current_index.write().await;

        // Build weighted list
        let mut weighted = Vec::new();
        for &index in healthy_indices {
            for _ in 0..backends[index].weight {
                weighted.push(index);
            }
        }

        if weighted.is_empty() {
            return Err(AgentError::ExecutionError(
                "No healthy backends".to_string(),
            ));
        }

        *current_index = (*current_index + 1) % weighted.len();
        Ok(weighted[*current_index])
    }

    /// Get current metrics.
    pub async fn get_metrics(&self) -> LoadBalancerMetrics {
        self.metrics.read().await.clone()
    }
}

#[async_trait]
impl Agent for LoadBalancer {
    fn name(&self) -> &str {
        &self.name
    }

    fn capabilities(&self) -> Vec<String> {
        // Return union of all backend capabilities
        Vec::new() // Simplified for now
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Increment total requests
        {
            let mut metrics = self.metrics.write().await;
            metrics.total_requests += 1;
        }

        let mut attempted = std::collections::HashSet::new();

        loop {
            let backend_index = self.select_backend().await?;

            // Get backend name for tracking
            let backend_name = {
                let backends = self.backends.read().await;
                backends[backend_index].agent.name().to_string()
            };

            // Avoid retrying same backend
            if attempted.contains(&backend_name) {
                if !self.config.enable_failover
                    || attempted.len() >= self.backends.read().await.len()
                {
                    return Err(AgentError::ExecutionError(
                        "All backends attempted".to_string(),
                    ));
                }
                continue;
            }

            attempted.insert(backend_name.clone());

            // Track request
            {
                let mut backends = self.backends.write().await;
                backends[backend_index].active_connections += 1;
                backends[backend_index].total_requests += 1;
            }

            let result = {
                let backends = self.backends.read().await;
                backends[backend_index].agent.process(message.clone()).await
            };

            // Decrement active connections
            {
                let mut backends = self.backends.write().await;
                backends[backend_index].active_connections -= 1;
            }

            match result {
                Ok(response) => {
                    // Success
                    let mut metrics = self.metrics.write().await;
                    metrics.successful_requests += 1;
                    return Ok(response);
                }
                Err(error) => {
                    // Failure
                    {
                        let mut backends = self.backends.write().await;
                        backends[backend_index].total_failures += 1;
                    }

                    {
                        let mut metrics = self.metrics.write().await;
                        metrics.failed_requests += 1;
                    }

                    // Check if should mark unhealthy
                    {
                        let mut backends = self.backends.write().await;
                        if backends[backend_index].total_failures
                            >= self.config.failure_threshold as u64
                        {
                            backends[backend_index].healthy = false;
                            Self::track_health_change(&self.metrics, &backend_name, "unhealthy")
                                .await;
                        }
                    }

                    // Try failover if enabled
                    if self.config.enable_failover
                        && attempted.len() < self.backends.read().await.len()
                    {
                        let mut metrics = self.metrics.write().await;
                        metrics.failover_attempts += 1;
                        continue;
                    }

                    // No more failover
                    return Err(AgentError::ExecutionError(format!(
                        "Backend {} failed: {}",
                        backend_name, error
                    )));
                }
            }
        }
    }
}
