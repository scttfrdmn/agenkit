///! Conditional agent composition pattern.
///!
///! Routes messages to different agents based on conditions.

use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use serde_json::json;
use std::sync::Arc;

/// Condition function type.
///
/// Returns true if the message should be routed to the associated agent.
pub type Condition = Arc<dyn Fn(&Message) -> bool + Send + Sync>;

/// Represents a condition-agent pair.
pub struct ConditionalRoute {
    pub condition: Condition,
    pub agent: Arc<dyn Agent>,
}

/// Agent that routes messages to different agents based on conditions.
///
/// Evaluates conditions in order and routes to the first matching agent.
/// Falls back to default agent if no condition matches.
///
/// # Example
///
/// ```no_run
/// use agenkit::composition::{ConditionalAgent, content_contains};
/// use agenkit::core::{Agent, Message};
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let tech_agent: Arc<dyn Agent> = todo!();
/// # let general_agent: Arc<dyn Agent> = todo!();
/// # let default_agent: Arc<dyn Agent> = todo!();
/// let mut conditional = ConditionalAgent::new("router", default_agent);
///
/// conditional.add_route(content_contains("technical"), tech_agent);
/// conditional.add_route(content_contains("general"), general_agent);
///
/// let message = Message::with_text("user", "Technical question");
/// let result = conditional.process(message).await?;
/// # Ok(())
/// # }
/// ```
pub struct ConditionalAgent {
    name: String,
    routes: Vec<ConditionalRoute>,
    default_agent: Arc<dyn Agent>,
}

impl ConditionalAgent {
    /// Create a new conditional agent.
    ///
    /// # Arguments
    ///
    /// * `name` - Name of this conditional agent
    /// * `default_agent` - Agent to use when no condition matches
    pub fn new(name: impl Into<String>, default_agent: Arc<dyn Agent>) -> Self {
        Self {
            name: name.into(),
            routes: Vec::new(),
            default_agent,
        }
    }

    /// Add a conditional route.
    ///
    /// # Arguments
    ///
    /// * `condition` - Function that returns true if this agent should be used
    /// * `agent` - Agent to use when condition is met
    pub fn add_route(&mut self, condition: Condition, agent: Arc<dyn Agent>) {
        self.routes.push(ConditionalRoute { condition, agent });
    }

    /// Get the conditional routes.
    pub fn routes(&self) -> &[ConditionalRoute] {
        &self.routes
    }

    /// Get the default agent.
    pub fn default_agent(&self) -> &Arc<dyn Agent> {
        &self.default_agent
    }
}

#[async_trait]
impl Agent for ConditionalAgent {
    fn name(&self) -> &str {
        &self.name
    }

    fn capabilities(&self) -> Vec<String> {
        // Collect unique capabilities from all agents
        let mut cap_set = std::collections::HashSet::new();

        // Add default agent capabilities
        for cap in self.default_agent.capabilities() {
            cap_set.insert(cap);
        }

        // Add route agent capabilities
        for route in &self.routes {
            for cap in route.agent.capabilities() {
                cap_set.insert(cap);
            }
        }

        let mut capabilities: Vec<String> = cap_set.into_iter().collect();
        capabilities.push("conditional".to_string());

        capabilities
    }

    /// Route the message to the first agent whose condition is met.
    ///
    /// # Arguments
    ///
    /// * `message` - Input message
    ///
    /// # Returns
    ///
    /// Response from the selected agent
    ///
    /// # Errors
    ///
    /// Returns an error if agent execution fails.
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Try each route in order
        for (i, route) in self.routes.iter().enumerate() {
            if (route.condition)(&message) {
                match route.agent.process(message).await {
                    Ok(mut result) => {
                        // Add metadata about routing decision
                        result
                            .metadata
                            .insert("conditional_agent_used".to_string(), json!(route.agent.name()));
                        result
                            .metadata
                            .insert("conditional_route".to_string(), json!(i + 1));
                        return Ok(result);
                    }
                    Err(err) => {
                        return Err(AgentError::ProcessingError(format!(
                            "Route {} ({}) failed: {}",
                            i + 1,
                            route.agent.name(),
                            err
                        )));
                    }
                }
            }
        }

        // No condition matched, use default agent
        match self.default_agent.process(message).await {
            Ok(mut result) => {
                // Add metadata about using default
                result.metadata.insert(
                    "conditional_agent_used".to_string(),
                    json!(self.default_agent.name()),
                );
                result
                    .metadata
                    .insert("conditional_route".to_string(), json!("default"));
                Ok(result)
            }
            Err(err) => Err(AgentError::ProcessingError(format!(
                "Default agent ({}) failed: {}",
                self.default_agent.name(),
                err
            ))),
        }
    }
}

// ==========================
// Common condition helpers
// ==========================

/// Return a condition that checks if message content contains a substring.
pub fn content_contains(substr: impl Into<String>) -> Condition {
    let substr = substr.into();
    Arc::new(move |message: &Message| {
        message
            .content_as_str()
            .map(|s| s.contains(&substr))
            .unwrap_or(false)
    })
}

/// Return a condition that checks if message role equals the given role.
pub fn role_equals(role: impl Into<String>) -> Condition {
    let role = role.into();
    Arc::new(move |message: &Message| message.role == role)
}

/// Return a condition that checks if metadata contains a key.
pub fn metadata_has_key(key: impl Into<String>) -> Condition {
    let key = key.into();
    Arc::new(move |message: &Message| message.metadata.contains_key(&key))
}

/// Return a condition that checks if metadata key equals value.
pub fn metadata_equals(key: impl Into<String>, value: serde_json::Value) -> Condition {
    let key = key.into();
    Arc::new(move |message: &Message| {
        message
            .metadata
            .get(&key)
            .map(|v| v == &value)
            .unwrap_or(false)
    })
}

/// Combine multiple conditions with AND logic.
pub fn and_conditions(conditions: Vec<Condition>) -> Condition {
    Arc::new(move |message: &Message| conditions.iter().all(|cond| cond(message)))
}

/// Combine multiple conditions with OR logic.
pub fn or_conditions(conditions: Vec<Condition>) -> Condition {
    Arc::new(move |message: &Message| conditions.iter().any(|cond| cond(message)))
}

/// Negate a condition.
pub fn not_condition(cond: Condition) -> Condition {
    Arc::new(move |message: &Message| !cond(message))
}

#[cfg(test)]
mod tests {
    use super::*;

    // Mock agent for testing
    struct NamedAgent {
        name: String,
    }

    #[async_trait]
    impl Agent for NamedAgent {
        fn name(&self) -> &str {
            &self.name
        }

        fn capabilities(&self) -> Vec<String> {
            vec![self.name.clone()]
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Ok(Message::with_text(
                "agent",
                format!("Processed by {}", self.name),
            ))
        }
    }

    #[tokio::test]
    async fn test_conditional_routing() {
        let tech_agent = Arc::new(NamedAgent {
            name: "tech-agent".to_string(),
        });
        let general_agent = Arc::new(NamedAgent {
            name: "general-agent".to_string(),
        });
        let default_agent = Arc::new(NamedAgent {
            name: "default-agent".to_string(),
        });

        let mut conditional = ConditionalAgent::new("router", default_agent);
        conditional.add_route(content_contains("technical"), tech_agent);
        conditional.add_route(content_contains("general"), general_agent);

        let input = Message::with_text("user", "This is a technical question");
        let result = conditional.process(input).await.unwrap();

        assert_eq!(result.content_as_str().unwrap(), "Processed by tech-agent");
        assert_eq!(
            result.metadata.get("conditional_agent_used").unwrap(),
            "tech-agent"
        );
        assert_eq!(result.metadata.get("conditional_route").unwrap(), 1);
    }

    #[tokio::test]
    async fn test_conditional_default() {
        let tech_agent = Arc::new(NamedAgent {
            name: "tech-agent".to_string(),
        });
        let default_agent = Arc::new(NamedAgent {
            name: "default-agent".to_string(),
        });

        let mut conditional = ConditionalAgent::new("router", default_agent);
        conditional.add_route(content_contains("technical"), tech_agent);

        let input = Message::with_text("user", "This is something else");
        let result = conditional.process(input).await.unwrap();

        assert_eq!(
            result.content_as_str().unwrap(),
            "Processed by default-agent"
        );
        assert_eq!(
            result.metadata.get("conditional_agent_used").unwrap(),
            "default-agent"
        );
        assert_eq!(
            result.metadata.get("conditional_route").unwrap(),
            "default"
        );
    }

    #[tokio::test]
    async fn test_condition_helpers() {
        let message = Message::with_text("user", "This is a test");

        // content_contains
        let cond = content_contains("test");
        assert!(cond(&message));
        let cond = content_contains("missing");
        assert!(!cond(&message));

        // role_equals
        let cond = role_equals("user");
        assert!(cond(&message));
        let cond = role_equals("agent");
        assert!(!cond(&message));

        // metadata_has_key
        let mut message_with_meta = Message::with_text("user", "test");
        message_with_meta
            .metadata
            .insert("priority".to_string(), json!("high"));
        let cond = metadata_has_key("priority");
        assert!(cond(&message_with_meta));
        assert!(!cond(&message));

        // metadata_equals
        let cond = metadata_equals("priority", json!("high"));
        assert!(cond(&message_with_meta));
        let cond = metadata_equals("priority", json!("low"));
        assert!(!cond(&message_with_meta));

        // and_conditions
        let cond = and_conditions(vec![content_contains("test"), role_equals("user")]);
        assert!(cond(&message));

        // or_conditions
        let cond = or_conditions(vec![content_contains("missing"), role_equals("user")]);
        assert!(cond(&message));

        // not_condition
        let cond = not_condition(content_contains("missing"));
        assert!(cond(&message));
    }

    #[tokio::test]
    async fn test_conditional_capabilities() {
        let agent1 = Arc::new(NamedAgent {
            name: "agent1".to_string(),
        });
        let agent2 = Arc::new(NamedAgent {
            name: "agent2".to_string(),
        });
        let default_agent = Arc::new(NamedAgent {
            name: "default".to_string(),
        });

        let mut conditional = ConditionalAgent::new("router", default_agent);
        conditional.add_route(content_contains("test"), agent1);
        conditional.add_route(content_contains("other"), agent2);

        let capabilities = conditional.capabilities();
        assert!(capabilities.contains(&"agent1".to_string()));
        assert!(capabilities.contains(&"agent2".to_string()));
        assert!(capabilities.contains(&"default".to_string()));
        assert!(capabilities.contains(&"conditional".to_string()));
    }
}
