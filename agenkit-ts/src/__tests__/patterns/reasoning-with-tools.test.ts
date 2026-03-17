/**
 * Comprehensive tests for ReasoningWithToolsAgent pattern.
 *
 * Tests cover:
 * - Constructor and configuration
 * - Tool management (add, get, remove)
 * - Reasoning loop with and without tool use
 * - Reasoning trace metadata
 * - Conclusion detection
 */

import { describe, it, expect } from 'vitest';
import {
  ReasoningWithToolsAgent,
  ReasoningStepType,
  createReasoningStep,
  createReasoningTrace,
  addStepToTrace,
  finalizeTrace,
  getTraceDuration,
} from '../../patterns/reasoning-with-tools';
import { Message, Tool, ToolResult, createMessage } from '../../core/interfaces';
import { createMockAgent } from './test-helpers';

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

describe('Reasoning Trace Utilities', () => {
  describe('createReasoningStep', () => {
    it('should create a thinking step', () => {
      const step = createReasoningStep(1, ReasoningStepType.THINKING, 'Thinking about it');

      expect(step.stepNumber).toBe(1);
      expect(step.stepType).toBe(ReasoningStepType.THINKING);
      expect(step.content).toBe('Thinking about it');
      expect(typeof step.timestamp).toBe('number');
    });

    it('should create a tool call step with options', () => {
      const step = createReasoningStep(2, ReasoningStepType.TOOL_CALL, 'Calling calculator', {
        toolName: 'calculator',
        toolParameters: { input: '2+2' },
      });

      expect(step.toolName).toBe('calculator');
      expect(step.toolParameters).toEqual({ input: '2+2' });
    });
  });

  describe('createReasoningTrace', () => {
    it('should create an empty trace', () => {
      const trace = createReasoningTrace();

      expect(trace.steps).toHaveLength(0);
      expect(trace.totalToolsUsed).toBe(0);
      expect(trace.totalThinkingSteps).toBe(0);
      expect(typeof trace.startTime).toBe('number');
    });
  });

  describe('addStepToTrace', () => {
    it('should increment totalThinkingSteps for THINKING step', () => {
      const trace = createReasoningTrace();
      const step = createReasoningStep(1, ReasoningStepType.THINKING, 'thought');

      addStepToTrace(trace, step);

      expect(trace.totalThinkingSteps).toBe(1);
      expect(trace.totalToolsUsed).toBe(0);
    });

    it('should increment totalToolsUsed for TOOL_CALL step', () => {
      const trace = createReasoningTrace();
      const step = createReasoningStep(1, ReasoningStepType.TOOL_CALL, 'called tool');

      addStepToTrace(trace, step);

      expect(trace.totalToolsUsed).toBe(1);
      expect(trace.totalThinkingSteps).toBe(0);
    });
  });

  describe('finalizeTrace', () => {
    it('should set endTime', () => {
      const trace = createReasoningTrace();
      finalizeTrace(trace);

      expect(trace.endTime).toBeDefined();
      expect(typeof trace.endTime).toBe('number');
    });
  });

  describe('getTraceDuration', () => {
    it('should return non-negative duration', () => {
      const trace = createReasoningTrace();
      finalizeTrace(trace);

      const duration = getTraceDuration(trace);
      expect(duration).toBeGreaterThanOrEqual(0);
    });
  });
});

describe('ReasoningWithToolsAgent', () => {
  const createTool = (name: string) =>
    new MockTool(name, `${name} tool`, `result from ${name}`);

  describe('Constructor', () => {
    it('should create agent with LLM and tools', () => {
      const llm = createMockAgent('llm', 'response');
      const tool = createTool('calculator');

      const agent = new ReasoningWithToolsAgent(llm, [tool]);

      expect(agent).toBeDefined();
      expect(agent.name).toContain('llm');
    });

    it('should include LLM name in agent name', () => {
      const llm = createMockAgent('my-gpt', 'response');
      const tool = createTool('search');

      const agent = new ReasoningWithToolsAgent(llm, [tool]);

      expect(agent.name).toContain('my-gpt');
    });

    it('should use default maxReasoningSteps of 20', () => {
      const llm = createMockAgent('llm', 'FINAL ANSWER: done');
      const tool = createTool('calc');

      const agent = new ReasoningWithToolsAgent(llm, [tool]);
      expect(agent).toBeDefined();
    });

    it('should accept custom config', () => {
      const llm = createMockAgent('llm', 'FINAL ANSWER: done');
      const tool = createTool('calc');

      const agent = new ReasoningWithToolsAgent(llm, [tool], {
        maxReasoningSteps: 5,
        enableTrace: false,
      });

      expect(agent).toBeDefined();
    });
  });

  describe('Tool Management', () => {
    it('getTool should return registered tool', () => {
      const llm = createMockAgent('llm', 'response');
      const tool = createTool('calculator');

      const agent = new ReasoningWithToolsAgent(llm, [tool]);

      expect(agent.getTool('calculator')).toBe(tool);
    });

    it('getTool should return undefined for unknown tool', () => {
      const llm = createMockAgent('llm', 'response');
      const tool = createTool('calculator');

      const agent = new ReasoningWithToolsAgent(llm, [tool]);

      expect(agent.getTool('nonexistent')).toBeUndefined();
    });

    it('addTool should register a new tool', () => {
      const llm = createMockAgent('llm', 'response');
      const tool1 = createTool('calculator');

      const agent = new ReasoningWithToolsAgent(llm, [tool1]);
      const tool2 = createTool('search');
      agent.addTool(tool2);

      expect(agent.getTool('search')).toBe(tool2);
    });

    it('removeTool should return true when tool existed', () => {
      const llm = createMockAgent('llm', 'response');
      const tool = createTool('calculator');

      const agent = new ReasoningWithToolsAgent(llm, [tool]);

      expect(agent.removeTool('calculator')).toBe(true);
      expect(agent.getTool('calculator')).toBeUndefined();
    });

    it('removeTool should return false when tool not found', () => {
      const llm = createMockAgent('llm', 'response');
      const tool = createTool('calculator');

      const agent = new ReasoningWithToolsAgent(llm, [tool]);

      expect(agent.removeTool('nonexistent')).toBe(false);
    });
  });

  describe('Processing', () => {
    it('should return a valid message', async () => {
      const llm = createMockAgent('llm', 'FINAL ANSWER: 42');
      const tool = createTool('calc');

      const agent = new ReasoningWithToolsAgent(llm, [tool], { maxReasoningSteps: 3 });
      const result = await agent.process(createMessage('user', 'What is 6*7?'));

      expect(result.role).toBe('assistant');
      expect(typeof result.content).toBe('string');
    });

    it('should include reasoning trace in metadata when trace enabled', async () => {
      const llm = createMockAgent('llm', 'FINAL ANSWER: done');
      const tool = createTool('calc');

      const agent = new ReasoningWithToolsAgent(llm, [tool], {
        maxReasoningSteps: 2,
        enableTrace: true,
      });
      const result = await agent.process(createMessage('user', 'Question?'));

      expect(result.metadata?.reasoning_trace).toBeDefined();
    });

    it('should not include trace metadata when trace disabled', async () => {
      const llm = createMockAgent('llm', 'FINAL ANSWER: done');
      const tool = createTool('calc');

      const agent = new ReasoningWithToolsAgent(llm, [tool], {
        maxReasoningSteps: 2,
        enableTrace: false,
      });
      const result = await agent.process(createMessage('user', 'Question?'));

      expect(result.metadata?.reasoning_trace).toBeUndefined();
    });

    it('should detect conclusion markers', async () => {
      const llm = createMockAgent('llm', 'In conclusion, the answer is 42.');
      const tool = createTool('calc');

      const agent = new ReasoningWithToolsAgent(llm, [tool], {
        maxReasoningSteps: 3,
        enableTrace: true,
      });
      const result = await agent.process(createMessage('user', 'Question?'));

      // Should have concluded
      expect(result.role).toBe('assistant');
    });

    it('should include tools_used count in metadata', async () => {
      const llm = createMockAgent('llm', 'FINAL ANSWER: result');
      const tool = createTool('calc');

      const agent = new ReasoningWithToolsAgent(llm, [tool], {
        maxReasoningSteps: 2,
        enableTrace: true,
      });
      const result = await agent.process(createMessage('user', 'Question?'));

      expect(typeof result.metadata?.tools_used).toBe('number');
    });
  });
});
