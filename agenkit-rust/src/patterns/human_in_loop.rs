//! Human-in-Loop Pattern - Agent Execution with Human Oversight
//!
//! Implements agent execution with human approval for high-stakes decisions.
//! When agent confidence is below a threshold, human approval is requested
//! before proceeding.
//!
//! # Key Concepts
//!
//! - **Confidence gates**: Approval required below confidence threshold
//! - **Human oversight**: Critical decisions reviewed by humans
//! - **Configurable thresholds**: Adjust approval requirements
//! - **Callback mechanism**: Flexible approval integration
//!
//! # Use Cases
//!
//! - Financial trading: approve large transactions
//! - Content moderation: verify edge cases
//! - Healthcare: approve treatment recommendations
//! - Legal: review contract changes
//! - Security: approve access grants
//!
//! # Performance Characteristics
//!
//! - **Time**: O(agent) + human response time (when approval needed)
//! - **Memory**: O(1) for message passing
//! - Blocking on human input when required
//!
//! # Example
//!
//! ```no_run
//! use agenkit::core::{Agent, Message};
//! use agenkit::patterns::{HumanInLoopAgent, HumanInLoopConfig, simple_approval_func};
//! use std::sync::Arc;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let trading_agent: Arc<dyn Agent> = todo!();
//! let human_in_loop = HumanInLoopAgent::new(HumanInLoopConfig {
//!     agent: trading_agent,
//!     approval_threshold: 0.8,
//!     approval_func: simple_approval_func(true),
//!     confidence_key: "confidence".to_string(),
//! })?;
//!
//! let result = human_in_loop.process(Message::with_text("user", "Execute trade")).await?;
//! # Ok(())
//! # }
//! ```

use std::sync::Arc;

use crate::core::{Agent, AgentError, Message};
use chrono::{DateTime, Utc};
use serde_json::json;

/// Approval request contains information about a pending approval decision.
#[derive(Debug, Clone)]
pub struct ApprovalRequest {
    /// Message is the agent's proposed response
    pub message: Message,
    /// Confidence is the agent's confidence level (0.0 to 1.0)
    pub confidence: f64,
    /// Context provides additional decision context
    pub context: std::collections::HashMap<String, serde_json::Value>,
    /// Timestamp when approval was requested
    pub timestamp: DateTime<Utc>,
}

impl ApprovalRequest {
    /// Create a new approval request.
    pub fn new(message: Message, confidence: f64) -> Self {
        Self {
            message,
            confidence,
            context: std::collections::HashMap::new(),
            timestamp: Utc::now(),
        }
    }

    /// Add context to the approval request.
    pub fn with_context(
        mut self,
        key: impl Into<String>,
        value: serde_json::Value,
    ) -> Self {
        self.context.insert(key.into(), value);
        self
    }
}

/// Approval response represents the human's decision.
#[derive(Debug, Clone)]
pub struct ApprovalResponse {
    /// Approved indicates if the action is approved
    pub approved: bool,
    /// Feedback provides optional human feedback
    pub feedback: Option<String>,
    /// ModifiedMessage is an optional modified version (if approved with changes)
    pub modified_message: Option<Message>,
}

impl ApprovalResponse {
    /// Create an approval response.
    pub fn new(approved: bool) -> Self {
        Self {
            approved,
            feedback: None,
            modified_message: None,
        }
    }

    /// Add feedback to the approval response.
    pub fn with_feedback(mut self, feedback: impl Into<String>) -> Self {
        self.feedback = Some(feedback.into());
        self
    }

    /// Add a modified message to the approval response.
    pub fn with_modified_message(mut self, message: Message) -> Self {
        self.modified_message = Some(message);
        self
    }
}

/// Function type called when human approval is needed.
///
/// The function receives an approval request and should return the human's
/// decision. This can be synchronous (blocking for user input) or asynchronous
/// (using a queue/callback system).
pub type ApprovalFunc = Box<dyn Fn(ApprovalRequest) -> Result<ApprovalResponse, AgentError> + Send + Sync>;

/// Configuration for HumanInLoopAgent.
pub struct HumanInLoopConfig {
    /// Agent to wrap with human approval
    pub agent: Arc<dyn Agent>,
    /// ApprovalThreshold for requiring approval (0.0 to 1.0, default: 0.8)
    /// Responses with confidence below this require approval
    pub approval_threshold: f64,
    /// ApprovalFunc is called when approval is needed
    pub approval_func: ApprovalFunc,
    /// ConfidenceKey specifies metadata key for confidence (default: "confidence")
    pub confidence_key: String,
}

/// Human-in-loop agent that wraps an agent with approval gates.
///
/// The agent executes normally, but when confidence is below the threshold,
/// human approval is requested before returning the response. This provides
/// oversight for high-stakes decisions while allowing autonomous operation
/// for routine tasks.
///
/// The human-in-loop pattern is ideal when autonomous operation needs
/// human oversight for critical or uncertain decisions.
///
/// # Example
///
/// ```no_run
/// use agenkit::core::{Agent, Message};
/// use agenkit::patterns::{HumanInLoopAgent, HumanInLoopConfig, simple_approval_func};
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let content_agent: Arc<dyn Agent> = todo!();
/// let human_in_loop = HumanInLoopAgent::new(HumanInLoopConfig {
///     agent: content_agent,
///     approval_threshold: 0.7,
///     approval_func: simple_approval_func(false), // Reject low confidence
///     confidence_key: "confidence".to_string(),
/// })?;
///
/// let input = Message::with_text("user", "Moderate this content");
/// let output = human_in_loop.process(input).await?;
/// # Ok(())
/// # }
/// ```
pub struct HumanInLoopAgent {
    agent: Arc<dyn Agent>,
    approval_threshold: f64,
    approval_func: ApprovalFunc,
    confidence_key: String,
}

impl HumanInLoopAgent {
    /// Create a new human-in-loop agent.
    ///
    /// # Arguments
    ///
    /// * `config` - Configuration with agent and approval settings
    ///
    /// The approval threshold determines when human approval is required.
    /// A threshold of 0.8 means approval is needed when confidence < 0.8.
    /// The agent's response metadata should include a confidence value.
    ///
    /// # Errors
    ///
    /// Returns an error if approval threshold is not between 0 and 1.
    pub fn new(config: HumanInLoopConfig) -> Result<Self, AgentError> {
        let threshold = if config.approval_threshold == 0.0 {
            0.8
        } else {
            config.approval_threshold
        };

        if !(0.0..=1.0).contains(&threshold) {
            return Err(AgentError::InvalidInput(format!(
                "approval threshold must be between 0 and 1 (got {})",
                threshold
            )));
        }

        let confidence_key = if config.confidence_key.is_empty() {
            "confidence".to_string()
        } else {
            config.confidence_key
        };

        Ok(Self {
            agent: config.agent,
            approval_threshold: threshold,
            approval_func: config.approval_func,
            confidence_key,
        })
    }

    /// Get the underlying agent.
    pub fn agent(&self) -> &Arc<dyn Agent> {
        &self.agent
    }

    /// Get the approval threshold.
    pub fn approval_threshold(&self) -> f64 {
        self.approval_threshold
    }

    /// Extract confidence value from message metadata.
    fn extract_confidence(&self, message: &Message) -> f64 {
        message
            .metadata
            .get(&self.confidence_key)
            .and_then(|v| v.as_f64())
            .unwrap_or(0.0)
    }
}

#[async_trait::async_trait]
impl Agent for HumanInLoopAgent {
    fn name(&self) -> &str {
        "HumanInLoopAgent"
    }

    fn capabilities(&self) -> Vec<String> {
        let mut caps = self.agent.capabilities();
        caps.push("human-in-loop".to_string());
        caps.push("approval".to_string());
        caps.push("oversight".to_string());
        caps
    }

    /// Execute the agent with human approval when needed.
    ///
    /// The process follows these steps:
    /// 1. Execute underlying agent
    /// 2. Extract confidence from response metadata
    /// 3. If confidence < threshold, request human approval
    /// 4. Return approved response or rejection message
    ///
    /// If approval is denied, a message indicating rejection is returned.
    /// If approval includes modifications, the modified message is returned.
    ///
    /// The final message includes metadata about the approval process.
    ///
    /// # Arguments
    ///
    /// * `message` - Input message
    ///
    /// # Returns
    ///
    /// Response from agent (possibly modified or rejected by human)
    ///
    /// # Errors
    ///
    /// Returns an error if agent execution or approval process fails.
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Execute underlying agent
        let mut response = self
            .agent
            .process(message.clone())
            .await
            .map_err(|e| AgentError::ProcessingError(format!("agent execution failed: {}", e)))?;

        // Extract confidence from metadata
        let confidence = self.extract_confidence(&response);

        // Check if approval needed
        let needs_approval = confidence < self.approval_threshold;

        // Add approval metadata
        response
            .metadata
            .insert("approval_needed".to_string(), json!(needs_approval));
        response
            .metadata
            .insert("confidence".to_string(), json!(confidence));
        response
            .metadata
            .insert("approval_threshold".to_string(), json!(self.approval_threshold));

        // If high confidence, return without approval
        if !needs_approval {
            response
                .metadata
                .insert("approval_status".to_string(), json!("bypassed"));
            return Ok(response);
        }

        // Request human approval
        let request = ApprovalRequest::new(response.clone(), confidence)
            .with_context("agent", json!(self.agent.name()))
            .with_context("approval_threshold", json!(self.approval_threshold))
            .with_context("original_message", json!(message.content_as_str().unwrap_or("")))
            .with_context(
                "confidence_shortfall",
                json!(self.approval_threshold - confidence),
            );

        let approval = (self.approval_func)(request).map_err(|e| {
            AgentError::ProcessingError(format!("approval request failed: {}", e))
        })?;

        // Handle approval decision
        if !approval.approved {
            // Request denied
            let mut rejection_msg =
                Message::with_text("agent", "Action rejected by human reviewer");

            if let Some(feedback) = approval.feedback {
                rejection_msg
                    .metadata
                    .insert("rejection_reason".to_string(), json!(feedback));
            }

            rejection_msg
                .metadata
                .insert("approval_status".to_string(), json!("rejected"));
            rejection_msg.metadata.insert(
                "original_response".to_string(),
                json!(response.content_as_str().unwrap_or("")),
            );
            rejection_msg
                .metadata
                .insert("confidence".to_string(), json!(confidence));

            return Ok(rejection_msg);
        }

        // Request approved
        let mut final_response = if let Some(modified) = approval.modified_message {
            // Use modified version
            let mut modified = modified;
            modified.metadata.insert(
                "approval_status".to_string(),
                json!("approved_with_modifications"),
            );
            modified.metadata.insert(
                "original_response".to_string(),
                json!(response.content_as_str().unwrap_or("")),
            );
            modified
        } else {
            response.metadata.insert("approval_status".to_string(), json!("approved"));
            response
        };

        if let Some(feedback) = approval.feedback {
            final_response
                .metadata
                .insert("approval_feedback".to_string(), json!(feedback));
        }

        Ok(final_response)
    }
}

/// Create a simple approval function for testing/demos.
///
/// This function automatically approves or rejects based on a static decision.
/// For production use, implement a custom approval function that prompts humans.
pub fn simple_approval_func(auto_approve: bool) -> ApprovalFunc {
    Box::new(move |request: ApprovalRequest| {
        Ok(ApprovalResponse::new(auto_approve).with_feedback(format!(
            "Auto-{} (confidence: {:.2})",
            if auto_approve { "approved" } else { "rejected" },
            request.confidence
        )))
    })
}

/// Create an approval function with dynamic confidence-based thresholds.
///
/// This allows different approval rules based on confidence levels:
/// - Very low confidence (< reject_below): always reject
/// - Low/medium confidence (reject_below to auto_approve_above): require manual approval (reject for safety)
/// - High confidence (>= auto_approve_above): auto-approve
pub fn confidence_based_approval_func(
    reject_below: f64,
    auto_approve_above: f64,
) -> ApprovalFunc {
    Box::new(move |request: ApprovalRequest| {
        if request.confidence < reject_below {
            return Ok(ApprovalResponse::new(false).with_feedback(format!(
                "Confidence too low ({:.2} < {:.2})",
                request.confidence, reject_below
            )));
        }

        if request.confidence >= auto_approve_above {
            return Ok(ApprovalResponse::new(true).with_feedback(format!(
                "Auto-approved ({:.2} >= {:.2})",
                request.confidence, auto_approve_above
            )));
        }

        // In this range, you would typically prompt a human
        // For this example, we'll reject to be safe
        Ok(ApprovalResponse::new(false).with_feedback(format!(
            "Manual approval required ({:.2} in threshold range)",
            request.confidence
        )))
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    // Mock agent for testing
    struct MockAgent {
        name: String,
        response: String,
        confidence: f64,
    }

    #[async_trait::async_trait]
    impl Agent for MockAgent {
        fn name(&self) -> &str {
            &self.name
        }

        fn capabilities(&self) -> Vec<String> {
            vec![format!("{}_capability", self.name)]
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Ok(Message::with_text("assistant", &self.response)
                .with_metadata("confidence", json!(self.confidence)))
        }
    }

    #[tokio::test]
    async fn test_human_in_loop_high_confidence() {
        let agent = Arc::new(MockAgent {
            name: "agent".to_string(),
            response: "High confidence response".to_string(),
            confidence: 0.95,
        });

        let human_in_loop = HumanInLoopAgent::new(HumanInLoopConfig {
            agent,
            approval_threshold: 0.8,
            approval_func: simple_approval_func(true),
            confidence_key: "confidence".to_string(),
        })
        .unwrap();

        let message = Message::with_text("user", "test");
        let result = human_in_loop.process(message).await.unwrap();

        assert_eq!(result.content_as_str(), Some("High confidence response"));
        assert_eq!(
            result.metadata.get("approval_status"),
            Some(&json!("bypassed"))
        );
        assert_eq!(result.metadata.get("approval_needed"), Some(&json!(false)));
    }

    #[tokio::test]
    async fn test_human_in_loop_low_confidence_approved() {
        let agent = Arc::new(MockAgent {
            name: "agent".to_string(),
            response: "Low confidence response".to_string(),
            confidence: 0.5,
        });

        let human_in_loop = HumanInLoopAgent::new(HumanInLoopConfig {
            agent,
            approval_threshold: 0.8,
            approval_func: simple_approval_func(true),
            confidence_key: "confidence".to_string(),
        })
        .unwrap();

        let message = Message::with_text("user", "test");
        let result = human_in_loop.process(message).await.unwrap();

        assert_eq!(result.content_as_str(), Some("Low confidence response"));
        assert_eq!(
            result.metadata.get("approval_status"),
            Some(&json!("approved"))
        );
        assert!(result.metadata.contains_key("approval_feedback"));
    }

    #[tokio::test]
    async fn test_human_in_loop_low_confidence_rejected() {
        let agent = Arc::new(MockAgent {
            name: "agent".to_string(),
            response: "Low confidence response".to_string(),
            confidence: 0.5,
        });

        let human_in_loop = HumanInLoopAgent::new(HumanInLoopConfig {
            agent,
            approval_threshold: 0.8,
            approval_func: simple_approval_func(false),
            confidence_key: "confidence".to_string(),
        })
        .unwrap();

        let message = Message::with_text("user", "test");
        let result = human_in_loop.process(message).await.unwrap();

        assert_eq!(
            result.content_as_str(),
            Some("Action rejected by human reviewer")
        );
        assert_eq!(
            result.metadata.get("approval_status"),
            Some(&json!("rejected"))
        );
        assert!(result.metadata.contains_key("original_response"));
    }

    #[tokio::test]
    async fn test_human_in_loop_invalid_threshold() {
        let agent = Arc::new(MockAgent {
            name: "agent".to_string(),
            response: "response".to_string(),
            confidence: 0.5,
        });

        let result = HumanInLoopAgent::new(HumanInLoopConfig {
            agent,
            approval_threshold: 1.5,
            approval_func: simple_approval_func(true),
            confidence_key: "confidence".to_string(),
        });

        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("must be between 0 and 1"));
    }

    #[tokio::test]
    async fn test_confidence_based_approval() {
        let approve_func = confidence_based_approval_func(0.3, 0.9);

        // Very low - reject
        let req1 = ApprovalRequest::new(Message::with_text("assistant", "test"), 0.2);
        let resp1 = approve_func(req1).unwrap();
        assert!(!resp1.approved);
        assert!(resp1.feedback.unwrap().contains("too low"));

        // High - approve
        let req2 = ApprovalRequest::new(Message::with_text("assistant", "test"), 0.95);
        let resp2 = approve_func(req2).unwrap();
        assert!(resp2.approved);
        assert!(resp2.feedback.unwrap().contains("Auto-approved"));

        // Medium - reject (needs manual approval)
        let req3 = ApprovalRequest::new(Message::with_text("assistant", "test"), 0.6);
        let resp3 = approve_func(req3).unwrap();
        assert!(!resp3.approved);
        assert!(resp3.feedback.unwrap().contains("Manual approval required"));
    }

    #[tokio::test]
    async fn test_human_in_loop_capabilities() {
        let agent = Arc::new(MockAgent {
            name: "agent".to_string(),
            response: "response".to_string(),
            confidence: 0.5,
        });

        let human_in_loop = HumanInLoopAgent::new(HumanInLoopConfig {
            agent,
            approval_threshold: 0.8,
            approval_func: simple_approval_func(true),
            confidence_key: "confidence".to_string(),
        })
        .unwrap();

        let caps = human_in_loop.capabilities();
        assert!(caps.contains(&"human-in-loop".to_string()));
        assert!(caps.contains(&"approval".to_string()));
        assert!(caps.contains(&"oversight".to_string()));
    }

    #[tokio::test]
    async fn test_human_in_loop_missing_confidence() {
        let agent = Arc::new(MockAgent {
            name: "agent".to_string(),
            response: "No confidence metadata".to_string(),
            confidence: 0.0, // Agent won't set confidence
        });

        // Override process to not include confidence metadata
        struct NoConfidenceAgent {
            name: String,
            response: String,
        }

        #[async_trait::async_trait]
        impl Agent for NoConfidenceAgent {
            fn name(&self) -> &str {
                &self.name
            }

            async fn process(&self, _message: Message) -> Result<Message, AgentError> {
                // Don't include confidence metadata
                Ok(Message::with_text("assistant", &self.response))
            }
        }

        let no_conf_agent = Arc::new(NoConfidenceAgent {
            name: "no_conf".to_string(),
            response: "response".to_string(),
        });

        let human_in_loop = HumanInLoopAgent::new(HumanInLoopConfig {
            agent: no_conf_agent,
            approval_threshold: 0.8,
            approval_func: simple_approval_func(false),
            confidence_key: "confidence".to_string(),
        })
        .unwrap();

        let message = Message::with_text("user", "test");
        let result = human_in_loop.process(message).await.unwrap();

        // Missing confidence defaults to 0.0, which triggers approval
        assert_eq!(
            result.content_as_str(),
            Some("Action rejected by human reviewer")
        );
    }
}
