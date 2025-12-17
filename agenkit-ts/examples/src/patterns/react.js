"use strict";
/**
 * ReAct Pattern - Reasoning + Acting
 *
 * The ReAct pattern combines reasoning (thinking through a problem) with acting
 * (using tools to gather information or take actions). The agent alternates between:
 * 1. Thought: Reasoning about what to do next
 * 2. Action: Executing a tool to gather information or take action
 * 3. Observation: Receiving the result of the action
 *
 * This pattern is based on the paper "ReAct: Synergizing Reasoning and Acting in
 * Language Models" and enables agents to dynamically reason about and interact with
 * their environment through tool use.
 *
 * Key Concepts:
 * - Interleaved reasoning and acting
 * - Tool-augmented agent behavior
 * - Observable decision-making process
 * - Self-directed exploration
 *
 * Example:
 * ```typescript
 * const tools = [searchTool, calculatorTool, weatherTool];
 * const reactAgent = new ReActAgent({
 *   agent: llmAgent,
 *   tools,
 *   maxSteps: 10
 * });
 *
 * const result = await reactAgent.process(
 *   createMessage('user', 'What is the weather in San Francisco?')
 * );
 * ```
 *
 * Performance Characteristics:
 * - Steps: O(maxSteps) - bounded by configuration
 * - Each step: agent inference + optional tool execution
 * - Memory: O(steps) for conversation history
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ReActAgent = exports.ReActStopReason = void 0;
exports.createReActAgent = createReActAgent;
const interfaces_1 = require("../core/interfaces");
/** Reason why ReAct loop terminated */
var ReActStopReason;
(function (ReActStopReason) {
    /** Agent provided final answer */
    ReActStopReason["FINAL_ANSWER"] = "final_answer";
    /** Reached maximum number of steps */
    ReActStopReason["MAX_STEPS"] = "max_steps";
    /** Agent made invalid action */
    ReActStopReason["INVALID_ACTION"] = "invalid_action";
    /** Tool execution failed */
    ReActStopReason["TOOL_ERROR"] = "tool_error";
})(ReActStopReason || (exports.ReActStopReason = ReActStopReason = {}));
/**
 * ReAct agent that combines reasoning with tool use.
 *
 * The agent follows this loop:
 * 1. Think: Reason about what to do next
 * 2. Act: Use a tool to gather information or take action
 * 3. Observe: See the result and incorporate into reasoning
 * 4. Repeat until final answer or max steps
 *
 * Expected agent response format:
 * ```
 * Thought: [reasoning about what to do]
 * Action: [tool name]
 * Action Input: [tool input]
 * ```
 *
 * Or for final answer:
 * ```
 * Thought: [reasoning about conclusion]
 * Final Answer: [the final answer]
 * ```
 */
class ReActAgent {
    constructor(config) {
        // Validation
        if (!config.agent) {
            throw new Error('agent is required');
        }
        if (!config.tools || config.tools.length === 0) {
            throw new Error('at least one tool is required');
        }
        this.agent = config.agent;
        this.tools = new Map(config.tools.map(t => [t.name, t]));
        this.maxSteps = config.maxSteps || 10;
        this.verbose = config.verbose !== undefined ? config.verbose : true;
        this.name = 'ReActAgent';
        this.steps = [];
        // Default prompt template
        this.promptTemplate =
            config.promptTemplate ||
                this.buildDefaultPrompt(Array.from(this.tools.values()));
    }
    /**
     * Build default prompt template with tool descriptions.
     */
    buildDefaultPrompt(tools) {
        const toolDescriptions = tools
            .map(t => `- ${t.name}: ${t.description}`)
            .join('\n');
        return `You are a helpful assistant that can use tools to answer questions.

Available tools:
${toolDescriptions}

Use the following format:

Thought: Think about what to do next
Action: [tool name]
Action Input: [input for the tool]
Observation: [result will be provided]

... (repeat Thought/Action/Observation as needed)

Thought: I now know the final answer
Final Answer: [your final answer here]

Begin!`;
    }
    /**
     * Execute the ReAct reasoning-acting loop.
     */
    async process(message) {
        this.steps = [];
        const conversationHistory = [];
        // Initial prompt
        conversationHistory.push(this.promptTemplate);
        conversationHistory.push(`\nQuestion: ${message.content}`);
        for (let step = 0; step < this.maxSteps; step++) {
            // Get agent's reasoning
            const prompt = conversationHistory.join('\n');
            const response = await this.agent.process((0, interfaces_1.createMessage)('user', prompt));
            const responseText = String(response.content);
            // Parse the response
            const parsed = this.parseResponse(responseText);
            // Check for final answer
            if (parsed.isFinal) {
                this.steps.push(parsed);
                return this.formatFinalAnswer(parsed, ReActStopReason.FINAL_ANSWER);
            }
            // Validate action
            if (!parsed.action) {
                this.steps.push(parsed);
                return this.formatFinalAnswer(parsed, ReActStopReason.INVALID_ACTION);
            }
            // Execute action
            const tool = this.tools.get(parsed.action);
            if (!tool) {
                parsed.observation = `Error: Tool '${parsed.action}' not found. Available tools: ${Array.from(this.tools.keys()).join(', ')}`;
                this.steps.push(parsed);
                conversationHistory.push(this.formatStep(parsed));
                continue;
            }
            try {
                const result = await tool.execute({ input: parsed.actionInput });
                if (result.success) {
                    parsed.observation = String(result.output);
                }
                else {
                    parsed.observation = `Error: ${result.error || 'Tool execution failed'}`;
                }
            }
            catch (error) {
                parsed.observation = `Error: ${error instanceof Error ? error.message : String(error)}`;
                this.steps.push(parsed);
                return this.formatFinalAnswer(parsed, ReActStopReason.TOOL_ERROR);
            }
            // Record step and add to conversation
            this.steps.push(parsed);
            conversationHistory.push(this.formatStep(parsed));
        }
        // Max steps reached
        const lastStep = this.steps[this.steps.length - 1] || {
            thought: 'Reached maximum steps without finding answer',
            isFinal: false,
        };
        return this.formatFinalAnswer(lastStep, ReActStopReason.MAX_STEPS);
    }
    /**
     * Parse agent response into structured step.
     */
    parseResponse(response) {
        const lines = response.split('\n').map(l => l.trim());
        const step = {
            thought: '',
            isFinal: false,
        };
        for (const line of lines) {
            if (line.startsWith('Thought:')) {
                step.thought = line.substring('Thought:'.length).trim();
            }
            else if (line.startsWith('Action:')) {
                step.action = line.substring('Action:'.length).trim();
            }
            else if (line.startsWith('Action Input:')) {
                step.actionInput = line.substring('Action Input:'.length).trim();
            }
            else if (line.startsWith('Final Answer:')) {
                step.thought = step.thought || 'Reached final answer';
                step.observation = line.substring('Final Answer:'.length).trim();
                step.isFinal = true;
                break;
            }
        }
        return step;
    }
    /**
     * Format step for conversation history.
     */
    formatStep(step) {
        let formatted = `Thought: ${step.thought}`;
        if (step.action) {
            formatted += `\nAction: ${step.action}`;
            formatted += `\nAction Input: ${step.actionInput || ''}`;
        }
        if (step.observation) {
            formatted += `\nObservation: ${step.observation}`;
        }
        return formatted;
    }
    /**
     * Format final answer message.
     */
    formatFinalAnswer(step, stopReason) {
        let content = '';
        if (this.verbose) {
            // Include full reasoning trace
            content = this.steps.map(s => this.formatStep(s)).join('\n\n');
            content += '\n\n---\n\n';
        }
        // Add final answer
        if (stopReason === ReActStopReason.FINAL_ANSWER) {
            content += step.observation || 'No final answer provided';
        }
        else {
            content += `Unable to complete task (${stopReason})`;
            if (step.thought) {
                content += `\nLast thought: ${step.thought}`;
            }
        }
        return (0, interfaces_1.createMessage)('assistant', content, {
            stopReason,
            steps: this.steps.length,
            reasoning: this.steps,
        });
    }
    /**
     * Get the reasoning history (useful for debugging/analysis).
     */
    getSteps() {
        return [...this.steps];
    }
    get capabilities() {
        return ['reasoning', 'tool-use', 'react'];
    }
}
exports.ReActAgent = ReActAgent;
/**
 * Create a ReAct agent with simple configuration.
 *
 * @param agent Agent to use for reasoning
 * @param tools Tools available to the agent
 * @param maxSteps Maximum number of steps (default: 10)
 * @returns ReActAgent instance
 */
function createReActAgent(agent, tools, maxSteps) {
    return new ReActAgent({ agent, tools, maxSteps });
}
