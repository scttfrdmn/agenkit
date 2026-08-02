//! Integration tests for cross-language compatibility
//!
//! Tests message serialization compatibility, HTTP transport interoperability,
//! protocol adherence, and JSON schema validation across languages.

#[cfg(feature = "native")]
mod cross_language_tests {
    use agenkit::core::Message;
    use serde_json::json;
    

    /// Test 1: Message JSON schema compatibility
    #[test]
    fn test_message_json_schema_compatibility() {
        let msg = Message::with_text("user", "Hello from Rust");
        let json_msg = serde_json::to_value(&msg).expect("Serialization failed");

        // Verify JSON structure matches cross-language schema
        assert!(json_msg.get("role").is_some());
        assert!(json_msg.get("content").is_some());
        assert!(json_msg.get("metadata").is_some());
        assert!(json_msg.get("timestamp").is_some());

        // Verify types
        assert!(json_msg.get("role").unwrap().is_string());
        assert!(json_msg.get("content").is_some());
        assert!(json_msg.get("metadata").unwrap().is_object());
        assert!(json_msg.get("timestamp").unwrap().is_string());
    }

    /// Test 2: Role field standardization
    #[test]
    fn test_role_field_standardization() {
        let standard_roles = vec!["user", "assistant", "system", "tool"];

        for role in standard_roles {
            let msg = Message::with_text(role, "Test");
            assert_eq!(msg.role, role);

            let json = serde_json::to_value(&msg).unwrap();
            assert_eq!(json.get("role").unwrap().as_str().unwrap(), role);
        }
    }

    /// Test 3: Metadata type compatibility
    ///
    /// The 3.14 below is a shared test vector, not an approximation of pi. C++'s
    /// `CoreIntegrationTest.MessageCreationAndSerialization`
    /// (agenkit-cpp/tests/integration/test_core.cpp) builds the same
    /// `string_key`/`float_key`/`bool_key`/`null_key` metadata map, so taking
    /// clippy's `std::f64::consts::PI` suggestion would widen a cross-language
    /// divergence to satisfy a lint.
    #[allow(clippy::approx_constant)]
    #[test]
    fn test_metadata_type_compatibility() {
        let msg = Message::with_text("user", "Test")
            .with_metadata("string_key", json!("string_value"))
            .with_metadata("number_key", json!(42))
            .with_metadata("float_key", json!(3.14))
            .with_metadata("bool_key", json!(true))
            .with_metadata("null_key", json!(null))
            .with_metadata("array_key", json!([1, 2, 3]))
            .with_metadata("object_key", json!({"nested": "value"}));

        let json = serde_json::to_value(&msg).unwrap();
        let metadata = json.get("metadata").unwrap().as_object().unwrap();

        // Verify all types are serializable
        assert_eq!(
            metadata.get("string_key").unwrap().as_str().unwrap(),
            "string_value"
        );
        assert_eq!(metadata.get("number_key").unwrap().as_i64().unwrap(), 42);
        assert!((metadata.get("float_key").unwrap().as_f64().unwrap() - 3.14).abs() < 0.01);
        assert!(metadata.get("bool_key").unwrap().as_bool().unwrap());
        assert!(metadata.get("null_key").unwrap().is_null());
        assert_eq!(
            metadata.get("array_key").unwrap().as_array().unwrap().len(),
            3
        );
        assert!(metadata.get("object_key").unwrap().is_object());
    }

    /// Test 4: Message deserialization from external JSON
    #[test]
    fn test_message_deserialization_from_external_json() {
        // Simulate JSON from another language implementation
        let external_json = json!({
            "role": "assistant",
            "content": "Response from external service",
            "metadata": {
                "source": "python",
                "request_id": "external-123"
            },
            "timestamp": "2024-01-15T10:30:00Z"
        });

        let msg: Message = serde_json::from_value(external_json).expect("Deserialization failed");

        assert_eq!(msg.role, "assistant");
        assert_eq!(
            msg.content_as_str().unwrap(),
            "Response from external service"
        );
        assert_eq!(
            msg.metadata.get("source").unwrap().as_str().unwrap(),
            "python"
        );
        assert_eq!(
            msg.metadata.get("request_id").unwrap().as_str().unwrap(),
            "external-123"
        );
    }

    /// Test 5: Timestamp format compatibility
    #[test]
    fn test_timestamp_format_compatibility() {
        let msg = Message::with_text("user", "Test");
        let json = serde_json::to_value(&msg).unwrap();

        let timestamp_str = json.get("timestamp").unwrap().as_str().unwrap();

        // Timestamp should be RFC3339 format (compatible with ISO 8601)
        assert!(timestamp_str.contains('T'));
        assert!(
            timestamp_str.contains('Z')
                || timestamp_str.contains('+')
                || timestamp_str.contains('-')
        );

        // Should be parseable as chrono DateTime
        let parsed = chrono::DateTime::parse_from_rfc3339(timestamp_str);
        assert!(parsed.is_ok());
    }

    /// Test 6: Content null handling
    #[test]
    fn test_content_null_handling() {
        // Test with string content
        let msg1 = Message::with_text("user", "test");
        assert_eq!(msg1.content_as_str().unwrap(), "test");

        // Test with JSON object content
        let msg2 = Message::new("user", json!({"key": "value"}));
        assert!(msg2.content.is_object());

        // Serialization should preserve content
        let json1 = serde_json::to_value(&msg1).unwrap();
        let json2 = serde_json::to_value(&msg2).unwrap();

        assert!(json1.get("content").is_some());
        assert!(json2.get("content").is_some());
    }

    /// Test 7: Nested metadata depth support
    #[test]
    fn test_nested_metadata_depth_support() {
        let deep_metadata = json!({
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "value": "deep value"
                        }
                    }
                }
            }
        });

        let msg = Message::with_text("user", "Test").with_metadata("deep", deep_metadata);

        let json = serde_json::to_value(&msg).unwrap();
        let found = json
            .get("metadata")
            .unwrap()
            .get("deep")
            .unwrap()
            .get("level1")
            .unwrap()
            .get("level2")
            .unwrap()
            .get("level3")
            .unwrap()
            .get("level4")
            .unwrap()
            .get("value")
            .unwrap()
            .as_str()
            .unwrap();

        assert_eq!(found, "deep value");
    }

    /// Test 8: Unicode handling across languages
    #[test]
    fn test_unicode_handling() {
        let unicode_content = "Test: English, 中文, العربية, Русский, עברית, 🌍🚀";

        let msg = Message::with_text("user", unicode_content);
        let json_str = serde_json::to_string(&msg).expect("Serialization failed");

        // Should successfully serialize and deserialize
        let deserialized: Message =
            serde_json::from_str(&json_str).expect("Deserialization failed");

        assert_eq!(deserialized.content_as_str().unwrap(), unicode_content);
    }

    /// Test 9: Large metadata payload handling
    #[test]
    fn test_large_metadata_payload() {
        let mut metadata = serde_json::Map::new();

        // Create a large metadata object with many fields
        for i in 0..100 {
            metadata.insert(format!("field_{}", i), json!(format!("value_{}", i)));
        }

        let msg = Message::with_text("user", "Test")
            .with_metadata("large_payload", serde_json::Value::Object(metadata));

        // Should serialize without issues
        let json_str = serde_json::to_string(&msg).expect("Serialization failed");
        assert!(!json_str.is_empty());

        // Should deserialize correctly
        let deserialized: Message =
            serde_json::from_str(&json_str).expect("Deserialization failed");
        assert!(!deserialized.metadata.is_empty());
    }

    /// Test 10: Empty metadata handling
    #[test]
    fn test_empty_metadata_handling() {
        let msg = Message::with_text("user", "Test");
        let json = serde_json::to_value(&msg).unwrap();

        // Metadata field should exist, even if empty
        assert!(json.get("metadata").is_some());
        let metadata = json.get("metadata").unwrap().as_object().unwrap();
        assert!(metadata.is_empty());
    }

    /// Test 11: Message round-trip serialization
    #[test]
    fn test_message_round_trip_serialization() {
        let original = Message::with_text("user", "Round trip test")
            .with_metadata("test_id", json!("rt-001"))
            .with_metadata("nested", json!({"key": "value"}));

        // Serialize
        let json_str = serde_json::to_string(&original).expect("Serialization failed");

        // Deserialize
        let deserialized: Message =
            serde_json::from_str(&json_str).expect("Deserialization failed");

        // Verify round-trip
        assert_eq!(deserialized.role, original.role);
        assert_eq!(
            deserialized.content_as_str().unwrap(),
            original.content_as_str().unwrap()
        );
        assert_eq!(
            deserialized.metadata.get("test_id"),
            original.metadata.get("test_id")
        );
        assert_eq!(
            deserialized.metadata.get("nested"),
            original.metadata.get("nested")
        );
    }

    /// Test 12: Cross-language field name preservation
    #[test]
    fn test_cross_language_field_name_preservation() {
        // Test that snake_case field names are handled correctly
        let msg = Message::with_text("user", "Test")
            .with_metadata("user_id", json!(123))
            .with_metadata("request_id", json!("req-456"))
            .with_metadata("trace_id", json!("trace-789"));

        let json = serde_json::to_value(&msg).unwrap();
        let metadata = json.get("metadata").unwrap().as_object().unwrap();

        // All field names should be preserved
        assert!(metadata.contains_key("user_id"));
        assert!(metadata.contains_key("request_id"));
        assert!(metadata.contains_key("trace_id"));
    }

    /// Test 13: HTTP transport format compatibility
    #[test]
    fn test_http_transport_format_compatibility() {
        let msg = Message::with_text("user", "HTTP test")
            .with_metadata("source", json!("http_transport"));

        // Simulate HTTP transport
        let json_body = serde_json::to_string(&msg).expect("Serialization failed");

        // Headers would include Content-Type: application/json
        assert!(json_body.contains("\"role\""));
        assert!(json_body.contains("\"content\""));
        assert!(json_body.contains("\"metadata\""));

        // Simulate receiving from HTTP
        let received: Message =
            serde_json::from_str(&json_body).expect("HTTP deserialization failed");

        assert_eq!(received.role, "user");
        assert_eq!(
            received.metadata.get("source").unwrap().as_str().unwrap(),
            "http_transport"
        );
    }

    /// Test 14: Protocol version compatibility
    #[test]
    fn test_protocol_version_compatibility() {
        // Messages should have consistent structure across versions
        let msg = Message::with_text("user", "Version test");
        let json = serde_json::to_value(&msg).unwrap();

        // Required fields for protocol compatibility
        assert!(json.get("role").is_some(), "Missing required 'role' field");
        assert!(
            json.get("content").is_some(),
            "Missing required 'content' field"
        );
        assert!(
            json.get("timestamp").is_some(),
            "Missing required 'timestamp' field"
        );
        assert!(
            json.get("metadata").is_some(),
            "Missing required 'metadata' field"
        );

        // Fields should have correct types
        assert!(
            json.get("role").unwrap().is_string(),
            "'role' should be string"
        );
        assert!(
            json.get("timestamp").unwrap().is_string(),
            "'timestamp' should be string"
        );
        assert!(
            json.get("metadata").unwrap().is_object(),
            "'metadata' should be object"
        );
    }
}

// Placeholder for non-native builds
#[cfg(not(feature = "native"))]
mod placeholder {
    #[test]
    fn test_cross_language_requires_native() {
        println!("Cross-language tests require 'native' feature");
    }
}
