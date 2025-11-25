/**
 * Tests for Reflection pattern.
 */

import {
  ReflectionAgent,
  StopReason,
  CritiqueFormat,
  ReflectionStep,
} from '../patterns/reflection';
import { Agent, Message, createMessage } from '../core/interfaces';

/**
 * Mock agent for testing.
 */
class MockAgent implements Agent {
  readonly name: string;
  private responses: string[];
  private responseIndex = 0;

  constructor(name: string, responses: string[]) {
    this.name = name;
    this.responses = responses;
  }

  async process(message: Message): Promise<Message> {
    if (this.responseIndex >= this.responses.length) {
      throw new Error('No more mock responses available');
    }

    const response = this.responses[this.responseIndex++];
    return createMessage('assistant', response);
  }
}

describe('ReflectionAgent', () => {
  describe('Configuration Validation', () => {
    it('should require generator', () => {
      expect(() => {
        new ReflectionAgent({
          generator: null as any,
          critic: new MockAgent('critic', []),
        });
      }).toThrow('generator is required');
    });

    it('should require critic', () => {
      expect(() => {
        new ReflectionAgent({
          generator: new MockAgent('generator', []),
          critic: null as any,
        });
      }).toThrow('critic is required');
    });

    it('should validate maxIterations', () => {
      expect(() => {
        new ReflectionAgent({
          generator: new MockAgent('generator', []),
          critic: new MockAgent('critic', []),
          maxIterations: 0,
        });
      }).toThrow('maxIterations must be at least 1');
    });

    it('should validate qualityThreshold', () => {
      expect(() => {
        new ReflectionAgent({
          generator: new MockAgent('generator', []),
          critic: new MockAgent('critic', []),
          qualityThreshold: 1.5,
        });
      }).toThrow('qualityThreshold must be between 0.0 and 1.0');
    });

    it('should validate improvementThreshold', () => {
      expect(() => {
        new ReflectionAgent({
          generator: new MockAgent('generator', []),
          critic: new MockAgent('critic', []),
          improvementThreshold: -0.1,
        });
      }).toThrow('improvementThreshold must be between 0.0 and 1.0');
    });

    it('should use default values', () => {
      const agent = new ReflectionAgent({
        generator: new MockAgent('generator', []),
        critic: new MockAgent('critic', []),
      });

      expect(agent).toBeDefined();
      expect(agent.name).toBe('ReflectionAgent');
    });
  });

  describe('Quality Threshold Stop', () => {
    it('should stop when quality threshold is met', async () => {
      const generator = new MockAgent('generator', ['Output v1']);
      const critic = new MockAgent('critic', [
        JSON.stringify({ score: 0.95, feedback: 'Excellent!' }),
      ]);

      const agent = new ReflectionAgent({
        generator,
        critic,
        maxIterations: 5,
        qualityThreshold: 0.9,
      });

      const result = await agent.process(createMessage('user', 'Test task'));

      expect(result.metadata?.stopReason).toBe(StopReason.QUALITY_THRESHOLD_MET);
      expect(result.metadata?.reflectionIterations).toBe(1);
      expect(result.metadata?.finalQualityScore).toBe(0.95);
    });
  });

  describe('Perfect Score Stop', () => {
    it('should stop on perfect score', async () => {
      const generator = new MockAgent('generator', ['Perfect output']);
      const critic = new MockAgent('critic', [
        JSON.stringify({ score: 1.0, feedback: 'Perfect!' }),
      ]);

      const agent = new ReflectionAgent({
        generator,
        critic,
        maxIterations: 5,
      });

      const result = await agent.process(createMessage('user', 'Test'));

      expect(result.metadata?.stopReason).toBe(StopReason.PERFECT_SCORE);
      expect(result.metadata?.finalQualityScore).toBe(1.0);
    });
  });

  describe('Minimal Improvement Stop', () => {
    it('should stop when improvement is minimal', async () => {
      const generator = new MockAgent('generator', [
        'Output v1',
        'Output v2',
        'Output v3',
      ]);
      const critic = new MockAgent('critic', [
        JSON.stringify({ score: 0.6, feedback: 'Good' }),
        JSON.stringify({ score: 0.61, feedback: 'Slightly better' }),
        JSON.stringify({ score: 0.611, feedback: 'Minimal change' }),
      ]);

      const agent = new ReflectionAgent({
        generator,
        critic,
        maxIterations: 5,
        qualityThreshold: 0.9,
        improvementThreshold: 0.05,
      });

      const result = await agent.process(createMessage('user', 'Test'));

      expect(result.metadata?.stopReason).toBe(StopReason.MINIMAL_IMPROVEMENT);
      expect(result.metadata?.reflectionIterations).toBe(2);
    });
  });

  describe('Max Iterations Stop', () => {
    it('should stop at max iterations', async () => {
      const generator = new MockAgent('generator', [
        'Output v1',
        'Output v2',
        'Output v3',
        'Output v4', // Need one more for after last critique
      ]);
      const critic = new MockAgent('critic', [
        JSON.stringify({ score: 0.5, feedback: 'OK' }),
        JSON.stringify({ score: 0.6, feedback: 'Better' }),
        JSON.stringify({ score: 0.7, feedback: 'Good' }),
      ]);

      const agent = new ReflectionAgent({
        generator,
        critic,
        maxIterations: 3,
        qualityThreshold: 0.95,
        improvementThreshold: 0.01,
      });

      const result = await agent.process(createMessage('user', 'Test'));

      expect(result.metadata?.stopReason).toBe(StopReason.MAX_ITERATIONS);
      expect(result.metadata?.reflectionIterations).toBe(3);
    });
  });

  describe('Critique Parsing', () => {
    it('should parse structured JSON critique', async () => {
      const generator = new MockAgent('generator', ['Test output']);
      const critic = new MockAgent('critic', [
        JSON.stringify({ score: 0.75, feedback: 'Good work' }),
      ]);

      const agent = new ReflectionAgent({
        generator,
        critic,
        critiqueFormat: CritiqueFormat.STRUCTURED,
        qualityThreshold: 0.7,
      });

      const result = await agent.process(createMessage('user', 'Test'));

      expect(result.metadata?.finalQualityScore).toBe(0.75);
      expect(result.metadata?.stopReason).toBe(StopReason.QUALITY_THRESHOLD_MET);
    });

    it('should handle free-form critique with Score: pattern', async () => {
      const generator = new MockAgent('generator', ['Output']);
      const critic = new MockAgent('critic', [
        'This is good work. Score: 0.85. Well done.',
      ]);

      const agent = new ReflectionAgent({
        generator,
        critic,
        critiqueFormat: CritiqueFormat.FREE_FORM,
        qualityThreshold: 0.8,
      });

      const result = await agent.process(createMessage('user', 'Test'));

      expect(result.metadata?.finalQualityScore).toBe(0.85);
    });

    it('should handle critique with percentage', async () => {
      const generator = new MockAgent('generator', ['Output']);
      const critic = new MockAgent('critic', ['Quality: 75% - needs improvement']);

      const agent = new ReflectionAgent({
        generator,
        critic,
        critiqueFormat: CritiqueFormat.FREE_FORM,
        qualityThreshold: 0.7,
      });

      const result = await agent.process(createMessage('user', 'Test'));

      expect(result.metadata?.finalQualityScore).toBe(0.75);
    });

    it('should handle critique with X/10 rating', async () => {
      const generator = new MockAgent('generator', ['Output']);
      const critic = new MockAgent('critic', ['Rating: 8.5/10']);

      const agent = new ReflectionAgent({
        generator,
        critic,
        critiqueFormat: CritiqueFormat.FREE_FORM,
        qualityThreshold: 0.8,
      });

      const result = await agent.process(createMessage('user', 'Test'));

      expect(result.metadata?.finalQualityScore).toBe(0.85);
    });

    it('should fallback to 0.5 if no score found', async () => {
      const generator = new MockAgent('generator', ['Output', 'Output v2']); // Need one more for refinement
      const critic = new MockAgent('critic', ['This looks okay']);

      const agent = new ReflectionAgent({
        generator,
        critic,
        critiqueFormat: CritiqueFormat.FREE_FORM,
        qualityThreshold: 0.9,
        maxIterations: 1,
      });

      const result = await agent.process(createMessage('user', 'Test'));

      expect(result.metadata?.finalQualityScore).toBe(0.5);
    });

    it('should handle malformed JSON gracefully', async () => {
      const generator = new MockAgent('generator', ['Output']);
      const critic = new MockAgent('critic', ['{invalid json Score: 0.8}']);

      const agent = new ReflectionAgent({
        generator,
        critic,
        critiqueFormat: CritiqueFormat.STRUCTURED,
        qualityThreshold: 0.7,
      });

      const result = await agent.process(createMessage('user', 'Test'));

      // Should fallback to free-form parsing
      expect(result.metadata?.finalQualityScore).toBe(0.8);
    });
  });

  describe('Verbose Mode', () => {
    it('should include reflection history when verbose=true', async () => {
      const generator = new MockAgent('generator', ['Output v1', 'Output v2']);
      const critic = new MockAgent('critic', [
        JSON.stringify({ score: 0.6, feedback: 'OK' }),
        JSON.stringify({ score: 0.95, feedback: 'Excellent' }),
      ]);

      const agent = new ReflectionAgent({
        generator,
        critic,
        maxIterations: 5,
        qualityThreshold: 0.9,
        verbose: true,
      });

      const result = await agent.process(createMessage('user', 'Test'));

      expect(result.metadata?.reflectionHistory).toBeDefined();
      const history = result.metadata?.reflectionHistory as ReflectionStep[];
      expect(history.length).toBe(2);
      expect(history[0].iteration).toBe(1);
      expect(history[0].qualityScore).toBe(0.6);
      expect(history[1].iteration).toBe(2);
      expect(history[1].qualityScore).toBe(0.95);
    });

    it('should not include history when verbose=false', async () => {
      const generator = new MockAgent('generator', ['Output']);
      const critic = new MockAgent('critic', [
        JSON.stringify({ score: 0.95, feedback: 'Good' }),
      ]);

      const agent = new ReflectionAgent({
        generator,
        critic,
        verbose: false,
        qualityThreshold: 0.9,
      });

      const result = await agent.process(createMessage('user', 'Test'));

      expect(result.metadata?.reflectionHistory).toBeUndefined();
    });
  });

  describe('Total Improvement', () => {
    it('should calculate total improvement', async () => {
      const generator = new MockAgent('generator', [
        'Output v1',
        'Output v2',
        'Output v3',
      ]);
      const critic = new MockAgent('critic', [
        JSON.stringify({ score: 0.5, feedback: 'Needs work' }),
        JSON.stringify({ score: 0.7, feedback: 'Better' }),
        JSON.stringify({ score: 0.95, feedback: 'Great!' }),
      ]);

      const agent = new ReflectionAgent({
        generator,
        critic,
        maxIterations: 5,
        qualityThreshold: 0.9,
      });

      const result = await agent.process(createMessage('user', 'Test'));

      expect(result.metadata?.initialQualityScore).toBe(0.5);
      expect(result.metadata?.finalQualityScore).toBe(0.95);
      expect(result.metadata?.totalImprovement).toBeCloseTo(0.45, 10);
    });
  });

  describe('Capabilities', () => {
    it('should combine capabilities from generator and critic', () => {
      class CapableAgent implements Agent {
        readonly name = 'capable';
        readonly capabilities = ['coding', 'testing'];
        async process(message: Message): Promise<Message> {
          return createMessage('assistant', 'response');
        }
      }

      const agent = new ReflectionAgent({
        generator: new CapableAgent(),
        critic: new CapableAgent(),
      });

      const caps = agent.capabilities;
      expect(caps).toContain('coding');
      expect(caps).toContain('testing');
      expect(caps).toContain('reflection');
      expect(caps).toContain('self-critique');
    });

    it('should handle agents without capabilities', () => {
      const agent = new ReflectionAgent({
        generator: new MockAgent('gen', []),
        critic: new MockAgent('crit', []),
      });

      const caps = agent.capabilities;
      expect(caps).toContain('reflection');
      expect(caps).toContain('self-critique');
    });
  });
});
