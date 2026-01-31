/**
 * LLM parameter validation utilities.
 *
 * Provides consistent validation for common LLM parameters across all adapters.
 */

export interface LLMParams {
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
}

/**
 * Validate common LLM parameters.
 *
 * @param params - Parameters to validate
 * @throws Error if any parameter is out of valid range
 */
export function validateLLMParams(params: LLMParams): void {
  // Validate temperature (0-2)
  if (params.temperature !== undefined) {
    if (typeof params.temperature !== 'number' || params.temperature < 0 || params.temperature > 2) {
      throw new Error(`temperature must be between 0 and 2, got ${params.temperature}`);
    }
  }

  // Validate max_tokens (> 0)
  if (params.max_tokens !== undefined) {
    if (typeof params.max_tokens !== 'number' || params.max_tokens <= 0) {
      throw new Error(`max_tokens must be positive, got ${params.max_tokens}`);
    }
  }

  // Validate top_p (0-1)
  if (params.top_p !== undefined) {
    if (typeof params.top_p !== 'number' || params.top_p < 0 || params.top_p > 1) {
      throw new Error(`top_p must be between 0 and 1, got ${params.top_p}`);
    }
  }

  // Validate frequency_penalty (-2 to 2)
  if (params.frequency_penalty !== undefined) {
    if (
      typeof params.frequency_penalty !== 'number' ||
      params.frequency_penalty < -2 ||
      params.frequency_penalty > 2
    ) {
      throw new Error(
        `frequency_penalty must be between -2 and 2, got ${params.frequency_penalty}`
      );
    }
  }

  // Validate presence_penalty (-2 to 2)
  if (params.presence_penalty !== undefined) {
    if (
      typeof params.presence_penalty !== 'number' ||
      params.presence_penalty < -2 ||
      params.presence_penalty > 2
    ) {
      throw new Error(
        `presence_penalty must be between -2 and 2, got ${params.presence_penalty}`
      );
    }
  }
}
