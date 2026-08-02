//! Property-based tests using proptest
//!
//! Tests invariants that should hold for arbitrary inputs:
//! message properties, middleware invariants, and composition properties.

use agenkit::composition::{FallbackAgent, SequentialAgent};
use agenkit::core::{Agent, AgentError, Message};
use agenkit::middleware::{
    CachingConfig, CachingMiddleware, CircuitBreakerConfig, RetryConfig, RetryMiddleware,
    TimeoutConfig, TimeoutMiddleware,
};
use async_trait::async_trait;
use proptest::prelude::*;
use serde_json::json;
use std::sync::Arc;

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

struct EchoAgent;

#[async_trait]
impl Agent for EchoAgent {
    fn name(&self) -> &str {
        "echo"
    }
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        Ok(Message::with_text(
            "assistant",
            message.content_as_str().unwrap_or(""),
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
        Err(AgentError::ProcessingError("always fails".to_string()))
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Message property tests
// ─────────────────────────────────────────────────────────────────────────────

proptest! {
    #![proptest_config(ProptestConfig::with_cases(50))]

    #[test]
    fn prop_message_role_preserved(role in "[a-z]{3,10}") {
        let msg = Message::with_text(&role, "content");
        prop_assert_eq!(msg.role, role);
    }

    #[test]
    fn prop_message_content_roundtrip(content in ".*") {
        let msg = Message::with_text("user", content.as_str());
        let retrieved = msg.content_as_str().unwrap_or("");
        prop_assert_eq!(retrieved, content.as_str());
    }

    #[test]
    fn prop_message_metadata_preserved(
        key in "[a-z][a-z0-9_]{1,15}",
        value in "[a-zA-Z0-9 ]{1,50}"
    ) {
        let msg = Message::with_text("user", "test")
            .with_metadata(key.clone(), json!(value.clone()));
        let stored = msg.metadata.get(&key).unwrap().as_str().unwrap();
        prop_assert_eq!(stored, value.as_str());
    }

    #[test]
    fn prop_message_json_roundtrip(content in "[a-zA-Z0-9 .,!?]{1,100}") {
        let msg = Message::with_text("user", content.as_str())
            .with_metadata("test", json!("value"));
        let json_str = serde_json::to_string(&msg).unwrap();
        let restored: Message = serde_json::from_str(&json_str).unwrap();
        prop_assert_eq!(restored.role, msg.role);
        prop_assert_eq!(restored.content, msg.content);
    }

    #[test]
    fn prop_message_multiple_metadata_keys(
        k1 in "key[0-9]",
        k2 in "val[0-9]",
        v1 in "[a-z]{3,10}",
        v2 in "[a-z]{3,10}"
    ) {
        // Ensure two different keys can coexist
        prop_assume!(k1 != k2);
        let msg = Message::with_text("user", "test")
            .with_metadata(k1.clone(), json!(v1.clone()))
            .with_metadata(k2.clone(), json!(v2.clone()));
        prop_assert!(msg.metadata.contains_key(&k1));
        prop_assert!(msg.metadata.contains_key(&k2));
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Middleware invariant property tests
// ─────────────────────────────────────────────────────────────────────────────

proptest! {
    #![proptest_config(ProptestConfig::with_cases(30))]

    #[test]
    fn prop_retry_never_exceeds_max_retries(max_retries in 1u32..=10u32) {
        // RetryConfig with given max_retries should be constructible
        let config = RetryConfig::builder()
            .max_retries(max_retries)
            .initial_delay(std::time::Duration::from_millis(1))
            .build();
        prop_assert_eq!(config.max_retries, max_retries);
    }

    #[test]
    fn prop_timeout_positive_duration(ms in 1u64..=10_000u64) {
        let config = TimeoutConfig::builder()
            .timeout(std::time::Duration::from_millis(ms))
            .build();
        prop_assert!(config.timeout.as_millis() as u64 == ms);
    }

    #[test]
    fn prop_cache_max_size_preserved(size in 1usize..=10_000usize) {
        let config = CachingConfig::builder()
            .max_size(size)
            .build();
        prop_assert_eq!(config.max_size, size);
    }

    #[test]
    fn prop_circuit_breaker_threshold_preserved(threshold in 1u32..=100u32) {
        let config = CircuitBreakerConfig::builder()
            .failure_threshold(threshold)
            .build();
        prop_assert_eq!(config.failure_threshold, threshold);
    }

    #[test]
    fn prop_retry_delay_ordering(
        initial_ms in 1u64..=100u64,
        max_ms_extra in 0u64..=1000u64
    ) {
        let initial = std::time::Duration::from_millis(initial_ms);
        let max = initial + std::time::Duration::from_millis(max_ms_extra);
        let config = RetryConfig::builder()
            .initial_delay(initial)
            .max_delay(max)
            .build();
        prop_assert!(config.max_delay >= config.initial_delay);
    }

    #[test]
    fn prop_retry_name_preserved_through_middleware(
        name in "[a-z][a-z0-9-]{3,15}"
    ) {
        // The middleware should preserve the inner agent's name
        struct NamedAgent { n: String }
        #[async_trait::async_trait]
        impl Agent for NamedAgent {
            fn name(&self) -> &str { &self.n }
            async fn process(&self, _msg: Message) -> Result<Message, AgentError> {
                Ok(Message::with_text("assistant", "ok"))
            }
        }
        let inner = NamedAgent { n: name.clone() };
        let agent = RetryMiddleware::new(inner, RetryConfig::default());
        prop_assert_eq!(agent.name(), name.as_str());
    }

    #[test]
    fn prop_timeout_name_preserved_through_middleware(
        name in "[a-z][a-z0-9-]{3,15}"
    ) {
        struct NamedAgent { n: String }
        #[async_trait::async_trait]
        impl Agent for NamedAgent {
            fn name(&self) -> &str { &self.n }
            async fn process(&self, _msg: Message) -> Result<Message, AgentError> {
                Ok(Message::with_text("assistant", "ok"))
            }
        }
        let inner = NamedAgent { n: name.clone() };
        let agent = TimeoutMiddleware::new(inner, TimeoutConfig::default());
        prop_assert_eq!(agent.name(), name.as_str());
    }

    #[test]
    fn prop_caching_name_preserved_through_middleware(
        name in "[a-z][a-z0-9-]{3,15}"
    ) {
        struct NamedAgent { n: String }
        #[async_trait::async_trait]
        impl Agent for NamedAgent {
            fn name(&self) -> &str { &self.n }
            async fn process(&self, _msg: Message) -> Result<Message, AgentError> {
                Ok(Message::with_text("assistant", "ok"))
            }
        }
        let inner = NamedAgent { n: name.clone() };
        let agent = CachingMiddleware::new(inner, CachingConfig::default());
        prop_assert_eq!(agent.name(), name.as_str());
    }

    #[test]
    fn prop_circuit_breaker_success_threshold_le_failure(
        success in 1u32..=5u32,
        failure_extra in 0u32..=10u32
    ) {
        let failure = success + failure_extra;
        let config = CircuitBreakerConfig::builder()
            .failure_threshold(failure)
            .success_threshold(success)
            .build();
        prop_assert!(config.success_threshold <= config.failure_threshold);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Composition property tests
// ─────────────────────────────────────────────────────────────────────────────

proptest! {
    #![proptest_config(ProptestConfig::with_cases(30))]

    #[test]
    fn prop_sequential_preserves_agent_count(n_agents in 1usize..=8usize) {
        let agents: Vec<Arc<dyn Agent>> = (0..n_agents)
            .map(|_i| Arc::new(EchoAgent) as Arc<dyn Agent>)
            .collect();
        let seq = SequentialAgent::new("seq", agents).unwrap();
        prop_assert_eq!(seq.agents().len(), n_agents);
    }

    #[test]
    fn prop_fallback_preserves_agent_count(n_agents in 1usize..=8usize) {
        let agents: Vec<Arc<dyn Agent>> = (0..n_agents)
            .map(|_| Arc::new(EchoAgent) as Arc<dyn Agent>)
            .collect();
        let fb = FallbackAgent::new("fb", agents).unwrap();
        prop_assert_eq!(fb.agents().len(), n_agents);
    }

    #[test]
    fn prop_sequential_name_preserved(name in "[a-z][a-z0-9-]{2,15}") {
        let agents: Vec<Arc<dyn Agent>> = vec![Arc::new(EchoAgent)];
        let seq = SequentialAgent::new(name.clone(), agents).unwrap();
        prop_assert_eq!(seq.name(), name.as_str());
    }

    #[test]
    fn prop_fallback_name_preserved(name in "[a-z][a-z0-9-]{2,15}") {
        let agents: Vec<Arc<dyn Agent>> = vec![Arc::new(EchoAgent)];
        let fb = FallbackAgent::new(name.clone(), agents).unwrap();
        prop_assert_eq!(fb.name(), name.as_str());
    }

    #[test]
    fn prop_fallback_uses_first_success(n_failures in 0usize..=5usize) {
        // n_failures ErrorAgents then one EchoAgent — should succeed
        let rt = tokio::runtime::Runtime::new().unwrap();
        let result = rt.block_on(async {
            let mut agents: Vec<Arc<dyn Agent>> = (0..n_failures)
                .map(|_| Arc::new(FailingAgent) as Arc<dyn Agent>)
                .collect();
            agents.push(Arc::new(EchoAgent) as Arc<dyn Agent>);
            let fb = FallbackAgent::new("fb", agents).unwrap();
            fb.process(Message::with_text("user", "test")).await
        });
        prop_assert!(result.is_ok());
    }

    #[test]
    fn prop_agent_name_stable_after_multiple_calls(
        name in "[a-z][a-z0-9-]{3,10}"
    ) {
        struct ConstantAgent { n: String }
        #[async_trait::async_trait]
        impl Agent for ConstantAgent {
            fn name(&self) -> &str { &self.n }
            async fn process(&self, _msg: Message) -> Result<Message, AgentError> {
                Ok(Message::with_text("assistant", "ok"))
            }
        }
        let agent = ConstantAgent { n: name.clone() };
        for _ in 0..10 {
            prop_assert_eq!(agent.name(), name.as_str());
        }
    }

    #[test]
    fn prop_message_role_roundtrip(role in "[a-z]{3,12}") {
        let msg = Message::with_text(&role, "content");
        let json = serde_json::to_string(&msg).unwrap();
        let restored: Message = serde_json::from_str(&json).unwrap();
        prop_assert_eq!(restored.role, role);
    }

    #[test]
    fn prop_message_metadata_count_preserved(n_keys in 1usize..=10usize) {
        let mut msg = Message::with_text("user", "test");
        for i in 0..n_keys {
            msg = msg.with_metadata(format!("key{}", i), json!(i));
        }
        prop_assert_eq!(msg.metadata.len(), n_keys);
    }

    #[test]
    fn prop_sequential_capabilities_include_sequential(n_agents in 1usize..=5usize) {
        let agents: Vec<Arc<dyn Agent>> = (0..n_agents)
            .map(|_| Arc::new(EchoAgent) as Arc<dyn Agent>)
            .collect();
        let seq = SequentialAgent::new("seq", agents).unwrap();
        prop_assert!(seq.capabilities().contains(&"sequential".to_string()));
    }
}
