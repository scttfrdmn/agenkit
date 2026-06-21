/**
 * Typed token usage for LLM adapter responses.
 *
 * Adapters record token counts in `Message.metadata`, but the shape varies:
 * some use a nested `usage` object (`src/adapters/*`), some place counts as
 * flat top-level keys (`src/llm/*`), and key names differ between the
 * `prompt_tokens`/`completion_tokens` and Anthropic `input_tokens`/`output_tokens`
 * conventions. `usageFromMessage` normalizes all of these into one struct so
 * cost-metering and budgeting layers consume a single shape.
 *
 * Mirrors the Go reference (`agenkit-go/adapter/llm/usage.go`).
 */

import { Message } from '../core/interfaces';

/**
 * Normalized, typed token usage. Fields are 0 when the provider does not
 * report them. The cache fields are provider-dependent (e.g. Anthropic prompt
 * caching, including via Bedrock) and are 0 when caching is inactive.
 */
export interface Usage {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  /** Prompt tokens served from a provider cache (billed at a reduced rate). */
  cacheReadTokens: number;
  /** Prompt tokens written to a provider cache on this request. */
  cacheCreationTokens: number;
}

/**
 * Optional interface an adapter (or a wrapper around one) may implement so
 * consumers can detect typed-usage support at compile time. The core LLM/Agent
 * contract stays unchanged; usage support is additive.
 */
export interface UsageReporter {
  /** Returns the most recent token usage, or undefined if unavailable. */
  usage(): Usage | undefined;
}

/** Coerce an unknown numeric metadata value to a number; 0 when not numeric. */
function toNum(v: unknown): number {
  return typeof v === 'number' && Number.isFinite(v) ? v : 0;
}

/**
 * Extract normalized token usage from an adapter response message.
 *
 * Reads either a nested `metadata.usage` object or flat top-level `metadata`
 * token keys, normalizing both naming conventions:
 *   - prompt_tokens / completion_tokens (OpenAI, Bedrock, Gemini, Ollama, LiteLLM)
 *   - input_tokens / output_tokens      (Anthropic)
 * and the cache keys (cache_read_tokens / cache_creation_tokens, plus the raw
 * provider aliases cache_read_input_tokens / cache_creation_input_tokens).
 *
 * @returns the Usage and `true`, or `[zeroUsage, false]` when no usage is present.
 */
export function usageFromMessage(message: Message | null | undefined): [Usage, boolean] {
  const zero: Usage = {
    promptTokens: 0,
    completionTokens: 0,
    totalTokens: 0,
    cacheReadTokens: 0,
    cacheCreationTokens: 0,
  };

  const metadata = message?.metadata;
  if (!metadata || typeof metadata !== 'object') {
    return [zero, false];
  }

  // Counts may live under metadata.usage (nested) or directly on metadata (flat).
  const nested = (metadata as Record<string, unknown>).usage;
  const source =
    nested && typeof nested === 'object'
      ? (nested as Record<string, unknown>)
      : (metadata as Record<string, unknown>);

  // Detect presence of any recognized token key before reporting ok=true.
  const tokenKeys = [
    'prompt_tokens',
    'input_tokens',
    'completion_tokens',
    'output_tokens',
    'total_tokens',
  ];
  const hasUsage = tokenKeys.some((k) => k in source);
  if (!hasUsage) {
    return [zero, false];
  }

  const pick = (...keys: string[]): number => {
    for (const k of keys) {
      if (k in source) return toNum(source[k]);
    }
    return 0;
  };

  const usage: Usage = {
    promptTokens: pick('prompt_tokens', 'input_tokens'),
    completionTokens: pick('completion_tokens', 'output_tokens'),
    totalTokens: pick('total_tokens'),
    cacheReadTokens: pick('cache_read_tokens', 'cache_read_input_tokens'),
    cacheCreationTokens: pick(
      'cache_creation_tokens',
      'cache_creation_input_tokens',
      'cache_write_tokens',
    ),
  };

  if (usage.totalTokens === 0) {
    usage.totalTokens = usage.promptTokens + usage.completionTokens;
  }

  return [usage, true];
}
