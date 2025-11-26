///! HTTP transport example.
///!
///! This example demonstrates how to:
///! 1. Create an agent server that exposes an agent over HTTP
///! 2. Create an HTTP client that communicates with the remote agent

use agenkit::core::{Agent, AgentError, Message};
use agenkit::transports::{HttpAgent, HttpServer, HttpTransportConfig};
use async_trait::async_trait;
use tokio::time::{sleep, Duration};

/// Counter agent that counts the number of messages it has processed.
struct CounterAgent {
    name: String,
    count: std::sync::Arc<std::sync::atomic::AtomicUsize>,
}

impl CounterAgent {
    fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            count: std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0)),
        }
    }
}

#[async_trait]
impl Agent for CounterAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Increment counter
        let count = self
            .count
            .fetch_add(1, std::sync::atomic::Ordering::SeqCst)
            + 1;

        // Return message with count
        let content = format!(
            "Message #{}: {}",
            count,
            message.content_as_str().unwrap_or("")
        );

        Ok(Message::with_text("assistant", content))
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["counter".to_string()]
    }
}

#[tokio::main]
async fn main() {
    // Initialize tracing for debugging
    tracing_subscriber::fmt::init();

    // Create a counter agent
    let agent = CounterAgent::new("counter");

    // Start HTTP server in background
    let server = HttpServer::new(agent, "127.0.0.1:8080");
    tokio::spawn(async move {
        println!("Starting HTTP server on 127.0.0.1:8080");
        if let Err(e) = server.serve().await {
            eprintln!("Server error: {}", e);
        }
    });

    // Give server time to start
    sleep(Duration::from_millis(500)).await;

    // Create HTTP client
    let config = HttpTransportConfig {
        base_url: "http://127.0.0.1:8080".to_string(),
        timeout_secs: 30,
        api_key: None,
    };
    let client = HttpAgent::new("counter-client", config);

    // Send several messages
    for i in 1..=5 {
        let msg = Message::with_text("user", format!("Hello #{}", i));
        println!("\nSending: {}", msg.content_as_str().unwrap());

        match client.process(msg).await {
            Ok(response) => {
                println!("Response: {}", response.content_as_str().unwrap());
            }
            Err(e) => {
                eprintln!("Error: {}", e);
            }
        }

        sleep(Duration::from_millis(100)).await;
    }

    println!("\nHTTP transport example complete!");
}
