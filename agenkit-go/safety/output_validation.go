package safety

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"reflect"
	"regexp"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// OutputValidationError is raised when output validation fails.
type OutputValidationError struct {
	Message string
	Details map[string]interface{}
}

// Error returns the error message.
func (e *OutputValidationError) Error() string {
	return e.Message
}

// SchemaValidator validates output against expected schema.
//
// Supports basic type checking and structure validation.
//
// Example:
//
//	validator := NewSchemaValidator(
//	    map[string]string{"result": "string", "count": "int"},
//	    []string{"result"},
//	    true,
//	)
//	isValid, err := validator.Validate(output)
type SchemaValidator struct {
	// Expected fields and their types
	expectedFields map[string]string

	// Required fields (subset of expected_fields)
	requiredFields map[string]bool

	// Allow additional fields not in schema
	allowAdditional bool
}

// NewSchemaValidator creates a new schema validator.
//
// Args:
//
//	expectedFields: Map of field names to type names (e.g., "string", "int", "bool")
//	requiredFields: List of required field names
//	allowAdditional: Allow additional fields not in schema
//
// Example:
//
//	validator := NewSchemaValidator(
//	    map[string]string{"name": "string", "age": "int"},
//	    []string{"name"},
//	    true,
//	)
func NewSchemaValidator(expectedFields map[string]string, requiredFields []string, allowAdditional bool) *SchemaValidator {
	requiredMap := make(map[string]bool)
	for _, field := range requiredFields {
		requiredMap[field] = true
	}

	return &SchemaValidator{
		expectedFields:  expectedFields,
		requiredFields:  requiredMap,
		allowAdditional: allowAdditional,
	}
}

// Validate validates output against schema.
//
// Args:
//
//	output: Output to validate
//
// Returns:
//
//	isValid: true if output is valid
//	errorMessage: Error message if invalid (nil if valid)
func (v *SchemaValidator) Validate(output interface{}) (bool, *string) {
	// If no schema specified, always valid
	if len(v.expectedFields) == 0 {
		return true, nil
	}

	// Check if output is dict-like
	outputMap, ok := output.(map[string]interface{})
	if !ok {
		// Try to parse as JSON if string
		if outputStr, ok := output.(string); ok {
			if err := json.Unmarshal([]byte(outputStr), &outputMap); err != nil {
				msg := "Output is not valid JSON or dict"
				return false, &msg
			}
		} else {
			msg := "Output must be a dictionary or JSON string"
			return false, &msg
		}
	}

	// Check required fields
	for field := range v.requiredFields {
		if _, ok := outputMap[field]; !ok {
			msg := fmt.Sprintf("Missing required field: %s", field)
			return false, &msg
		}
	}

	// Check field types
	for fieldName, expectedType := range v.expectedFields {
		if value, ok := outputMap[fieldName]; ok {
			actualType := getTypeName(value)
			if actualType != expectedType {
				msg := fmt.Sprintf("Field '%s' has wrong type: expected %s, got %s",
					fieldName, expectedType, actualType)
				return false, &msg
			}
		}
	}

	// Check for additional fields
	if !v.allowAdditional {
		for key := range outputMap {
			if _, ok := v.expectedFields[key]; !ok {
				msg := fmt.Sprintf("Unexpected field: %s", key)
				return false, &msg
			}
		}
	}

	return true, nil
}

// getTypeName returns a simple type name for a value.
func getTypeName(value interface{}) string {
	if value == nil {
		return "nil"
	}

	switch value.(type) {
	case string:
		return "string"
	case int, int8, int16, int32, int64:
		return "int"
	case float32, float64:
		return "float"
	case bool:
		return "bool"
	case map[string]interface{}:
		return "dict"
	case []interface{}:
		return "list"
	default:
		return reflect.TypeOf(value).String()
	}
}

// SensitiveDataRedactor redacts sensitive data from outputs.
//
// Detects and redacts:
//   - API keys
//   - Passwords
//   - Tokens
//   - PII (email, phone, SSN, credit cards)
//   - Custom sensitive patterns
//
// Example:
//
//	redactor := NewSensitiveDataRedactor()
//	redacted := redactor.Redact(data)
type SensitiveDataRedactor struct {
	// Sensitive field names (case-insensitive)
	sensitiveFields map[string]bool

	// Patterns for detecting sensitive data
	sensitivePatterns []struct {
		pattern  *regexp.Regexp
		dataType string
	}

	// Redaction placeholder
	redactionText string
}

// NewSensitiveDataRedactor creates a new sensitive data redactor.
//
// Example:
//
//	redactor := NewSensitiveDataRedactor()
func NewSensitiveDataRedactor() *SensitiveDataRedactor {
	sensitiveFields := map[string]bool{
		"password":    true,
		"api_key":     true,
		"apikey":      true,
		"token":       true,
		"secret":      true,
		"auth":        true,
		"credential":  true,
		"private_key": true,
		"access_key":  true,
	}

	// Compile sensitive patterns
	patterns := []struct {
		pattern  string
		dataType string
	}{
		{`sk-[a-zA-Z0-9]{32,}`, "API_KEY"},
		{`[a-zA-Z0-9_-]{32,}`, "API_KEY"},
		{`AKIA[0-9A-Z]{16}`, "AWS_ACCESS_KEY"},
		{`ghp_[a-zA-Z0-9]{36}`, "GITHUB_TOKEN"},
		{`\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b`, "EMAIL"},
		{`\b\d{3}[-.]?\d{3}[-.]?\d{4}\b`, "PHONE"},
		{`\b\d{3}-\d{2}-\d{4}\b`, "SSN"},
		{`\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b`, "CREDIT_CARD"},
		{`eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+`, "JWT"},
	}

	compiledPatterns := make([]struct {
		pattern  *regexp.Regexp
		dataType string
	}, 0, len(patterns))

	for _, p := range patterns {
		re, err := regexp.Compile("(?i)" + p.pattern)
		if err != nil {
			log.Printf("WARNING: Failed to compile pattern %s: %v", p.pattern, err)
			continue
		}
		compiledPatterns = append(compiledPatterns, struct {
			pattern  *regexp.Regexp
			dataType string
		}{re, p.dataType})
	}

	return &SensitiveDataRedactor{
		sensitiveFields:   sensitiveFields,
		sensitivePatterns: compiledPatterns,
		redactionText:     "***REDACTED***",
	}
}

// Redact redacts sensitive data from output.
//
// Args:
//
//	data: Data to redact (can be map, string, slice, or primitive)
//
// Returns:
//
//	Redacted copy of data
func (r *SensitiveDataRedactor) Redact(data interface{}) interface{} {
	switch v := data.(type) {
	case map[string]interface{}:
		return r.redactDict(v)
	case string:
		return r.redactString(v)
	case []interface{}:
		redacted := make([]interface{}, len(v))
		for i, item := range v {
			redacted[i] = r.Redact(item)
		}
		return redacted
	default:
		return data
	}
}

// redactDict redacts sensitive fields in dictionary.
func (r *SensitiveDataRedactor) redactDict(data map[string]interface{}) map[string]interface{} {
	redacted := make(map[string]interface{})

	for key, value := range data {
		// Check if field name is sensitive
		if r.sensitiveFields[strings.ToLower(key)] {
			redacted[key] = r.redactionText
		} else {
			// Recursively redact nested structures
			switch v := value.(type) {
			case map[string]interface{}, []interface{}, string:
				redacted[key] = r.Redact(v)
			default:
				redacted[key] = value
			}
		}
	}

	return redacted
}

// redactString redacts sensitive patterns from string.
func (r *SensitiveDataRedactor) redactString(text string) string {
	redacted := text

	// Apply pattern-based redaction
	for _, p := range r.sensitivePatterns {
		matches := p.pattern.FindAllString(redacted, -1)
		for _, match := range matches {
			// Replace with placeholder + type
			redacted = strings.ReplaceAll(redacted, match, fmt.Sprintf("%s_%s", r.redactionText, p.dataType))
		}
	}

	return redacted
}

// HasSensitiveData checks if data contains sensitive information.
func (r *SensitiveDataRedactor) HasSensitiveData(data interface{}) bool {
	switch v := data.(type) {
	case map[string]interface{}:
		// Check field names
		for key := range v {
			if r.sensitiveFields[strings.ToLower(key)] {
				return true
			}
		}
		// Check values recursively
		for _, value := range v {
			if r.HasSensitiveData(value) {
				return true
			}
		}

	case string:
		// Check patterns
		for _, p := range r.sensitivePatterns {
			if p.pattern.MatchString(v) {
				return true
			}
		}

	case []interface{}:
		for _, item := range v {
			if r.HasSensitiveData(item) {
				return true
			}
		}
	}

	return false
}

// OutputValidationMiddleware provides middleware for output validation and sensitive data redaction.
//
// Features:
//   - Schema validation
//   - Sensitive data redaction
//   - Output size limits
//   - Content policy enforcement
//
// Example:
//
//	middleware := NewOutputValidationMiddleware(
//	    baseAgent,
//	    validator,
//	    redactor,
//	    true,
//	    100000,
//	)
type OutputValidationMiddleware struct {
	agent      agenkit.Agent
	schema     *SchemaValidator
	redactor   *SensitiveDataRedactor
	autoRedact bool
	maxSize    int
}

// NewOutputValidationMiddleware creates a new output validation middleware.
//
// Args:
//
//	agent: Agent to wrap
//	schema: Schema validator (nil = no schema validation)
//	redactor: Sensitive data redactor (nil = default redactor)
//	autoRedact: Automatically redact sensitive data
//	maxSize: Maximum output size (characters)
//
// Example:
//
//	middleware := NewOutputValidationMiddleware(
//	    agent,
//	    NewSchemaValidator(map[string]string{"result": "string"}, nil, true),
//	    NewSensitiveDataRedactor(),
//	    true,
//	    100000,
//	)
func NewOutputValidationMiddleware(
	agent agenkit.Agent,
	schema *SchemaValidator,
	redactor *SensitiveDataRedactor,
	autoRedact bool,
	maxSize int,
) *OutputValidationMiddleware {
	if redactor == nil {
		redactor = NewSensitiveDataRedactor()
	}

	return &OutputValidationMiddleware{
		agent:      agent,
		schema:     schema,
		redactor:   redactor,
		autoRedact: autoRedact,
		maxSize:    maxSize,
	}
}

// Name returns the name of the underlying agent.
func (m *OutputValidationMiddleware) Name() string {
	return m.agent.Name()
}

// Capabilities returns capabilities of the underlying agent.
func (m *OutputValidationMiddleware) Capabilities() []string {
	return m.agent.Capabilities()
}

// Process processes message with output validation.
func (m *OutputValidationMiddleware) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Process with wrapped agent
	response, err := m.agent.Process(ctx, message)
	if err != nil {
		return nil, err
	}

	// 1. Check output size
	contentStr := response.Content
	if len(contentStr) > m.maxSize {
		return nil, &OutputValidationError{
			Message: fmt.Sprintf("Output exceeds maximum size (%d chars)", m.maxSize),
			Details: map[string]interface{}{
				"actual_size": len(contentStr),
			},
		}
	}

	// 2. Validate against schema
	if m.schema != nil {
		isValid, errorMsgPtr := m.schema.Validate(response.Content)
		if !isValid {
			errorMsg := *errorMsgPtr
			contentPreview := contentStr
			if len(contentPreview) > 200 {
				contentPreview = contentPreview[:200]
			}

			return nil, &OutputValidationError{
				Message: fmt.Sprintf("Output validation failed: %s", errorMsg),
				Details: map[string]interface{}{
					"content_preview": contentPreview,
				},
			}
		}
	}

	// 3. Auto-redact sensitive data
	if m.autoRedact {
		redactedContent := m.redactor.Redact(response.Content)

		// Create new Message with redacted content
		response = &agenkit.Message{
			Role:     response.Role,
			Content:  fmt.Sprintf("%v", redactedContent),
			Metadata: response.Metadata,
		}
	}

	// 4. Log if sensitive data detected (even if redacted)
	if m.autoRedact && m.redactor.HasSensitiveData(response.Content) {
		log.Println("WARNING: Output may contain sensitive data (has been redacted)")
	}

	return response, nil
}
