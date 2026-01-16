//! Output validation and sensitive data redaction.
//!
//! Provides schema validation and automatic redaction of sensitive data
//! from agent outputs.

use crate::core::{Agent, AgentError, IntrospectionResult, Message};
use async_trait::async_trait;
use regex::Regex;
use serde_json::Value;
use std::collections::{HashMap, HashSet};

/// Schema validator configuration.
#[derive(Debug, Clone)]
pub struct SchemaValidatorConfig {
    /// Expected fields with their types
    pub expected_fields: HashMap<String, String>,
    /// Required fields
    pub required_fields: HashSet<String>,
    /// Allow additional fields not in schema
    pub allow_additional_fields: bool,
}

impl Default for SchemaValidatorConfig {
    fn default() -> Self {
        Self {
            expected_fields: HashMap::new(),
            required_fields: HashSet::new(),
            allow_additional_fields: true,
        }
    }
}

/// Schema validator for output structure.
pub struct SchemaValidator {
    config: SchemaValidatorConfig,
}

impl SchemaValidator {
    /// Create a new schema validator.
    pub fn new(config: SchemaValidatorConfig) -> Self {
        Self { config }
    }

    /// Validate JSON value against schema.
    pub fn validate(&self, value: &Value) -> (bool, Option<String>) {
        let obj = match value.as_object() {
            Some(o) => o,
            None => return (false, Some("Expected JSON object".to_string())),
        };

        // Check required fields
        for required in &self.config.required_fields {
            if !obj.contains_key(required) {
                return (false, Some(format!("Missing required field: {}", required)));
            }
        }

        // Check field types
        for (field, expected_type) in &self.config.expected_fields {
            if let Some(field_value) = obj.get(field) {
                if !Self::check_type(field_value, expected_type) {
                    return (
                        false,
                        Some(format!(
                            "Field '{}' has wrong type (expected: {})",
                            field, expected_type
                        )),
                    );
                }
            }
        }

        // Check for unexpected fields
        if !self.config.allow_additional_fields {
            for key in obj.keys() {
                if !self.config.expected_fields.contains_key(key) {
                    return (false, Some(format!("Unexpected field: {}", key)));
                }
            }
        }

        (true, None)
    }

    fn check_type(value: &Value, expected_type: &str) -> bool {
        match expected_type {
            "string" => value.is_string(),
            "number" => value.is_number(),
            "boolean" => value.is_boolean(),
            "array" => value.is_array(),
            "object" => value.is_object(),
            _ => true, // Unknown type, allow
        }
    }
}

/// Sensitive data redactor configuration.
#[derive(Debug, Clone)]
pub struct SensitiveDataRedactorConfig {
    /// Redaction placeholder text
    pub redaction_text: String,
    /// Enable field name detection
    pub enable_field_detection: bool,
    /// Enable pattern-based detection
    pub enable_pattern_detection: bool,
}

impl Default for SensitiveDataRedactorConfig {
    fn default() -> Self {
        Self {
            redaction_text: "***REDACTED***".to_string(),
            enable_field_detection: true,
            enable_pattern_detection: true,
        }
    }
}

/// Sensitive data redactor.
pub struct SensitiveDataRedactor {
    config: SensitiveDataRedactorConfig,
    sensitive_field_names: HashSet<String>,
    patterns: Vec<(String, Regex)>,
}

impl SensitiveDataRedactor {
    /// Create a new sensitive data redactor.
    pub fn new() -> Self {
        Self::with_config(SensitiveDataRedactorConfig::default())
    }

    /// Create with custom configuration.
    pub fn with_config(config: SensitiveDataRedactorConfig) -> Self {
        let sensitive_field_names = Self::build_sensitive_field_names();
        let patterns = Self::build_patterns();

        Self {
            config,
            sensitive_field_names,
            patterns,
        }
    }

    fn build_sensitive_field_names() -> HashSet<String> {
        vec![
            "password",
            "api_key",
            "token",
            "secret",
            "auth",
            "credential",
            "private_key",
            "access_key",
            "apikey",
        ]
        .into_iter()
        .map(|s| s.to_string())
        .collect()
    }

    fn build_patterns() -> Vec<(String, Regex)> {
        vec![
            (
                "API Key (sk-)".to_string(),
                Regex::new(r"sk-[a-zA-Z0-9]{32,}").unwrap(),
            ),
            (
                "AWS Key".to_string(),
                Regex::new(r"AKIA[0-9A-Z]{16}").unwrap(),
            ),
            (
                "GitHub Token".to_string(),
                Regex::new(r"ghp_[a-zA-Z0-9]{36}").unwrap(),
            ),
            (
                "JWT".to_string(),
                Regex::new(r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+").unwrap(),
            ),
            (
                "Email".to_string(),
                Regex::new(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b").unwrap(),
            ),
            (
                "Phone (US)".to_string(),
                Regex::new(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b").unwrap(),
            ),
            (
                "SSN".to_string(),
                Regex::new(r"\b\d{3}-\d{2}-\d{4}\b").unwrap(),
            ),
            (
                "Credit Card".to_string(),
                Regex::new(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b").unwrap(),
            ),
        ]
    }

    /// Redact sensitive data from text.
    pub fn redact_text(&self, text: &str) -> String {
        if !self.config.enable_pattern_detection {
            return text.to_string();
        }

        let mut result = text.to_string();
        for (data_type, pattern) in &self.patterns {
            result = pattern
                .replace_all(
                    &result,
                    format!("{}[{}]", self.config.redaction_text, data_type),
                )
                .to_string();
        }
        result
    }

    /// Redact sensitive data from JSON value (recursive).
    pub fn redact_json(&self, value: &Value) -> Value {
        match value {
            Value::Object(obj) => {
                let mut new_obj = serde_json::Map::new();
                for (key, val) in obj {
                    if self.config.enable_field_detection
                        && self.sensitive_field_names.contains(&key.to_lowercase())
                    {
                        new_obj.insert(
                            key.clone(),
                            Value::String(self.config.redaction_text.clone()),
                        );
                    } else {
                        new_obj.insert(key.clone(), self.redact_json(val));
                    }
                }
                Value::Object(new_obj)
            }
            Value::String(s) => {
                if self.config.enable_pattern_detection {
                    Value::String(self.redact_text(s))
                } else {
                    value.clone()
                }
            }
            Value::Array(arr) => Value::Array(arr.iter().map(|v| self.redact_json(v)).collect()),
            _ => value.clone(),
        }
    }
}

impl Default for SensitiveDataRedactor {
    fn default() -> Self {
        Self::new()
    }
}

/// Output validation middleware.
pub struct OutputValidationMiddleware<A: Agent> {
    inner: A,
    schema_validator: Option<SchemaValidator>,
    redactor: Option<SensitiveDataRedactor>,
    max_size: usize,
}

impl<A: Agent> OutputValidationMiddleware<A> {
    /// Create a new output validation middleware.
    pub fn new(agent: A) -> Self {
        Self {
            inner: agent,
            schema_validator: None,
            redactor: None,
            max_size: 100_000,
        }
    }

    /// Add schema validation.
    pub fn with_schema_validator(mut self, validator: SchemaValidator) -> Self {
        self.schema_validator = Some(validator);
        self
    }

    /// Add sensitive data redaction.
    pub fn with_redactor(mut self) -> Self {
        self.redactor = Some(SensitiveDataRedactor::new());
        self
    }

    /// Set maximum output size.
    pub fn with_max_size(mut self, size: usize) -> Self {
        self.max_size = size;
        self
    }
}

#[async_trait]
impl<A: Agent> Agent for OutputValidationMiddleware<A> {
    fn name(&self) -> &str {
        self.inner.name()
    }

    fn capabilities(&self) -> Vec<String> {
        self.inner.capabilities()
    }

    fn introspect(&self) -> IntrospectionResult {
        let mut result = self.inner.introspect();
        result.metadata.insert(
            "middleware".to_string(),
            serde_json::json!("output_validation"),
        );
        result
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let mut response = self.inner.process(message).await?;

        // Check size
        let content_str = response.content_as_str().unwrap_or("");
        if content_str.len() > self.max_size {
            return Err(AgentError::ProcessingError(format!(
                "Output too large: {} chars (max: {})",
                content_str.len(),
                self.max_size
            )));
        }

        // Schema validation
        if let Some(validator) = &self.schema_validator {
            if let Ok(json_value) = serde_json::from_str::<Value>(content_str) {
                let (is_valid, error) = validator.validate(&json_value);
                if !is_valid {
                    eprintln!("Schema validation warning: {}", error.unwrap_or_default());
                }
            }
        }

        // Redaction
        if let Some(redactor) = &self.redactor {
            // Try to parse as JSON and redact
            if let Ok(json_value) = serde_json::from_str::<Value>(content_str) {
                let redacted = redactor.redact_json(&json_value);
                response = Message::new("assistant", serde_json::json!(redacted));
            } else {
                // Redact as text
                let redacted_text = redactor.redact_text(content_str);
                response = Message::with_text("assistant", redacted_text);
            }
        }

        Ok(response)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sensitive_data_redactor_text() {
        let redactor = SensitiveDataRedactor::new();

        // API key
        let text = "My API key is sk-1234567890abcdefghijklmnopqrstuvwxyz";
        let redacted = redactor.redact_text(text);
        assert!(redacted.contains("***REDACTED***"));
        assert!(!redacted.contains("sk-1234567890"));

        // Email
        let text = "Contact me at user@example.com";
        let redacted = redactor.redact_text(text);
        assert!(redacted.contains("***REDACTED***"));
        assert!(!redacted.contains("user@example.com"));
    }

    #[test]
    fn test_schema_validator() {
        let mut config = SchemaValidatorConfig::default();
        config
            .expected_fields
            .insert("name".to_string(), "string".to_string());
        config
            .expected_fields
            .insert("age".to_string(), "number".to_string());
        config.required_fields.insert("name".to_string());

        let validator = SchemaValidator::new(config);

        // Valid
        let valid_json = serde_json::json!({"name": "Alice", "age": 30});
        let (is_valid, _) = validator.validate(&valid_json);
        assert!(is_valid);

        // Missing required field
        let invalid_json = serde_json::json!({"age": 30});
        let (is_valid, error) = validator.validate(&invalid_json);
        assert!(!is_valid);
        assert!(error.unwrap().contains("Missing required field"));
    }
}
