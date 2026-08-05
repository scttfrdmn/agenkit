//go:build ignore

// minihaystack demonstrates Haystack-equivalent RAG pipeline patterns using Agenkit.
//
// deepset Haystack popularised the "pipeline" abstraction for NLP and RAG: a
// sequential chain of components where each component processes the incoming
// message and passes it to the next. The core RAG pattern is:
//
//	Retriever  → find relevant documents from a store
//	PromptBuilder → combine retrieved context + question into a prompt
//	Generator  → call an LLM to produce the final answer
//
// Agenkit maps these ideas cleanly onto its core primitives:
//
//	Component interface       → Process(ctx, *agenkit.Message) (*agenkit.Message, error)
//	Pipeline                  → sequential Component chain (fluent Add API)
//	InMemoryDocumentStore     → keyword-overlap search over in-memory documents
//	Retriever component       → wraps InMemoryDocumentStore; stores hits in metadata
//	PromptBuilder component   → fills {{context}}/{{question}} template from metadata
//	Generator component       → calls llm.LLM with the built prompt
//
// This file implements lightweight inline versions to make the mapping explicit.
// Production code should use the native Agenkit pattern types.
//
// Prerequisites (optional — demo degrades gracefully if unavailable):
//
//	ollama serve && ollama pull llama3.2
//
// Run with:
//
//	go run main.go
package main

import (
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/llm"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ---------------------------------------------------------------------------
// Component interface — the fundamental Haystack abstraction
// ---------------------------------------------------------------------------

// Component is the minimal interface shared by all pipeline stages.
// Each implementation receives an agenkit.Message, does its work (potentially
// storing results in the message's metadata), and returns a (possibly new)
// message for the next stage.
// Equivalent to Haystack's Component protocol.
type Component interface {
	Name() string
	Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error)
}

// ---------------------------------------------------------------------------
// Pipeline — sequential component chain
// ---------------------------------------------------------------------------

// Pipeline runs a list of components in order. The output message of each
// stage becomes the input to the next.
// Equivalent to Haystack's Pipeline with .add_component() and .run().
type Pipeline struct {
	name       string
	components []Component
}

// NewPipeline creates an empty pipeline with the given name.
func NewPipeline(name string) *Pipeline {
	return &Pipeline{name: name}
}

// Add appends a component to the pipeline and returns the pipeline for
// fluent chaining.
func (p *Pipeline) Add(c Component) *Pipeline {
	p.components = append(p.components, c)
	return p
}

// Run creates an initial message from the input string, threads it through all
// components in order, and returns the final message's text content.
func (p *Pipeline) Run(ctx context.Context, input string) (string, error) {
	msg := agenkit.NewMessage("user", input)

	for i, c := range p.components {
		out, err := c.Process(ctx, msg)
		if err != nil {
			return "", fmt.Errorf("pipeline %q component %d (%s): %w", p.name, i, c.Name(), err)
		}
		msg = out
	}

	return msg.ContentString(), nil
}

// ---------------------------------------------------------------------------
// Document — a stored piece of text
// ---------------------------------------------------------------------------

// Document represents a single retrievable unit of text in the document store.
// Equivalent to Haystack's Document dataclass.
type Document struct {
	ID      string
	Title   string
	Content string
	Score   float64 // relevance score assigned during retrieval
}

// ---------------------------------------------------------------------------
// InMemoryDocumentStore — keyword-overlap document store
// ---------------------------------------------------------------------------

// InMemoryDocumentStore holds documents in memory and ranks them by keyword
// overlap with a query.
// Equivalent to Haystack's InMemoryDocumentStore.
type InMemoryDocumentStore struct {
	docs []Document
}

// Add appends a document to the store.
func (s *InMemoryDocumentStore) Add(doc Document) {
	s.docs = append(s.docs, doc)
}

// Search returns the top-K documents ranked by the number of query words
// that appear in the document's content (case-insensitive). Documents with
// zero overlap are excluded.
func (s *InMemoryDocumentStore) Search(query string, topK int) []Document {
	queryWords := strings.Fields(strings.ToLower(query))
	if len(queryWords) == 0 {
		return nil
	}

	scored := make([]Document, len(s.docs))
	copy(scored, s.docs)

	for i := range scored {
		lowerContent := strings.ToLower(scored[i].Content + " " + scored[i].Title)
		var overlap int
		for _, w := range queryWords {
			if strings.Contains(lowerContent, w) {
				overlap++
			}
		}
		scored[i].Score = float64(overlap) / float64(len(queryWords))
	}

	// Simple insertion sort (store is small; avoids a sort import).
	for i := 1; i < len(scored); i++ {
		for j := i; j > 0 && scored[j].Score > scored[j-1].Score; j-- {
			scored[j], scored[j-1] = scored[j-1], scored[j]
		}
	}

	// Keep only documents with a non-zero score, up to topK.
	var results []Document
	for _, d := range scored {
		if d.Score == 0 || len(results) >= topK {
			break
		}
		results = append(results, d)
	}
	return results
}

// ---------------------------------------------------------------------------
// Retriever component
// ---------------------------------------------------------------------------

// Retriever queries the document store with the message's text content,
// formats the hits as a numbered list, and stores the formatted context in
// the message metadata under the key "retrieved_docs".
// Equivalent to Haystack's InMemoryBM25Retriever (or InMemoryEmbeddingRetriever).
type Retriever struct {
	name  string
	store *InMemoryDocumentStore
	topK  int
}

// Name returns the component identifier.
func (r *Retriever) Name() string { return r.name }

// Process retrieves documents relevant to the message content and annotates
// the returned message with the formatted context.
func (r *Retriever) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	query := msg.ContentString()
	docs := r.store.Search(query, r.topK)

	var sb strings.Builder
	if len(docs) == 0 {
		sb.WriteString("No relevant documents found.")
	} else {
		for i, d := range docs {
			fmt.Fprintf(&sb, "Document %d: %s (score: %.2f)\n%s\n---\n", i+1, d.Title, d.Score, d.Content)
		}
	}
	context := strings.TrimSuffix(sb.String(), "---\n")

	// Pass the query through unchanged but annotate the metadata.
	out := agenkit.NewMessage("user", query)
	if out.Metadata == nil {
		out.Metadata = make(map[string]any)
	}
	out.Metadata["retrieved_docs"] = context
	out.Metadata["doc_count"] = len(docs)
	out.Metadata["doc_titles"] = docTitles(docs)
	return out, nil
}

func docTitles(docs []Document) []string {
	titles := make([]string, len(docs))
	for i, d := range docs {
		titles[i] = d.Title
	}
	return titles
}

// ---------------------------------------------------------------------------
// PromptBuilder component
// ---------------------------------------------------------------------------

// PromptBuilder renders a prompt template by substituting {{context}} with
// the retrieved documents (from metadata) and {{question}} with the message
// content.
// Equivalent to Haystack's PromptBuilder(template=…).
type PromptBuilder struct {
	name     string
	template string // must contain {{context}} and {{question}} placeholders
}

// Name returns the component identifier.
func (b *PromptBuilder) Name() string { return b.name }

// Process renders the template and returns a new message containing the
// rendered prompt. Metadata is forwarded unchanged.
func (b *PromptBuilder) Process(_ context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	question := msg.ContentString()

	contextStr := "[no context retrieved]"
	if raw, ok := msg.Metadata["retrieved_docs"]; ok {
		if s, ok := raw.(string); ok && s != "" {
			contextStr = s
		}
	}

	prompt := strings.ReplaceAll(b.template, "{{context}}", contextStr)
	prompt = strings.ReplaceAll(prompt, "{{question}}", question)

	out := agenkit.NewMessage("user", prompt)
	out.Metadata = msg.Metadata
	return out, nil
}

// ---------------------------------------------------------------------------
// Generator component
// ---------------------------------------------------------------------------

// Generator calls the LLM with the message content as the user turn and
// returns the assistant's reply as a new message.
// Equivalent to Haystack's OpenAIGenerator (or any other LLM generator node).
type Generator struct {
	name      string
	llmClient llm.LLM
}

// Name returns the component identifier.
func (g *Generator) Name() string { return g.name }

// Process sends the message to the LLM and returns the assistant reply.
// If the LLM server is unreachable it returns a demo placeholder so the rest
// of the pipeline can complete.
func (g *Generator) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	msgs := []*agenkit.Message{
		agenkit.NewMessage("system", "You are a helpful assistant. Answer the question using only the provided context. Be concise."),
		msg,
	}

	resp, err := g.llmClient.Complete(ctx, msgs)
	if err != nil {
		if strings.Contains(err.Error(), "connection refused") ||
			strings.Contains(err.Error(), "no such host") {
			fmt.Println("  [LLM not running — showing structure only]")
			out := agenkit.NewMessage("assistant", "[demo: LLM not available — RAG pipeline structure demonstrated]")
			out.Metadata = msg.Metadata
			return out, nil
		}
		return nil, fmt.Errorf("generator LLM call failed: %w", err)
	}

	out := agenkit.NewMessage("assistant", resp.ContentString())
	out.Metadata = msg.Metadata
	return out, nil
}

// ---------------------------------------------------------------------------
// Sample documents
// ---------------------------------------------------------------------------

// sampleDocuments returns a small corpus covering five distinct topics.
// The retriever's keyword-overlap scoring ensures each query below returns
// the most relevant document(s).
func sampleDocuments() []Document {
	return []Document{
		{
			ID:    "doc-ai",
			Title: "Advances in Artificial Intelligence",
			Content: "Artificial intelligence (AI) has transformed industries through machine learning, " +
				"deep neural networks, and large language models. Transformer architectures, introduced " +
				"in 2017, underpin models such as GPT-4 and Claude that can reason, write code, and " +
				"generate images. Reinforcement learning from human feedback (RLHF) has been key to " +
				"aligning AI systems with human values.",
		},
		{
			ID:    "doc-climate",
			Title: "Climate Change and Renewable Energy",
			Content: "Global average temperatures have risen approximately 1.2 °C above pre-industrial " +
				"levels, driven primarily by greenhouse gas emissions from fossil fuels. Solar and wind " +
				"energy capacity has grown exponentially, now accounting for over 30% of new electricity " +
				"generation globally. Carbon capture and storage (CCS) technologies are being deployed " +
				"to offset hard-to-abate industrial emissions.",
		},
		{
			ID:    "doc-space",
			Title: "Space Exploration Milestones",
			Content: "The Artemis programme aims to return humans to the Moon by 2026 and establish a " +
				"sustainable lunar presence as a stepping stone to Mars. SpaceX's Starship is the most " +
				"powerful rocket ever built, designed for full reusability. The James Webb Space Telescope " +
				"has captured infrared images of galaxies formed just 300 million years after the Big Bang.",
		},
		{
			ID:    "doc-medicine",
			Title: "Breakthroughs in Modern Medicine",
			Content: "mRNA vaccine technology, proven by COVID-19 vaccines, is now being adapted to target " +
				"cancer, HIV, and influenza. CRISPR-Cas9 gene editing has enabled the first approved cure " +
				"for sickle-cell disease. AI-assisted diagnostics can detect diabetic retinopathy, certain " +
				"cancers, and cardiac abnormalities from medical imaging with accuracy matching specialists.",
		},
		{
			ID:    "doc-economics",
			Title: "Global Economic Trends",
			Content: "Deglobalisation trends, triggered by supply-chain disruptions during the pandemic and " +
				"geopolitical tensions, have prompted reshoring of semiconductor and pharmaceutical " +
				"manufacturing. Central banks in major economies raised interest rates sharply to combat " +
				"post-pandemic inflation, leading to tighter credit conditions. Digital currencies and " +
				"instant payment rails are reshaping cross-border transactions.",
		},
	}
}

// ---------------------------------------------------------------------------
// Demo helpers
// ---------------------------------------------------------------------------

func printSection(title string) {
	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println(title)
	fmt.Println(strings.Repeat("=", 60))
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

func main() {
	ctx := context.Background()

	// Single Ollama-backed LLM used by the Generator component.
	// NewOpenAICompatibleLLM works with Ollama, vLLM, llama.cpp, LM Studio — any
	// server that exposes the OpenAI /v1/chat/completions endpoint.
	ollamaLLM := llm.NewOpenAICompatibleLLM(
		"http://localhost:11434/v1",
		"llama3.2",
		"ollama",
		"", // no API key required for local servers
	)

	fmt.Println("MiniHaystack — Haystack RAG pipeline patterns with Agenkit")
	fmt.Println("Mapping: Component / Pipeline / InMemoryDocumentStore / Retriever / PromptBuilder / Generator")

	// ------------------------------------------------------------------
	// Build the document store and populate it
	// ------------------------------------------------------------------
	printSection("Document Store")
	store := &InMemoryDocumentStore{}
	for _, doc := range sampleDocuments() {
		store.Add(doc)
		fmt.Printf("  added: %s\n", doc.Title)
	}

	// ------------------------------------------------------------------
	// Assemble the RAG pipeline: Retriever → PromptBuilder → Generator
	// ------------------------------------------------------------------
	printSection("Pipeline Assembly  (Retriever → PromptBuilder → Generator)")
	fmt.Println("Haystack equivalent: Pipeline().add_component('retriever', …).add_component('builder', …).add_component('generator', …)")

	ragTemplate := `Answer the following question using only the context below.
If the context does not contain enough information, say so.

Context:
{{context}}

Question: {{question}}

Answer:`

	pipeline := NewPipeline("rag").
		Add(&Retriever{
			name:  "retriever",
			store: store,
			topK:  2,
		}).
		Add(&PromptBuilder{
			name:     "prompt_builder",
			template: ragTemplate,
		}).
		Add(&Generator{
			name:      "generator",
			llmClient: ollamaLLM,
		})

	fmt.Printf("Pipeline %q: %d components\n", pipeline.name, len(pipeline.components))
	for i, c := range pipeline.components {
		fmt.Printf("  [%d] %s\n", i+1, c.Name())
	}

	// ------------------------------------------------------------------
	// Run the pipeline with two different questions
	// ------------------------------------------------------------------
	questions := []struct {
		q     string
		topic string
	}{
		{
			q:     "What is CRISPR and how is it being used in medicine?",
			topic: "medicine",
		},
		{
			q:     "How has transformer architecture changed artificial intelligence?",
			topic: "AI",
		},
	}

	for i, question := range questions {
		printSection(fmt.Sprintf("Query %d: %s", i+1, question.topic))
		fmt.Printf("Question: %s\n\n", question.q)

		// Run retrieval step first to show which documents were selected.
		retriever := &Retriever{name: "retriever", store: store, topK: 2}
		retrieved, err := retriever.Process(ctx, agenkit.NewMessage("user", question.q))
		if err != nil {
			fmt.Fprintf(os.Stderr, "retrieval failed: %v\n", err)
			os.Exit(1)
		}
		if titles, ok := retrieved.Metadata["doc_titles"].([]string); ok && len(titles) > 0 {
			fmt.Printf("Retrieved documents: %s\n\n", strings.Join(titles, ", "))
		}

		// Run the full pipeline.
		answer, err := pipeline.Run(ctx, question.q)
		if err != nil {
			fmt.Fprintf(os.Stderr, "pipeline failed: %v\n", err)
			os.Exit(1)
		}

		fmt.Printf("Answer:\n%s\n", answer)
	}

	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("MiniHaystack demo complete.")
	fmt.Println()
	fmt.Println("Key takeaways:")
	fmt.Println("  Component          → interface: Name() + Process(ctx, *agenkit.Message)")
	fmt.Println("  Pipeline.Add       → fluent API; output of step N feeds step N+1")
	fmt.Println("  InMemoryDocStore   → keyword-overlap scoring; swap for vector search in prod")
	fmt.Println("  Retriever          → stores hits in message.Metadata[\"retrieved_docs\"]")
	fmt.Println("  PromptBuilder      → {{context}}/{{question}} template substitution")
	fmt.Println("  Generator          → calls llm.LLM; graceful fallback when server is down")
	fmt.Println()
	fmt.Println("For production use, prefer the native Agenkit pattern types:")
	fmt.Println("  patterns.NewSequentialAgent with middleware for caching and retries —")
	fmt.Println("  same pipeline concept with battle-tested observability hooks.")
}
