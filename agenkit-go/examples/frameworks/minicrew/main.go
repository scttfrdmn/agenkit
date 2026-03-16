//go:build ignore

// minicrew demonstrates CrewAI-equivalent multi-agent team patterns using Agenkit.
//
// CrewAI organises LLM-backed agents into a "crew" with assigned roles, goals,
// and backstories. Each agent works on a specific task. Crews can run tasks
// sequentially (one after another) or in parallel. Agenkit maps these ideas
// directly onto its core primitives:
//
//	CrewMember (Agent + role/goal/backstory)  → agenkit.Agent with LLM backing
//	Task (description + expected output)      → structured work unit per agent
//	Crew (members + tasks + process)          → orchestrator calling agents in order
//	ProcessSequential                         → patterns.SequentialAgent
//
// This file implements inline versions of each concept to make the mapping
// explicit. Production code should use the native Agenkit pattern types.
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
// ProcessType — controls how the Crew executes tasks
// ---------------------------------------------------------------------------

// ProcessType determines whether a Crew runs its tasks one at a time or in
// parallel. Maps to CrewAI's Process enum.
type ProcessType string

const (
	// ProcessSequential runs tasks in order; each task's output can feed into
	// the next task's context. Equivalent to CrewAI's Process.sequential.
	ProcessSequential ProcessType = "sequential"

	// ProcessParallel runs all tasks concurrently. Equivalent to CrewAI's
	// Process.parallel (demonstrated as a concept; wiring omitted for brevity).
	ProcessParallel ProcessType = "parallel"
)

// ---------------------------------------------------------------------------
// CrewMember — an LLM-backed agent with role, goal, and backstory
// ---------------------------------------------------------------------------

// CrewMember is a specialised agent with an assigned role, goal, and backstory
// that are injected into the system prompt on every task execution.
// Equivalent to CrewAI's Agent(role=…, goal=…, backstory=…, llm=…).
type CrewMember struct {
	Name      string
	Role      string
	Goal      string
	Backstory string
	LLMClient llm.LLM
}

// Execute carries out a single task described by taskDescription.
// It builds a system prompt from the member's role, goal, and backstory, then
// sends the task as a user message. If the LLM server is unreachable the
// method returns a placeholder so the rest of the demo can continue.
func (m *CrewMember) Execute(ctx context.Context, task string) (string, error) {
	systemPrompt := fmt.Sprintf(
		"You are %s.\n\nRole: %s\nGoal: %s\nBackstory: %s\n\nComplete the task given to you concisely and professionally.",
		m.Name, m.Role, m.Goal, m.Backstory,
	)

	msgs := []*agenkit.Message{
		agenkit.NewMessage("system", systemPrompt),
		agenkit.NewMessage("user", task),
	}

	resp, err := m.LLMClient.Complete(ctx, msgs)
	if err != nil {
		if strings.Contains(err.Error(), "connection refused") ||
			strings.Contains(err.Error(), "no such host") {
			fmt.Printf("  [LLM not running — %s showing structure only]\n", m.Name)
			return fmt.Sprintf("[demo: %s — LLM not available]", m.Name), nil
		}
		return "", fmt.Errorf("%s failed to execute task: %w", m.Name, err)
	}

	return resp.ContentString(), nil
}

// ---------------------------------------------------------------------------
// Task — a unit of work assigned to a specific CrewMember
// ---------------------------------------------------------------------------

// Task describes a piece of work to be carried out by a single CrewMember.
// Equivalent to CrewAI's Task(description=…, expected_output=…, agent=…).
type Task struct {
	Description    string
	ExpectedOutput string
	Agent          *CrewMember
	Output         string // populated by Crew.Run after execution
}

// ---------------------------------------------------------------------------
// Crew — orchestrates members and tasks according to the chosen process
// ---------------------------------------------------------------------------

// Crew groups a set of CrewMembers and Tasks and drives their execution.
// Equivalent to CrewAI's Crew(agents=[…], tasks=[…], process=Process.sequential).
type Crew struct {
	Members []*CrewMember
	Tasks   []*Task
	Process ProcessType
}

// Run executes all tasks according to the crew's process type and returns
// the outputs in task order. For ProcessSequential each task is run in order;
// task outputs are collected but not automatically chained (agents work from
// the task description, not each other's raw output) unless the description
// explicitly references prior work — mirroring CrewAI's default behaviour.
func (c *Crew) Run(ctx context.Context) ([]string, error) {
	switch c.Process {
	case ProcessSequential:
		return c.runSequential(ctx)
	default:
		return c.runSequential(ctx)
	}
}

func (c *Crew) runSequential(ctx context.Context) ([]string, error) {
	outputs := make([]string, 0, len(c.Tasks))
	for i, task := range c.Tasks {
		fmt.Printf("\n  [crew] task %d/%d assigned to %s\n", i+1, len(c.Tasks), task.Agent.Name)
		out, err := task.Agent.Execute(ctx, task.Description)
		if err != nil {
			return nil, fmt.Errorf("task %d (%q) failed: %w", i+1, task.Description[:min(40, len(task.Description))], err)
		}
		task.Output = out
		outputs = append(outputs, out)
	}
	return outputs, nil
}

// min returns the smaller of a and b.
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
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

	// Single Ollama-backed LLM shared across all crew members.
	// In a real crew you might give each member a different model.
	ollamaLLM := llm.NewOpenAICompatibleLLM(
		"http://localhost:11434/v1",
		"llama3.2",
		"ollama",
		"", // no API key required for local servers
	)

	fmt.Println("MiniCrew — CrewAI patterns with Agenkit")
	fmt.Println("Mapping: CrewMember / Task / Crew / ProcessSequential")

	// ------------------------------------------------------------------
	// Define the crew — 3 members with distinct roles
	// ------------------------------------------------------------------
	printSection("Crew Definition")

	researcher := &CrewMember{
		Name:      "Alex",
		Role:      "Senior Research Analyst",
		Goal:      "Uncover cutting-edge developments in AI and provide accurate, well-researched findings",
		Backstory: "You are a seasoned researcher with a talent for synthesising complex information into clear insights. You have a background in computer science and data science.",
		LLMClient: ollamaLLM,
	}

	writer := &CrewMember{
		Name:      "Jordan",
		Role:      "Technical Content Writer",
		Goal:      "Craft compelling, accurate, and accessible technical articles that engage a broad audience",
		Backstory: "You are an experienced technical writer who bridges the gap between complex research and everyday readers. You excel at structuring information clearly.",
		LLMClient: ollamaLLM,
	}

	reviewer := &CrewMember{
		Name:      "Sam",
		Role:      "Editorial Reviewer",
		Goal:      "Ensure all published content is accurate, well-structured, and ready for a professional audience",
		Backstory: "You are a meticulous editor with deep technical knowledge. You catch errors, improve clarity, and ensure content meets the highest standards.",
		LLMClient: ollamaLLM,
	}

	fmt.Printf("Members : %s (%s), %s (%s), %s (%s)\n",
		researcher.Name, researcher.Role,
		writer.Name, writer.Role,
		reviewer.Name, reviewer.Role,
	)

	// ------------------------------------------------------------------
	// Define the tasks — one per crew member, in pipeline order
	// ------------------------------------------------------------------
	printSection("Task Pipeline  (ProcessSequential)")
	fmt.Println("CrewAI equivalent: Crew(agents=[…], tasks=[…], process=Process.sequential)")

	researchTask := &Task{
		Description:    "Research the latest developments in multi-agent AI systems. Identify the top 3 key trends, key players, and potential impact on software development. Provide a structured summary of your findings.",
		ExpectedOutput: "A structured research summary with 3 key trends, notable projects or organisations for each, and a brief impact assessment.",
		Agent:          researcher,
	}

	writingTask := &Task{
		Description:    "Using insights about multi-agent AI systems, write a short 3-paragraph article titled 'The Rise of Multi-Agent AI'. The article should be engaging, accurate, and suitable for a technical blog audience.",
		ExpectedOutput: "A polished 3-paragraph article with a clear introduction, body discussing key trends, and a forward-looking conclusion.",
		Agent:          writer,
	}

	reviewTask := &Task{
		Description:    "Review the draft article about multi-agent AI systems. Check for factual accuracy, clarity, and professional tone. Provide a brief review note and a final revised version of the article if changes are needed.",
		ExpectedOutput: "A short review note (2-3 sentences) followed by the final article, ready for publication.",
		Agent:          reviewer,
	}

	// ------------------------------------------------------------------
	// Assemble and run the crew
	// ------------------------------------------------------------------
	crew := &Crew{
		Members: []*CrewMember{researcher, writer, reviewer},
		Tasks:   []*Task{researchTask, writingTask, reviewTask},
		Process: ProcessSequential,
	}

	fmt.Printf("Process : %s\n", crew.Process)
	fmt.Printf("Tasks   : %d\n", len(crew.Tasks))

	outputs, err := crew.Run(ctx)
	if err != nil {
		fmt.Fprintf(os.Stderr, "crew run failed: %v\n", err)
		os.Exit(1)
	}

	// ------------------------------------------------------------------
	// Print results
	// ------------------------------------------------------------------
	taskLabels := []string{"Research findings", "Draft article", "Final review + article"}
	for i, out := range outputs {
		printSection(fmt.Sprintf("Output %d: %s  (by %s)", i+1, taskLabels[i], crew.Tasks[i].Agent.Name))
		fmt.Println(out)
	}

	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("MiniCrew demo complete.")
	fmt.Println()
	fmt.Println("Key takeaways:")
	fmt.Println("  CrewMember  → agenkit.Agent backed by llm.LLM with role/goal/backstory system prompt")
	fmt.Println("  Task        → structured work unit; .Output stores the result")
	fmt.Println("  Crew.Run    → sequential task dispatch, one agent per task")
	fmt.Println("  Process.*   → maps to patterns.SequentialAgent / parallel goroutines")
	fmt.Println()
	fmt.Println("For production use, compose with the native Agenkit pattern types:")
	fmt.Println("  patterns.NewSequentialAgent, patterns.NewRouterAgent — same concepts,")
	fmt.Println("  with built-in error handling and observability hooks.")
}
