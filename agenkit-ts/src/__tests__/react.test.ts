/**
 * Tests for ReAct Pattern (Reasoning + Acting).
 */

import {
  ReActAgent,
  ReActConfig,
  ReActStep,
  ReActStopReason,
  createReActAgent,
} from '../patterns/react';
import { Agent, Message, Tool, ToolResult, createMessage } from '../core/interfaces';

/**
 * Mock agent that returns predefined responses.
 */
class MockAgent implements Agent {
  readonly name: string;
  private responses: string[];
  private callCount: number;

  constructor(name: string, responses: string[]) {
    this.name = name;
    this.responses = responses;
    this.callCount = 0;
  }

  async process(message: Message): Promise<Message> {
    if (this.callCount >= this.responses.length) {
      throw new Error('No more mock responses available');
    }
    const response = this.responses[this.callCount];
    this.callCount++;
    return createMessage('assistant', response);
  }
}

/**
 * Mock tool for testing.
 */
class MockTool implements Tool {
  readonly name: string;
  readonly description: string;
  private response: string;
  private shouldFail: boolean;

  constructor(name: string, description: string, response: string, shouldFail = false) {
    this.name = name;
    this.description = description;
    this.response = response;
    this.shouldFail = shouldFail;
  }

  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    if (this.shouldFail) {
      throw new Error('Tool execution failed');
    }

    return {
      output: this.response,
      success: true,
    };
  }
}

describe('ReActAgent', () => {
  describe('Configuration Validation', () => {
    it('should require agent', () => {
      expect(() => {
        new ReActAgent({
          agent: null as any,
          tools: [new MockTool('test', 'Test tool', 'result')],
        });
      }).toThrow('agent is required');
    });

    it('should require at least one tool', () => {
      expect(() => {
        new ReActAgent({
          agent: new MockAgent('test', []),
          tools: [],
        });
      }).toThrow('at least one tool is required');
    });

    it('should use default maxSteps', () => {
      const agent = new MockAgent('test', ['Final Answer: Done']);
      const tool = new MockTool('test_tool', 'Test', 'result');
      const reactAgent = new ReActAgent({ agent, tools: [tool] });

      // Access private field through type assertion for testing
      expect((reactAgent as any).maxSteps).toBe(10);
    });

    it('should use custom maxSteps', () => {
      const agent = new MockAgent('test', ['Final Answer: Done']);
      const tool = new MockTool('test_tool', 'Test', 'result');
      const reactAgent = new ReActAgent({ agent, tools: [tool], maxSteps: 5 });

      expect((reactAgent as any).maxSteps).toBe(5);
    });

    it('should use default verbose mode', () => {
      const agent = new MockAgent('test', ['Final Answer: Done']);
      const tool = new MockTool('test_tool', 'Test', 'result');
      const reactAgent = new ReActAgent({ agent, tools: [tool] });

      expect((reactAgent as any).verbose).toBe(true);
    });
  });

  describe('Basic ReAct Loop', () => {
    it('should execute single step with final answer', async () => {
      const agent = new MockAgent('test', [
        'Thought: I can answer directly\nFinal Answer: The answer is 42',
      ]);
      const tool = new MockTool('calculator', 'Does math', '42');
      const reactAgent = new ReActAgent({ agent, tools: [tool] });

      const result = await reactAgent.process(createMessage('user', 'What is the answer?'));

      expect(result.content).toContain('The answer is 42');
      expect(result.metadata?.stopReason).toBe(ReActStopReason.FINAL_ANSWER);
      expect(result.metadata?.steps).toBe(1);
    });

    it('should execute multi-step reasoning', async () => {
      const agent = new MockAgent('test', [
        'Thought: I need to search for information\nAction: search\nAction Input: weather',
        'Thought: I now have the answer\nFinal Answer: It is sunny',
      ]);
      const searchTool = new MockTool('search', 'Search for info', 'The weather is sunny');
      const reactAgent = new ReActAgent({ agent, tools: [searchTool] });

      const result = await reactAgent.process(
        createMessage('user', 'What is the weather?')
      );

      expect(result.content).toContain('It is sunny');
      expect(result.metadata?.stopReason).toBe(ReActStopReason.FINAL_ANSWER);
      expect(result.metadata?.steps).toBe(2);
    });

    it('should handle multiple tool calls', async () => {
      const agent = new MockAgent('test', [
        'Thought: First search\nAction: search\nAction Input: population',
        'Thought: Now calculate\nAction: calculator\nAction Input: 1000 * 2',
        'Thought: I have the answer\nFinal Answer: Population is 2000',
      ]);
      const searchTool = new MockTool('search', 'Search', '1000');
      const calcTool = new MockTool('calculator', 'Calculate', '2000');
      const reactAgent = new ReActAgent({
        agent,
        tools: [searchTool, calcTool],
      });

      const result = await reactAgent.process(createMessage('user', 'What is the population?'));

      expect(result.content).toContain('2000');
      expect(result.metadata?.steps).toBe(3);
    });
  });

  describe('Tool Execution', () => {
    it('should execute tool and return observation', async () => {
      const agent = new MockAgent('test', [
        'Thought: Use calculator\nAction: calculator\nAction Input: 5 + 3',
        'Thought: Done\nFinal Answer: 8',
      ]);
      const calcTool = new MockTool('calculator', 'Does math', '8');
      const reactAgent = new ReActAgent({ agent, tools: [calcTool] });

      const result = await reactAgent.process(createMessage('user', 'What is 5+3?'));

      const steps = reactAgent.getSteps();
      expect(steps[0].action).toBe('calculator');
      expect(steps[0].actionInput).toBe('5 + 3');
      expect(steps[0].observation).toBe('8');
    });

    it('should handle tool not found', async () => {
      const agent = new MockAgent('test', [
        'Thought: Use unknown tool\nAction: unknown_tool\nAction Input: test',
        'Thought: Try again\nFinal Answer: Could not complete',
      ]);
      const tool = new MockTool('calculator', 'Does math', '42');
      const reactAgent = new ReActAgent({ agent, tools: [tool] });

      const result = await reactAgent.process(createMessage('user', 'Test'));

      const steps = reactAgent.getSteps();
      expect(steps[0].observation).toContain('not found');
      expect(steps[0].observation).toContain('calculator');
    });

    it('should handle tool execution failure', async () => {
      const agent = new MockAgent('test', [
        'Thought: Use failing tool\nAction: failing_tool\nAction Input: test',
      ]);
      const failingTool = new MockTool('failing_tool', 'Fails', '', true);
      const reactAgent = new ReActAgent({ agent, tools: [failingTool] });

      const result = await reactAgent.process(createMessage('user', 'Test'));

      expect(result.metadata?.stopReason).toBe(ReActStopReason.TOOL_ERROR);
      const steps = reactAgent.getSteps();
      expect(steps[0].observation).toContain('Error');
    });
  });

  describe('Stop Conditions', () => {
    it('should stop at max steps', async () => {
      // Generate responses that never give final answer
      const responses = Array(5)
        .fill(null)
        .map((_, i) => `Thought: Step ${i}\nAction: search\nAction Input: query ${i}`);

      const agent = new MockAgent('test', responses);
      const tool = new MockTool('search', 'Search', 'result');
      const reactAgent = new ReActAgent({ agent, tools: [tool], maxSteps: 3 });

      const result = await reactAgent.process(createMessage('user', 'Test'));

      expect(result.metadata?.stopReason).toBe(ReActStopReason.MAX_STEPS);
      expect(result.metadata?.steps).toBe(3);
    });

    it('should stop on invalid action', async () => {
      const agent = new MockAgent('test', [
        'Thought: Invalid response without action or final answer',
      ]);
      const tool = new MockTool('test', 'Test', 'result');
      const reactAgent = new ReActAgent({ agent, tools: [tool] });

      const result = await reactAgent.process(createMessage('user', 'Test'));

      expect(result.metadata?.stopReason).toBe(ReActStopReason.INVALID_ACTION);
    });

    it('should stop on final answer', async () => {
      const agent = new MockAgent('test', [
        'Thought: I know the answer\nFinal Answer: 42',
      ]);
      const tool = new MockTool('test', 'Test', 'result');
      const reactAgent = new ReActAgent({ agent, tools: [tool] });

      const result = await reactAgent.process(createMessage('user', 'What is the answer?'));

      expect(result.metadata?.stopReason).toBe(ReActStopReason.FINAL_ANSWER);
      expect(result.content).toContain('42');
    });
  });

  describe('Verbose Mode', () => {
    it('should include reasoning trace in verbose mode', async () => {
      const agent = new MockAgent('test', [
        'Thought: First step\nAction: search\nAction Input: test',
        'Thought: Second step\nFinal Answer: Done',
      ]);
      const tool = new MockTool('search', 'Search', 'result');
      const reactAgent = new ReActAgent({ agent, tools: [tool], verbose: true });

      const result = await reactAgent.process(createMessage('user', 'Test'));

      expect(result.content).toContain('Thought: First step');
      expect(result.content).toContain('Action: search');
      expect(result.content).toContain('Observation: result');
      expect(result.content).toContain('Thought: Second step');
    });

    it('should exclude reasoning trace in non-verbose mode', async () => {
      const agent = new MockAgent('test', [
        'Thought: First step\nAction: search\nAction Input: test',
        'Thought: Second step\nFinal Answer: Done',
      ]);
      const tool = new MockTool('search', 'Search', 'result');
      const reactAgent = new ReActAgent({ agent, tools: [tool], verbose: false });

      const result = await reactAgent.process(createMessage('user', 'Test'));

      expect(result.content).not.toContain('Thought: First step');
      expect(result.content).not.toContain('Action: search');
      expect(result.content).toContain('Done');
    });
  });

  describe('Step Tracking', () => {
    it('should track all steps', async () => {
      const agent = new MockAgent('test', [
        'Thought: Step 1\nAction: tool1\nAction Input: input1',
        'Thought: Step 2\nAction: tool2\nAction Input: input2',
        'Thought: Done\nFinal Answer: Complete',
      ]);
      const tool1 = new MockTool('tool1', 'Tool 1', 'result1');
      const tool2 = new MockTool('tool2', 'Tool 2', 'result2');
      const reactAgent = new ReActAgent({ agent, tools: [tool1, tool2] });

      await reactAgent.process(createMessage('user', 'Test'));

      const steps = reactAgent.getSteps();
      expect(steps.length).toBe(3);
      expect(steps[0].thought).toBe('Step 1');
      expect(steps[0].action).toBe('tool1');
      expect(steps[0].observation).toBe('result1');
      expect(steps[1].thought).toBe('Step 2');
      expect(steps[1].action).toBe('tool2');
      expect(steps[1].observation).toBe('result2');
      expect(steps[2].isFinal).toBe(true);
    });

    it('should return copy of steps', () => {
      const agent = new MockAgent('test', ['Final Answer: Done']);
      const tool = new MockTool('test', 'Test', 'result');
      const reactAgent = new ReActAgent({ agent, tools: [tool] });

      const steps1 = reactAgent.getSteps();
      const steps2 = reactAgent.getSteps();

      expect(steps1).toEqual(steps2);
      expect(steps1).not.toBe(steps2); // Different array instances
    });
  });

  describe('Response Parsing', () => {
    it('should parse thought only', async () => {
      const agent = new MockAgent('test', [
        'Thought: Just thinking\nFinal Answer: Done',
      ]);
      const tool = new MockTool('test', 'Test', 'result');
      const reactAgent = new ReActAgent({ agent, tools: [tool] });

      await reactAgent.process(createMessage('user', 'Test'));

      const steps = reactAgent.getSteps();
      expect(steps[0].thought).toBe('Just thinking');
      expect(steps[0].action).toBeUndefined();
    });

    it('should parse thought and action', async () => {
      const agent = new MockAgent('test', [
        'Thought: Need to search\nAction: search\nAction Input: query',
        'Final Answer: Done',
      ]);
      const tool = new MockTool('search', 'Search', 'result');
      const reactAgent = new ReActAgent({ agent, tools: [tool] });

      await reactAgent.process(createMessage('user', 'Test'));

      const steps = reactAgent.getSteps();
      expect(steps[0].thought).toBe('Need to search');
      expect(steps[0].action).toBe('search');
      expect(steps[0].actionInput).toBe('query');
    });

    it('should parse final answer', async () => {
      const agent = new MockAgent('test', ['Final Answer: The result is 42']);
      const tool = new MockTool('test', 'Test', 'result');
      const reactAgent = new ReActAgent({ agent, tools: [tool] });

      await reactAgent.process(createMessage('user', 'Test'));

      const steps = reactAgent.getSteps();
      expect(steps[0].isFinal).toBe(true);
      expect(steps[0].observation).toBe('The result is 42');
    });
  });

  describe('Capabilities', () => {
    it('should declare capabilities', () => {
      const agent = new MockAgent('test', ['Final Answer: Done']);
      const tool = new MockTool('test', 'Test', 'result');
      const reactAgent = new ReActAgent({ agent, tools: [tool] });

      const caps = reactAgent.capabilities;
      expect(caps).toContain('reasoning');
      expect(caps).toContain('tool-use');
      expect(caps).toContain('react');
    });
  });

  describe('Convenience Function', () => {
    it('should create agent with createReActAgent', async () => {
      const agent = new MockAgent('test', ['Final Answer: Done']);
      const tool = new MockTool('test', 'Test', 'result');
      const reactAgent = createReActAgent(agent, [tool], 5);

      expect(reactAgent.name).toBe('ReActAgent');
      expect((reactAgent as any).maxSteps).toBe(5);
    });
  });

  describe('Integration Scenarios', () => {
    it('should handle complex multi-tool workflow', async () => {
      const agent = new MockAgent('test', [
        'Thought: First get the data\nAction: fetch_data\nAction Input: users',
        'Thought: Now process it\nAction: process\nAction Input: format json',
        'Thought: Finally store it\nAction: store\nAction Input: database',
        'Thought: All done\nFinal Answer: Successfully processed and stored user data',
      ]);

      const fetchTool = new MockTool('fetch_data', 'Fetch data', 'raw user data');
      const processTool = new MockTool('process', 'Process data', '{"users": [...]}');
      const storeTool = new MockTool('store', 'Store data', 'stored successfully');

      const reactAgent = new ReActAgent({
        agent,
        tools: [fetchTool, processTool, storeTool],
        maxSteps: 10,
      });

      const result = await reactAgent.process(
        createMessage('user', 'Process the user data')
      );

      expect(result.metadata?.stopReason).toBe(ReActStopReason.FINAL_ANSWER);
      expect(result.metadata?.steps).toBe(4);
      expect(result.content).toContain('Successfully processed');

      const steps = reactAgent.getSteps();
      expect(steps[0].action).toBe('fetch_data');
      expect(steps[1].action).toBe('process');
      expect(steps[2].action).toBe('store');
      expect(steps[3].isFinal).toBe(true);
    });
  });
});
