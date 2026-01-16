//! Safety framework for securing AI agent operations.
//!
//! Provides comprehensive security features including input validation,
//! output validation, permission-based access control, anomaly detection,
//! and security audit logging.
//!
//! # Components
//!
//! - **Input Validation**: Detects prompt injection attacks, validates content
//! - **Output Validation**: Schema validation, sensitive data redaction
//! - **Permissions**: Role-based access control (RBAC), sandbox constraints
//! - **Anomaly Detection**: Behavioral monitoring, suspicious pattern detection
//! - **Audit Logging**: Security event logging with structured audit trails
//!
//! # Example
//!
//! ```rust
//! use agenkit::safety::{
//!     InputValidationMiddleware, PromptInjectionDetector, ContentFilter,
//! };
//! use agenkit::core::{Agent, Message};
//!
//! # async fn example() {
//! # struct MyAgent;
//! # #[async_trait::async_trait]
//! # impl Agent for MyAgent {
//! #     fn name(&self) -> &str { "test" }
//! #     async fn process(&self, msg: Message) -> Result<Message, agenkit::core::AgentError> {
//! #         Ok(Message::with_text("assistant", "ok"))
//! #     }
//! # }
//! let agent = MyAgent;
//!
//! // Add input validation
//! let safe_agent = InputValidationMiddleware::new(agent)
//!     .with_prompt_injection_detector()
//!     .with_content_filter();
//!
//! let msg = Message::with_text("user", "Hello!");
//! let response = safe_agent.process(msg).await;
//! # }
//! ```

pub mod anomaly_detection;
pub mod audit;
pub mod errors;
pub mod input_validation;
pub mod output_validation;
pub mod permissions;

pub use anomaly_detection::{AnomalyDetectionMiddleware, AnomalyDetector, SecurityEvent};
pub use audit::{AuditEvent, AuditEventType, AuditSeverity, SecurityAuditLogger};
pub use errors::{PermissionDeniedError, SecurityError, ValidationError};
pub use input_validation::{ContentFilter, InputValidationMiddleware, PromptInjectionDetector};
pub use output_validation::{OutputValidationMiddleware, SchemaValidator, SensitiveDataRedactor};
pub use permissions::{Permission, PermissionMiddleware, Role, Sandbox};
