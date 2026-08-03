/**
 * Per-call inference options.
 *
 * The channel a caller uses to influence *how* one call runs, as opposed to
 * `Message`, which carries *what* the call is about. It exists because wrappers
 * need to vary inference settings per invocation of an agent they did not
 * construct: `SelfConsistencyAgent` samples the same prompt N times and takes a
 * majority vote, so sample diversity *is* the technique, and temperature is the
 * knob that produces it (#801).
 */

import { Agent, Message } from './interfaces.js';

/**
 * Per-call inference options for a single agent invocation.
 *
 * Passed via the optional {@link Agent.processWith} capability rather than by
 * widening `process()`. Agents that do not implement it fall back to `process()`
 * and ignore the options, so nothing breaks — but a caller can check with
 * {@link supportsOptions} when it needs to know.
 *
 * Every field is optional and `undefined` means "unset", not a default. This is
 * the difference that matters: an agent must be able to tell "the caller did not
 * ask for a temperature" from "the caller asked for 0". Sending a defaulted value
 * downstream would silently override whatever the agent or provider was
 * configured with.
 *
 * Bounds match `validateLLMParams`, so options pass through to a provider
 * without translation. Names are camelCase per TypeScript convention — the
 * snake_case in `LLMParams` is the wire format, and adapters translate at that
 * boundary rather than leaking it into the public API.
 *
 * Usage:
 * ```typescript
 * const response = await processWithOptions(agent, message, { temperature: 0.9 });
 * ```
 */
export interface CallOptions {
  /** Sampling temperature, 0-2. Higher is more random. */
  temperature?: number;

  /** Maximum tokens to generate. Must be positive. */
  maxTokens?: number;

  /** Nucleus sampling probability mass, 0-1. */
  topP?: number;

  /** Provider-side sampling seed, for reproducible sampling where supported. */
  seed?: number;

  /** Sequences that end generation. */
  stop?: string[];

  /**
   * Provider-specific options with no cross-provider meaning.
   *
   * Kept separate from the named fields so a typo in a portable option is a
   * compile error rather than a silently ignored key.
   */
  extra?: Record<string, unknown>;
}

/**
 * Validate options, throwing on any value outside its documented range.
 *
 * Validated at the call site that set the value, where the fix is, instead of
 * several layers down at the provider.
 *
 * @param options Options to validate
 * @throws Error if any option is outside its documented range
 */
export function validateCallOptions(options: CallOptions): void {
  if (options.temperature !== undefined) {
    if (
      typeof options.temperature !== 'number' ||
      Number.isNaN(options.temperature) ||
      options.temperature < 0 ||
      options.temperature > 2
    ) {
      throw new Error(`temperature must be between 0 and 2, got ${options.temperature}`);
    }
  }

  if (options.maxTokens !== undefined) {
    if (
      typeof options.maxTokens !== 'number' ||
      !Number.isInteger(options.maxTokens) ||
      options.maxTokens <= 0
    ) {
      throw new Error(`maxTokens must be a positive integer, got ${options.maxTokens}`);
    }
  }

  if (options.topP !== undefined) {
    if (
      typeof options.topP !== 'number' ||
      Number.isNaN(options.topP) ||
      options.topP < 0 ||
      options.topP > 1
    ) {
      throw new Error(`topP must be between 0 and 1, got ${options.topP}`);
    }
  }

  if (options.seed !== undefined) {
    if (typeof options.seed !== 'number' || !Number.isInteger(options.seed)) {
      throw new Error(`seed must be an integer, got ${options.seed}`);
    }
  }
}

/**
 * Report whether no option is set.
 *
 * Lets a caller skip the `processWith` path entirely when it has nothing to say,
 * rather than handing an agent an options object in which everything is
 * `undefined`. An empty options set is indistinguishable from not asking.
 *
 * @param options Options to inspect, or undefined
 * @returns True if no option is set
 */
export function isCallOptionsEmpty(options?: CallOptions): boolean {
  if (!options) {
    return true;
  }
  return (
    options.temperature === undefined &&
    options.maxTokens === undefined &&
    options.topP === undefined &&
    options.seed === undefined &&
    options.stop === undefined &&
    (options.extra === undefined || Object.keys(options.extra).length === 0)
  );
}

/**
 * Render options as `LLMParams`, the snake_case shape adapters accept.
 *
 * Unset fields are omitted rather than emitted as `undefined`, so an option the
 * caller never set cannot override the adapter's or provider's own default.
 * `seed`, `stop` and `extra` have no named `LLMParams` field and are passed
 * through by key.
 *
 * @param options Options to render
 * @returns Only the options that were set
 */
export function callOptionsToParams(options?: CallOptions): Record<string, unknown> {
  const params: Record<string, unknown> = {};
  if (!options) {
    return params;
  }

  if (options.temperature !== undefined) {
    params.temperature = options.temperature;
  }
  if (options.maxTokens !== undefined) {
    params.max_tokens = options.maxTokens;
  }
  if (options.topP !== undefined) {
    params.top_p = options.topP;
  }
  if (options.seed !== undefined) {
    params.seed = options.seed;
  }
  if (options.stop !== undefined) {
    params.stop = [...options.stop];
  }
  if (options.extra) {
    Object.assign(params, options.extra);
  }

  return params;
}

/**
 * Merge two option sets, with `override` winning field by field.
 *
 * Only fields actually set in `override` win: a field left `undefined` there
 * must not erase the same field in `base`, because `undefined` means "did not
 * ask", not "clear it".
 *
 * @param base Options to start from
 * @param override Options that take precedence where set
 * @returns A new merged options object
 */
export function mergeCallOptions(base?: CallOptions, override?: CallOptions): CallOptions {
  const merged: CallOptions = { ...base };

  if (!override) {
    return merged;
  }

  if (override.temperature !== undefined) {
    merged.temperature = override.temperature;
  }
  if (override.maxTokens !== undefined) {
    merged.maxTokens = override.maxTokens;
  }
  if (override.topP !== undefined) {
    merged.topP = override.topP;
  }
  if (override.seed !== undefined) {
    merged.seed = override.seed;
  }
  if (override.stop !== undefined) {
    merged.stop = [...override.stop];
  }
  if (override.extra) {
    merged.extra = { ...base?.extra, ...override.extra };
  }

  return merged;
}

/**
 * Report whether an agent honours per-call options.
 *
 * A caller that needs its options to actually take effect should check this
 * rather than assume, since an agent without `processWith` has no way to apply
 * them. Exposed as a helper so the check is spelled one way everywhere.
 *
 * @param agent Agent to inspect
 * @returns True if the agent implements the optional processWith capability
 */
export function supportsOptions(agent: Agent): boolean {
  return typeof agent.processWith === 'function';
}

/**
 * Forward a message to an agent, applying options if it can honour them.
 *
 * The single place that resolves "can this agent take options", so the pattern
 * is not re-derived at each wrapper call site in `techniques/reasoning`. When
 * the agent has no `processWith` the options are dropped — deliberately, since
 * there is nowhere to put them — so a caller that needs to know whether that
 * happened must check {@link supportsOptions} first. That is exactly why
 * `SelfConsistencyAgent` exposes a `temperatureApplied` accessor (#801).
 *
 * Passing no options, or an options object with nothing set, skips the
 * capability check entirely: an empty options set is indistinguishable from not
 * asking, and an agent should not be handed one just because this helper was
 * used.
 *
 * @param agent Agent to call
 * @param message Message to process
 * @param options Optional per-call options
 * @returns The agent's response
 */
export async function processWithOptions(
  agent: Agent,
  message: Message,
  options?: CallOptions,
): Promise<Message> {
  if (isCallOptionsEmpty(options) || !agent.processWith) {
    return agent.process(message);
  }
  return agent.processWith(message, options as CallOptions);
}
