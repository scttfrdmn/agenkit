//! Tests that per-call options reach every LLM call in every reasoning technique (#801).
//!
//! The failure being guarded against is not an exception — it is a phase of a
//! multi-phase technique that forgets to forward its options. That phase still
//! produces a response, so only the entry path distinguishes it from a working one,
//! and only an assertion that the phase actually ran keeps the forwarding assertion
//! from being vacuous.

use agenkit::core::{supports_options, Agent, AgentError, CallOptions, Message, OptionsAgent};
use agenkit::techniques::reasoning::{
    ChainOfThoughtAgent, ChainOfThoughtConfig, GraphOfThoughtAgent, GraphOfThoughtConfig,
    LeastToMostAgent, LeastToMostConfig, PlanAndSolveAgent, PlanAndSolveConfig, SearchStrategy,
    SelfConsistencyAgent, SelfConsistencyConfig, TreeOfThoughtAgent, TreeOfThoughtConfig,
    VotingStrategy,
};
use async_trait::async_trait;
use std::sync::{Arc, Mutex};

/// Answers by prompt rather than round-robin.
///
/// Several techniques need this: their later phases are gated on the shape of
/// earlier answers, and a fixed response can drive them down a path that never
/// reaches the phase under test.
type Responder = Arc<dyn Fn(&str) -> String + Send + Sync>;

/// An agent that records how each call arrived and what it carried.
struct RecordingAgent {
    responder: Responder,
    state: Mutex<Recorded>,
}

#[derive(Default)]
struct Recorded {
    plain_calls: usize,
    option_calls: usize,
    prompts: Vec<String>,
    /// One entry per call: the options it carried, or `None` for the plain path.
    seen: Vec<Option<CallOptions>>,
}

impl RecordingAgent {
    fn new() -> Arc<Self> {
        Self::with_responder(|_| "The answer is 42.".to_string())
    }

    fn with_responder<F>(responder: F) -> Arc<Self>
    where
        F: Fn(&str) -> String + Send + Sync + 'static,
    {
        Arc::new(Self {
            responder: Arc::new(responder),
            state: Mutex::new(Recorded::default()),
        })
    }

    fn answer(&self, message: &Message) -> Message {
        let prompt = message.content_as_str().unwrap_or("").to_string();
        let reply = (self.responder)(&prompt);
        self.state.lock().unwrap().prompts.push(prompt);
        Message::with_text("assistant", reply)
    }

    fn plain_calls(&self) -> usize {
        self.state.lock().unwrap().plain_calls
    }

    fn option_calls(&self) -> usize {
        self.state.lock().unwrap().option_calls
    }

    /// Whether any call carried a prompt containing `substr`.
    ///
    /// Used to prove a gated phase was actually exercised.
    fn saw_prompt_containing(&self, substr: &str) -> bool {
        self.state
            .lock()
            .unwrap()
            .prompts
            .iter()
            .any(|prompt| prompt.contains(substr))
    }

    /// The temperature each call carried, `None` where a call took the plain path.
    fn temperatures(&self) -> Vec<Option<f64>> {
        self.state
            .lock()
            .unwrap()
            .seen
            .iter()
            .map(|options| options.as_ref().and_then(|o| o.temperature))
            .collect()
    }

    fn max_tokens(&self) -> Vec<Option<u32>> {
        self.state
            .lock()
            .unwrap()
            .seen
            .iter()
            .map(|options| options.as_ref().and_then(|o| o.max_tokens))
            .collect()
    }

    /// Assert every call went through `process_with` with `want` as its temperature.
    ///
    /// "Every" is the point: a temperature that reaches only some of the LLM calls in
    /// a multi-phase technique is not the temperature the caller asked for.
    fn assert_every_call_carried_temperature(&self, want: f64) {
        let temperatures = self.temperatures();
        assert!(
            !temperatures.is_empty(),
            "the agent was never called; the test proves nothing"
        );
        assert_eq!(
            self.plain_calls(),
            0,
            "some call took the plain path and dropped its options"
        );
        assert_eq!(
            temperatures,
            vec![Some(want); temperatures.len()],
            "not every call carried temperature {}",
            want
        );
    }
}

#[async_trait]
impl Agent for RecordingAgent {
    fn name(&self) -> &str {
        "recording_agent"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["mock".to_string(), "options".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        {
            let mut state = self.state.lock().unwrap();
            state.plain_calls += 1;
            state.seen.push(None);
        }
        Ok(self.answer(&message))
    }

    fn as_options_agent(&self) -> Option<&dyn OptionsAgent> {
        Some(self)
    }
}

#[async_trait]
impl OptionsAgent for RecordingAgent {
    async fn process_with(
        &self,
        message: Message,
        options: &CallOptions,
    ) -> Result<Message, AgentError> {
        {
            let mut state = self.state.lock().unwrap();
            state.option_calls += 1;
            state.seen.push(Some(options.clone()));
        }
        Ok(self.answer(&message))
    }
}

/// An agent with no options capability, used to prove the drop is reported.
struct PlainAgent;

#[async_trait]
impl Agent for PlainAgent {
    fn name(&self) -> &str {
        "plain"
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        Ok(Message::with_text("assistant", "The answer is 42."))
    }
}

// ============================================================================
// Capability advertisement
// ============================================================================

// A reasoning technique that cannot take options cannot be driven by a wrapper
// such as SelfConsistencyAgent. Checked for all six so adding one that forgets
// `as_options_agent` fails here rather than silently dropping options at runtime.
#[test]
fn test_every_reasoning_technique_advertises_the_options_capability() {
    let techniques: Vec<(&str, Box<dyn Agent>)> = vec![
        (
            "ChainOfThoughtAgent",
            Box::new(ChainOfThoughtAgent::new(
                Arc::new(PlainAgent),
                ChainOfThoughtConfig::default(),
            )),
        ),
        (
            "SelfConsistencyAgent",
            Box::new(SelfConsistencyAgent::new(
                Arc::new(PlainAgent),
                SelfConsistencyConfig::default(),
            )),
        ),
        (
            "TreeOfThoughtAgent",
            Box::new(TreeOfThoughtAgent::new(
                Arc::new(PlainAgent),
                TreeOfThoughtConfig::default(),
            )),
        ),
        (
            "GraphOfThoughtAgent",
            Box::new(GraphOfThoughtAgent::new(
                Arc::new(PlainAgent),
                GraphOfThoughtConfig::default(),
            )),
        ),
        (
            "LeastToMostAgent",
            Box::new(LeastToMostAgent::new(
                Arc::new(PlainAgent),
                LeastToMostConfig::default(),
            )),
        ),
        (
            "PlanAndSolveAgent",
            Box::new(PlanAndSolveAgent::new(
                Arc::new(PlainAgent),
                PlanAndSolveConfig::default(),
            )),
        ),
    ];

    for (name, technique) in &techniques {
        assert!(
            supports_options(technique.as_ref()),
            "{} does not implement OptionsAgent",
            name
        );
    }
}

// A plain agent must not claim the capability, or `process_with_options` would
// route to a `process_with` that does not exist.
#[test]
fn test_a_plain_agent_does_not_advertise_the_capability() {
    assert!(!supports_options(&PlainAgent));
}

// ============================================================================
// SelfConsistency — the technique whose temperature config was silently discarded
// ============================================================================

#[tokio::test]
async fn test_self_consistency_forwards_the_configured_temperature_to_every_sample() {
    let agent = RecordingAgent::new();
    let sc = SelfConsistencyAgent::new(
        agent.clone(),
        SelfConsistencyConfig {
            num_samples: 4,
            temperature: Some(0.9),
            ..Default::default()
        },
    );

    sc.process(Message::with_text("user", "Q")).await.unwrap();

    assert_eq!(agent.option_calls(), 4);
    agent.assert_every_call_carried_temperature(0.9);
}

#[tokio::test]
async fn test_self_consistency_treats_a_temperature_of_zero_as_set() {
    // 0 is greedy decoding — a real request, not "unset". Any representation that
    // conflates the two is how the option got dropped in the first place.
    let agent = RecordingAgent::new();
    let sc = SelfConsistencyAgent::new(
        agent.clone(),
        SelfConsistencyConfig {
            num_samples: 2,
            temperature: Some(0.0),
            ..Default::default()
        },
    );

    let response = sc.process(Message::with_text("user", "Q")).await.unwrap();

    agent.assert_every_call_carried_temperature(0.0);
    assert_eq!(response.metadata["temperature"], serde_json::json!(0.0));
    assert_eq!(response.metadata["temperature_applied"], true);
}

#[tokio::test]
async fn test_self_consistency_sends_no_options_when_no_temperature_is_configured() {
    // An unset temperature must be omitted, not forwarded as zero: sampling at 0
    // would override whatever the wrapped agent was configured with, and would
    // destroy the very diversity this technique depends on.
    let agent = RecordingAgent::new();
    let sc = SelfConsistencyAgent::new(
        agent.clone(),
        SelfConsistencyConfig {
            num_samples: 3,
            ..Default::default()
        },
    );

    let response = sc.process(Message::with_text("user", "Q")).await.unwrap();

    assert_eq!(agent.plain_calls(), 3);
    assert_eq!(agent.option_calls(), 0);
    assert!(response.metadata["temperature"].is_null());
    // Nothing was requested, so nothing was dropped.
    assert_eq!(response.metadata["temperature_applied"], true);
}

#[tokio::test]
async fn test_self_consistency_reports_temperature_applied_false_for_a_plain_agent() {
    // The drop has to be visible. An agent without the options capability cannot
    // honour a temperature, and a caller that set one needs to be able to find that
    // out — silently accepting it is the bug.
    let sc = SelfConsistencyAgent::new(
        Arc::new(PlainAgent),
        SelfConsistencyConfig {
            num_samples: 2,
            temperature: Some(0.8),
            ..Default::default()
        },
    );

    assert!(!sc.temperature_applied());

    let response = sc.process(Message::with_text("user", "Q")).await.unwrap();

    assert_eq!(response.metadata["temperature_applied"], false);
    // The requested value is still reported, so "asked for 0.8 and did not get it"
    // is distinguishable from "never asked".
    assert_eq!(response.metadata["temperature"], serde_json::json!(0.8));
}

#[test]
fn test_self_consistency_reports_temperature_applied_true_when_none_is_set() {
    let sc = SelfConsistencyAgent::new(Arc::new(PlainAgent), SelfConsistencyConfig::default());
    assert!(sc.temperature_applied());
}

#[test]
#[should_panic(expected = "temperature must be between 0 and 2")]
fn test_self_consistency_rejects_a_temperature_above_the_range() {
    // Fail where the value was set, not on the first sample.
    SelfConsistencyAgent::new(
        Arc::new(PlainAgent),
        SelfConsistencyConfig {
            temperature: Some(2.1),
            ..Default::default()
        },
    );
}

#[test]
#[should_panic(expected = "temperature must be between 0 and 2")]
fn test_self_consistency_rejects_a_negative_temperature() {
    SelfConsistencyAgent::new(
        Arc::new(PlainAgent),
        SelfConsistencyConfig {
            temperature: Some(-0.1),
            ..Default::default()
        },
    );
}

#[tokio::test]
async fn test_self_consistency_overrides_the_callers_temperature_with_its_own() {
    // Deliberate: this technique's correctness depends on sampling diversity, so a
    // caller reaching through it must not silently flatten the samples.
    let agent = RecordingAgent::new();
    let sc = SelfConsistencyAgent::new(
        agent.clone(),
        SelfConsistencyConfig {
            num_samples: 2,
            temperature: Some(1.1),
            ..Default::default()
        },
    );

    sc.process_with(
        Message::with_text("user", "Q"),
        &CallOptions::new().with_temperature(0.0).with_max_tokens(64),
    )
    .await
    .unwrap();

    agent.assert_every_call_carried_temperature(1.1);
    // Every other option passes through untouched.
    assert_eq!(agent.max_tokens(), vec![Some(64), Some(64)]);
}

#[tokio::test]
async fn test_self_consistency_keeps_its_own_temperature_when_the_caller_sets_none() {
    // An unset temperature in the caller's options must read as "did not ask", not as
    // a request to clear the configured value.
    let agent = RecordingAgent::new();
    let sc = SelfConsistencyAgent::new(
        agent.clone(),
        SelfConsistencyConfig {
            num_samples: 2,
            temperature: Some(0.7),
            ..Default::default()
        },
    );

    sc.process_with(
        Message::with_text("user", "Q"),
        &CallOptions::new().with_max_tokens(32),
    )
    .await
    .unwrap();

    agent.assert_every_call_carried_temperature(0.7);
    assert_eq!(agent.max_tokens(), vec![Some(32), Some(32)]);
}

#[tokio::test]
async fn test_self_consistency_forwards_through_a_chain_of_thought() {
    // The realistic composition: SelfConsistency samples a ChainOfThought, which owns
    // no LLM and must pass the options down to the agent that does. A break anywhere
    // in that chain leaves the temperature unapplied.
    let agent = RecordingAgent::with_responder(|_| "1. Think\n2. Conclude\nTherefore, 42".into());
    let cot = ChainOfThoughtAgent::new(agent.clone(), ChainOfThoughtConfig::default());
    let sc = SelfConsistencyAgent::new(
        Arc::new(cot),
        SelfConsistencyConfig {
            num_samples: 3,
            temperature: Some(1.2),
            ..Default::default()
        },
    );

    assert!(sc.temperature_applied());
    sc.process(Message::with_text("user", "Q")).await.unwrap();

    assert_eq!(agent.option_calls(), 3);
    agent.assert_every_call_carried_temperature(1.2);
}

#[tokio::test]
async fn test_self_consistency_voting_still_works_with_a_temperature_set() {
    // Threading options must not disturb the technique's own behaviour.
    let agent = RecordingAgent::new();
    let sc = SelfConsistencyAgent::new(
        agent.clone(),
        SelfConsistencyConfig {
            num_samples: 3,
            voting_strategy: VotingStrategy::Majority,
            temperature: Some(0.5),
            ..Default::default()
        },
    );

    let response = sc.process(Message::with_text("user", "Q")).await.unwrap();

    assert_eq!(response.metadata["num_samples"], 3);
    assert_eq!(
        response.metadata["consistency_score"],
        serde_json::json!(1.0)
    );
}

// ============================================================================
// process() must not manufacture options
// ============================================================================

#[tokio::test]
async fn test_process_leaves_chain_of_thought_on_the_plain_path() {
    // `process()` means "no per-call options". It must not synthesise an empty set
    // and route through `process_with`, which would make every wrapped agent see an
    // options call it never got before.
    let agent = RecordingAgent::with_responder(|_| "1. Step\n2. Step\nTherefore, done".into());
    let cot = ChainOfThoughtAgent::new(agent.clone(), ChainOfThoughtConfig::default());

    cot.process(Message::with_text("user", "Q")).await.unwrap();

    assert_eq!(agent.plain_calls(), 1);
    assert_eq!(agent.option_calls(), 0);
}

#[tokio::test]
async fn test_chain_of_thought_forwards_options() {
    let agent = RecordingAgent::with_responder(|_| "1. Step\n2. Step\nTherefore, done".into());
    let cot = ChainOfThoughtAgent::new(agent.clone(), ChainOfThoughtConfig::default());

    cot.process_with(
        Message::with_text("user", "Q"),
        &CallOptions::new().with_temperature(0.2),
    )
    .await
    .unwrap();

    assert_eq!(agent.option_calls(), 1);
    agent.assert_every_call_carried_temperature(0.2);
}

// ============================================================================
// Multi-phase techniques — every phase, not just the first
// ============================================================================

#[tokio::test]
async fn test_least_to_most_forwards_options_to_decomposition_and_every_subproblem() {
    // If only decompose forwards, the subproblem solves run at the wrong temperature
    // and nothing reports it.
    let agent = RecordingAgent::with_responder(|prompt| {
        if prompt.contains("Break down this problem") {
            "1. Calculate 3*4\n2. Calculate 2*5\n3. Add the results".into()
        } else {
            "12".into()
        }
    });
    let ltm = LeastToMostAgent::new(agent.clone(), LeastToMostConfig::default());

    ltm.process_with(
        Message::with_text("user", "Calculate 3*4 + 2*5"),
        &CallOptions::new().with_temperature(0.5),
    )
    .await
    .unwrap();

    // Decompose plus one call per subproblem.
    assert_eq!(agent.option_calls(), 4);
    assert!(
        agent.saw_prompt_containing("Solve this subproblem"),
        "no subproblem was solved; the per-subproblem forward went untested"
    );
    agent.assert_every_call_carried_temperature(0.5);
}

#[tokio::test]
async fn test_plan_and_solve_forwards_options_to_planning_validation_and_every_step() {
    // Validation is the phase most likely to be forgotten, since it is optional.
    let agent = RecordingAgent::with_responder(|prompt| {
        if prompt.contains("completeness and feasibility") {
            "VALID: Plan is complete".into()
        } else if prompt.contains("step-by-step plan") {
            "1. Gather ingredients\n2. Preheat oven".into()
        } else {
            "Step done.".into()
        }
    });
    let pas = PlanAndSolveAgent::new(
        agent.clone(),
        PlanAndSolveConfig {
            validate_plan: true,
            ..Default::default()
        },
    );

    pas.process_with(
        Message::with_text("user", "How do I bake a cake?"),
        &CallOptions::new().with_temperature(0.4),
    )
    .await
    .unwrap();

    // Plan + validate + 2 steps.
    assert_eq!(agent.option_calls(), 4);
    assert!(
        agent.saw_prompt_containing("completeness and feasibility"),
        "validation never ran; the phase under test was not entered"
    );
    assert!(
        agent.saw_prompt_containing("Execute this step"),
        "no step executed; the per-step forward went untested"
    );
    agent.assert_every_call_carried_temperature(0.4);
}

#[tokio::test]
async fn test_plan_and_solve_forwards_options_through_the_replanning_branch() {
    // The replanning branch adds three more LLM calls and only runs when validation
    // rejects the plan, so the happy-path test above never reaches it. A dropped
    // forward in a branch no test enters is invisible.
    let agent = RecordingAgent::with_responder(|prompt| {
        if prompt.contains("Previous Plan Issues") {
            "1. A better first step\n2. A better second step".into()
        } else if prompt.contains("completeness and feasibility") {
            // Neither "VALID" nor "YES" — rejecting the plan is what triggers
            // replanning.
            "This plan is missing error handling.".into()
        } else if prompt.contains("step-by-step plan") {
            "1. Gather ingredients\n2. Preheat oven".into()
        } else {
            "Step done.".into()
        }
    });
    let pas = PlanAndSolveAgent::new(
        agent.clone(),
        PlanAndSolveConfig {
            validate_plan: true,
            allow_replanning: true,
            ..Default::default()
        },
    );

    pas.process_with(
        Message::with_text("user", "How do I bake a cake?"),
        &CallOptions::new().with_temperature(0.3),
    )
    .await
    .unwrap();

    assert!(
        agent.saw_prompt_containing("Previous Plan Issues"),
        "replanning never ran; the branch under test was not entered"
    );
    agent.assert_every_call_carried_temperature(0.3);
}

// Branch diversity is the whole point of Tree-of-Thought, so a temperature that
// reaches only some branches defeats it.
//
// The branch text has to survive the default evaluator's 0.3 prune threshold. Length
// alone does not get there — 138 characters scores 138/500 = 0.276 — so the text also
// needs the +0.2 structure bonus, which requires two numbered markers each at the
// start of a line. A single-line "1. … 2. …" matches only once and is pruned, leaving
// only the root expanded and the recursive expansion — where a dropped forward would
// actually hide — untested.
const LONG_ENOUGH_TO_SURVIVE_PRUNING: &str =
    "1. Decompose the problem into independent parts and examine each in turn.\n\
     2. Recombine the partial results into one answer. Therefore, 42";

async fn assert_tree_of_thought_forwards(strategy: SearchStrategy) {
    let agent = RecordingAgent::with_responder(|_| LONG_ENOUGH_TO_SURVIVE_PRUNING.into());
    let tot = TreeOfThoughtAgent::new(
        agent.clone(),
        TreeOfThoughtConfig {
            strategy,
            branching_factor: 2,
            max_depth: 2,
            ..Default::default()
        },
    );

    tot.process_with(
        Message::with_text("user", "Q"),
        &CallOptions::new().with_temperature(1.1),
    )
    .await
    .unwrap();

    // branching_factor 2 at max_depth 2 means the root plus its two surviving children
    // are each expanded: 2 + 2 + 2 calls. Asserting the count, not just "more than
    // zero", is what proves the recursion ran rather than the root alone.
    assert_eq!(
        agent.option_calls(),
        6,
        "{:?}: expected the root and both children to be expanded",
        strategy
    );
    // Only an expansion below the root carries the parent's branch text in its path.
    assert!(
        agent.saw_prompt_containing(LONG_ENOUGH_TO_SURVIVE_PRUNING),
        "{:?}: no node below the root was expanded; the recursive path went untested",
        strategy
    );
    agent.assert_every_call_carried_temperature(1.1);
}

// All three strategies are exercised: each drives expand_node from its own loop, so
// forwarding fixed in one says nothing about the other two.
#[tokio::test]
async fn test_tree_of_thought_forwards_options_under_bfs() {
    assert_tree_of_thought_forwards(SearchStrategy::BFS).await;
}

#[tokio::test]
async fn test_tree_of_thought_forwards_options_under_dfs() {
    assert_tree_of_thought_forwards(SearchStrategy::DFS).await;
}

#[tokio::test]
async fn test_tree_of_thought_forwards_options_under_best_first() {
    assert_tree_of_thought_forwards(SearchStrategy::BestFirst).await;
}

#[tokio::test]
async fn test_graph_of_thought_forwards_options_to_every_call_in_the_graph_build() {
    // Premises, thought expansion, edge identification and the conclusion. The
    // conclusion phase is gated on the graph not having hit max_nodes, so the mock
    // answers by prompt: a fixed response fills the graph to the cap and that phase
    // never runs, leaving a dropped forward there invisible.
    let agent = RecordingAgent::with_responder(|prompt| {
        if prompt.contains("premises") {
            "1. First premise\n2. Second premise".into()
        } else if prompt.contains("new insights") || prompt.contains("initial thoughts") {
            // Empty breaks the expansion loop, leaving room under max_nodes for the
            // conclusion call.
            String::new()
        } else if prompt.contains("logical relationship") {
            "SUPPORT".into()
        } else {
            "Therefore, 42".into()
        }
    });
    let got = GraphOfThoughtAgent::new(agent.clone(), GraphOfThoughtConfig::default());

    got.process_with(
        Message::with_text("user", "Q"),
        &CallOptions::new().with_temperature(0.6),
    )
    .await
    .unwrap();

    // Each gated phase must have actually run, or the assertion below is vacuous
    // for it.
    for phase in [
        "premises",
        "new insights",
        "logical relationship",
        "Final conclusion",
    ] {
        assert!(
            agent.saw_prompt_containing(phase),
            "the {} phase never ran; a dropped forward there would go unnoticed",
            phase
        );
    }
    agent.assert_every_call_carried_temperature(0.6);
}
