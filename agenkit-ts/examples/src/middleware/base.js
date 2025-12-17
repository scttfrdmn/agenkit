"use strict";
/**
 * Base middleware definitions for agent wrapping.
 *
 * Middleware wraps agents to add cross-cutting concerns like:
 * - Retry logic
 * - Circuit breaking
 * - Timeouts
 * - Logging
 * - Metrics
 * - Caching
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.BaseMiddleware = void 0;
exports.applyMiddleware = applyMiddleware;
/**
 * Apply multiple middleware to an agent.
 *
 * Middleware is applied in order, so the first middleware in the array
 * is the outermost wrapper (executes first).
 *
 * @param agent Base agent
 * @param middleware Array of middleware to apply
 * @returns Wrapped agent
 *
 * Usage:
 *   const wrapped = applyMiddleware(
 *     agent,
 *     [retryMiddleware, timeoutMiddleware, loggingMiddleware]
 *   );
 */
function applyMiddleware(agent, middleware) {
    return middleware.reduce((wrapped, mw) => mw(wrapped), agent);
}
/**
 * Base class for middleware implementations.
 *
 * Provides common functionality for wrapping agents.
 */
class BaseMiddleware {
    constructor(agent) {
        this.agent = agent;
    }
    get name() {
        return this.agent.name;
    }
    get capabilities() {
        return this.agent.capabilities;
    }
    async *processStream(message) {
        if (!this.agent.processStream) {
            throw new Error(`Agent ${this.agent.name} does not support streaming`);
        }
        yield* this.agent.processStream(message);
    }
}
exports.BaseMiddleware = BaseMiddleware;
