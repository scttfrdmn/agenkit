package io.agenkit.evaluation;

/**
 * A named evaluation metric with a score and optional metadata.
 */
public record Metric(String name, double score, String description) {

    public Metric(String name, double score) {
        this(name, score, "");
    }

    public boolean passes(double threshold) {
        return score >= threshold;
    }

    @Override
    public String toString() {
        return "Metric{" + name + "=" + String.format("%.3f", score) + "}";
    }
}
