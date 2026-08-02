///! Cross-language message serialization tests for Rust.
///!
///! Validates that Agenkit messages serialize/deserialize consistently
///! with the canonical JSON schema across all language implementations.
use agenkit::core::Message;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

/// Test fixtures loaded from shared JSON file
#[derive(Debug, serde::Deserialize)]
struct MessageFixtures {
    version: String,
    description: String,
    test_cases: Vec<MessageTestCase>,
}

#[derive(Debug, serde::Deserialize)]
struct MessageTestCase {
    id: String,
    name: String,
    message: MessageData,
    validation: serde_json::Value,
}

#[derive(Debug, serde::Deserialize, serde::Serialize)]
struct MessageData {
    role: String,
    content: serde_json::Value,
    #[serde(default)]
    metadata: HashMap<String, serde_json::Value>,
    #[serde(default)]
    timestamp: Option<String>,
}

fn load_fixtures() -> MessageFixtures {
    let fixtures_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .join("tests/cross_language/fixtures/messages.json");

    let content = fs::read_to_string(&fixtures_path)
        .unwrap_or_else(|e| panic!("Failed to load fixtures from {:?}: {}", fixtures_path, e));

    serde_json::from_str(&content).unwrap_or_else(|e| panic!("Failed to parse fixtures: {}", e))
}

fn load_schema() -> Value {
    let schema_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .join("tests/cross_language/schemas/message.schema.json");

    let content = fs::read_to_string(&schema_path)
        .unwrap_or_else(|e| panic!("Failed to load schema from {:?}: {}", schema_path, e));

    serde_json::from_str(&content).unwrap_or_else(|e| panic!("Failed to parse schema: {}", e))
}

fn validate_against_schema(message_json: &Value, _schema: &Value) {
    // Basic validation against schema structure
    // Note: Full jsonschema validation requires the jsonschema crate
    // For now, we do basic structural validation

    assert!(message_json.is_object(), "Message must be an object");
    let obj = message_json.as_object().unwrap();

    // Check required fields
    assert!(obj.contains_key("role"), "Message must have 'role' field");
    assert!(
        obj.contains_key("content"),
        "Message must have 'content' field"
    );

    // Validate role is valid enum value
    let role = obj.get("role").unwrap().as_str().unwrap();
    let valid_roles = ["user", "assistant", "system", "tool", "agent"];
    assert!(
        valid_roles.contains(&role),
        "Invalid role: {}. Must be one of: {:?}",
        role,
        valid_roles
    );

    // Validate content is string or object
    let content = obj.get("content").unwrap();
    assert!(
        content.is_string() || content.is_object(),
        "Content must be string or object"
    );

    // Validate metadata if present
    if let Some(metadata) = obj.get("metadata") {
        assert!(metadata.is_object(), "Metadata must be an object");
    }
}

fn message_to_json(msg: &Message) -> Value {
    serde_json::to_value(msg).expect("Failed to serialize message")
}

#[test]
fn test_fixtures_load() {
    let fixtures = load_fixtures();
    assert_eq!(fixtures.version, "1.0");
    assert!(!fixtures.test_cases.is_empty());
}

#[test]
fn test_schema_validates_fixtures() {
    let fixtures = load_fixtures();
    let schema = load_schema();

    for test_case in &fixtures.test_cases {
        let message_json = serde_json::to_value(&test_case.message)
            .expect(&format!("Failed to serialize test case: {}", test_case.id));

        validate_against_schema(&message_json, &schema);
    }
}

#[test]
fn test_simple_user_message() {
    let fixtures = load_fixtures();
    let schema = load_schema();

    let test_case = fixtures
        .test_cases
        .iter()
        .find(|tc| tc.id == "simple_user_message")
        .expect("Test case not found");

    // Create message from fixture
    let msg = Message::new(
        test_case.message.role.clone(),
        test_case.message.content.clone(),
    );

    // Validate properties
    assert_eq!(msg.role, "user");
    assert_eq!(msg.content.as_str(), Some("Hello, agent!"));

    // Serialize and validate
    let serialized = message_to_json(&msg);
    validate_against_schema(&serialized, &schema);

    // Verify key properties match
    assert_eq!(serialized["role"], test_case.message.role);
    assert_eq!(serialized["content"], test_case.message.content);
}

#[test]
fn test_assistant_message_with_metadata() {
    let fixtures = load_fixtures();
    let schema = load_schema();

    let test_case = fixtures
        .test_cases
        .iter()
        .find(|tc| tc.id == "assistant_message_with_metadata")
        .expect("Test case not found");

    // Create message with metadata
    let mut msg = Message::new(
        test_case.message.role.clone(),
        test_case.message.content.clone(),
    );
    msg.metadata = test_case.message.metadata.clone();

    // Validate
    assert_eq!(msg.role, "assistant");
    assert_eq!(msg.content.as_str(), Some("I can help you with that!"));
    assert_eq!(msg.metadata.len(), 3);
    assert!(msg.metadata.contains_key("model"));
    assert!(msg.metadata.contains_key("temperature"));
    assert!(msg.metadata.contains_key("tokens"));

    // Serialize and validate
    let serialized = message_to_json(&msg);
    validate_against_schema(&serialized, &schema);
}

#[test]
fn test_system_message() {
    let fixtures = load_fixtures();
    let schema = load_schema();

    let test_case = fixtures
        .test_cases
        .iter()
        .find(|tc| tc.id == "system_message")
        .expect("Test case not found");

    let msg = Message::new(
        test_case.message.role.clone(),
        test_case.message.content.clone(),
    );

    assert_eq!(msg.role, "system");
    assert!(msg.content.as_str().unwrap().contains("helpful assistant"));

    let serialized = message_to_json(&msg);
    validate_against_schema(&serialized, &schema);
}

#[test]
fn test_tool_message_structured() {
    let fixtures = load_fixtures();
    let schema = load_schema();

    let test_case = fixtures
        .test_cases
        .iter()
        .find(|tc| tc.id == "tool_message_structured")
        .expect("Test case not found");

    // Structured content (already a JSON object)
    let mut msg = Message::new(
        test_case.message.role.clone(),
        test_case.message.content.clone(),
    );
    msg.metadata = test_case.message.metadata.clone();

    // Validate structured content
    assert_eq!(msg.role, "tool");
    assert!(msg.content.is_object());

    let content_obj = msg.content.as_object().unwrap();
    assert_eq!(content_obj.get("tool_name").unwrap(), "calculator");
    assert_eq!(content_obj.get("result").unwrap(), 5);
    assert_eq!(content_obj.get("success").unwrap(), true);

    // Serialize and validate
    let serialized = message_to_json(&msg);
    validate_against_schema(&serialized, &schema);
}

#[test]
fn test_agent_message() {
    let fixtures = load_fixtures();
    let schema = load_schema();

    let test_case = fixtures
        .test_cases
        .iter()
        .find(|tc| tc.id == "agent_message")
        .expect("Test case not found");

    let mut msg = Message::new(
        test_case.message.role.clone(),
        test_case.message.content.clone(),
    );
    msg.metadata = test_case.message.metadata.clone();

    assert_eq!(msg.role, "agent");
    assert!(msg.content.as_str().unwrap().contains("reasoning steps"));
    assert_eq!(msg.metadata.get("technique").unwrap(), "chain_of_thought");

    let serialized = message_to_json(&msg);
    validate_against_schema(&serialized, &schema);
}

#[test]
fn test_empty_content() {
    let fixtures = load_fixtures();
    let schema = load_schema();

    let test_case = fixtures
        .test_cases
        .iter()
        .find(|tc| tc.id == "empty_content")
        .expect("Test case not found");

    let msg = Message::new(
        test_case.message.role.clone(),
        test_case.message.content.clone(),
    );

    assert_eq!(msg.role, "assistant");
    assert_eq!(msg.content.as_str(), Some(""));

    let serialized = message_to_json(&msg);
    validate_against_schema(&serialized, &schema);
}

#[test]
fn test_large_content() {
    let fixtures = load_fixtures();
    let schema = load_schema();

    let test_case = fixtures
        .test_cases
        .iter()
        .find(|tc| tc.id == "large_content")
        .expect("Test case not found");

    let mut msg = Message::new(
        test_case.message.role.clone(),
        test_case.message.content.clone(),
    );
    msg.metadata = test_case.message.metadata.clone();

    let validation = test_case.validation.as_object().unwrap();
    let min_length = validation
        .get("min_content_length")
        .unwrap()
        .as_u64()
        .unwrap();

    let content_str = msg.content.as_str().unwrap();
    assert!(content_str.len() >= min_length as usize);
    assert!(content_str.contains("Lorem ipsum"));

    let serialized = message_to_json(&msg);
    validate_against_schema(&serialized, &schema);
}

#[test]
fn test_unicode_content() {
    let fixtures = load_fixtures();
    let schema = load_schema();

    let test_case = fixtures
        .test_cases
        .iter()
        .find(|tc| tc.id == "unicode_content")
        .expect("Test case not found");

    let mut msg = Message::new(
        test_case.message.role.clone(),
        test_case.message.content.clone(),
    );
    msg.metadata = test_case.message.metadata.clone();

    // Verify Unicode characters preserved
    let content_str = msg.content.as_str().unwrap();
    assert!(content_str.contains("世界"));
    assert!(content_str.contains("🌍"));
    assert!(content_str.contains("мир"));

    let serialized = message_to_json(&msg);
    validate_against_schema(&serialized, &schema);
}

#[test]
fn test_nested_metadata() {
    let fixtures = load_fixtures();
    let schema = load_schema();

    let test_case = fixtures
        .test_cases
        .iter()
        .find(|tc| tc.id == "nested_metadata")
        .expect("Test case not found");

    let mut msg = Message::new(
        test_case.message.role.clone(),
        test_case.message.content.clone(),
    );
    msg.metadata = test_case.message.metadata.clone();

    // Verify nested structure
    assert!(msg.metadata.contains_key("analysis"));
    let analysis = msg.metadata.get("analysis").unwrap().as_object().unwrap();
    assert_eq!(analysis.get("sentiment").unwrap(), "positive");

    assert!(msg.metadata.contains_key("processing"));
    assert!(msg.metadata.get("processing").unwrap().is_object());

    assert!(msg.metadata.contains_key("tags"));
    assert!(msg.metadata.get("tags").unwrap().is_array());

    let serialized = message_to_json(&msg);
    validate_against_schema(&serialized, &schema);
}

// 3.14159 is the literal `score` value in
// tests/cross_language/fixtures/messages.json, which Python, TypeScript, C++,
// and Zig all assert against too. Substituting `std::f64::consts::PI` as clippy
// suggests would change the expected value and desynchronise this core from the
// shared fixture — the number is a fixture constant that happens to look like
// pi, not an approximation of it.
#[allow(clippy::approx_constant)]
#[test]
fn test_numeric_metadata() {
    let fixtures = load_fixtures();
    let schema = load_schema();

    let test_case = fixtures
        .test_cases
        .iter()
        .find(|tc| tc.id == "numeric_metadata")
        .expect("Test case not found");

    let mut msg = Message::new(
        test_case.message.role.clone(),
        test_case.message.content.clone(),
    );
    msg.metadata = test_case.message.metadata.clone();

    // Verify numeric types preserved
    assert_eq!(msg.metadata.get("count").unwrap().as_i64(), Some(42));
    assert!((msg.metadata.get("score").unwrap().as_f64().unwrap() - 3.14159).abs() < 0.0001);
    assert_eq!(msg.metadata.get("is_final").unwrap().as_bool(), Some(true));
    assert!(msg.metadata.get("optional_value").unwrap().is_null());

    let serialized = message_to_json(&msg);
    validate_against_schema(&serialized, &schema);
}

#[test]
fn test_all_fixtures_roundtrip() {
    let fixtures = load_fixtures();
    let schema = load_schema();

    for test_case in &fixtures.test_cases {
        // Create message
        let mut msg = Message::new(
            test_case.message.role.clone(),
            test_case.message.content.clone(),
        );
        msg.metadata = test_case.message.metadata.clone();

        // Serialize
        let serialized = message_to_json(&msg);

        // Validate against schema
        validate_against_schema(&serialized, &schema);

        // Verify core properties match
        assert_eq!(serialized["role"].as_str().unwrap(), test_case.message.role);
        assert!(serialized.get("content").is_some());
    }
}
