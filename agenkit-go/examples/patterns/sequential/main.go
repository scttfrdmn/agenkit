// Package main demonstrates the Sequential pattern for pipeline composition.
//
// The Sequential pattern chains agents together where each agent's output
// becomes the input for the next agent. This creates processing pipelines
// ideal for multi-stage workflows.
//
// This example shows:
//   - Creating a document processing pipeline (extract -> translate -> summarize)
//   - Passing data through multiple transformation stages
//   - Observing intermediate results via metadata
//   - Handling errors in the pipeline
//
// Run with: go run sequential_pattern.go
package main

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// ExtractorAgent extracts key information from documents
type ExtractorAgent struct{}

func (e *ExtractorAgent) Name() string {
	return "Extractor"
}

func (e *ExtractorAgent) Capabilities() []string {
	return []string{"extraction", "parsing"}
}

func (e *ExtractorAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    e.Name(),
		Capabilities: e.Capabilities(),
	}
}

func (e *ExtractorAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("\n📄 Stage 1: Extracting key information...")

	// Simulate extraction by identifying key points
	content := message.Content
	var extracted strings.Builder

	extracted.WriteString("Extracted Key Information:\n")
	extracted.WriteString("- Original text length: ")
	extracted.WriteString(fmt.Sprintf("%d characters\n", len(content)))

	// Extract sentences (simplified)
	sentences := strings.Split(content, ".")
	extracted.WriteString(fmt.Sprintf("- Sentence count: %d\n", len(sentences)))

	// Extract keywords (simplified)
	words := strings.Fields(content)
	extracted.WriteString(fmt.Sprintf("- Word count: %d\n", len(words)))

	result := agenkit.NewMessage("agent", extracted.String())
	result.WithMetadata("stage", "extraction").
		WithMetadata("original_length", len(content))

	fmt.Printf("   ✓ Extracted metadata from document\n")
	return result, nil
}

// TranslatorAgent translates content to different format/language
type TranslatorAgent struct{}

func (t *TranslatorAgent) Name() string {
	return "Translator"
}

func (t *TranslatorAgent) Capabilities() []string {
	return []string{"translation", "transformation"}
}

func (t *TranslatorAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    t.Name(),
		Capabilities: t.Capabilities(),
	}
}

func (t *TranslatorAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("\n🌐 Stage 2: Translating to structured format...")

	// Simulate translation by converting to structured format
	var translated strings.Builder
	translated.WriteString("Structured Data:\n")
	translated.WriteString("{\n")

	lines := strings.Split(message.Content, "\n")
	for _, line := range lines {
		if strings.TrimSpace(line) != "" {
			translated.WriteString("  ")
			translated.WriteString(line)
			translated.WriteString("\n")
		}
	}

	translated.WriteString("}\n")

	result := agenkit.NewMessage("agent", translated.String())
	result.WithMetadata("stage", "translation").
		WithMetadata("format", "structured")

	fmt.Printf("   ✓ Translated to structured format\n")
	return result, nil
}

// SummarizerAgent creates concise summaries
type SummarizerAgent struct{}

func (s *SummarizerAgent) Name() string {
	return "Summarizer"
}

func (s *SummarizerAgent) Capabilities() []string {
	return []string{"summarization", "synthesis"}
}

func (s *SummarizerAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    s.Name(),
		Capabilities: s.Capabilities(),
	}
}

func (s *SummarizerAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("\n📝 Stage 3: Generating summary...")

	// Simulate summarization
	var summary strings.Builder
	summary.WriteString("Document Processing Summary:\n\n")

	// Check if we have pipeline metadata
	if pipelineStages, ok := message.Metadata["pipeline_stages"].([]map[string]interface{}); ok {
		summary.WriteString("Pipeline Stages Completed:\n")
		for _, stage := range pipelineStages {
			if agentName, ok := stage["agent"].(string); ok {
				summary.WriteString(fmt.Sprintf("  ✓ %s\n", agentName))
			}
		}
		summary.WriteString("\n")
	}

	summary.WriteString("Final Result:\n")
	summary.WriteString("The document has been successfully processed through extraction,\n")
	summary.WriteString("translation, and summarization stages. All key information has\n")
	summary.WriteString("been preserved and transformed into a structured format.\n")

	result := agenkit.NewMessage("agent", summary.String())
	result.WithMetadata("stage", "summarization").
		WithMetadata("final", true)

	fmt.Printf("   ✓ Generated final summary\n")
	return result, nil
}

func main() {
	fmt.Println("=== Sequential Pattern Demo ===")
	fmt.Println("Demonstrating document processing pipeline")

	// Create agents for each stage
	extractor := &ExtractorAgent{}
	translator := &TranslatorAgent{}
	summarizer := &SummarizerAgent{}

	// Create sequential pipeline
	pipeline, err := patterns.NewSequentialAgent([]agenkit.Agent{
		extractor,
		translator,
		summarizer,
	})
	if err != nil {
		log.Fatalf("Failed to create pipeline: %v", err)
	}

	fmt.Printf("Created pipeline: %s -> %s -> %s\n",
		extractor.Name(), translator.Name(), summarizer.Name())

	// Example document to process
	document := agenkit.NewMessage("user", `This is a sample document for processing.
It contains multiple sentences and various pieces of information.
The sequential pattern will process this through multiple stages.`)

	fmt.Println("\n📥 Input Document:")
	fmt.Printf("   %s\n", strings.ReplaceAll(document.Content, "\n", "\n   "))

	// Process through pipeline
	ctx := context.Background()
	result, err := pipeline.Process(ctx, document)
	if err != nil {
		log.Fatalf("Pipeline failed: %v", err)
	}

	// Display final result
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📤 Pipeline Output:")
	fmt.Println(result.Content)

	// Display metadata
	if pipelineLength, ok := result.Metadata["pipeline_length"].(int); ok {
		fmt.Printf("\nPipeline Statistics:\n")
		fmt.Printf("  Stages: %d\n", pipelineLength)
	}

	if stages, ok := result.Metadata["pipeline_stages"].([]map[string]interface{}); ok {
		fmt.Printf("  Agents: %d\n", len(stages))
	}

	// Demonstrate error handling
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n🔄 Testing error handling...")

	// Create a failing agent
	failingAgent := &FailingAgent{}
	faultPipeline, err := patterns.NewSequentialAgent([]agenkit.Agent{
		extractor,
		failingAgent,
		summarizer,
	})
	if err != nil {
		log.Fatalf("Failed to create fault pipeline: %v", err)
	}

	_, err = faultPipeline.Process(ctx, document)
	if err != nil {
		fmt.Printf("   ✓ Pipeline correctly stopped on error: %v\n", err)
	}

	fmt.Println("\n✅ Sequential pattern demo complete!")
}

// FailingAgent simulates an agent that fails
type FailingAgent struct{}

func (f *FailingAgent) Name() string {
	return "FailingAgent"
}

func (f *FailingAgent) Capabilities() []string {
	return []string{"failure"}
}

func (f *FailingAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    f.Name(),
		Capabilities: f.Capabilities(),
	}
}

func (f *FailingAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return nil, fmt.Errorf("simulated failure in pipeline")
}
