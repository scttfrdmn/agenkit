"use strict";
/**
 * Automated Optimization Framework
 *
 * This module provides intelligent optimization of agent configurations, prompts,
 * and hyperparameters using Bayesian optimization, genetic algorithms, and other
 * search strategies.
 *
 * Example:
 * ```typescript
 * const searchSpace = new SearchSpace();
 * searchSpace.addContinuous('temperature', 0.0, 1.0);
 * searchSpace.addContinuous('top_p', 0.0, 1.0);
 *
 * const optimizer = new RandomSearchOptimizer(
 *   (config) => new MyAgent(config),
 *   searchSpace,
 *   'accuracy'
 * );
 *
 * const result = await optimizer.optimize(testCases, 50);
 * console.log(`Best config: ${JSON.stringify(result.bestConfig)}`);
 * console.log(`Best score: ${result.bestScore.toFixed(3)}`);
 * ```
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.RandomSearchOptimizer = exports.Optimizer = exports.SearchSpace = void 0;
exports.getOptimizationDuration = getOptimizationDuration;
exports.getOptimizationImprovement = getOptimizationImprovement;
exports.optimizationResultToDict = optimizationResultToDict;
const core_1 = require("./core");
const quality_metrics_1 = require("./quality-metrics");
/**
 * Definition of parameter search space for optimization.
 *
 * Supports continuous, discrete, integer, and categorical parameters.
 */
class SearchSpace {
    constructor() {
        this.parameters = new Map();
    }
    /**
     * Add continuous parameter with range [low, high].
     *
     * @param name Parameter name
     * @param low Minimum value
     * @param high Maximum value
     */
    addContinuous(name, low, high) {
        this.parameters.set(name, { type: 'continuous', low, high });
    }
    /**
     * Add discrete parameter with specific values.
     *
     * @param name Parameter name
     * @param values Valid values for parameter
     */
    addDiscrete(name, values) {
        this.parameters.set(name, { type: 'discrete', values });
    }
    /**
     * Add integer parameter with range [low, high].
     *
     * @param name Parameter name
     * @param low Minimum value
     * @param high Maximum value
     */
    addInteger(name, low, high) {
        this.parameters.set(name, { type: 'integer', low, high });
    }
    /**
     * Add categorical parameter with specific values.
     *
     * @param name Parameter name
     * @param values Valid values for parameter
     */
    addCategorical(name, values) {
        this.parameters.set(name, { type: 'categorical', values });
    }
    /**
     * Sample random configuration from search space.
     *
     * @returns Random configuration
     */
    sample() {
        const config = {};
        for (const [name, spec] of this.parameters.entries()) {
            if (spec.type === 'continuous') {
                const low = spec.low;
                const high = spec.high;
                config[name] = Math.random() * (high - low) + low;
            }
            else if (spec.type === 'discrete' || spec.type === 'categorical') {
                const values = spec.values;
                config[name] = values[Math.floor(Math.random() * values.length)];
            }
            else if (spec.type === 'integer') {
                const low = spec.low;
                const high = spec.high;
                config[name] = Math.floor(Math.random() * (high - low + 1)) + low;
            }
        }
        return config;
    }
    /**
     * Validate that configuration is within search space.
     *
     * @param config Configuration to validate
     * @returns True if configuration is valid
     */
    validate(config) {
        for (const [name, value] of Object.entries(config)) {
            const spec = this.parameters.get(name);
            if (!spec) {
                return false;
            }
            if (spec.type === 'continuous') {
                if (typeof value !== 'number' || value < spec.low || value > spec.high) {
                    return false;
                }
            }
            else if (spec.type === 'discrete') {
                if (!spec.values.includes(value)) {
                    return false;
                }
            }
            else if (spec.type === 'integer') {
                if (typeof value !== 'number' ||
                    !Number.isInteger(value) ||
                    value < spec.low ||
                    value > spec.high) {
                    return false;
                }
            }
            else if (spec.type === 'categorical') {
                if (!spec.values.includes(value)) {
                    return false;
                }
            }
        }
        return true;
    }
    /**
     * Get parameter specification.
     *
     * @param name Parameter name
     * @returns Parameter specification if exists
     */
    getParameter(name) {
        return this.parameters.get(name);
    }
    /**
     * Get all parameter names.
     *
     * @returns Array of parameter names
     */
    getParameterNames() {
        return Array.from(this.parameters.keys());
    }
    /**
     * Get number of parameters.
     *
     * @returns Number of parameters
     */
    size() {
        return this.parameters.size;
    }
}
exports.SearchSpace = SearchSpace;
/**
 * Get duration of optimization in seconds.
 *
 * @param result Optimization result
 * @returns Duration in seconds
 */
function getOptimizationDuration(result) {
    return (result.endTime.getTime() - result.startTime.getTime()) / 1000;
}
/**
 * Get improvement from initial to best score.
 *
 * @param result Optimization result
 * @returns Improvement percentage
 */
function getOptimizationImprovement(result) {
    if (result.history.length === 0) {
        return 0;
    }
    const initialScore = result.history[0][1];
    if (initialScore === 0) {
        return 0;
    }
    return ((result.bestScore - initialScore) / Math.abs(initialScore)) * 100;
}
/**
 * Convert optimization result to plain object.
 *
 * @param result Optimization result
 * @returns Plain object representation
 */
function optimizationResultToDict(result) {
    return {
        best_config: result.bestConfig,
        best_score: result.bestScore,
        n_iterations: result.nIterations,
        improvement_percent: getOptimizationImprovement(result),
        duration_seconds: getOptimizationDuration(result),
        start_time: result.startTime.toISOString(),
        end_time: result.endTime.toISOString(),
        metadata: result.metadata,
    };
}
/**
 * Base class for optimization algorithms.
 *
 * Subclasses should implement the optimize() method to perform
 * intelligent search over the configuration space.
 */
class Optimizer {
    /**
     * Create optimizer.
     *
     * @param agentFactory Function that creates agent from config
     * @param searchSpace SearchSpace defining parameter space
     * @param objective Metric name or custom objective function
     * @param maximize Whether to maximize (true) or minimize (false) objective
     */
    constructor(agentFactory, searchSpace, objective, maximize = true) {
        this.history = [];
        this.agentFactory = agentFactory;
        this.searchSpace = searchSpace;
        this.objective = objective;
        this.maximize = maximize;
    }
    /**
     * Evaluate a configuration on test cases.
     *
     * @param config Configuration to evaluate
     * @param testCases Test cases for evaluation
     * @returns Objective score (higher is better if maximize=true)
     */
    async evaluateConfig(config, testCases) {
        // Create agent with config
        const agent = this.agentFactory(config);
        let score;
        if (typeof this.objective === 'string') {
            // Use named metric
            const metrics = [];
            if (this.objective === 'accuracy') {
                metrics.push(new quality_metrics_1.AccuracyMetric());
            }
            const evaluator = new core_1.Evaluator(agent, metrics, 'opt-session');
            const result = await evaluator.evaluate(testCases);
            // Get metric value
            if (this.objective === 'accuracy' && result.accuracy !== undefined) {
                score = result.accuracy;
            }
            else if (this.objective === 'quality_score' && result.qualityScore !== undefined) {
                score = result.qualityScore;
            }
            else if (this.objective === 'latency_ms' && result.avgLatencyMs !== undefined) {
                score = result.avgLatencyMs;
                // Invert for latency (lower is better)
                if (this.maximize) {
                    score = -score;
                }
            }
            else {
                // Default to accuracy
                score = result.accuracy ?? 0;
            }
        }
        else {
            // Use custom objective function
            score = await this.objective(agent, testCases);
        }
        return this.maximize ? score : -score;
    }
    /**
     * Get optimization history.
     *
     * @returns History of (config, score) pairs
     */
    getHistory() {
        return [...this.history];
    }
}
exports.Optimizer = Optimizer;
/**
 * Baseline random search optimizer.
 *
 * Randomly samples configurations from the search space and
 * evaluates them. Useful as a baseline for comparison.
 */
class RandomSearchOptimizer extends Optimizer {
    /**
     * Run random search optimization.
     *
     * @param testCases Test cases for evaluation
     * @param nIterations Number of iterations to run
     * @returns OptimizationResult with best configuration and history
     */
    async optimize(testCases, nIterations) {
        const startTime = new Date();
        this.history = [];
        let bestConfig = null;
        let bestScore = -Infinity;
        for (let i = 0; i < nIterations; i++) {
            // Sample random configuration
            const config = this.searchSpace.sample();
            // Evaluate
            const score = await this.evaluateConfig(config, testCases);
            this.history.push([{ ...config }, score]);
            // Update best
            if (score > bestScore) {
                bestScore = score;
                bestConfig = { ...config };
            }
        }
        const endTime = new Date();
        // Fallback if no valid config found
        if (bestConfig === null) {
            bestConfig = this.searchSpace.sample();
        }
        return {
            bestConfig,
            bestScore,
            history: this.history,
            nIterations,
            startTime,
            endTime,
            metadata: { algorithm: 'random_search' },
        };
    }
}
exports.RandomSearchOptimizer = RandomSearchOptimizer;
