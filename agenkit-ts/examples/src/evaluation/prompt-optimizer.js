"use strict";
/**
 * Prompt Optimization Framework
 *
 * Automatically improve prompts through systematic variation and testing
 * using grid search, random search, or genetic algorithms.
 *
 * Example:
 * ```typescript
 * const template = `You are a {role}.
 * {instructions}`;
 *
 * const variations = {
 *   role: ['helpful assistant', 'expert advisor'],
 *   instructions: ['Be concise.', 'Be detailed.'],
 * };
 *
 * const optimizer = new PromptOptimizer({
 *   template,
 *   variations,
 *   agentFactory: (prompt) => new MyAgent({ systemPrompt: prompt }),
 *   metrics: ['accuracy'],
 * });
 *
 * const result = await optimizer.optimize(testCases, 'grid');
 * console.log(`Best prompt: ${result.bestPrompt}`);
 * console.log(`Best scores: ${JSON.stringify(result.bestScores)}`);
 * ```
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.PromptOptimizer = void 0;
exports.getPromptOptimizationDuration = getPromptOptimizationDuration;
exports.promptOptimizationResultToDict = promptOptimizationResultToDict;
const core_1 = require("./core");
const quality_metrics_1 = require("./quality-metrics");
/**
 * Get duration of prompt optimization in seconds.
 *
 * @param result Optimization result
 * @returns Duration in seconds
 */
function getPromptOptimizationDuration(result) {
    return (result.endTime.getTime() - result.startTime.getTime()) / 1000;
}
/**
 * Convert prompt optimization result to plain object.
 *
 * @param result Optimization result
 * @returns Plain object representation
 */
function promptOptimizationResultToDict(result) {
    return {
        best_prompt: result.bestPrompt,
        best_config: result.bestConfig,
        best_scores: result.bestScores,
        n_evaluated: result.nEvaluated,
        strategy: result.strategy,
        duration_seconds: getPromptOptimizationDuration(result),
        start_time: result.startTime.toISOString(),
        end_time: result.endTime.toISOString(),
    };
}
/**
 * Optimize prompts through systematic variation.
 *
 * Supports multiple optimization strategies:
 * - Grid search: Exhaustive evaluation of all combinations
 * - Random search: Random sampling of combinations
 * - Genetic algorithm: Evolutionary optimization
 */
class PromptOptimizer {
    /**
     * Create prompt optimizer.
     *
     * @param config Optimizer configuration
     */
    constructor(config) {
        this.history = [];
        this.template = config.template;
        this.variations = config.variations;
        this.agentFactory = config.agentFactory;
        this.metrics = config.metrics;
        this.objectiveMetric = config.objectiveMetric || config.metrics[0];
        this.maximize = config.maximize ?? true;
    }
    /**
     * Optimize prompt using specified strategy.
     *
     * @param testCases Test cases for evaluation
     * @param strategy Optimization strategy
     * @param options Strategy-specific options
     * @returns Optimization result
     */
    async optimize(testCases, strategy, options) {
        const startTime = new Date();
        this.history = [];
        let result;
        switch (strategy) {
            case 'grid':
                result = await this.optimizeGrid(testCases);
                break;
            case 'random':
                const nSamples = options?.nSamples || 20;
                result = await this.optimizeRandom(testCases, nSamples);
                break;
            case 'genetic':
                const geneticConfig = {
                    populationSize: options?.populationSize || 10,
                    nGenerations: options?.nGenerations || 10,
                    mutationRate: options?.mutationRate || 0.2,
                };
                result = await this.optimizeGenetic(testCases, geneticConfig);
                break;
            default:
                throw new Error(`Unknown strategy: ${strategy}`);
        }
        result.endTime = new Date();
        return result;
    }
    /**
     * Grid search: exhaustive evaluation of all combinations.
     *
     * @param testCases Test cases for evaluation
     * @returns Optimization result
     */
    async optimizeGrid(testCases) {
        const configs = this.generateAllConfigs();
        let bestConfig = null;
        let bestScores = {};
        let bestObjective = this.maximize ? -Infinity : Infinity;
        for (const config of configs) {
            const prompt = this.fillTemplate(config);
            const scores = await this.evaluatePrompt(prompt, config, testCases);
            const objective = scores[this.objectiveMetric] || 0;
            const isBetter = this.maximize ? objective > bestObjective : objective < bestObjective;
            if (isBetter) {
                bestObjective = objective;
                bestConfig = config;
                bestScores = scores;
            }
        }
        return {
            bestPrompt: this.fillTemplate(bestConfig),
            bestConfig: bestConfig,
            bestScores,
            history: this.history,
            nEvaluated: configs.length,
            strategy: 'grid',
            startTime: new Date(),
            endTime: new Date(),
        };
    }
    /**
     * Random search: sample random combinations.
     *
     * @param testCases Test cases for evaluation
     * @param nSamples Number of samples to evaluate
     * @returns Optimization result
     */
    async optimizeRandom(testCases, nSamples) {
        let bestConfig = null;
        let bestScores = {};
        let bestObjective = this.maximize ? -Infinity : Infinity;
        for (let i = 0; i < nSamples; i++) {
            const config = this.sampleConfig();
            const prompt = this.fillTemplate(config);
            const scores = await this.evaluatePrompt(prompt, config, testCases);
            const objective = scores[this.objectiveMetric] || 0;
            const isBetter = this.maximize ? objective > bestObjective : objective < bestObjective;
            if (isBetter) {
                bestObjective = objective;
                bestConfig = config;
                bestScores = scores;
            }
        }
        return {
            bestPrompt: this.fillTemplate(bestConfig),
            bestConfig: bestConfig,
            bestScores,
            history: this.history,
            nEvaluated: nSamples,
            strategy: 'random',
            startTime: new Date(),
            endTime: new Date(),
        };
    }
    /**
     * Genetic algorithm: evolutionary optimization.
     *
     * @param testCases Test cases for evaluation
     * @param config Genetic algorithm configuration
     * @returns Optimization result
     */
    async optimizeGenetic(testCases, config) {
        const populationSize = config.populationSize || 10;
        const nGenerations = config.nGenerations || 10;
        const mutationRate = config.mutationRate || 0.2;
        // Initialize population
        let population = [];
        for (let i = 0; i < populationSize; i++) {
            const cfg = this.sampleConfig();
            const prompt = this.fillTemplate(cfg);
            const scores = await this.evaluatePrompt(prompt, cfg, testCases);
            const fitness = scores[this.objectiveMetric] || 0;
            population.push({ config: cfg, fitness });
        }
        // Evolve
        for (let gen = 0; gen < nGenerations; gen++) {
            // Sort by fitness
            population.sort((a, b) => (this.maximize ? b.fitness - a.fitness : a.fitness - b.fitness));
            // Select top half (elitism)
            const survivors = population.slice(0, Math.floor(populationSize / 2));
            // Create offspring
            const offspring = [];
            while (offspring.length + survivors.length < populationSize) {
                // Tournament selection
                const parent1 = this.tournamentSelect(survivors);
                const parent2 = this.tournamentSelect(survivors);
                // Crossover
                const child = this.crossover(parent1.config, parent2.config);
                // Mutation
                if (Math.random() < mutationRate) {
                    this.mutate(child);
                }
                // Evaluate
                const prompt = this.fillTemplate(child);
                const scores = await this.evaluatePrompt(prompt, child, testCases);
                const fitness = scores[this.objectiveMetric] || 0;
                offspring.push({ config: child, fitness });
            }
            population = [...survivors, ...offspring];
        }
        // Find best
        population.sort((a, b) => (this.maximize ? b.fitness - a.fitness : a.fitness - b.fitness));
        const best = population[0];
        return {
            bestPrompt: this.fillTemplate(best.config),
            bestConfig: best.config,
            bestScores: { [this.objectiveMetric]: best.fitness },
            history: this.history,
            nEvaluated: this.history.length,
            strategy: 'genetic',
            startTime: new Date(),
            endTime: new Date(),
        };
    }
    /**
     * Fill template with configuration values.
     *
     * @param config Variable configuration
     * @returns Filled prompt
     */
    fillTemplate(config) {
        let result = this.template;
        for (const [key, value] of Object.entries(config)) {
            const placeholder = `{${key}}`;
            result = result.replace(new RegExp(placeholder, 'g'), value);
        }
        return result;
    }
    /**
     * Generate all possible configurations (Cartesian product).
     *
     * @returns All configuration combinations
     */
    generateAllConfigs() {
        const keys = Object.keys(this.variations);
        const valueLists = keys.map(key => this.variations[key]);
        return this.cartesianProduct(keys, valueLists, 0, {});
    }
    /**
     * Generate Cartesian product recursively.
     *
     * @param keys Variable names
     * @param valueLists Lists of values for each variable
     * @param index Current index
     * @param current Current configuration
     * @returns All configurations
     */
    cartesianProduct(keys, valueLists, index, current) {
        if (index === keys.length) {
            return [{ ...current }];
        }
        const results = [];
        for (const value of valueLists[index]) {
            current[keys[index]] = value;
            const configs = this.cartesianProduct(keys, valueLists, index + 1, current);
            results.push(...configs);
        }
        return results;
    }
    /**
     * Sample random configuration.
     *
     * @returns Random configuration
     */
    sampleConfig() {
        const config = {};
        for (const [key, values] of Object.entries(this.variations)) {
            config[key] = values[Math.floor(Math.random() * values.length)];
        }
        return config;
    }
    /**
     * Evaluate prompt on test cases.
     *
     * @param prompt Prompt to evaluate
     * @param config Configuration used
     * @param testCases Test cases
     * @returns Metric scores
     */
    async evaluatePrompt(prompt, config, testCases) {
        const agent = this.agentFactory(prompt);
        // Create metrics
        const metricObjects = [];
        if (this.metrics.includes('accuracy')) {
            metricObjects.push(new quality_metrics_1.AccuracyMetric());
        }
        const evaluator = new core_1.Evaluator(agent, metricObjects);
        const result = await evaluator.evaluate(testCases);
        // Extract scores
        const scores = {};
        for (const metric of this.metrics) {
            if (metric === 'accuracy' && result.accuracy !== undefined) {
                scores.accuracy = result.accuracy;
            }
            else if (metric === 'quality_score' && result.qualityScore !== undefined) {
                scores.quality_score = result.qualityScore;
            }
            else if (metric === 'latency_ms' && result.avgLatencyMs !== undefined) {
                scores.latency_ms = result.avgLatencyMs;
            }
        }
        // Record evaluation
        this.history.push({ prompt, config, scores });
        return scores;
    }
    /**
     * Tournament selection for genetic algorithm.
     *
     * @param population Population to select from
     * @returns Selected individual
     */
    tournamentSelect(population) {
        const tournamentSize = 3;
        const tournament = [];
        for (let i = 0; i < tournamentSize; i++) {
            const idx = Math.floor(Math.random() * population.length);
            tournament.push(population[idx]);
        }
        tournament.sort((a, b) => (this.maximize ? b.fitness - a.fitness : a.fitness - b.fitness));
        return tournament[0];
    }
    /**
     * Crossover two configurations.
     *
     * @param parent1 First parent
     * @param parent2 Second parent
     * @returns Child configuration
     */
    crossover(parent1, parent2) {
        const child = {};
        for (const key of Object.keys(this.variations)) {
            child[key] = Math.random() < 0.5 ? parent1[key] : parent2[key];
        }
        return child;
    }
    /**
     * Mutate configuration.
     *
     * @param config Configuration to mutate (mutated in place)
     */
    mutate(config) {
        const keys = Object.keys(this.variations);
        const keyToMutate = keys[Math.floor(Math.random() * keys.length)];
        const values = this.variations[keyToMutate];
        config[keyToMutate] = values[Math.floor(Math.random() * values.length)];
    }
    /**
     * Get optimization history.
     *
     * @returns History of prompt evaluations
     */
    getHistory() {
        return [...this.history];
    }
}
exports.PromptOptimizer = PromptOptimizer;
