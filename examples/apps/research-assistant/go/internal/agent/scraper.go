package agent

import (
	"context"
	"fmt"
	"strings"

	agenkit "github.com/scttfrdmn/agenkit/agenkit-go"
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

	content := strings.ToLower(message.Content)
	var result string

	// Simulate scraping based on content
	switch {
	case strings.Contains(content, "html"):
		result = "Scraped HTML content: <html><body>Sample content</body></html>"
	case strings.Contains(content, "pdf"):
		result = "Extracted PDF text: Sample PDF content with multiple pages"
	default:
		result = fmt.Sprintf("Scraped web content for: %s", message.Content)
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
