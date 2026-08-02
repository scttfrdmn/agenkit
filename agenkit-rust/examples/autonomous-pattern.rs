//! Autonomous Agent Pattern Example
//!
//! Demonstrates the Autonomous pattern for goal-directed self-organizing agents
//! that operate independently with minimal human intervention.
//!
//! Run with: cargo run --example autonomous_pattern

use agenkit::patterns::{AutonomousAgent, GoalStatus};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

/// Example 1: Basic autonomous agent
async fn example_basic() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n=== Example 1: Basic Autonomous Agent ===\n");

    let mut agent = AutonomousAgent::new("Complete research project", 10);

    println!("Objective: {}", agent.objective());
    println!("Max iterations: {}\n", agent.max_iterations());

    agent.add_goal("Literature review", 10);
    agent.add_goal("Data collection", 8);
    agent.add_goal("Analysis", 5);
    agent.add_goal("Write paper", 3);

    println!("Goals added: {}", agent.goals().len());
    for goal in agent.goals() {
        println!("  - {} (priority: {})", goal.description, goal.priority);
    }

    println!("\nRunning agent...\n");
    let result = agent.run().await?;

    println!("Result:");
    println!("  Objective: {}", result.objective);
    println!("  Iterations: {}", result.iterations);
    println!(
        "  Goals completed: {}/{}",
        result.goals_completed,
        agent.goals().len()
    );
    println!("\nProgress: {:.1}%", agent.get_progress());

    Ok(())
}

/// Example 2: Custom worker function
async fn example_custom_worker() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n=== Example 2: Custom Worker Function ===\n");

    let mut agent = AutonomousAgent::new("Build web application", 15);

    agent.add_goal("Design database schema", 10);
    agent.add_goal("Create API endpoints", 8);
    agent.add_goal("Build frontend", 6);
    agent.add_goal("Write tests", 4);
    agent.add_goal("Deploy to production", 2);

    // Custom worker that simulates detailed work
    agent.set_worker(Arc::new(|goal| {
        let work_done = match goal.description.as_str() {
            desc if desc.contains("database") => "Defined tables, relationships, and indexes",
            desc if desc.contains("API") => "Implemented REST endpoints with validation",
            desc if desc.contains("frontend") => "Created React components and routing",
            desc if desc.contains("tests") => "Wrote unit and integration tests",
            desc if desc.contains("Deploy") => "Configured CI/CD and deployed to AWS",
            _ => "Made progress on task",
        };

        Ok(format!("{}: {}", goal.description, work_done))
    }));

    println!("Running agent with custom worker...\n");
    let result = agent.run().await?;

    println!("Work completed:");
    for (i, work) in result.results.iter().enumerate() {
        println!("  {}. {}", i + 1, work);
    }

    println!("\nFinal progress: {:.1}%", agent.get_progress());

    Ok(())
}

/// Example 3: Priority-based goal selection
async fn example_priority() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n=== Example 3: Priority-Based Goal Selection ===\n");

    let mut agent = AutonomousAgent::new("Incident response", 12);

    agent.add_goal("Document findings", 2);
    agent.add_goal("Notify stakeholders", 5);
    agent.add_goal("Fix critical bug", 10); // Highest priority
    agent.add_goal("Write post-mortem", 1);

    println!("Goals (with priorities):");
    for goal in agent.goals() {
        println!("  - {} [priority: {}]", goal.description, goal.priority);
    }

    println!("\nAgent will work on highest priority goals first...\n");

    let result = agent.run().await?;

    println!("Goals completed: {}", result.goals_completed);
    println!("\nFirst 3 iterations (should prioritize 'Fix critical bug'):");
    for (i, work) in result.results.iter().take(3).enumerate() {
        println!("  {}. {}", i + 1, work);
    }

    Ok(())
}

/// Example 4: Stop condition
async fn example_stop_condition() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n=== Example 4: Stop Condition ===\n");

    let mut agent = AutonomousAgent::new("Long-running task", 100);
    agent.add_goal("Process data", 10);

    let processed_items = Arc::new(AtomicUsize::new(0));
    let processed_clone = processed_items.clone();

    // Stop after processing 50 items
    let target = 50;
    agent.set_stop_condition(Arc::new(move || {
        processed_clone.load(Ordering::SeqCst) >= target
    }));

    agent.set_worker(Arc::new(move |goal| {
        let count = processed_items.fetch_add(10, Ordering::SeqCst) + 10;
        Ok(format!("{}: Processed {} items", goal.description, count))
    }));

    println!("Target: Process 50 items");
    println!("Max iterations: 100");
    println!("\nRunning with stop condition...\n");

    let result = agent.run().await?;

    println!(
        "Stopped after {} iterations (target reached)",
        result.iterations
    );
    println!("Well before max_iterations=100!\n");

    Ok(())
}

/// Example 5: Manual stop
async fn example_manual_stop() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n=== Example 5: Manual Stop ===\n");

    const MAX_ITERATIONS: usize = 1000;
    const STOP_AFTER: usize = 25;

    let mut agent = AutonomousAgent::new("Continuous monitoring", MAX_ITERATIONS);
    agent.add_goal("Monitor system health", 10);

    // Obtained *before* run(), which borrows the agent for as long as it runs. The
    // earlier shape of this example wrapped the agent in a Mutex and had the stopper
    // task call `agent.stop()` through it -- but run() holds that same lock for the
    // whole run, so the stopper blocked forever and silently never fired. The example
    // still printed "manually stopped" because the goal happened to complete on its
    // own after 5 iterations.
    let stopper = agent.stop_handle();

    // A goal that never finishes, so the run can only end by being stopped, and a
    // worker that trips the stopper after a fixed number of checks. Counting
    // iterations rather than sleeping keeps the example deterministic -- a wall-clock
    // stopper races the loop, which spins through all 1000 iterations in well under a
    // millisecond.
    let checks = Arc::new(AtomicUsize::new(0));
    agent.set_worker(Arc::new(move |goal| {
        goal.progress = 0.0;
        if checks.fetch_add(1, Ordering::SeqCst) + 1 >= STOP_AFTER {
            println!("  [External trigger] Stopping agent...");
            stopper.stop();
        }
        Ok(format!("checked: {}", goal.description))
    }));

    println!("Starting continuous monitoring...");
    println!("(will be stopped externally after {STOP_AFTER} checks)\n");

    let result = agent.run().await?;

    println!("\nAgent stopped after {} iterations", result.iterations);
    if result.iterations < MAX_ITERATIONS {
        println!("(manually stopped before reaching max_iterations={MAX_ITERATIONS})\n");
    } else {
        // Kept as a real branch rather than an unconditional claim: the old version
        // asserted it had been stopped no matter what actually happened.
        println!("(ran to max_iterations={MAX_ITERATIONS}: stop() had no effect)\n");
    }

    Ok(())
}

/// Example 6: Progress tracking
async fn example_progress_tracking() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n=== Example 6: Progress Tracking ===\n");

    let mut agent = AutonomousAgent::new("Software release", 20);

    agent.add_goal("Code freeze", 10);
    agent.add_goal("QA testing", 8);
    agent.add_goal("Documentation", 5);
    agent.add_goal("Release notes", 3);

    println!("Tracking progress during execution:\n");

    // `run()` drives the agent to completion in one call — it does not yield
    // between goals — so progress is sampled before and after, not per phase.
    // This was previously written as `for phase in 1..=4 { ...; break; }`, which
    // printed "Phase 1" and stopped: the loop implied a multi-phase API that
    // does not exist. `run()` is the only entry point; there is no
    // step-at-a-time variant to interleave with.
    println!("Before: {:.1}% complete", agent.get_progress());

    let has_active = agent.goals().iter().any(|g| g.status == GoalStatus::Active);
    if has_active {
        let result = agent.run().await?;

        println!("After:  {:.1}% complete", agent.get_progress());
        println!("  Iterations: {}", result.iterations);
        println!(
            "  Goals completed: {}/{}",
            result.goals_completed,
            agent.goals().len()
        );
    }

    println!("\n✓ Release complete!\n");

    Ok(())
}

/// Example 7: Goal lifecycle
async fn example_goal_lifecycle() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n=== Example 7: Goal Lifecycle ===\n");

    let mut agent = AutonomousAgent::new("Study project lifecycle", 6);

    let goal = agent.add_goal("Learn Rust", 10);

    println!("New goal created:");
    println!("  Description: {}", goal.description);
    println!("  Priority: {}", goal.priority);
    println!("  Status: {}", goal.status);
    println!("  Progress: {:.0}%", goal.progress * 100.0);
    println!("  Created at: {}\n", goal.created_at);

    println!("Running agent...\n");
    let result = agent.run().await?;

    println!("After {} iterations:", result.iterations);
    let final_goal = &agent.goals()[0];
    println!("  Status: {}", final_goal.status);
    println!("  Progress: {:.0}%\n", final_goal.progress * 100.0);

    Ok(())
}

/// Example 8: Multiple goals with different completion times
async fn example_goal_completion_times() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n=== Example 8: Goal Completion Times ===\n");

    let mut agent = AutonomousAgent::new("Varied task durations", 30);

    agent.add_goal("Quick task (1 iteration)", 10);
    agent.add_goal("Medium task (5 iterations)", 8);
    agent.add_goal("Long task (15 iterations)", 5);

    println!("Goals with different estimated durations:");
    for goal in agent.goals() {
        println!("  - {}", goal.description);
    }

    println!("\nRunning agent...\n");
    let result = agent.run().await?;

    println!("Results:");
    println!("  Total iterations: {}", result.iterations);
    println!("  Goals completed: {}", result.goals_completed);

    println!("\nFinal goal states:");
    for goal in agent.goals() {
        let status_icon = match goal.status {
            GoalStatus::Completed => "✓",
            GoalStatus::Active => "○",
            GoalStatus::Abandoned => "✗",
        };
        println!(
            "  {} {} - {:.0}% complete",
            status_icon,
            goal.description,
            goal.progress * 100.0
        );
    }

    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Autonomous Agent Pattern Examples");
    println!("=================================");

    // Run all examples
    example_basic().await?;
    example_custom_worker().await?;
    example_priority().await?;
    example_stop_condition().await?;
    example_manual_stop().await?;
    example_progress_tracking().await?;
    example_goal_lifecycle().await?;
    example_goal_completion_times().await?;

    println!("✓ All examples completed successfully!");

    Ok(())
}
