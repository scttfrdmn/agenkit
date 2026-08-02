//! Metrics collection with Prometheus and OTLP exporters.
//!
//! Provides automatic request counting, duration tracking, and MetricsMiddleware
//! for instrumenting agent performance.
//!
//! # Example
//!
//! ```rust,no_run
//! use agenkit::observability::{init_metrics, MetricsMiddleware};
//! use agenkit::core::{Agent, Message};
//!
//! # struct MyAgent;
//! # #[async_trait::async_trait]
//! # impl Agent for MyAgent {
//! #     fn name(&self) -> &str { "test" }
//! #     async fn process(&self, msg: Message) -> Result<Message, agenkit::core::AgentError> { Ok(msg) }
//! # }
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // Initialize metrics with the OTLP exporter
//! init_metrics("otlp", Some("http://localhost:4317"))?;
//!
//! // Wrap agent with metrics
//! let agent = MyAgent;
//! let metrics_agent = MetricsMiddleware::new(agent);
//!
//! // Process message - metrics recorded automatically
//! let message = Message::with_text("user", "Hello");
//! let response = metrics_agent.process(message).await?;
//! # Ok(())
//! # }
//! ```

use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use once_cell::sync::OnceCell;
use opentelemetry::{
    metrics::{Counter, Histogram, Meter},
    KeyValue,
};
use opentelemetry_otlp::WithExportConfig;
use opentelemetry_sdk::metrics::{PeriodicReader, SdkMeterProvider};
use std::time::{Duration, Instant};

/// Global meter provider instance.
static METER_PROVIDER: OnceCell<SdkMeterProvider> = OnceCell::new();

/// How often the periodic reader exports.
///
/// Matches the OTel spec default for `OTEL_METRIC_EXPORT_INTERVAL`. Stated
/// explicitly so the delivery latency is visible here rather than inherited.
const EXPORT_INTERVAL: Duration = Duration::from_secs(60);

/// Initialize metrics collection with OpenTelemetry.
///
/// Sets up a global meter provider with the specified exporter type.
/// This must be called before creating any MetricsMiddleware instances.
///
/// # Supported Exporters
///
/// - `"otlp"` - OTLP gRPC exporter. Uses `endpoint` when given; otherwise defers
///   to the exporter's own resolution of `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`,
///   then `OTEL_EXPORTER_OTLP_ENDPOINT`, then the spec default.
/// - `"stdout"` - Console exporter, for debugging.
///
/// `"prometheus"` is **rejected**. The `opentelemetry-prometheus` and
/// `prometheus` crates were removed from `Cargo.toml` because they pulled in
/// vulnerable transitive dependencies (thrift, protobuf 2.x), so there is no
/// exporter to install. Returning an error is deliberate: this function used to
/// accept `"prometheus"` and return `Ok(())` while exporting nothing, which is
/// strictly worse than failing — a scrape endpoint that never appears looks
/// identical to a misconfigured scrape target. Use `"otlp"` and let a collector
/// expose Prometheus.
///
/// # Arguments
///
/// * `exporter_type` - Type of exporter to use
/// * `endpoint` - Optional endpoint URL; only meaningful for `"otlp"`
///
/// # Shutdown
///
/// The reader exports on an interval, so metrics recorded shortly before exit
/// are only delivered if [`shutdown_metrics`] runs. Prefer
/// [`shutdown_observability`](super::shutdown_observability).
///
/// # Example
///
/// ```rust,no_run
/// # use agenkit::observability::init_metrics;
/// // OTLP exporter
/// init_metrics("otlp", Some("http://localhost:4317"))?;
///
/// // Console exporter (debugging)
/// init_metrics("stdout", None)?;
/// # Ok::<(), agenkit::core::AgentError>(())
/// ```
pub fn init_metrics(exporter_type: &str, endpoint: Option<&str>) -> Result<(), AgentError> {
    let builder = SdkMeterProvider::builder();

    // A PeriodicReader is what actually exports. The previous implementation
    // installed no reader at all and returned Ok(()) for every exporter type,
    // so nothing was ever exported for any configuration (#772).
    //
    // The interval is set explicitly rather than left at the SDK default: the
    // reader spawns a thread that exports on a timer, and a long default turns
    // "metrics are missing" into "metrics are late", which is much harder to
    // diagnose from the consumer side.
    let builder = match exporter_type {
        "stdout" => {
            let exporter = opentelemetry_stdout::MetricExporter::default();
            builder.with_reader(
                PeriodicReader::builder(exporter)
                    .with_interval(EXPORT_INTERVAL)
                    .build(),
            )
        }
        "otlp" => {
            let mut exporter_builder = opentelemetry_otlp::MetricExporter::builder().with_tonic();
            // Only set the endpoint when we have one: an explicit value
            // overrides the environment, so passing an empty string would
            // suppress OTEL_EXPORTER_OTLP_ENDPOINT rather than defer to it.
            if let Some(endpoint) = endpoint.filter(|e| !e.is_empty()) {
                exporter_builder = exporter_builder.with_endpoint(endpoint);
            }
            let exporter = exporter_builder.build().map_err(|e| {
                AgentError::ProcessingError(format!("failed to build OTLP metric exporter: {}", e))
            })?;
            builder.with_reader(
                PeriodicReader::builder(exporter)
                    .with_interval(EXPORT_INTERVAL)
                    .build(),
            )
        }
        "prometheus" => {
            return Err(AgentError::ProcessingError(
                "the prometheus metrics exporter is not available in this build \
                 (opentelemetry-prometheus was removed over vulnerable transitive \
                 dependencies); use \"otlp\" and expose Prometheus from a collector"
                    .to_string(),
            ))
        }
        _ => {
            return Err(AgentError::ProcessingError(format!(
                "Unsupported exporter type: {}",
                exporter_type
            )))
        }
    };

    let provider = builder.build();

    // Set global meter provider
    opentelemetry::global::set_meter_provider(provider.clone());

    // Store in global for cleanup (ignore if already set)
    let _ = METER_PROVIDER.set(provider);

    Ok(())
}

/// Get a meter instance from the global provider.
///
/// This function retrieves a meter from the currently configured global
/// meter provider. It will return a no-op meter if `init_metrics()` has
/// not been called.
///
/// # Arguments
///
/// * `name` - Name for the meter (typically "agenkit.observability")
pub fn get_meter(name: &'static str) -> Meter {
    opentelemetry::global::meter(name)
}

/// MetricsMiddleware wraps an agent to add metrics collection.
///
/// This middleware automatically:
/// - Counts total requests with status labels (success/error)
/// - Records request duration in seconds
/// - Labels metrics with agent name
///
/// # Metrics Collected
///
/// - `agent_requests_total` (counter) - Total number of requests, labeled by agent_name and status
/// - `agent_request_duration_seconds` (histogram) - Request duration distribution
///
/// # Example
///
/// ```rust,no_run
/// # use agenkit::observability::{init_metrics, MetricsMiddleware};
/// # use agenkit::core::{Agent, Message};
/// # struct MyAgent;
/// # #[async_trait::async_trait]
/// # impl Agent for MyAgent {
/// #     fn name(&self) -> &str { "test" }
/// #     async fn process(&self, msg: Message) -> Result<Message, agenkit::core::AgentError> { Ok(msg) }
/// # }
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// init_metrics("otlp", Some("http://localhost:4317"))?;
///
/// let agent = MyAgent;
/// let metrics_agent = MetricsMiddleware::new(agent);
///
/// let message = Message::with_text("user", "test");
/// let response = metrics_agent.process(message).await?;
/// # Ok(())
/// # }
/// ```
pub struct MetricsMiddleware<A: Agent> {
    inner: A,
    requests_total: Counter<u64>,
    request_duration: Histogram<f64>,
    agent_name: String,
}

impl<A: Agent> MetricsMiddleware<A> {
    /// Create new metrics middleware.
    ///
    /// # Arguments
    ///
    /// * `agent` - The agent to wrap with metrics collection
    ///
    /// # Example
    ///
    /// ```rust
    /// # use agenkit::observability::MetricsMiddleware;
    /// # use agenkit::core::{Agent, Message};
    /// # struct MyAgent;
    /// # #[async_trait::async_trait]
    /// # impl Agent for MyAgent {
    /// #     fn name(&self) -> &str { "test" }
    /// #     async fn process(&self, msg: Message) -> Result<Message, agenkit::core::AgentError> { Ok(msg) }
    /// # }
    /// let agent = MyAgent;
    /// let metrics_agent = MetricsMiddleware::new(agent);
    /// ```
    pub fn new(agent: A) -> Self {
        let meter = get_meter("agenkit.observability");
        let agent_name = agent.name().to_string();

        // Create counter for total requests (0.32 renamed .init() -> .build())
        let requests_total = meter
            .u64_counter("agent_requests_total")
            .with_description("Total number of agent requests")
            .build();

        // Create histogram for request duration
        let request_duration = meter
            .f64_histogram("agent_request_duration_seconds")
            .with_description("Agent request duration in seconds")
            .build();

        Self {
            inner: agent,
            requests_total,
            request_duration,
            agent_name,
        }
    }
}

#[async_trait]
impl<A: Agent + Send + Sync> Agent for MetricsMiddleware<A> {
    fn name(&self) -> &str {
        self.inner.name()
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let start = Instant::now();

        // Process message
        let result = self.inner.process(message).await;

        // Record duration
        let duration = start.elapsed().as_secs_f64();
        self.request_duration.record(
            duration,
            &[KeyValue::new("agent_name", self.agent_name.clone())],
        );

        // Record request count with status
        let status = if result.is_ok() { "success" } else { "error" };
        self.requests_total.add(
            1,
            &[
                KeyValue::new("agent_name", self.agent_name.clone()),
                KeyValue::new("status", status),
            ],
        );

        result
    }
}

/// Shutdown the global meter provider.
///
/// This should be called before application exit to ensure all metrics are
/// flushed to the exporter.
pub fn shutdown_metrics() {
    if let Some(provider) = METER_PROVIDER.get() {
        let _ = provider.shutdown();
    }
}
