package io.agenkit.budget;

import java.util.Map;

/**
 * Pricing information for LLM models (cost per 1M tokens).
 */
public final class ModelPricing {

    private static final Map<String, double[]> PRICES = Map.of(
            "gpt-4o",                  new double[]{5.0, 15.0},
            "gpt-4o-mini",             new double[]{0.15, 0.60},
            "gpt-4-turbo",             new double[]{10.0, 30.0},
            "gpt-3.5-turbo",           new double[]{0.50, 1.50},
            "claude-3-5-sonnet-20241022", new double[]{3.0, 15.0},
            "claude-3-haiku-20240307",    new double[]{0.25, 1.25},
            "claude-opus-4-5",            new double[]{15.0, 75.0}
    );

    private ModelPricing() {}

    /** Returns {inputCostPer1MTokens, outputCostPer1MTokens} for a model. */
    public static double[] getPricing(String model) {
        return PRICES.getOrDefault(model, new double[]{1.0, 3.0});
    }

    public static double calculateCost(String model, int inputTokens, int outputTokens) {
        double[] pricing = getPricing(model);
        return (pricing[0] * inputTokens + pricing[1] * outputTokens) / 1_000_000.0;
    }
}
