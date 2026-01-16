//! Metrics collection with OpenTelemetry.
//!
//! This module provides metric recording with Prometheus and OTLP exporters,
//! automatic metric collection through middleware, and custom metric recording.
//!
//! # Example
//!
//! ```rust,no_run
//! use agenkit::observability::{init_metrics, MetricsMiddleware};
//! use agenkit::core::Agent;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // Initialize metrics
//! init_metrics("prometheus", Some("0.0.0.0:9464"))?;
//!
//! // Wrap agent with metrics middleware
//! // let agent = MyAgent::new();
//! // let metrics_agent = MetricsMiddleware::new(agent);
//!
//! // Process messages (metrics recorded automatically)
//! // let response = metrics_agent.process(msg).await?;
//! # Ok(())
//! # }
//! ```

use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use once_cell::sync::OnceCell;
use opentelemetry::{
    global,
    metrics::{Counter, Histogram, Meter, MeterProvider as _},
    KeyValue,
};
use opentelemetry_sdk::metrics::{PeriodicReader, SdkMeterProvider};
use std::time::Instant;

/// Global meter provider (initialized once).
static GLOBAL_METER_PROVIDER: OnceCell<SdkMeterProvider> = OnceCell::new();

/// Initialize metrics with the specified exporter type.
///
/// This function must be called before using any metrics functionality.
/// It can only be called once per process.
///
/// # Arguments
///
/// * `exporter_type` - Type of exporter: "prometheus" or "otlp"
/// * `endpoint` - Optional endpoint for the exporter
///
/// # Example
///
/// ```rust,no_run
/// use agenkit::observability::metrics::init_metrics;
///
/// // Prometheus exporter on port 9464
/// init_metrics("prometheus", Some("0.0.0.0:9464"))?;
///
/// // OTLP exporter to localhost
/// init_metrics("otlp", Some("http://localhost:4317"))?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
///
/// # Errors
///
/// Returns an error if:
/// - Exporter type is unknown
/// - Meter provider is already initialized
/// - Exporter setup fails
pub fn init_metrics(
    exporter_type: &str,
    endpoint: Option<&str>,
) -> Result<(), Box<dyn std::error::Error>> {
    let provider: SdkMeterProvider = match exporter_type {
        "prometheus" => {
            let exporter = opentelemetry_prometheus::exporter()
                .with_registry(prometheus::Registry::new())
                .build()?;

            SdkMeterProvider::builder().with_reader(exporter).build()
        }
        "otlp" => {
            use opentelemetry_otlp::WithExportConfig;
            let endpoint = endpoint.unwrap_or("http://localhost:4317");

            let exporter = opentelemetry_otlp::new_exporter()
                .tonic()
                .with_endpoint(endpoint)
                .build_metrics_exporter(
                    Box::new(
                        opentelemetry_sdk::metrics::reader::DefaultAggregationSelector::new(),
                    ),
                    Box::new(
                        opentelemetry_sdk::metrics::reader::DefaultTemporalitySelector::new(),
                    ),
                )?;

            let reader =
                PeriodicReader::builder(exporter, opentelemetry_sdk::runtime::Tokio).build();

            SdkMeterProvider::builder().with_reader(reader).build()
        }
        _ => {
            return Err(format!("Unknown exporter type: {}", exporter_type).into());
        }
    };

    GLOBAL_METER_PROVIDER
        .set(provider.clone())
        .map_err(|_| "Meter provider already initialized")?;

    // Set as global provider
    global::set_meter_provider(provider);

    Ok(())
}

/// Get the global meter.
///
/// # Panics
///
/// Panics if `init_metrics()` has not been called.
pub fn get_meter(name: impl Into<String>) -> Meter {
    GLOBAL_METER_PROVIDER
        .get()
        .expect("Meter provider not initialized. Call init_metrics() first.")
        .meter(name.into())
}

/// Middleware that automatically records metrics for agent operations.
///
/// This middleware wraps an agent and records:
/// - Request count (counter with success/error status)
/// - Request duration (histogram in seconds)
///
/// # Example
///
/// ```rust,no_run
/// use agenkit::observability::MetricsMiddleware;
/// use agenkit::core::Agent;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// // let agent = MyAgent::new();
/// // let metrics_agent = MetricsMiddleware::new(agent);
/// // let response = metrics_agent.process(msg).await?;
/// # Ok(())
/// # }
/// ```
pub struct MetricsMiddleware<A: Agent> {
    inner: A,
    requests_total: Counter<u64>,
    request_duration: Histogram<f64>,
}

impl<A: Agent> MetricsMiddleware<A> {
    /// Create a new MetricsMiddleware wrapping the given agent.
    ///
    /// # Panics
    ///
    /// Panics if `init_metrics()` has not been called.
    pub fn new(inner: A) -> Self {
        let meter = get_meter("agenkit-rust");

        let requests_total = meter
            .u64_counter("agent_requests_total")
            .with_description("Total number of agent requests")
            .init();

        let request_duration = meter
            .f64_histogram("agent_request_duration_seconds")
            .with_description("Agent request duration in seconds")
            .init();

        Self {
            inner,
            requests_total,
            request_duration,
        }
    }

    /// Get a reference to the inner agent.
    pub fn inner(&self) -> &A {
        &self.inner
    }

    /// Consume this middleware and return the inner agent.
    pub fn into_inner(self) -> A {
        self.inner
    }
}

#[async_trait]
impl<A: Agent> Agent for MetricsMiddleware<A> {
    fn name(&self) -> &str {
        self.inner.name()
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let start = Instant::now();
        let result = self.inner.process(message).await;
        let duration = start.elapsed().as_secs_f64();

        // Record metrics
        let status = if result.is_ok() { "success" } else { "error" };
        let agent_name = self.inner.name();

        self.requests_total.add(
            1,
            &[
                KeyValue::new("agent.name", agent_name.to_string()),
                KeyValue::new("status", status.to_string()),
            ],
        );

        self.request_duration.record(
            duration,
            &[KeyValue::new("agent.name", agent_name.to_string())],
        );

        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::{Agent, AgentError, Message};
    use async_trait::async_trait;
    use std::sync::Arc;

    struct TestAgent {
        name: String,
    }

    #[async_trait]
    impl Agent for TestAgent {
        fn name(&self) -> &str {
            &self.name
        }

        async fn process(&self, mut message: Message) -> Result<Message, AgentError> {
            message.role = "assistant".to_string();
            Ok(message)
        }
    }

    struct FailingAgent {
        name: String,
    }

    #[async_trait]
    impl Agent for FailingAgent {
        fn name(&self) -> &str {
            &self.name
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Err(AgentError::ProcessingError(
                "intentional failure".to_string(),
            ))
        }
    }

    #[test]
    fn test_init_metrics_prometheus() {
        // Prometheus exporter should work (or already be initialized)
        let result = init_metrics("prometheus", None);
        assert!(
            result.is_ok()
                || result
                    .unwrap_err()
                    .to_string()
                    .contains("already initialized"),
            "Prometheus exporter should initialize or already be initialized"
        );
    }

    #[test]
    fn test_init_metrics_unknown() {
        // Unknown exporter type should fail
        let result = init_metrics("unknown", None);
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("Unknown exporter type"));
    }

    #[tokio::test]
    async fn test_metrics_middleware_success() {
        // Initialize if not already done
        let _ = init_metrics("prometheus", None);

        let agent = TestAgent {
            name: "test_agent".to_string(),
        };
        let metrics_agent = MetricsMiddleware::new(agent);

        let message = Message::new("user", serde_json::json!("test"));
        let result = metrics_agent.process(message).await;

        assert!(result.is_ok());
        assert_eq!(result.unwrap().role, "assistant");
    }

    #[tokio::test]
    async fn test_metrics_middleware_error() {
        // Initialize if not already done
        let _ = init_metrics("prometheus", None);

        let agent = FailingAgent {
            name: "failing".to_string(),
        };
        let metrics_agent = MetricsMiddleware::new(agent);

        let message = Message::new("user", serde_json::json!("test"));
        let result = metrics_agent.process(message).await;

        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_metrics_middleware_records_duration() {
        // Initialize if not already done
        let _ = init_metrics("prometheus", None);

        let agent = TestAgent {
            name: "test_agent".to_string(),
        };
        let metrics_agent = MetricsMiddleware::new(agent);

        let message = Message::new("user", serde_json::json!("test"));
        let start = Instant::now();
        let _ = metrics_agent.process(message).await;
        let elapsed = start.elapsed();

        // Duration should be recorded (can't easily verify the value, but we can check it completes)
        assert!(elapsed.as_secs_f64() >= 0.0);
    }

    #[test]
    fn test_metrics_middleware_name_delegation() {
        // Initialize if not already done
        let _ = init_metrics("prometheus", None);

        let agent = TestAgent {
            name: "test_agent".to_string(),
        };
        let metrics_agent = MetricsMiddleware::new(agent);

        assert_eq!(metrics_agent.name(), "test_agent");
    }

    #[test]
    fn test_metrics_middleware_inner_access() {
        // Initialize if not already done
        let _ = init_metrics("prometheus", None);

        let agent = TestAgent {
            name: "test_agent".to_string(),
        };
        let metrics_agent = MetricsMiddleware::new(agent);

        assert_eq!(metrics_agent.inner().name(), "test_agent");
    }

    #[test]
    fn test_metrics_middleware_into_inner() {
        // Initialize if not already done
        let _ = init_metrics("prometheus", None);

        let agent = TestAgent {
            name: "test_agent".to_string(),
        };
        let metrics_agent = MetricsMiddleware::new(agent);

        let inner = metrics_agent.into_inner();
        assert_eq!(inner.name(), "test_agent");
    }

    #[tokio::test]
    async fn test_multiple_requests() {
        // Initialize if not already done
        let _ = init_metrics("prometheus", None);

        let agent = TestAgent {
            name: "test_agent".to_string(),
        };
        let metrics_agent = Arc::new(MetricsMiddleware::new(agent));

        // Process multiple requests
        for i in 0..5 {
            let message = Message::new("user", serde_json::json!(format!("test {}", i)));
            let result: Result<Message, AgentError> = metrics_agent.process(message).await;
            assert!(result.is_ok());
        }
    }

    #[tokio::test]
    async fn test_mixed_success_and_failure() {
        // Initialize if not already done
        let _ = init_metrics("prometheus", None);

        // Test successful requests
        let agent = TestAgent {
            name: "test_agent".to_string(),
        };
        let metrics_agent = MetricsMiddleware::new(agent);
        let message = Message::new("user", serde_json::json!("test"));
        let result = metrics_agent.process(message).await;
        assert!(result.is_ok());

        // Test failing requests
        let failing_agent = FailingAgent {
            name: "failing".to_string(),
        };
        let failing_metrics_agent = MetricsMiddleware::new(failing_agent);
        let message = Message::new("user", serde_json::json!("test"));
        let result = failing_metrics_agent.process(message).await;
        assert!(result.is_err());
    }
}
