/**
 * Tests that per-call options reach every LLM call in every reasoning technique (#801).
 *
 * The failure being guarded against is not an exception — it is a phase of a
 * multi-phase technique that forgets to forward its options. That phase still
 * produces a response, so only the entry path distinguishes it from a working
 * one, and only an assertion that the phase actually ran keeps the forwarding
 * assertion from being vacuous.
 */

import { describe, it, expect } from 'vitest';
import { Agent, Message, createMessage } from '../../core/interfaces';
import { CallOptions, supportsOptions } from '../../core/call-options';
import { ChainOfThought } from './chain-of-thought';
import { SelfConsistencyAgent } from './self-consistency';
import { TreeOfThought, type SearchStrategy } from './tree-of-thought';
import { GraphOfThought } from './graph-of-thought';
import { LeastToMost } from './least-to-most';
import { PlanAndSolve } from './plan-and-solve';

/**
 * An agent that records how each call arrived and what it carried.
 *
 * `responder` answers by prompt rather than round-robin, which several
 * techniques need: their later phases are gated on the shape of earlier answers,
 * and a fixed response can drive them down a path that never reaches the phase
 * under test.
 */
class RecordingAgent implements Agent {
  readonly name = 'recording_agent';
  readonly capabilities = ['mock', 'options'];

  plainCalls = 0;
  optionCalls = 0;
  prompts: string[] = [];
  /** One entry per call: the options it carried, or undefined for the plain path. */
  seen: (CallOptions | undefined)[] = [];

  constructor(private readonly responder: (prompt: string) => string = () => 'The answer is 42.') {}

  async process(message: Message): Promise<Message> {
    this.plainCalls += 1;
    this.seen.push(undefined);
    return this.answer(message);
  }

  async processWith(message: Message, options: CallOptions): Promise<Message> {
    this.optionCalls += 1;
    this.seen.push(options);
    return this.answer(message);
  }

  private answer(message: Message): Message {
    const prompt = String(message.content);
    this.prompts.push(prompt);
    return createMessage('assistant', this.responder(prompt));
  }

  /**
   * Whether any call carried a prompt containing `substr`.
   *
   * Used to prove a gated phase was actually exercised.
   */
  sawPromptContaining(substr: string): boolean {
    return this.prompts.some((prompt) => prompt.includes(substr));
  }
}

/**
 * Assert every call went through processWith with the given temperature set.
 *
 * "Every" is the point: a temperature that reaches only some of the LLM calls in
 * a multi-phase technique is not the temperature the caller asked for.
 */
function expectEveryCallCarriedTemperature(agent: RecordingAgent, want: number): void {
  expect(agent.seen.length, 'the agent was never called; the test proves nothing').toBeGreaterThan(
    0,
  );
  expect(agent.plainCalls, 'some call took the plain path and dropped its options').toBe(0);
  expect(agent.seen.map((options) => options?.temperature)).toEqual(agent.seen.map(() => want));
}

// A reasoning technique that cannot take options cannot be driven by a wrapper
// such as SelfConsistencyAgent. Checked for all six so adding one that forgets
// processWith fails here rather than silently dropping options at runtime.
describe('every reasoning technique advertises the options capability', () => {
  const plain: Agent = { name: 'p', process: async () => createMessage('assistant', 'x') };

  it.each([
    ['ChainOfThought', new ChainOfThought(plain)],
    ['SelfConsistencyAgent', new SelfConsistencyAgent(plain)],
    ['TreeOfThought', new TreeOfThought(plain)],
    ['GraphOfThought', new GraphOfThought(plain)],
    ['LeastToMost', new LeastToMost(plain)],
    ['PlanAndSolve', new PlanAndSolve(plain)],
  ] as [string, Agent][])('%s implements processWith', (_name, technique) => {
    expect(supportsOptions(technique)).toBe(true);
  });
});

// ============================================================================
// SelfConsistency — the technique whose temperature config was silently discarded
// ============================================================================

describe('SelfConsistencyAgent temperature', () => {
  it('forwards the configured temperature to every sample', async () => {
    const agent = new RecordingAgent();
    const sc = new SelfConsistencyAgent(agent, { numSamples: 4, temperature: 0.9 });

    await sc.process(createMessage('user', 'Q'));

    expect(agent.optionCalls).toBe(4);
    expectEveryCallCarriedTemperature(agent, 0.9);
  });

  it('treats a temperature of 0 as set', async () => {
    // 0 is greedy decoding — a real request, not "unset". Any representation that
    // conflates the two is how the option got dropped in the first place.
    const agent = new RecordingAgent();
    const sc = new SelfConsistencyAgent(agent, { numSamples: 2, temperature: 0 });

    const response = await sc.process(createMessage('user', 'Q'));

    expectEveryCallCarriedTemperature(agent, 0);
    expect(response.metadata?.temperature).toBe(0);
    expect(response.metadata?.temperature_applied).toBe(true);
  });

  it('sends no options at all when no temperature is configured', async () => {
    // An unset temperature must be omitted, not forwarded as zero: sampling at 0
    // would override whatever the wrapped agent was configured with, and would
    // destroy the very diversity this technique depends on.
    const agent = new RecordingAgent();
    const sc = new SelfConsistencyAgent(agent, { numSamples: 3 });

    const response = await sc.process(createMessage('user', 'Q'));

    expect(agent.plainCalls).toBe(3);
    expect(agent.optionCalls).toBe(0);
    expect(response.metadata?.temperature).toBeUndefined();
    // Nothing was requested, so nothing was dropped.
    expect(response.metadata?.temperature_applied).toBe(true);
  });

  it('reports temperatureApplied false for an agent that cannot honour it', async () => {
    // The drop has to be visible. An agent without processWith cannot honour a
    // temperature, and a caller that set one needs to be able to find that out —
    // silently accepting it is the bug.
    const plain: Agent = { name: 'p', process: async () => createMessage('assistant', '42') };
    const sc = new SelfConsistencyAgent(plain, { numSamples: 2, temperature: 0.8 });

    expect(sc.temperatureApplied()).toBe(false);

    const response = await sc.process(createMessage('user', 'Q'));

    expect(response.metadata?.temperature_applied).toBe(false);
    // The requested value is still reported, so "asked for 0.8 and did not get it"
    // is distinguishable from "never asked".
    expect(response.metadata?.temperature).toBe(0.8);
  });

  it('reports temperatureApplied true when no temperature is set', () => {
    const plain: Agent = { name: 'p', process: async () => createMessage('assistant', '42') };
    expect(new SelfConsistencyAgent(plain).temperatureApplied()).toBe(true);
  });

  it.each([-0.1, 2.1])(
    'rejects an out-of-range temperature of %s at construction',
    (temperature) => {
      // Fail where the value was set, not on the first sample.
      const plain: Agent = { name: 'p', process: async () => createMessage('assistant', '42') };
      expect(() => new SelfConsistencyAgent(plain, { temperature })).toThrow(
        /temperature must be between 0 and 2/,
      );
    },
  );

  it("overrides a caller's temperature with its own", async () => {
    // Deliberate: this technique's correctness depends on sampling diversity, so a
    // caller reaching through it must not silently flatten the samples.
    const agent = new RecordingAgent();
    const sc = new SelfConsistencyAgent(agent, { numSamples: 2, temperature: 1.1 });

    await sc.processWith(createMessage('user', 'Q'), { temperature: 0, maxTokens: 64 });

    expectEveryCallCarriedTemperature(agent, 1.1);
    // Every other option passes through untouched.
    expect(agent.seen.map((o) => o?.maxTokens)).toEqual([64, 64]);
  });

  it('keeps its own temperature when the caller passes an explicit undefined', async () => {
    // `{ temperature: undefined }` is the shape a caller forwarding an optional
    // variable produces. It must read as "did not ask", not as a request to clear
    // the configured value.
    const agent = new RecordingAgent();
    const sc = new SelfConsistencyAgent(agent, { numSamples: 2, temperature: 0.7 });

    await sc.processWith(createMessage('user', 'Q'), { temperature: undefined });

    expectEveryCallCarriedTemperature(agent, 0.7);
  });

  it('forwards through a ChainOfThought', async () => {
    // The realistic composition: SelfConsistency samples a ChainOfThought, which
    // owns no LLM and must pass the options down to the agent that does. A break
    // anywhere in that chain leaves the temperature unapplied.
    const agent = new RecordingAgent(() => '1. Think\n2. Conclude\nTherefore, 42');
    const sc = new SelfConsistencyAgent(new ChainOfThought(agent), {
      numSamples: 3,
      temperature: 1.2,
    });

    expect(sc.temperatureApplied()).toBe(true);
    await sc.process(createMessage('user', 'Q'));

    expect(agent.optionCalls).toBe(3);
    expectEveryCallCarriedTemperature(agent, 1.2);
  });
});

// ============================================================================
// process() must not manufacture options
// ============================================================================

describe('process() passes no options', () => {
  it('leaves ChainOfThought on the plain path', async () => {
    const agent = new RecordingAgent(() => '1. Step\n2. Step\nTherefore, done');
    await new ChainOfThought(agent).process(createMessage('user', 'Q'));

    expect(agent.plainCalls).toBe(1);
    expect(agent.optionCalls).toBe(0);
  });
});

// ============================================================================
// Multi-phase techniques — every phase, not just the first
// ============================================================================

describe('LeastToMost', () => {
  it('forwards options to decomposition and every subproblem', async () => {
    // If only decompose forwards, the subproblem solves run at the wrong
    // temperature and nothing reports it.
    const responses = ['1. Calculate 3*4\n2. Calculate 2*5\n3. Add the results', '12', '10', '22'];
    let i = 0;
    const agent = new RecordingAgent(() => responses[Math.min(i++, responses.length - 1)]);

    await new LeastToMost(agent).processWith(createMessage('user', 'Calculate 3*4 + 2*5'), {
      temperature: 0.5,
    });

    // Decompose plus one call per subproblem.
    expect(agent.optionCalls).toBe(4);
    expect(agent.sawPromptContaining('Solve this subproblem')).toBe(true);
    expectEveryCallCarriedTemperature(agent, 0.5);
  });
});

describe('PlanAndSolve', () => {
  it('forwards options to planning, validation and every step', async () => {
    // Validation is the phase most likely to be forgotten, since it is optional.
    const agent = new RecordingAgent((prompt) => {
      if (prompt.includes('completeness and feasibility')) return 'VALID: Plan is complete';
      if (prompt.includes('step-by-step plan')) return '1. Gather ingredients\n2. Preheat oven';
      return 'Step done.';
    });

    await new PlanAndSolve(agent, { validatePlan: true }).processWith(
      createMessage('user', 'How do I bake a cake?'),
      { temperature: 0.4 },
    );

    // Plan + validate + 2 steps.
    expect(agent.optionCalls).toBe(4);
    expect(agent.sawPromptContaining('completeness and feasibility')).toBe(true);
    expectEveryCallCarriedTemperature(agent, 0.4);
  });

  it('forwards options through the replanning branch', async () => {
    // The replanning branch adds three more LLM calls and only runs when
    // validation rejects the plan, so the happy-path test above never reaches it.
    // A dropped forward in a branch no test enters is invisible.
    const agent = new RecordingAgent((prompt) => {
      if (prompt.includes('Previous Plan Issues')) {
        return '1. A better first step\n2. A better second step';
      }
      // Neither "VALID" nor "YES" — rejecting the plan is what triggers replanning.
      if (prompt.includes('completeness and feasibility')) {
        return 'This plan is missing error handling.';
      }
      if (prompt.includes('step-by-step plan')) return '1. Gather ingredients\n2. Preheat oven';
      return 'Step done.';
    });

    await new PlanAndSolve(agent, { validatePlan: true, allowReplanning: true }).processWith(
      createMessage('user', 'How do I bake a cake?'),
      { temperature: 0.3 },
    );

    expect(
      agent.sawPromptContaining('Previous Plan Issues'),
      'replanning never ran; the branch under test was not entered',
    ).toBe(true);
    expectEveryCallCarriedTemperature(agent, 0.3);
  });
});

describe('TreeOfThought', () => {
  // Branch diversity is the whole point of the technique, so a temperature that
  // reaches only some branches defeats it.
  //
  // The branch text has to survive the default evaluator's 0.3 prune threshold,
  // which scores anything under 50 characters at 0.2. A short response gets every
  // depth-1 branch pruned, so only the root is ever expanded and the recursive
  // expansion — where a dropped forward would actually hide — goes untested.
  //
  // All three strategies are exercised: each drives expandNode from its own loop,
  // so forwarding fixed in one says nothing about the other two.
  const longEnoughToSurvivePruning =
    '1. Decompose the problem into independent parts and examine each in turn. ' +
    '2. Recombine the partial results. Therefore, 42';

  it.each(['bfs', 'dfs', 'best-first'] as SearchStrategy[])(
    'forwards options to every branch under %s search',
    async (strategy) => {
      const agent = new RecordingAgent(() => longEnoughToSurvivePruning);
      const tot = new TreeOfThought(agent, { strategy, branchingFactor: 2, maxDepth: 2 });

      await tot.processWith(createMessage('user', 'Q'), { temperature: 1.1 });

      // branchingFactor 2 at maxDepth 2 means the root plus its two surviving
      // children are each expanded: 2 + 2 + 2 calls. Asserting the count, not just
      // "more than zero", is what proves the recursion ran rather than the root
      // alone.
      expect(agent.optionCalls).toBe(6);
      // Only an expansion below the root carries the reasoning-so-far preamble.
      expect(
        agent.sawPromptContaining('Reasoning so far'),
        'no node below the root was expanded; the recursive path went untested',
      ).toBe(true);
      expectEveryCallCarriedTemperature(agent, 1.1);
    },
  );
});

describe('GraphOfThought', () => {
  it('forwards options to every call in the graph build', async () => {
    // Premises, thought expansion, edge identification and the conclusion. The
    // conclusion phase is gated on the graph not having hit maxNodes, so the mock
    // answers by prompt: a fixed response fills the graph to the cap and that
    // phase never runs, leaving a dropped forward there invisible.
    const agent = new RecordingAgent((prompt) => {
      if (prompt.includes('premises')) return '1. First premise\n2. Second premise';
      // Empty breaks the expansion loop, leaving room under maxNodes for the
      // conclusion call.
      if (prompt.includes('new insights') || prompt.includes('initial thoughts')) return '';
      if (prompt.includes('logical relationship')) return 'SUPPORTS';
      return 'Therefore, 42';
    });

    await new GraphOfThought(agent).processWith(createMessage('user', 'Q'), { temperature: 0.6 });

    // Each gated phase must have actually run, or the assertion below is vacuous
    // for it.
    for (const phase of ['premises', 'new insights', 'logical relationship', 'Final conclusion']) {
      expect(
        agent.sawPromptContaining(phase),
        `the ${phase} phase never ran; a dropped forward there would go unnoticed`,
      ).toBe(true);
    }
    expectEveryCallCarriedTemperature(agent, 0.6);
  });
});
