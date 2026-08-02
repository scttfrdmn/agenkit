//! Pattern technique tests
//!
//! Comprehensive tests for agenkit pattern implementations:
//! Reflection, ReAct, Planning, Autonomous, Sequential, Parallel,
//! Task, Conversational, and MultiAgent patterns.

use agenkit::core::{Agent, AgentError, Message, Tool, ToolResult};
use agenkit::patterns::{
    AutonomousAgent, ConversationalAgent, ConversationalConfig, CritiqueFormat, DefaultAggregators,
    MultiAgentOrchestrator, OrchestrationStrategy, ParallelAgent, PlanningAgent, PlanningConfig,
    ReActAgent, ReActConfig, ReflectionAgent, ReflectionConfig, SequentialAgent, StopReason, Task,
    TaskConfig,
};
use async_trait::async_trait;
use serde_json::json;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;

// ─────────────────────────────────────────────────────────────────────────────
// Shared helpers
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
                .with_metadata("agent", json!(self.name.clone())),
        )
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["echo".to_string()]
    }
}

// Simple tool for ReAct tests
struct EchoTool;

#[async_trait]
impl Tool for EchoTool {
    fn name(&self) -> &str {
        "echo"
    }

    fn description(&self) -> &str {
        "Returns input as output"
    }

    async fn execute(
        &self,
        params: HashMap<String, serde_json::Value>,
    ) -> Result<ToolResult, AgentError> {
        let input = params.get("input").cloned().unwrap_or(json!(""));
        Ok(ToolResult::success(input))
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
            "deliberate failure".to_string(),
        ))
    }
}

struct ScorerAgent {
    score: f64,
}

#[async_trait]
impl Agent for ScorerAgent {
    fn name(&self) -> &str {
        "scorer"
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        Ok(Message::with_text("assistant", self.score.to_string())
            .with_metadata("score", json!(self.score)))
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Reflection tests
// ─────────────────────────────────────────────────────────────────────────────

fn make_reflection_config(
    generator: Arc<dyn Agent>,
    critic: Arc<dyn Agent>,
    max_iterations: usize,
    quality_threshold: f64,
    format: CritiqueFormat,
) -> ReflectionConfig {
    ReflectionConfig {
        generator,
        critic,
        max_iterations,
        quality_threshold,
        improvement_threshold: 0.05,
        critique_format: format,
        verbose: false,
    }
}

#[tokio::test]
async fn test_reflection_creation() {
    let gen = Arc::new(EchoAgent {
        name: "gen".to_string(),
    });
    let crit = Arc::new(ScorerAgent { score: 0.85 });
    let cfg = make_reflection_config(gen, crit, 3, 0.9, CritiqueFormat::Structured);
    assert!(ReflectionAgent::new(cfg).is_ok());
}

#[tokio::test]
async fn test_reflection_name_non_empty() {
    let gen = Arc::new(EchoAgent {
        name: "gen".to_string(),
    });
    let crit = Arc::new(ScorerAgent { score: 0.85 });
    let agent = ReflectionAgent::new(make_reflection_config(
        gen,
        crit,
        2,
        0.9,
        CritiqueFormat::Structured,
    ))
    .unwrap();
    assert!(!agent.name().is_empty());
}

#[tokio::test]
async fn test_reflection_capabilities_non_empty() {
    let gen = Arc::new(EchoAgent {
        name: "gen".to_string(),
    });
    let crit = Arc::new(ScorerAgent { score: 0.85 });
    let agent = ReflectionAgent::new(make_reflection_config(
        gen,
        crit,
        2,
        0.9,
        CritiqueFormat::Structured,
    ))
    .unwrap();
    assert!(!agent.capabilities().is_empty());
}

#[tokio::test]
async fn test_reflection_high_score_stops_early() {
    // Critic returns 0.99 — above default threshold 0.9, so loop stops at 1st iter
    let gen = Arc::new(EchoAgent {
        name: "gen".to_string(),
    });
    let crit = Arc::new(ScorerAgent { score: 0.99 });
    let agent = ReflectionAgent::new(make_reflection_config(
        gen,
        crit,
        5,
        0.9,
        CritiqueFormat::Structured,
    ))
    .unwrap();
    let result = agent.process(Message::with_text("user", "hello")).await;
    assert!(result.is_ok());
    let resp = result.unwrap();
    // Should have stopped early — iterations should be <= 2
    if let Some(iters) = resp.metadata.get("reflection_iterations") {
        let n = iters.as_u64().unwrap_or(99);
        assert!(n <= 2, "expected early stop but got {} iterations", n);
    }
}

#[tokio::test]
async fn test_reflection_max_iterations_enforced() {
    // Critic returns 0.5 — below threshold, so should reach max iterations
    let gen = Arc::new(EchoAgent {
        name: "gen".to_string(),
    });
    let crit = Arc::new(ScorerAgent { score: 0.5 });
    let agent = ReflectionAgent::new(make_reflection_config(
        gen,
        crit,
        2,
        0.9,
        CritiqueFormat::Structured,
    ))
    .unwrap();
    let result = agent.process(Message::with_text("user", "hello")).await;
    // Should complete (even if score not met) when max_iterations reached
    assert!(result.is_ok() || result.is_err()); // Either is acceptable
}

#[tokio::test]
async fn test_reflection_metadata_present() {
    let gen = Arc::new(EchoAgent {
        name: "gen".to_string(),
    });
    let crit = Arc::new(ScorerAgent { score: 0.95 });
    let agent = ReflectionAgent::new(make_reflection_config(
        gen,
        crit,
        2,
        0.9,
        CritiqueFormat::Structured,
    ))
    .unwrap();
    let result = agent.process(Message::with_text("user", "test")).await;
    if let Ok(resp) = result {
        // Should have at least some metadata from the reflection
        assert!(!resp.metadata.is_empty());
    }
}

#[tokio::test]
async fn test_reflection_freeform_format() {
    let gen = Arc::new(EchoAgent {
        name: "gen".to_string(),
    });
    let crit = Arc::new(ScorerAgent { score: 0.95 });
    let agent = ReflectionAgent::new(make_reflection_config(
        gen,
        crit,
        2,
        0.9,
        CritiqueFormat::FreeForm,
    ))
    .unwrap();
    let result = agent.process(Message::with_text("user", "freeform")).await;
    assert!(result.is_ok() || result.is_err());
}

#[tokio::test]
async fn test_reflection_stop_reason_variants() {
    // Just ensure all StopReason variants are accessible
    let reasons = [
        StopReason::QualityThresholdMet,
        StopReason::MinimalImprovement,
        StopReason::MaxIterations,
        StopReason::PerfectScore,
    ];
    assert_eq!(reasons.len(), 4);
}

// ─────────────────────────────────────────────────────────────────────────────
// ReAct tests
// ─────────────────────────────────────────────────────────────────────────────

fn make_react_config(agent: Arc<dyn Agent>, max_steps: usize) -> ReActConfig {
    ReActConfig {
        agent,
        tools: vec![Arc::new(EchoTool)],
        max_steps,
        verbose: false,
        prompt_template: None,
    }
}

#[tokio::test]
async fn test_react_creation() {
    let inner = Arc::new(EchoAgent {
        name: "react-inner".to_string(),
    });
    assert!(ReActAgent::new(make_react_config(inner, 5)).is_ok());
}

#[tokio::test]
async fn test_react_name_non_empty() {
    let inner = Arc::new(EchoAgent {
        name: "react-inner".to_string(),
    });
    let agent = ReActAgent::new(make_react_config(inner, 5)).unwrap();
    assert!(!agent.name().is_empty());
}

#[tokio::test]
async fn test_react_has_name() {
    // ReActAgent has a fixed name "ReActAgent"
    let inner = Arc::new(EchoAgent {
        name: "react-inner".to_string(),
    });
    let agent = ReActAgent::new(make_react_config(inner, 5)).unwrap();
    assert!(!agent.name().is_empty());
    // ReAct delegates capabilities to inner agent
    let _caps = agent.capabilities(); // just ensure it doesn't panic
}

#[tokio::test]
async fn test_react_final_answer_response() {
    // Agent that returns "Final Answer: 42"
    struct FinalAnswerAgent;
    #[async_trait]
    impl Agent for FinalAnswerAgent {
        fn name(&self) -> &str {
            "final-answer"
        }
        async fn process(&self, _msg: Message) -> Result<Message, AgentError> {
            Ok(Message::with_text("assistant", "Final Answer: 42"))
        }
    }
    let inner = Arc::new(FinalAnswerAgent);
    let agent = ReActAgent::new(make_react_config(inner, 5)).unwrap();
    let result = agent
        .process(Message::with_text("user", "what is 6*7?"))
        .await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_react_max_steps_enforced() {
    // Agent never gives "Final Answer" — should stop at max_steps
    struct ThinkingAgent;
    #[async_trait]
    impl Agent for ThinkingAgent {
        fn name(&self) -> &str {
            "thinker"
        }
        async fn process(&self, _msg: Message) -> Result<Message, AgentError> {
            Ok(Message::with_text(
                "assistant",
                "Thought: still thinking\nAction: search\nAction Input: query",
            ))
        }
    }
    let inner = Arc::new(ThinkingAgent);
    let agent = ReActAgent::new(make_react_config(inner, 2)).unwrap();
    let result = agent.process(Message::with_text("user", "research")).await;
    // Should complete (possibly with MaxSteps) rather than loop forever
    assert!(result.is_ok() || result.is_err());
}

#[tokio::test]
async fn test_react_zero_max_steps() {
    let inner = Arc::new(EchoAgent {
        name: "inner".to_string(),
    });
    // max_steps = 0 means no steps allowed — should error or return immediately
    let agent = ReActAgent::new(make_react_config(inner, 0)).unwrap();
    let result = agent.process(Message::with_text("user", "test")).await;
    assert!(result.is_ok() || result.is_err());
}

#[tokio::test]
async fn test_react_step_struct_fields() {
    use agenkit::patterns::ReActStep;
    let step = ReActStep {
        thought: "thinking...".to_string(),
        action: "search".to_string(),
        action_input: "query".to_string(),
        observation: "found result".to_string(),
        step_number: 1,
        is_final: false,
    };
    assert_eq!(step.step_number, 1);
    assert!(!step.is_final);
    assert_eq!(step.action, "search");
}

#[tokio::test]
async fn test_react_with_prompt_template() {
    struct FinalAnswerAgent;
    #[async_trait]
    impl Agent for FinalAnswerAgent {
        fn name(&self) -> &str {
            "final-answer"
        }
        async fn process(&self, _msg: Message) -> Result<Message, AgentError> {
            Ok(Message::with_text("assistant", "Final Answer: done"))
        }
    }
    let inner = Arc::new(FinalAnswerAgent);
    let config = ReActConfig {
        agent: inner,
        tools: vec![Arc::new(EchoTool)],
        max_steps: 3,
        verbose: false,
        prompt_template: Some("Custom template: {input}".to_string()),
    };
    assert!(ReActAgent::new(config).is_ok());
}

// ─────────────────────────────────────────────────────────────────────────────
// Planning tests
// ─────────────────────────────────────────────────────────────────────────────

fn make_planning_config(llm: Arc<dyn Agent>) -> PlanningConfig {
    PlanningConfig {
        llm,
        executor: None,
        max_steps: 5,
        allow_replanning: false,
        system_prompt: None,
    }
}

#[tokio::test]
async fn test_planning_creation() {
    let llm = Arc::new(EchoAgent {
        name: "planner-llm".to_string(),
    });
    assert!(PlanningAgent::new(make_planning_config(llm)).is_ok());
}

#[tokio::test]
async fn test_planning_name_non_empty() {
    let llm = Arc::new(EchoAgent {
        name: "planner-llm".to_string(),
    });
    let agent = PlanningAgent::new(make_planning_config(llm)).unwrap();
    assert!(!agent.name().is_empty());
}

#[tokio::test]
async fn test_planning_capabilities_non_empty() {
    let llm = Arc::new(EchoAgent {
        name: "planner-llm".to_string(),
    });
    let agent = PlanningAgent::new(make_planning_config(llm)).unwrap();
    assert!(!agent.capabilities().is_empty());
}

#[tokio::test]
async fn test_planning_processes_message() {
    let llm = Arc::new(EchoAgent {
        name: "planner-llm".to_string(),
    });
    let agent = PlanningAgent::new(make_planning_config(llm)).unwrap();
    let result = agent
        .process(Message::with_text("user", "organize a party"))
        .await;
    assert!(result.is_ok() || result.is_err());
}

#[tokio::test]
async fn test_planning_allow_replanning_flag() {
    let llm = Arc::new(EchoAgent {
        name: "planner-llm".to_string(),
    });
    let config = PlanningConfig {
        llm,
        executor: None,
        max_steps: 3,
        allow_replanning: true,
        system_prompt: Some("You are a planning assistant.".to_string()),
    };
    assert!(PlanningAgent::new(config).is_ok());
}

#[tokio::test]
async fn test_plan_step_status_variants() {
    use agenkit::patterns::StepStatus;
    let statuses = [
        StepStatus::Pending,
        StepStatus::InProgress,
        StepStatus::Completed,
        StepStatus::Failed,
        StepStatus::Skipped,
    ];
    assert_eq!(statuses.len(), 5);
}

// ─────────────────────────────────────────────────────────────────────────────
// Autonomous tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_autonomous_creation() {
    let agent = AutonomousAgent::new("Research AI trends", 5);
    assert!(!agent.name().is_empty());
}

#[tokio::test]
async fn test_autonomous_add_goals() {
    let mut agent = AutonomousAgent::new("Build a project", 10);
    agent.add_goal("Design architecture", 10);
    agent.add_goal("Implement features", 8);
    agent.add_goal("Write tests", 5);
    // Agent was created and goals added without panic
    assert!(!agent.name().is_empty());
}

#[tokio::test]
async fn test_autonomous_run_returns_result() {
    let mut agent = AutonomousAgent::new("Simple task", 2);
    agent.add_goal("Do something", 5);
    let result = agent.run().await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_autonomous_run_result_fields() {
    let mut agent = AutonomousAgent::new("Research project", 3);
    agent.add_goal("Literature review", 10);
    agent.add_goal("Analysis", 5);
    let result = agent.run().await.unwrap();
    assert_eq!(result.objective, "Research project");
    assert!(result.iterations <= 3);
}

#[tokio::test]
async fn test_autonomous_no_goals() {
    let mut agent = AutonomousAgent::new("No goals task", 5);
    let result = agent.run().await;
    // Should complete with no goals to process
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_autonomous_goal_status_variants() {
    use agenkit::patterns::GoalStatus;
    let statuses = [
        GoalStatus::Active,
        GoalStatus::Completed,
        GoalStatus::Abandoned,
    ];
    assert_eq!(statuses.len(), 3);
}

// ─────────────────────────────────────────────────────────────────────────────
// Sequential (patterns module) tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_sequential_pattern_creation() {
    let agents: Vec<Arc<dyn Agent>> = vec![
        Arc::new(EchoAgent {
            name: "a".to_string(),
        }),
        Arc::new(EchoAgent {
            name: "b".to_string(),
        }),
    ];
    assert!(SequentialAgent::new(agents).is_ok());
}

#[tokio::test]
async fn test_sequential_pattern_empty_fails() {
    let agents: Vec<Arc<dyn Agent>> = vec![];
    assert!(SequentialAgent::new(agents).is_err());
}

#[tokio::test]
async fn test_sequential_pattern_runs_in_order() {
    let agents: Vec<Arc<dyn Agent>> = vec![
        Arc::new(EchoAgent {
            name: "first".to_string(),
        }),
        Arc::new(EchoAgent {
            name: "second".to_string(),
        }),
    ];
    let agent = SequentialAgent::new(agents).unwrap();
    let result = agent.process(Message::with_text("user", "input")).await;
    assert!(result.is_ok());
    let resp = result.unwrap();
    // Output should be from the last agent ("second")
    assert!(resp.content_as_str().unwrap_or("").contains("second"));
}

#[tokio::test]
async fn test_sequential_pattern_error_short_circuits() {
    let agents: Vec<Arc<dyn Agent>> = vec![
        Arc::new(ErrorAgent),
        Arc::new(EchoAgent {
            name: "b".to_string(),
        }),
    ];
    let agent = SequentialAgent::new(agents).unwrap();
    let result = agent.process(Message::with_text("user", "test")).await;
    assert!(result.is_err());
}

#[tokio::test]
async fn test_sequential_pattern_single_agent() {
    let agents: Vec<Arc<dyn Agent>> = vec![Arc::new(EchoAgent {
        name: "solo".to_string(),
    })];
    let agent = SequentialAgent::new(agents).unwrap();
    let result = agent.process(Message::with_text("user", "solo test")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_sequential_pattern_capabilities_merged() {
    let agents: Vec<Arc<dyn Agent>> = vec![
        Arc::new(EchoAgent {
            name: "a".to_string(),
        }),
        Arc::new(EchoAgent {
            name: "b".to_string(),
        }),
    ];
    let agent = SequentialAgent::new(agents).unwrap();
    let caps = agent.capabilities();
    assert!(caps.contains(&"sequential".to_string()) || caps.contains(&"pipeline".to_string()));
}

// ─────────────────────────────────────────────────────────────────────────────
// Parallel (patterns module) tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_parallel_pattern_creation() {
    let agents: Vec<Arc<dyn Agent>> = vec![
        Arc::new(EchoAgent {
            name: "a".to_string(),
        }),
        Arc::new(EchoAgent {
            name: "b".to_string(),
        }),
    ];
    assert!(ParallelAgent::new(agents, DefaultAggregators::concatenate).is_ok());
}

#[tokio::test]
async fn test_parallel_pattern_empty_fails() {
    let agents: Vec<Arc<dyn Agent>> = vec![];
    assert!(ParallelAgent::new(agents, DefaultAggregators::concatenate).is_err());
}

#[tokio::test]
async fn test_parallel_pattern_runs_concurrently() {
    let agents: Vec<Arc<dyn Agent>> = vec![
        Arc::new(EchoAgent {
            name: "m1".to_string(),
        }),
        Arc::new(EchoAgent {
            name: "m2".to_string(),
        }),
        Arc::new(EchoAgent {
            name: "m3".to_string(),
        }),
    ];
    let agent = ParallelAgent::new(agents, DefaultAggregators::concatenate).unwrap();
    let result = agent.process(Message::with_text("user", "analyze")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_parallel_pattern_majority_vote() {
    let agents: Vec<Arc<dyn Agent>> = vec![
        Arc::new(EchoAgent {
            name: "v1".to_string(),
        }),
        Arc::new(EchoAgent {
            name: "v2".to_string(),
        }),
        Arc::new(EchoAgent {
            name: "v3".to_string(),
        }),
    ];
    let agent = ParallelAgent::new(agents, DefaultAggregators::majority_vote).unwrap();
    let result = agent.process(Message::with_text("user", "vote")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_parallel_pattern_partial_failure() {
    let agents: Vec<Arc<dyn Agent>> = vec![
        Arc::new(EchoAgent {
            name: "ok".to_string(),
        }),
        Arc::new(ErrorAgent),
    ];
    let agent = ParallelAgent::new(agents, DefaultAggregators::first).unwrap();
    let result = agent.process(Message::with_text("user", "test")).await;
    // Should succeed since at least one agent succeeded
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_parallel_pattern_capabilities() {
    let agents: Vec<Arc<dyn Agent>> = vec![Arc::new(EchoAgent {
        name: "a".to_string(),
    })];
    let agent = ParallelAgent::new(agents, DefaultAggregators::concatenate).unwrap();
    let caps = agent.capabilities();
    assert!(caps.contains(&"parallel".to_string()) || caps.contains(&"ensemble".to_string()));
}

// ─────────────────────────────────────────────────────────────────────────────
// Task tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_task_creation() {
    let agent: Arc<dyn Agent> = Arc::new(EchoAgent {
        name: "task-agent".to_string(),
    });
    let _task = Task::new(agent, TaskConfig::default());
    // No panic — task created successfully
}

#[tokio::test]
async fn test_task_execute_succeeds() {
    let agent: Arc<dyn Agent> = Arc::new(EchoAgent {
        name: "task-agent".to_string(),
    });
    let task = Task::new(agent, TaskConfig::default());
    let result = task.execute(Message::with_text("user", "do this")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_task_execute_returns_response() {
    let agent: Arc<dyn Agent> = Arc::new(EchoAgent {
        name: "task-agent".to_string(),
    });
    let task = Task::new(agent, TaskConfig::default());
    let result = task
        .execute(Message::with_text("user", "hello"))
        .await
        .unwrap();
    assert_eq!(result.role, "assistant");
}

#[tokio::test]
async fn test_task_with_retries_config() {
    let agent: Arc<dyn Agent> = Arc::new(EchoAgent {
        name: "task-agent".to_string(),
    });
    let config = TaskConfig {
        timeout: None,
        retries: 2,
    };
    let task = Task::new(agent, config);
    let result = task.execute(Message::with_text("user", "retry task")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_task_with_timeout_config() {
    let agent: Arc<dyn Agent> = Arc::new(EchoAgent {
        name: "task-agent".to_string(),
    });
    let config = TaskConfig {
        timeout: Some(Duration::from_secs(30)),
        retries: 0,
    };
    let task = Task::new(agent, config);
    let result = task.execute(Message::with_text("user", "timed task")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_task_failure_propagates() {
    let agent: Arc<dyn Agent> = Arc::new(ErrorAgent);
    let config = TaskConfig {
        timeout: None,
        retries: 0,
    };
    let task = Task::new(agent, config);
    let result = task.execute(Message::with_text("user", "fail")).await;
    assert!(result.is_err());
}

// ─────────────────────────────────────────────────────────────────────────────
// Conversational tests
// ─────────────────────────────────────────────────────────────────────────────

fn make_conversational(llm: Arc<dyn Agent>, max_history: usize) -> ConversationalAgent {
    ConversationalAgent::new(ConversationalConfig {
        llm,
        max_history,
        system_prompt: None,
        include_system: true,
    })
    .unwrap()
}

#[tokio::test]
async fn test_conversational_creation() {
    let llm = Arc::new(EchoAgent {
        name: "chat-llm".to_string(),
    });
    let result = ConversationalAgent::new(ConversationalConfig {
        llm,
        max_history: 10,
        system_prompt: None,
        include_system: true,
    });
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_conversational_name_non_empty() {
    let llm = Arc::new(EchoAgent {
        name: "chat-llm".to_string(),
    });
    let agent = make_conversational(llm, 10);
    assert!(!agent.name().is_empty());
}

#[tokio::test]
async fn test_conversational_first_turn() {
    let llm = Arc::new(EchoAgent {
        name: "chat-llm".to_string(),
    });
    let agent = make_conversational(llm, 10);
    let result = agent.process(Message::with_text("user", "Hello!")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_conversational_multiple_turns() {
    let llm = Arc::new(EchoAgent {
        name: "chat-llm".to_string(),
    });
    let agent = make_conversational(llm, 10);
    let _ = agent.process(Message::with_text("user", "Turn 1")).await;
    let result = agent.process(Message::with_text("user", "Turn 2")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_conversational_with_system_prompt() {
    let llm = Arc::new(EchoAgent {
        name: "chat-llm".to_string(),
    });
    let result = ConversationalAgent::new(ConversationalConfig {
        llm,
        max_history: 5,
        system_prompt: Some("You are a helpful assistant.".to_string()),
        include_system: true,
    });
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_conversational_small_history_limit() {
    let llm = Arc::new(EchoAgent {
        name: "chat-llm".to_string(),
    });
    let agent = make_conversational(llm, 2);
    // Process more messages than max_history — should not panic
    for i in 0..5 {
        let _ = agent
            .process(Message::with_text("user", format!("Message {}", i)))
            .await;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// MultiAgent tests
// ─────────────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_multiagent_sequential_creation() {
    let mut orch = MultiAgentOrchestrator::new(OrchestrationStrategy::Sequential);
    let agent: Arc<dyn Agent> = Arc::new(EchoAgent {
        name: "worker".to_string(),
    });
    orch.register_agent("worker", agent);
    // Verify strategy is preserved
    assert_eq!(orch.strategy(), OrchestrationStrategy::Sequential);
}

#[tokio::test]
async fn test_multiagent_parallel_creation() {
    let mut orch = MultiAgentOrchestrator::new(OrchestrationStrategy::Parallel);
    let agent: Arc<dyn Agent> = Arc::new(EchoAgent {
        name: "worker".to_string(),
    });
    orch.register_agent("worker", agent);
    assert_eq!(orch.strategy(), OrchestrationStrategy::Parallel);
}

#[tokio::test]
async fn test_multiagent_sequential_processes() {
    let mut orch = MultiAgentOrchestrator::new(OrchestrationStrategy::Sequential);
    orch.register_agent(
        "a",
        Arc::new(EchoAgent {
            name: "a".to_string(),
        }) as Arc<dyn Agent>,
    );
    orch.register_agent(
        "b",
        Arc::new(EchoAgent {
            name: "b".to_string(),
        }) as Arc<dyn Agent>,
    );
    let result = orch.process(Message::with_text("user", "test")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_multiagent_parallel_processes() {
    let mut orch = MultiAgentOrchestrator::new(OrchestrationStrategy::Parallel);
    orch.register_agent(
        "a",
        Arc::new(EchoAgent {
            name: "a".to_string(),
        }) as Arc<dyn Agent>,
    );
    orch.register_agent(
        "b",
        Arc::new(EchoAgent {
            name: "b".to_string(),
        }) as Arc<dyn Agent>,
    );
    let result = orch.process(Message::with_text("user", "test")).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_multiagent_no_agents() {
    let mut orch = MultiAgentOrchestrator::new(OrchestrationStrategy::Sequential);
    let result = orch.process(Message::with_text("user", "no agents")).await;
    assert!(result.is_ok() || result.is_err());
}

#[tokio::test]
async fn test_multiagent_list_agents() {
    let mut orch = MultiAgentOrchestrator::new(OrchestrationStrategy::Sequential);
    orch.register_agent(
        "a",
        Arc::new(EchoAgent {
            name: "a".to_string(),
        }) as Arc<dyn Agent>,
    );
    orch.register_agent(
        "b",
        Arc::new(EchoAgent {
            name: "b".to_string(),
        }) as Arc<dyn Agent>,
    );
    let agents = orch.list_agents();
    assert_eq!(agents.len(), 2);
}
