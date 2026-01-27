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
        let is_valid = response_upper.contains("VALID") || response_upper.contains("YES");

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
            .unwrap_or_else(|| String::new());

        let plan_steps: Vec<String> = plan.steps.iter().map(|s| s.description.clone()).collect();

        let mut metadata = std::collections::HashMap::new();
        metadata.insert("technique".to_string(), json!("plan_and_solve"));
        metadata.insert("plan_steps".to_string(), json!(plan_steps));
        metadata.insert("execution_steps".to_string(), json!(execution_results));
        metadata.insert("num_steps".to_string(), json!(plan.steps.len()));
        metadata.insert("validated".to_string(), json!(plan.validated));
        metadata.insert(
            "validation_notes".to_string(),
            json!(plan.validation_notes),
        );
        metadata.insert("allow_replanning".to_string(), json!(self.allow_replanning));

        let mut result_message =
            Message::new("assistant", serde_json::Value::String(final_solution));
        result_message.metadata = metadata;
        Ok(result_message)
    }
}
