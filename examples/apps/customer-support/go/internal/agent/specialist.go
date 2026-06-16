package agent

import (
	"context"
	"log"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// SpecialistAgent handles complex queries with RAG search and analytics.
type SpecialistAgent struct {
	name string
}

// NewSpecialistAgent creates a new specialist agent.
func NewSpecialistAgent() *SpecialistAgent {
	return &SpecialistAgent{
		name: "specialist",
	}
}

// Name returns the agent name.
func (a *SpecialistAgent) Name() string {
	return a.name
}

// Capabilities returns agent capabilities.
func (a *SpecialistAgent) Capabilities() []string {
	return []string{"rag", "analytics", "complex_queries"}
}

// Introspect returns a snapshot of the agent's current state.
func (a *SpecialistAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(a)
}

// Process handles complex queries.
//
// In production, this would:
// 1. Perform vector similarity search (RAG)
// 2. Analyze customer history
// 3. Generate personalized responses
//
// For now, it provides intelligent responses based on keywords.
func (a *SpecialistAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	query := strings.ToLower(message.ContentString())

	log.Printf("Specialist agent processing: %s", query)

	// Handle health checks
	if message.Metadata != nil {
		if msgType, ok := message.Metadata["type"].(string); ok && msgType == "health_check" {
			return &agenkit.Message{
				Role:    "assistant",
				Content: "healthy",
				Metadata: map[string]interface{}{
					"source": "specialist",
					"status": "ok",
				},
			}, nil
		}
	}

	// Simulate RAG search and complex processing
	var response string
	var confidence float64 = 0.85
	var sources []string

	// Topic detection
	switch {
	case strings.Contains(query, "performance") || strings.Contains(query, "slow"):
		response = "I've analyzed your account performance. Based on recent data, I recommend: " +
			"1) Clear browser cache and cookies, 2) Reduce concurrent operations, " +
			"3) Upgrade to Premium for enhanced performance infrastructure. " +
			"Your current usage shows 2.3GB data with 50+ concurrent files."
		sources = []string{"performance_kb", "account_analytics", "system_metrics"}

	case strings.Contains(query, "integration") || strings.Contains(query, "api"):
		response = "For API integration, I recommend: " +
			"1) Use OAuth 2.0 authentication (docs.example.com/oauth), " +
			"2) Rate limits: 1000 req/hour (Standard), 10000 req/hour (Premium), " +
			"3) SDKs available: Python, JavaScript, Go. " +
			"Your account has API access enabled."
		sources = []string{"api_docs", "integration_guide", "account_settings"}

	case strings.Contains(query, "security") || strings.Contains(query, "breach"):
		response = "Security is our top priority. Based on your account review: " +
			"1) No unauthorized access detected in last 90 days, " +
			"2) Recommend enabling 2FA (currently disabled), " +
			"3) Consider using hardware security keys. " +
			"Last login: 2 hours ago from your usual location."
		sources = []string{"security_logs", "account_activity", "best_practices"}

	case strings.Contains(query, "data") || strings.Contains(query, "storage"):
		response = "Your data analysis: " +
			"1) Current usage: 2.3GB / 5GB (46% used), " +
			"2) Growth rate: +150MB/month, " +
			"3) Projected capacity in 18 months. " +
			"Consider Premium (unlimited storage) or archive old files."
		sources = []string{"storage_analytics", "usage_trends", "capacity_planning"}

	case strings.Contains(query, "team") || strings.Contains(query, "collaborate"):
		response = "Team collaboration setup: " +
			"1) Current: 1 user (owner), " +
			"2) Add team members in Settings > Team (requires Premium), " +
			"3) Recommended roles: Admin (full access), Editor (read/write), Viewer (read-only). " +
			"Premium plan supports unlimited team members."
		sources = []string{"team_management", "collaboration_guide", "account_type"}

	default:
		response = "Based on comprehensive analysis of your query, I recommend reviewing our documentation at docs.example.com. " +
			"For personalized assistance with this specific issue, I can escalate to our specialist team. " +
			"Would you like me to create a support ticket?"
		sources = []string{"general_kb"}
		confidence = 0.60
	}

	log.Printf("Generated response with %d sources, confidence: %.2f", len(sources), confidence)

	// Return response with metadata
	return &agenkit.Message{
		Role:    "assistant",
		Content: response,
		Metadata: map[string]interface{}{
			"source":       "specialist_rag",
			"confidence":   confidence,
			"sources":      sources,
			"num_sources":  len(sources),
			"processed_by": "go_worker",
		},
	}, nil
}
