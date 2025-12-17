"use strict";
/**
 * Bayesian Optimization for Hyperparameter Tuning
 *
 * This module implements Bayesian optimization using a simplified surrogate model
 * based on local statistics. It balances exploration and exploitation through
 * acquisition functions (Expected Improvement, Upper Confidence Bound).
 *
 * Example:
 * ```typescript
 * const searchSpace = new SearchSpace();
 * searchSpace.addContinuous('temperature', 0.0, 1.0);
 * searchSpace.addContinuous('top_p', 0.0, 1.0);
 *
 * const optimizer = new BayesianOptimizer({
 *   agentFactory: (config) => new MyAgent(config),
 *   searchSpace,
 *   objective: 'accuracy',
 *   nInitial: 5,
 *   acquisitionFunction: 'ei',
 * });
 *
 * const result = await optimizer.optimize(testCases, 50);
 * console.log(`Best config: ${JSON.stringify(result.bestConfig)}`);
 * console.log(`Best score: ${result.bestScore.toFixed(3)}`);
 * ```
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.BayesianOptimizer = void 0;
const optimizer_1 = require("./optimizer");
/**
 * Bayesian Optimizer for intelligent hyperparameter search.
 *
 * Uses a simplified surrogate model based on local statistics to guide
 * the search process. Balances exploration (trying new areas) with
 * exploitation (refining known good areas) using acquisition functions.
 */
class BayesianOptimizer extends optimizer_1.Optimizer {
    /**
     * Create Bayesian optimizer.
     *
     * @param config Optimizer configuration
     */
    constructor(config) {
        super(config.agentFactory, config.searchSpace, config.objective, config.maximize ?? true);
        this.bestConfig = null;
        this.bestScore = -Infinity;
        this.acquisitionFunction = config.acquisitionFunction || 'ei';
        this.nInitial = config.nInitial || 5;
        this.xi = config.xi || 0.01;
        this.kappa = config.kappa || 2.576; // 99% confidence interval
    }
    /**
     * Run Bayesian optimization.
     *
     * Algorithm:
     * 1. Sample n_initial random configurations
     * 2. Evaluate and build local statistics
     * 3. Use acquisition function to select next config
     * 4. Evaluate new config
     * 5. Update statistics and repeat
     *
     * @param testCases Test cases for evaluation
     * @param nIterations Number of iterations to run
     * @returns OptimizationResult with best configuration and history
     */
    async optimize(testCases, nIterations) {
        const startTime = new Date();
        this.history = [];
        this.bestConfig = null;
        this.bestScore = -Infinity;
        // Phase 1: Initial random exploration
        const nInitialEvals = Math.min(this.nInitial, nIterations);
        for (let i = 0; i < nInitialEvals; i++) {
            const config = this.searchSpace.sample();
            const score = await this.evaluateConfig(config, testCases);
            this.history.push([{ ...config }, score]);
            if (score > this.bestScore) {
                this.bestScore = score;
                this.bestConfig = { ...config };
            }
        }
        // Phase 2: Bayesian optimization
        for (let i = nInitialEvals; i < nIterations; i++) {
            // Select next configuration using acquisition function
            const config = await this.selectNextConfig();
            // Evaluate
            const score = await this.evaluateConfig(config, testCases);
            this.history.push([{ ...config }, score]);
            // Update best
            if (score > this.bestScore) {
                this.bestScore = score;
                this.bestConfig = { ...config };
            }
        }
        const endTime = new Date();
        // Fallback if no valid config found
        if (this.bestConfig === null) {
            this.bestConfig = this.searchSpace.sample();
        }
        return {
            bestConfig: this.bestConfig,
            bestScore: this.bestScore,
            history: this.history,
            nIterations,
            startTime,
            endTime,
            metadata: {
                algorithm: 'bayesian_optimization',
                acquisition_function: this.acquisitionFunction,
                n_initial: this.nInitial,
            },
        };
    }
    /**
     * Select next configuration to evaluate using acquisition function.
     *
     * Samples multiple candidates and selects the one with highest
     * acquisition value.
     *
     * @returns Next configuration to evaluate
     */
    async selectNextConfig() {
        // Sample multiple candidates
        const nCandidates = 100;
        const candidates = [];
        for (let i = 0; i < nCandidates; i++) {
            candidates.push(this.searchSpace.sample());
        }
        // Evaluate acquisition function for each candidate
        let bestCandidate = candidates[0];
        let bestAcquisition = -Infinity;
        for (const candidate of candidates) {
            const acquisition = this.computeAcquisition(candidate);
            if (acquisition > bestAcquisition) {
                bestAcquisition = acquisition;
                bestCandidate = candidate;
            }
        }
        return bestCandidate;
    }
    /**
     * Compute acquisition function value for a configuration.
     *
     * @param config Configuration to evaluate
     * @returns Acquisition value (higher = more promising)
     */
    computeAcquisition(config) {
        // Calculate local statistics (mean and std) from nearby points
        const { mean, std } = this.computeLocalStatistics(config);
        switch (this.acquisitionFunction) {
            case 'ei':
                return this.expectedImprovement(mean, std);
            case 'ucb':
                return this.upperConfidenceBound(mean, std);
            case 'pi':
                return this.probabilityOfImprovement(mean, std);
            default:
                return this.expectedImprovement(mean, std);
        }
    }
    /**
     * Compute local statistics (mean and std) from nearby evaluated points.
     *
     * Uses a simplified approach: weighted average based on distance in
     * parameter space.
     *
     * @param config Configuration to compute statistics for
     * @returns Mean and standard deviation estimates
     */
    computeLocalStatistics(config) {
        if (this.history.length === 0) {
            return { mean: 0, std: 1 };
        }
        // Calculate distances to all evaluated points
        const distances = [];
        const scores = [];
        for (const [evalConfig, score] of this.history) {
            const distance = this.configDistance(config, evalConfig);
            distances.push(distance);
            scores.push(score);
        }
        // Use k-nearest neighbors (k=5) for local statistics
        const k = Math.min(5, this.history.length);
        const indices = this.argsort(distances).slice(0, k);
        // Calculate weighted mean and std
        let sumWeights = 0;
        let weightedSum = 0;
        for (const idx of indices) {
            // Weight decreases with distance (inverse distance weighting)
            const weight = 1.0 / (distances[idx] + 1e-10);
            weightedSum += scores[idx] * weight;
            sumWeights += weight;
        }
        const mean = weightedSum / sumWeights;
        // Calculate standard deviation
        let sumSquaredDiff = 0;
        for (const idx of indices) {
            const weight = 1.0 / (distances[idx] + 1e-10);
            sumSquaredDiff += weight * Math.pow(scores[idx] - mean, 2);
        }
        const std = Math.sqrt(sumSquaredDiff / sumWeights);
        return { mean, std: Math.max(std, 0.01) }; // Minimum std to avoid division by zero
    }
    /**
     * Calculate distance between two configurations.
     *
     * For continuous parameters: normalized Euclidean distance
     * For discrete/categorical: 0 if same, 1 if different
     *
     * @param config1 First configuration
     * @param config2 Second configuration
     * @returns Distance between configurations
     */
    configDistance(config1, config2) {
        let distance = 0;
        let count = 0;
        for (const name of this.searchSpace.getParameterNames()) {
            const param = this.searchSpace.getParameter(name);
            if (!param)
                continue;
            const val1 = config1[name];
            const val2 = config2[name];
            if (param.type === 'continuous' || param.type === 'integer') {
                // Normalized Euclidean distance
                const range = param.high - param.low;
                const normalizedDiff = (Number(val1) - Number(val2)) / range;
                distance += normalizedDiff * normalizedDiff;
                count++;
            }
            else {
                // Discrete/categorical: binary distance
                distance += val1 === val2 ? 0 : 1;
                count++;
            }
        }
        return count > 0 ? Math.sqrt(distance / count) : 0;
    }
    /**
     * Expected Improvement acquisition function.
     *
     * @param mean Predicted mean
     * @param std Predicted standard deviation
     * @returns EI value
     */
    expectedImprovement(mean, std) {
        if (std < 1e-10) {
            return 0;
        }
        const improvement = mean - this.bestScore - this.xi;
        const z = improvement / std;
        // EI = improvement * Φ(z) + std * φ(z)
        // where Φ is CDF and φ is PDF of standard normal
        const ei = improvement * this.normalCdf(z) + std * this.normalPdf(z);
        return Math.max(ei, 0);
    }
    /**
     * Upper Confidence Bound acquisition function.
     *
     * @param mean Predicted mean
     * @param std Predicted standard deviation
     * @returns UCB value
     */
    upperConfidenceBound(mean, std) {
        return mean + this.kappa * std;
    }
    /**
     * Probability of Improvement acquisition function.
     *
     * @param mean Predicted mean
     * @param std Predicted standard deviation
     * @returns PI value
     */
    probabilityOfImprovement(mean, std) {
        if (std < 1e-10) {
            return 0;
        }
        const improvement = mean - this.bestScore - this.xi;
        const z = improvement / std;
        return this.normalCdf(z);
    }
    /**
     * Standard normal cumulative distribution function (CDF).
     *
     * @param x Input value
     * @returns Φ(x)
     */
    normalCdf(x) {
        // Using error function approximation
        return 0.5 * (1 + this.erf(x / Math.sqrt(2)));
    }
    /**
     * Standard normal probability density function (PDF).
     *
     * @param x Input value
     * @returns φ(x)
     */
    normalPdf(x) {
        return Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);
    }
    /**
     * Error function approximation.
     *
     * @param x Input value
     * @returns erf(x)
     */
    erf(x) {
        // Abramowitz and Stegun approximation
        const sign = x >= 0 ? 1 : -1;
        x = Math.abs(x);
        const a1 = 0.254829592;
        const a2 = -0.284496736;
        const a3 = 1.421413741;
        const a4 = -1.453152027;
        const a5 = 1.061405429;
        const p = 0.3275911;
        const t = 1.0 / (1.0 + p * x);
        const y = 1.0 - ((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
        return sign * y;
    }
    /**
     * Get indices that would sort an array.
     *
     * @param arr Array to sort
     * @returns Sorted indices
     */
    argsort(arr) {
        return arr
            .map((val, idx) => ({ val, idx }))
            .sort((a, b) => a.val - b.val)
            .map(item => item.idx);
    }
}
exports.BayesianOptimizer = BayesianOptimizer;
