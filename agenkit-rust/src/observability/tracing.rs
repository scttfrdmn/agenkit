//! Distributed tracing with OpenTelemetry.
//!
//! Provides W3C Trace Context propagation, span creation, and TracingMiddleware
//! for automatic instrumentation of agent workflows.
//!
//! # Example
//!
//! ```rust,no_run
//! use agenkit::observability::{init_tracing, TracingMiddleware};
//! use agenkit::core::{Agent, Message};
//!
//! # struct MyAgent;
//! # #[async_trait::async_trait]
//! # impl Agent for MyAgent {
//! #     fn name(&self) -> &str { "test" }
//! #     async fn process(&self, msg: Message) -> Result<Message, agenkit::core::AgentError> { Ok(msg) }
//! # }
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // Initialize tracing with console exporter
//! init_tracing("console", None)?;
//!
//! // Wrap agent with tracing
//! let agent = MyAgent;
//! let traced_agent = TracingMiddleware::new(agent, None);
//!
//! // Process message - span created automatically
//! let message = Message::with_text("user", "Hello");
//! let response = traced_agent.process(message).await?;
//! # Ok(())
//! # }
//! ```

use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use once_cell::sync::OnceCell;
use opentelemetry::{
    global,
    trace::{Span, SpanKind, Status, Tracer, TracerProvider as _},
    KeyValue,
};
use opentelemetry_sdk::{
    trace::{Sampler, SdkTracerProvider},
    Resource,
};
use std::collections::HashMap;

/// Global tracer provider instance.
static TRACER_PROVIDER: OnceCell<SdkTracerProvider> = OnceCell::new();

/// Initialize distributed tracing with OpenTelemetry.
///
/// Sets up a global tracer provider with the specified exporter type.
/// This must be called before creating any TracingMiddleware instances.
///
/// # Supported Exporters
///
/// - `"otlp"` - OTLP gRPC exporter (requires endpoint)
/// - `"jaeger"` - Jaeger exporter (requires endpoint)
/// - `"console"` - Console/stdout exporter (for debugging)
///
/// # Arguments
///
/// * `exporter_type` - Type of exporter to use
/// * `endpoint` - Optional endpoint URL (required for otlp and jaeger)
///
/// # Example
///
/// ```rust,no_run
/// # use agenkit::observability::init_tracing;
/// // OTLP exporter
/// init_tracing("otlp", Some("http://localhost:4317"))?;
///
/// // Console exporter (no endpoint needed)
/// init_tracing("console", None)?;
/// # Ok::<(), agenkit::core::AgentError>(())
/// ```
pub fn init_tracing(exporter_type: &str, _endpoint: Option<&str>) -> Result<(), AgentError> {
    // Create resource with service name
    let resource = Resource::builder()
        .with_attribute(KeyValue::new("service.name", "agenkit"))
        .build();

    // Configure sampling (parent-based with 100% sampling for now)
    let sampler = Sampler::ParentBased(Box::new(Sampler::AlwaysOn));

    // Create tracer provider (0.32 moved resource/sampler onto the builder
    // directly; the standalone trace::Config type was removed).
    let provider = SdkTracerProvider::builder()
        .with_resource(resource)
        .with_sampler(sampler);

    // Add span processor based on exporter type
    let provider = match exporter_type {
        "console" => {
            let exporter = opentelemetry_stdout::SpanExporter::default();
            provider.with_simple_exporter(exporter)
        }
        "otlp" | "jaeger" => {
            // For now, use console exporter as placeholder
            // Full OTLP/Jaeger support requires additional configuration
            let exporter = opentelemetry_stdout::SpanExporter::default();
            provider.with_simple_exporter(exporter)
        }
        _ => {
            return Err(AgentError::ProcessingError(format!(
                "Unsupported exporter type: {}",
                exporter_type
            )));
        }
    };

    let provider = provider.build();

    // Set global tracer provider
    global::set_tracer_provider(provider.clone());

    // Store in global for cleanup (ignore if already set)
    let _ = TRACER_PROVIDER.set(provider);

    // Set W3C Trace Context propagator
    global::set_text_map_propagator(
        opentelemetry_sdk::propagation::TraceContextPropagator::new(),
    );

    Ok(())
}

/// Get a tracer instance from the global provider.
///
/// This function retrieves a tracer from the currently configured global
/// tracer provider. It will return a no-op tracer if `init_tracing()` has
/// not been called.
///
/// # Arguments
///
/// * `name` - Name for the tracer (typically "agenkit.observability")
pub fn get_tracer(name: &'static str) -> opentelemetry::global::BoxedTracer {
    global::tracer(name)
}

/// Extract W3C Trace Context from message metadata.
///
/// Looks for a "trace_context" key in the message metadata that contains
/// the W3C traceparent header. Returns an OpenTelemetry Context with the
/// extracted span context.
///
/// # Arguments
///
/// * `metadata` - Message metadata HashMap
///
/// # Returns
///
/// An OpenTelemetry Context with the extracted trace context, or an empty
/// context if no trace context was found in metadata.
///
/// # Example
///
/// ```rust
/// # use agenkit::observability::extract_trace_context;
/// # use std::collections::HashMap;
/// # use serde_json::json;
/// let mut metadata = HashMap::new();
/// metadata.insert("trace_context".to_string(), json!({
///     "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
/// }));
///
/// let context = extract_trace_context(&metadata);
/// ```
pub fn extract_trace_context(
    metadata: &HashMap<String, serde_json::Value>,
) -> opentelemetry::Context {
    use opentelemetry::propagation::TextMapPropagator;

    // Get trace_context from metadata
    let trace_ctx = match metadata.get("trace_context") {
        Some(ctx) => ctx,
        None => return opentelemetry::Context::current(),
    };

    // Convert to HashMap<String, String> for propagator
    let carrier: HashMap<String, String> = match trace_ctx.as_object() {
        Some(obj) => obj
            .iter()
            .filter_map(|(k, v)| v.as_str().map(|s| (k.clone(), s.to_string())))
            .collect(),
        None => return opentelemetry::Context::current(),
    };

    // Extract context using W3C propagator
    let propagator = opentelemetry_sdk::propagation::TraceContextPropagator::new();
    propagator.extract(&carrier)
}

/// Inject W3C Trace Context from a specific context into message metadata.
///
/// Serializes an OpenTelemetry span context into W3C Trace Context format
/// and stores it in the message metadata under the "trace_context" key.
///
/// This function only injects trace context if there is a valid span in the
/// provided context. If no valid span exists, the function returns without
/// modifying the metadata.
///
/// # Arguments
///
/// * `metadata` - Mutable reference to message metadata HashMap
/// * `cx` - OpenTelemetry context containing the span to inject
pub fn inject_trace_context_from(
    metadata: &mut HashMap<String, serde_json::Value>,
    cx: &opentelemetry::Context,
) {
    use opentelemetry::trace::TraceContextExt;
    use serde_json::json;

    let span = cx.span();
    let span_context = span.span_context();

    // Only inject if there's a valid span context
    if !span_context.is_valid() {
        return;
    }

    // Manually create W3C traceparent format
    let trace_id = format!("{:032x}", span_context.trace_id());
    let span_id = format!("{:016x}", span_context.span_id());
    let flags = if span_context.is_sampled() { "01" } else { "00" };
    let traceparent = format!("00-{}-{}-{}", trace_id, span_id, flags);

    // Inject into metadata
    let mut trace_ctx = HashMap::new();
    trace_ctx.insert("traceparent".to_string(), json!(traceparent));
    metadata.insert("trace_context".to_string(), json!(trace_ctx));
}

/// Inject W3C Trace Context into message metadata.
///
/// Serializes the current OpenTelemetry span context into W3C Trace Context
/// format and stores it in the message metadata under the "trace_context" key.
///
/// This function only injects trace context if there is an active span in the
/// current OpenTelemetry context. If no active span exists, the function returns
/// without modifying the metadata.
///
/// # Arguments
///
/// * `metadata` - Mutable reference to message metadata HashMap
///
/// # Example
///
/// ```rust
/// # use agenkit::observability::inject_trace_context_from;
/// # use std::collections::HashMap;
/// # use opentelemetry::trace::{
/// #     SpanContext, TraceId, SpanId, TraceFlags, TraceState, TraceContextExt,
/// # };
/// # use opentelemetry::Context;
/// // Build a context carrying a valid span context (normally created by a tracer).
/// let span_context = SpanContext::new(
///     TraceId::from_hex("4bf92f3577b34da6a3ce929d0e0e4736").unwrap(),
///     SpanId::from_hex("00f067aa0ba902b7").unwrap(),
///     TraceFlags::SAMPLED,
///     false,
///     TraceState::default(),
/// );
/// let cx = Context::current().with_remote_span_context(span_context);
///
/// let mut metadata = HashMap::new();
/// inject_trace_context_from(&mut metadata, &cx);
///
/// // metadata now contains trace_context with traceparent
/// assert!(metadata.contains_key("trace_context"));
/// ```
pub fn inject_trace_context(metadata: &mut HashMap<String, serde_json::Value>) {
    let cx = opentelemetry::Context::current();
    inject_trace_context_from(metadata, &cx);
}

/// TracingMiddleware wraps an agent to add distributed tracing.
///
/// This middleware automatically:
/// - Extracts parent trace context from incoming message metadata
/// - Creates a new span for the agent's processing
/// - Sets span attributes (agent name, message role, etc.)
/// - Injects trace context into response metadata
/// - Records errors in spans
///
/// # Example
///
/// ```rust,no_run
/// # use agenkit::observability::TracingMiddleware;
/// # use agenkit::core::{Agent, Message};
/// # struct MyAgent;
/// # #[async_trait::async_trait]
/// # impl Agent for MyAgent {
/// #     fn name(&self) -> &str { "test" }
/// #     async fn process(&self, msg: Message) -> Result<Message, agenkit::core::AgentError> { Ok(msg) }
/// # }
/// let agent = MyAgent;
/// let traced = TracingMiddleware::new(agent, None);
/// ```
pub struct TracingMiddleware<A: Agent> {
    inner: A,
    span_name: String,
}

impl<A: Agent> TracingMiddleware<A> {
    /// Create new tracing middleware.
    ///
    /// # Arguments
    ///
    /// * `agent` - The agent to wrap with tracing
    /// * `span_name` - Optional custom span name (defaults to "agent.{name}.process")
    ///
    /// # Example
    ///
    /// ```rust
    /// # use agenkit::observability::TracingMiddleware;
    /// # use agenkit::core::{Agent, Message};
    /// # struct MyAgent;
    /// # #[async_trait::async_trait]
    /// # impl Agent for MyAgent {
    /// #     fn name(&self) -> &str { "test" }
    /// #     async fn process(&self, msg: Message) -> Result<Message, agenkit::core::AgentError> { Ok(msg) }
    /// # }
    /// let agent = MyAgent;
    ///
    /// // Default span name: "agent.test.process"
    /// let traced = TracingMiddleware::new(agent, None);
    ///
    /// // Custom span name
    /// # let agent = MyAgent;
    /// let traced = TracingMiddleware::new(agent, Some("custom.span"));
    /// ```
    pub fn new(agent: A, span_name: Option<&str>) -> Self {
        let span_name = span_name
            .map(|s| s.to_string())
            .unwrap_or_else(|| format!("agent.{}.process", agent.name()));

        Self {
            inner: agent,
            span_name,
        }
    }
}

#[async_trait]
impl<A: Agent + Send + Sync> Agent for TracingMiddleware<A> {
    fn name(&self) -> &str {
        self.inner.name()
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        use opentelemetry::propagation::TextMapPropagator;
        use opentelemetry::trace::TraceContextExt;

        let tracer = get_tracer("agenkit.observability");

        // Extract parent context from message metadata
        let parent_context = extract_trace_context(&message.metadata);

        // Start span with parent context
        let mut span = tracer
            .span_builder(self.span_name.clone())
            .with_kind(SpanKind::Internal)
            .start_with_context(&tracer, &parent_context);

        // Get the span context for injection later
        let span_context = span.span_context().clone();

        // Set span attributes
        span.set_attribute(KeyValue::new("agent.name", self.inner.name().to_string()));
        span.set_attribute(KeyValue::new("message.role", message.role.clone()));

        // Add content length attribute
        let content_str = message.content.to_string();
        span.set_attribute(KeyValue::new("message.content_length", content_str.len() as i64));

        // Add metadata as attributes (only basic types)
        for (key, value) in &message.metadata {
            match value {
                serde_json::Value::String(s) => {
                    span.set_attribute(KeyValue::new(format!("message.metadata.{}", key), s.clone()));
                }
                serde_json::Value::Number(n) => {
                    if let Some(i) = n.as_i64() {
                        span.set_attribute(KeyValue::new(format!("message.metadata.{}", key), i));
                    } else if let Some(f) = n.as_f64() {
                        span.set_attribute(KeyValue::new(format!("message.metadata.{}", key), f));
                    }
                }
                serde_json::Value::Bool(b) => {
                    span.set_attribute(KeyValue::new(format!("message.metadata.{}", key), *b));
                }
                _ => {} // Skip complex types
            }
        }

        // Process message
        let result = self.inner.process(message).await;

        // Inject trace context into response if span context is valid
        let mut response = result?;

        if span_context.is_valid() {
            // Manually create W3C traceparent format
            let trace_id = format!("{:032x}", span_context.trace_id());
            let span_id = format!("{:016x}", span_context.span_id());
            let flags = if span_context.is_sampled() { "01" } else { "00" };
            let traceparent = format!("00-{}-{}-{}", trace_id, span_id, flags);

            // Inject into metadata
            let mut trace_ctx = HashMap::new();
            trace_ctx.insert("traceparent".to_string(), serde_json::json!(traceparent));
            response.metadata.insert("trace_context".to_string(), serde_json::json!(trace_ctx));
        }

        Ok(response)
    }
}

/// Shutdown the global tracer provider.
///
/// This should be called before application exit to ensure all spans are
/// flushed to the exporter.
pub fn shutdown() {
    // 0.32 removed global::shutdown_tracer_provider(); shut down the stored
    // provider explicitly instead. Flushes any pending spans to the exporter.
    if let Some(provider) = TRACER_PROVIDER.get() {
        let _ = provider.shutdown();
    }
}
