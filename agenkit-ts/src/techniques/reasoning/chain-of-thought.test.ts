/**
 * Tests for Chain-of-Thought reasoning technique.
 */

import { describe, it, expect } from 'vitest';
import { Agent, Message, createMessage } from '../../core/interfaces';
import { ChainOfThought, createChainOfThought } from './chain-of-thought';

/**
 * Mock agent for testing.
 */
class MockAgent implements Agent {
  readonly name: string;
  readonly capabilities: string[];
  private readonly response: string;
  private shouldFail: boolean;

  constructor(response: string) {
    this.name = 'mock_agent';
    this.capabilities = ['mock', 'testing'];
    this.response = response;
    this.shouldFail = false;
  }

  setFail(fail: boolean): void {
    this.shouldFail = fail;
  }

  async process(message: Message): Promise<Message> {
    if (this.shouldFail) {
      throw new Error('Mock agent failed');
    }

    return createMessage('assistant', this.response);
  }
}

describe('ChainOfThought', () => {
  describe('basic functionality', () => {
    it('should process message with CoT prompting', async () => {
      const mockAgent = new MockAgent(
        '1. First, let me analyze the problem.\n2. Then, I will calculate.\n3. The answer is 42.',
      );

      const cot = new ChainOfThought(mockAgent);

      const message = createMessage('user', 'What is the answer?');
      const response = await cot.process(message);

      expect(response.content).toContain('42');
      expect(response.metadata?.technique).toBe('chain_of_thought');
      expect(response.metadata?.reasoning_steps).toHaveLength(3);
      expect(response.metadata?.num_steps).toBe(3);
    });

    it('should have correct name and capabilities', () => {
      const mockAgent = new MockAgent('response');
      const cot = new ChainOfThought(mockAgent);

      expect(cot.name).toBe('chain_of_thought');
      expect(cot.capabilities).toContain('reasoning');
      expect(cot.capabilities).toContain('step_by_step');
      expect(cot.capabilities).toContain('chain_of_thought');
      expect(cot.capabilities).toContain('explainable_ai');
    });

    it('should apply prompt template', async () => {
      let capturedPrompt = '';
      const customAgent: Agent = {
        name: 'custom',
        async process(message: Message): Promise<Message> {
          capturedPrompt = String(message.content);
          return createMessage('assistant', 'Step 1: answer');
        },
      };

      const cot = new ChainOfThought(customAgent);

      await cot.process(createMessage('user', 'Test query'));

      expect(capturedPrompt).toContain("Let's think step by step:");
      expect(capturedPrompt).toContain('Test query');
    });
  });

  describe('step parsing', () => {
    it('should parse numbered steps', async () => {
      const mockAgent = new MockAgent(
        '1. First step\n2. Second step\n3. Third step\n4. Fourth step',
      );

      const cot = new ChainOfThought(mockAgent);

      const message = createMessage('user', 'Test');
      const response = await cot.process(message);

      const steps = response.metadata?.reasoning_steps as string[];
      expect(steps).toHaveLength(4);
      expect(steps[0]).toBe('First step');
      expect(steps[1]).toBe('Second step');
      expect(steps[2]).toBe('Third step');
      expect(steps[3]).toBe('Fourth step');
    });

    it('should parse numbered steps with parentheses', async () => {
      const mockAgent = new MockAgent('1) First step\n2) Second step\n3) Third step');

      const cot = new ChainOfThought(mockAgent);

      const message = createMessage('user', 'Test');
      const response = await cot.process(message);

      const steps = response.metadata?.reasoning_steps as string[];
      expect(steps).toHaveLength(3);
      expect(steps[0]).toBe('First step');
    });

    it('should parse bullet points with dashes', async () => {
      const mockAgent = new MockAgent('- First step\n- Second step\n- Third step');

      const cot = new ChainOfThought(mockAgent);

      const message = createMessage('user', 'Test');
      const response = await cot.process(message);

      const steps = response.metadata?.reasoning_steps as string[];
      expect(steps).toHaveLength(3);
      expect(steps[0]).toBe('First step');
    });

    it('should parse bullet points with asterisks', async () => {
      const mockAgent = new MockAgent('* First step\n* Second step\n* Third step');

      const cot = new ChainOfThought(mockAgent);

      const message = createMessage('user', 'Test');
      const response = await cot.process(message);

      const steps = response.metadata?.reasoning_steps as string[];
      expect(steps).toHaveLength(3);
      expect(steps[0]).toBe('First step');
    });

    it('should parse bullet points with bullet character', async () => {
      const mockAgent = new MockAgent('• First step\n• Second step\n• Third step');

      const cot = new ChainOfThought(mockAgent);

      const message = createMessage('user', 'Test');
      const response = await cot.process(message);

      const steps = response.metadata?.reasoning_steps as string[];
      expect(steps).toHaveLength(3);
      expect(steps[0]).toBe('First step');
    });

    it('should fall back to delimiter-based splitting', async () => {
      const mockAgent = new MockAgent('First thought\nSecond thought\nThird thought');

      const cot = new ChainOfThought(mockAgent);

      const message = createMessage('user', 'Test');
      const response = await cot.process(message);

      const steps = response.metadata?.reasoning_steps as string[];
      expect(steps).toHaveLength(3);
      expect(steps[0]).toBe('First thought');
    });

    it('should handle mixed content with numbered steps', async () => {
      const mockAgent = new MockAgent(
        'Let me think through this:\n1. First, analyze\n2. Then, calculate\n3. Finally, conclude',
      );

      const cot = new ChainOfThought(mockAgent);

      const message = createMessage('user', 'Test');
      const response = await cot.process(message);

      const steps = response.metadata?.reasoning_steps as string[];
      expect(steps).toHaveLength(3);
      expect(steps[0]).toBe('First, analyze');
    });
  });

  describe('custom configuration', () => {
    it('should use custom prompt template', async () => {
      let capturedPrompt = '';
      const customAgent: Agent = {
        name: 'custom',
        async process(message: Message): Promise<Message> {
          capturedPrompt = String(message.content);
          return createMessage('assistant', '1. Answer');
        },
      };

      const cot = new ChainOfThought(customAgent, {
        promptTemplate: 'Solve carefully:\n{query}',
      });

      await cot.process(createMessage('user', 'Test query'));

      expect(capturedPrompt).toBe('Solve carefully:\nTest query');
    });

    it('should respect maxSteps limit', async () => {
      const mockAgent = new MockAgent(
        '1. First\n2. Second\n3. Third\n4. Fourth\n5. Fifth\n6. Sixth',
      );

      const cot = new ChainOfThought(mockAgent, {
        maxSteps: 3,
      });

      const message = createMessage('user', 'Test');
      const response = await cot.process(message);

      const steps = response.metadata?.reasoning_steps as string[];
      expect(steps).toHaveLength(3);
      expect(response.metadata?.num_steps).toBe(3);
    });

    it('should support custom step delimiter', async () => {
      const mockAgent = new MockAgent('First step | Second step | Third step');

      const cot = new ChainOfThought(mockAgent, {
        stepDelimiter: ' | ',
      });

      const message = createMessage('user', 'Test');
      const response = await cot.process(message);

      const steps = response.metadata?.reasoning_steps as string[];
      expect(steps).toHaveLength(3);
      expect(steps[0]).toBe('First step');
    });

    it('should disable step parsing when parseSteps is false', async () => {
      const mockAgent = new MockAgent('1. First\n2. Second\n3. Third');

      const cot = new ChainOfThought(mockAgent, {
        parseSteps: false,
      });

      const message = createMessage('user', 'Test');
      const response = await cot.process(message);

      expect(response.metadata?.reasoning_steps).toBeUndefined();
      expect(response.metadata?.num_steps).toBeUndefined();
      expect(response.metadata?.technique).toBe('chain_of_thought');
    });
  });

  describe('edge cases', () => {
    it('should handle empty response', async () => {
      const mockAgent = new MockAgent('');

      const cot = new ChainOfThought(mockAgent);

      const message = createMessage('user', 'Test');
      const response = await cot.process(message);

      const steps = response.metadata?.reasoning_steps as string[];
      expect(steps).toHaveLength(0);
      expect(response.metadata?.num_steps).toBe(0);
    });

    it('should handle single step', async () => {
      const mockAgent = new MockAgent('1. Only one step');

      const cot = new ChainOfThought(mockAgent);

      const message = createMessage('user', 'Test');
      const response = await cot.process(message);

      // Single numbered step should fall back to delimiter parsing
      const steps = response.metadata?.reasoning_steps as string[];
      expect(steps.length).toBeGreaterThan(0);
    });

    it('should handle response with no clear structure', async () => {
      const mockAgent = new MockAgent('This is just a plain text response without structure.');

      const cot = new ChainOfThought(mockAgent);

      const message = createMessage('user', 'Test');
      const response = await cot.process(message);

      const steps = response.metadata?.reasoning_steps as string[];
      expect(steps).toHaveLength(1);
      expect(steps[0]).toContain('plain text response');
    });

    it('should throw error if template missing {query} placeholder', async () => {
      const mockAgent = new MockAgent('response');

      const cot = new ChainOfThought(mockAgent, {
        promptTemplate: 'This template has no placeholder',
      });

      const message = createMessage('user', 'Test');

      await expect(cot.process(message)).rejects.toThrow(
        'Prompt template must contain {query} placeholder',
      );
    });
  });

  describe('factory function', () => {
    it('should create agent with createChainOfThought', async () => {
      const mockAgent = new MockAgent('1. Step one\n2. Step two');

      const cot = createChainOfThought(mockAgent, {
        maxSteps: 5,
      });

      expect(cot).toBeInstanceOf(ChainOfThought);
      expect(cot.name).toBe('chain_of_thought');

      const message = createMessage('user', 'Test');
      const response = await cot.process(message);

      expect(response.metadata?.reasoning_steps).toHaveLength(2);
    });
  });

  describe('error handling', () => {
    it('should propagate agent errors', async () => {
      const mockAgent = new MockAgent('response');
      mockAgent.setFail(true);

      const cot = new ChainOfThought(mockAgent);

      const message = createMessage('user', 'Test');

      await expect(cot.process(message)).rejects.toThrow('Mock agent failed');
    });
  });
});
