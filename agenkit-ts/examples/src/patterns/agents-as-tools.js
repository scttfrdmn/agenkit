"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.AgentTool = exports.OutputFormat = void 0;
exports.createAgentTool = createAgentTool;
exports.createAgentToolSimple = createAgentToolSimple;
const interfaces_1 = require("../core/interfaces");
/** Output format for agent responses */
var OutputFormat;
(function (OutputFormat) {
    /** Just the message content as a string */
    OutputFormat["STRING"] = "string";
    /** Object with content and metadata */
    OutputFormat["DICT"] = "dict";
    /** Full Message object */
    OutputFormat["MESSAGE"] = "message";
})(OutputFormat || (exports.OutputFormat = OutputFormat = {}));
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
class AgentTool {
    constructor(config) {
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
    async execute(params) {
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
            const message = (0, interfaces_1.createMessage)('user', String(input));
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
        }
        catch (error) {
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
    formatOutput(response) {
        switch (this.outputFormat) {
            case OutputFormat.STRING:
                return String(response.content);
            case OutputFormat.DICT:
                const result = {
                    content: response.content,
                };
                if (this.includeMetadata) {
                    result.metadata = response.metadata;
                }
                return result;
            case OutputFormat.MESSAGE:
                return response;
            default:
                return String(response.content);
        }
    }
    /**
     * Get the underlying agent (useful for testing/inspection).
     */
    getAgent() {
        return this.agent;
    }
    /**
     * Get the input parameter key.
     */
    getInputKey() {
        return this.inputKey;
    }
    /**
     * Get the output format setting.
     */
    getOutputFormat() {
        return this.outputFormat;
    }
    /**
     * String representation of the tool.
     */
    toString() {
        return `AgentTool(name='${this.name}', agent=${this.agent.name})`;
    }
}
exports.AgentTool = AgentTool;
/**
 * Create an agent tool with full configuration options.
 *
 * @param config AgentTool configuration
 * @returns AgentTool instance
 */
function createAgentTool(config) {
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
function createAgentToolSimple(agent, name, description) {
    return new AgentTool({
        agent,
        name,
        description,
    });
}
