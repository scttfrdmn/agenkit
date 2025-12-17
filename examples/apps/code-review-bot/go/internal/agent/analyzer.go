package agent

import (
	"context"
	"fmt"
	"strings"

	"github.com/anthropics/agenkit-go/agenkit"
)

// AnalyzerAgent performs static code analysis.
type AnalyzerAgent struct {
	name string
}

// NewAnalyzerAgent creates a new analyzer agent.
func NewAnalyzerAgent() *AnalyzerAgent {
	return &AnalyzerAgent{
		name: "analyzer",
	}
}

// Name returns the agent name.
func (a *AnalyzerAgent) Name() string {
	return a.name
}

// Capabilities returns agent capabilities.
func (a *AnalyzerAgent) Capabilities() []string {
	return []string{"static_analysis", "security_scanning", "complexity_analysis"}
}

// Process analyzes code for issues.
func (a *AnalyzerAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	code := message.Content

	// Handle health checks
	if message.Metadata != nil {
		if msgType, ok := message.Metadata["type"].(string); ok && msgType == "health_check" {
			return &agenkit.Message{
				Role:    "assistant",
				Content: "healthy",
				Metadata: map[string]interface{}{
					"status": "ok",
				},
			}, nil
		}
	}

	// Detect language
	language := "unknown"
	if message.Metadata != nil {
		if lang, ok := message.Metadata["language"].(string); ok {
			language = lang
		}
	}

	// Perform analysis
	issues := a.analyzeCode(code, language)

	// Calculate metrics
	complexity := a.calculateComplexity(code)
	securityScore := a.calculateSecurityScore(issues)

	// Build response
	report := a.buildReport(issues, complexity, securityScore)

	return &agenkit.Message{
		Role:    "assistant",
		Content: report,
		Metadata: map[string]interface{}{
			"source":         "static_analyzer",
			"language":       language,
			"issues_found":   len(issues),
			"complexity":     complexity,
			"security_score": securityScore,
			"processed_by":   "go_analyzer",
		},
	}, nil
}

// Issue represents a code issue.
type Issue struct {
	Severity string
	Line     int
	Message  string
	Category string
}

func (a *AnalyzerAgent) analyzeCode(code string, language string) []Issue {
	issues := []Issue{}

	lines := strings.Split(code, "\n")

	// Security checks
	for i, line := range lines {
		lineLower := strings.ToLower(line)

		// SQL injection
		if strings.Contains(lineLower, "execute(") && strings.Contains(lineLower, "+") {
			issues = append(issues, Issue{
				Severity: "high",
				Line:     i + 1,
				Message:  "Potential SQL injection - avoid string concatenation in queries",
				Category: "security",
			})
		}

		// Hardcoded secrets
		if strings.Contains(lineLower, "password") && strings.Contains(line, "=") {
			issues = append(issues, Issue{
				Severity: "critical",
				Line:     i + 1,
				Message:  "Potential hardcoded password - use environment variables",
				Category: "security",
			})
		}

		// eval() usage
		if strings.Contains(lineLower, "eval(") {
			issues = append(issues, Issue{
				Severity: "high",
				Line:     i + 1,
				Message:  "Use of eval() is dangerous - consider safer alternatives",
				Category: "security",
			})
		}
	}

	// Code quality checks
	for i, line := range lines {
		// Long lines
		if len(line) > 120 {
			issues = append(issues, Issue{
				Severity: "low",
				Line:     i + 1,
				Message:  fmt.Sprintf("Line too long (%d characters) - consider breaking it up", len(line)),
				Category: "style",
			})
		}

		// Missing error handling (language-specific)
		if language == "go" && strings.Contains(line, ":=") && !strings.Contains(line, "err") {
			if strings.Contains(line, "Open(") || strings.Contains(line, "Read(") {
				issues = append(issues, Issue{
					Severity: "medium",
					Line:     i + 1,
					Message:  "Potential unchecked error - always check error returns",
					Category: "reliability",
				})
			}
		}
	}

	return issues
}

func (a *AnalyzerAgent) calculateComplexity(code string) int {
	// Simple cyclomatic complexity approximation
	complexity := 1

	keywords := []string{"if", "for", "while", "case", "catch", "&&", "||"}
	codeLower := strings.ToLower(code)

	for _, keyword := range keywords {
		complexity += strings.Count(codeLower, keyword)
	}

	return complexity
}

func (a *AnalyzerAgent) calculateSecurityScore(issues []Issue) float64 {
	if len(issues) == 0 {
		return 100.0
	}

	deductions := 0.0
	for _, issue := range issues {
		switch issue.Severity {
		case "critical":
			deductions += 30.0
		case "high":
			deductions += 15.0
		case "medium":
			deductions += 5.0
		case "low":
			deductions += 1.0
		}
	}

	score := 100.0 - deductions
	if score < 0 {
		score = 0
	}

	return score
}

func (a *AnalyzerAgent) buildReport(issues []Issue, complexity int, securityScore float64) string {
	var report strings.Builder

	report.WriteString("# Static Analysis Report\n\n")

	// Summary
	report.WriteString("## Summary\n\n")
	report.WriteString(fmt.Sprintf("- **Issues Found**: %d\n", len(issues)))
	report.WriteString(fmt.Sprintf("- **Complexity**: %d\n", complexity))
	report.WriteString(fmt.Sprintf("- **Security Score**: %.1f/100\n\n", securityScore))

	// Complexity assessment
	report.WriteString("## Complexity Assessment\n\n")
	if complexity < 10 {
		report.WriteString("✅ Low complexity - code is easy to understand and maintain.\n\n")
	} else if complexity < 20 {
		report.WriteString("⚠️  Moderate complexity - consider breaking into smaller functions.\n\n")
	} else {
		report.WriteString("❌ High complexity - refactoring strongly recommended.\n\n")
	}

	// Issues
	if len(issues) > 0 {
		report.WriteString("## Issues\n\n")

		// Group by severity
		severities := []string{"critical", "high", "medium", "low"}
		for _, severity := range severities {
			severityIssues := []Issue{}
			for _, issue := range issues {
				if issue.Severity == severity {
					severityIssues = append(severityIssues, issue)
				}
			}

			if len(severityIssues) > 0 {
				report.WriteString(fmt.Sprintf("### %s Priority (%d)\n\n", strings.Title(severity), len(severityIssues)))
				for _, issue := range severityIssues {
					report.WriteString(fmt.Sprintf("- **Line %d** [%s]: %s\n", issue.Line, issue.Category, issue.Message))
				}
				report.WriteString("\n")
			}
		}
	} else {
		report.WriteString("## Issues\n\n")
		report.WriteString("✅ No issues found - code looks good!\n\n")
	}

	return report.String()
}
