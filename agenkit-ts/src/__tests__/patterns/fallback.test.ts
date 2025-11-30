/**
 * Comprehensive tests for Fallback pattern.
 *
 * Tests cover:
 * - Constructor validation
 * - Sequential retry logic
 * - Success on first/middle/last agent
 * - All agents fail scenario
 * - Error collection
 * - Recovery strategies
 * - Edge cases
 */

import { describe, it, expect } from 'vitest';
import {
  FallbackAgent,
  RecoveryAgent,
  withRecovery,
  DefaultRecovery,
} from '../../patterns/fallback';
import { Message, createMessage } from '../../core/interfaces';
import {
  createMockAgent,
  createErrorAgent,
  FlakyAgent,
  CallCountingAgent,
  validateMessage,
  hasMetadata,
  getMetadata,
} from './test-helpers';

describe('FallbackAgent', () => {
  describe('Constructor', () => {
    it('should create agent with valid agents list', () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const fallback = new FallbackAgent([agent1, agent2]);

      expect(fallback).toBeDefined();
      expect(fallback.name).toBe('FallbackAgent');
    });

    it('should throw error with empty agents list', () => {
      expect(() => new FallbackAgent([])).toThrow('at least one agent is required');
    });

    it('should throw error with null agents', () => {
      expect(() => new FallbackAgent(null as any)).toThrow('at least one agent is required');
    });

    it('should throw error with undefined agents', () => {
      expect(() => new FallbackAgent(undefined as any)).toThrow('at least one agent is required');
    });

    it('should work with single agent', () => {
      const agent = createMockAgent('solo', 'result');
      const fallback = new FallbackAgent([agent]);

      expect(fallback).toBeDefined();
      expect(fallback.capabilities).toContain('fallback');
    });
  });

  describe('Capabilities', () => {
    it('should include fallback capabilities', () => {
      const agent = createMockAgent('agent', 'result');
      const fallback = new FallbackAgent([agent]);

      const caps = fallback.capabilities;
      expect(caps).toContain('fallback');
      expect(caps).toContain('retry');
      expect(caps).toContain('high-availability');
    });

    it('should combine capabilities from all agents', () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const fallback = new FallbackAgent([agent1, agent2]);
      const caps = fallback.capabilities;

      expect(caps).toContain('mock');
      expect(caps).toContain('fallback');
    });

    it('should deduplicate capabilities', () => {
      const agent1 = createMockAgent('agent1', 'result1');
      const agent2 = createMockAgent('agent2', 'result2');

      const fallback = new FallbackAgent([agent1, agent2]);
      const caps = fallback.capabilities;

      const mockCount = caps.filter((c) => c === 'mock').length;
      expect(mockCount).toBe(1);
    });
  });

  describe('Basic Processing', () => {
    it('should return first agent result on success', async () => {
      const agent1 = createMockAgent('agent1', 'first result');
      const agent2 = createMockAgent('agent2', 'second result');

      const fallback = new FallbackAgent([agent1, agent2]);

      const input = createMessage('user', 'test');
      const result = await fallback.process(input);

      validateMessage(result);
      expect(result.content).toBe('first result');
    });

    it('should throw error with null message', async () => {
      const agent = createMockAgent('agent', 'result');
      const fallback = new FallbackAgent([agent]);

      await expect(fallback.process(null as any)).rejects.toThrow('message cannot be nil');
    });

    it('should throw error with undefined message', async () => {
      const agent = createMockAgent('agent', 'result');
      const fallback = new FallbackAgent([agent]);

      await expect(fallback.process(undefined as any)).rejects.toThrow('message cannot be nil');
    });

    it('should not call second agent if first succeeds', async () => {
      const agent1 = createMockAgent('agent1', 'success');
      const agent2 = new CallCountingAgent('agent2', 'fallback');

      const fallback = new FallbackAgent([agent1, agent2]);

      const input = createMessage('user', 'test');
      await fallback.process(input);

      expect(agent2.callCount).toBe(0);
    });
  });

  describe('Fallback Logic', () => {
    it('should try second agent if first fails', async () => {
      const agent1 = createErrorAgent('agent1', 'first failed');
      const agent2 = createMockAgent('agent2', 'second success');

      const fallback = new FallbackAgent([agent1, agent2]);

      const input = createMessage('user', 'test');
      const result = await fallback.process(input);

      expect(result.content).toBe('second success');
    });

    it('should try third agent if first two fail', async () => {
      const agent1 = createErrorAgent('agent1', 'first failed');
      const agent2 = createErrorAgent('agent2', 'second failed');
      const agent3 = createMockAgent('agent3', 'third success');

      const fallback = new FallbackAgent([agent1, agent2, agent3]);

      const input = createMessage('user', 'test');
      const result = await fallback.process(input);

      expect(result.content).toBe('third success');
    });

    it('should succeed on last agent', async () => {
      const agent1 = createErrorAgent('agent1', 'fail1');
      const agent2 = createErrorAgent('agent2', 'fail2');
      const agent3 = createMockAgent('agent3', 'final success');

      const fallback = new FallbackAgent([agent1, agent2, agent3]);

      const input = createMessage('user', 'test');
      const result = await fallback.process(input);

      expect(result.content).toBe('final success');
      expect(getMetadata(result, 'fallback_success_index')).toBe(2);
    });

    it('should succeed on middle agent', async () => {
      const agent1 = createErrorAgent('agent1', 'fail1');
      const agent2 = createMockAgent('agent2', 'middle success');
      const agent3 = createMockAgent('agent3', 'not reached');

      const fallback = new FallbackAgent([agent1, agent2, agent3]);

      const input = createMessage('user', 'test');
      const result = await fallback.process(input);

      expect(result.content).toBe('middle success');
      expect(getMetadata(result, 'fallback_success_index')).toBe(1);
    });

    it('should throw error if all agents fail', async () => {
      const agent1 = createErrorAgent('agent1', 'error1');
      const agent2 = createErrorAgent('agent2', 'error2');
      const agent3 = createErrorAgent('agent3', 'error3');

      const fallback = new FallbackAgent([agent1, agent2, agent3]);

      const input = createMessage('user', 'test');
      await expect(fallback.process(input)).rejects.toThrow('all 3 agents failed');
    });

    it('should try agents in order', async () => {
      const callOrder: string[] = [];

      const agent1 = createMockAgent('agent1', '');
      agent1.process = async () => {
        callOrder.push('agent1');
        throw new Error('fail');
      };

      const agent2 = createMockAgent('agent2', '');
      agent2.process = async () => {
        callOrder.push('agent2');
        throw new Error('fail');
      };

      const agent3 = createMockAgent('agent3', '');
      agent3.process = async () => {
        callOrder.push('agent3');
        return createMessage('assistant', 'success');
      };

      const fallback = new FallbackAgent([agent1, agent2, agent3]);

      const input = createMessage('user', 'test');
      await fallback.process(input);

      expect(callOrder).toEqual(['agent1', 'agent2', 'agent3']);
    });
  });

  describe('Metadata', () => {
    it('should add fallback metadata to successful result', async () => {
      const agent1 = createErrorAgent('agent1', 'fail');
      const agent2 = createMockAgent('agent2', 'success');

      const fallback = new FallbackAgent([agent1, agent2]);

      const input = createMessage('user', 'test');
      const result = await fallback.process(input);

      expect(hasMetadata(result, 'fallback_attempts')).toBe(true);
      expect(hasMetadata(result, 'fallback_success_index')).toBe(true);
      expect(hasMetadata(result, 'fallback_success_agent')).toBe(true);
      expect(hasMetadata(result, 'fallback_total_agents')).toBe(true);
    });

    it('should record correct attempt count', async () => {
      const agent1 = createErrorAgent('agent1', 'fail');
      const agent2 = createMockAgent('agent2', 'success');

      const fallback = new FallbackAgent([agent1, agent2]);

      const input = createMessage('user', 'test');
      const result = await fallback.process(input);

      expect(getMetadata(result, 'fallback_attempts')).toBe(2);
      expect(getMetadata(result, 'fallback_total_agents')).toBe(2);
    });

    it('should record successful agent information', async () => {
      const agent1 = createErrorAgent('agent1', 'fail');
      const agent2 = createMockAgent('successAgent', 'success');

      const fallback = new FallbackAgent([agent1, agent2]);

      const input = createMessage('user', 'test');
      const result = await fallback.process(input);

      expect(getMetadata(result, 'fallback_success_agent')).toBe('successAgent');
      expect(getMetadata(result, 'fallback_success_index')).toBe(1);
    });

    it('should include failed attempts in metadata', async () => {
      const agent1 = createErrorAgent('agent1', 'error1');
      const agent2 = createErrorAgent('agent2', 'error2');
      const agent3 = createMockAgent('agent3', 'success');

      const fallback = new FallbackAgent([agent1, agent2, agent3]);

      const input = createMessage('user', 'test');
      const result = await fallback.process(input);

      expect(hasMetadata(result, 'fallback_failed_attempts')).toBe(true);
      const failures = getMetadata(result, 'fallback_failed_attempts') as any[];
      expect(failures).toHaveLength(2);
      expect(failures[0].index).toBe(0);
      expect(failures[0].agent).toBe('agent1');
      expect(failures[0].error).toContain('error1');
      expect(failures[1].index).toBe(1);
      expect(failures[1].agent).toBe('agent2');
      expect(failures[1].error).toContain('error2');
    });

    it('should not include failed attempts if first succeeds', async () => {
      const agent1 = createMockAgent('agent1', 'success');
      const agent2 = createMockAgent('agent2', 'not used');

      const fallback = new FallbackAgent([agent1, agent2]);

      const input = createMessage('user', 'test');
      const result = await fallback.process(input);

      expect(hasMetadata(result, 'fallback_failed_attempts')).toBe(false);
    });
  });

  describe('Error Collection', () => {
    it('should collect all error messages', async () => {
      const agent1 = createErrorAgent('agent1', 'first error');
      const agent2 = createErrorAgent('agent2', 'second error');
      const agent3 = createErrorAgent('agent3', 'third error');

      const fallback = new FallbackAgent([agent1, agent2, agent3]);

      const input = createMessage('user', 'test');

      try {
        await fallback.process(input);
        expect.fail('Should have thrown error');
      } catch (error) {
        const errorMsg = (error as Error).message;
        expect(errorMsg).toContain('first error');
        expect(errorMsg).toContain('second error');
        expect(errorMsg).toContain('third error');
      }
    });

    it('should include agent names in error', async () => {
      const agent1 = createErrorAgent('primaryAgent', 'error1');
      const agent2 = createErrorAgent('backupAgent', 'error2');

      const fallback = new FallbackAgent([agent1, agent2]);

      const input = createMessage('user', 'test');

      try {
        await fallback.process(input);
        expect.fail('Should have thrown error');
      } catch (error) {
        const errorMsg = (error as Error).message;
        expect(errorMsg).toContain('primaryAgent');
        expect(errorMsg).toContain('backupAgent');
      }
    });

    it('should include agent indices in error', async () => {
      const agent1 = createErrorAgent('agent1', 'error1');
      const agent2 = createErrorAgent('agent2', 'error2');

      const fallback = new FallbackAgent([agent1, agent2]);

      const input = createMessage('user', 'test');

      try {
        await fallback.process(input);
        expect.fail('Should have thrown error');
      } catch (error) {
        const errorMsg = (error as Error).message;
        expect(errorMsg).toContain('[0]');
        expect(errorMsg).toContain('[1]');
      }
    });
  });

  describe('RecoveryAgent', () => {
    it('should return primary result on success', async () => {
      const primary = createMockAgent('primary', 'primary result');
      const recovery = withRecovery(primary, async () => createMessage('assistant', 'recovered'));

      const input = createMessage('user', 'test');
      const result = await recovery.process(input);

      expect(result.content).toBe('primary result');
      expect(hasMetadata(result, 'recovery_used')).toBe(false);
    });

    it('should use recovery on primary failure', async () => {
      const primary = createErrorAgent('primary', 'primary failed');
      const recovery = withRecovery(primary, async () =>
        createMessage('assistant', 'recovered response'),
      );

      const input = createMessage('user', 'test');
      const result = await recovery.process(input);

      expect(result.content).toBe('recovered response');
      expect(getMetadata(result, 'recovery_used')).toBe(true);
    });

    it('should include original error in recovery metadata', async () => {
      const primary = createErrorAgent('primary', 'original error');
      const recovery = withRecovery(primary, async () => createMessage('assistant', 'recovered'));

      const input = createMessage('user', 'test');
      const result = await recovery.process(input);

      expect(getMetadata(result, 'original_error')).toContain('original error');
    });

    it('should throw if both primary and recovery fail', async () => {
      const primary = createErrorAgent('primary', 'primary error');
      const recovery = withRecovery(primary, async () => {
        throw new Error('recovery error');
      });

      const input = createMessage('user', 'test');

      try {
        await recovery.process(input);
        expect.fail('Should have thrown error');
      } catch (error) {
        const errorMsg = (error as Error).message;
        expect(errorMsg).toContain('primary error');
        expect(errorMsg).toContain('recovery error');
      }
    });

    it('should have correct name', () => {
      const primary = createMockAgent('myAgent', 'result');
      const recovery = withRecovery(primary, async () => createMessage('assistant', 'recovered'));

      expect(recovery.name).toBe('myAgent+Recovery');
    });

    it('should include recovery in capabilities', () => {
      const primary = createMockAgent('agent', 'result');
      const recovery = withRecovery(primary, async () => createMessage('assistant', 'recovered'));

      const caps = recovery.capabilities;
      expect(caps).toContain('recovery');
      expect(caps).toContain('error-handling');
    });

    it('should pass message and error to recovery function', async () => {
      let capturedMessage: Message | undefined;
      let capturedError: Error | undefined;

      const primary = createErrorAgent('primary', 'test error');
      const recovery = withRecovery(primary, async (msg, err) => {
        capturedMessage = msg;
        capturedError = err;
        return createMessage('assistant', 'recovered');
      });

      const input = createMessage('user', 'test input');
      await recovery.process(input);

      expect(capturedMessage).toBeDefined();
      expect(String(capturedMessage!.content)).toBe('test input');
      expect(capturedError).toBeDefined();
      expect(capturedError!.message).toContain('test error');
    });
  });

  describe('Default Recovery Strategies', () => {
    describe('Static Message', () => {
      it('should return fixed message', async () => {
        const recovery = DefaultRecovery.staticMessage('Service unavailable');
        const msg = createMessage('user', 'test');
        const err = new Error('fail');

        const result = await recovery(msg, err);

        expect(result.content).toBe('Service unavailable');
      });
    });

    describe('Empty Response', () => {
      it('should return empty message', async () => {
        const msg = createMessage('user', 'test');
        const err = new Error('fail');

        const result = await DefaultRecovery.emptyResponse(msg, err);

        expect(result.content).toBe('');
      });
    });

    describe('Error Response', () => {
      it('should return error details', async () => {
        const msg = createMessage('user', 'test');
        const err = new Error('something broke');

        const result = await DefaultRecovery.errorResponse(msg, err);

        expect(String(result.content)).toContain('An error occurred');
        expect(String(result.content)).toContain('something broke');
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle many fallback agents', async () => {
      const agents = Array.from({ length: 5 }, (_, i) =>
        i < 4 ? createErrorAgent(`agent${i}`, `error${i}`) : createMockAgent(`agent${i}`, 'success'),
      );

      const fallback = new FallbackAgent(agents);

      const input = createMessage('user', 'test');
      const result = await fallback.process(input);

      expect(result.content).toBe('success');
      expect(getMetadata(result, 'fallback_attempts')).toBe(5);
      expect(getMetadata(result, 'fallback_success_index')).toBe(4);
    });

    it('should handle flaky agents that eventually succeed', async () => {
      const flaky = new FlakyAgent('flaky', 'eventual success', 2, 'temporary failure');
      const backup = createMockAgent('backup', 'backup result');

      const fallback = new FallbackAgent([flaky, backup]);

      const input = createMessage('user', 'test');
      const result = await fallback.process(input);

      expect(result.content).toBe('backup result');
      expect(flaky.callCount).toBe(1);
    });

    it('should handle rapid successive calls', async () => {
      const counter = new CallCountingAgent('counter', 'counted');
      const fallback = new FallbackAgent([counter]);

      const input = createMessage('user', 'test');

      await Promise.all([
        fallback.process(input),
        fallback.process(input),
        fallback.process(input),
      ]);

      expect(counter.callCount).toBe(3);
    });

    it('should handle mixed success and failure patterns', async () => {
      const results: string[] = [];

      // First call: agent1 fails, agent2 succeeds
      const agent1a = createErrorAgent('agent1', 'fail');
      const agent2a = createMockAgent('agent2', 'fallback success');
      const fallback1 = new FallbackAgent([agent1a, agent2a]);
      const result1 = await fallback1.process(createMessage('user', 'test'));
      results.push(String(result1.content));

      // Second call: agent1 succeeds immediately
      const agent1b = createMockAgent('agent1', 'primary success');
      const agent2b = createMockAgent('agent2', 'not used');
      const fallback2 = new FallbackAgent([agent1b, agent2b]);
      const result2 = await fallback2.process(createMessage('user', 'test'));
      results.push(String(result2.content));

      expect(results).toEqual(['fallback success', 'primary success']);
    });

    it('should handle single successful agent', async () => {
      const agent = createMockAgent('solo', 'solo success');
      const fallback = new FallbackAgent([agent]);

      const input = createMessage('user', 'test');
      const result = await fallback.process(input);

      expect(result.content).toBe('solo success');
      expect(getMetadata(result, 'fallback_attempts')).toBe(1);
      expect(getMetadata(result, 'fallback_success_index')).toBe(0);
    });

    it('should handle single failing agent', async () => {
      const agent = createErrorAgent('solo', 'solo failure');
      const fallback = new FallbackAgent([agent]);

      const input = createMessage('user', 'test');
      await expect(fallback.process(input)).rejects.toThrow('all 1 agents failed');
    });
  });
});
