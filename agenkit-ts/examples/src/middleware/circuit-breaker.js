"use strict";
/**
 * Circuit breaker middleware - prevents cascading failures.
 *
 * Implements the circuit breaker pattern to protect services from
 * repeated failures by temporarily stopping requests.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.CircuitBreakerMiddleware = exports.CircuitBreakerError = exports.CircuitState = void 0;
exports.circuitBreaker = circuitBreaker;
const base_1 = require("./base");
/**
 * Circuit breaker states.
 */
var CircuitState;
(function (CircuitState) {
    CircuitState["CLOSED"] = "CLOSED";
    CircuitState["OPEN"] = "OPEN";
    CircuitState["HALF_OPEN"] = "HALF_OPEN";
})(CircuitState || (exports.CircuitState = CircuitState = {}));
/**
 * Circuit breaker error.
 */
class CircuitBreakerError extends Error {
    constructor(agentName) {
        super(`Circuit breaker OPEN for agent: ${agentName}`);
        this.name = 'CircuitBreakerError';
    }
}
exports.CircuitBreakerError = CircuitBreakerError;
/**
 * CircuitBreakerMiddleware implements the circuit breaker pattern.
 *
 * Features:
 * - Three states: CLOSED, OPEN, HALF_OPEN
 * - Automatic recovery attempts
 * - Configurable thresholds
 * - Metrics tracking
 *
 * Usage:
 *   const agent = new CircuitBreakerMiddleware(baseAgent, {
 *     failureThreshold: 5,
 *     successThreshold: 2,
 *     timeout: 60000,
 *   });
 */
class CircuitBreakerMiddleware extends base_1.BaseMiddleware {
    constructor(agent, config = {}) {
        super(agent);
        this.state = CircuitState.CLOSED;
        this.failureCount = 0;
        this.successCount = 0;
        this.nextAttempt = 0;
        this.failureThreshold = config.failureThreshold || 5;
        this.successThreshold = config.successThreshold || 2;
        this.timeout = config.timeout || 60000;
        this.cbName = config.name || `circuit-breaker-${agent.name}`;
    }
    async process(message) {
        // Check circuit state
        if (this.state === CircuitState.OPEN) {
            // Check if timeout expired
            if (Date.now() >= this.nextAttempt) {
                this.state = CircuitState.HALF_OPEN;
                this.successCount = 0;
            }
            else {
                throw new CircuitBreakerError(this.agent.name);
            }
        }
        try {
            const response = await this.agent.process(message);
            // Record success
            this.onSuccess();
            return response;
        }
        catch (error) {
            // Record failure
            this.onFailure();
            throw error;
        }
    }
    onSuccess() {
        this.failureCount = 0;
        if (this.state === CircuitState.HALF_OPEN) {
            this.successCount++;
            if (this.successCount >= this.successThreshold) {
                this.state = CircuitState.CLOSED;
                this.successCount = 0;
            }
        }
    }
    onFailure() {
        this.failureCount++;
        if (this.state === CircuitState.HALF_OPEN) {
            // Failed in half-open, immediately open circuit
            this.state = CircuitState.OPEN;
            this.nextAttempt = Date.now() + this.timeout;
            this.successCount = 0;
        }
        else if (this.failureCount >= this.failureThreshold) {
            // Exceeded threshold, open circuit
            this.state = CircuitState.OPEN;
            this.nextAttempt = Date.now() + this.timeout;
        }
    }
    /**
     * Get current circuit state.
     */
    getState() {
        return this.state;
    }
    /**
     * Get failure count.
     */
    getFailureCount() {
        return this.failureCount;
    }
    /**
     * Get success count (in half-open state).
     */
    getSuccessCount() {
        return this.successCount;
    }
    /**
     * Manually reset circuit breaker.
     */
    reset() {
        this.state = CircuitState.CLOSED;
        this.failureCount = 0;
        this.successCount = 0;
        this.nextAttempt = 0;
    }
}
exports.CircuitBreakerMiddleware = CircuitBreakerMiddleware;
/**
 * Create circuit breaker middleware function.
 *
 * @param config Circuit breaker configuration
 * @returns Middleware function
 */
function circuitBreaker(config = {}) {
    return (agent) => new CircuitBreakerMiddleware(agent, config);
}
