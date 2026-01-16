//! Planning Pattern Example
//!
//! Demonstrates the Planning pattern for breaking complex tasks into
//! manageable steps and executing them in order.
//!
//! Run with: cargo run --example planning_pattern

use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::{
    DefaultStepExecutor, Plan, PlanStep, PlanningAgent, PlanningConfig, StepExecutor, StepStatus,
};
use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;

/// Mock LLM agent that generates plans for different scenarios
struct MockLLMAgent {
    scenario: String,
}

#[async_trait]
impl Agent for MockLLMAgent {
    fn name(&self) -> &str {
        "MockLLM"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["planning".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");

        // Generate appropriate plan based on scenario
        let plan_text = if content.contains("event") || self.scenario == "event" {
            "Goal: Organize a successful team event\nSteps:\n\
             1. Choose date and venue for the event\n\
             2. Create invitation list with all team members\n\
             3. Send invitations via email\n\
             4. Arrange catering and refreshments\n\
             5. Prepare agenda and activities"
                .to_string()
        } else if content.contains("website") || self.scenario == "website" {
            "Goal: Launch a new company website\nSteps:\n\
             1. Design website mockups and wireframes\n\
             2. Develop frontend with HTML/CSS/JS\n\
             3. Implement backend API and database\n\
             4. Write content and add images\n\
             5. Deploy to production server\n\
             6. Configure domain and SSL certificate"
                .to_string()
        } else if content.contains("campaign") || self.scenario == "campaign" {
            "Goal: Execute marketing campaign\nSteps:\n\
             1. Define target audience and goals\n\
             2. Create campaign content and assets\n\
             3. Set up advertising channels\n\
             4. Launch campaign across platforms\n\
             5. Monitor metrics and performance"
                .to_string()
        } else {
            "Goal: Complete the task\nSteps:\n\
             1. Analyze requirements\n\
             2. Create implementation plan\n\
             3. Execute the plan\n\
             4. Verify results"
                .to_string()
        };

        Ok(Message::with_text("assistant", plan_text))
    }
}

/// Custom step executor that simulates realistic step execution
struct CustomStepExecutor {
    verbose: bool,
}

#[async_trait]
impl StepExecutor for CustomStepExecutor {
    async fn execute(
        &self,
        step: &PlanStep,
        context: &HashMap<String, serde_json::Value>,
    ) -> Result<serde_json::Value, AgentError> {
        if self.verbose {
            println!("  → Executing: {}", step.description);
        }

        // Simulate different execution results based on step content
        let result = if step.description.contains("Choose date") {
            "Selected June 15th, 2:00 PM at Conference Room A"
        } else if step.description.contains("invitation list") {
            "Created list of 25 team members"
        } else if step.description.contains("Send invitations") {
            "Sent 25 email invitations (24 delivered, 1 bounced)"
        } else if step.description.contains("catering") {
            "Booked catering service for 25 people, budget: $500"
        } else if step.description.contains("agenda") {
            "Prepared 2-hour agenda with team building activities"
        } else if step.description.contains("Design website") {
            "Created mockups in Figma (5 pages, responsive design)"
        } else if step.description.contains("frontend") {
            "Built responsive frontend with React and Tailwind CSS"
        } else if step.description.contains("backend") {
            "Implemented REST API with PostgreSQL database"
        } else if step.description.contains("content") {
            "Added 12 pages of content with 45 images"
        } else if step.description.contains("Deploy") {
            "Deployed to AWS (load time: 1.2s, 99.9% uptime)"
        } else if step.description.contains("domain") {
            "Configured www.example.com with Let's Encrypt SSL"
        } else if step.description.contains("target audience") {
            "Defined audience: 25-45 year olds, tech industry professionals"
        } else if step.description.contains("campaign content") {
            "Created 3 video ads, 5 social posts, 2 blog articles"
        } else if step.description.contains("advertising") {
            "Set up Google Ads, Facebook Ads, LinkedIn campaigns"
        } else if step.description.contains("Launch campaign") {
            "Campaign live across 4 platforms, initial reach: 10,000"
        } else if step.description.contains("Monitor") {
            "Tracking: 500 clicks, 50 conversions, 10% CTR"
        } else {
            "Step completed successfully"
        };

        // Check if previous steps are available in context
        if self.verbose && !context.is_empty() {
            println!("    (Using context from {} previous steps)", context.len());
        }

        // Small delay to simulate work
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

        Ok(serde_json::json!(result))
    }
}

/// Example 1: Simple event planning with default executor
async fn example_simple_planning() -> Result<(), AgentError> {
    println!("\n=== Example 1: Simple Event Planning (Default Executor) ===\n");

    let llm = Arc::new(MockLLMAgent {
        scenario: "event".to_string(),
    });

    let planner = PlanningAgent::new(PlanningConfig {
        llm,
        executor: None, // Use DefaultStepExecutor
        max_steps: 10,
        allow_replanning: false,
        system_prompt: None,
    })?;

    let message = Message::with_text("user", "Organize a team event");
    let result = planner.process(message).await?;

    println!("Result:\n{}\n", result.content_as_str().unwrap_or(""));

    // Show plan details from metadata
    if let Some(plan_value) = result.metadata.get("plan") {
        if let Ok(plan) = serde_json::from_value::<Plan>(plan_value.clone()) {
            println!("Plan Details:");
            println!("  Goal: {}", plan.goal);
            println!("  Total Steps: {}", plan.steps.len());
            println!(
                "  Completed: {}",
                plan.steps
                    .iter()
                    .filter(|s| s.status == StepStatus::Completed)
                    .count()
            );
        }
    }

    Ok(())
}

/// Example 2: Website launch with custom executor
async fn example_custom_executor() -> Result<(), AgentError> {
    println!("\n=== Example 2: Website Launch (Custom Executor) ===\n");

    let llm = Arc::new(MockLLMAgent {
        scenario: "website".to_string(),
    });

    let custom_executor = Arc::new(CustomStepExecutor { verbose: true });

    let planner = PlanningAgent::new(PlanningConfig {
        llm,
        executor: Some(custom_executor),
        max_steps: 10,
        allow_replanning: false,
        system_prompt: None,
    })?;

    let message = Message::with_text("user", "Launch a new website");
    let result = planner.process(message).await?;

    println!("\nResult:\n{}\n", result.content_as_str().unwrap_or(""));

    if let Some(progress) = result.metadata.get("progress") {
        println!("Overall Progress: {:.1}%", progress.as_f64().unwrap_or(0.0));
    }

    Ok(())
}

/// Example 3: Marketing campaign with progress tracking
async fn example_progress_tracking() -> Result<(), AgentError> {
    println!("\n=== Example 3: Marketing Campaign (Progress Tracking) ===\n");

    let llm = Arc::new(MockLLMAgent {
        scenario: "campaign".to_string(),
    });

    let custom_executor = Arc::new(CustomStepExecutor { verbose: false });

    let planner = PlanningAgent::new(PlanningConfig {
        llm,
        executor: Some(custom_executor),
        max_steps: 8,
        allow_replanning: false,
        system_prompt: Some(
            "You are a marketing planning expert. Create detailed campaign plans.".to_string(),
        ),
    })?;

    println!("Starting marketing campaign planning...\n");

    let message = Message::with_text("user", "Execute a marketing campaign");
    let result = planner.process(message).await?;

    // Extract plan from metadata
    if let Some(plan_value) = result.metadata.get("plan") {
        if let Ok(plan) = serde_json::from_value::<Plan>(plan_value.clone()) {
            println!("Campaign Plan Execution:");
            println!("Goal: {}\n", plan.goal);

            for step in &plan.steps {
                let status_icon = match step.status {
                    StepStatus::Completed => "✓",
                    StepStatus::Failed => "✗",
                    StepStatus::Skipped => "⊘",
                    StepStatus::InProgress => "→",
                    StepStatus::Pending => "○",
                };

                println!(
                    "{} Step {}: {}",
                    status_icon,
                    step.step_number + 1,
                    step.description
                );

                if let Some(result) = &step.result {
                    if let Some(result_str) = result.as_str() {
                        println!("  Result: {}", result_str);
                    }
                }
            }

            println!("\nProgress: {:.1}%", plan.get_progress());
            println!(
                "Status: {}",
                if plan.is_complete() {
                    "Complete"
                } else {
                    "In Progress"
                }
            );
        }
    }

    Ok(())
}

/// Example 4: Demonstrating step dependencies
async fn example_dependencies() -> Result<(), AgentError> {
    println!("\n=== Example 4: Step Dependencies ===\n");

    // Create a plan manually to demonstrate dependencies
    let mut plan = Plan::new(
        "Build a simple application",
        vec![
            PlanStep::new("Set up development environment", 0, vec![]),
            PlanStep::new("Design database schema", 1, vec![]),
            PlanStep::new("Implement database migrations", 2, vec![1]), // Depends on step 1
            PlanStep::new("Create API endpoints", 3, vec![2]),          // Depends on step 2
            PlanStep::new("Build frontend UI", 4, vec![0]),             // Depends on step 0
            PlanStep::new("Integrate frontend with API", 5, vec![3, 4]), // Depends on 3 and 4
            PlanStep::new("Write tests", 6, vec![5]),                   // Depends on step 5
            PlanStep::new("Deploy to production", 7, vec![6]),          // Depends on step 6
        ],
    );

    println!("Plan: {}", plan.goal);
    println!("Total steps: {}\n", plan.steps.len());

    // Show dependency graph
    println!("Dependency Graph:");
    for step in &plan.steps {
        print!("  Step {}: {}", step.step_number, step.description);
        if !step.dependencies.is_empty() {
            print!(" (depends on: {:?})", step.dependencies);
        }
        println!();
    }

    println!("\nExecution Order:");

    // Simulate execution by repeatedly getting next steps
    let executor = DefaultStepExecutor;
    let mut context = HashMap::new();
    let mut execution_round = 0;

    while !plan.is_complete() {
        // Collect step numbers first to avoid borrow checker issues
        let next_step_numbers: Vec<usize> = plan
            .get_next_steps()
            .iter()
            .map(|step| step.step_number)
            .collect();

        if next_step_numbers.is_empty() {
            break;
        }

        execution_round += 1;
        println!("\nRound {}:", execution_round);

        for step_num in next_step_numbers {
            let step = &plan.steps[step_num];
            println!("  → Executing Step {}: {}", step_num, step.description);

            // Execute and update
            let result = executor.execute(step, &context).await?;
            plan.steps[step_num].status = StepStatus::Completed;
            plan.steps[step_num].result = Some(result.clone());
            context.insert(format!("step_{}_result", step_num), result);
        }

        println!("  Progress: {:.1}%", plan.get_progress());
    }

    println!("\n✓ All steps completed!");
    println!("Final Progress: {:.1}%", plan.get_progress());

    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    println!("Planning Pattern Examples");
    println!("========================\n");

    // Run all examples
    example_simple_planning().await?;
    example_custom_executor().await?;
    example_progress_tracking().await?;
    example_dependencies().await?;

    println!("\n✓ All examples completed successfully!");

    Ok(())
}
