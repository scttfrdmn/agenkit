/**
 * Conditional agent composition pattern.
 *
 * Routes messages to different agents based on conditions.
 */

import type { Agent, Message } from '../core/interfaces.js';

/**
 * Condition function type.
 *
 * Returns true if the message should be routed to the associated agent.
 */
export type Condition = (message: Message) => boolean;

/**
 * Represents a condition-agent pair.
 */
export interface ConditionalRoute {
  condition: Condition;
  agent: Agent;
}

/**
 * Agent that routes messages to different agents based on conditions.
 *
 * Evaluates conditions in order and routes to the first matching agent.
 * Falls back to default agent if no condition matches.
 *
 * @example
 * ```typescript
 * const conditional = new ConditionalAgent('router', defaultAgent);
 *
 * conditional.addRoute(
 *   (msg) => msg.content.includes('technical'),
 *   technicalAgent
 * );
 *
 * conditional.addRoute(
 *   (msg) => msg.content.includes('general'),
 *   generalAgent
 * );
 *
 * const result = await conditional.process(message);
 * ```
 */
export class ConditionalAgent implements Agent {
  readonly name: string;
  private routes: ConditionalRoute[] = [];
  private defaultAgent: Agent;

  /**
   * Create a new conditional agent.
   *
   * @param name - Name of this conditional agent
   * @param defaultAgent - Agent to use when no condition matches
   */
  constructor(name: string, defaultAgent: Agent) {
    this.name = name;
    this.defaultAgent = defaultAgent;
  }

  /**
   * Add a conditional route.
   *
   * @param condition - Function that returns true if this agent should be used
   * @param agent - Agent to use when condition is met
   */
  addRoute(condition: Condition, agent: Agent): void {
    this.routes.push({ condition, agent });
  }

  /**
   * Get combined capabilities of all agents.
   */
  get capabilities(): string[] {
    const capsSet = new Set<string>();

    // Add default agent capabilities
    if (this.defaultAgent.capabilities) {
      for (const cap of this.defaultAgent.capabilities) {
        capsSet.add(cap);
      }
    }

    // Add route agent capabilities
    for (const route of this.routes) {
      if (route.agent.capabilities) {
        for (const cap of route.agent.capabilities) {
          capsSet.add(cap);
        }
      }
    }

    const caps = Array.from(capsSet);
    caps.push('conditional');
    return caps;
  }

  /**
   * Route the message to the first agent whose condition is met.
   *
   * @param message - Input message
   * @returns Response from the selected agent
   * @throws Error if agent execution fails
   */
  async process(message: Message): Promise<Message> {
    // Try each route in order
    for (let i = 0; i < this.routes.length; i++) {
      const route = this.routes[i];

      if (route.condition(message)) {
        try {
          const result = await route.agent.process(message);

          // Add metadata about routing decision
          result.metadata = result.metadata || {};
          result.metadata.conditional_agent_used = route.agent.name;
          result.metadata.conditional_route = i + 1;

          return result;
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : String(error);
          throw new Error(
            `Route ${i + 1} (${route.agent.name}) failed: ${errorMessage}`,
          );
        }
      }
    }

    // No condition matched, use default agent
    try {
      const result = await this.defaultAgent.process(message);

      // Add metadata about using default
      result.metadata = result.metadata || {};
      result.metadata.conditional_agent_used = this.defaultAgent.name;
      result.metadata.conditional_route = 'default';

      return result;
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      throw new Error(
        `Default agent (${this.defaultAgent.name}) failed: ${errorMessage}`,
      );
    }
  }

  /**
   * Get the conditional routes.
   */
  getRoutes(): ConditionalRoute[] {
    return this.routes;
  }

  /**
   * Get the default agent.
   */
  getDefaultAgent(): Agent {
    return this.defaultAgent;
  }
}

// ==========================
// Common condition helpers
// ==========================

/**
 * Return a condition that checks if message content contains a substring.
 *
 * @param substr - Substring to search for
 * @returns Condition function
 */
export function contentContains(substr: string): Condition {
  return (message: Message): boolean => {
    return typeof message.content === 'string' && message.content.includes(substr);
  };
}

/**
 * Return a condition that checks if message role equals the given role.
 *
 * @param role - Role to check for
 * @returns Condition function
 */
export function roleEquals(role: string): Condition {
  return (message: Message): boolean => {
    return message.role === role;
  };
}

/**
 * Return a condition that checks if metadata contains a key.
 *
 * @param key - Metadata key to check for
 * @returns Condition function
 */
export function metadataHasKey(key: string): Condition {
  return (message: Message): boolean => {
    return message.metadata ? key in message.metadata : false;
  };
}

/**
 * Return a condition that checks if metadata key equals value.
 *
 * @param key - Metadata key to check
 * @param value - Expected value
 * @returns Condition function
 */
export function metadataEquals(key: string, value: unknown): Condition {
  return (message: Message): boolean => {
    return message.metadata ? message.metadata[key] === value : false;
  };
}

/**
 * Combine multiple conditions with AND logic.
 *
 * @param conditions - Conditions to combine
 * @returns Combined condition function
 */
export function andConditions(...conditions: Condition[]): Condition {
  return (message: Message): boolean => {
    return conditions.every((cond) => cond(message));
  };
}

/**
 * Combine multiple conditions with OR logic.
 *
 * @param conditions - Conditions to combine
 * @returns Combined condition function
 */
export function orConditions(...conditions: Condition[]): Condition {
  return (message: Message): boolean => {
    return conditions.some((cond) => cond(message));
  };
}

/**
 * Negate a condition.
 *
 * @param cond - Condition to negate
 * @returns Negated condition function
 */
export function notCondition(cond: Condition): Condition {
  return (message: Message): boolean => {
    return !cond(message);
  };
}
