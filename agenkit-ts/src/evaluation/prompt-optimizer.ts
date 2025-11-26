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

import { Agent } from '../core/interfaces';
import { Evaluator, TestCase } from './core';
import { AccuracyMetric } from './quality-metrics';

/**
 * Optimization strategy types.
 */
export type OptimizationStrategy = 'grid' | 'random' | 'genetic';

/**
 * Agent factory that creates agents from prompt strings.
 */
export type PromptAgentFactory = (prompt: string) => Agent;

/**
 * Single prompt evaluation result.
 */
export interface PromptEvaluation {
  /** Generated prompt text */
  prompt: string;
  /** Variable configuration used */
  config: Record<string, string>;
  /** Metric scores achieved */
  scores: Record<string, number>;
}

/**
 * Results from prompt optimization.
 */
export interface PromptOptimizationResult {
  /** Best prompt found */
  bestPrompt: string;
  /** Best variable configuration */
  bestConfig: Record<string, string>;
  /** Best metric scores */
  bestScores: Record<string, number>;
  /** All evaluations performed */
  history: PromptEvaluation[];
  /** Number of prompts evaluated */
  nEvaluated: number;
  /** Strategy used */
  strategy: string;
  /** Optimization start time */
  startTime: Date;
  /** Optimization end time */
  endTime: Date;
}

/**
 * Get duration of prompt optimization in seconds.
 *
 * @param result Optimization result
 * @returns Duration in seconds
 */
export function getPromptOptimizationDuration(result: PromptOptimizationResult): number {
  return (result.endTime.getTime() - result.startTime.getTime()) / 1000;
}

/**
 * Convert prompt optimization result to plain object.
 *
 * @param result Optimization result
 * @returns Plain object representation
 */
export function promptOptimizationResultToDict(
  result: PromptOptimizationResult
): Record<string, unknown> {
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
 * Configuration for prompt optimizer.
 */
export interface PromptOptimizerConfig {
  /** Prompt template with {variable} placeholders */
  template: string;
  /** Map of variable names to possible values */
  variations: Record<string, string[]>;
  /** Function that creates agent from prompt string */
  agentFactory: PromptAgentFactory;
  /** List of metrics to evaluate */
  metrics: string[];
  /** Primary metric for optimization (defaults to first metric) */
  objectiveMetric?: string;
  /** Whether to maximize (true) or minimize (false) objective */
  maximize?: boolean;
}

/**
 * Genetic algorithm configuration.
 */
export interface GeneticConfig {
  /** Population size */
  populationSize?: number;
  /** Number of generations */
  nGenerations?: number;
  /** Mutation rate (0-1) */
  mutationRate?: number;
}

/**
 * Optimize prompts through systematic variation.
 *
 * Supports multiple optimization strategies:
 * - Grid search: Exhaustive evaluation of all combinations
 * - Random search: Random sampling of combinations
 * - Genetic algorithm: Evolutionary optimization
 */
export class PromptOptimizer {
  private template: string;
  private variations: Record<string, string[]>;
  private agentFactory: PromptAgentFactory;
  private metrics: string[];
  private objectiveMetric: string;
  private maximize: boolean;
  private history: PromptEvaluation[] = [];

  /**
   * Create prompt optimizer.
   *
   * @param config Optimizer configuration
   */
  constructor(config: PromptOptimizerConfig) {
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
  async optimize(
    testCases: TestCase[],
    strategy: OptimizationStrategy,
    options?: Record<string, unknown>
  ): Promise<PromptOptimizationResult> {
    const startTime = new Date();
    this.history = [];

    let result: PromptOptimizationResult;

    switch (strategy) {
      case 'grid':
        result = await this.optimizeGrid(testCases);
        break;
      case 'random':
        const nSamples = (options?.nSamples as number) || 20;
        result = await this.optimizeRandom(testCases, nSamples);
        break;
      case 'genetic':
        const geneticConfig: GeneticConfig = {
          populationSize: (options?.populationSize as number) || 10,
          nGenerations: (options?.nGenerations as number) || 10,
          mutationRate: (options?.mutationRate as number) || 0.2,
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
  private async optimizeGrid(testCases: TestCase[]): Promise<PromptOptimizationResult> {
    const configs = this.generateAllConfigs();

    let bestConfig: Record<string, string> | null = null;
    let bestScores: Record<string, number> = {};
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
      bestPrompt: this.fillTemplate(bestConfig!),
      bestConfig: bestConfig!,
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
  private async optimizeRandom(
    testCases: TestCase[],
    nSamples: number
  ): Promise<PromptOptimizationResult> {
    let bestConfig: Record<string, string> | null = null;
    let bestScores: Record<string, number> = {};
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
      bestPrompt: this.fillTemplate(bestConfig!),
      bestConfig: bestConfig!,
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
  private async optimizeGenetic(
    testCases: TestCase[],
    config: GeneticConfig
  ): Promise<PromptOptimizationResult> {
    const populationSize = config.populationSize || 10;
    const nGenerations = config.nGenerations || 10;
    const mutationRate = config.mutationRate || 0.2;

    // Initialize population
    let population: Array<{ config: Record<string, string>; fitness: number }> = [];
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
      const offspring: typeof population = [];
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
  private fillTemplate(config: Record<string, string>): string {
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
  private generateAllConfigs(): Array<Record<string, string>> {
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
  private cartesianProduct(
    keys: string[],
    valueLists: string[][],
    index: number,
    current: Record<string, string>
  ): Array<Record<string, string>> {
    if (index === keys.length) {
      return [{ ...current }];
    }

    const results: Array<Record<string, string>> = [];
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
  private sampleConfig(): Record<string, string> {
    const config: Record<string, string> = {};
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
  private async evaluatePrompt(
    prompt: string,
    config: Record<string, string>,
    testCases: TestCase[]
  ): Promise<Record<string, number>> {
    const agent = this.agentFactory(prompt);

    // Create metrics
    const metricObjects = [];
    if (this.metrics.includes('accuracy')) {
      metricObjects.push(new AccuracyMetric());
    }

    const evaluator = new Evaluator(agent, metricObjects);
    const result = await evaluator.evaluate(testCases);

    // Extract scores
    const scores: Record<string, number> = {};
    for (const metric of this.metrics) {
      if (metric === 'accuracy' && result.accuracy !== undefined) {
        scores.accuracy = result.accuracy;
      } else if (metric === 'quality_score' && result.qualityScore !== undefined) {
        scores.quality_score = result.qualityScore;
      } else if (metric === 'latency_ms' && result.avgLatencyMs !== undefined) {
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
  private tournamentSelect(
    population: Array<{ config: Record<string, string>; fitness: number }>
  ): { config: Record<string, string>; fitness: number } {
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
  private crossover(
    parent1: Record<string, string>,
    parent2: Record<string, string>
  ): Record<string, string> {
    const child: Record<string, string> = {};
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
  private mutate(config: Record<string, string>): void {
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
  getHistory(): PromptEvaluation[] {
    return [...this.history];
  }
}
