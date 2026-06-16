/**
 * Agents-as-Tools Pattern - Hierarchical Agent Delegation
 *
 * The Agents-as-Tools pattern enables agents to call other agents as tools,
 * creating hierarchical multi-agent systems where specialized agents can be
 * invoked by supervisor agents.
 *
 * Key Concepts:
 * - Supervisor Agent: Coordinates and delegates to specialist agents
 * - Specialist Agents: Wrapped as tools with specific capabilities
 * - Hierarchical Composition: Build complex systems from simple agents
 * - Tool Interface: Agents become tools compatible with existing infrastructure
 *
 * Use Cases:
 * - Multi-domain problem solving (routing to experts)
 * - Complex task decomposition
 * - Agent specialization and expertise
 * - Scalable agent architectures
 *
 * Example:
 * ```typescript
 * const specialist = new CodeSpecialistAgent();
 * const tool = createAgentTool({
 *   agent: specialist,
 *   name: 'code_expert',
 *   description: 'Expert programmer for code-related tasks'
 * });
 *
 * const result = await tool.execute({ query: 'Write a sorting function' });
 * console.log(result.output); // Generated code
 * ```
 *
 * Performance Characteristics:
 * - Latency: Same as underlying agent
 * - Enables hierarchical composition
 * - Maintains full observability (traces preserved)
 */

import { Agent, Message, Tool, ToolResult, createMessage } from '../core/interfaces';

/** Output format for agent responses */
export enum OutputFormat {
  /** Just the message content as a string */
  STRING = 'string',
  /** Object with content and metadata */
  DICT = 'dict',
  /** Full Message object */
  MESSAGE = 'message',
}

/**
 * Configuration for creating an AgentTool.
 */
export interface AgentToolConfig {
  /** Agent to wrap as a tool */
  agent: Agent;
  /** Tool name for identification */
  name: string;
  /** Description for LLM tool selection */
  description: string;
  /** Parameter name for input (default: 'query') */
  inputKey?: string;
  /** How to format output (default: STRING) */
  outputFormat?: OutputFormat;
  /** Include agent metadata in output (default: false) */
  includeMetadata?: boolean;
}

/**
 * Wraps an agent as a tool for hierarchical delegation.
 *
 * Allows agents to invoke other agents as tools, enabling:
 * - Supervisor agents that route to specialists
 * - Hierarchical multi-agent systems
 * - Agent specialization and composition
 *
 * Example:
 * ```typescript
 * const codeAgent = new CodeSpecialistAgent();
 * const codeTool = new AgentTool({
 *   agent: codeAgent,
 *   name: 'code_expert',
 *   description: 'Expert in programming and code review'
 * });
 *
 * // Use in supervisor
 * const result = await codeTool.execute({
 *   query: 'Implement quicksort in TypeScript'
 * });
 * ```
 */
export class AgentTool implements Tool {
  readonly name: string;
  readonly description: string;
  readonly parametersSchema?: Record<string, unknown>;

  private agent: Agent;
  private inputKey: string;
  private outputFormat: OutputFormat;
  private includeMetadata: boolean;

  constructor(config: AgentToolConfig) {
    // Validation
    if (!config.agent) {
      throw new Error('agent is required');
    }
    if (!config.name || config.name.trim() === '') {
      throw new Error('tool name cannot be empty');
    }
    if (!config.description || config.description.trim() === '') {
      throw new Error('tool description cannot be empty');
    }

    this.agent = config.agent;
    this.name = config.name;
    this.description = config.description;
    this.inputKey = config.inputKey || 'query';
    this.outputFormat = config.outputFormat || OutputFormat.STRING;
    this.includeMetadata = config.includeMetadata || false;

    // Generate JSON schema for parameters
    this.parametersSchema = {
      type: 'object',
      properties: {
        [this.inputKey]: {
          type: 'string',
          description: 'Input to the agent',
        },
      },
      required: [this.inputKey],
    };
  }

  /**
   * Execute the wrapped agent.
   *
   * @param params Parameters containing the input key
   * @returns Tool result with formatted agent output
   */
  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    // Extract input
    const input = params[this.inputKey];
    if (input === undefined || input === null) {
      const availableKeys = Object.keys(params);
      return {
        output: null,
        success: false,
        error: `Missing required parameter '${this.inputKey}'. Available: ${availableKeys.join(', ')}`,
      };
    }

    try {
      // Create message and call agent
      const message = createMessage('user', String(input));
      const response = await this.agent.process(message);

      // Format output based on configuration
      const output = this.formatOutput(response);

      // Create result with metadata
      return {
        output,
        success: true,
        metadata: {
          agentName: this.agent.name,
          toolName: this.name,
        },
      };
    } catch (error) {
      return {
        output: null,
        success: false,
        error: `Agent '${this.agent.name}' failed: ${error instanceof Error ? error.message : String(error)}`,
      };
    }
  }

  /**
   * Format agent response based on output format setting.
   */
  private formatOutput(response: Message): unknown {
    switch (this.outputFormat) {
      case OutputFormat.STRING:
        return String(response.content);

      case OutputFormat.DICT: {
        const result: Record<string, unknown> = {
          content: response.content,
        };
        if (this.includeMetadata) {
          result.metadata = response.metadata;
        }
        return result;
      }

      case OutputFormat.MESSAGE:
        return response;

      default:
        return String(response.content);
    }
  }

  /**
   * Get the underlying agent (useful for testing/inspection).
   */
  getAgent(): Agent {
    return this.agent;
  }

  /**
   * Get the input parameter key.
   */
  getInputKey(): string {
    return this.inputKey;
  }

  /**
   * Get the output format setting.
   */
  getOutputFormat(): OutputFormat {
    return this.outputFormat;
  }

  /**
   * String representation of the tool.
   */
  toString(): string {
    return `AgentTool(name='${this.name}', agent=${this.agent.name})`;
  }
}

/**
 * Create an agent tool with full configuration options.
 *
 * @param config AgentTool configuration
 * @returns AgentTool instance
 */
export function createAgentTool(config: AgentToolConfig): AgentTool {
  return new AgentTool(config);
}

/**
 * Create an agent tool with simple defaults.
 *
 * Uses default values:
 * - inputKey: 'query'
 * - outputFormat: STRING
 * - includeMetadata: false
 *
 * @param agent Agent to wrap
 * @param name Tool name
 * @param description Tool description
 * @returns AgentTool instance
 */
export function createAgentToolSimple(
  agent: Agent,
  name: string,
  description: string
): AgentTool {
  return new AgentTool({
    agent,
    name,
    description,
  });
}
