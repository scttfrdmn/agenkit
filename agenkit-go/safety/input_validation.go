// Package safety provides safety mechanisms for agents.
//
// Provides protection against:
//   - Prompt injection attacks
//   - Malicious inputs
//   - Content policy violations
//   - Input size limits
//   - Output validation
//   - Permission checks
//   - Audit logging
//   - Anomaly detection
package safety

import (
	"context"
	"fmt"
	"log"
	"regexp"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ValidationError is raised when input validation fails.
type ValidationError struct {
	Message string
	Details map[string]interface{}
}

// Error returns the error message.
func (e *ValidationError) Error() string {
	return e.Message
}

// PromptInjectionDetector detects potential prompt injection attempts.
//
// Uses pattern matching and heuristics to identify common prompt injection
// techniques like instruction overrides, jailbreaks, and system prompts.
//
// Example:
//
//	detector := NewPromptInjectionDetector(10)
//	isInjection, score, patterns := detector.Detect("Ignore all previous instructions")
//	fmt.Printf("Is injection: %v, Score: %d\n", isInjection, score)
type PromptInjectionDetector struct {
	// Patterns indicating prompt injection attempts
	dangerousPatterns []string

	// Suspicious keywords (weighted scoring)
	suspiciousKeywords map[string]int

	// Score threshold for blocking (0-100)
	threshold int

	// Compiled regex patterns
	compiledPatterns []*regexp.Regexp
}

// NewPromptInjectionDetector creates a new prompt injection detector.
//
// Args:
//
//	threshold: Score threshold for blocking (0-100)
//
// Example:
//
//	detector := NewPromptInjectionDetector(10)
func NewPromptInjectionDetector(threshold int) *PromptInjectionDetector {
	dangerousPatterns := []string{
		`ignore\s+(previous|all|above|prior)\s+instructions?`,
		`disregard\s+(previous|all|above|prior)`,
		`forget\s+(everything|all|previous)`,
		`new\s+instructions?:`,
		`system\s*(prompt|message)?:`,
		`you\s+are\s+now`,
		`act\s+as\s+(if|though)`,
		`pretend\s+(you|to)\s+(are|be)`,
		`roleplay\s+as`,
		`^sudo\s+`,
		`admin\s+mode`,
		`developer\s+mode`,
		`god\s+mode`,
		`jailbreak`,
		`</?\s*system\s*>`,
		`<\|.*?\|>`, // Special tokens
		`\[INST\]`,  // Llama-style tokens
		`\{system\}`,
	}

	suspiciousKeywords := map[string]int{
		"ignore":       3,
		"disregard":    3,
		"override":     2,
		"bypass":       3,
		"jailbreak":    5,
		"prompt":       2,
		"injection":    4,
		"system":       2,
		"admin":        2,
		"root":         2,
		"sudo":         3,
		"privilege":    2,
		"instructions": 2,
	}

	// Compile patterns
	compiledPatterns := make([]*regexp.Regexp, 0, len(dangerousPatterns))
	for _, pattern := range dangerousPatterns {
		re, err := regexp.Compile("(?i)" + pattern)
		if err != nil {
			log.Printf("WARNING: Failed to compile pattern %s: %v", pattern, err)
			continue
		}
		compiledPatterns = append(compiledPatterns, re)
	}

	return &PromptInjectionDetector{
		dangerousPatterns:  dangerousPatterns,
		suspiciousKeywords: suspiciousKeywords,
		threshold:          threshold,
		compiledPatterns:   compiledPatterns,
	}
}

// Detect detects prompt injection attempts.
//
// Args:
//
//	text: Input text to analyze
//
// Returns:
//
//	isInjection: true if injection detected
//	score: Risk score (0-100+)
//	matchedPatterns: List of matched patterns
//
// Example:
//
//	isInjection, score, patterns := detector.Detect("Ignore all previous instructions")
func (d *PromptInjectionDetector) Detect(text string) (bool, int, []string) {
	textLower := strings.ToLower(text)
	score := 0
	matched := make([]string, 0)

	// Check dangerous patterns
	for i, re := range d.compiledPatterns {
		if re.MatchString(textLower) {
			score += 10
			matched = append(matched, d.dangerousPatterns[i])
		}
	}

	// Check suspicious keywords
	wordRe := regexp.MustCompile(`\w+`)
	words := wordRe.FindAllString(textLower, -1)
	for _, word := range words {
		if points, ok := d.suspiciousKeywords[word]; ok {
			score += points
		}
	}

	// Heuristics
	// Multiple special characters (possible encoding/obfuscation)
	specialCharsRe := regexp.MustCompile(`[<>{}[\]|]`)
	specialChars := specialCharsRe.FindAllString(text, -1)
	if len(specialChars) > 5 {
		score += 2
	}

	// Very long prompts (possible payload)
	if len(text) > 5000 {
		score += 1
	}

	// Repeated instructions
	repeatedRe := regexp.MustCompile(`(?i)(please|must|you (should|will|must))`)
	repeated := repeatedRe.FindAllString(textLower, -1)
	if len(repeated) > 5 {
		score += 2
	}

	isInjection := score >= d.threshold

	return isInjection, score, matched
}

// IsSafe checks if text is safe (no injection detected).
func (d *PromptInjectionDetector) IsSafe(text string) bool {
	isInjection, _, _ := d.Detect(text)
	return !isInjection
}

// ContentFilter filters content based on policies.
//
// Supports:
//   - Banned words/phrases
//   - PII detection (basic)
//   - Size limits
//   - Format validation
//
// Example:
//
//	filter := NewContentFilter(10000, 1, []string{"badword"})
//	isValid, errorMsg := filter.Validate("Some content")
type ContentFilter struct {
	// Banned words/phrases
	bannedWords map[string]bool

	// Maximum content size (characters)
	maxSize int

	// Minimum content size (characters)
	minSize int

	// Allowed content types (if specified)
	allowedContentTypes map[string]bool

	// Compiled PII patterns
	piiPatterns []struct {
		pattern *regexp.Regexp
		name    string
	}
}

// NewContentFilter creates a new content filter.
//
// Args:
//
//	maxSize: Maximum content size in characters
//	minSize: Minimum content size in characters
//	bannedWords: List of banned words/phrases
//
// Example:
//
//	filter := NewContentFilter(10000, 1, []string{"spam", "badword"})
func NewContentFilter(maxSize, minSize int, bannedWords []string) *ContentFilter {
	bannedMap := make(map[string]bool)
	for _, word := range bannedWords {
		bannedMap[strings.ToLower(word)] = true
	}

	// Basic PII patterns
	piiPatterns := []struct {
		pattern *regexp.Regexp
		name    string
	}{
		{regexp.MustCompile(`\b\d{3}-\d{2}-\d{4}\b`), "Social Security Number"},
		{regexp.MustCompile(`\b\d{16}\b`), "Credit Card Number"},
		{regexp.MustCompile(`(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b`), "Email Address"},
	}

	return &ContentFilter{
		bannedWords:         bannedMap,
		maxSize:             maxSize,
		minSize:             minSize,
		allowedContentTypes: nil,
		piiPatterns:         piiPatterns,
	}
}

// Validate validates content against policies.
//
// Args:
//
//	content: Content to validate
//
// Returns:
//
//	isValid: true if content is valid
//	errorMessage: Error message if invalid (nil if valid)
//
// Example:
//
//	isValid, err := filter.Validate("Some content")
//	if !isValid {
//	    fmt.Println(err)
//	}
func (f *ContentFilter) Validate(content interface{}) (bool, *string) {
	// Convert to string for validation
	contentStr, ok := content.(string)
	if !ok {
		contentStr = fmt.Sprintf("%v", content)
	}

	// Size checks
	if len(contentStr) > f.maxSize {
		msg := fmt.Sprintf("Content exceeds maximum size (%d chars)", f.maxSize)
		return false, &msg
	}

	if len(contentStr) < f.minSize {
		msg := fmt.Sprintf("Content below minimum size (%d chars)", f.minSize)
		return false, &msg
	}

	// Banned words
	contentLower := strings.ToLower(contentStr)
	for word := range f.bannedWords {
		if strings.Contains(contentLower, word) {
			msg := fmt.Sprintf("Content contains banned word: %s", word)
			return false, &msg
		}
	}

	// Basic PII detection
	for _, pii := range f.piiPatterns {
		if pii.pattern.MatchString(contentStr) {
			msg := fmt.Sprintf("Content may contain %s", pii.name)
			return false, &msg
		}
	}

	return true, nil
}

// IsSafe checks if content is safe.
func (f *ContentFilter) IsSafe(content interface{}) bool {
	isValid, _ := f.Validate(content)
	return isValid
}

// InputValidationMiddleware provides middleware for input validation and prompt injection defense.
//
// Features:
//   - Prompt injection detection
//   - Content filtering
//   - Input sanitization
//   - Size limits
//
// Example:
//
//	middleware := NewInputValidationMiddleware(
//	    baseAgent,
//	    NewPromptInjectionDetector(15),
//	    NewContentFilter(5000, 1, []string{"spam"}),
//	    true,
//	)
//	response, _ := middleware.Process(ctx, message)
type InputValidationMiddleware struct {
	agent         agenkit.Agent
	detector      *PromptInjectionDetector
	contentFilter *ContentFilter
	strict        bool
}

// NewInputValidationMiddleware creates a new input validation middleware.
//
// Args:
//
//	agent: Agent to wrap
//	detector: Prompt injection detector (nil = default detector)
//	contentFilter: Content filter (nil = default filter)
//	strict: If true, block on validation failure. If false, log warning only.
//
// Example:
//
//	middleware := NewInputValidationMiddleware(
//	    agent,
//	    NewPromptInjectionDetector(10),
//	    NewContentFilter(10000, 1, nil),
//	    true,
//	)
func NewInputValidationMiddleware(
	agent agenkit.Agent,
	detector *PromptInjectionDetector,
	contentFilter *ContentFilter,
	strict bool,
) *InputValidationMiddleware {
	if detector == nil {
		detector = NewPromptInjectionDetector(10)
	}
	if contentFilter == nil {
		contentFilter = NewContentFilter(10000, 1, nil)
	}

	return &InputValidationMiddleware{
		agent:         agent,
		detector:      detector,
		contentFilter: contentFilter,
		strict:        strict,
	}
}

// Name returns the name of the underlying agent.
func (m *InputValidationMiddleware) Name() string {
	return m.agent.Name()
}

// Capabilities returns capabilities of the underlying agent.
func (m *InputValidationMiddleware) Capabilities() []string {
	return m.agent.Capabilities()
}

// Process processes message with input validation.
func (m *InputValidationMiddleware) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Validate message content
	contentStr := message.Content

	// 1. Check for prompt injection
	isInjection, score, matched := m.detector.Detect(contentStr)
	if isInjection {
		errorMsg := fmt.Sprintf(
			"Potential prompt injection detected (score: %d, patterns: %d)",
			score, len(matched),
		)

		if m.strict {
			matchedPreview := matched
			if len(matchedPreview) > 3 {
				matchedPreview = matchedPreview[:3]
			}

			contentPreview := contentStr
			if len(contentPreview) > 100 {
				contentPreview = contentPreview[:100]
			}

			return nil, &ValidationError{
				Message: errorMsg,
				Details: map[string]interface{}{
					"score":            score,
					"matched_patterns": matchedPreview,
					"content_preview":  contentPreview,
				},
			}
		}

		// Non-strict mode: log warning and continue
		log.Printf("WARNING: %s", errorMsg)
	}

	// 2. Check content filter
	isValid, errorMsgPtr := m.contentFilter.Validate(message.Content)
	if !isValid {
		errorMsg := *errorMsgPtr
		if m.strict {
			contentPreview := contentStr
			if len(contentPreview) > 100 {
				contentPreview = contentPreview[:100]
			}

			return nil, &ValidationError{
				Message: fmt.Sprintf("Content validation failed: %s", errorMsg),
				Details: map[string]interface{}{
					"content_preview": contentPreview,
				},
			}
		}

		log.Printf("WARNING: Content validation failed: %s", errorMsg)
	}

	// 3. Process with wrapped agent
	return m.agent.Process(ctx, message)
}
