//! Error types for the safety framework.

use thiserror::Error;

/// Security-related errors.
#[derive(Error, Debug, Clone)]
pub enum SecurityError {
    #[error("validation error: {0}")]
    Validation(String),

    #[error("permission denied: {0}")]
    PermissionDenied(String),

    #[error("anomaly detected: {0}")]
    AnomalyDetected(String),

    #[error("audit error: {0}")]
    AuditError(String),

    #[error("configuration error: {0}")]
    ConfigError(String),
}

/// Validation-specific errors.
#[derive(Error, Debug, Clone)]
pub enum ValidationError {
    #[error("prompt injection detected (score: {score}): {message}")]
    PromptInjection { score: u32, message: String },

    #[error("content filter violation: {0}")]
    ContentFilterViolation(String),

    #[error("invalid schema: {0}")]
    SchemaValidation(String),

    #[error("size limit exceeded: {0}")]
    SizeLimit(String),

    #[error("PII detected: {0}")]
    PiiDetected(String),
}

impl From<ValidationError> for SecurityError {
    fn from(err: ValidationError) -> Self {
        SecurityError::Validation(err.to_string())
    }
}

/// Permission denied error.
#[derive(Error, Debug, Clone)]
#[error("permission denied: {permission} (role: {role})")]
pub struct PermissionDeniedError {
    pub permission: String,
    pub role: String,
}

impl From<PermissionDeniedError> for SecurityError {
    fn from(err: PermissionDeniedError) -> Self {
        SecurityError::PermissionDenied(err.to_string())
    }
}
