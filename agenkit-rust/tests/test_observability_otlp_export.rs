//! Regression test for #768: `init_tracing("otlp", endpoint)` must export spans
//! to the given endpoint, not to stdout.
//!
//! This lives in its own test binary on purpose. `init_tracing` installs a
//! process-global tracer provider stored in a `OnceCell`, and `shutdown()`
//! flushes *that* provider — so a test that needs to force a flush must own the
//! global. Sharing a binary with the other observability tests would make which
//! provider gets flushed depend on test execution order.
//!
//! The assertion is deliberately at the transport level rather than the payload
//! level: we prove a TCP connection is made to the configured endpoint. Parsing
//! the OTLP protobuf would test the SDK, not agenkit's wiring. The bug being
//! guarded is that *no* connection was ever attempted, because the endpoint was
//! discarded and spans went to `opentelemetry_stdout`.

#![cfg(feature = "opentelemetry")]

use agenkit::core::{Agent, AgentError, Message};
use agenkit::observability::{init_tracing_with_config, TracingMiddleware};
use std::sync::mpsc;
use std::time::Duration;

struct SimpleAgent;

#[async_trait::async_trait]
impl Agent for SimpleAgent {
    fn name(&self) -> &str {
        "otlp-export-agent"
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        Ok(Message::with_text("assistant", "ok"))
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn test_otlp_exporter_connects_to_configured_endpoint() {
    // Bind port 0 so the OS picks a free port — a hardcoded port collides with
    // other suites on the shared CI runners.
    let listener =
        std::net::TcpListener::bind("127.0.0.1:0").expect("failed to bind test listener");
    let port = listener.local_addr().unwrap().port();

    let (tx, rx) = mpsc::channel();

    // Accept on a plain thread: this is a raw TCP accept, not gRPC. We never
    // speak OTLP back, so the exporter's send will ultimately fail — that is
    // fine and is not what we are asserting. The connection attempt itself is
    // the evidence that the endpoint was honoured.
    //
    // The thread is detached rather than joined, and the signal comes over a
    // channel with a timeout. An earlier draft joined the thread and, if nothing
    // had connected yet, opened a connection itself to unblock the accept — that
    // connection would have satisfied the test's own assertion, making it pass
    // even with the endpoint discarded.
    std::thread::spawn(move || {
        if listener.accept().is_ok() {
            let _ = tx.send(());
        }
    });

    let endpoint = format!("http://127.0.0.1:{}", port);
    init_tracing_with_config("otlp", Some(&endpoint), Some("test-service"), 1.0)
        .expect("init_tracing_with_config(\"otlp\", ...) should succeed");

    // Emit a span through the middleware, the same path a real caller uses.
    let traced = TracingMiddleware::new(SimpleAgent, None);
    let response = traced.process(Message::with_text("user", "hello")).await;
    assert!(response.is_ok(), "traced agent should process successfully");

    // Flush via the public entry point the docs tell callers to use, so this
    // test also covers the path that matters in production. Without it the batch
    // processor would hold the span until its scheduled delay — and at process
    // exit it would be dropped silently.
    agenkit::observability::shutdown_observability();

    // The connection may land slightly after shutdown returns. Wait with a
    // timeout rather than joining the accept thread, which would block forever
    // if the endpoint were ignored.
    assert!(
        rx.recv_timeout(Duration::from_secs(10)).is_ok(),
        "no TCP connection was made to the configured OTLP endpoint {} — \
         the endpoint is being discarded (#768)",
        endpoint
    );
}
