//! Comprehensive middleware example demonstrating all 6 middleware types.
//!
//! This example shows how to use and compose middleware to add cross-cutting
//! concerns to agents: retry, circuit breaker, timeout, rate limiting, caching,
//! and batching.
//!
//! Run with: cargo run --example middleware_example --features native

use agenkit::core::{Agent, AgentError, Message};
use agenkit::middleware::{
    BatchingConfig, BatchingMiddleware, CachingConfig, CachingMiddleware, CircuitBreakerConfig,
    CircuitBreakerMiddleware, RateLimiterConfig, RateLimiterMiddleware, RetryConfig,
    RetryMiddleware, TimeoutConfig, TimeoutMiddleware,
};
use async_trait::async_trait;
use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::Arc;
use std::time::Duration;

/// Simple echo agent for demonstration.
struct EchoAgent {
    name: String,
    call_count: Arc<AtomicU32>,
}

impl EchoAgent {
    fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            call_count: Arc::new(AtomicU32::new(0)),
        }
    }

    fn calls(&self) -> u32 {
        self.call_count.load(Ordering::SeqCst)
    }
}

#[async_trait]
impl Agent for EchoAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let count = self.call_count.fetch_add(1, Ordering::SeqCst) + 1;
        println!("  [{}] Processing message (call #{})", self.name, count);

        Ok(Message::with_text(
            "assistant",
            format!(
                "Echo: {} (call #{})",
                message.content_as_str().unwrap_or(""),
                count
            ),
        ))
    }
}

/// Example 1: Retry Middleware
async fn example_retry() {
    println!("\n{}", "=".repeat(80));
    println!("EXAMPLE 1: Retry Middleware");
    println!("{}", "=".repeat(80));
    println!("Automatically retries failed requests with exponential backoff.\n");

    let agent = EchoAgent::new("retry-agent");

    let config = RetryConfig::builder()
        .max_retries(3)
        .initial_delay(Duration::from_millis(100))
        .max_delay(Duration::from_secs(2))
        .multiplier(2.0)
        .build();

    let retry_agent = RetryMiddleware::new(agent, config);

    let msg = Message::with_text("user", "Hello with retry!");
    let response = retry_agent.process(msg).await.unwrap();

    println!("Response: {}", response.content_as_str().unwrap());
    println!("Retry middleware: operation completed successfully");
}

/// Example 2: Circuit Breaker Middleware
async fn example_circuit_breaker() {
    println!("\n{}", "=".repeat(80));
    println!("EXAMPLE 2: Circuit Breaker Middleware");
    println!("{}", "=".repeat(80));
    println!("Prevents cascading failures by opening circuit after threshold.\n");

    let agent = EchoAgent::new("circuit-breaker-agent");

    let config = CircuitBreakerConfig::builder()
        .failure_threshold(5)
        .success_threshold(2)
        .timeout(Duration::from_secs(60))
        .build();

    let cb_agent = CircuitBreakerMiddleware::new(agent, config);

    // Successful request
    let msg = Message::with_text("user", "Hello");
    let response = cb_agent.process(msg).await.unwrap();

    println!("Response: {}", response.content_as_str().unwrap());
    println!("Circuit state: CLOSED (normal operation)");
}

/// Example 3: Timeout Middleware
async fn example_timeout() {
    println!("\n{}", "=".repeat(80));
    println!("EXAMPLE 3: Timeout Middleware");
    println!("{}", "=".repeat(80));
    println!("Enforces time limits on agent operations.\n");

    let agent = EchoAgent::new("timeout-agent");

    let config = TimeoutConfig::builder()
        .timeout(Duration::from_secs(5))
        .build();

    let timeout_agent = TimeoutMiddleware::new(agent, config);

    let msg = Message::with_text("user", "Hello with timeout!");
    let response = timeout_agent.process(msg).await.unwrap();

    println!("Response: {}", response.content_as_str().unwrap());
    println!("Operation completed within timeout");
}

/// Example 4: Rate Limiter Middleware
async fn example_rate_limiter() {
    println!("\n{}", "=".repeat(80));
    println!("EXAMPLE 4: Rate Limiter Middleware");
    println!("{}", "=".repeat(80));
    println!("Controls request rate using token bucket algorithm.\n");

    let agent = EchoAgent::new("rate-limiter-agent");

    let config = RateLimiterConfig::builder()
        .tokens_per_second(2.0) // 2 requests per second
        .capacity(5.0) // Allow bursts up to 5
        .max_wait_time(Duration::from_secs(5))
        .build();

    let rl_agent = Arc::new(RateLimiterMiddleware::new(agent, config));

    println!("Sending 3 requests (burst allowed)...");

    // Send 3 requests quickly - should succeed due to initial capacity
    for i in 1..=3 {
        let msg = Message::with_text("user", format!("Request {}", i));
        let response = rl_agent.process(msg).await.unwrap();
        println!("Response {}: {}", i, response.content_as_str().unwrap());
    }

    println!("Rate limiter: all requests processed within rate limits");
}

/// Example 5: Caching Middleware
async fn example_caching() {
    println!("\n{}", "=".repeat(80));
    println!("EXAMPLE 5: Caching Middleware");
    println!("{}", "=".repeat(80));
    println!("Caches responses with LRU eviction and TTL.\n");

    let agent = EchoAgent::new("caching-agent");

    let config = CachingConfig::builder()
        .max_size(100)
        .ttl(Duration::from_secs(60))
        .build();

    let cache_agent = CachingMiddleware::new(agent, config);

    let msg = Message::with_text("user", "What is 2+2?");

    // First call - cache miss
    println!("First call (cache miss)...");
    let response1 = cache_agent.process(msg.clone()).await.unwrap();
    println!("Response: {}", response1.content_as_str().unwrap());

    // Second call - cache hit
    println!("\nSecond call (cache hit)...");
    let response2 = cache_agent.process(msg).await.unwrap();
    println!("Response: {}", response2.content_as_str().unwrap());

    println!("\nCache: second call served from cache (same response)");
}

/// Example 6: Batching Middleware
async fn example_batching() {
    println!("\n{}", "=".repeat(80));
    println!("EXAMPLE 6: Batching Middleware");
    println!("{}", "=".repeat(80));
    println!("Aggregates multiple requests for efficient processing.\n");

    let agent = EchoAgent::new("batching-agent");

    let config = BatchingConfig::builder()
        .max_batch_size(3)
        .max_wait_time(Duration::from_millis(100))
        .build();

    let batch_agent = Arc::new(BatchingMiddleware::new(agent, config));

    println!("Sending 3 concurrent requests (will be batched)...");

    // Spawn concurrent requests
    let mut handles = vec![];
    for i in 1..=3 {
        let agent_clone = Arc::clone(&batch_agent);
        let handle = tokio::spawn(async move {
            let msg = Message::with_text("user", format!("Batch request {}", i));
            agent_clone.process(msg).await
        });
        handles.push(handle);
    }

    // Wait for all to complete
    for (i, handle) in handles.into_iter().enumerate() {
        let response = handle.await.unwrap().unwrap();
        println!("Response {}: {}", i + 1, response.content_as_str().unwrap());
    }

    println!("Batching: all requests processed in batch");
}

/// Example 7: Composing Multiple Middleware
async fn example_composition() {
    println!("\n{}", "=".repeat(80));
    println!("EXAMPLE 7: Composing Multiple Middleware");
    println!("{}", "=".repeat(80));
    println!("Stack multiple middleware for combined functionality.\n");

    let agent = EchoAgent::new("composed-agent");

    // Layer 1: Retry (innermost)
    let retry_config = RetryConfig::builder().max_retries(3).build();
    let agent = RetryMiddleware::new(agent, retry_config);

    // Layer 2: Circuit Breaker
    let cb_config = CircuitBreakerConfig::builder().failure_threshold(5).build();
    let agent = CircuitBreakerMiddleware::new(agent, cb_config);

    // Layer 3: Timeout
    let timeout_config = TimeoutConfig::builder()
        .timeout(Duration::from_secs(10))
        .build();
    let agent = TimeoutMiddleware::new(agent, timeout_config);

    // Layer 4: Caching (outermost)
    let cache_config = CachingConfig::builder().max_size(100).build();
    let agent = CachingMiddleware::new(agent, cache_config);

    println!("Middleware stack: Caching → Timeout → Circuit Breaker → Retry → Agent\n");

    let msg = Message::with_text("user", "Composed middleware!");
    let response = agent.process(msg).await.unwrap();

    println!("Response: {}", response.content_as_str().unwrap());
    println!("\nMiddleware composition allows flexible behavior customization.");
}

#[tokio::main]
async fn main() {
    println!("\n{}", "=".repeat(80));
    println!("MIDDLEWARE EXAMPLES FOR AGENKIT-RUST");
    println!("{}", "=".repeat(80));
    println!("Demonstrating all 6 middleware types and composition patterns.\n");

    // Run all examples
    example_retry().await;
    example_circuit_breaker().await;
    example_timeout().await;
    example_rate_limiter().await;
    example_caching().await;
    example_batching().await;
    example_composition().await;

    // Summary
    println!("\n{}", "=".repeat(80));
    println!("KEY TAKEAWAYS");
    println!("{}", "=".repeat(80));
    println!(
        r#"
1. RETRY: Automatic retry with exponential backoff for transient failures
2. CIRCUIT BREAKER: Prevent cascading failures by opening circuit
3. TIMEOUT: Enforce time limits on operations
4. RATE LIMITER: Control request rate using token bucket
5. CACHING: Cache responses with LRU eviction and TTL
6. BATCHING: Aggregate requests for efficient processing

COMPOSITION: Stack multiple middleware for combined functionality
- Order matters: Caching → Timeout → Circuit Breaker → Retry → Agent
- Each layer adds specific behavior
- Fully composable with zero runtime overhead

See docs/MIDDLEWARE.md for detailed design patterns and best practices.
"#
    );
}
