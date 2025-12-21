// Package main demonstrates the Multi-Agent pattern for coordinating multiple agents.
//
// The Multi-Agent pattern enables multiple agents to work together on complex tasks
// through different collaboration strategies like sequential execution, parallel
// processing, and consensus building.
//
// This example shows:
//   - Creating specialized agents with domain expertise
//   - Orchestrating agents sequentially (pipeline)
//   - Parallel execution for concurrent processing
//   - Consensus mechanisms for decision-making
//   - Dynamic agent registration and management
//
// Run with: go run multiagent_pattern.go
package main

import (
	"context"
	"fmt"
	"log"
	"strings"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// ResearchAgent simulates a research specialist
type ResearchAgent struct {
	specialty string
}

func (r *ResearchAgent) Name() string {
	return "Researcher"
}

func (r *ResearchAgent) Capabilities() []string {
	return []string{"research", "analysis"}
}

func (r *ResearchAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	content := message.Content

	// Simulate research work
	time.Sleep(50 * time.Millisecond)

	research := fmt.Sprintf("[Research - %s] Key findings: AI agents show promise in %s. "+
		"Recent studies indicate significant advances in multi-agent collaboration.",
		r.specialty, content)

	return agenkit.NewMessage("assistant", research), nil
}

// WritingAgent simulates a content writing specialist
type WritingAgent struct {
	style string
}

func (w *WritingAgent) Name() string {
	return "Writer"
}

func (w *WritingAgent) Capabilities() []string {
	return []string{"writing", "editing"}
}

func (w *WritingAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	content := message.Content

	// Simulate writing work
	time.Sleep(50 * time.Millisecond)

	text := fmt.Sprintf("[Writer - %s style] This comprehensive report explores %s. "+
		"The analysis reveals important insights for the field.",
		w.style, content)

	return agenkit.NewMessage("assistant", text), nil
}

// EditorAgent simulates an editing specialist
type EditorAgent struct{}

func (e *EditorAgent) Name() string {
	return "Editor"
}

func (e *EditorAgent) Capabilities() []string {
	return []string{"editing", "proofreading"}
}

func (e *EditorAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Simulate editing work
	time.Sleep(50 * time.Millisecond)

	feedback := "[Editor] Reviewed document. Corrected grammar, " +
		"improved clarity, and ensured consistent tone. " +
		"Ready for publication."

	return agenkit.NewMessage("assistant", feedback), nil
}

// CriticAgent simulates a critique specialist
type CriticAgent struct {
	perspective string
}

func (c *CriticAgent) Name() string {
	return "Critic"
}

func (c *CriticAgent) Capabilities() []string {
	return []string{"critique", "analysis"}
}

func (c *CriticAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	content := message.Content

	critique := fmt.Sprintf("[Critic - %s perspective] Regarding %s: "+
		"The approach has merit but should consider additional factors. "+
		"Recommend further validation.",
		c.perspective, content)

	return agenkit.NewMessage("assistant", critique), nil
}

// Example 1: Sequential orchestration (pipeline)
func exampleSequentialOrchestration() error {
	fmt.Println("\n=== Example 1: Sequential Orchestration ===\n")

	orchestrator := patterns.NewMultiAgentOrchestrator(patterns.OrchestrationStrategySequential)

	if err := orchestrator.RegisterAgent("researcher", &ResearchAgent{specialty: "ML"}); err != nil {
		return err
	}
	if err := orchestrator.RegisterAgent("writer", &WritingAgent{style: "academic"}); err != nil {
		return err
	}
	if err := orchestrator.RegisterAgent("editor", &EditorAgent{}); err != nil {
		return err
	}

	fmt.Printf("Registered agents: %v\n", orchestrator.ListAgents())
	fmt.Println("\nProcessing: Write a report on AI agents\n")

	message := agenkit.NewMessage("user", "AI agent capabilities")
	result, err := orchestrator.Process(context.Background(), message)
	if err != nil {
		return err
	}

	fmt.Printf("Combined result:\n%s\n\n", result.Content)

	// Check task history
	tasks := orchestrator.GetTasks()
	fmt.Printf("Tasks executed: %d\n", len(tasks))
	for _, task := range tasks {
		fmt.Printf("  - %s: %s\n", task.AgentName, task.Status)
	}

	return nil
}

// Example 2: Consensus building
func exampleConsensus() error {
	fmt.Println("\n=== Example 2: Consensus Building ===\n")

	consensus := patterns.NewConsensusAgent(patterns.VotingStrategyMajority)

	consensus.AddAgent(&CriticAgent{perspective: "conservative"})
	consensus.AddAgent(&CriticAgent{perspective: "innovative"})
	consensus.AddAgent(&CriticAgent{perspective: "pragmatic"})

	fmt.Printf("Voting strategy: %s\n", consensus.VotingStrategy())
	fmt.Printf("Number of agents: %d\n\n", len(consensus.Agents()))

	message := agenkit.NewMessage("user", "implementing multi-agent systems")
	result, err := consensus.Process(context.Background(), message)
	if err != nil {
		return err
	}

	fmt.Printf("Consensus result:\n%s\n\n", result.Content)

	return nil
}

// Example 3: Research team collaboration
func exampleResearchTeam() error {
	fmt.Println("\n=== Example 3: Research Team Collaboration ===\n")

	orchestrator := patterns.NewMultiAgentOrchestrator(patterns.OrchestrationStrategySequential)

	if err := orchestrator.RegisterAgent("ml_researcher", &ResearchAgent{specialty: "Machine Learning"}); err != nil {
		return err
	}
	if err := orchestrator.RegisterAgent("nlp_researcher", &ResearchAgent{specialty: "Natural Language Processing"}); err != nil {
		return err
	}
	if err := orchestrator.RegisterAgent("systems_researcher", &ResearchAgent{specialty: "Distributed Systems"}); err != nil {
		return err
	}

	message := agenkit.NewMessage("user", "conversational AI architectures")
	result, err := orchestrator.Process(context.Background(), message)
	if err != nil {
		return err
	}

	fmt.Printf("Research findings:\n%s\n\n", result.Content)

	return nil
}

// Example 4: Content creation pipeline
func exampleContentPipeline() error {
	fmt.Println("\n=== Example 4: Content Creation Pipeline ===\n")

	orchestrator := patterns.NewMultiAgentOrchestrator(patterns.OrchestrationStrategySequential)

	fmt.Println("Stage 1: Research")
	if err := orchestrator.RegisterAgent("researcher", &ResearchAgent{specialty: "Technical"}); err != nil {
		return err
	}

	fmt.Println("Stage 2: Writing")
	if err := orchestrator.RegisterAgent("writer", &WritingAgent{style: "technical"}); err != nil {
		return err
	}

	fmt.Println("Stage 3: Editing")
	if err := orchestrator.RegisterAgent("editor", &EditorAgent{}); err != nil {
		return err
	}

	fmt.Println("\nProcessing content pipeline...\n")

	message := agenkit.NewMessage("user", "agent design patterns")
	result, err := orchestrator.Process(context.Background(), message)
	if err != nil {
		return err
	}

	fmt.Printf("Pipeline output:\n%s\n\n", result.Content)

	// Show pipeline stages
	tasks := orchestrator.GetTasks()
	fmt.Println("Pipeline stages completed:")
	for i, task := range tasks {
		fmt.Printf("  %d. %s - %s\n", i+1, task.AgentName, task.Status)
	}

	return nil
}

// Example 5: Dynamic agent registration
func exampleDynamicRegistration() error {
	fmt.Println("\n=== Example 5: Dynamic Agent Registration ===\n")

	orchestrator := patterns.NewMultiAgentOrchestrator(patterns.OrchestrationStrategySequential)

	fmt.Printf("Initial agents: %v\n", orchestrator.ListAgents())

	// Add agents dynamically
	fmt.Println("\nAdding researcher...")
	if err := orchestrator.RegisterAgent("researcher", &ResearchAgent{specialty: "AI"}); err != nil {
		return err
	}
	fmt.Printf("Agents: %v\n", orchestrator.ListAgents())

	fmt.Println("\nAdding writer...")
	if err := orchestrator.RegisterAgent("writer", &WritingAgent{style: "concise"}); err != nil {
		return err
	}
	fmt.Printf("Agents: %v\n", orchestrator.ListAgents())

	// Process with current agents
	message := agenkit.NewMessage("user", "test topic")
	result, err := orchestrator.Process(context.Background(), message)
	if err != nil {
		return err
	}
	fmt.Printf("\nResult with 2 agents:\n%s\n\n", result.Content)

	// Remove an agent
	fmt.Println("Removing researcher...")
	orchestrator.UnregisterAgent("researcher")
	fmt.Printf("Agents: %v\n", orchestrator.ListAgents())

	return nil
}

func main() {
	fmt.Println("Multi-Agent Collaboration Pattern Examples")
	fmt.Println(strings.Repeat("=", 60))

	// Run all examples
	if err := exampleSequentialOrchestration(); err != nil {
		log.Fatalf("Example 1 failed: %v", err)
	}

	if err := exampleConsensus(); err != nil {
		log.Fatalf("Example 2 failed: %v", err)
	}

	if err := exampleResearchTeam(); err != nil {
		log.Fatalf("Example 3 failed: %v", err)
	}

	if err := exampleContentPipeline(); err != nil {
		log.Fatalf("Example 4 failed: %v", err)
	}

	if err := exampleDynamicRegistration(); err != nil {
		log.Fatalf("Example 5 failed: %v", err)
	}

	fmt.Println("\n" + strings.Repeat("=", 60))
	fmt.Println("✓ All examples completed successfully!")
	fmt.Println("\n💡 Key takeaways:")
	fmt.Println("   - Sequential: Agents process in order, output → input chaining")
	fmt.Println("   - Parallel: Multiple agents work concurrently")
	fmt.Println("   - Consensus: Agents vote to reach agreements")
	fmt.Println("   - Dynamic: Agents can be added/removed at runtime")
	fmt.Println()
	fmt.Println("🎯 When to use Multi-Agent:")
	fmt.Println("   - Complex tasks requiring multiple specializations")
	fmt.Println("   - Pipelines with distinct stages")
	fmt.Println("   - Decision-making requiring multiple perspectives")
	fmt.Println("   - Systems needing modular, composable agents")
}
