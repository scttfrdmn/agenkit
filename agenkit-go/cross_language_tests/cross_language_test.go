package tests

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/xeipuuv/gojsonschema"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// MessageFixtures represents the structure of messages.json
type MessageFixtures struct {
	Version   string        `json:"version"`
	TestCases []MessageTest `json:"test_cases"`
}

// MessageTest represents a single test case
type MessageTest struct {
	ID         string                 `json:"id"`
	Name       string                 `json:"name"`
	Message    map[string]interface{} `json:"message"`
	Validation map[string]interface{} `json:"validation"`
}

func loadMessageFixtures(t *testing.T) MessageFixtures {
	// Load from fixtures directory
	fixturesPath := filepath.Join("..", "..", "tests", "cross_language", "fixtures", "messages.json")
	data, err := os.ReadFile(fixturesPath)
	require.NoError(t, err, "Failed to load message fixtures")

	var fixtures MessageFixtures
	err = json.Unmarshal(data, &fixtures)
	require.NoError(t, err, "Failed to parse message fixtures")

	return fixtures
}

func loadMessageSchema(t *testing.T) *gojsonschema.Schema {
	schemaPath := filepath.Join("..", "..", "tests", "cross_language", "schemas", "message.schema.json")
	schemaLoader := gojsonschema.NewReferenceLoader("file://" + schemaPath)

	schema, err := gojsonschema.NewSchema(schemaLoader)
	require.NoError(t, err, "Failed to load message schema")

	return schema
}

func validateAgainstSchema(t *testing.T, schema *gojsonschema.Schema, data map[string]interface{}) {
	documentLoader := gojsonschema.NewGoLoader(data)
	result, err := schema.Validate(documentLoader)
	require.NoError(t, err, "Schema validation error")

	if !result.Valid() {
		t.Errorf("Schema validation failed:")
		for _, desc := range result.Errors() {
			t.Errorf("- %s", desc)
		}
	}
}

func messageToMap(msg *agenkit.Message) map[string]interface{} {
	result := map[string]interface{}{
		"role":    msg.Role,
		"content": msg.ContentString(),
	}

	if len(msg.Metadata) > 0 {
		result["metadata"] = msg.Metadata
	}

	if !msg.Timestamp.IsZero() {
		result["timestamp"] = msg.Timestamp.Format("2006-01-02T15:04:05Z07:00")
	}

	return result
}

func TestMessageFixturesLoad(t *testing.T) {
	fixtures := loadMessageFixtures(t)

	assert.Equal(t, "1.0", fixtures.Version)
	assert.Greater(t, len(fixtures.TestCases), 0)
}

func TestSchemaValidatesFixtures(t *testing.T) {
	fixtures := loadMessageFixtures(t)
	schema := loadMessageSchema(t)

	for _, testCase := range fixtures.TestCases {
		t.Run(testCase.ID, func(t *testing.T) {
			validateAgainstSchema(t, schema, testCase.Message)
		})
	}
}

func TestSimpleUserMessage(t *testing.T) {
	fixtures := loadMessageFixtures(t)
	schema := loadMessageSchema(t)

	// Find test case
	var testCase MessageTest
	for _, tc := range fixtures.TestCases {
		if tc.ID == "simple_user_message" {
			testCase = tc
			break
		}
	}
	require.NotEmpty(t, testCase.ID, "Test case not found")

	// Create message from fixture
	msg := &agenkit.Message{
		Role:     testCase.Message["role"].(string),
		Content:  testCase.Message["content"].(string),
		Metadata: make(map[string]interface{}),
	}

	// Validate properties
	assert.Equal(t, "user", msg.Role)
	assert.Equal(t, "Hello, agent!", msg.ContentString())

	// Serialize back
	serialized := messageToMap(msg)

	// Validate against schema
	validateAgainstSchema(t, schema, serialized)

	// Verify key properties match
	assert.Equal(t, testCase.Message["role"], serialized["role"])
	assert.Equal(t, testCase.Message["content"], serialized["content"])
}

func TestAssistantMessageWithMetadata(t *testing.T) {
	fixtures := loadMessageFixtures(t)
	schema := loadMessageSchema(t)

	var testCase MessageTest
	for _, tc := range fixtures.TestCases {
		if tc.ID == "assistant_message_with_metadata" {
			testCase = tc
			break
		}
	}
	require.NotEmpty(t, testCase.ID)

	// Extract metadata
	metadata := testCase.Message["metadata"].(map[string]interface{})

	msg := &agenkit.Message{
		Role:     testCase.Message["role"].(string),
		Content:  testCase.Message["content"].(string),
		Metadata: metadata,
	}

	// Validate
	assert.Equal(t, "assistant", msg.Role)
	assert.Equal(t, "I can help you with that!", msg.ContentString())
	assert.Equal(t, 3, len(msg.Metadata))
	assert.Contains(t, msg.Metadata, "model")
	assert.Contains(t, msg.Metadata, "temperature")
	assert.Contains(t, msg.Metadata, "tokens")

	// Serialize and validate
	serialized := messageToMap(msg)
	validateAgainstSchema(t, schema, serialized)
}

func TestToolMessageStructured(t *testing.T) {
	fixtures := loadMessageFixtures(t)
	schema := loadMessageSchema(t)

	var testCase MessageTest
	for _, tc := range fixtures.TestCases {
		if tc.ID == "tool_message_structured" {
			testCase = tc
			break
		}
	}
	require.NotEmpty(t, testCase.ID)

	// Content is structured (map) - in Go, need to JSON-encode it
	content := testCase.Message["content"].(map[string]interface{})
	contentJSON, err := json.Marshal(content)
	require.NoError(t, err)

	metadata := testCase.Message["metadata"].(map[string]interface{})

	msg := &agenkit.Message{
		Role:     testCase.Message["role"].(string),
		Content:  string(contentJSON), // JSON-encoded structured content
		Metadata: metadata,
	}

	// Validate
	assert.Equal(t, "tool", msg.Role)

	// Parse content back for validation
	var contentMap map[string]interface{}
	err = json.Unmarshal([]byte(msg.ContentString()), &contentMap)
	require.NoError(t, err)
	assert.Equal(t, "calculator", contentMap["tool_name"])
	assert.Equal(t, float64(5), contentMap["result"])
	assert.Equal(t, true, contentMap["success"])

	// Serialize (needs to parse JSON content for schema validation)
	serialized := map[string]interface{}{
		"role":     msg.Role,
		"content":  contentMap, // Use parsed map for schema validation
		"metadata": msg.Metadata,
	}
	validateAgainstSchema(t, schema, serialized)
}

func TestUnicodeContent(t *testing.T) {
	fixtures := loadMessageFixtures(t)
	schema := loadMessageSchema(t)

	var testCase MessageTest
	for _, tc := range fixtures.TestCases {
		if tc.ID == "unicode_content" {
			testCase = tc
			break
		}
	}
	require.NotEmpty(t, testCase.ID)

	msg := &agenkit.Message{
		Role:     testCase.Message["role"].(string),
		Content:  testCase.Message["content"].(string),
		Metadata: testCase.Message["metadata"].(map[string]interface{}),
	}

	// Verify Unicode characters preserved
	assert.Contains(t, msg.ContentString(), "世界")
	assert.Contains(t, msg.ContentString(), "🌍")
	assert.Contains(t, msg.ContentString(), "мир")

	// Serialize and validate
	serialized := messageToMap(msg)
	validateAgainstSchema(t, schema, serialized)
}

func TestNestedMetadata(t *testing.T) {
	fixtures := loadMessageFixtures(t)
	schema := loadMessageSchema(t)

	var testCase MessageTest
	for _, tc := range fixtures.TestCases {
		if tc.ID == "nested_metadata" {
			testCase = tc
			break
		}
	}
	require.NotEmpty(t, testCase.ID)

	msg := &agenkit.Message{
		Role:     testCase.Message["role"].(string),
		Content:  testCase.Message["content"].(string),
		Metadata: testCase.Message["metadata"].(map[string]interface{}),
	}

	// Verify nested structure
	assert.Contains(t, msg.Metadata, "analysis")
	analysis := msg.Metadata["analysis"].(map[string]interface{})
	assert.Equal(t, "positive", analysis["sentiment"])

	assert.Contains(t, msg.Metadata, "processing")
	assert.Contains(t, msg.Metadata, "tags")

	// Serialize and validate
	serialized := messageToMap(msg)
	validateAgainstSchema(t, schema, serialized)
}

func TestAllFixturesRoundtrip(t *testing.T) {
	fixtures := loadMessageFixtures(t)
	schema := loadMessageSchema(t)

	for _, testCase := range fixtures.TestCases {
		t.Run(testCase.ID, func(t *testing.T) {
			// Handle content - string or structured
			var content string
			switch v := testCase.Message["content"].(type) {
			case string:
				content = v
			case map[string]interface{}:
				// JSON-encode structured content
				contentJSON, err := json.Marshal(v)
				require.NoError(t, err)
				content = string(contentJSON)
			default:
				t.Fatalf("Unexpected content type: %T", v)
			}

			// Create message
			msg := &agenkit.Message{
				Role:    testCase.Message["role"].(string),
				Content: content,
			}

			if metadata, ok := testCase.Message["metadata"].(map[string]interface{}); ok {
				msg.Metadata = metadata
			} else {
				msg.Metadata = make(map[string]interface{})
			}

			// Serialize
			serialized := messageToMap(msg)

			// Validate against schema
			validateAgainstSchema(t, schema, serialized)

			// Verify core properties match
			assert.Equal(t, testCase.Message["role"], serialized["role"])
		})
	}
}
