"use strict";
/**
 * Timeout middleware - prevents long-running requests.
 *
 * Automatically cancels requests that exceed a time limit.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.TimeoutMiddleware = exports.TimeoutError = void 0;
exports.timeout = timeout;
const base_1 = require("./base");
/**
 * Timeout error.
 */
class TimeoutError extends Error {
    constructor(timeout) {
        super(`Request timeout after ${timeout}ms`);
        this.name = 'TimeoutError';
    }
}
exports.TimeoutError = TimeoutError;
/**
 * TimeoutMiddleware implements request timeout.
 *
 * Features:
 * - Configurable timeout
 * - Automatic cancellation
 * - Clear error messages
 *
 * Usage:
 *   const agent = new TimeoutMiddleware(baseAgent, {
 *     timeout: 30000, // 30 seconds
 *   });
 */
class TimeoutMiddleware extends base_1.BaseMiddleware {
    constructor(agent, config) {
        super(agent);
        this.timeout = config.timeout;
    }
    async process(message) {
        return Promise.race([
            this.agent.process(message),
            new Promise((_, reject) => setTimeout(() => reject(new TimeoutError(this.timeout)), this.timeout)),
        ]);
    }
}
exports.TimeoutMiddleware = TimeoutMiddleware;
/**
 * Create timeout middleware function.
 *
 * @param config Timeout configuration
 * @returns Middleware function
 */
function timeout(config) {
    return (agent) => new TimeoutMiddleware(agent, config);
}
