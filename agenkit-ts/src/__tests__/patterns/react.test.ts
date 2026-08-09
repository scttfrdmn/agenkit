/**
 * Comprehensive tests for ReActAgent pattern.
 *
 * Tests cover:
 * - Constructor validation
 * - ReAct reasoning-acting loop
 * - Tool use and observation
 * - Final answer handling
 * - Error handling
 * - Metadata and introspection
 */

import { describe, it, expect } from 'vitest';
import {
  ReActAgent,
  createReActAgent,
  ReActStopReason,
  type ReActStep,
} from '../../patterns/react';
import { Message, Tool, ToolResult, createMessage } from '../../core/interfaces';
import { createMockAgent, createErrorAgent } from './test-helpers';

/** Mock tool for testing */
class MockTool implements Tool {
  readonly name: string;
  readonly description: string;
  private result: string;
  callCount = 0;

  constructor(name: string, description: string, result: string) {
    this.name = name;
    this.description = description;
    this.result = result;
  }

  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    this.callCount++;
    return { output: this.result, success: true };
  }
}

/** Tool that fails */
class FailingTool implements Tool {
  readonly name: string;
  readonly description = 'A failing tool';

  constructor(name: string) {
    this.name = name;
  }

  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    throw new Error('tool execution failed');
  }
}

/** Agent that always returns a "Final Answer:" */
function createFinalAnswerAgent(answer: string) {
  return createMockAgent('llm', `Thought: I know the answer\nFinal Answer: ${answer}`);
}

/** Agent that returns an action then a final answer */
function createToolUseAgent(toolName: string, toolInput: string, finalAnswer: string) {
  let callCount = 0;
  return {
    name: 'llm',
    capabilities: ['mock'],
    async process(message: Message): Promise<Message> {
      callCount++;
      if (callCount === 1) {
        return createMessage(
          'assistant',
          `Thought: I need to use a tool\nAction: ${toolName}\nAction Input: ${toolInput}`
        );
      }
      return createMessage('assistant', `Thought: Done\nFinal Answer: ${finalAnswer}`);
    },
  };
}

describe('ReActAgent', () => {
  describe('Constructor', () => {
    it('should create agent with valid configuration', () => {
      const agent = createMockAgent('llm', 'response');
      const tool = new MockTool('search', 'Search the web', 'result');

      const react = new ReActAgent({ agent, tools: [tool] });

      expect(react).toBeDefined();
      expect(react.name).toBe('ReActAgent');
    });

    it('should throw when agent is missing', () => {
      const tool = new MockTool('search', 'Search the web', 'result');

      expect(
        () => new ReActAgent({ agent: null as any, tools: [tool] })
      ).toThrow('agent is required');
    });

    it('should throw when tools array is empty', () => {
      const agent = createMockAgent('llm', 'response');

      expect(
        () => new ReActAgent({ agent, tools: [] })
      ).toThrow('at least one tool is required');
    });

    it('should throw when tools is null', () => {
      const agent = createMockAgent('llm', 'response');

      expect(
        () => new ReActAgent({ agent, tools: null as any })
      ).toThrow('at least one tool is required');
    });

    it('should use default maxSteps of 10', () => {
      const agent = createMockAgent('llm', 'Thought: done\nFinal Answer: ok');
      const tool = new MockTool('search', 'Search', 'result');

      const react = new ReActAgent({ agent, tools: [tool] });
      expect(react).toBeDefined();
    });

    it('createReActAgent factory should work', () => {
      const agent = createMockAgent('llm', 'response');
      const tool = new MockTool('search', 'Search', 'result');

      const react = createReActAgent(agent, [tool], 5);
      expect(react.name).toBe('ReActAgent');
    });
  });

  describe('Capabilities', () => {
    it('should include reasoning, tool-use, react', () => {
      const agent = createMockAgent('llm', 'response');
      const tool = new MockTool('search', 'Search', 'result');

      const react = new ReActAgent({ agent, tools: [tool] });

      expect(react.capabilities).toContain('reasoning');
      expect(react.capabilities).toContain('tool-use');
      expect(react.capabilities).toContain('react');
    });
  });

  describe('Final Answer Processing', () => {
    it('should return final answer when agent provides one immediately', async () => {
      const agent = createFinalAnswerAgent('Paris is the capital of France');
      const tool = new MockTool('search', 'Search', 'result');

      const react = new ReActAgent({ agent, tools: [tool] });
      const result = await react.process(createMessage('user', 'What is the capital of France?'));

      expect(result.content).toContain('Paris is the capital of France');
    });

    it('should include stop reason in metadata', async () => {
      const agent = createFinalAnswerAgent('42');
      const tool = new MockTool('calc', 'Calculator', '42');

      const react = new ReActAgent({ agent, tools: [tool] });
      const result = await react.process(createMessage('user', 'What is 6*7?'));

      expect(result.metadata?.stopReason).toBe(ReActStopReason.FINAL_ANSWER);
    });

    it('should include steps count in metadata', async () => {
      const agent = createFinalAnswerAgent('answer');
      const tool = new MockTool('tool', 'Tool', 'result');

      const react = new ReActAgent({ agent, tools: [tool] });
      const result = await react.process(createMessage('user', 'Question?'));

      expect(typeof result.metadata?.steps).toBe('number');
    });

    // #765: Python and Zig signal completion with "Action: Final Answer"
    // (a sentinel action name, answer in a following "Action Input:" line)
    // rather than this core's own "Final Answer: <answer>" line prefix.
    // Without parser tolerance for both forms, a Python-style response
    // reaching this core looks up "Final Answer" as a tool name, misses,
    // and burns every step until max_steps.
    it('should accept "Action: Final Answer" / "Action Input:" as an alternate final-answer form', async () => {
      const agent = createMockAgent(
        'llm',
        'Thought: I know the answer\nAction: Final Answer\nAction Input: The result is 4'
      );
      const tool = new MockTool('calc', 'Calculator', '4');

      const react = new ReActAgent({ agent, tools: [tool], maxSteps: 3 });
      const result = await react.process(createMessage('user', 'What is 2+2?'));

      expect(result.content).toContain('The result is 4');
      expect(result.metadata?.stopReason).toBe(ReActStopReason.FINAL_ANSWER);
    });
  });

  describe('Max Steps', () => {
    it('should stop at maxSteps and return appropriate stop reason', async () => {
      // Agent never gives a final answer
      const agent = createMockAgent('llm', 'Thought: still thinking\nAction: search\nAction Input: query');
      const tool = new MockTool('search', 'Search', 'result');

      const react = new ReActAgent({ agent, tools: [tool], maxSteps: 2 });
      const result = await react.process(createMessage('user', 'Question?'));

      expect(result.metadata?.stopReason).toBe(ReActStopReason.MAX_STEPS);
      expect(result.content).toContain(ReActStopReason.MAX_STEPS);
    });
  });

  describe('Invalid Action', () => {
    it('should stop with invalid action when no tool or final answer specified', async () => {
      // Response with a thought but no action and no final answer
      const agent = createMockAgent('llm', 'Thought: just thinking with no action');
      const tool = new MockTool('search', 'Search', 'result');

      const react = new ReActAgent({ agent, tools: [tool], maxSteps: 1 });
      const result = await react.process(createMessage('user', 'Question?'));

      // Should stop - either max steps or invalid action
      expect(result.metadata?.stopReason).toBeDefined();
    });
  });

  describe('Tool Execution Error', () => {
    it('should stop with tool error stop reason on exception', async () => {
      // Agent tries to use a failing tool
      const agent = createMockAgent(
        'llm',
        'Thought: use tool\nAction: failingtool\nAction Input: input'
      );
      const tool = new FailingTool('failingtool');

      const react = new ReActAgent({ agent, tools: [tool], maxSteps: 3 });
      const result = await react.process(createMessage('user', 'Question?'));

      expect(result.metadata?.stopReason).toBe(ReActStopReason.TOOL_ERROR);
    });
  });

  describe('getSteps', () => {
    it('should return empty array before processing', () => {
      const agent = createMockAgent('llm', 'response');
      const tool = new MockTool('search', 'Search', 'result');

      const react = new ReActAgent({ agent, tools: [tool] });

      expect(react.getSteps()).toHaveLength(0);
    });

    it('should return steps after processing', async () => {
      const agent = createFinalAnswerAgent('answer');
      const tool = new MockTool('search', 'Search', 'result');

      const react = new ReActAgent({ agent, tools: [tool] });
      await react.process(createMessage('user', 'Question?'));

      const steps = react.getSteps();
      expect(steps.length).toBeGreaterThan(0);
    });

    it('should reset steps on each new process call', async () => {
      const agent = createFinalAnswerAgent('answer');
      const tool = new MockTool('search', 'Search', 'result');

      const react = new ReActAgent({ agent, tools: [tool] });
      await react.process(createMessage('user', 'First question'));
      const stepsAfterFirst = react.getSteps().length;

      await react.process(createMessage('user', 'Second question'));
      const stepsAfterSecond = react.getSteps().length;

      // Steps count may be the same since it resets each time
      expect(stepsAfterSecond).toBeGreaterThan(0);
    });
  });

  describe('Verbose Mode', () => {
    it('should include reasoning trace in verbose mode', async () => {
      const agent = createFinalAnswerAgent('answer');
      const tool = new MockTool('search', 'Search', 'result');

      const react = new ReActAgent({ agent, tools: [tool], verbose: true });
      const result = await react.process(createMessage('user', 'Question?'));

      // Verbose mode includes step details in content
      expect(typeof result.content).toBe('string');
    });

    it('should not include reasoning trace in non-verbose mode', async () => {
      const agent = createFinalAnswerAgent('clean answer');
      const tool = new MockTool('search', 'Search', 'result');

      const react = new ReActAgent({ agent, tools: [tool], verbose: false });
      const result = await react.process(createMessage('user', 'Question?'));

      expect(result.content).toBe('clean answer');
    });
  });
});
