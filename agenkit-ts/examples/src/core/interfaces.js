"use strict";
/**
 * Core interfaces for agenkit TypeScript implementation.
 *
 * Minimal, composable interfaces for AI agents with focus on:
 * - Simplicity: Few required methods
 * - Composability: Easy to wrap and extend
 * - Type safety: Full TypeScript support
 * - Performance: Minimal overhead
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.createMessage = createMessage;
exports.validateMessage = validateMessage;
/**
 * Helper function to create a Message with defaults.
 *
 * @param role Message role or message object
 * @param content Message content (if role is string)
 * @param metadata Optional metadata (if role is string)
 * @returns Complete message with timestamp
 */
function createMessage(role, content, metadata) {
    // Object syntax: createMessage({ role, content })
    if (typeof role === 'object') {
        return {
            role: role.role || 'user',
            content: role.content,
            metadata: role.metadata || {},
            timestamp: role.timestamp || new Date().toISOString(),
        };
    }
    // Positional syntax: createMessage('user', 'Hello')
    return {
        role,
        content,
        metadata: metadata || {},
        timestamp: new Date().toISOString(),
    };
}
/**
 * Helper function to validate a message.
 *
 * @param message Message to validate
 * @throws Error if message is invalid
 */
function validateMessage(message) {
    if (!message.role || typeof message.role !== 'string') {
        throw new Error('Message role must be a non-empty string');
    }
    if (message.content === undefined || message.content === null) {
        throw new Error('Message content cannot be undefined or null');
    }
}
