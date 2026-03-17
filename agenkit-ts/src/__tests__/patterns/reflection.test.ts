/**
 * Comprehensive tests for ReflectionAgent pattern.
 *
 * Tests cover:
 * - Constructor validation
 * - Critique parsing (structured and free-form)
 * - Stop conditions (quality threshold, perfect score, max iterations)
 * - Result metadata
 * - Verbose mode
 */

import { describe, it, expect } from 'vitest';
import {
  ReflectionAgent,
  StopReason,
  CritiqueFormat,
} from '../../patterns/reflection';
import { Message, createMessage } from '../../core/interfaces';
import { createMockAgent, ExtendedMockAgent } from './test-helpers';

/** Generator that returns a fixed output */
function createGeneratorAgent(output: string) {
  return createMockAgent('generator', output);
}

/** Critic that returns JSON with score */
function createStructuredCriticAgent(score: number, feedback: string) {
  return createMockAgent('critic', JSON.stringify({ score, feedback }));
}

/** Critic that returns free-form text with score */
function createFreeFormCriticAgent(score: number) {
  return createMockAgent('critic', `Score: ${score}\nThe output is good.`);
}

/** Generator that returns incrementally better outputs */
class ProgressiveGeneratorAgent {
  readonly name = 'progressive_generator';
  private callCount = 0;
  readonly capabilities = ['mock'];

  async process(message: Message): Promise<Message> {
    this.callCount++;
    return createMessage('assistant', `Output version ${this.callCount}`);
  }
}

describe('ReflectionAgent', () => {
  describe('Constructor', () => {
    it('should create agent with valid configuration', () => {
      const generator = createGeneratorAgent('output');
      const critic = createStructuredCriticAgent(0.5, 'ok');

      const agent = new ReflectionAgent({ generator, critic });
      expect(agent.name).toBe('ReflectionAgent');
    });

    it('should throw when generator is missing', () => {
      const critic = createStructuredCriticAgent(0.5, 'ok');

      expect(
        () => new ReflectionAgent({ generator: null as any, critic })
      ).toThrow('generator is required');
    });

    it('should throw when critic is missing', () => {
      const generator = createGeneratorAgent('output');

      expect(
        () => new ReflectionAgent({ generator, critic: null as any })
      ).toThrow('critic is required');
    });

    it('should throw when maxIterations is less than 1', () => {
      const generator = createGeneratorAgent('output');
      const critic = createStructuredCriticAgent(0.5, 'ok');

      expect(
        () => new ReflectionAgent({ generator, critic, maxIterations: 0 })
      ).toThrow('maxIterations must be at least 1');
    });

    it('should throw when qualityThreshold is out of range', () => {
      const generator = createGeneratorAgent('output');
      const critic = createStructuredCriticAgent(0.5, 'ok');

      expect(
        () => new ReflectionAgent({ generator, critic, qualityThreshold: 1.5 })
      ).toThrow('qualityThreshold must be between 0.0 and 1.0');

      expect(
        () => new ReflectionAgent({ generator, critic, qualityThreshold: -0.1 })
      ).toThrow('qualityThreshold must be between 0.0 and 1.0');
    });

    it('should throw when improvementThreshold is out of range', () => {
      const generator = createGeneratorAgent('output');
      const critic = createStructuredCriticAgent(0.5, 'ok');

      expect(
        () => new ReflectionAgent({ generator, critic, improvementThreshold: -0.1 })
      ).toThrow('improvementThreshold must be between 0.0 and 1.0');
    });
  });

  describe('Capabilities', () => {
    it('should include reflection and self-critique', () => {
      const generator = createGeneratorAgent('output');
      const critic = createStructuredCriticAgent(0.5, 'ok');

      const agent = new ReflectionAgent({ generator, critic });

      expect(agent.capabilities).toContain('reflection');
      expect(agent.capabilities).toContain('self-critique');
    });

    it('should include generator capabilities', () => {
      const generator = new ExtendedMockAgent({
        name: 'gen',
        capabilities: ['text-generation'],
      });
      const critic = createStructuredCriticAgent(0.5, 'ok');

      const agent = new ReflectionAgent({ generator, critic });

      expect(agent.capabilities).toContain('text-generation');
    });
  });

  describe('Quality Threshold Stop', () => {
    it('should stop when quality threshold is met', async () => {
      const generator = createGeneratorAgent('good output');
      // Critic returns score above 0.9 threshold
      const critic = createStructuredCriticAgent(0.95, 'Excellent!');

      const agent = new ReflectionAgent({
        generator,
        critic,
        qualityThreshold: 0.9,
      });

      const result = await agent.process(createMessage('user', 'Write something'));

      expect(result.metadata?.stopReason).toBe(StopReason.QUALITY_THRESHOLD_MET);
    });
  });

  describe('Perfect Score Stop', () => {
    it('should stop at perfect score', async () => {
      const generator = createGeneratorAgent('perfect output');
      const critic = createStructuredCriticAgent(1.0, 'Perfect!');

      const agent = new ReflectionAgent({ generator, critic });

      const result = await agent.process(createMessage('user', 'Write something'));

      expect(result.metadata?.stopReason).toBe(StopReason.PERFECT_SCORE);
    });
  });

  describe('Max Iterations Stop', () => {
    it('should stop at max iterations', async () => {
      const generator = createGeneratorAgent('mediocre output');
      // Critic always returns low score
      const critic = createStructuredCriticAgent(0.3, 'Needs improvement');

      const agent = new ReflectionAgent({
        generator,
        critic,
        maxIterations: 2,
        qualityThreshold: 0.9,
        improvementThreshold: 0.0, // never stop on minimal improvement
      });

      const result = await agent.process(createMessage('user', 'Write something'));

      expect(result.metadata?.stopReason).toBe(StopReason.MAX_ITERATIONS);
    });
  });

  describe('Result Metadata', () => {
    it('should include reflectionIterations in metadata', async () => {
      const generator = createGeneratorAgent('output');
      const critic = createStructuredCriticAgent(0.95, 'Great!');

      const agent = new ReflectionAgent({ generator, critic });
      const result = await agent.process(createMessage('user', 'Task'));

      expect(typeof result.metadata?.reflectionIterations).toBe('number');
      expect(result.metadata!.reflectionIterations as number).toBeGreaterThan(0);
    });

    it('should include finalQualityScore in metadata', async () => {
      const generator = createGeneratorAgent('output');
      const critic = createStructuredCriticAgent(0.8, 'Good');

      const agent = new ReflectionAgent({
        generator,
        critic,
        maxIterations: 1,
      });
      const result = await agent.process(createMessage('user', 'Task'));

      expect(typeof result.metadata?.finalQualityScore).toBe('number');
    });

    it('should include stopReason in metadata', async () => {
      const generator = createGeneratorAgent('output');
      const critic = createStructuredCriticAgent(0.95, 'Great!');

      const agent = new ReflectionAgent({ generator, critic });
      const result = await agent.process(createMessage('user', 'Task'));

      expect(result.metadata?.stopReason).toBeDefined();
    });
  });

  describe('Verbose Mode', () => {
    it('should include reflection history in verbose mode', async () => {
      const generator = createGeneratorAgent('output');
      const critic = createStructuredCriticAgent(0.95, 'Great!');

      const agent = new ReflectionAgent({
        generator,
        critic,
        verbose: true,
      });
      const result = await agent.process(createMessage('user', 'Task'));

      expect(result.metadata?.reflectionHistory).toBeDefined();
    });

    it('should not include reflection history in non-verbose mode', async () => {
      const generator = createGeneratorAgent('output');
      const critic = createStructuredCriticAgent(0.95, 'Great!');

      const agent = new ReflectionAgent({
        generator,
        critic,
        verbose: false,
      });
      const result = await agent.process(createMessage('user', 'Task'));

      expect(result.metadata?.reflectionHistory).toBeUndefined();
    });
  });

  describe('Free-Form Critique', () => {
    it('should parse free-form critique with score', async () => {
      const generator = createGeneratorAgent('output');
      const critic = createFreeFormCriticAgent(0.9);

      const agent = new ReflectionAgent({
        generator,
        critic,
        critiqueFormat: CritiqueFormat.FREE_FORM,
        qualityThreshold: 0.85,
      });

      const result = await agent.process(createMessage('user', 'Task'));

      expect(result.metadata?.stopReason).toBe(StopReason.QUALITY_THRESHOLD_MET);
    });
  });

  describe('Reset Between Calls', () => {
    it('should reset history between process calls', async () => {
      const generator = createGeneratorAgent('output');
      const critic = createStructuredCriticAgent(0.95, 'Great!');

      const agent = new ReflectionAgent({ generator, critic });

      const result1 = await agent.process(createMessage('user', 'Task 1'));
      const result2 = await agent.process(createMessage('user', 'Task 2'));

      // Both should have valid iterations
      expect(result1.metadata?.reflectionIterations).toBeGreaterThan(0);
      expect(result2.metadata?.reflectionIterations).toBeGreaterThan(0);
    });
  });
});
