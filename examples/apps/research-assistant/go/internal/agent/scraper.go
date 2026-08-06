package agent

import (
	"context"
	"fmt"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ScraperAgent handles web scraping and content extraction.
type ScraperAgent struct {
	name string
}

// NewScraperAgent creates a new scraper agent.
func NewScraperAgent() *ScraperAgent {
	return &ScraperAgent{name: "scraper"}
}

// Name returns the agent name.
func (a *ScraperAgent) Name() string {
	return a.name
}

// Capabilities returns agent capabilities.
func (a *ScraperAgent) Capabilities() []string {
	return []string{"html_parsing", "pdf_extraction", "web_scraping"}
}

// Introspect satisfies agenkit.Agent, which grpc.NewGRPCServer requires. It was
// missing since Introspect() joined the interface (#847); nothing noticed because
// this tree had no go.mod and no cmd/worker, so nothing ever compiled it (#857).
func (a *ScraperAgent) Introspect() *agenkit.IntrospectionResult {
	result, err := agenkit.NewIntrospectionResult(
		a.name,
		a.Capabilities(),
		nil,
		map[string]interface{}{"worker_language": "go"},
		nil,
	)
	if err != nil {
		return nil
	}
	return result
}

// Process handles scraping requests.
func (a *ScraperAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Health check
	if message.Metadata != nil {
		if msgType, ok := message.Metadata["type"].(string); ok && msgType == "health_check" {
			return &agenkit.Message{
				Role:     "assistant",
				Content:  "healthy",
				Metadata: map[string]interface{}{"status": "ok"},
			}, nil
		}
	}

	// Message.Content is `any` (it can carry structured content), so read it
	// through ContentString() rather than passing it to a string parameter.
	request := message.ContentString()
	content := strings.ToLower(request)
	var result string

	// Simulate scraping based on content
	switch {
	case strings.Contains(content, "html"):
		result = "Scraped HTML content: <html><body>Sample content</body></html>"
	case strings.Contains(content, "pdf"):
		result = "Extracted PDF text: Sample PDF content with multiple pages"
	default:
		result = fmt.Sprintf("Scraped web content for: %s", request)
	}

	return &agenkit.Message{
		Role:    "assistant",
		Content: result,
		Metadata: map[string]interface{}{
			"source":       "go_scraper",
			"content_type": "text",
		},
	}, nil
}
