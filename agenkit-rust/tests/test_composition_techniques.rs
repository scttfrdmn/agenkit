//! Composition pattern tests
//!
//! Comprehensive tests for agenkit composition patterns:
//! Sequential, Parallel, Conditional, and Fallback.

use agenkit::composition::{
    content_contains, ConditionalAgent, FallbackAgent, ParallelAgent, SequentialAgent,
};
use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use serde_json::json;
use std::sync::Arc;

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

struct EchoAgent {
    name: String,
}

#[async_trait]
impl Agent for EchoAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("").to_string();
        Ok(
            Message::with_text("assistant", format!("{}:{}", self.name, content))
                .with_metadata("processed_by", json!(self.name.clone())),
        )
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["echo".to_string(), format!("echo-{}", self.name)]
    }
}

struct ErrorAgent;

#[async_trait]
impl Agent for ErrorAgent {
    fn name(&self) -> &str {
        "error-agent"
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        Err(AgentError::ProcessingError(
            "intentional failure".to_string(),
        ))
    }
}

fn echo(name: &str) -> Arc<dyn Agent> {
    Arc::new(EchoAgent {
        name: name.to_string(),
    })
}

// ─────────────────────────────────────────────────────────────────────────────
// Sequential composition tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_sequential_creation_with_name() {
    let agents = vec![echo("a"), echo("b")];
    let result = SequentialAgent::new("pipeline", agents);
    assert!(result.is_ok());
    assert_eq!(result.unwrap().name(), "pipeline");
}

#[tokio::test]
async fn test_sequential_empty_agents_rejected() {
    let result = SequentialAgent::new("empty", vec![]);
    assert!(result.is_err());
}

#[tokio::test]
async fn test_sequential_all_succeed_in_order() {
    let agents = vec![echo("first"), echo("second")];
    let seq = SequentialAgent::new("pipeline", agents).unwrap();
    let result = seq.process(Message::with_text("user", "data")).await;
    assert!(result.is_ok());
    let resp = result.unwrap();
    // Second agent processes output of first agent: "second:first:data"
    let text = resp.content_as_str().unwrap_or("");
    assert!(
        text.contains("second"),
        "expected output from 'second', got: {}",
        text
    );
}

#[tokio::test]
async fn test_sequential_fail_fast_on_first_error() {
    let err_agent = Arc::new(ErrorAgent) as Arc<dyn Agent>;
    let agents = vec![err_agent, echo("b")];
    let seq = SequentialAgent::new("pipeline", agents).unwrap();
    let result = seq.process(Message::with_text("user", "test")).await;
    assert!(result.is_err());
    let err = result.unwrap_err();
    let msg = format!("{}", err);
    // Error message should reference the failing step
    assert!(!msg.is_empty());
}

#[tokio::test]
async fn test_sequential_output_chained_as_input() {
    // First agent prepends "A:", second prepends "B:" — result should be "B:A:input"
    let agents = vec![echo("A"), echo("B")];
    let seq = SequentialAgent::new("chain", agents).unwrap();
    let result = seq
        .process(Message::with_text("user", "input"))
        .await
        .unwrap();
    let text = result.content_as_str().unwrap_or("");
    assert!(text.contains("B"), "expected B in output: {}", text);
    assert!(text.contains("A"), "expected A in output: {}", text);
}

#[tokio::test]
async fn test_sequential_single_agent() {
    let agents = vec![echo("solo")];
    let seq = SequentialAgent::new("solo-pipeline", agents).unwrap();
    let result = seq.process(Message::with_text("user", "solo-input")).await;
    assert!(result.is_ok());
    let text = result.unwrap().content_as_str().unwrap_or("").to_string();
    assert!(text.contains("solo"));
}

#[tokio::test]
async fn test_sequential_capabilities_include_sequential() {
    let agents = vec![echo("a")];
    let seq = SequentialAgent::new("seq", agents).unwrap();
    assert!(seq.capabilities().contains(&"sequential".to_string()));
}

#[tokio::test]
async fn test_sequential_error_identifies_step() {
    let err_agent = Arc::new(ErrorAgent) as Arc<dyn Agent>;
    let agents = vec![echo("a"), err_agent, echo("c")];
    let seq = SequentialAgent::new("pipeline", agents).unwrap();
    let err = seq
        .process(Message::with_text("user", "test"))
        .await
        .unwrap_err();
    let msg = format!("{}", err);
    // Error should mention step number (2) or agent name
    assert!(
        msg.contains("2") || msg.contains("error"),
        "unexpected error: {}",
        msg
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Parallel composition tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_parallel_creation_with_name() {
    let agents = vec![echo("a"), echo("b")];
    let result = ParallelAgent::new("ensemble", agents);
    assert!(result.is_ok());
    assert_eq!(result.unwrap().name(), "ensemble");
}

#[tokio::test]
async fn test_parallel_empty_agents_rejected() {
    let result = ParallelAgent::new("empty", vec![]);
    assert!(result.is_err());
}

#[tokio::test]
async fn test_parallel_all_succeed() {
    let agents = vec![echo("m1"), echo("m2"), echo("m3")];
    let par = ParallelAgent::new("parallel", agents).unwrap();
    let result = par.process(Message::with_text("user", "analyze")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_parallel_partial_failure_returns_error() {
    // composition::ParallelAgent fails if ANY agent fails (strict mode)
    let agents: Vec<Arc<dyn Agent>> = vec![echo("ok"), Arc::new(ErrorAgent)];
    let par = ParallelAgent::new("strict", agents).unwrap();
    let result = par.process(Message::with_text("user", "test")).await;
    // Composition parallel is strict: any failure → overall failure
    assert!(result.is_err());
}

#[tokio::test]
async fn test_parallel_single_agent() {
    let agents = vec![echo("solo")];
    let par = ParallelAgent::new("single", agents).unwrap();
    let result = par.process(Message::with_text("user", "test")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_parallel_metadata_includes_agent_count() {
    let agents = vec![echo("a"), echo("b"), echo("c")];
    let par = ParallelAgent::new("ensemble", agents).unwrap();
    let result = par
        .process(Message::with_text("user", "test"))
        .await
        .unwrap();
    // Should have metadata about parallel execution
    assert!(!result.metadata.is_empty());
}

#[tokio::test]
async fn test_parallel_capabilities_include_parallel() {
    let agents = vec![echo("a")];
    let par = ParallelAgent::new("par", agents).unwrap();
    assert!(par.capabilities().contains(&"parallel".to_string()));
}

// ─────────────────────────────────────────────────────────────────────────────
// Conditional composition tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_conditional_creation() {
    let default = echo("default");
    let cond = ConditionalAgent::new("router", default);
    assert_eq!(cond.name(), "router");
}

#[tokio::test]
async fn test_conditional_routes_to_matching_agent() {
    let default_agent = echo("default");
    let tech_agent = echo("tech");
    let mut cond = ConditionalAgent::new("router", default_agent);
    cond.add_route(content_contains("technical"), tech_agent);

    let result = cond
        .process(Message::with_text("user", "a technical question"))
        .await;
    assert!(result.is_ok());
    let text = result.unwrap().content_as_str().unwrap_or("").to_string();
    assert!(
        text.contains("tech"),
        "expected tech agent response, got: {}",
        text
    );
}

#[tokio::test]
async fn test_conditional_falls_back_to_default() {
    let default_agent = echo("default");
    let tech_agent = echo("tech");
    let mut cond = ConditionalAgent::new("router", default_agent);
    cond.add_route(content_contains("technical"), tech_agent);

    // Non-technical message should go to default
    let result = cond
        .process(Message::with_text("user", "hello there"))
        .await;
    assert!(result.is_ok());
    let text = result.unwrap().content_as_str().unwrap_or("").to_string();
    assert!(
        text.contains("default"),
        "expected default agent, got: {}",
        text
    );
}

#[tokio::test]
async fn test_conditional_no_routes_uses_default() {
    let default_agent = echo("default");
    let cond = ConditionalAgent::new("router", default_agent);
    let result = cond.process(Message::with_text("user", "anything")).await;
    assert!(result.is_ok());
    assert!(result
        .unwrap()
        .content_as_str()
        .unwrap_or("")
        .contains("default"));
}

#[tokio::test]
async fn test_conditional_multiple_routes_first_match_wins() {
    let default_agent = echo("default");
    let agent_a = echo("agent-a");
    let agent_b = echo("agent-b");
    let mut cond = ConditionalAgent::new("router", default_agent);
    cond.add_route(content_contains("hello"), agent_a);
    cond.add_route(content_contains("hello"), agent_b); // also matches, but second

    let result = cond
        .process(Message::with_text("user", "hello world"))
        .await;
    assert!(result.is_ok());
    // First match (agent-a) should win
    let text = result.unwrap().content_as_str().unwrap_or("").to_string();
    assert!(
        text.contains("agent-a"),
        "first match should win, got: {}",
        text
    );
}

#[tokio::test]
async fn test_conditional_metadata_from_matched_agent() {
    let default_agent = echo("default");
    let special = echo("special");
    let mut cond = ConditionalAgent::new("router", default_agent);
    cond.add_route(content_contains("special"), special);

    let result = cond
        .process(Message::with_text("user", "special request"))
        .await
        .unwrap();
    assert!(result.metadata.contains_key("processed_by"));
}

#[tokio::test]
async fn test_conditional_capabilities_include_conditional() {
    let cond = ConditionalAgent::new("router", echo("default"));
    assert!(cond.capabilities().contains(&"conditional".to_string()));
}

#[tokio::test]
async fn test_conditional_condition_receives_message_content() {
    let default_agent = echo("default");
    let target = echo("target");
    let mut cond = ConditionalAgent::new("router", default_agent);
    // Custom condition: check metadata key
    use agenkit::composition::metadata_has_key;
    cond.add_route(metadata_has_key("priority"), target);

    let msg = Message::with_text("user", "important task")
        .with_metadata("priority", serde_json::json!("high"));
    let result = cond.process(msg).await.unwrap();
    let text = result.content_as_str().unwrap_or("");
    assert!(
        text.contains("target"),
        "metadata condition should route to target, got: {}",
        text
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Fallback composition tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_fallback_creation_with_name() {
    let agents = vec![echo("primary"), echo("secondary")];
    let result = FallbackAgent::new("reliable", agents);
    assert!(result.is_ok());
    assert_eq!(result.unwrap().name(), "reliable");
}

#[tokio::test]
async fn test_fallback_empty_agents_rejected() {
    let result = FallbackAgent::new("empty", vec![]);
    assert!(result.is_err());
}

#[tokio::test]
async fn test_fallback_primary_succeeds_no_fallback() {
    let primary = echo("primary");
    let fallback = echo("fallback");
    let agent = FallbackAgent::new("reliable", vec![primary, fallback]).unwrap();
    let result = agent.process(Message::with_text("user", "test")).await;
    assert!(result.is_ok());
    let text = result.unwrap().content_as_str().unwrap_or("").to_string();
    // Primary succeeded, so "primary" should be in output
    assert!(
        text.contains("primary"),
        "primary should handle it, got: {}",
        text
    );
}

#[tokio::test]
async fn test_fallback_primary_fails_uses_fallback() {
    let err_agent = Arc::new(ErrorAgent) as Arc<dyn Agent>;
    let fallback = echo("fallback");
    let agent = FallbackAgent::new("reliable", vec![err_agent, fallback]).unwrap();
    let result = agent.process(Message::with_text("user", "test")).await;
    assert!(result.is_ok());
    let text = result.unwrap().content_as_str().unwrap_or("").to_string();
    assert!(
        text.contains("fallback"),
        "fallback should handle it, got: {}",
        text
    );
}

#[tokio::test]
async fn test_fallback_all_fail_returns_last_error() {
    let agents: Vec<Arc<dyn Agent>> = vec![
        Arc::new(ErrorAgent),
        Arc::new(ErrorAgent),
        Arc::new(ErrorAgent),
    ];
    let agent = FallbackAgent::new("all-fail", agents).unwrap();
    let result = agent.process(Message::with_text("user", "test")).await;
    assert!(result.is_err());
}

#[tokio::test]
async fn test_fallback_chain_of_three() {
    // First two fail, third succeeds
    let err1 = Arc::new(ErrorAgent) as Arc<dyn Agent>;
    let err2 = Arc::new(ErrorAgent) as Arc<dyn Agent>;
    let last = echo("last-resort");
    let agent = FallbackAgent::new("chain", vec![err1, err2, last]).unwrap();
    let result = agent.process(Message::with_text("user", "test")).await;
    assert!(result.is_ok());
    let text = result.unwrap().content_as_str().unwrap_or("").to_string();
    assert!(
        text.contains("last-resort"),
        "last resort should handle it, got: {}",
        text
    );
}

#[tokio::test]
async fn test_fallback_single_agent_success() {
    let agent = FallbackAgent::new("single", vec![echo("only")]).unwrap();
    let result = agent.process(Message::with_text("user", "test")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_fallback_capabilities_include_fallback() {
    let agent = FallbackAgent::new("f", vec![echo("a")]).unwrap();
    assert!(agent.capabilities().contains(&"fallback".to_string()));
}

#[tokio::test]
async fn test_fallback_not_called_on_primary_success() {
    // Track if fallback was called using a counting mechanism
    use std::sync::atomic::{AtomicUsize, Ordering};
    struct TrackingAgent {
        calls: Arc<AtomicUsize>,
    }
    #[async_trait]
    impl Agent for TrackingAgent {
        fn name(&self) -> &str {
            "tracker"
        }
        async fn process(&self, _msg: Message) -> Result<Message, AgentError> {
            self.calls.fetch_add(1, Ordering::SeqCst);
            Ok(Message::with_text("assistant", "tracked"))
        }
    }

    let fallback_calls = Arc::new(AtomicUsize::new(0));
    let tracker = Arc::new(TrackingAgent {
        calls: Arc::clone(&fallback_calls),
    });
    let agents: Vec<Arc<dyn Agent>> = vec![echo("primary"), tracker];
    let agent = FallbackAgent::new("reliable", agents).unwrap();
    let _ = agent.process(Message::with_text("user", "test")).await;
    // Fallback should NOT have been called since primary succeeded
    assert_eq!(fallback_calls.load(Ordering::SeqCst), 0);
}

// ─────────────────────────────────────────────────────────────────────────────
// Module-level tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_composition_exports_accessible() {
    use agenkit::composition::{
        and_conditions, content_contains, metadata_equals, metadata_has_key, not_condition,
        or_conditions, role_equals, AgentResult, Condition, ConditionalAgent, ConditionalRoute,
        FallbackAgent, ParallelAgent, SequentialAgent,
    };
    // All types should be importable and usable
    let _: Option<ConditionalAgent> = None;
    let _: Option<FallbackAgent> = None;
    let _: Option<ParallelAgent> = None;
    let _: Option<SequentialAgent> = None;
    let _ = content_contains("test");
    let _ = role_equals("user");
    let _ = metadata_has_key("key");
}

#[tokio::test]
async fn test_composition_composition_of_compositions() {
    // SequentialAgent(FallbackAgent, ConditionalAgent) — compose compositions
    let fallback = FallbackAgent::new("fb", vec![echo("a"), echo("b")]).unwrap();
    let cond = {
        let mut c = ConditionalAgent::new("cond", echo("default"));
        c.add_route(content_contains("tech"), echo("tech"));
        c
    };
    let pipeline: Vec<Arc<dyn Agent>> = vec![Arc::new(fallback), Arc::new(cond)];
    let seq = SequentialAgent::new("composed", pipeline).unwrap();
    let result = seq.process(Message::with_text("user", "tech query")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_composition_condition_utilities() {
    use agenkit::composition::{and_conditions, content_contains, not_condition, or_conditions};

    let tech_cond = content_contains("tech");
    let not_tech = not_condition(content_contains("tech"));
    let either = or_conditions(vec![content_contains("tech"), content_contains("science")]);
    let both = and_conditions(vec![content_contains("tech"), content_contains("science")]);

    let tech_msg = Message::with_text("user", "tech question");
    let other_msg = Message::with_text("user", "other question");

    assert!(tech_cond(&tech_msg));
    assert!(!tech_cond(&other_msg));
    assert!(!not_tech(&tech_msg));
    assert!(not_tech(&other_msg));
    assert!(either(&tech_msg));
    assert!(!either(&other_msg));
    assert!(!both(&tech_msg)); // only "tech", not "science"
}

#[tokio::test]
async fn test_composition_agent_result_struct() {
    use agenkit::composition::AgentResult;
    let success = AgentResult {
        agent_name: "test".to_string(),
        message: Some(Message::with_text("assistant", "ok")),
        error: None,
    };
    assert_eq!(success.agent_name, "test");
    assert!(success.message.is_some());
    assert!(success.error.is_none());
}

#[tokio::test]
async fn test_composition_no_naming_conflicts() {
    // patterns::SequentialAgent and composition::SequentialAgent are different types
    use agenkit::patterns::SequentialAgent as PatternSeq;
    let p_agents: Vec<Arc<dyn Agent>> = vec![echo("a")];
    let _pattern_seq = PatternSeq::new(p_agents).unwrap();

    let c_agents: Vec<Arc<dyn Agent>> = vec![echo("b")];
    let _comp_seq = SequentialAgent::new("comp", c_agents).unwrap();
    // Both coexist without naming conflicts
}
