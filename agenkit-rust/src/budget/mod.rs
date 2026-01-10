//! Budget tracking and cost management for AI agents.
//!
//! This module provides comprehensive cost tracking, budget enforcement, and model optimization
//! for AI agent operations. It supports multiple LLM providers with automatic cost calculation
//! and intelligent budget management.
//!
//! # Components
//!
//! - **ModelPricing**: Centralized pricing database for all LLM providers
//! - **CostTracker**: Recording and querying costs per session/agent/global
//! - **BudgetLimiter**: Middleware enforcing cost limits with configurable actions
//! - **BudgetWarning**: Non-blocking warnings at configurable thresholds
//! - **ModelOptimizer**: Intelligent model routing based on query complexity
//! - **ThinkingBudgetAllocator**: Dynamic budget allocation for extended thinking modes
//!
//! # Example
//!
//! ```rust
//! use agenkit::budget::{ModelPricing, CostTracker, BudgetLimiter, BudgetConfig};
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // Create pricing database
//! let pricing = ModelPricing::new();
//!
//! // Create cost tracker
//! let tracker = CostTracker::new();
//!
//! // Create budget limiter
//! let config = BudgetConfig::builder()
//!     .session_limit(10.0)
//!     .agent_limit(100.0)
//!     .global_limit(500.0)
//!     .action("error")
//!     .build();
//!
//! let limiter = BudgetLimiter::new(tracker.clone(), config);
//!
//! // Track costs
//! tracker.record_cost("session-1", "agent-1", "gpt-4", 1000, 500, None).await?;
//!
//! // Query costs
//! let session_cost = tracker.get_session_cost("session-1").await?;
//! println!("Session cost: ${:.4}", session_cost);
//! # Ok(())
//! # }
//! ```

pub mod models;
pub mod pricing;
pub mod tracker;
pub mod limiter;
pub mod optimizer;
pub mod allocator;

pub use models::{CostRecord, UsageStats};
pub use pricing::ModelPricing;
pub use tracker::{CostStorage, CostTracker, InMemoryCostStorage};
pub use limiter::{BudgetConfig, BudgetConfigBuilder, BudgetLimiter};
pub use optimizer::{ModelOptimizer, OptimizerConfig};
pub use allocator::{ThinkingBudgetAllocator, ThinkingModeDetector};
