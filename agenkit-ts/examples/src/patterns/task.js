"use strict";
/**
 * Task pattern for one-shot agent execution with lifecycle management.
 *
 * This module provides the Task pattern, which wraps an Agent for single-use
 * execution with automatic resource cleanup.
 *
 * Key Features:
 * - One-shot execution semantics
 * - Automatic resource cleanup
 * - Timeout support
 * - Retry logic with exponential backoff
 * - Prevention of reuse after completion
 * - Context manager support (async)
 *
 * Example:
 * ```typescript
 * // Basic usage
 * const task = new Task(agent, { timeout: 30000, retries: 2 });
 * try {
 *   const result = await task.execute(message);
 *   console.log(result.content);
 * } finally {
 *   await task.cleanup();
 * }
 *
 * // With context manager pattern
 * await Task.withTask(agent, async (task) => {
 *   const result = await task.execute(message);
 *   return result;
 * });
 * ```
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.TimeoutError = exports.Task = void 0;
exports.executeTask = executeTask;
/**
 * One-shot agent execution with lifecycle management.
 *
 * A Task wraps an Agent for single-use execution, providing:
 * - Explicit one-shot semantics
 * - Automatic resource cleanup
 * - Task-specific configuration (timeout, retries)
 * - Prevention of reuse after completion
 *
 * Key Distinction:
 * - **Agent**: Multi-turn conversation with state
 * - **Task**: One-shot execution, then cleanup
 *
 * Use Task when:
 * - Single purpose operation that needs cleanup
 * - You want explicit resource management
 * - You need timeout/retry at task level
 *
 * Examples: summarize_document, classify_text, extract_entities
 */
class Task {
    constructor(agent, config = {}) {
        this.agent = agent;
        this.timeout = config.timeout;
        this.retries = config.retries || 0;
        this.config = config;
        this._completed = false;
    }
    /**
     * Execute the task once.
     *
     * This method can only be called once per Task instance. After execution
     * completes (successfully or with error), the Task is marked as completed
     * and cannot be reused.
     *
     * @param message Input message for the agent
     * @returns The agent's response
     * @throws RuntimeError if task already completed
     * @throws TimeoutError if execution exceeds timeout
     */
    async execute(message) {
        if (this._completed) {
            throw new Error('Task already completed. Create a new Task for another execution.');
        }
        const attempts = this.retries + 1; // retries=0 means 1 attempt
        let lastError;
        for (let attempt = 0; attempt < attempts; attempt++) {
            try {
                // Execute with optional timeout
                const result = this.timeout
                    ? await this.withTimeout(this.agent.process(message), this.timeout)
                    : await this.agent.process(message);
                // Success - mark completed and return
                this._completed = true;
                this._result = result;
                return result;
            }
            catch (error) {
                lastError = error instanceof Error ? error : new Error(String(error));
                // If timeout, don't retry
                if (error instanceof TimeoutError) {
                    this._completed = true;
                    await this.cleanup();
                    throw error;
                }
                // If this was the last attempt, fail
                if (attempt === attempts - 1) {
                    this._completed = true;
                    await this.cleanup();
                    throw error;
                }
                // Otherwise, retry after exponential backoff
                await this.sleep(100 * (attempt + 1));
            }
        }
        // Should never reach here, but just in case
        this._completed = true;
        await this.cleanup();
        throw lastError || new Error('Task execution failed');
    }
    /**
     * Clean up resources after task completion.
     *
     * This method is called automatically when:
     * - Task execution completes successfully
     * - Task execution fails with an error
     * - Using withTask() (automatic cleanup)
     *
     * Override this method in subclasses to add custom cleanup logic:
     * - Close network connections
     * - Release memory/resources
     * - Save state to disk
     * - Send telemetry
     */
    async cleanup() {
        // Default implementation - hook for subclasses
        // Could close agent connections, release middleware resources, etc.
    }
    /**
     * Check if the task has been completed.
     */
    get completed() {
        return this._completed;
    }
    /**
     * Get the result of the task (if completed successfully).
     */
    get result() {
        return this._result;
    }
    /**
     * Execute a function with timeout.
     */
    async withTimeout(promise, timeoutMs) {
        return Promise.race([
            promise,
            new Promise((_, reject) => setTimeout(() => reject(new TimeoutError(`Task timed out after ${timeoutMs}ms`)), timeoutMs)),
        ]);
    }
    /**
     * Sleep for specified milliseconds.
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    /**
     * Context manager pattern for automatic cleanup.
     *
     * @param agent Agent to execute
     * @param fn Function to execute with the task
     * @param config Task configuration
     * @returns Result from the function
     *
     * @example
     * ```typescript
     * const result = await Task.withTask(agent, async (task) => {
     *   return await task.execute(message);
     * });
     * ```
     */
    static async withTask(agent, fn, config) {
        const task = new Task(agent, config);
        try {
            return await fn(task);
        }
        finally {
            await task.cleanup();
        }
    }
}
exports.Task = Task;
/**
 * Timeout error for task execution.
 */
class TimeoutError extends Error {
    constructor(message) {
        super(message);
        this.name = 'TimeoutError';
    }
}
exports.TimeoutError = TimeoutError;
/**
 * Execute a task with automatic cleanup.
 *
 * Convenience function that wraps Task creation, execution, and cleanup.
 *
 * @param agent Agent to execute
 * @param message Input message
 * @param config Task configuration
 * @returns Agent response
 *
 * @example
 * ```typescript
 * const result = await executeTask(
 *   agent,
 *   createMessage('user', 'Summarize this document'),
 *   { timeout: 30000, retries: 2 }
 * );
 * ```
 */
async function executeTask(agent, message, config) {
    return Task.withTask(agent, async (task) => task.execute(message), config);
}
