package patterns

import (
	"sort"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// Compile-time proof that every pattern in this package satisfies agenkit.Agent.
//
// These assertions exist because their absence was the bug: a2b79a2d added
// Introspect() to the Agent interface and implemented it in composition/ and
// middleware/, but not here. Nothing in the package requires conformance, so
// patterns/ kept compiling while none of these types could be passed to
// middleware.NewRetryDecorator or nested inside a composition/ agent — the
// toolkit's central promise, broken at every call site (#847).
//
// Keep one line per agent-shaped type. A future addition to the Agent interface
// then fails the build here, in the package that owns the types, rather than in
// some downstream example nobody compiles.
var (
	_ agenkit.Agent = (*AutonomousAgent)(nil)
	_ agenkit.Agent = (*CollaborativeAgent)(nil)
	_ agenkit.Agent = (*ConsensusAgent)(nil)
	_ agenkit.Agent = (*ConversationalAgent)(nil)
	_ agenkit.Agent = (*FallbackAgent)(nil)
	_ agenkit.Agent = (*HumanInLoopAgent)(nil)
	_ agenkit.Agent = (*MultiAgentOrchestrator)(nil)
	_ agenkit.Agent = (*ParallelAgent)(nil)
	_ agenkit.Agent = (*ParallelPattern)(nil)
	_ agenkit.Agent = (*PlanningAgent)(nil)
	_ agenkit.Agent = (*ReActAgent)(nil)
	_ agenkit.Agent = (*ReasoningWithToolsAgent)(nil)
	_ agenkit.Agent = (*RecoveryAgent)(nil)
	_ agenkit.Agent = (*ReflectionAgent)(nil)
	_ agenkit.Agent = (*RouterAgent)(nil)
	_ agenkit.Agent = (*RouterPattern)(nil)
	_ agenkit.Agent = (*SequentialAgent)(nil)
	_ agenkit.Agent = (*SequentialPattern)(nil)
	_ agenkit.Agent = (*SupervisorAgent)(nil)
)

// agentNames returns the names of the given agents, in slice order.
//
// Used by the multi-agent patterns to describe their composition in
// IntrospectionResult.InternalState, matching the "agent_count"/"agent_names"
// shape that composition/sequential.go established.
func agentNames(agents []agenkit.Agent) []string {
	names := make([]string, len(agents))
	for i, agent := range agents {
		names[i] = agent.Name()
	}
	return names
}

// agentNamesFromMap returns the names of the given agents sorted by key, so that
// introspecting a map-backed agent set twice yields the same order. Go map
// iteration is deliberately random; an unstable list here would make two
// introspection snapshots of an unchanged agent compare as different.
func agentNamesFromMap(agents map[string]agenkit.Agent) []string {
	keys := make([]string, 0, len(agents))
	for key := range agents {
		keys = append(keys, key)
	}
	sort.Strings(keys)

	names := make([]string, 0, len(keys))
	for _, key := range keys {
		names = append(names, agents[key].Name())
	}
	return names
}
