/**
 * Model pricing data for LLM cost tracking.
 *
 * Pricing data as of January 2026. Rates are per 1 million tokens.
 */

/**
 * Pricing data for LLM models (as of January 2026).
 *
 * All prices are per 1 million tokens (input and output separately).
 *
 * Example:
 *   const pricing = new ModelPricing();
 *   const cost = pricing.calculate('claude-sonnet-4', 10000, 'input');
 *   console.log(`Cost: $${cost.toFixed(4)}`);
 *   // Cost: $0.0300
 */
export class ModelPricing {
  // Pricing data (per 1M tokens)
  private static PRICING: Record<string, { input: number; output: number }> = {
    // OpenAI
    'gpt-4o': { input: 2.5, output: 10.0 },
    'gpt-4-turbo': { input: 10.0, output: 30.0 },
    'gpt-3.5-turbo': { input: 0.5, output: 1.5 },
    o3: { input: 5.0, output: 15.0 },
    'o3-mini': { input: 1.0, output: 3.0 },
    // Anthropic
    'claude-opus-4': { input: 15.0, output: 75.0 },
    'claude-sonnet-4': { input: 3.0, output: 15.0 },
    'claude-sonnet-4.5': { input: 3.0, output: 15.0 },
    'claude-haiku-3': { input: 0.25, output: 1.25 },
    // Google
    'gemini-2.0-flash-exp': { input: 0.0, output: 0.0 }, // Free tier
    'gemini-pro': { input: 0.5, output: 1.5 },
    // Generic fallback
    default: { input: 0.01, output: 0.01 },
  };

  /**
   * Calculate cost for tokens.
   *
   * Example:
   *   const pricing = new ModelPricing();
   *   const cost = pricing.calculate('claude-opus-4', 100000, 'input');
   *   console.log(`$${cost.toFixed(2)}`);
   *   // $1.50
   */
  calculate(model: string, tokens: number, direction: 'input' | 'output'): number {
    if (direction !== 'input' && direction !== 'output') {
      throw new Error(`direction must be 'input' or 'output', got: ${direction}`);
    }

    let modelKey = model;
    if (!(model in ModelPricing.PRICING)) {
      console.warn(
        `Unknown model '${model}', using default pricing. ` +
          `Known models: ${Object.keys(ModelPricing.PRICING).join(', ')}`,
      );
      modelKey = 'default';
    }

    const pricePerMillion = ModelPricing.PRICING[modelKey][direction];
    return (tokens / 1_000_000) * pricePerMillion;
  }

  /**
   * Get pricing for specific model.
   *
   * Returns dict with "input" and "output" prices per 1M tokens,
   * or undefined if model not found.
   *
   * Example:
   *   const pricing = new ModelPricing();
   *   const rates = pricing.getModelPricing('claude-sonnet-4');
   *   console.log(rates);
   *   // { input: 3.00, output: 15.00 }
   */
  getModelPricing(model: string): { input: number; output: number } | undefined {
    return ModelPricing.PRICING[model];
  }

  /**
   * List all supported models.
   *
   * Example:
   *   const pricing = new ModelPricing();
   *   const models = pricing.listModels();
   *   console.log(models.length);
   *   // 12
   */
  listModels(): string[] {
    return Object.keys(ModelPricing.PRICING).filter((model) => model !== 'default');
  }

  /**
   * Update pricing for model (for testing or custom deployments).
   *
   * Example:
   *   ModelPricing.updatePricing('custom-model', 1.0, 5.0);
   *   const pricing = new ModelPricing();
   *   const cost = pricing.calculate('custom-model', 1000000, 'output');
   *   console.log(`$${cost.toFixed(2)}`);
   *   // $5.00
   */
  static updatePricing(model: string, inputPrice: number, outputPrice: number): void {
    ModelPricing.PRICING[model] = { input: inputPrice, output: outputPrice };
    console.log(
      `Updated pricing for ${model}: $${inputPrice}/M input, $${outputPrice}/M output`,
    );
  }

  /**
   * Estimate cost for a conversation.
   *
   * Example:
   *   const pricing = new ModelPricing();
   *   const cost = pricing.estimateConversationCost(
   *     'claude-sonnet-4',
   *     100,
   *     1000,
   *     500,
   *   );
   *   console.log(`Estimated: $${cost.toFixed(2)}`);
   *   // Estimated: $1.05
   */
  estimateConversationCost(
    model: string,
    numTurns: number,
    avgInputTokens: number,
    avgOutputTokens: number,
  ): number {
    const totalInput = numTurns * avgInputTokens;
    const totalOutput = numTurns * avgOutputTokens;

    const inputCost = this.calculate(model, totalInput, 'input');
    const outputCost = this.calculate(model, totalOutput, 'output');

    return inputCost + outputCost;
  }

  /**
   * Compare costs across different models.
   *
   * Example:
   *   const pricing = new ModelPricing();
   *   const comparison = pricing.compareModels(
   *     ['claude-haiku-3', 'claude-sonnet-4', 'claude-opus-4'],
   *     100000,
   *     50000,
   *   );
   *   for (const [model, cost] of Object.entries(comparison).sort((a, b) => a[1] - b[1])) {
   *     console.log(`${model}: $${cost.toFixed(2)}`);
   *   }
   *   // claude-haiku-3: $0.09
   *   // claude-sonnet-4: $1.05
   *   // claude-opus-4: $5.25
   */
  compareModels(
    models: string[],
    inputTokens: number,
    outputTokens: number,
  ): Record<string, number> {
    const costs: Record<string, number> = {};

    for (const model of models) {
      const inputCost = this.calculate(model, inputTokens, 'input');
      const outputCost = this.calculate(model, outputTokens, 'output');
      costs[model] = inputCost + outputCost;
    }

    return costs;
  }
}
