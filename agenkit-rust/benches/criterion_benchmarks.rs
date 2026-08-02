//! Comprehensive criterion benchmarks for Agenkit patterns
//!
//! Measures framework overhead for agent patterns using criterion for
//! statistical analysis and regression detection.

use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::*;
use async_trait::async_trait;
use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion};
// `criterion::black_box` is deprecated in favour of the std one, which criterion now
// just re-exports (#778). Importing it here keeps the 18 call sites below unchanged.
use std::hint::black_box;
use std::sync::Arc;
use tokio::runtime::Runtime;

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

/// Benchmark sequential pattern
fn bench_sequential(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();

    let mut group = c.benchmark_group("sequential");

    for num_agents in [1, 2, 3, 5, 10].iter() {
        group.bench_with_input(
            BenchmarkId::from_parameter(num_agents),
            num_agents,
            |b, &num_agents| {
                b.to_async(&rt).iter(|| async move {
                    let agents: Vec<Arc<dyn Agent>> = (0..num_agents)
                        .map(|i| EchoAgent::new(format!("agent{}", i)) as Arc<dyn Agent>)
                        .collect();

                    let seq = SequentialAgent::new(agents).unwrap();
                    let msg = Message::with_text("user", black_box("test message"));
                    let _result = seq.process(msg).await.unwrap();
                });
            },
        );
    }

    group.finish();
}

/// Benchmark parallel pattern
fn bench_parallel(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();

    let mut group = c.benchmark_group("parallel");

    for num_agents in [1, 2, 3, 5, 10].iter() {
        group.bench_with_input(
            BenchmarkId::from_parameter(num_agents),
            num_agents,
            |b, &num_agents| {
                b.to_async(&rt).iter(|| async move {
                    let agents: Vec<Arc<dyn Agent>> = (0..num_agents)
                        .map(|i| EchoAgent::new(format!("agent{}", i)) as Arc<dyn Agent>)
                        .collect();

                    let parallel = ParallelAgent::new(agents, |results| {
                        results
                            .first()
                            .cloned()
                            .unwrap_or_else(|| Message::with_text("assistant", ""))
                    })
                    .unwrap();

                    let msg = Message::with_text("user", black_box("test message"));
                    let _result = parallel.process(msg).await.unwrap();
                });
            },
        );
    }

    group.finish();
}

/// Benchmark reflection pattern
fn bench_reflection(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();

    let mut group = c.benchmark_group("reflection");

    for max_iter in [1, 2, 3, 5].iter() {
        group.bench_with_input(
            BenchmarkId::from_parameter(max_iter),
            max_iter,
            |b, &max_iter| {
                b.to_async(&rt).iter(|| async move {
                    let generator = EchoAgent::new("generator");
                    let critic = EchoAgent::new("critic");
                    let config = ReflectionConfig {
                        generator,
                        critic,
                        max_iterations: max_iter,
                        quality_threshold: 0.9,
                        improvement_threshold: 0.05,
                        critique_format: CritiqueFormat::Structured,
                        verbose: false,
                    };
                    let agent = ReflectionAgent::new(config).unwrap();
                    let msg = Message::with_text("user", black_box("test message"));
                    let _result = agent.process(msg).await.unwrap();
                });
            },
        );
    }

    group.finish();
}

/// Benchmark fallback pattern
fn bench_fallback(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();

    c.bench_function("fallback_2_agents", |b| {
        b.to_async(&rt).iter(|| async {
            let agent1 = EchoAgent::new("agent1");
            let agent2 = EchoAgent::new("agent2");
            let agents: Vec<Arc<dyn Agent>> = vec![agent1, agent2];
            let fallback = FallbackAgent::new(agents).unwrap();
            let msg = Message::with_text("user", black_box("test"));
            let _result = fallback.process(msg).await.unwrap();
        });
    });
}

/// Benchmark collaborative pattern
fn bench_collaborative(c: &mut Criterion) {
    let rt = Runtime::new().unwrap();

    let mut group = c.benchmark_group("collaborative");

    for num_rounds in [1, 2, 3, 5].iter() {
        group.bench_with_input(
            BenchmarkId::from_parameter(num_rounds),
            num_rounds,
            |b, &num_rounds| {
                b.to_async(&rt).iter(|| async move {
                    let agent1 = EchoAgent::new("agent1");
                    let agent2 = EchoAgent::new("agent2");
                    let config = CollaborativeConfig {
                        agents: vec![agent1, agent2],
                        max_rounds: num_rounds,
                        consensus_func: None,
                        merge_func: DefaultMergeFunc::first,
                    };
                    let collab = CollaborativeAgent::new(config).unwrap();
                    let msg = Message::with_text("user", black_box("test"));
                    let _result = collab.process(msg).await.unwrap();
                });
            },
        );
    }

    group.finish();
}

/// Benchmark message creation and manipulation
fn bench_message_operations(c: &mut Criterion) {
    let mut group = c.benchmark_group("message");

    group.bench_function("create_text", |b| {
        b.iter(|| {
            let _msg = Message::with_text(black_box("user"), black_box("Hello, world!"));
        });
    });

    group.bench_function("clone", |b| {
        let msg = Message::with_text("user", "Hello, world!");
        b.iter(|| {
            let _cloned = black_box(&msg).clone();
        });
    });

    group.bench_function("content_as_str", |b| {
        let msg = Message::with_text("user", "Hello, world!");
        b.iter(|| {
            let _content = black_box(&msg).content_as_str().unwrap();
        });
    });

    group.finish();
}

/// Benchmark metadata operations
fn bench_metadata_operations(c: &mut Criterion) {
    let mut group = c.benchmark_group("metadata");

    group.bench_function("with_metadata", |b| {
        b.iter(|| {
            let msg = Message::with_text("user", "test");
            let value = serde_json::Value::String("test_value".to_string());
            let _msg = msg.with_metadata(black_box("key"), value);
        });
    });

    group.bench_function("get_metadata", |b| {
        let value = serde_json::Value::String("test_value".to_string());
        let msg = Message::with_text("user", "test").with_metadata("key", value);
        b.iter(|| {
            let _value = black_box(&msg).metadata.get(black_box("key"));
        });
    });

    group.finish();
}

/// Benchmark memory optimizations
fn bench_memory_optimizations(c: &mut Criterion) {
    let mut group = c.benchmark_group("memory_optimizations");

    // Baseline: standard Message::with_text
    group.bench_function("standard_message_creation", |b| {
        b.iter(|| {
            let _msg = Message::with_text(black_box("user"), black_box("Hello, world!"));
        });
    });

    // Optimized: using fast helpers
    #[cfg(feature = "native")]
    group.bench_function("optimized_message_creation", |b| {
        use agenkit::optimizations::fast;
        b.iter(|| {
            let _msg = fast::user_text(black_box("Hello, world!"));
        });
    });

    // Baseline: creating 100 messages without capacity hint
    group.bench_function("standard_batch_100", |b| {
        b.iter(|| {
            let mut messages = Vec::new();
            for i in 0..100 {
                messages.push(Message::with_text("user", format!("Message {}", i)));
            }
            black_box(messages);
        });
    });

    // Optimized: creating 100 messages with pre-allocated capacity
    #[cfg(feature = "native")]
    group.bench_function("optimized_batch_100", |b| {
        use agenkit::optimizations::MessageBatch;
        b.iter(|| {
            let mut batch = MessageBatch::with_capacity(100);
            for i in 0..100 {
                batch.push_user(format!("Message {}", i));
            }
            black_box(batch.into_messages());
        });
    });

    // String interning: common role
    #[cfg(feature = "native")]
    group.bench_function("string_pool_common_role", |b| {
        use agenkit::optimizations::string_pool;
        b.iter(|| {
            let _interned = string_pool::intern(black_box("user"));
        });
    });

    // String interning: custom role
    #[cfg(feature = "native")]
    group.bench_function("string_pool_custom_role", |b| {
        use agenkit::optimizations::string_pool;
        b.iter(|| {
            let _interned = string_pool::intern(black_box("custom_role_12345"));
        });
    });

    group.finish();
}

/// Benchmark concurrency optimizations
fn bench_concurrency_optimizations(c: &mut Criterion) {
    let mut group = c.benchmark_group("concurrency_optimizations");

    // Benchmark ConcurrentQueue operations
    #[cfg(feature = "native")]
    group.bench_function("concurrent_queue_push_pop", |b| {
        use agenkit::optimizations::ConcurrentQueue;
        let queue = ConcurrentQueue::new();
        b.iter(|| {
            queue.push(black_box(42));
            let _ = queue.pop();
        });
    });

    // Benchmark parallel map vs sequential
    #[cfg(feature = "native")]
    group.bench_function("parallel_map_100", |b| {
        use agenkit::optimizations::parallel;
        b.iter(|| {
            let items: Vec<i32> = (0..100).collect();
            let _results = parallel::map(items, |x| x * 2);
        });
    });

    #[cfg(feature = "native")]
    group.bench_function("sequential_map_100", |b| {
        b.iter(|| {
            let items: Vec<i32> = (0..100).collect();
            let _results: Vec<i32> = items.into_iter().map(|x| x * 2).collect();
        });
    });

    // Benchmark parallel reduce
    #[cfg(feature = "native")]
    group.bench_function("parallel_reduce_1000", |b| {
        use agenkit::optimizations::parallel;
        b.iter(|| {
            let items: Vec<i32> = (0..1000).collect();
            let _sum = parallel::reduce(items, 0, |a, b| a + b);
        });
    });

    #[cfg(feature = "native")]
    group.bench_function("sequential_reduce_1000", |b| {
        b.iter(|| {
            let items: Vec<i32> = (0..1000).collect();
            let _sum: i32 = items.into_iter().sum();
        });
    });

    // Benchmark parallel filter_map
    #[cfg(feature = "native")]
    group.bench_function("parallel_filter_map_1000", |b| {
        use agenkit::optimizations::parallel;
        b.iter(|| {
            let items: Vec<i32> = (0..1000).collect();
            let _results =
                parallel::filter_map(items, |x| if x % 2 == 0 { Some(x * 2) } else { None });
        });
    });

    // Benchmark WorkStealingExecutor
    #[cfg(feature = "native")]
    group.bench_function("work_stealing_executor_10", |b| {
        use agenkit::optimizations::WorkStealingExecutor;
        let executor = WorkStealingExecutor::with_max_parallelism();
        b.iter(|| {
            let tasks: Vec<_> = (0..10).map(|i| move || i * 2).collect();
            let _results = executor.execute(tasks);
        });
    });

    group.finish();
}

criterion_group!(
    benches,
    bench_sequential,
    bench_parallel,
    bench_reflection,
    bench_fallback,
    bench_collaborative,
    bench_message_operations,
    bench_metadata_operations,
    bench_memory_optimizations,
    bench_concurrency_optimizations
);

criterion_main!(benches);
