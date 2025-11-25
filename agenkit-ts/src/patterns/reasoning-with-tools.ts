/**
 * Tool-Use During Reasoning Pattern
 *
 * Enables interleaved reasoning and tool usage, where tools can be called
 * DURING the reasoning process rather than only after reasoning completes.
 *
 * This pattern is inspired by Claude 4 and o3's extended thinking capabilities,
 * where the model can use tools to refine its reasoning in real-time.
 *
 * Key differences from ReAct:
 * - ReAct: Observe → Think → Act → Observe → Think → Act (sequential)
 * - This: Think ↔ Act (interleaved, tools available during thinking)
 * - Tools help refine reasoning, not just execute actions
 * - Supports extended thinking with tool integration
 *
 * Example:
 * ```typescript
 * import { ReasoningWithToolsAgent } from 'agenkit';
 *
 * const agent = new ReasoningWithToolsAgent(
 *   llm,
 *   [calculator, webSearch, database],
 *   { maxReasoningSteps: 10 }
 * );
 *
 * // Agent can use tools WHILE reasoning about the problem
 * const response = await agent.process(createMessage(
 *   'user',
 *   "What's the total cost if I buy 3 items at $15.99 each with 8.5% tax?"
 * ));
 *
 * // Agent might:
 * // 1. Start reasoning about the problem
 * // 2. Call calculator tool: 3 * 15.99 = 47.97
 * // 3. Continue reasoning with that result
 * // 4. Call calculator tool: 47.97 * 1.085 = 52.05
 * // 5. Complete reasoning with final answer
 * ```
 */

import { Agent, Message, Tool, ToolResult, createMessage } from '../core/interfaces';

/**
 * Type of reasoning step.
 */
export enum ReasoningStepType {
  THINKING = 'thinking',
  TOOL_CALL = 'tool_call',
  TOOL_RESULT = 'tool_result',
  CONCLUSION = 'conclusion',
}

/**
 * A single step in the reasoning process.
 */
export interface ReasoningStep {
  /** Step number */
  stepNumber: number;
  /** Type of step */
  stepType: ReasoningStepType;
  /** Step content */
  content: string;
  /** Tool name (if tool call) */
  toolName?: string;
  /** Tool parameters (if tool call) */
  toolParameters?: Record<string, any>;
  /** Tool result (if tool result) */
  toolResult?: any;
  /** Confidence score */
  confidence?: number;
  /** Timestamp */
  timestamp: number;
}

/**
 * Complete trace of reasoning process.
 */
export interface ReasoningTrace {
  /** All reasoning steps */
  steps: ReasoningStep[];
  /** Total tools used */
  totalToolsUsed: number;
  /** Total thinking steps */
  totalThinkingSteps: number;
  /** Start time */
  startTime: number;
  /** End time */
  endTime?: number;
}

/**
 * Configuration for ReasoningWithToolsAgent.
 */
export interface ReasoningWithToolsConfig {
  /** Maximum reasoning steps */
  maxReasoningSteps?: number;
  /** Custom tool use prompt */
  toolUsePrompt?: string;
  /** Enable reasoning trace */
  enableTrace?: boolean;
  /** Confidence threshold */
  confidenceThreshold?: number;
}

/**
 * Create a reasoning step.
 */
export function createReasoningStep(
  stepNumber: number,
  stepType: ReasoningStepType,
  content: string,
  options?: {
    toolName?: string;
    toolParameters?: Record<string, any>;
    toolResult?: any;
    confidence?: number;
  }
): ReasoningStep {
  return {
    stepNumber,
    stepType,
    content,
    toolName: options?.toolName,
    toolParameters: options?.toolParameters,
    toolResult: options?.toolResult,
    confidence: options?.confidence,
    timestamp: Date.now(),
  };
}

/**
 * Create a reasoning trace.
 */
export function createReasoningTrace(): ReasoningTrace {
  return {
    steps: [],
    totalToolsUsed: 0,
    totalThinkingSteps: 0,
    startTime: Date.now(),
  };
}

/**
 * Add a step to reasoning trace.
 */
export function addStepToTrace(trace: ReasoningTrace, step: ReasoningStep): void {
  trace.steps.push(step);

  if (step.stepType === ReasoningStepType.THINKING) {
    trace.totalThinkingSteps++;
  } else if (step.stepType === ReasoningStepType.TOOL_CALL) {
    trace.totalToolsUsed++;
  }
}

/**
 * Finalize reasoning trace.
 */
export function finalizeTrace(trace: ReasoningTrace): void {
  trace.endTime = Date.now();
}

/**
 * Get trace duration in seconds.
 */
export function getTraceDuration(trace: ReasoningTrace): number {
  const end = trace.endTime || Date.now();
  return (end - trace.startTime) / 1000;
}

/**
 * Convert reasoning trace to dictionary.
 */
export function traceToDict(trace: ReasoningTrace): Record<string, any> {
  return {
    steps: trace.steps.map(step => ({
      step_number: step.stepNumber,
      step_type: step.stepType,
      content: step.content,
      tool_name: step.toolName,
      tool_parameters: step.toolParameters,
      tool_result: step.toolResult,
      confidence: step.confidence,
      timestamp: step.timestamp,
    })),
    total_tools_used: trace.totalToolsUsed,
    total_thinking_steps: trace.totalThinkingSteps,
    duration_seconds: getTraceDuration(trace),
  };
}

/**
 * Agent that can use tools during reasoning (not just after).
 *
 * This pattern enables the model to:
 * 1. Start reasoning about a problem
 * 2. Realize it needs information
 * 3. Call a tool to get that information
 * 4. Continue reasoning with the new information
 * 5. Repeat as needed
 *
 * This is different from ReAct where:
 * - Reasoning happens BEFORE action
 * - Action is taken BASED ON completed reasoning
 * - New observation triggers NEW reasoning
 */
export class ReasoningWithToolsAgent implements Agent {
  readonly name: string;

  private llm: Agent;
  private tools: Map<string, Tool>;
  private maxReasoningSteps: number;
  private toolUsePrompt: string;
  private enableTrace: boolean;
  private confidenceThreshold: number;

  constructor(llm: Agent, tools: Tool[], config?: ReasoningWithToolsConfig) {
    this.llm = llm;
    this.tools = new Map(tools.map(t => [t.name, t]));
    this.maxReasoningSteps = config?.maxReasoningSteps ?? 20;
    this.toolUsePrompt = config?.toolUsePrompt ?? this.defaultToolPrompt();
    this.enableTrace = config?.enableTrace ?? true;
    this.confidenceThreshold = config?.confidenceThreshold ?? 0.8;
    this.name = `reasoning_with_tools_${llm.name}`;
  }

  /**
   * Generate default tool usage prompt.
   */
  private defaultToolPrompt(): string {
    const toolDescriptions = Array.from(this.tools.values())
      .map(tool => `- ${tool.name}: ${tool.description}`)
      .join('\n');

    return `You can use tools WHILE reasoning about the problem.
When you need information or computation, use a tool immediately.
Don't wait until you finish reasoning - use tools as needed.

Available tools:
${toolDescriptions}

To use a tool, output:
TOOL_CALL: <tool_name>
PARAMETERS: {"param1": "value1", ...}

Continue reasoning after you get the tool result.`;
  }

  /**
   * Process message with reasoning and tool use.
   */
  async process(message: Message): Promise<Message> {
    const trace = this.enableTrace ? createReasoningTrace() : undefined;

    // Enhance message with tool instructions
    const enhancedContent = `${this.toolUsePrompt}

USER QUESTION:
${message.content}

Begin reasoning. Use tools as needed while thinking.`;

    // Reasoning loop
    let currentContext = enhancedContent;
    let finalAnswer: string | undefined;

    for (let stepNum = 0; stepNum < this.maxReasoningSteps; stepNum++) {
      // Get next reasoning step from LLM
      const response = await this.llm.process(createMessage('user', currentContext));
      const responseText = String(response.content);

      // Check if this is a tool call
      if (responseText.includes('TOOL_CALL:')) {
        const [toolName, parameters, remainingText] = this.parseToolCall(responseText);

        if (toolName && this.tools.has(toolName)) {
          // Record thinking before tool call
          if (trace && remainingText.trim()) {
            addStepToTrace(
              trace,
              createReasoningStep(stepNum, ReasoningStepType.THINKING, remainingText.trim())
            );
          }

          // Execute tool
          const tool = this.tools.get(toolName)!;
          try {
            const toolResult = await tool.execute(parameters);

            // Record tool call and result
            if (trace) {
              addStepToTrace(
                trace,
                createReasoningStep(stepNum, ReasoningStepType.TOOL_CALL, `Called ${toolName}`, {
                  toolName,
                  toolParameters: parameters,
                })
              );
              addStepToTrace(
                trace,
                createReasoningStep(stepNum, ReasoningStepType.TOOL_RESULT, String(toolResult.data), {
                  toolName,
                  toolResult: toolResult.data,
                })
              );
            }

            // Update context with tool result
            currentContext = `Previous reasoning: ${currentContext}

TOOL RESULT from ${toolName}:
${toolResult.data}

Continue reasoning with this information.`;
          } catch (error) {
            // Tool execution failed
            const errorMsg = `Tool ${toolName} failed: ${error}`;
            if (trace) {
              addStepToTrace(
                trace,
                createReasoningStep(stepNum, ReasoningStepType.TOOL_RESULT, errorMsg, { toolName })
              );
            }
            currentContext = `${currentContext}

ERROR: ${errorMsg}

Continue reasoning without this tool.`;
          }
        } else {
          // Unknown tool, continue with regular thinking
          if (trace) {
            addStepToTrace(trace, createReasoningStep(stepNum, ReasoningStepType.THINKING, responseText));
          }
          currentContext = `${currentContext}

${responseText}

Continue.`;
        }
      } else {
        // Check if we have a final answer
        if (this.isConclusion(responseText)) {
          finalAnswer = this.extractAnswer(responseText);
          if (trace) {
            addStepToTrace(
              trace,
              createReasoningStep(stepNum, ReasoningStepType.CONCLUSION, finalAnswer)
            );
          }
          break;
        }

        // Regular thinking step
        if (trace) {
          addStepToTrace(trace, createReasoningStep(stepNum, ReasoningStepType.THINKING, responseText));
        }

        // Update context for next iteration
        currentContext = `${currentContext}

${responseText}

Continue reasoning or provide final answer.`;
      }
    }

    // Finalize trace
    if (trace) {
      finalizeTrace(trace);
    }

    // If no answer found, use last response
    if (!finalAnswer) {
      finalAnswer = currentContext;
    }

    // Create response with trace
    const metadata: Record<string, any> = {};
    if (trace) {
      metadata.reasoning_trace = traceToDict(trace);
      metadata.reasoning_steps = trace.steps.length;
      metadata.tools_used = trace.totalToolsUsed;
    }

    return createMessage('assistant', finalAnswer, Object.keys(metadata).length > 0 ? metadata : undefined);
  }

  /**
   * Parse tool call from text.
   */
  private parseToolCall(text: string): [string | undefined, Record<string, any>, string] {
    try {
      // Extract tool name
      if (!text.includes('TOOL_CALL:')) {
        return [undefined, {}, text];
      }

      const parts = text.split('TOOL_CALL:', 2);
      const before = parts[0];
      const after = parts[1];

      // Get tool name (first line after TOOL_CALL:)
      const lines = after.split('\n');
      const toolName = lines[0].trim();

      // Extract parameters
      let parameters: Record<string, any> = {};
      if (after.includes('PARAMETERS:')) {
        const paramParts = after.split('PARAMETERS:', 2);
        const paramText = paramParts[1].trim();

        // Try to parse JSON
        try {
          // Find JSON object
          const start = paramText.indexOf('{');
          if (start !== -1) {
            // Find matching closing brace
            let depth = 0;
            let end = start;
            for (let i = start; i < paramText.length; i++) {
              if (paramText[i] === '{') {
                depth++;
              } else if (paramText[i] === '}') {
                depth--;
                if (depth === 0) {
                  end = i + 1;
                  break;
                }
              }
            }

            const jsonStr = paramText.substring(start, end);
            parameters = JSON.parse(jsonStr);
          }
        } catch (e) {
          // JSON parse failed, use empty parameters
        }
      }

      return [toolName, parameters, before];
    } catch (error) {
      return [undefined, {}, text];
    }
  }

  /**
   * Check if text contains a final conclusion.
   */
  private isConclusion(text: string): boolean {
    const conclusionMarkers = [
      'FINAL ANSWER:',
      'CONCLUSION:',
      'Therefore,',
      'In conclusion,',
      'The answer is',
    ];

    const textUpper = text.toUpperCase();
    return conclusionMarkers.some(marker => textUpper.includes(marker.toUpperCase()));
  }

  /**
   * Extract final answer from conclusion text.
   */
  private extractAnswer(text: string): string {
    // Try to extract text after conclusion marker
    const markers = ['FINAL ANSWER:', 'CONCLUSION:', 'The answer is'];
    const textUpper = text.toUpperCase();

    for (const marker of markers) {
      if (textUpper.includes(marker.toUpperCase())) {
        const idx = textUpper.indexOf(marker.toUpperCase());
        return text.substring(idx + marker.length).trim();
      }
    }

    return text;
  }

  /**
   * Get tool by name.
   */
  getTool(name: string): Tool | undefined {
    return this.tools.get(name);
  }

  /**
   * Add a tool.
   */
  addTool(tool: Tool): void {
    this.tools.set(tool.name, tool);
  }

  /**
   * Remove a tool.
   */
  removeTool(name: string): boolean {
    return this.tools.delete(name);
  }
}
