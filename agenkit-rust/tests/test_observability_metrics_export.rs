//! Regression test for #772: `init_metrics("otlp", endpoint)` must actually
//! export, rather than installing no reader and returning `Ok(())`.
//!
//! Own test binary, for the same reason as `test_observability_otlp_export.rs`:
//! `init_metrics` installs a process-global meter provider in a `OnceCell` and
//! `shutdown_metrics()` flushes *that* provider, so a test that forces a flush
//! must own the global or the flush becomes order-dependent.
//!
//! The assertion is at the transport level — a TCP connection reaches the
//! configured endpoint. Parsing the OTLP protobuf would test the SDK rather than
//! agenkit's wiring, and the bug being guarded is that no reader existed at all,
//! so nothing was ever exported and no connection was ever attempted.
//!
//! Note what this test does *not* do: assert that `init_metrics` returned `Ok`.
//! The pre-fix code returned `Ok` too. Only the connection distinguishes them.

#![cfg(feature = "opentelemetry")]

use agenkit::core::{Agent, AgentError, Message};
use agenkit::observability::{init_metrics, MetricsMiddleware};
use std::sync::mpsc;
use std::time::Duration;

struct SimpleAgent;

#[async_trait::async_trait]
impl Agent for SimpleAgent {
    fn name(&self) -> &str {
        "metrics-export-agent"
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        Ok(Message::with_text("assistant", "ok"))
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn test_otlp_metrics_reach_the_configured_endpoint() {
    // Port 0: the OS picks a free port, so this cannot collide with another
    // suite on a shared runner.
    let listener =
        std::net::TcpListener::bind("127.0.0.1:0").expect("failed to bind test listener");
    let port = listener.local_addr().unwrap().port();

    let (tx, rx) = mpsc::channel();

    // Detached accept thread signalling over a channel. Deliberately *not*
    // joined, and deliberately never opening a connection itself to unblock:
    // a test that makes its own connection would satisfy its own assertion and
    // pass even with no exporter installed.
    std::thread::spawn(move || {
        if listener.accept().is_ok() {
            let _ = tx.send(());
        }
    });

    let endpoint = format!("http://127.0.0.1:{}", port);
    init_metrics("otlp", Some(&endpoint)).expect("init_metrics(\"otlp\", ...) should succeed");

    // Record a metric through the middleware, the path a real caller uses.
    let metered = MetricsMiddleware::new(SimpleAgent);
    let response = metered.process(Message::with_text("user", "hello")).await;
    assert!(response.is_ok(), "metered agent should process successfully");

    // Force the export now rather than waiting out the 60s interval. This is
    // also the flush a real caller must perform before exit.
    agenkit::observability::shutdown_metrics();

    assert!(
        rx.recv_timeout(Duration::from_secs(10)).is_ok(),
        "no TCP connection was made to the configured OTLP metrics endpoint {} — \
         no reader/exporter is installed, so nothing is exported for any \
         exporter type (#772)",
        endpoint
    );
}
