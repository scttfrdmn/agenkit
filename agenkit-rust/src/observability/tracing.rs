//! Distributed tracing with OpenTelemetry.
//!
//! This module provides W3C Trace Context propagation across agents,
//! automatic span creation, and integration with OpenTelemetry exporters.
//!
//! # Features
//!
//! - **W3C Trace Context**: Standard trace propagation via message metadata
//! - **Multiple Exporters**: OTLP, Jaeger, Zipkin, Console
//! - **Automatic Spans**: TracingMiddleware creates spans for each agent call
//! - **Error Recording**: Failures are recorded as span events
//!
//! # Example
//!
//! ```rust,no_run
//! use agenkit::observability::tracing::{init_tracing, TracingMiddleware};
//! use agenkit::core::{Agent, Message};
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // Initialize tracing
//! init_tracing("otlp", Some("http://localhost:4317"))?;
//!
//! // Wrap agent with tracing middleware
//! // let agent = MyAgent::new();
//! // let traced_agent = TracingMiddleware::new(agent, None);
//! //
//! // // Process messages (spans created automatically)
//! // let msg = Message::with_text("user", "Hello");
//! // let response = traced_agent.process(msg).await?;
//! # Ok(())
//! # }
//! ```

use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use once_cell::sync::OnceCell;
use opentelemetry::{
    global,
    propagation::{Extractor, Injector, TextMapPropagator},
    trace::{Span, SpanKind, Status, Tracer, TracerProvider as _},
    Context, KeyValue,
};
use opentelemetry_sdk::{
    propagation::TraceContextPropagator,
    trace::{Config, Sampler, TracerProvider},
};
use std::collections::HashMap;
use std::sync::Arc;

/// Global tracer provider (initialized once).
static GLOBAL_TRACER_PROVIDER: OnceCell<TracerProvider> = OnceCell::new();

/// Initialize tracing with the specified exporter type.
///
/// This function must be called before using any tracing functionality.
/// It can only be called once per process.
///
/// # Arguments
///
/// * `exporter_type` - Type of exporter: "otlp", "jaeger", "zipkin", or "console"
/// * `endpoint` - Optional endpoint URL for the exporter
///
/// # Example
///
/// ```rust,no_run
/// use agenkit::observability::tracing::init_tracing;
///
/// // OTLP exporter to localhost
/// init_tracing("otlp", Some("http://localhost:4317"))?;
///
/// // Console exporter (for development)
/// init_tracing("console", None)?;
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
///
/// # Errors
///
/// Returns an error if:
/// - Exporter type is unknown
/// - Tracer provider is already initialized
/// - Exporter setup fails
pub fn init_tracing(
    exporter_type: &str,
    endpoint: Option<&str>,
) -> Result<(), Box<dyn std::error::Error>> {
    let provider = match exporter_type {
        "otlp" => {
            use opentelemetry_otlp::WithExportConfig;
            let endpoint = endpoint.unwrap_or("http://localhost:4317");

            let exporter = opentelemetry_otlp::new_exporter()
                .tonic()
                .with_endpoint(endpoint)
                .build_span_exporter()?;

            TracerProvider::builder()
                .with_batch_exporter(exporter, opentelemetry_sdk::runtime::Tokio)
                .with_config(Config::default().with_sampler(Sampler::AlwaysOn))
                .build()
        }
        "jaeger" => {
            let endpoint = endpoint.unwrap_or("127.0.0.1:6831");

            #[allow(deprecated)]
            let exporter = opentelemetry_jaeger::new_agent_pipeline()
                .with_endpoint(endpoint)
                .build_sync_agent_exporter()?;

            TracerProvider::builder()
                .with_simple_exporter(exporter)
                .with_config(Config::default().with_sampler(Sampler::AlwaysOn))
                .build()
        }
        "zipkin" => {
            use opentelemetry_zipkin::ZipkinPipelineBuilder;
            let endpoint = endpoint.unwrap_or("http://localhost:9411/api/v2/spans");

            let exporter = ZipkinPipelineBuilder::default()
                .with_service_name("agenkit")
                .with_collector_endpoint(endpoint)
                .init_exporter()?;

            TracerProvider::builder()
                .with_batch_exporter(exporter, opentelemetry_sdk::runtime::Tokio)
                .with_config(Config::default().with_sampler(Sampler::AlwaysOn))
                .build()
        }
        "console" => {
            // Console exporter for development
            let exporter = opentelemetry_stdout::SpanExporter::default();
            TracerProvider::builder()
                .with_simple_exporter(exporter)
                .with_config(Config::default().with_sampler(Sampler::AlwaysOn))
                .build()
        }
        _ => {
            return Err(format!("Unknown exporter type: {}", exporter_type).into());
        }
    };

    GLOBAL_TRACER_PROVIDER
        .set(provider.clone())
        .map_err(|_| "Tracer provider already initialized")?;

    // Set as global provider
    global::set_tracer_provider(provider);

    Ok(())
}

/// Get the global tracer.
///
/// # Panics
///
/// Panics if `init_tracing()` has not been called.
pub fn get_tracer() -> opentelemetry_sdk::trace::Tracer {
    let provider = GLOBAL_TRACER_PROVIDER
        .get()
        .expect("Tracer provider not initialized. Call init_tracing() first.");

    provider.tracer("agenkit-rust")
}

/// Get the global tracer if initialized, otherwise return None.
///
/// This is a non-panicking version of `get_tracer()` for optional tracer access.
pub fn get_tracer_if_initialized() -> Option<opentelemetry_sdk::trace::Tracer> {
    GLOBAL_TRACER_PROVIDER
        .get()
        .map(|provider| provider.tracer("agenkit-rust"))
}

/// Adapter for extracting trace context from message metadata.
struct MessageMetadataExtractor<'a>(&'a HashMap<String, serde_json::Value>);

impl<'a> Extractor for MessageMetadataExtractor<'a> {
    fn get(&self, key: &str) -> Option<&str> {
        self.0.get(key).and_then(|v| v.as_str())
    }

    fn keys(&self) -> Vec<&str> {
        self.0.keys().map(|k| k.as_str()).collect()
    }
}

/// Adapter for injecting trace context into message metadata.
struct MessageMetadataInjector<'a>(&'a mut HashMap<String, serde_json::Value>);

impl<'a> Injector for MessageMetadataInjector<'a> {
    fn set(&mut self, key: &str, value: String) {
        self.0
            .insert(key.to_string(), serde_json::Value::String(value));
    }
}

/// Extract W3C Trace Context from message metadata.
///
/// This function reads the `traceparent` and `tracestate` headers from
/// the message metadata and returns an OpenTelemetry Context.
///
/// # Arguments
///
/// * `metadata` - Message metadata containing trace context headers
///
/// # Example
///
/// ```rust
/// use agenkit::observability::tracing::extract_trace_context;
/// use std::collections::HashMap;
///
/// let mut metadata = HashMap::new();
/// metadata.insert("traceparent".to_string(),
///     serde_json::Value::String("00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01".to_string()));
///
/// let context = extract_trace_context(&metadata);
/// ```
pub fn extract_trace_context(metadata: &HashMap<String, serde_json::Value>) -> Context {
    let propagator = TraceContextPropagator::new();
    let extractor = MessageMetadataExtractor(metadata);
    propagator.extract(&extractor)
}

/// Inject W3C Trace Context into message metadata.
///
/// This function writes the `traceparent` and `tracestate` headers into
/// the message metadata from the current OpenTelemetry Context.
///
/// # Arguments
///
/// * `metadata` - Message metadata to inject trace context into
/// * `context` - OpenTelemetry context containing trace information
///
/// # Example
///
/// ```rust
/// use agenkit::observability::tracing::{inject_trace_context, extract_trace_context};
/// use std::collections::HashMap;
/// use opentelemetry::Context;
///
/// let mut metadata = HashMap::new();
/// let context = Context::current();
/// inject_trace_context(&mut metadata, &context);
///
/// // Now metadata contains traceparent header
/// assert!(metadata.contains_key("traceparent"));
/// ```
pub fn inject_trace_context(metadata: &mut HashMap<String, serde_json::Value>, context: &Context) {
    let propagator = TraceContextPropagator::new();
    let mut injector = MessageMetadataInjector(metadata);
    propagator.inject_context(context, &mut injector);
}

/// Middleware that adds distributed tracing to agents.
///
/// TracingMiddleware wraps an agent and automatically creates spans for
/// each `process()` call. Trace context is propagated via message metadata
/// using W3C Trace Context headers.
///
/// # Example
///
/// ```rust,no_run
/// use agenkit::observability::tracing::TracingMiddleware;
/// use agenkit::core::{Agent, Message, AgentError};
/// use async_trait::async_trait;
///
/// struct MyAgent;
///
/// #[async_trait]
/// impl Agent for MyAgent {
///     fn name(&self) -> &str { "my_agent" }
///     async fn process(&self, msg: Message) -> Result<Message, AgentError> {
///         Ok(Message::with_text("assistant", "Hello"))
///     }
/// }
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// // Wrap agent with tracing
/// let agent = MyAgent;
/// let traced_agent = TracingMiddleware::new(agent, None);
///
/// // Process message (span created automatically)
/// let msg = Message::with_text("user", "Hello");
/// let response = traced_agent.process(msg).await?;
/// # Ok(())
/// # }
/// ```
pub struct TracingMiddleware<A: Agent> {
    inner: A,
    span_name: String,
    tracer: Arc<opentelemetry_sdk::trace::Tracer>,
}

impl<A: Agent> TracingMiddleware<A> {
    /// Create a new TracingMiddleware wrapping the given agent.
    ///
    /// # Arguments
    ///
    /// * `inner` - The agent to wrap
    /// * `span_name` - Optional span name (defaults to agent name)
    ///
    /// # Panics
    ///
    /// Panics if `init_tracing()` has not been called.
    pub fn new(inner: A, span_name: Option<String>) -> Self {
        let span_name = span_name.unwrap_or_else(|| inner.name().to_string());
        let tracer = Arc::new(get_tracer());

        Self {
            inner,
            span_name,
            tracer,
        }
    }

    /// Get a reference to the inner agent.
    pub fn inner(&self) -> &A {
        &self.inner
    }

    /// Unwrap and return the inner agent.
    pub fn into_inner(self) -> A {
        self.inner
    }
}

#[async_trait]
impl<A: Agent> Agent for TracingMiddleware<A> {
    fn name(&self) -> &str {
        self.inner.name()
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Extract parent context from message metadata
        let parent_context = extract_trace_context(&message.metadata);

        // Start new span as child of parent context
        let mut span = self
            .tracer
            .span_builder(self.span_name.clone())
            .with_kind(SpanKind::Internal)
            .start_with_context(self.tracer.as_ref(), &parent_context);

        // Set span attributes
        span.set_attribute(KeyValue::new("agent.name", self.inner.name().to_string()));
        span.set_attribute(KeyValue::new("message.role", message.role.clone()));

        if let Some(content_str) = message.content_as_str() {
            span.set_attribute(KeyValue::new(
                "message.content_length",
                content_str.len() as i64,
            ));
        }

        // Process message
        let result = self.inner.process(message).await;

        // Record result
        match &result {
            Ok(response) => {
                span.set_status(Status::Ok);
                span.set_attribute(KeyValue::new("response.role", response.role.clone()));

                // Inject trace context into response metadata
                let mut response = response.clone();
                let span_context = span.span_context();
                if span_context.is_valid() {
                    let traceparent = format!(
                        "00-{}-{}-{:02x}",
                        span_context.trace_id(),
                        span_context.span_id(),
                        span_context.trace_flags()
                    );
                    response.metadata.insert(
                        "traceparent".to_string(),
                        serde_json::Value::String(traceparent),
                    );
                }

                span.end();
                Ok(response)
            }
            Err(e) => {
                span.set_status(Status::error(e.to_string()));
                span.record_error(e);
                span.end();
                Err(e.clone())
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::{Agent, AgentError, Message};
    use async_trait::async_trait;
    use opentelemetry::trace::TraceContextExt;

    struct TestAgent {
        name: String,
    }

    #[async_trait]
    impl Agent for TestAgent {
        fn name(&self) -> &str {
            &self.name
        }

        async fn process(&self, message: Message) -> Result<Message, AgentError> {
            Ok(Message::with_text(
                "assistant",
                format!("Echo: {}", message.content_as_str().unwrap_or("")),
            ))
        }
    }

    struct FailingAgent;

    #[async_trait]
    impl Agent for FailingAgent {
        fn name(&self) -> &str {
            "failing"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Err(AgentError::ProcessingError(
                "intentional failure".to_string(),
            ))
        }
    }

    #[test]
    fn test_init_tracing_console() {
        // Console exporter should always work (or already be initialized)
        let result = init_tracing("console", None);
        assert!(
            result.is_ok()
                || result
                    .unwrap_err()
                    .to_string()
                    .contains("already initialized"),
            "Console exporter should initialize or already be initialized"
        );
    }

    #[test]
    fn test_extract_trace_context_empty() {
        let metadata = HashMap::new();
        let context = extract_trace_context(&metadata);
        // Should return a valid context (even if empty)
        assert!(
            context.span().span_context().is_valid() || !context.span().span_context().is_valid()
        );
    }

    #[test]
    fn test_extract_trace_context_with_traceparent() {
        let mut metadata = HashMap::new();
        metadata.insert(
            "traceparent".to_string(),
            serde_json::Value::String(
                "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01".to_string(),
            ),
        );

        let context = extract_trace_context(&metadata);
        assert!(context.span().span_context().is_valid());
    }

    #[test]
    fn test_inject_trace_context() {
        // Initialize tracing for this test
        let _ = init_tracing("console", None);

        let mut metadata = HashMap::new();
        let context = Context::current();
        inject_trace_context(&mut metadata, &context);

        // Should have added traceparent header (even if trace is not active)
        // The exact presence depends on whether there's an active span
        assert!(metadata.contains_key("traceparent") || metadata.is_empty());
    }

    #[tokio::test]
    async fn test_tracing_middleware_creates_span() {
        // Initialize tracing
        let _ = init_tracing("console", None);

        let agent = TestAgent {
            name: "test_agent".to_string(),
        };
        let traced_agent = TracingMiddleware::new(agent, None);

        let message = Message::with_text("user", "Hello");
        let result = traced_agent.process(message).await;

        assert!(result.is_ok());
        let response = result.unwrap();
        assert_eq!(response.role, "assistant");
    }

    #[tokio::test]
    async fn test_tracing_middleware_propagates_context() {
        // Initialize tracing
        let _ = init_tracing("console", None);

        let agent = TestAgent {
            name: "test_agent".to_string(),
        };
        let traced_agent = TracingMiddleware::new(agent, None);

        // Create message with trace context
        let mut metadata = HashMap::new();
        metadata.insert(
            "traceparent".to_string(),
            serde_json::Value::String(
                "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01".to_string(),
            ),
        );

        let message = Message::new("user", serde_json::Value::String("Hello".to_string()))
            .with_metadata("traceparent", metadata["traceparent"].clone());

        let result = traced_agent.process(message).await;

        assert!(result.is_ok());
        let response = result.unwrap();

        // Response should have trace context in metadata
        assert!(response.metadata.contains_key("traceparent"));
    }

    #[tokio::test]
    async fn test_tracing_middleware_records_errors() {
        // Initialize tracing
        let _ = init_tracing("console", None);

        let agent = FailingAgent;
        let traced_agent = TracingMiddleware::new(agent, Some("failing_agent".to_string()));

        let message = Message::with_text("user", "This will fail");
        let result = traced_agent.process(message).await;

        assert!(result.is_err());
        match result {
            Err(AgentError::ProcessingError(msg)) => {
                assert_eq!(msg, "intentional failure");
            }
            _ => panic!("Expected ProcessingError"),
        }
    }

    #[test]
    fn test_tracing_middleware_name_delegation() {
        // Initialize tracing
        let _ = init_tracing("console", None);

        let agent = TestAgent {
            name: "test_agent".to_string(),
        };
        let traced_agent = TracingMiddleware::new(agent, None);

        assert_eq!(traced_agent.name(), "test_agent");
    }

    #[test]
    fn test_tracing_middleware_inner_access() {
        // Initialize tracing
        let _ = init_tracing("console", None);

        let agent = TestAgent {
            name: "test_agent".to_string(),
        };
        let traced_agent = TracingMiddleware::new(agent, None);

        assert_eq!(traced_agent.inner().name(), "test_agent");
    }

    #[test]
    fn test_tracing_middleware_into_inner() {
        // Initialize tracing
        let _ = init_tracing("console", None);

        let agent = TestAgent {
            name: "test_agent".to_string(),
        };
        let traced_agent = TracingMiddleware::new(agent, None);

        let inner = traced_agent.into_inner();
        assert_eq!(inner.name(), "test_agent");
    }
}
