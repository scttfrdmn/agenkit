"use strict";
/**
 * Retry middleware - automatic retries with exponential backoff.
 *
 * Handles transient failures by retrying requests with configurable
 * backoff strategy.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.RetryMiddleware = void 0;
exports.retry = retry;
const base_1 = require("./base");
/**
 * Default retry predicate - retries on network errors.
 */
function defaultShouldRetry(error) {
    // Retry on network errors, timeouts, 5xx errors
    const message = error.message.toLowerCase();
    return (message.includes('network') ||
        message.includes('timeout') ||
        message.includes('econnrefused') ||
        message.includes('enotfound') ||
        message.includes('http 5'));
}
/**
 * RetryMiddleware implements automatic retry with exponential backoff.
 *
 * Features:
 * - Configurable retry attempts
 * - Exponential backoff
 * - Customizable retry predicate
 * - Preserves error stack traces
 *
 * Usage:
 *   const agent = new RetryMiddleware(baseAgent, {
 *     maxAttempts: 3,
 *     initialDelay: 1000,
 *     backoffMultiplier: 2.0,
 *   });
 */
class RetryMiddleware extends base_1.BaseMiddleware {
    constructor(agent, config = {}) {
        super(agent);
        this.maxAttempts = config.maxAttempts || 3;
        this.initialDelay = config.initialDelay || 1000;
        this.backoffMultiplier = config.backoffMultiplier || 2.0;
        this.maxDelay = config.maxDelay || 30000;
        this.shouldRetry = config.shouldRetry || defaultShouldRetry;
    }
    async process(message) {
        let lastError = null;
        for (let attempt = 0; attempt < this.maxAttempts; attempt++) {
            try {
                return await this.agent.process(message);
            }
            catch (error) {
                lastError = error;
                // Don't retry if predicate says no or if we're on last attempt
                if (!this.shouldRetry(lastError) || attempt === this.maxAttempts - 1) {
                    throw lastError;
                }
                // Calculate delay with exponential backoff
                const delay = Math.min(this.initialDelay * Math.pow(this.backoffMultiplier, attempt), this.maxDelay);
                // Wait before retrying
                await new Promise((resolve) => setTimeout(resolve, delay));
            }
        }
        // Should never reach here, but TypeScript needs it
        throw lastError || new Error('Retry failed');
    }
}
exports.RetryMiddleware = RetryMiddleware;
/**
 * Create retry middleware function.
 *
 * @param config Retry configuration
 * @returns Middleware function
 */
function retry(config = {}) {
    return (agent) => new RetryMiddleware(agent, config);
}
