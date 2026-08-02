// Plan-and-Solve Prompting Technique
//
// Explicitly separates planning (devising a solution strategy) from solving
// (executing the strategy). Creates more structured reasoning than pure CoT
// by forcing an upfront planning phase.
//
// Reference: "Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning"
// Lei Wang et al., 2023 - https://arxiv.org/abs/2305.04091

use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use regex::Regex;
use serde_json::json;
use std::sync::Arc;

#[derive(Debug, Clone)]
pub struct PlanStep {
    pub description: String,
    pub order: usize,
    pub dependencies: Vec<usize>,
    pub estimated_complexity: usize,
    pub result: Option<String>,
    pub executed: bool,
}

#[derive(Debug, Clone)]
pub struct Plan {
    pub steps: Vec<PlanStep>,
    pub problem: String,
    pub strategy: Option<String>,
    pub validated: bool,
    pub validation_notes: Option<String>,
}

pub type PlannerFn = Arc<dyn Fn(&str) -> Result<Plan, AgentError> + Send + Sync>;
pub type SolverFn = Arc<dyn Fn(&PlanStep, &[String]) -> Result<String, AgentError> + Send + Sync>;

pub struct PlanAndSolveConfig {
    pub planner: Option<PlannerFn>,
    pub solver: Option<SolverFn>,
    pub validate_plan: bool,
    pub allow_replanning: bool,
}

impl Default for PlanAndSolveConfig {
    fn default() -> Self {
        Self {
            planner: None,
            solver: None,
            validate_plan: true,
            allow_replanning: false,
        }
    }
}

pub struct PlanAndSolveAgent {
    agent: Arc<dyn Agent>,
    planner: Option<PlannerFn>,
    solver: Option<SolverFn>,
    validate_plan: bool,
    allow_replanning: bool,
}

impl PlanAndSolveAgent {
    pub fn new(agent: Arc<dyn Agent>, config: PlanAndSolveConfig) -> Self {
        Self {
            agent,
            planner: config.planner,
            solver: config.solver,
            validate_plan: config.validate_plan,
            allow_replanning: config.allow_replanning,
        }
    }

    async fn llm_call(&self, prompt: &str) -> Result<String, AgentError> {
        let message = Message::new("user", serde_json::Value::String(prompt.to_string()));
        let response = self.agent.process(message).await?;

        match response.content {
            serde_json::Value::String(s) => Ok(s),
            other => Ok(other.to_string()),
        }
    }

    async fn create_plan(&self, problem: &str) -> Result<Plan, AgentError> {
        if let Some(planner) = &self.planner {
            return planner(problem);
        }

        let prompt = format!(
            "Create a detailed step-by-step plan to solve this problem.\n\
             List each step on a separate line, numbered 1, 2, 3, etc.\n\
             Focus on WHAT needs to be done, not HOW to do it yet.\n\n\
             Problem: {}\n\n\
             Solution Plan:",
            problem
        );

        let response = self.llm_call(&prompt).await?;
        let number_pattern = Regex::new(r"^\d+[\.\)]\s*").unwrap();

        let steps: Vec<PlanStep> = response
            .trim()
            .lines()
            .enumerate()
            .filter_map(|(i, line)| {
                let trimmed = line.trim();
                if trimmed.is_empty() {
                    return None;
                }

                let cleaned = number_pattern.replace(trimmed, "");
                if !cleaned.is_empty() {
                    Some(PlanStep {
                        description: cleaned.to_string(),
                        order: i,
                        dependencies: Vec::new(),
                        estimated_complexity: 1,
                        result: None,
                        executed: false,
                    })
                } else {
                    None
                }
            })
            .collect();

        Ok(Plan {
            steps,
            problem: problem.to_string(),
            strategy: None,
            validated: false,
            validation_notes: None,
        })
    }

    async fn validate(&self, plan: &mut Plan) -> Result<(), AgentError> {
        let plan_formatted = self.format_plan(plan);
        let prompt = format!(
            "Review this solution plan for completeness and feasibility.\n\
             Is this plan sufficient to solve the problem? Are there any missing steps or issues?\n\n\
             Problem: {}\n\n\
             Plan:\n{}\n\n\
             Validation (answer \"VALID\" or describe issues):",
            plan.problem, plan_formatted
        );

        let response = self.llm_call(&prompt).await?;
        let response_upper = response.to_uppercase();
        // Check for INVALID first to avoid matching "VALID" inside "INVALID"
        let is_valid = !response_upper.contains("INVALID")
            && (response_upper.contains("VALID") || response_upper.contains("YES"));

        plan.validated = is_valid;
        plan.validation_notes = Some(response.trim().to_string());

        Ok(())
    }

    fn format_plan(&self, plan: &Plan) -> String {
        plan.steps
            .iter()
            .enumerate()
            .map(|(i, step)| {
                let status = if step.executed { "✓" } else { "○" };
                format!("{}. [{}] {}", i + 1, status, step.description)
            })
            .collect::<Vec<_>>()
            .join("\n")
    }

    async fn execute_step(
        &self,
        step: &PlanStep,
        previous_results: &[String],
    ) -> Result<String, AgentError> {
        if let Some(solver) = &self.solver {
            return solver(step, previous_results);
        }

        let prompt = if !previous_results.is_empty() {
            let context = previous_results
                .iter()
                .enumerate()
                .map(|(i, result)| format!("Previous step {} result: {}", i + 1, result))
                .collect::<Vec<_>>()
                .join("\n");

            format!(
                "Execute this step of the plan, using previous results as context.\n\n\
                 Previous Results:\n{}\n\n\
                 Current Step: {}\n\n\
                 Execution Result:",
                context, step.description
            )
        } else {
            format!(
                "Execute this step of the plan:\n\n\
                 Step: {}\n\n\
                 Execution Result:",
                step.description
            )
        };

        let result = self.llm_call(&prompt).await?;
        Ok(result.trim().to_string())
    }

    async fn execute_plan(&self, plan: &mut Plan) -> Result<Vec<String>, AgentError> {
        let mut results = Vec::new();

        for step in &mut plan.steps {
            let result = self.execute_step(step, &results).await?;
            step.result = Some(result.clone());
            step.executed = true;
            results.push(result);
        }

        Ok(results)
    }
}

#[async_trait]
impl Agent for PlanAndSolveAgent {
    fn name(&self) -> &str {
        "plan_and_solve"
    }

    fn capabilities(&self) -> Vec<String> {
        vec![
            "reasoning".to_string(),
            "planning".to_string(),
            "plan_and_solve".to_string(),
            "strategic_thinking".to_string(),
            "step_by_step_execution".to_string(),
        ]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let problem = match &message.content {
            serde_json::Value::String(s) => s.clone(),
            other => other.to_string(),
        };

        let mut plan = self.create_plan(&problem).await?;

        if self.validate_plan {
            self.validate(&mut plan).await?;

            if !plan.validated && self.allow_replanning {
                let improved_prompt = format!(
                    "The previous plan had issues. Create an improved plan.\n\n\
                     Problem: {}\n\n\
                     Previous Plan Issues:\n{}\n\n\
                     Improved Plan:",
                    problem,
                    plan.validation_notes.as_deref().unwrap_or("")
                );

                let _ = self.llm_call(&improved_prompt).await;
                plan = self.create_plan(&problem).await?;
                self.validate(&mut plan).await?;
            }
        }

        let execution_results = self.execute_plan(&mut plan).await?;
        let final_solution = execution_results
            .last()
            .cloned()
            .unwrap_or_else(String::new);

        let plan_steps: Vec<String> = plan.steps.iter().map(|s| s.description.clone()).collect();

        let mut metadata = std::collections::HashMap::new();
        metadata.insert("technique".to_string(), json!("plan_and_solve"));
        metadata.insert("plan_steps".to_string(), json!(plan_steps));
        metadata.insert("execution_steps".to_string(), json!(execution_results));
        metadata.insert("num_steps".to_string(), json!(plan.steps.len()));
        metadata.insert("validated".to_string(), json!(plan.validated));
        metadata.insert("validation_notes".to_string(), json!(plan.validation_notes));
        metadata.insert("allow_replanning".to_string(), json!(self.allow_replanning));
        if let Some(strategy) = &plan.strategy {
            metadata.insert("strategy".to_string(), json!(strategy));
        }

        let mut result_message =
            Message::new("assistant", serde_json::Value::String(final_solution));
        result_message.metadata = metadata;
        Ok(result_message)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    struct MockAgent {
        responses: Mutex<Vec<String>>,
        call_count: Mutex<usize>,
    }

    impl MockAgent {
        fn new(responses: Vec<String>) -> Self {
            Self {
                responses: Mutex::new(responses),
                call_count: Mutex::new(0),
            }
        }

        fn call_count(&self) -> usize {
            *self.call_count.lock().unwrap()
        }
    }

    #[async_trait]
    impl Agent for MockAgent {
        fn name(&self) -> &str {
            "mock_agent"
        }

        fn capabilities(&self) -> Vec<String> {
            vec!["mock".to_string(), "testing".to_string()]
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            let mut count = self.call_count.lock().unwrap();
            let responses = self.responses.lock().unwrap();
            let response = responses[*count % responses.len()].clone();
            *count += 1;

            Ok(Message::new(
                "assistant",
                serde_json::Value::String(response),
            ))
        }
    }

    #[tokio::test]
    async fn test_basic_plan_and_solve() {
        let mock_agent = Arc::new(MockAgent::new(vec![
            "1. Gather ingredients\n2. Preheat oven\n3. Mix ingredients\n4. Bake".to_string(),
            "VALID: Plan is complete".to_string(),
            "Gathered: flour, sugar, eggs".to_string(),
            "Preheated oven to 350°F".to_string(),
            "Mixed all ingredients thoroughly".to_string(),
            "Baked for 30 minutes".to_string(),
        ]));

        let config = PlanAndSolveConfig {
            validate_plan: true,
            ..Default::default()
        };

        let agent = PlanAndSolveAgent::new(mock_agent, config);
        let message = Message::new(
            "user",
            serde_json::Value::String("How do I bake a cake?".to_string()),
        );

        let response = agent.process(message).await.unwrap();

        assert!(!response.content.to_string().is_empty());
        assert_eq!(
            response.metadata.get("technique").unwrap(),
            "plan_and_solve"
        );
        assert_eq!(response.metadata.get("num_steps").unwrap(), 4);
    }

    #[tokio::test]
    async fn test_name_and_capabilities() {
        let mock_agent = Arc::new(MockAgent::new(vec!["response".to_string()]));
        let agent = PlanAndSolveAgent::new(mock_agent, Default::default());

        assert_eq!(agent.name(), "plan_and_solve");

        let caps = agent.capabilities();
        assert!(caps.contains(&"reasoning".to_string()));
        assert!(caps.contains(&"planning".to_string()));
        assert!(caps.contains(&"plan_and_solve".to_string()));
        assert!(caps.contains(&"strategic_thinking".to_string()));
        assert!(caps.contains(&"step_by_step_execution".to_string()));
    }

    #[tokio::test]
    async fn test_create_plan() {
        let mock_agent = Arc::new(MockAgent::new(vec![
            "1. Step one\n2. Step two\n3. Step three".to_string(),
        ]));

        let config = PlanAndSolveConfig {
            validate_plan: false,
            ..Default::default()
        };

        let agent = PlanAndSolveAgent::new(mock_agent, config);
        let plan = agent.create_plan("Test problem").await.unwrap();

        assert_eq!(plan.steps.len(), 3);
        assert_eq!(plan.problem, "Test problem");
        assert_eq!(plan.steps[0].description, "Step one");
    }

    #[tokio::test]
    async fn test_parse_steps_correctly() {
        let mock_agent = Arc::new(MockAgent::new(vec![
            "1. First step\n2. Second step".to_string()
        ]));

        let config = PlanAndSolveConfig {
            validate_plan: false,
            ..Default::default()
        };

        let agent = PlanAndSolveAgent::new(mock_agent, config);
        let plan = agent.create_plan("Problem").await.unwrap();

        assert_eq!(plan.steps.len(), 2);
        assert_eq!(plan.steps[0].description, "First step");
        assert_eq!(plan.steps[1].description, "Second step");
    }

    #[tokio::test]
    async fn test_validate_plan_when_enabled() {
        let mock_agent = Arc::new(MockAgent::new(vec![
            "1. Step 1\n2. Step 2".to_string(),
            "VALID: The plan is complete and feasible".to_string(),
            "Result 1".to_string(),
            "Result 2".to_string(),
        ]));

        let config = PlanAndSolveConfig {
            validate_plan: true,
            ..Default::default()
        };

        let agent = PlanAndSolveAgent::new(mock_agent, config);
        let message = Message::new("user", serde_json::Value::String("Problem".to_string()));

        let response = agent.process(message).await.unwrap();

        assert_eq!(response.metadata.get("validated").unwrap(), true);
        assert!(response
            .metadata
            .get("validation_notes")
            .unwrap()
            .as_str()
            .unwrap()
            .contains("VALID"));
    }

    #[tokio::test]
    async fn test_skip_validation_when_disabled() {
        let mock_agent = Arc::new(MockAgent::new(vec![
            "1. Step".to_string(),
            "Result".to_string(),
        ]));

        let config = PlanAndSolveConfig {
            validate_plan: false,
            ..Default::default()
        };

        let agent = PlanAndSolveAgent::new(mock_agent.clone(), config);
        let message = Message::new(
            "user",
            serde_json::Value::String("Simple problem".to_string()),
        );

        let _ = agent.process(message).await.unwrap();

        // With validation disabled, should only call LLM twice (plan + execute)
        // not three times (plan + validate + execute)
        assert_eq!(mock_agent.call_count(), 2);
    }

    #[tokio::test]
    async fn test_handle_invalid_plan_validation() {
        let mock_agent = Arc::new(MockAgent::new(vec![
            "1. Step 1".to_string(),
            "INVALID: Missing important step".to_string(),
            "Result 1".to_string(),
        ]));

        let config = PlanAndSolveConfig {
            validate_plan: true,
            allow_replanning: false,
            ..Default::default()
        };

        let agent = PlanAndSolveAgent::new(mock_agent, config);
        let message = Message::new("user", serde_json::Value::String("Problem".to_string()));

        let response = agent.process(message).await.unwrap();

        assert_eq!(response.metadata.get("validated").unwrap(), false);
        assert!(response
            .metadata
            .get("validation_notes")
            .unwrap()
            .as_str()
            .unwrap()
            .contains("INVALID"));
    }

    #[tokio::test]
    async fn test_execute_steps_sequentially() {
        let mock_agent = Arc::new(MockAgent::new(vec![
            "1. Step A\n2. Step B".to_string(),
            "Answer A".to_string(),
            "Answer B".to_string(),
        ]));

        let config = PlanAndSolveConfig {
            validate_plan: false,
            ..Default::default()
        };

        let agent = PlanAndSolveAgent::new(mock_agent, config);
        let message = Message::new("user", serde_json::Value::String("Problem".to_string()));

        let response = agent.process(message).await.unwrap();
        let execution_steps = response
            .metadata
            .get("execution_steps")
            .unwrap()
            .as_array()
            .unwrap();

        assert_eq!(execution_steps.len(), 2);
        assert_eq!(execution_steps[0], "Answer A");
        assert_eq!(execution_steps[1], "Answer B");
    }

    #[tokio::test]
    async fn test_return_final_solution_as_content() {
        let mock_agent = Arc::new(MockAgent::new(vec![
            "1. Subproblem 1\n2. Subproblem 2".to_string(),
            "Intermediate".to_string(),
            "Final answer".to_string(),
        ]));

        let config = PlanAndSolveConfig {
            validate_plan: false,
            ..Default::default()
        };

        let agent = PlanAndSolveAgent::new(mock_agent, config);
        let message = Message::new("user", serde_json::Value::String("Problem".to_string()));

        let response = agent.process(message).await.unwrap();

        assert_eq!(response.content.as_str().unwrap(), "Final answer");
        assert_eq!(response.metadata.get("role"), None); // Assistant role is on message, not metadata
    }

    #[tokio::test]
    async fn test_track_execution_state() {
        let mut step = PlanStep {
            description: "Test step".to_string(),
            order: 0,
            dependencies: Vec::new(),
            estimated_complexity: 1,
            executed: false,
            result: None,
        };

        assert!(!step.executed);

        step.executed = true;
        step.result = Some("Test result".to_string());

        assert!(step.executed);
        assert_eq!(step.result.as_ref().unwrap(), "Test result");
    }

    #[tokio::test]
    async fn test_custom_planner() {
        let custom_planner: PlannerFn = Arc::new(|problem: &str| {
            Ok(Plan {
                problem: problem.to_string(),
                steps: vec![
                    PlanStep {
                        description: "Custom step 1".to_string(),
                        order: 0,
                        dependencies: Vec::new(),
                        estimated_complexity: 1,
                        executed: false,
                        result: None,
                    },
                    PlanStep {
                        description: "Custom step 2".to_string(),
                        order: 1,
                        dependencies: Vec::new(),
                        estimated_complexity: 1,
                        executed: false,
                        result: None,
                    },
                ],
                validated: false,
                strategy: Some("Custom strategy".to_string()),
                validation_notes: None,
            })
        });

        let mock_agent = Arc::new(MockAgent::new(vec![
            "Step 1 result".to_string(),
            "Step 2 result".to_string(),
        ]));

        let config = PlanAndSolveConfig {
            planner: Some(custom_planner),
            validate_plan: false,
            ..Default::default()
        };

        let agent = PlanAndSolveAgent::new(mock_agent, config);
        let message = Message::new(
            "user",
            serde_json::Value::String("Test problem".to_string()),
        );

        let response = agent.process(message).await.unwrap();

        let plan_steps = response
            .metadata
            .get("plan_steps")
            .unwrap()
            .as_array()
            .unwrap();
        assert_eq!(plan_steps.len(), 2);
        assert_eq!(plan_steps[0], "Custom step 1");
        assert_eq!(
            response.metadata.get("strategy").unwrap(),
            "Custom strategy"
        );
    }

    #[tokio::test]
    async fn test_custom_solver() {
        let custom_solver: SolverFn = Arc::new(|step: &PlanStep, _previous: &[String]| {
            Ok(format!("Custom solution for: {}", step.description))
        });

        let mock_agent = Arc::new(MockAgent::new(vec!["1. Test step".to_string()]));

        let config = PlanAndSolveConfig {
            solver: Some(custom_solver),
            validate_plan: false,
            ..Default::default()
        };

        let agent = PlanAndSolveAgent::new(mock_agent, config);
        let message = Message::new(
            "user",
            serde_json::Value::String("Test problem".to_string()),
        );

        let response = agent.process(message).await.unwrap();

        assert!(response
            .content
            .as_str()
            .unwrap()
            .contains("Custom solution"));
    }

    #[tokio::test]
    async fn test_replanning_when_validation_fails() {
        let mock_agent = Arc::new(MockAgent::new(vec![
            "1. Initial step".to_string(),
            "INVALID: Missing steps".to_string(),
            "".to_string(), // Replanning prompt response
            "1. Better step 1\n2. Better step 2".to_string(),
            "VALID".to_string(),
            "Result 1".to_string(),
            "Result 2".to_string(),
        ]));

        let config = PlanAndSolveConfig {
            validate_plan: true,
            allow_replanning: true,
            ..Default::default()
        };

        let agent = PlanAndSolveAgent::new(mock_agent, config);
        let message = Message::new(
            "user",
            serde_json::Value::String("Complex problem".to_string()),
        );

        let response = agent.process(message).await.unwrap();

        // Should have replanned and gotten a valid plan
        assert_eq!(response.metadata.get("num_steps").unwrap(), 2);
    }

    #[tokio::test]
    async fn test_handle_empty_plan() {
        let mock_agent = Arc::new(MockAgent::new(vec!["".to_string()]));

        let config = PlanAndSolveConfig {
            validate_plan: false,
            ..Default::default()
        };

        let agent = PlanAndSolveAgent::new(mock_agent, config);
        let plan = agent.create_plan("Problem").await.unwrap();

        assert_eq!(plan.steps.len(), 0);
    }

    #[tokio::test]
    async fn test_handle_single_step_plan() {
        let mock_agent = Arc::new(MockAgent::new(vec![
            "1. Only step".to_string(),
            "Step result".to_string(),
        ]));

        let config = PlanAndSolveConfig {
            validate_plan: false,
            ..Default::default()
        };

        let agent = PlanAndSolveAgent::new(mock_agent, config);
        let message = Message::new("user", serde_json::Value::String("Simple task".to_string()));

        let response = agent.process(message).await.unwrap();

        assert_eq!(response.metadata.get("num_steps").unwrap(), 1);
        assert_eq!(response.content.as_str().unwrap(), "Step result");
    }

    #[tokio::test]
    async fn test_parse_period_numbering() {
        let mock_agent = Arc::new(MockAgent::new(vec![
            "1. Step one\n2. Step two\n3. Step three".to_string(),
        ]));

        let config = PlanAndSolveConfig {
            validate_plan: false,
            ..Default::default()
        };

        let agent = PlanAndSolveAgent::new(mock_agent, config);
        let plan = agent.create_plan("Problem").await.unwrap();

        assert_eq!(plan.steps.len(), 3);
        assert_eq!(plan.steps[0].description, "Step one");
        assert_eq!(plan.steps[1].description, "Step two");
        assert_eq!(plan.steps[2].description, "Step three");
    }

    #[tokio::test]
    async fn test_parse_parenthesis_numbering() {
        let mock_agent = Arc::new(MockAgent::new(vec!["1) Step one\n2) Step two".to_string()]));

        let config = PlanAndSolveConfig {
            validate_plan: false,
            ..Default::default()
        };

        let agent = PlanAndSolveAgent::new(mock_agent, config);
        let plan = agent.create_plan("Problem").await.unwrap();

        assert_eq!(plan.steps.len(), 2);
        assert_eq!(plan.steps[0].description, "Step one");
        assert_eq!(plan.steps[1].description, "Step two");
    }

    #[tokio::test]
    async fn test_skip_empty_lines() {
        let mock_agent = Arc::new(MockAgent::new(vec![
            "1. Step one\n\n2. Step two\n\n".to_string()
        ]));

        let config = PlanAndSolveConfig {
            validate_plan: false,
            ..Default::default()
        };

        let agent = PlanAndSolveAgent::new(mock_agent, config);
        let plan = agent.create_plan("Problem").await.unwrap();

        assert_eq!(plan.steps.len(), 2);
    }

    #[tokio::test]
    async fn test_include_all_required_metadata_fields() {
        let mock_agent = Arc::new(MockAgent::new(vec![
            "1. Step 1\n2. Step 2".to_string(),
            "VALID".to_string(),
            "Result 1".to_string(),
            "Result 2".to_string(),
        ]));

        let config = PlanAndSolveConfig {
            validate_plan: true,
            ..Default::default()
        };

        let agent = PlanAndSolveAgent::new(mock_agent, config);
        let message = Message::new("user", serde_json::Value::String("Test".to_string()));

        let response = agent.process(message).await.unwrap();

        assert!(response.metadata.contains_key("technique"));
        assert_eq!(
            response.metadata.get("technique").unwrap(),
            "plan_and_solve"
        );
        assert!(response.metadata.contains_key("num_steps"));
        assert_eq!(response.metadata.get("num_steps").unwrap(), 2);
        assert!(response.metadata.contains_key("plan_steps"));
        assert!(response.metadata.contains_key("execution_steps"));
        assert!(response.metadata.contains_key("validated"));
        assert!(response.metadata.contains_key("validation_notes"));
        assert!(response.metadata.contains_key("allow_replanning"));
    }

    #[tokio::test]
    async fn test_track_strategy_when_provided() {
        let custom_planner: PlannerFn = Arc::new(|problem: &str| {
            Ok(Plan {
                problem: problem.to_string(),
                steps: vec![PlanStep {
                    description: "Step".to_string(),
                    order: 0,
                    dependencies: Vec::new(),
                    estimated_complexity: 1,
                    executed: false,
                    result: None,
                }],
                validated: false,
                strategy: Some("Divide and conquer".to_string()),
                validation_notes: None,
            })
        });

        let mock_agent = Arc::new(MockAgent::new(vec!["Result".to_string()]));

        let config = PlanAndSolveConfig {
            planner: Some(custom_planner),
            validate_plan: false,
            ..Default::default()
        };

        let agent = PlanAndSolveAgent::new(mock_agent, config);
        let message = Message::new("user", serde_json::Value::String("Problem".to_string()));

        let response = agent.process(message).await.unwrap();

        assert_eq!(
            response.metadata.get("strategy").unwrap(),
            "Divide and conquer"
        );
    }

    #[tokio::test]
    async fn test_track_step_dependencies() {
        let plan = Plan {
            problem: "Test".to_string(),
            steps: vec![
                PlanStep {
                    description: "Step 1".to_string(),
                    order: 0,
                    dependencies: Vec::new(),
                    estimated_complexity: 1,
                    executed: false,
                    result: None,
                },
                PlanStep {
                    description: "Step 2".to_string(),
                    order: 1,
                    dependencies: vec![0],
                    estimated_complexity: 1,
                    executed: false,
                    result: None,
                },
                PlanStep {
                    description: "Step 3".to_string(),
                    order: 2,
                    dependencies: vec![0, 1],
                    estimated_complexity: 2,
                    executed: false,
                    result: None,
                },
            ],
            validated: false,
            strategy: None,
            validation_notes: None,
        };

        // Verify step 2 depends on step 1
        assert_eq!(plan.steps[1].dependencies, vec![0]);

        // Verify step 3 depends on steps 1 and 2
        assert_eq!(plan.steps[2].dependencies, vec![0, 1]);

        // Verify complexity tracking
        assert_eq!(plan.steps[2].estimated_complexity, 2);
    }

    #[tokio::test]
    async fn test_create_valid_plan_structure() {
        let plan = Plan {
            problem: "Test problem".to_string(),
            steps: Vec::new(),
            validated: false,
            strategy: None,
            validation_notes: None,
        };

        assert_eq!(plan.problem, "Test problem");
        assert_eq!(plan.steps.len(), 0);
        assert!(!plan.validated);
    }

    #[tokio::test]
    async fn test_support_optional_fields() {
        let plan = Plan {
            problem: "Test".to_string(),
            steps: Vec::new(),
            validated: true,
            strategy: Some("Test strategy".to_string()),
            validation_notes: Some("All good".to_string()),
        };

        assert_eq!(plan.strategy.unwrap(), "Test strategy");
        assert_eq!(plan.validation_notes.unwrap(), "All good");
    }

    #[tokio::test]
    async fn test_create_valid_plan_step_structure() {
        let step = PlanStep {
            description: "Test step".to_string(),
            order: 0,
            dependencies: Vec::new(),
            estimated_complexity: 1,
            executed: false,
            result: None,
        };

        assert_eq!(step.description, "Test step");
        assert_eq!(step.order, 0);
        assert_eq!(step.dependencies.len(), 0);
        assert_eq!(step.estimated_complexity, 1);
        assert!(!step.executed);
    }

    #[tokio::test]
    async fn test_support_optional_result_field() {
        let step = PlanStep {
            description: "Test step".to_string(),
            order: 0,
            dependencies: Vec::new(),
            estimated_complexity: 1,
            executed: true,
            result: Some("Test result".to_string()),
        };

        assert_eq!(step.result.unwrap(), "Test result");
    }
}
