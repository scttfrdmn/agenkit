// Health checking for agents with Kubernetes-style probes:
// - Liveness: Is the agent alive?
// - Readiness: Is the agent ready to accept traffic?
// - Startup: Has initialization completed?
// - Prometheus metrics export

use crate::core::{Agent, AgentError, Message};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;
use tokio::time;

/// Health status values.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HealthStatus {
    Healthy,
    Unhealthy,
    Degraded,
    Unknown,
}

impl HealthStatus {
    pub fn as_str(&self) -> &str {
        match self {
            HealthStatus::Healthy => "healthy",
            HealthStatus::Unhealthy => "unhealthy",
            HealthStatus::Degraded => "degraded",
            HealthStatus::Unknown => "unknown",
        }
    }
}

/// Types of health probes.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ProbeType {
    Liveness,
    Readiness,
    Startup,
}

impl ProbeType {
    pub fn as_str(&self) -> &str {
        match self {
            ProbeType::Liveness => "liveness",
            ProbeType::Readiness => "readiness",
            ProbeType::Startup => "startup",
        }
    }
}

/// Result of a health check.
#[derive(Debug, Clone)]
pub struct HealthCheckResult {
    pub status: HealthStatus,
    pub probe_type: ProbeType,
    pub message: String,
    pub timestamp: Instant,
    pub duration_ms: f64,
}

/// Health check configuration.
#[derive(Debug, Clone)]
pub struct HealthCheckConfig {
    // Liveness probe settings
    pub liveness_enabled: bool,
    pub liveness_interval: Duration,
    pub liveness_timeout: Duration,
    pub liveness_failure_threshold: usize,

    // Readiness probe settings
    pub readiness_enabled: bool,
    pub readiness_interval: Duration,
    pub readiness_timeout: Duration,
    pub readiness_failure_threshold: usize,

    // Startup probe settings
    pub startup_enabled: bool,
    pub startup_timeout: Duration,
    pub startup_failure_threshold: usize,
}

impl Default for HealthCheckConfig {
    fn default() -> Self {
        Self {
            liveness_enabled: true,
            liveness_interval: Duration::from_secs(10),
            liveness_timeout: Duration::from_secs(5),
            liveness_failure_threshold: 3,
            readiness_enabled: true,
            readiness_interval: Duration::from_secs(5),
            readiness_timeout: Duration::from_secs(3),
            readiness_failure_threshold: 2,
            startup_enabled: true,
            startup_timeout: Duration::from_secs(30),
            startup_failure_threshold: 30,
        }
    }
}

/// Health check metrics.
#[derive(Debug, Clone)]
pub struct HealthMetrics {
    pub total_checks: HashMap<ProbeType, u64>,
    pub successful_checks: HashMap<ProbeType, u64>,
    pub failed_checks: HashMap<ProbeType, u64>,
    pub last_check_time: HashMap<ProbeType, Instant>,
    pub last_check_duration: HashMap<ProbeType, f64>,
    pub consecutive_failures: HashMap<ProbeType, usize>,
    pub uptime_start: Instant,
}

impl HealthMetrics {
    pub fn new() -> Self {
        Self {
            total_checks: HashMap::new(),
            successful_checks: HashMap::new(),
            failed_checks: HashMap::new(),
            last_check_time: HashMap::new(),
            last_check_duration: HashMap::new(),
            consecutive_failures: HashMap::new(),
            uptime_start: Instant::now(),
        }
    }

    pub fn get_uptime(&self) -> f64 {
        self.uptime_start.elapsed().as_secs_f64()
    }
}

impl Default for HealthMetrics {
    fn default() -> Self {
        Self::new()
    }
}

/// Health checker monitors agent health.
pub struct HealthChecker {
    agent: Arc<dyn Agent>,
    config: HealthCheckConfig,
    metrics: Arc<RwLock<HealthMetrics>>,
    is_alive: Arc<RwLock<bool>>,
    is_ready: Arc<RwLock<bool>>,
    startup_complete: Arc<RwLock<bool>>,
}

impl HealthChecker {
    /// Create a new health checker.
    pub fn new(agent: Arc<dyn Agent>, config: HealthCheckConfig) -> Self {
        Self {
            agent,
            config,
            metrics: Arc::new(RwLock::new(HealthMetrics::new())),
            is_alive: Arc::new(RwLock::new(true)),
            is_ready: Arc::new(RwLock::new(false)),
            startup_complete: Arc::new(RwLock::new(false)),
        }
    }

    /// Check if agent is healthy overall.
    pub async fn is_healthy(&self) -> bool {
        let is_alive = *self.is_alive.read().await;
        let is_ready = *self.is_ready.read().await;
        is_alive && is_ready
    }

    /// Start background health check tasks.
    pub fn start(&self) {
        if self.config.liveness_enabled {
            let checker = self.clone_for_task();
            tokio::spawn(async move {
                checker.liveness_loop().await;
            });
        }

        if self.config.readiness_enabled {
            let checker = self.clone_for_task();
            tokio::spawn(async move {
                checker.readiness_loop().await;
            });
        }

        if self.config.startup_enabled {
            let checker = self.clone_for_task();
            tokio::spawn(async move {
                checker.startup_check().await;
            });
        }
    }

    fn clone_for_task(&self) -> Self {
        Self {
            agent: Arc::clone(&self.agent),
            config: self.config.clone(),
            metrics: Arc::clone(&self.metrics),
            is_alive: Arc::clone(&self.is_alive),
            is_ready: Arc::clone(&self.is_ready),
            startup_complete: Arc::clone(&self.startup_complete),
        }
    }

    /// Perform a liveness check.
    pub async fn check_liveness(&self) -> HealthCheckResult {
        let start_time = Instant::now();
        let probe_type = ProbeType::Liveness;

        self.track_check_started(probe_type).await;

        // Basic liveness: Can we call methods?
        let _ = self.agent.name();
        let _ = self.agent.capabilities();

        // Success
        let duration = start_time.elapsed().as_secs_f64() * 1000.0;
        self.track_check_success(probe_type, duration).await;

        HealthCheckResult {
            status: HealthStatus::Healthy,
            probe_type,
            message: "Agent process is alive".to_string(),
            timestamp: Instant::now(),
            duration_ms: duration,
        }
    }

    /// Perform a readiness check.
    pub async fn check_readiness(&self) -> HealthCheckResult {
        let start_time = Instant::now();
        let probe_type = ProbeType::Readiness;

        self.track_check_started(probe_type).await;

        // Check if startup completed
        if self.config.startup_enabled && !*self.startup_complete.read().await {
            let duration = start_time.elapsed().as_secs_f64() * 1000.0;
            self.track_check_failure(probe_type, duration).await;
            return HealthCheckResult {
                status: HealthStatus::Unhealthy,
                probe_type,
                message: "Startup not complete".to_string(),
                timestamp: Instant::now(),
                duration_ms: duration,
            };
        }

        // Test with a simple request
        let test_msg = Message {
            role: "system".to_string(),
            content: "readiness_check".to_string(),
            metadata: None,
        };

        let result =
            time::timeout(self.config.readiness_timeout, self.agent.process(test_msg)).await;
        let duration = start_time.elapsed().as_secs_f64() * 1000.0;

        match result {
            Ok(Ok(response)) if !response.content.is_empty() => {
                // Success
                self.track_check_success(probe_type, duration).await;

                HealthCheckResult {
                    status: HealthStatus::Healthy,
                    probe_type,
                    message: "Agent is ready to handle requests".to_string(),
                    timestamp: Instant::now(),
                    duration_ms: duration,
                }
            }
            _ => {
                self.track_check_failure(probe_type, duration).await;
                HealthCheckResult {
                    status: HealthStatus::Unhealthy,
                    probe_type,
                    message: "Readiness check failed".to_string(),
                    timestamp: Instant::now(),
                    duration_ms: duration,
                }
            }
        }
    }

    /// Perform a startup check.
    pub async fn check_startup(&self) -> HealthCheckResult {
        let start_time = Instant::now();
        let probe_type = ProbeType::Startup;

        self.track_check_started(probe_type).await;

        // Perform readiness check as startup test
        let readiness_result = self.check_readiness().await;

        if readiness_result.status == HealthStatus::Healthy {
            *self.startup_complete.write().await = true;

            let duration = start_time.elapsed().as_secs_f64() * 1000.0;
            self.track_check_success(probe_type, duration).await;

            HealthCheckResult {
                status: HealthStatus::Healthy,
                probe_type,
                message: "Startup complete".to_string(),
                timestamp: Instant::now(),
                duration_ms: duration,
            }
        } else {
            let duration = start_time.elapsed().as_secs_f64() * 1000.0;
            self.track_check_failure(probe_type, duration).await;

            HealthCheckResult {
                status: HealthStatus::Unhealthy,
                probe_type,
                message: "Startup checks not passing yet".to_string(),
                timestamp: Instant::now(),
                duration_ms: duration,
            }
        }
    }

    async fn liveness_loop(&self) {
        let mut interval = time::interval(self.config.liveness_interval);
        loop {
            interval.tick().await;
            let result = self.check_liveness().await;

            let mut is_alive = self.is_alive.write().await;
            if result.status == HealthStatus::Unhealthy {
                let metrics = self.metrics.read().await;
                let failures = metrics
                    .consecutive_failures
                    .get(&ProbeType::Liveness)
                    .copied()
                    .unwrap_or(0);
                if failures >= self.config.liveness_failure_threshold {
                    *is_alive = false;
                }
            } else {
                *is_alive = true;
            }
        }
    }

    async fn readiness_loop(&self) {
        let mut interval = time::interval(self.config.readiness_interval);
        loop {
            interval.tick().await;
            let result = self.check_readiness().await;

            let mut is_ready = self.is_ready.write().await;
            if result.status == HealthStatus::Unhealthy {
                let metrics = self.metrics.read().await;
                let failures = metrics
                    .consecutive_failures
                    .get(&ProbeType::Readiness)
                    .copied()
                    .unwrap_or(0);
                if failures >= self.config.readiness_failure_threshold {
                    *is_ready = false;
                }
            } else {
                *is_ready = true;
            }
        }
    }

    async fn startup_check(&self) {
        let start_time = Instant::now();
        let mut attempts = 0;

        let mut interval = time::interval(Duration::from_secs(10));
        loop {
            interval.tick().await;

            if start_time.elapsed() > self.config.startup_timeout {
                break;
            }

            attempts += 1;
            if attempts > self.config.startup_failure_threshold {
                break;
            }

            let result = self.check_startup().await;
            if result.status == HealthStatus::Healthy {
                break;
            }
        }
    }

    async fn track_check_started(&self, probe_type: ProbeType) {
        let mut metrics = self.metrics.write().await;
        *metrics.total_checks.entry(probe_type).or_insert(0) += 1;
    }

    async fn track_check_success(&self, probe_type: ProbeType, duration_ms: f64) {
        let mut metrics = self.metrics.write().await;
        *metrics.successful_checks.entry(probe_type).or_insert(0) += 1;
        metrics.last_check_time.insert(probe_type, Instant::now());
        metrics.last_check_duration.insert(probe_type, duration_ms);
        metrics.consecutive_failures.insert(probe_type, 0);
    }

    async fn track_check_failure(&self, probe_type: ProbeType, duration_ms: f64) {
        let mut metrics = self.metrics.write().await;
        *metrics.failed_checks.entry(probe_type).or_insert(0) += 1;
        metrics.last_check_time.insert(probe_type, Instant::now());
        metrics.last_check_duration.insert(probe_type, duration_ms);
        *metrics.consecutive_failures.entry(probe_type).or_insert(0) += 1;
    }

    /// Export metrics in Prometheus format.
    pub async fn export_prometheus_metrics(&self) -> String {
        let metrics = self.metrics.read().await;
        let mut lines = Vec::new();

        // Total checks
        lines.push("# HELP agenkit_health_checks_total Total number of health checks performed".to_string());
        lines.push("# TYPE agenkit_health_checks_total counter".to_string());
        for (probe_type, count) in &metrics.total_checks {
            lines.push(format!(
                "agenkit_health_checks_total{{probe=\"{}\"}} {}",
                probe_type.as_str(),
                count
            ));
        }

        // Failed checks
        lines.push("".to_string());
        lines.push("# HELP agenkit_health_check_failures_total Total number of failed health checks".to_string());
        lines.push("# TYPE agenkit_health_check_failures_total counter".to_string());
        for (probe_type, count) in &metrics.failed_checks {
            lines.push(format!(
                "agenkit_health_check_failures_total{{probe=\"{}\"}} {}",
                probe_type.as_str(),
                count
            ));
        }

        // Duration
        lines.push("".to_string());
        lines.push("# HELP agenkit_health_check_duration_ms Duration of last health check in milliseconds".to_string());
        lines.push("# TYPE agenkit_health_check_duration_ms gauge".to_string());
        for (probe_type, duration) in &metrics.last_check_duration {
            lines.push(format!(
                "agenkit_health_check_duration_ms{{probe=\"{}\"}} {:.2}",
                probe_type.as_str(),
                duration
            ));
        }

        // Uptime
        lines.push("".to_string());
        lines.push("# HELP agenkit_agent_uptime_seconds Uptime in seconds".to_string());
        lines.push("# TYPE agenkit_agent_uptime_seconds gauge".to_string());
        lines.push(format!(
            "agenkit_agent_uptime_seconds {:.2}",
            metrics.get_uptime()
        ));

        // Health status
        lines.push("".to_string());
        lines.push("# HELP agenkit_agent_healthy Agent health status (1=healthy, 0=unhealthy)".to_string());
        lines.push("# TYPE agenkit_agent_healthy gauge".to_string());
        let health_value = if self.is_healthy().await { 1 } else { 0 };
        lines.push(format!("agenkit_agent_healthy {}", health_value));

        lines.join("\n")
    }

    /// Get current metrics.
    pub async fn get_metrics(&self) -> HealthMetrics {
        self.metrics.read().await.clone()
    }
}
