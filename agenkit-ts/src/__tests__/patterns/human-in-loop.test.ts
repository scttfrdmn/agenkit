/**
 * Comprehensive tests for Human-in-Loop pattern.
 *
 * Tests cover:
 * - Constructor validation
 * - Confidence-based approval
 * - Approval and rejection flows
 * - Custom approval functions
 * - Error handling
 * - Edge cases
 */

import { describe, it, expect } from 'vitest';
import {
  HumanInLoopAgent,
  ApprovalRequest,
  ApprovalResponse,
  simpleApprovalFunc,
  confidenceBasedApprovalFunc,
} from '../../patterns/human-in-loop';
import { Message, createMessage } from '../../core/interfaces';
import {
  createMockAgent,
  createErrorAgent,
  createConfidenceAgent,
  validateMessage,
  hasMetadata,
  getMetadata,
} from './test-helpers';

describe('HumanInLoopAgent', () => {
  describe('Constructor', () => {
    it('should create agent with valid configuration', () => {
      const agent = createMockAgent('agent', 'result');
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalFunc,
      });

      expect(humanInLoop).toBeDefined();
      expect(humanInLoop.name).toBe('HumanInLoopAgent');
    });

    it('should throw error with null config', () => {
      expect(() => new HumanInLoopAgent(null as any)).toThrow('config is required');
    });

    it('should throw error with undefined config', () => {
      expect(() => new HumanInLoopAgent(undefined as any)).toThrow('config is required');
    });

    it('should throw error with missing agent', () => {
      const approvalFunc = simpleApprovalFunc(true);

      expect(
        () =>
          new HumanInLoopAgent({
            agent: null as any,
            approvalFunc,
          }),
      ).toThrow('agent is required');
    });

    it('should throw error with missing approval function', () => {
      const agent = createMockAgent('agent', 'result');

      expect(
        () =>
          new HumanInLoopAgent({
            agent,
            approvalFunc: null as any,
          }),
      ).toThrow('approval function is required');
    });

    it('should use default threshold if not provided', () => {
      const agent = createMockAgent('agent', 'result');
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalFunc,
      });

      expect(humanInLoop).toBeDefined();
    });

    it('should accept custom threshold', () => {
      const agent = createMockAgent('agent', 'result');
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.7,
        approvalFunc,
      });

      expect(humanInLoop).toBeDefined();
    });

    it('should throw error with invalid threshold below 0', () => {
      const agent = createMockAgent('agent', 'result');
      const approvalFunc = simpleApprovalFunc(true);

      expect(
        () =>
          new HumanInLoopAgent({
            agent,
            approvalThreshold: -0.1,
            approvalFunc,
          }),
      ).toThrow('approval threshold must be between 0 and 1');
    });

    it('should throw error with invalid threshold above 1', () => {
      const agent = createMockAgent('agent', 'result');
      const approvalFunc = simpleApprovalFunc(true);

      expect(
        () =>
          new HumanInLoopAgent({
            agent,
            approvalThreshold: 1.1,
            approvalFunc,
          }),
      ).toThrow('approval threshold must be between 0 and 1');
    });

    it('should accept custom confidence key', () => {
      const agent = createMockAgent('agent', 'result');
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalFunc,
        confidenceKey: 'custom_confidence',
      });

      expect(humanInLoop).toBeDefined();
    });
  });

  describe('Capabilities', () => {
    it('should include human-in-loop capabilities', () => {
      const agent = createMockAgent('agent', 'result');
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalFunc,
      });

      const caps = humanInLoop.capabilities;
      expect(caps).toContain('human-in-loop');
      expect(caps).toContain('approval');
      expect(caps).toContain('oversight');
    });

    it('should combine agent capabilities', () => {
      const agent = createMockAgent('agent', 'result');
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalFunc,
      });

      const caps = humanInLoop.capabilities;
      expect(caps).toContain('mock');
      expect(caps).toContain('human-in-loop');
    });
  });

  describe('Confidence-Based Approval', () => {
    it('should bypass approval for high confidence', async () => {
      const agent = createConfidenceAgent('agent', 'high confidence result', 0.9);
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
      });

      const input = createMessage('user', 'test');
      const result = await humanInLoop.process(input);

      expect(result.content).toBe('high confidence result');
      expect(getMetadata(result, 'approval_needed')).toBe(false);
      expect(getMetadata(result, 'approval_status')).toBe('bypassed');
    });

    it('should request approval for low confidence', async () => {
      const agent = createConfidenceAgent('agent', 'low confidence result', 0.5);
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
      });

      const input = createMessage('user', 'test');
      const result = await humanInLoop.process(input);

      expect(getMetadata(result, 'approval_needed')).toBe(true);
      expect(getMetadata(result, 'approval_status')).toBe('approved');
    });

    it('should use threshold exactly as boundary', async () => {
      const agent = createConfidenceAgent('agent', 'exact threshold', 0.8);
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
      });

      const input = createMessage('user', 'test');
      const result = await humanInLoop.process(input);

      expect(getMetadata(result, 'approval_needed')).toBe(false);
    });

    it('should handle missing confidence as 0', async () => {
      const agent = createMockAgent('agent', 'no confidence');
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
      });

      const input = createMessage('user', 'test');
      const result = await humanInLoop.process(input);

      expect(getMetadata(result, 'confidence')).toBe(0);
      expect(getMetadata(result, 'approval_needed')).toBe(true);
    });

    it('should extract confidence from custom key', async () => {
      const agent = createMockAgent('agent', '');
      agent.process = async () => {
        const msg = createMessage('assistant', 'result');
        msg.metadata = { custom_score: 0.9 };
        return msg;
      };

      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
        confidenceKey: 'custom_score',
      });

      const input = createMessage('user', 'test');
      const result = await humanInLoop.process(input);

      expect(getMetadata(result, 'approval_needed')).toBe(false);
    });
  });

  describe('Approval Flow', () => {
    it('should call approval function with correct request', async () => {
      let capturedRequest: ApprovalRequest | undefined;

      const agent = createConfidenceAgent('agent', 'result', 0.5);
      const approvalFunc = async (request: ApprovalRequest) => {
        capturedRequest = request;
        return { approved: true };
      };

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
      });

      const input = createMessage('user', 'test input');
      await humanInLoop.process(input);

      expect(capturedRequest).toBeDefined();
      expect(capturedRequest!.confidence).toBe(0.5);
      expect(capturedRequest!.message.content).toBe('result');
      expect(capturedRequest!.context).toBeDefined();
      expect(capturedRequest!.timestamp).toBeDefined();
    });

    it('should include context in approval request', async () => {
      let capturedContext: Record<string, unknown> | undefined;

      const agent = createConfidenceAgent('agent', 'result', 0.5);
      const approvalFunc = async (request: ApprovalRequest) => {
        capturedContext = request.context;
        return { approved: true };
      };

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
      });

      const input = createMessage('user', 'test input');
      await humanInLoop.process(input);

      expect(capturedContext).toBeDefined();
      expect(capturedContext!.agent).toBe('agent');
      expect(capturedContext!.approval_threshold).toBe(0.8);
      expect(capturedContext!.original_message).toBe('test input');
      // Floating point comparison - use toBeCloseTo for precision
      expect(Number(capturedContext!.confidence_shortfall)).toBeCloseTo(0.3, 5);
    });

    it('should return original response when approved', async () => {
      const agent = createConfidenceAgent('agent', 'pending result', 0.5);
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
      });

      const input = createMessage('user', 'test');
      const result = await humanInLoop.process(input);

      expect(result.content).toBe('pending result');
      expect(getMetadata(result, 'approval_status')).toBe('approved');
    });

    it('should return modified response when provided', async () => {
      const agent = createConfidenceAgent('agent', 'original', 0.5);
      const approvalFunc = async (request: ApprovalRequest): Promise<ApprovalResponse> => {
        return {
          approved: true,
          modifiedMessage: createMessage('assistant', 'modified by human'),
        };
      };

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
      });

      const input = createMessage('user', 'test');
      const result = await humanInLoop.process(input);

      expect(result.content).toBe('modified by human');
      expect(getMetadata(result, 'approval_status')).toBe('approved_with_modifications');
      expect(getMetadata(result, 'original_response')).toBe('original');
    });

    it('should include feedback in metadata when approved', async () => {
      const agent = createConfidenceAgent('agent', 'result', 0.5);
      const approvalFunc = async (): Promise<ApprovalResponse> => {
        return {
          approved: true,
          feedback: 'Looks good to me',
        };
      };

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
      });

      const input = createMessage('user', 'test');
      const result = await humanInLoop.process(input);

      expect(getMetadata(result, 'approval_feedback')).toBe('Looks good to me');
    });
  });

  describe('Rejection Flow', () => {
    it('should return rejection message when not approved', async () => {
      const agent = createConfidenceAgent('agent', 'unapproved result', 0.5);
      const approvalFunc = simpleApprovalFunc(false);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
      });

      const input = createMessage('user', 'test');
      const result = await humanInLoop.process(input);

      expect(result.content).toBe('Action rejected by human reviewer');
      expect(getMetadata(result, 'approval_status')).toBe('rejected');
    });

    it('should include original response in rejection metadata', async () => {
      const agent = createConfidenceAgent('agent', 'rejected content', 0.5);
      const approvalFunc = simpleApprovalFunc(false);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
      });

      const input = createMessage('user', 'test');
      const result = await humanInLoop.process(input);

      expect(getMetadata(result, 'original_response')).toBe('rejected content');
      expect(getMetadata(result, 'confidence')).toBe(0.5);
    });

    it('should include rejection reason when provided', async () => {
      const agent = createConfidenceAgent('agent', 'result', 0.5);
      const approvalFunc = async (): Promise<ApprovalResponse> => {
        return {
          approved: false,
          feedback: 'Too risky to proceed',
        };
      };

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
      });

      const input = createMessage('user', 'test');
      const result = await humanInLoop.process(input);

      expect(getMetadata(result, 'rejection_reason')).toBe('Too risky to proceed');
    });
  });

  describe('Metadata', () => {
    it('should add approval metadata to all responses', async () => {
      const agent = createConfidenceAgent('agent', 'result', 0.9);
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
      });

      const input = createMessage('user', 'test');
      const result = await humanInLoop.process(input);

      expect(hasMetadata(result, 'approval_needed')).toBe(true);
      expect(hasMetadata(result, 'confidence')).toBe(true);
      expect(hasMetadata(result, 'approval_threshold')).toBe(true);
    });

    it('should record correct confidence values', async () => {
      const agent = createConfidenceAgent('agent', 'result', 0.75);
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
      });

      const input = createMessage('user', 'test');
      const result = await humanInLoop.process(input);

      expect(getMetadata(result, 'confidence')).toBe(0.75);
      expect(getMetadata(result, 'approval_threshold')).toBe(0.8);
    });
  });

  describe('Error Handling', () => {
    it('should throw error with null message', async () => {
      const agent = createMockAgent('agent', 'result');
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalFunc,
      });

      await expect(humanInLoop.process(null as any)).rejects.toThrow('message cannot be nil');
    });

    it('should handle agent execution failure', async () => {
      const agent = createErrorAgent('agent', 'agent error');
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalFunc,
      });

      const input = createMessage('user', 'test');
      await expect(humanInLoop.process(input)).rejects.toThrow('agent execution failed');
    });

    it('should include original error in agent failure', async () => {
      const agent = createErrorAgent('agent', 'custom agent error');
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalFunc,
      });

      const input = createMessage('user', 'test');

      try {
        await humanInLoop.process(input);
        expect.fail('Should have thrown error');
      } catch (error) {
        const errorMsg = (error as Error).message;
        expect(errorMsg).toContain('custom agent error');
      }
    });

    it('should handle approval function failure', async () => {
      const agent = createConfidenceAgent('agent', 'result', 0.5);
      const approvalFunc = async (): Promise<ApprovalResponse> => {
        throw new Error('approval system down');
      };

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
      });

      const input = createMessage('user', 'test');
      await expect(humanInLoop.process(input)).rejects.toThrow('approval request failed');
    });

    it('should include approval error details', async () => {
      const agent = createConfidenceAgent('agent', 'result', 0.5);
      const approvalFunc = async (): Promise<ApprovalResponse> => {
        throw new Error('network timeout');
      };

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
      });

      const input = createMessage('user', 'test');

      try {
        await humanInLoop.process(input);
        expect.fail('Should have thrown error');
      } catch (error) {
        const errorMsg = (error as Error).message;
        expect(errorMsg).toContain('network timeout');
      }
    });
  });

  describe('Simple Approval Function', () => {
    it('should auto-approve when configured', async () => {
      const func = simpleApprovalFunc(true);
      const request: ApprovalRequest = {
        message: createMessage('assistant', 'test'),
        confidence: 0.5,
        context: {},
        timestamp: new Date().toISOString(),
      };

      const response = await func(request);

      expect(response.approved).toBe(true);
      expect(response.feedback).toContain('Auto-approved');
    });

    it('should auto-reject when configured', async () => {
      const func = simpleApprovalFunc(false);
      const request: ApprovalRequest = {
        message: createMessage('assistant', 'test'),
        confidence: 0.5,
        context: {},
        timestamp: new Date().toISOString(),
      };

      const response = await func(request);

      expect(response.approved).toBe(false);
      expect(response.feedback).toContain('Auto-rejected');
    });

    it('should include confidence in feedback', async () => {
      const func = simpleApprovalFunc(true);
      const request: ApprovalRequest = {
        message: createMessage('assistant', 'test'),
        confidence: 0.73,
        context: {},
        timestamp: new Date().toISOString(),
      };

      const response = await func(request);

      expect(response.feedback).toContain('0.73');
    });
  });

  describe('Confidence-Based Approval Function', () => {
    it('should auto-reject below threshold', async () => {
      const func = confidenceBasedApprovalFunc(0.3, 0.9);
      const request: ApprovalRequest = {
        message: createMessage('assistant', 'test'),
        confidence: 0.2,
        context: {},
        timestamp: new Date().toISOString(),
      };

      const response = await func(request);

      expect(response.approved).toBe(false);
      expect(response.feedback).toContain('too low');
    });

    it('should auto-approve above threshold', async () => {
      const func = confidenceBasedApprovalFunc(0.3, 0.9);
      const request: ApprovalRequest = {
        message: createMessage('assistant', 'test'),
        confidence: 0.95,
        context: {},
        timestamp: new Date().toISOString(),
      };

      const response = await func(request);

      expect(response.approved).toBe(true);
      expect(response.feedback).toContain('Auto-approved');
    });

    it('should require manual approval in middle range', async () => {
      const func = confidenceBasedApprovalFunc(0.3, 0.9);
      const request: ApprovalRequest = {
        message: createMessage('assistant', 'test'),
        confidence: 0.6,
        context: {},
        timestamp: new Date().toISOString(),
      };

      const response = await func(request);

      expect(response.approved).toBe(false);
      expect(response.feedback).toContain('Manual approval required');
    });
  });

  describe('Edge Cases', () => {
    it('should handle confidence exactly at 0', async () => {
      const agent = createConfidenceAgent('agent', 'result', 0.0);
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
      });

      const input = createMessage('user', 'test');
      const result = await humanInLoop.process(input);

      expect(getMetadata(result, 'confidence')).toBe(0);
      expect(getMetadata(result, 'approval_needed')).toBe(true);
    });

    it('should handle confidence exactly at 1', async () => {
      const agent = createConfidenceAgent('agent', 'result', 1.0);
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0.8,
        approvalFunc,
      });

      const input = createMessage('user', 'test');
      const result = await humanInLoop.process(input);

      expect(getMetadata(result, 'confidence')).toBe(1);
      expect(getMetadata(result, 'approval_needed')).toBe(false);
    });

    it('should handle threshold at 0', async () => {
      const agent = createConfidenceAgent('agent', 'result', 0.5);
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 0,
        approvalFunc,
      });

      const input = createMessage('user', 'test');
      const result = await humanInLoop.process(input);

      expect(getMetadata(result, 'approval_needed')).toBe(false);
    });

    it('should handle threshold at 1', async () => {
      const agent = createConfidenceAgent('agent', 'result', 0.99);
      const approvalFunc = simpleApprovalFunc(true);

      const humanInLoop = new HumanInLoopAgent({
        agent,
        approvalThreshold: 1,
        approvalFunc,
      });

      const input = createMessage('user', 'test');
      const result = await humanInLoop.process(input);

      expect(getMetadata(result, 'approval_needed')).toBe(true);
    });
  });
});
