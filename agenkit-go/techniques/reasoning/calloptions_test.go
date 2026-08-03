package reasoning

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// Every reasoning technique must advertise the options capability, or a wrapper
// such as SelfConsistency cannot vary the temperature through it. Asserted at
// compile time so adding a technique that forgets ProcessWith fails the build
// rather than silently dropping options at runtime (#801).
var (
	_ agenkit.OptionsAgent = (*ChainOfThought)(nil)
	_ agenkit.OptionsAgent = (*SelfConsistency)(nil)
	_ agenkit.OptionsAgent = (*TreeOfThought)(nil)
	_ agenkit.OptionsAgent = (*GraphOfThought)(nil)
	_ agenkit.OptionsAgent = (*LeastToMost)(nil)
	_ agenkit.OptionsAgent = (*PlanAndSolveAgent)(nil)
)

// recordingOptionsAgent is an OptionsAgent that records how each call arrived.
//
// It separates plainCalls from optionCalls because the failure being guarded
// against is a phase of a multi-phase technique that forgets to forward its
// options: that phase still produces a response, so only the entry path
// distinguishes it from a working one.
//
// Thread-safe — SelfConsistency and TreeOfThought both fan out over goroutines.
type recordingOptionsAgent struct {
	responses []string

	// responder, when set, answers by prompt instead of round-robin. Needed for
	// techniques whose later phases are gated on the shape of earlier answers —
	// a fixed response can drive them down a path that never reaches the phase
	// under test.
	responder func(prompt string) string

	mu          sync.Mutex
	calls       int
	plainCalls  int
	optionCalls int
	prompts     []string
	seen        []*agenkit.CallOptions
}

var _ agenkit.OptionsAgent = (*recordingOptionsAgent)(nil)

func newRecordingOptionsAgent(responses ...string) *recordingOptionsAgent {
	if len(responses) == 0 {
		responses = []string{"The answer is 42."}
	}
	return &recordingOptionsAgent{responses: responses}
}

func (a *recordingOptionsAgent) Name() string { return "recording_options_agent" }

func (a *recordingOptionsAgent) Capabilities() []string { return []string{"mock", "options"} }

func (a *recordingOptionsAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(a)
}

func (a *recordingOptionsAgent) nextResponse(prompt string) string {
	a.calls++
	a.prompts = append(a.prompts, prompt)
	if a.responder != nil {
		return a.responder(prompt)
	}
	return a.responses[(a.calls-1)%len(a.responses)]
}

func (a *recordingOptionsAgent) Process(
	ctx context.Context,
	message *agenkit.Message,
) (*agenkit.Message, error) {
	a.mu.Lock()
	a.plainCalls++
	a.seen = append(a.seen, nil)
	response := a.nextResponse(message.ContentString())
	a.mu.Unlock()
	return agenkit.NewMessage("assistant", response), nil
}

func (a *recordingOptionsAgent) ProcessWith(
	ctx context.Context,
	message *agenkit.Message,
	opts ...agenkit.CallOption,
) (*agenkit.Message, error) {
	a.mu.Lock()
	a.optionCalls++
	a.seen = append(a.seen, agenkit.BuildCallOptions(opts...))
	response := a.nextResponse(message.ContentString())
	a.mu.Unlock()
	return agenkit.NewMessage("assistant", response), nil
}

// sawPromptContaining reports whether any call carried a prompt with substr.
//
// Used to prove a gated phase was actually exercised. Several techniques skip
// later phases depending on what earlier ones returned, so a forwarding assertion
// over "every call" is vacuous for a phase that never ran.
func (a *recordingOptionsAgent) sawPromptContaining(substr string) bool {
	a.mu.Lock()
	defer a.mu.Unlock()
	for _, prompt := range a.prompts {
		if strings.Contains(prompt, substr) {
			return true
		}
	}
	return false
}

// counts returns the call tallies under the lock.
func (a *recordingOptionsAgent) counts() (plain, withOptions int) {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.plainCalls, a.optionCalls
}

// assertEveryCallCarriedTemperature fails unless every call went through
// ProcessWith with the given temperature set.
//
// "Every" is the point: a temperature that reaches only some of the LLM calls in
// a multi-phase technique is not the temperature the caller asked for.
func (a *recordingOptionsAgent) assertEveryCallCarriedTemperature(t *testing.T, want float64) {
	t.Helper()

	a.mu.Lock()
	defer a.mu.Unlock()

	if len(a.seen) == 0 {
		t.Fatal("the agent was never called; the test proves nothing")
	}
	for i, opts := range a.seen {
		if opts == nil {
			t.Errorf("call %d took the plain Process path; its options were dropped", i)
			continue
		}
		if opts.Temperature == nil {
			t.Errorf("call %d carried no temperature", i)
			continue
		}
		if *opts.Temperature != want {
			t.Errorf("call %d temperature = %v, want %v", i, *opts.Temperature, want)
		}
	}
}

// ============================================================================
// SelfConsistency — the technique whose WithTemperature was silently discarded
// ============================================================================

func TestSelfConsistencyForwardsTemperatureToEverySample(t *testing.T) {
	agent := newRecordingOptionsAgent("The answer is 42.")
	sc := NewSelfConsistency(agent, WithNumSamples(4), WithTemperature(0.9))

	if _, err := sc.Process(context.Background(), agenkit.NewMessage("user", "Q")); err != nil {
		t.Fatalf("Process: %v", err)
	}

	plain, withOptions := agent.counts()
	if plain != 0 || withOptions != 4 {
		t.Errorf("Process=%d ProcessWith=%d, want 0 and 4", plain, withOptions)
	}
	agent.assertEveryCallCarriedTemperature(t, 0.9)
}

func TestSelfConsistencyTemperatureZeroSurvivesAsSet(t *testing.T) {
	// 0.0 is greedy decoding — a real request, not "unset". A pointer-free
	// representation would make this case indistinguishable from no temperature
	// at all, which is exactly how the option got dropped.
	agent := newRecordingOptionsAgent("The answer is 42.")
	sc := NewSelfConsistency(agent, WithNumSamples(2), WithTemperature(0.0))

	response, err := sc.Process(context.Background(), agenkit.NewMessage("user", "Q"))
	if err != nil {
		t.Fatalf("Process: %v", err)
	}

	agent.assertEveryCallCarriedTemperature(t, 0.0)

	temperature, ok := response.Metadata["temperature"].(*float64)
	if !ok || temperature == nil {
		t.Fatalf("metadata temperature = %v, want a set *float64", response.Metadata["temperature"])
	}
	if *temperature != 0.0 {
		t.Errorf("metadata temperature = %v, want 0", *temperature)
	}
	if response.Metadata["temperature_applied"] != true {
		t.Errorf("temperature_applied = %v, want true", response.Metadata["temperature_applied"])
	}
}

func TestSelfConsistencyNoTemperatureMeansNoOptions(t *testing.T) {
	// An unset temperature must be omitted, not forwarded as zero: sampling at 0
	// would override whatever the wrapped agent was configured with, and would
	// destroy the very diversity this technique depends on.
	agent := newRecordingOptionsAgent("The answer is 42.")
	sc := NewSelfConsistency(agent, WithNumSamples(3))

	response, err := sc.Process(context.Background(), agenkit.NewMessage("user", "Q"))
	if err != nil {
		t.Fatalf("Process: %v", err)
	}

	plain, withOptions := agent.counts()
	if plain != 3 || withOptions != 0 {
		t.Errorf("Process=%d ProcessWith=%d, want 3 and 0", plain, withOptions)
	}
	if response.Metadata["temperature"] != (*float64)(nil) {
		t.Errorf("metadata temperature = %v, want nil", response.Metadata["temperature"])
	}
	// Nothing was requested, so nothing was dropped.
	if response.Metadata["temperature_applied"] != true {
		t.Errorf("temperature_applied = %v, want true", response.Metadata["temperature_applied"])
	}
}

func TestSelfConsistencyTemperatureAppliedFalseForPlainAgent(t *testing.T) {
	// The drop has to be visible. A plain Agent cannot honour a temperature, and
	// a caller that set one needs to be able to find that out — silently
	// accepting it is the bug (#801).
	sc := NewSelfConsistency(NewMockAgent([]string{"The answer is 42."}), WithTemperature(0.8))

	if sc.TemperatureApplied() {
		t.Error("TemperatureApplied() is true for a plain Agent, which cannot apply it")
	}

	response, err := sc.Process(context.Background(), agenkit.NewMessage("user", "Q"))
	if err != nil {
		t.Fatalf("Process: %v", err)
	}
	if response.Metadata["temperature_applied"] != false {
		t.Errorf("temperature_applied = %v, want false", response.Metadata["temperature_applied"])
	}
	// The requested value is still reported, so "asked for 0.8 and did not get
	// it" is distinguishable from "never asked".
	temperature, ok := response.Metadata["temperature"].(*float64)
	if !ok || temperature == nil || *temperature != 0.8 {
		t.Errorf("metadata temperature = %v, want 0.8", response.Metadata["temperature"])
	}
}

func TestSelfConsistencyTemperatureAppliedTrueWhenUnset(t *testing.T) {
	sc := NewSelfConsistency(NewMockAgent([]string{"42"}))
	if !sc.TemperatureApplied() {
		t.Error("TemperatureApplied() is false with no temperature set; nothing was dropped")
	}
}

func TestSelfConsistencyRejectsOutOfRangeTemperature(t *testing.T) {
	// Fail at construction, not on the first sample, and mirror
	// agenkit.WithTemperature so the two spellings cannot disagree.
	for _, temp := range []float64{-0.1, 2.1} {
		t.Run(fmt.Sprintf("%v", temp), func(t *testing.T) {
			defer func() {
				if recover() == nil {
					t.Errorf("WithTemperature(%v) did not panic", temp)
				}
			}()
			WithTemperature(temp)
		})
	}
}

func TestSelfConsistencyForwardsThroughAChainOfThought(t *testing.T) {
	// The realistic composition: SelfConsistency samples a ChainOfThought, which
	// owns no LLM and must pass the options down to the agent that does. A break
	// anywhere in that chain leaves the temperature unapplied.
	agent := newRecordingOptionsAgent("1. Think\n2. Conclude\nTherefore, 42")
	cot := NewChainOfThought(agent)
	sc := NewSelfConsistency(cot, WithNumSamples(3), WithTemperature(1.2))

	if !sc.TemperatureApplied() {
		t.Fatal("TemperatureApplied() is false, but ChainOfThought is an OptionsAgent")
	}
	if _, err := sc.Process(context.Background(), agenkit.NewMessage("user", "Q")); err != nil {
		t.Fatalf("Process: %v", err)
	}

	plain, withOptions := agent.counts()
	if plain != 0 || withOptions != 3 {
		t.Errorf("Process=%d ProcessWith=%d, want 0 and 3", plain, withOptions)
	}
	agent.assertEveryCallCarriedTemperature(t, 1.2)
}

// ============================================================================
// ProcessWith == Process when no options are passed
// ============================================================================

func TestChainOfThoughtProcessPassesNoOptions(t *testing.T) {
	agent := newRecordingOptionsAgent("1. Step\n2. Step\nTherefore, done")
	cot := NewChainOfThought(agent)

	if _, err := cot.Process(context.Background(), agenkit.NewMessage("user", "Q")); err != nil {
		t.Fatalf("Process: %v", err)
	}

	plain, withOptions := agent.counts()
	if plain != 1 || withOptions != 0 {
		t.Errorf("Process=%d ProcessWith=%d, want 1 and 0", plain, withOptions)
	}
}

// ============================================================================
// Multi-phase techniques — every phase, not just the first
// ============================================================================

func TestLeastToMostForwardsOptionsToEveryPhase(t *testing.T) {
	// Decomposition plus one call per subproblem. If only decompose forwards, the
	// subproblem solves run at the wrong temperature and nothing reports it.
	agent := newRecordingOptionsAgent(
		"1. Calculate 3*4\n2. Calculate 2*5\n3. Add the results",
		"12",
		"10",
		"22",
	)
	ltm := NewLeastToMost(agent)

	_, err := ltm.ProcessWith(
		context.Background(),
		agenkit.NewMessage("user", "Calculate 3*4 + 2*5"),
		agenkit.WithTemperature(0.5),
	)
	if err != nil {
		t.Fatalf("ProcessWith: %v", err)
	}

	plain, withOptions := agent.counts()
	if plain != 0 {
		t.Errorf("%d call(s) took the plain path; every phase must forward", plain)
	}
	if withOptions != 4 {
		t.Errorf("ProcessWith=%d, want 4 (decompose + 3 subproblems)", withOptions)
	}
	agent.assertEveryCallCarriedTemperature(t, 0.5)
}

func TestPlanAndSolveForwardsOptionsToEveryPhase(t *testing.T) {
	// Planning, validation and every step execution. Validation is the phase most
	// likely to be forgotten, since it is optional.
	agent := newRecordingOptionsAgent(
		"1. Gather ingredients\n2. Preheat oven",
		"VALID: Plan is complete",
		"Gathered: flour, sugar, eggs",
		"Preheated oven to 350°F",
	)
	pas := NewPlanAndSolveAgent(agent, PlanAndSolveConfig{ValidatePlan: true})

	_, err := pas.ProcessWith(
		context.Background(),
		agenkit.NewMessage("user", "How do I bake a cake?"),
		agenkit.WithTemperature(0.4),
	)
	if err != nil {
		t.Fatalf("ProcessWith: %v", err)
	}

	plain, withOptions := agent.counts()
	if plain != 0 {
		t.Errorf("%d call(s) took the plain path; every phase must forward", plain)
	}
	if withOptions != 4 {
		t.Errorf("ProcessWith=%d, want 4 (plan + validate + 2 steps)", withOptions)
	}
	agent.assertEveryCallCarriedTemperature(t, 0.4)
}

func TestPlanAndSolveForwardsOptionsThroughReplanning(t *testing.T) {
	// The replanning branch adds three more LLM calls and only runs when
	// validation rejects the plan, so the happy-path test above never reaches it.
	// A dropped forward in a branch no test enters is invisible.
	agent := &recordingOptionsAgent{responder: func(prompt string) string {
		switch {
		case strings.Contains(prompt, "Previous Plan Issues"):
			return "1. A better first step\n2. A better second step"
		case strings.Contains(prompt, "completeness and feasibility"):
			// Neither "VALID" nor "YES" — rejecting the plan is what triggers
			// replanning.
			return "This plan is missing error handling."
		case strings.Contains(prompt, "step-by-step plan"):
			return "1. Gather ingredients\n2. Preheat oven"
		default:
			return "Step done."
		}
	}}
	pas := NewPlanAndSolveAgent(agent, PlanAndSolveConfig{
		ValidatePlan:    true,
		AllowReplanning: true,
	})

	_, err := pas.ProcessWith(
		context.Background(),
		agenkit.NewMessage("user", "How do I bake a cake?"),
		agenkit.WithTemperature(0.3),
	)
	if err != nil {
		t.Fatalf("ProcessWith: %v", err)
	}

	if plain, _ := agent.counts(); plain != 0 {
		t.Errorf("%d call(s) took the plain path; the replanning branch must forward too", plain)
	}
	if !agent.sawPromptContaining("Previous Plan Issues") {
		t.Fatal("replanning never ran; the branch under test was not entered")
	}
	agent.assertEveryCallCarriedTemperature(t, 0.3)
}

func TestTreeOfThoughtForwardsOptionsToEveryBranch(t *testing.T) {
	// Branch diversity is the whole point of the technique, so a temperature that
	// reaches only some branches defeats it.
	//
	// The branch text has to survive the default evaluator's 0.3 prune threshold,
	// which scores anything under 50 characters at 0.2. A short response gets every
	// depth-1 branch pruned, so only the root is ever expanded and the recursive
	// expansion — where a dropped forward would actually hide — goes untested.
	//
	// All three strategies are exercised: each drives expandNode from its own
	// loop, so forwarding fixed in one says nothing about the other two.
	for _, strategy := range []SearchStrategy{
		SearchStrategyBFS,
		SearchStrategyDFS,
		SearchStrategyBestFirst,
	} {
		t.Run(string(strategy), func(t *testing.T) {
			agent := newRecordingOptionsAgent(
				"1. Decompose the problem into independent parts and examine each in turn. " +
					"2. Recombine the partial results. Therefore, 42")
			tot := NewTreeOfThought(
				agent,
				WithStrategy(strategy),
				WithBranchingFactor(2),
				WithMaxDepth(2),
			)

			_, err := tot.ProcessWith(
				context.Background(),
				agenkit.NewMessage("user", "Q"),
				agenkit.WithTemperature(1.1),
			)
			if err != nil {
				t.Fatalf("ProcessWith: %v", err)
			}

			plain, withOptions := agent.counts()
			if plain != 0 {
				t.Errorf("%d branch generation(s) took the plain path", plain)
			}
			// branchingFactor 2 at maxDepth 2 means the root plus its two surviving
			// children are each expanded: 2 + 2 + 2 calls. Asserting the count, not
			// just "more than zero", is what proves the recursion ran rather than
			// the root alone.
			if withOptions != 6 {
				t.Errorf("ProcessWith=%d, want 6 (root + 2 children, 2 branches each)", withOptions)
			}
			// Only an expansion below the root carries the reasoning-so-far preamble.
			if !agent.sawPromptContaining("Reasoning so far") {
				t.Error("no node below the root was expanded; the recursive path went untested")
			}
			agent.assertEveryCallCarriedTemperature(t, 1.1)
		})
	}
}

func TestGraphOfThoughtForwardsOptionsToEveryCall(t *testing.T) {
	// Premises, thought expansion, edge identification and the conclusion. The
	// conclusion phase is gated on the graph not having hit maxNodes, so the mock
	// answers by prompt: a fixed response fills the graph to the cap and that
	// phase never runs, leaving a dropped forward there invisible.
	agent := &recordingOptionsAgent{responder: func(prompt string) string {
		switch {
		case strings.Contains(prompt, "premises"):
			return "1. First premise\n2. Second premise"
		case strings.Contains(prompt, "new insights"), strings.Contains(prompt, "initial thoughts"):
			// Empty breaks the expansion loop, leaving room under maxNodes for
			// the conclusion call.
			return ""
		case strings.Contains(prompt, "logical relationship"):
			return "SUPPORTS"
		default:
			return "Therefore, 42"
		}
	}}
	got := NewGraphOfThought(agent)

	_, err := got.ProcessWith(
		context.Background(),
		agenkit.NewMessage("user", "Q"),
		agenkit.WithTemperature(0.6),
	)
	if err != nil {
		t.Fatalf("ProcessWith: %v", err)
	}

	plain, withOptions := agent.counts()
	if plain != 0 {
		t.Errorf("%d call(s) took the plain path; every graph-build call must forward", plain)
	}
	if withOptions == 0 {
		t.Fatal("the agent was never called; the test proves nothing")
	}
	// Each gated phase must have actually run, or the assertion below is vacuous
	// for it.
	for _, phase := range []string{"premises", "final conclusion"} {
		if !agent.sawPromptContaining(phase) {
			t.Errorf("the %q phase never ran; a dropped forward there would go unnoticed", phase)
		}
	}
	agent.assertEveryCallCarriedTemperature(t, 0.6)
}
