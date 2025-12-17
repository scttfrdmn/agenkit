//! Bayesian Optimization Example
//!
//! This example demonstrates Bayesian optimization for hyperparameter tuning.
//! Bayesian optimization is ideal when:
//!   - Objective function is expensive to evaluate (minutes per trial)
//!   - Search space is continuous or mixed (continuous + discrete)
//!   - You want efficient exploration with limited evaluation budget
//!   - You need to balance exploration vs exploitation
//!
//! Run with: cargo run --example evaluation-bayesian-optimizer

use agenkit::evaluation::optimizer::{
    BayesianOptimizer, SearchSpace, AcquisitionFunction,
};
use std::collections::HashMap;

/// Expensive objective function to minimize
/// Simulates an agent evaluation that takes time
async fn expensive_objective(config: HashMap<String, serde_json::Value>) -> Result<f64, agenkit::core::AgentError> {
    let temperature = config.get("temperature").unwrap().as_f64().unwrap();
    let max_tokens = config.get("max_tokens").unwrap().as_i64().unwrap() as f64;
    let top_p = config.get("top_p").unwrap().as_f64().unwrap();

    // Simulate expensive evaluation
    tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;

    // Objective: balance quality, cost, and latency
    // Quality improves with temperature up to 0.7, then degrades
    let quality_score = 1.0 - (temperature - 0.7).abs() * 2.0;

    // Cost increases with max_tokens
    let cost_penalty = max_tokens / 2000.0;

    // top_p affects reliability (best around 0.9)
    let reliability_score = 1.0 - (top_p - 0.9).abs() * 2.0;

    // Combined score (lower is better)
    let score = -(quality_score * 0.5 + reliability_score * 0.3 - cost_penalty * 0.2);

    Ok(score)
}

/// Simple quadratic function for demonstration
async fn quadratic_objective(config: HashMap<String, serde_json::Value>) -> Result<f64, agenkit::core::AgentError> {
    let x = config.get("x").unwrap().as_f64().unwrap();
    let y = config.get("y").unwrap().as_f64().unwrap();

    // Find minimum of (x-3)² + (y-7)²
    Ok((x - 3.0).powi(2) + (y - 7.0).powi(2))
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("\n{}", "=".repeat(70));
    println!("Bayesian Optimization Example");
    println!("{}", "=".repeat(70));

    // ========================================================================
    // Example 1: Simple 2D Optimization
    // ========================================================================
    println!("\nExample 1: Simple 2D Optimization");
    println!("{}", "-".repeat(70));
    println!("Objective: Find minimum of (x-3)² + (y-7)²");
    println!("Known optimum: x=3, y=7, score=0\n");

    let mut space = SearchSpace::new();
    space.add_continuous("x", 0.0, 10.0);
    space.add_continuous("y", 0.0, 10.0);

    let mut optimizer = BayesianOptimizer::new(
        quadratic_objective,
        space,
        false, // minimize
        AcquisitionFunction::EI,
        5,     // 5 random initialization samples
    );

    println!("🔧 Configuration:");
    println!("   Acquisition Function: Expected Improvement (EI)");
    println!("   Initial Samples: 5 (random exploration)");
    println!("   Total Iterations: 20");

    let result = optimizer.optimize(20).await?;

    println!("\n📊 Results:");
    println!("   Best Score: {:.6}", result.best_score);
    println!("   Best x: {:.4}", result.best_config.get("x").unwrap().as_f64().unwrap());
    println!("   Best y: {:.4}", result.best_config.get("y").unwrap().as_f64().unwrap());
    println!("   Iterations: {}", result.n_iterations);
    println!("   Duration: {:.2}s", result.duration_secs());

    // Show convergence
    println!("\n📈 Convergence:");
    let mut best_so_far = f64::INFINITY;
    for (i, step) in result.history.iter().enumerate() {
        if step.score < best_so_far {
            best_so_far = step.score;
            println!("   Iteration {}: New best = {:.6}", i + 1, best_so_far);
        }
    }

    // ========================================================================
    // Example 2: Hyperparameter Tuning (Expensive Objective)
    // ========================================================================
    println!("\n\nExample 2: LLM Hyperparameter Tuning");
    println!("{}", "-".repeat(70));
    println!("Objective: Optimize temperature, max_tokens, and top_p");
    println!("Goal: Balance quality, cost, and reliability\n");

    let mut space2 = SearchSpace::new();
    space2.add_continuous("temperature", 0.0, 1.0);
    space2.add_integer("max_tokens", 100, 2000);
    space2.add_continuous("top_p", 0.1, 1.0);

    let mut optimizer2 = BayesianOptimizer::new(
        expensive_objective,
        space2,
        false, // minimize cost
        AcquisitionFunction::UCB,
        5,
    );

    println!("🔧 Configuration:");
    println!("   Acquisition Function: Upper Confidence Bound (UCB)");
    println!("   Parameters:");
    println!("     - temperature: [0.0, 1.0] continuous");
    println!("     - max_tokens: [100, 2000] integer");
    println!("     - top_p: [0.1, 1.0] continuous");
    println!("   Initial Samples: 5");
    println!("   Total Iterations: 30");

    let result2 = optimizer2.optimize(30).await?;

    println!("\n📊 Results:");
    println!("   Best Score: {:.6}", result2.best_score);
    println!("   Best Configuration:");
    println!("     - temperature: {:.4}", result2.best_config.get("temperature").unwrap().as_f64().unwrap());
    println!("     - max_tokens: {}", result2.best_config.get("max_tokens").unwrap().as_i64().unwrap());
    println!("     - top_p: {:.4}", result2.best_config.get("top_p").unwrap().as_f64().unwrap());
    println!("   Total Duration: {:.2}s", result2.duration_secs());
    println!("   Avg Time/Iteration: {:.2}s", result2.duration_secs() / result2.n_iterations as f64);

    // ========================================================================
    // Example 3: Comparing Acquisition Functions
    // ========================================================================
    println!("\n\nExample 3: Comparing Acquisition Functions");
    println!("{}", "-".repeat(70));
    println!("Testing EI, UCB, and PI on same objective\n");

    let acquisition_functions = vec![
        (AcquisitionFunction::EI, "Expected Improvement (EI)", "Balanced exploration/exploitation"),
        (AcquisitionFunction::UCB, "Upper Confidence Bound (UCB)", "More exploratory"),
        (AcquisitionFunction::PI, "Probability of Improvement (PI)", "More exploitative"),
    ];

    for (acq_func, name, description) in acquisition_functions {
        println!("Testing: {} - {}", name, description);

        let mut space = SearchSpace::new();
        space.add_continuous("x", 0.0, 10.0);

        let objective = |config: HashMap<String, serde_json::Value>| {
            Box::pin(async move {
                let x = config.get("x").unwrap().as_f64().unwrap();
                // Minimize (x - 5)²
                Ok((x - 5.0).powi(2))
            })
        };

        let mut optimizer = BayesianOptimizer::new(
            objective,
            space,
            false,
            acq_func,
            3,
        );

        let result = optimizer.optimize(15).await?;

        println!("   Best x: {:.4}, Best Score: {:.6}",
            result.best_config.get("x").unwrap().as_f64().unwrap(),
            result.best_score
        );
    }

    // ========================================================================
    // Example 4: Maximization vs Minimization
    // ========================================================================
    println!("\n\nExample 4: Maximization vs Minimization");
    println!("{}", "-".repeat(70));

    // Same function, different optimization directions
    let test_objective = |config: HashMap<String, serde_json::Value>| {
        Box::pin(async move {
            let x = config.get("x").unwrap().as_f64().unwrap();
            Ok((x - 6.0).powi(2))
        })
    };

    // Minimization (find x=6, score=0)
    let mut space_min = SearchSpace::new();
    space_min.add_continuous("x", 0.0, 10.0);
    let mut opt_min = BayesianOptimizer::new(
        test_objective,
        space_min,
        false, // minimize
        AcquisitionFunction::EI,
        3,
    );
    let result_min = opt_min.optimize(15).await?;

    println!("🔽 Minimization:");
    println!("   Best x: {:.4}", result_min.best_config.get("x").unwrap().as_f64().unwrap());
    println!("   Best Score: {:.6} (should be close to 0)", result_min.best_score);

    // Maximization (find x at boundaries)
    let mut space_max = SearchSpace::new();
    space_max.add_continuous("x", 0.0, 10.0);
    let test_objective_max = |config: HashMap<String, serde_json::Value>| {
        Box::pin(async move {
            let x = config.get("x").unwrap().as_f64().unwrap();
            Ok((x - 6.0).powi(2))
        })
    };
    let mut opt_max = BayesianOptimizer::new(
        test_objective_max,
        space_max,
        true, // maximize
        AcquisitionFunction::UCB,
        3,
    );
    let result_max = opt_max.optimize(15).await?;

    println!("\n🔼 Maximization:");
    println!("   Best x: {:.4}", result_max.best_config.get("x").unwrap().as_f64().unwrap());
    println!("   Best Score: {:.6} (should be close to 16 at boundaries)", result_max.best_score);

    // ========================================================================
    // Summary
    // ========================================================================
    println!("\n{}", "=".repeat(70));
    println!("Summary: Bayesian Optimization");
    println!("{}", "=".repeat(70));

    println!("\n📚 Key Concepts:");

    println!("\n1. Acquisition Functions:");
    println!("   • Expected Improvement (EI): Balanced, good default choice");
    println!("   • Upper Confidence Bound (UCB): More exploratory, finds global optimum");
    println!("   • Probability of Improvement (PI): More exploitative, refines quickly");

    println!("\n2. When to Use Bayesian Optimization:");
    println!("   ✓ Expensive evaluations (minutes per trial)");
    println!("   ✓ Limited evaluation budget (20-50 iterations)");
    println!("   ✓ Continuous or mixed parameter spaces");
    println!("   ✓ Need for sample efficiency");
    println!("   ✗ Very cheap evaluations (use random or grid search)");
    println!("   ✗ High-dimensional spaces (>20 parameters)");
    println!("   ✗ Discrete-only parameters (use other methods)");

    println!("\n3. Algorithm Phases:");
    println!("   Phase 1: Random Exploration (n_initial samples)");
    println!("   - Sample randomly to build initial model");
    println!("   - Typically 5-10 samples");
    println!("   \n   Phase 2: Guided Search (remaining iterations)");
    println!("   - Use acquisition function to propose candidates");
    println!("   - Balance exploration vs exploitation");
    println!("   - Converge toward optimum");

    println!("\n4. Hyperparameter Recommendations:");
    println!("   • n_initial: 5-10 (more for complex spaces)");
    println!("   • Total iterations: 20-50 (depends on budget)");
    println!("   • Acquisition: EI for general use, UCB for exploration");

    println!("\n5. Common Use Cases:");
    println!("   • LLM hyperparameters (temperature, top_p, max_tokens)");
    println!("   • Agent configuration (retry limits, timeouts)");
    println!("   • Model selection with cost constraints");
    println!("   • Prompt template optimization");
    println!("   • Multi-objective optimization (quality + cost + latency)");

    println!("\n🎯 Best Practices:");
    println!("   1. Start with 5-10 random samples for initialization");
    println!("   2. Use EI acquisition function as default");
    println!("   3. Run 20-50 total iterations (including initialization)");
    println!("   4. Normalize parameters to [0, 1] range if possible");
    println!("   5. Use log scale for parameters spanning orders of magnitude");
    println!("   6. Evaluate multiple runs with different seeds");
    println!("   7. Monitor convergence - stop early if no improvement");

    println!("\n⚡ Performance Tips:");
    println!("   • Bayesian optimization overhead is ~1-10ms per iteration");
    println!("   • Most time spent in objective function evaluation");
    println!("   • Parallelize evaluations if possible (batch Bayesian optimization)");
    println!("   • Cache results to avoid re-evaluating same configs");

    println!("\n✅ Examples Complete!");
    println!("{}", "=".repeat(70));

    Ok(())
}
