// Production-ready agent with load balancing, health checks, and enhanced retry.
//
// This example demonstrates how to build a production agent system with:
// - Load balancing across multiple backend agents
// - Health monitoring with Kubernetes-style probes
// - Enhanced retry with jitter and backpressure detection
// - Prometheus metrics export
//
// Perfect for 30-hour autonomous agent deployments.

use agenkit_rust::core::{Agent, AgentError, Message};
use agenkit_rust::infrastructure::{
    EnhancedRetryConfig, EnhancedRetryDecorator, HealthCheckConfig, HealthChecker,
    JitterType, LoadBalancer, LoadBalancerConfig, LoadBalancingStrategy,
};
use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::time::{sleep, Duration};

/// Simulated agent for testing production infrastructure.
struct SimulatedAgent {
    name: String,
    failure_rate: f64,
    request_count: Arc<tokio::sync::Mutex<u64>>,
}

impl SimulatedAgent {
    fn new(name: &str, failure_rate: f64) -> Self {
        Self {
            name: name.to_string(),
            failure_rate,
            request_count: Arc::new(tokio::sync::Mutex::new(0)),
        }
    }
}

#[async_trait]
impl Agent for SimulatedAgent {
    fn name(&self) -> String {
        self.name.clone()
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["text_generation".to_string(), "reasoning".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let mut count = self.request_count.lock().await;
        *count += 1;
        let request_num = *count;
        drop(count);

        // Simulate processing time
        sleep(Duration::from_millis(100)).await;

        // Simulate occasional failures
        if rand::random::<f64>() < self.failure_rate {
            return Err(AgentError::ProcessingError(format!(
                "{}: Simulated transient error",
                self.name
            )));
        }

        let mut metadata = HashMap::new();
        metadata.insert("agent".to_string(), self.name.clone());
        metadata.insert("request_count".to_string(), request_num.to_string());
        metadata.insert(
            "timestamp".to_string(),
            chrono::Utc::now().to_rfc3339(),
        );

        Ok(Message {
            role: "agent".to_string(),
            content: format!("{} processed: {}", self.name, message.content),
            metadata: Some(metadata),
        })
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Starting production agent system...");

    // 1. Create backend agents with varying failure rates
    let backend1 = Arc::new(SimulatedAgent::new("agent-1", 0.1));
    let backend2 = Arc::new(SimulatedAgent::new("agent-2", 0.05));
    let backend3 = Arc::new(SimulatedAgent::new("agent-3", 0.15));

    // 2. Wrap each backend with enhanced retry
    let retry_config = EnhancedRetryConfig {
        max_attempts: 3,
        initial_backoff: Duration::from_millis(100),
        max_backoff: Duration::from_secs(5),
        backoff_multiplier: 2.0,
        jitter_type: JitterType::Full,
        enable_backpressure: true,
        backpressure_threshold: 0.3,
        backpressure_window: 10,
        ..Default::default()
    };

    let retry_backend1 = Arc::new(EnhancedRetryDecorator::new(
        backend1.clone(),
        retry_config.clone(),
    ));
    let retry_backend2 = Arc::new(EnhancedRetryDecorator::new(
        backend2.clone(),
        retry_config.clone(),
    ));
    let retry_backend3 = Arc::new(EnhancedRetryDecorator::new(
        backend3.clone(),
        retry_config.clone(),
    ));

    // 3. Create load balancer with health checking
    let lb_config = LoadBalancerConfig {
        strategy: LoadBalancingStrategy::LeastConnections,
        health_check_enabled: true,
        health_check_interval: Duration::from_secs(5),
        health_check_timeout: Duration::from_secs(2),
        max_retries_per_backend: 2,
    };

    let load_balancer = Arc::new(LoadBalancer::new(
        vec![
            retry_backend1.clone(),
            retry_backend2.clone(),
            retry_backend3.clone(),
        ],
        lb_config,
    ));

    // 4. Set up health checker for the load balancer
    let health_config = HealthCheckConfig {
        liveness_enabled: true,
        liveness_interval: Duration::from_secs(10),
        liveness_failure_threshold: 3,
        readiness_enabled: true,
        readiness_interval: Duration::from_secs(5),
        readiness_failure_threshold: 2,
        startup_enabled: true,
        startup_timeout: Duration::from_secs(30),
        startup_failure_threshold: 5,
        ..Default::default()
    };

    let health_checker = Arc::new(HealthChecker::new(
        load_balancer.clone(),
        health_config,
    ));
    health_checker.start().await;

    // Wait for startup to complete
    println!("Waiting for startup checks...");
    sleep(Duration::from_secs(2)).await;

    if !health_checker.is_healthy() {
        eprintln!("System failed startup checks");
        return Ok(());
    }

    println!("System is healthy and ready!");

    // 5. Process requests through the production system
    let mut successful = 0;
    let mut failed = 0;

    for i in 0..20 {
        let message = Message {
            role: "user".to_string(),
            content: format!("Request {}", i),
            metadata: None,
        };

        match load_balancer.process(message).await {
            Ok(response) => {
                println!("Request {}: SUCCESS - {}", i, response.content);
                successful += 1;
            }
            Err(e) => {
                eprintln!("Request {}: FAILED - {:?}", i, e);
                failed += 1;
            }
        }

        // Brief pause between requests
        sleep(Duration::from_millis(200)).await;
    }

    // 6. Export metrics
    println!("\n{}", "=".repeat(60));
    println!("FINAL METRICS");
    println!("{}", "=".repeat(60));

    // Load balancer metrics
    let lb_metrics = load_balancer.get_metrics();
    println!("\nLoad Balancer:");
    println!("  Total requests: {}", lb_metrics.total_requests);
    println!("  Successful: {}", lb_metrics.successful_requests);
    println!("  Failed: {}", lb_metrics.failed_requests);
    if lb_metrics.total_requests > 0 {
        let success_rate =
            (lb_metrics.successful_requests as f64 / lb_metrics.total_requests as f64) * 100.0;
        println!("  Success rate: {:.1}%", success_rate);
    }

    // Backend distribution
    println!("\nBackend Distribution:");
    for (backend_id, count) in &lb_metrics.backend_request_counts {
        println!("  {}: {} requests", backend_id, count);
    }

    // Retry metrics for each backend
    println!("\nRetry Metrics:");
    let backends = vec![retry_backend1, retry_backend2, retry_backend3];
    for (i, backend) in backends.iter().enumerate() {
        let metrics = backend.get_metrics();
        println!("  Agent {}:", i + 1);
        println!("    Total attempts: {}", metrics.total_attempts);
        println!(
            "    Successful on first: {}",
            metrics.successful_first_attempt
        );
        println!("    Successful on retry: {}", metrics.successful_on_retry);
        println!(
            "    Failed after retries: {}",
            metrics.failed_after_retries
        );
        println!("    Total retries: {}", metrics.total_retries);
        if metrics.backpressure_detected > 0 {
            println!(
                "    Backpressure detected: {} times",
                metrics.backpressure_detected
            );
        }
    }

    // Health metrics
    let health_metrics = health_checker.get_metrics();
    println!("\nHealth Checks:");
    for (probe_type, count) in &health_metrics.total_checks {
        let success = health_metrics
            .successful_checks
            .get(probe_type)
            .unwrap_or(&0);
        let failed_count = health_metrics.failed_checks.get(probe_type).unwrap_or(&0);
        println!(
            "  {:?}: {}/{} passed ({} failed)",
            probe_type, success, count, failed_count
        );
    }

    // Export Prometheus metrics
    println!("\nPrometheus Metrics:");
    println!("{}", "=".repeat(60));
    let prometheus_metrics = health_checker.export_prometheus_metrics();
    println!("{}", prometheus_metrics);

    // Stop health checker
    health_checker.stop().await;
    println!("\nProduction agent system stopped.");

    Ok(())
}
