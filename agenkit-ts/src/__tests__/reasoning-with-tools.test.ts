/**
 * Tests for Reasoning with Tools pattern.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  ReasoningWithToolsAgent,
  ReasoningStepType,
  ReasoningStep,
  ReasoningTrace,
  createReasoningStep,
  createReasoningTrace,
  addStepToTrace,
  finalizeTrace,
  getTraceDuration,
  traceToDict,
} from '../patterns/reasoning-with-tools';
import { Agent, Message, Tool, ToolResult, createMessage } from '../core/interfaces';

// ============================================================================
// Mock Implementations
// ============================================================================

class MockLLM implements Agent {
  readonly name = 'mock_llm';
  private responses: string[];
  private callCount: number;

  constructor(responses: string[]) {
    this.responses = responses;
    this.callCount = 0;
  }

  async process(message: Message): Promise<Message> {
    if (this.callCount < this.responses.length) {
      const response = this.responses[this.callCount];
      this.callCount++;
      return createMessage('assistant', response);
    }
    return createMessage('assistant', "I don't know");
  }

  getCallCount(): number {
    return this.callCount;
  }
}

class MockTool implements Tool {
  readonly name: string;
  readonly description: string;
  readonly parameters: Record<string, any>;
  private result: any;
  public callCount: number;
  public lastParameters?: Record<string, any>;

  constructor(name: string, result: any = 'result') {
    this.name = name;
    this.description = `Mock tool: ${name}`;
    this.parameters = { type: 'object', properties: {} };
    this.result = result;
    this.callCount = 0;
  }

  async execute(params?: Record<string, any>): Promise<ToolResult> {
    this.callCount++;
    this.lastParameters = params;

    if (this.result instanceof Error) {
      throw this.result;
    }

    return {
      success: true,
      data: this.result,
      error: undefined,
    };
  }
}

// ============================================================================
// ReasoningStep Tests
// ============================================================================

describe('ReasoningStep', () => {
  it('should create a thinking step', () => {
    const step = createReasoningStep(1, ReasoningStepType.THINKING, 'Thinking about the problem', {
      confidence: 0.9,
    });

    expect(step.stepNumber).toBe(1);
    expect(step.stepType).toBe(ReasoningStepType.THINKING);
    expect(step.content).toBe('Thinking about the problem');
    expect(step.confidence).toBe(0.9);
    expect(step.toolName).toBeUndefined();
  });

  it('should create a tool call step', () => {
    const step = createReasoningStep(2, ReasoningStepType.TOOL_CALL, 'Calling calculator', {
      toolName: 'calculator',
      toolParameters: { operation: 'add', a: 1, b: 2 },
    });

    expect(step.stepType).toBe(ReasoningStepType.TOOL_CALL);
    expect(step.toolName).toBe('calculator');
    expect(step.toolParameters).toEqual({ operation: 'add', a: 1, b: 2 });
  });

  it('should have timestamp', () => {
    const before = Date.now();
    const step = createReasoningStep(1, ReasoningStepType.THINKING, 'Test');
    const after = Date.now();

    expect(step.timestamp).toBeGreaterThanOrEqual(before);
    expect(step.timestamp).toBeLessThanOrEqual(after);
  });
});

// ============================================================================
// ReasoningTrace Tests
// ============================================================================

describe('ReasoningTrace', () => {
  let trace: ReasoningTrace;

  beforeEach(() => {
    trace = createReasoningTrace();
  });

  it('should create empty trace', () => {
    expect(trace.steps).toEqual([]);
    expect(trace.totalToolsUsed).toBe(0);
    expect(trace.totalThinkingSteps).toBe(0);
    expect(trace.endTime).toBeUndefined();
  });

  it('should add thinking step', () => {
    const step = createReasoningStep(1, ReasoningStepType.THINKING, 'Thinking');
    addStepToTrace(trace, step);

    expect(trace.steps).toHaveLength(1);
    expect(trace.totalThinkingSteps).toBe(1);
    expect(trace.totalToolsUsed).toBe(0);
  });

  it('should add tool call step', () => {
    const step = createReasoningStep(1, ReasoningStepType.TOOL_CALL, 'Calling tool');
    addStepToTrace(trace, step);

    expect(trace.steps).toHaveLength(1);
    expect(trace.totalToolsUsed).toBe(1);
    expect(trace.totalThinkingSteps).toBe(0);
  });

  it('should track multiple steps', () => {
    addStepToTrace(trace, createReasoningStep(1, ReasoningStepType.THINKING, 'Think 1'));
    addStepToTrace(trace, createReasoningStep(2, ReasoningStepType.TOOL_CALL, 'Call tool'));
    addStepToTrace(trace, createReasoningStep(3, ReasoningStepType.TOOL_RESULT, 'Result'));
    addStepToTrace(trace, createReasoningStep(4, ReasoningStepType.THINKING, 'Think 2'));

    expect(trace.steps).toHaveLength(4);
    expect(trace.totalThinkingSteps).toBe(2);
    expect(trace.totalToolsUsed).toBe(1);
  });

  it('should finalize trace', () => {
    finalizeTrace(trace);

    expect(trace.endTime).toBeDefined();
    expect(trace.endTime).toBeGreaterThanOrEqual(trace.startTime);
  });

  it('should calculate duration', () => {
    finalizeTrace(trace);

    const duration = getTraceDuration(trace);

    expect(duration).toBeGreaterThanOrEqual(0);
    expect(duration).toBeLessThan(1); // Should be very fast
  });

  it('should convert to dict', () => {
    addStepToTrace(trace, createReasoningStep(1, ReasoningStepType.THINKING, 'Test'));
    finalizeTrace(trace);

    const dict = traceToDict(trace);

    expect(dict.steps).toHaveLength(1);
    expect(dict.total_thinking_steps).toBe(1);
    expect(dict.total_tools_used).toBe(0);
    expect(dict.duration_seconds).toBeGreaterThanOrEqual(0);
  });
});

// ============================================================================
// ReasoningWithToolsAgent Tests
// ============================================================================

describe('ReasoningWithToolsAgent', () => {
  describe('Configuration', () => {
    it('should create with default config', () => {
      const llm = new MockLLM(['FINAL ANSWER: 42']);
      const agent = new ReasoningWithToolsAgent(llm, []);

      expect(agent.name).toContain('reasoning_with_tools');
      expect(agent.name).toContain('mock_llm');
    });

    it('should create with custom config', () => {
      const llm = new MockLLM(['FINAL ANSWER: 42']);
      const tool = new MockTool('calculator');
      const agent = new ReasoningWithToolsAgent(llm, [tool], {
        maxReasoningSteps: 5,
        enableTrace: false,
        confidenceThreshold: 0.9,
      });

      expect(agent.name).toContain('reasoning_with_tools');
    });

    it('should store tools', () => {
      const llm = new MockLLM(['FINAL ANSWER: 42']);
      const tool1 = new MockTool('tool1');
      const tool2 = new MockTool('tool2');
      const agent = new ReasoningWithToolsAgent(llm, [tool1, tool2]);

      expect(agent.getTool('tool1')).toBe(tool1);
      expect(agent.getTool('tool2')).toBe(tool2);
    });
  });

  describe('Basic Reasoning', () => {
    it('should process simple conclusion', async () => {
      const llm = new MockLLM(['FINAL ANSWER: 42']);
      const agent = new ReasoningWithToolsAgent(llm, []);

      const response = await agent.process(createMessage('user', 'What is the answer?'));

      expect(response.content).toContain('42');
    });

    it('should include reasoning trace in metadata', async () => {
      const llm = new MockLLM(['FINAL ANSWER: 42']);
      const agent = new ReasoningWithToolsAgent(llm, []);

      const response = await agent.process(createMessage('user', 'What is the answer?'));

      expect(response.metadata).toBeDefined();
      expect(response.metadata?.reasoning_trace).toBeDefined();
      expect(response.metadata?.reasoning_steps).toBeGreaterThan(0);
    });

    it('should handle multiple thinking steps', async () => {
      const llm = new MockLLM(['Thinking step 1', 'Thinking step 2', 'FINAL ANSWER: Done']);
      const agent = new ReasoningWithToolsAgent(llm, []);

      const response = await agent.process(createMessage('user', 'Question'));

      expect(response.content).toContain('Done');
      expect(response.metadata?.reasoning_steps).toBe(3);
    });

    it('should respect max reasoning steps', async () => {
      const llm = new MockLLM(['Step 1', 'Step 2', 'Step 3', 'Step 4', 'Step 5']);
      const agent = new ReasoningWithToolsAgent(llm, [], { maxReasoningSteps: 3 });

      const response = await agent.process(createMessage('user', 'Question'));

      expect(response.metadata?.reasoning_steps).toBeLessThanOrEqual(3);
    });
  });

  describe('Tool Usage', () => {
    it('should parse and execute tool call', async () => {
      const tool = new MockTool('calculator', '47.97');
      const llm = new MockLLM([
        'TOOL_CALL: calculator\nPARAMETERS: {"operation": "multiply"}',
        'FINAL ANSWER: 47.97',
      ]);
      const agent = new ReasoningWithToolsAgent(llm, [tool]);

      const response = await agent.process(createMessage('user', 'Calculate'));

      expect(tool.callCount).toBe(1);
      expect(response.metadata?.tools_used).toBe(1);
    });

    it('should pass tool parameters', async () => {
      const tool = new MockTool('calculator', '3');
      const llm = new MockLLM([
        'TOOL_CALL: calculator\nPARAMETERS: {"a": 1, "b": 2}',
        'FINAL ANSWER: 3',
      ]);
      const agent = new ReasoningWithToolsAgent(llm, [tool]);

      await agent.process(createMessage('user', 'Add 1 and 2'));

      expect(tool.lastParameters).toEqual({ a: 1, b: 2 });
    });

    it('should continue reasoning with tool result', async () => {
      const tool = new MockTool('calculator', '100');
      const llm = new MockLLM([
        'TOOL_CALL: calculator\nPARAMETERS: {"operation": "calculate"}',
        'FINAL ANSWER: The result is 100',
      ]);
      const agent = new ReasoningWithToolsAgent(llm, [tool]);

      const response = await agent.process(createMessage('user', 'Calculate'));

      expect(response.content).toContain('100');
    });

    it('should handle tool execution errors', async () => {
      const tool = new MockTool('failing_tool', new Error('Tool failed'));
      const llm = new MockLLM([
        'TOOL_CALL: failing_tool\nPARAMETERS: {}',
        'FINAL ANSWER: Could not complete',
      ]);
      const agent = new ReasoningWithToolsAgent(llm, [tool]);

      const response = await agent.process(createMessage('user', 'Try tool'));

      expect(response.content).toBeDefined();
      // Should not throw, should handle error gracefully
    });

    it('should handle unknown tool', async () => {
      const llm = new MockLLM([
        'TOOL_CALL: unknown_tool\nPARAMETERS: {}',
        'FINAL ANSWER: Done without tool',
      ]);
      const agent = new ReasoningWithToolsAgent(llm, []);

      const response = await agent.process(createMessage('user', 'Question'));

      expect(response.metadata?.tools_used).toBe(0);
    });

    it('should use multiple tools', async () => {
      const tool1 = new MockTool('tool1', 'result1');
      const tool2 = new MockTool('tool2', 'result2');
      const llm = new MockLLM([
        'TOOL_CALL: tool1\nPARAMETERS: {}',
        'TOOL_CALL: tool2\nPARAMETERS: {}',
        'FINAL ANSWER: Used both tools',
      ]);
      const agent = new ReasoningWithToolsAgent(llm, [tool1, tool2]);

      const response = await agent.process(createMessage('user', 'Use tools'));

      expect(tool1.callCount).toBe(1);
      expect(tool2.callCount).toBe(1);
      expect(response.metadata?.tools_used).toBe(2);
    });
  });

  describe('Tool Management', () => {
    it('should add tool dynamically', () => {
      const llm = new MockLLM(['FINAL ANSWER: OK']);
      const agent = new ReasoningWithToolsAgent(llm, []);
      const tool = new MockTool('new_tool');

      agent.addTool(tool);

      expect(agent.getTool('new_tool')).toBe(tool);
    });

    it('should remove tool', () => {
      const llm = new MockLLM(['FINAL ANSWER: OK']);
      const tool = new MockTool('tool1');
      const agent = new ReasoningWithToolsAgent(llm, [tool]);

      const removed = agent.removeTool('tool1');

      expect(removed).toBe(true);
      expect(agent.getTool('tool1')).toBeUndefined();
    });

    it('should return false when removing non-existent tool', () => {
      const llm = new MockLLM(['FINAL ANSWER: OK']);
      const agent = new ReasoningWithToolsAgent(llm, []);

      const removed = agent.removeTool('nonexistent');

      expect(removed).toBe(false);
    });
  });

  describe('Trace Functionality', () => {
    it('should generate trace by default', async () => {
      const llm = new MockLLM(['Thinking', 'FINAL ANSWER: Done']);
      const agent = new ReasoningWithToolsAgent(llm, []);

      const response = await agent.process(createMessage('user', 'Question'));

      expect(response.metadata?.reasoning_trace).toBeDefined();
    });

    it('should not generate trace when disabled', async () => {
      const llm = new MockLLM(['FINAL ANSWER: Done']);
      const agent = new ReasoningWithToolsAgent(llm, [], { enableTrace: false });

      const response = await agent.process(createMessage('user', 'Question'));

      expect(response.metadata?.reasoning_trace).toBeUndefined();
    });

    it('should track all step types in trace', async () => {
      const tool = new MockTool('calculator', '42');
      const llm = new MockLLM([
        'Thinking about it',
        'TOOL_CALL: calculator\nPARAMETERS: {}',
        'FINAL ANSWER: 42',
      ]);
      const agent = new ReasoningWithToolsAgent(llm, [tool]);

      const response = await agent.process(createMessage('user', 'Calculate'));

      const trace = response.metadata?.reasoning_trace;
      expect(trace).toBeDefined();
      expect(trace.steps.some((s: any) => s.step_type === 'thinking')).toBe(true);
      expect(trace.steps.some((s: any) => s.step_type === 'tool_call')).toBe(true);
      expect(trace.steps.some((s: any) => s.step_type === 'tool_result')).toBe(true);
      expect(trace.steps.some((s: any) => s.step_type === 'conclusion')).toBe(true);
    });
  });

  describe('Conclusion Detection', () => {
    it('should detect "FINAL ANSWER:" marker', async () => {
      const llm = new MockLLM(['FINAL ANSWER: 42']);
      const agent = new ReasoningWithToolsAgent(llm, []);

      const response = await agent.process(createMessage('user', 'Question'));

      expect(response.content).toContain('42');
    });

    it('should detect "CONCLUSION:" marker', async () => {
      const llm = new MockLLM(['CONCLUSION: The answer is 42']);
      const agent = new ReasoningWithToolsAgent(llm, []);

      const response = await agent.process(createMessage('user', 'Question'));

      expect(response.content).toContain('42');
    });

    it('should detect "Therefore," marker', async () => {
      const llm = new MockLLM(['Therefore, the result is 42']);
      const agent = new ReasoningWithToolsAgent(llm, []);

      const response = await agent.process(createMessage('user', 'Question'));

      expect(response.content).toBeDefined();
    });

    it('should detect "The answer is" marker', async () => {
      const llm = new MockLLM(['The answer is 42']);
      const agent = new ReasoningWithToolsAgent(llm, []);

      const response = await agent.process(createMessage('user', 'Question'));

      expect(response.content).toBeDefined();
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty tool parameters', async () => {
      const tool = new MockTool('tool1', 'result');
      const llm = new MockLLM(['TOOL_CALL: tool1\nPARAMETERS: {}', 'FINAL ANSWER: Done']);
      const agent = new ReasoningWithToolsAgent(llm, [tool]);

      const response = await agent.process(createMessage('user', 'Test'));

      expect(tool.callCount).toBe(1);
      expect(tool.lastParameters).toEqual({});
    });

    it('should handle malformed tool call', async () => {
      const llm = new MockLLM(['TOOL_CALL: invalid format', 'FINAL ANSWER: Done anyway']);
      const agent = new ReasoningWithToolsAgent(llm, []);

      const response = await agent.process(createMessage('user', 'Test'));

      expect(response.content).toBeDefined();
    });

    it('should handle no conclusion within max steps', async () => {
      const responses = Array(5)
        .fill(null)
        .map((_, i) => `Thinking step ${i + 1}`);
      const llm = new MockLLM(responses);
      const agent = new ReasoningWithToolsAgent(llm, [], { maxReasoningSteps: 3 });

      const response = await agent.process(createMessage('user', 'Question'));

      // Should return something even without proper conclusion
      expect(response.content).toBeDefined();
    });
  });
});
