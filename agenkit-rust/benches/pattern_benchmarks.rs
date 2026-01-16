//! Pattern performance benchmarks
//!
//! Measures framework overhead for agent patterns using simple mock agents
//! to isolate pattern logic from LLM latency.

use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::*;
use async_trait::async_trait;
use std::sync::Arc;
use std::time::Instant;

/// Simple echo agent for benchmarking
struct EchoAgent {
    agent_name: String,
}

impl EchoAgent {
    fn new(name: impl Into<String>) -> Arc<Self> {
        Arc::new(Self {
            agent_name: name.into(),
        })
    }
}

#[async_trait]
impl Agent for EchoAgent {
    fn name(&self) -> &str {
        &self.agent_name
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["echo".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Simple echo - return input as output
        Ok(Message::with_text(
            "assistant",
            message.content_as_str().unwrap_or("echo"),
        ))
    }
}

/// Benchmark runner
async fn benchmark<F, Fut>(name: &str, iterations: usize, f: F)
where
    F: Fn() -> Fut,
    Fut: std::future::Future<Output = Result<(), AgentError>>,
{
    // Warmup
    for _ in 0..10 {
        let _ = f().await;
    }

    // Benchmark
    let start = Instant::now();
    for _ in 0..iterations {
        let _ = f().await;
    }
    let elapsed = start.elapsed();

    let avg_us = elapsed.as_micros() / iterations as u128;
    let ops_per_sec = iterations as f64 / elapsed.as_secs_f64();

    println!(
        "{:<30} {:>10} μs/op  {:>10.0} ops/s",
        name, avg_us, ops_per_sec
    );
}

#[tokio::main]
async fn main() {
    println!("=== Agenkit Pattern Benchmarks (Rust) ===\n");
    println!(
        "{:<30} {:>10}        {:>10}",
        "Pattern", "Time", "Throughput"
    );
    println!("{}", "-".repeat(60));

    let iterations = 1000;

    // Sequential
    benchmark("Sequential", iterations, || async {
        let agent1 = EchoAgent::new("agent1");
        let agent2 = EchoAgent::new("agent2");
        let agent3 = EchoAgent::new("agent3");
        let agents: Vec<Arc<dyn Agent>> = vec![agent1, agent2, agent3];
        let seq = SequentialAgent::new(agents)?;
        let msg = Message::with_text("user", "test");
        let _ = seq.process(msg).await?;
        Ok::<(), AgentError>(())
    })
    .await;

    // Parallel
    benchmark("Parallel", iterations, || async {
        let agent1 = EchoAgent::new("agent1");
        let agent2 = EchoAgent::new("agent2");
        let agent3 = EchoAgent::new("agent3");
        let agents: Vec<Arc<dyn Agent>> = vec![agent1, agent2, agent3];
        let parallel = ParallelAgent::new(agents, |results| {
            results
                .first()
                .cloned()
                .unwrap_or_else(|| Message::with_text("assistant", ""))
        })?;
        let msg = Message::with_text("user", "test");
        let _ = parallel.process(msg).await?;
        Ok::<(), AgentError>(())
    })
    .await;

    // Reflection
    benchmark("Reflection", iterations, || async {
        let generator = EchoAgent::new("generator");
        let critic = EchoAgent::new("critic");
        let config = ReflectionConfig {
            generator,
            critic,
            max_iterations: 2,
            quality_threshold: 0.9,
            improvement_threshold: 0.05,
            critique_format: CritiqueFormat::Structured,
            verbose: false,
        };
        let agent = ReflectionAgent::new(config)?;
        let msg = Message::with_text("user", "test");
        let _ = agent.process(msg).await?;
        Ok::<(), AgentError>(())
    })
    .await;

    // Fallback
    benchmark("Fallback", iterations, || async {
        let agent1 = EchoAgent::new("agent1");
        let agent2 = EchoAgent::new("agent2");
        let agents: Vec<Arc<dyn Agent>> = vec![agent1, agent2];
        let fallback = FallbackAgent::new(agents)?;
        let msg = Message::with_text("user", "test");
        let _ = fallback.process(msg).await?;
        Ok::<(), AgentError>(())
    })
    .await;

    // Collaborative
    benchmark("Collaborative", iterations, || async {
        let agent1 = EchoAgent::new("agent1");
        let agent2 = EchoAgent::new("agent2");
        let config = CollaborativeConfig {
            agents: vec![agent1, agent2],
            max_rounds: 2,
            consensus_func: None,
            merge_func: DefaultMergeFunc::first,
        };
        let collab = CollaborativeAgent::new(config)?;
        let msg = Message::with_text("user", "test");
        let _ = collab.process(msg).await?;
        Ok::<(), AgentError>(())
    })
    .await;

    println!("\n=== Benchmark Complete ===");
}
