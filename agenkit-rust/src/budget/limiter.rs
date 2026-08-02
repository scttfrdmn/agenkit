//! Budget limiting middleware for enforcing cost constraints.

use crate::budget::tracker::CostTracker;
use crate::core::{Agent, AgentError, IntrospectionResult, Message};
use async_trait::async_trait;
use std::str::FromStr;
use std::sync::Arc;
use thiserror::Error;
use tracing::warn;

/// Budget limit errors.
#[derive(Error, Debug)]
pub enum BudgetError {
    #[error("session budget exceeded: ${0:.4} >= ${1:.4}")]
    SessionLimitExceeded(f64, f64),

    #[error("agent budget exceeded: ${0:.4} >= ${1:.4}")]
    AgentLimitExceeded(f64, f64),

    #[error("global budget exceeded: ${0:.4} >= ${1:.4}")]
    GlobalLimitExceeded(f64, f64),

    #[error("budget tracking error: {0}")]
    TrackingError(String),
}

/// Budget enforcement action.
#[derive(Debug, Clone, PartialEq)]
pub enum BudgetAction {
    /// Raise an error when limit exceeded
    Error,
    /// Log a warning when limit exceeded
    Warning,
    /// Switch to a cheaper model when limit exceeded
    SwitchModel(String),
}

impl FromStr for BudgetAction {
    type Err = String;

    /// Parse action from string.
    ///
    /// Accepts `"error"`, `"warning"`, or `"switch:<model>"`.
    ///
    /// This was an inherent `BudgetAction::from_str` shadowing the standard trait
    /// method (#778). The signature is unchanged, so `BudgetAction::from_str(s)` still
    /// compiles for callers with `std::str::FromStr` in scope, and `s.parse()` now
    /// works too.
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "error" => Ok(BudgetAction::Error),
            "warning" => Ok(BudgetAction::Warning),
            s if s.starts_with("switch:") => {
                let model = s.strip_prefix("switch:").unwrap();
                Ok(BudgetAction::SwitchModel(model.to_string()))
            }
            _ => Err(format!("Unknown budget action: {}", s)),
        }
    }
}

/// Budget limiter configuration.
#[derive(Debug, Clone)]
pub struct BudgetConfig {
    /// Session budget limit (USD)
    pub session_limit: Option<f64>,

    /// Agent budget limit (USD)
    pub agent_limit: Option<f64>,

    /// Global budget limit (USD)
    pub global_limit: Option<f64>,

    /// Action to take when limit exceeded
    pub action: BudgetAction,

    /// Warning threshold (percentage of limit, 0.0-1.0)
    pub warning_threshold: f64,
}

impl Default for BudgetConfig {
    fn default() -> Self {
        Self {
            session_limit: Some(10.0),
            agent_limit: Some(100.0),
            global_limit: Some(500.0),
            action: BudgetAction::Error,
            warning_threshold: 0.8,
        }
    }
}

/// Budget configuration builder.
pub struct BudgetConfigBuilder {
    config: BudgetConfig,
}

impl BudgetConfigBuilder {
    /// Create a new builder.
    pub fn new() -> Self {
        Self {
            config: BudgetConfig::default(),
        }
    }

    /// Set session limit.
    pub fn session_limit(mut self, limit: f64) -> Self {
        self.config.session_limit = Some(limit);
        self
    }

    /// Set agent limit.
    pub fn agent_limit(mut self, limit: f64) -> Self {
        self.config.agent_limit = Some(limit);
        self
    }

    /// Set global limit.
    pub fn global_limit(mut self, limit: f64) -> Self {
        self.config.global_limit = Some(limit);
        self
    }

    /// Set action.
    ///
    /// An unrecognised action string is ignored and the previous action kept. That is
    /// deliberate for a builder that cannot return an error, but it is silent, so it
    /// is logged -- otherwise a typo like `"warn"` leaves the default `Error` action
    /// in place with no indication (#778).
    pub fn action(mut self, action: &str) -> Self {
        match action.parse::<BudgetAction>() {
            Ok(parsed) => self.config.action = parsed,
            Err(err) => warn!("ignoring invalid budget action: {}", err),
        }
        self
    }

    /// Set warning threshold.
    pub fn warning_threshold(mut self, threshold: f64) -> Self {
        self.config.warning_threshold = threshold;
        self
    }

    /// Build the configuration.
    pub fn build(self) -> BudgetConfig {
        self.config
    }
}

impl Default for BudgetConfigBuilder {
    fn default() -> Self {
        Self::new()
    }
}

/// Budget limiter middleware.
pub struct BudgetLimiter<A: Agent> {
    agent: Arc<A>,
    agent_name: String,
    tracker: CostTracker,
    config: BudgetConfig,
}

impl<A: Agent + 'static> BudgetLimiter<A> {
    /// Create a new budget limiter.
    pub fn new(agent: A, agent_name: String, tracker: CostTracker, config: BudgetConfig) -> Self {
        Self {
            agent: Arc::new(agent),
            agent_name,
            tracker,
            config,
        }
    }

    /// Check if budget limits are exceeded.
    async fn check_limits(&self, session_id: &str) -> Result<(), BudgetError> {
        // Check session limit
        if let Some(session_limit) = self.config.session_limit {
            let session_cost = self
                .tracker
                .get_session_cost(session_id)
                .await
                .map_err(BudgetError::TrackingError)?;

            if session_cost >= session_limit {
                return Err(BudgetError::SessionLimitExceeded(
                    session_cost,
                    session_limit,
                ));
            }

            // Check warning threshold
            if session_cost >= session_limit * self.config.warning_threshold {
                warn!(
                    "Session {} approaching budget limit: ${:.4} / ${:.4}",
                    session_id, session_cost, session_limit
                );
            }
        }

        // Check agent limit
        if let Some(agent_limit) = self.config.agent_limit {
            let agent_cost = self
                .tracker
                .get_agent_cost(&self.agent_name)
                .await
                .map_err(BudgetError::TrackingError)?;

            if agent_cost >= agent_limit {
                return Err(BudgetError::AgentLimitExceeded(agent_cost, agent_limit));
            }

            // Check warning threshold
            if agent_cost >= agent_limit * self.config.warning_threshold {
                warn!(
                    "Agent {} approaching budget limit: ${:.4} / ${:.4}",
                    self.agent_name, agent_cost, agent_limit
                );
            }
        }

        // Check global limit
        if let Some(global_limit) = self.config.global_limit {
            let global_cost = self
                .tracker
                .get_global_cost()
                .await
                .map_err(BudgetError::TrackingError)?;

            if global_cost >= global_limit {
                return Err(BudgetError::GlobalLimitExceeded(global_cost, global_limit));
            }

            // Check warning threshold
            if global_cost >= global_limit * self.config.warning_threshold {
                warn!(
                    "Global budget approaching limit: ${:.4} / ${:.4}",
                    global_cost, global_limit
                );
            }
        }

        Ok(())
    }

    /// Handle budget exceeded based on action.
    fn handle_budget_exceeded(&self, error: BudgetError) -> Result<(), AgentError> {
        match self.config.action {
            BudgetAction::Error => Err(AgentError::ProcessingError(format!(
                "Budget limit exceeded: {}",
                error
            ))),
            BudgetAction::Warning => {
                warn!("Budget limit exceeded: {}", error);
                Ok(())
            }
            BudgetAction::SwitchModel(ref model) => {
                warn!("Budget limit exceeded, switching to model: {}", model);
                // In a real implementation, we would modify the message to use the cheaper model
                Ok(())
            }
        }
    }

    /// Process message with session tracking.
    pub async fn process_with_session(
        &self,
        message: &Message,
        session_id: &str,
    ) -> Result<Message, AgentError> {
        // Check budget before processing
        if let Err(e) = self.check_limits(session_id).await {
            self.handle_budget_exceeded(e)?;
        }

        // Process message
        let response = self.agent.process(message.clone()).await?;

        Ok(response)
    }
}

#[async_trait]
impl<A: Agent + 'static> Agent for BudgetLimiter<A> {
    fn name(&self) -> &str {
        &self.agent_name
    }

    fn capabilities(&self) -> Vec<String> {
        self.agent.capabilities()
    }

    fn introspect(&self) -> IntrospectionResult {
        let mut result = self.agent.introspect();
        result.metadata.insert(
            "budget_limiter".to_string(),
            serde_json::json!({
                "session_limit": self.config.session_limit,
                "agent_limit": self.config.agent_limit,
                "global_limit": self.config.global_limit,
                "action": format!("{:?}", self.config.action),
                "warning_threshold": self.config.warning_threshold,
            }),
        );
        result
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Default session for Agent trait compatibility
        self.process_with_session(&message, "default").await
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct TestAgent;

    #[async_trait]
    impl Agent for TestAgent {
        fn name(&self) -> &str {
            "test"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Ok(Message::with_text("assistant", "response"))
        }
    }

    #[tokio::test]
    async fn test_budget_limiter_within_limits() {
        let tracker = CostTracker::new();

        // Record a small cost
        tracker
            .record_cost("session-1", "agent-1", "gpt-3.5-turbo", 100, 50, 0, None)
            .await
            .unwrap();

        let config = BudgetConfig {
            session_limit: Some(10.0),
            agent_limit: Some(100.0),
            global_limit: Some(500.0),
            action: BudgetAction::Error,
            warning_threshold: 0.8,
        };

        let agent = TestAgent;
        let limiter = BudgetLimiter::new(agent, "agent-1".to_string(), tracker, config);

        let msg = Message::with_text("user", "test");
        let result = limiter.process_with_session(&msg, "session-1").await;

        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_budget_limiter_session_exceeded() {
        let tracker = CostTracker::new();

        // Record a large cost that exceeds session limit
        tracker
            .record_cost_explicit(
                "session-1",
                "agent-1",
                "gpt-4",
                100000,
                50000,
                0,
                15.0,
                0.0,
                None,
            )
            .await
            .unwrap();

        let config = BudgetConfig {
            session_limit: Some(10.0),
            agent_limit: Some(100.0),
            global_limit: Some(500.0),
            action: BudgetAction::Error,
            warning_threshold: 0.8,
        };

        let agent = TestAgent;
        let limiter = BudgetLimiter::new(agent, "agent-1".to_string(), tracker, config);

        let msg = Message::with_text("user", "test");
        let result = limiter.process_with_session(&msg, "session-1").await;

        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_budget_limiter_warning_action() {
        let tracker = CostTracker::new();

        // Record a large cost
        tracker
            .record_cost_explicit(
                "session-1",
                "agent-1",
                "gpt-4",
                100000,
                50000,
                0,
                15.0,
                0.0,
                None,
            )
            .await
            .unwrap();

        let config = BudgetConfig {
            session_limit: Some(10.0),
            agent_limit: Some(100.0),
            global_limit: Some(500.0),
            action: BudgetAction::Warning, // Warning instead of error
            warning_threshold: 0.8,
        };

        let agent = TestAgent;
        let limiter = BudgetLimiter::new(agent, "agent-1".to_string(), tracker, config);

        let msg = Message::with_text("user", "test");
        let result = limiter.process_with_session(&msg, "session-1").await;

        // Should succeed with warning action
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_budget_config_builder() {
        let config = BudgetConfigBuilder::new()
            .session_limit(5.0)
            .agent_limit(50.0)
            .global_limit(250.0)
            .action("warning")
            .warning_threshold(0.9)
            .build();

        assert_eq!(config.session_limit, Some(5.0));
        assert_eq!(config.agent_limit, Some(50.0));
        assert_eq!(config.global_limit, Some(250.0));
        assert_eq!(config.action, BudgetAction::Warning);
        assert_eq!(config.warning_threshold, 0.9);
    }
}
