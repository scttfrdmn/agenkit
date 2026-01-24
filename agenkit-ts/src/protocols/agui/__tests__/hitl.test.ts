/**
 * Comprehensive tests for AG-UI Human-in-Loop adapter.
 *
 * Tests cover:
 * - HITL adapter construction
 * - Interrupt event emission
 * - Approval workflows
 * - Confidence-based triggering
 * - Integration with HumanInLoopAgent
 */

import { describe, it, expect, vi } from 'vitest';
import { Agent, Message } from '../../../core/interfaces';
import { HumanInLoopAgent, ApprovalRequest, ApprovalResponse } from '../../../patterns/human-in-loop';
import {
  AGUIHumanInLoopAdapter,
  Interrupt,
  TextMessageComplete,
  MetadataEvent,
} from '../index';

// Mock agent for testing
class ConfidenceAgent implements Agent {
  readonly name = 'ConfidenceAgent';
  readonly capabilities = ['test'];

  constructor(private confidence: number) {}

  async process(message: Message): Promise<Message> {
    return {
      role: 'assistant',
      content: 'Response',
      metadata: {
        confidence: this.confidence,
      },
      timestamp: new Date().toISOString(),
    };
  }
}

describe('AGUIHumanInLoopAdapter', () => {
  describe('Constructor', () => {
    it('should create adapter with HumanInLoopAgent', async () => {
      const agent = new ConfidenceAgent(0.9);
      const approvalFunc = async (_req: ApprovalRequest): Promise<ApprovalResponse> => ({
        approved: true,
      });

      const hilAgent = new HumanInLoopAgent({
        agent,
        approvalFunc,
        approvalThreshold: 0.8,
      });

      const adapter = new AGUIHumanInLoopAdapter(hilAgent);
      expect(adapter).toBeDefined();
    });

    it('should create adapter with regular agent', () => {
      const agent = new ConfidenceAgent(0.9);
      const adapter = new AGUIHumanInLoopAdapter(agent as any);

      expect(adapter).toBeDefined();
    });

    it('should accept custom configuration', () => {
      const agent = new ConfidenceAgent(0.9);
      const adapter = new AGUIHumanInLoopAdapter(agent as any, {
        agentName: 'CustomHITL',
        emitInterrupts: false,
      });

      expect(adapter).toBeDefined();
    });
  });

  describe('Interrupt emission', () => {
    it('should emit interrupt when approval is requested', async () => {
      const agent = new ConfidenceAgent(0.6); // Below threshold
      const approvalFunc = async (_req: ApprovalRequest): Promise<ApprovalResponse> => ({
        approved: true,
        feedback: 'Approved by manager',
      });

      const hilAgent = new HumanInLoopAgent({
        agent,
        approvalFunc,
        approvalThreshold: 0.8,
      });

      const adapter = new AGUIHumanInLoopAdapter(hilAgent, {
        emitInterrupts: true,
      });

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        events.push(event);
      }

      const interrupt = events.find((e) => e instanceof Interrupt);
      expect(interrupt).toBeDefined();
    });

    it('should not emit interrupt when confidence is above threshold', async () => {
      const agent = new ConfidenceAgent(0.95); // Above threshold
      const approvalFunc = async (_req: ApprovalRequest): Promise<ApprovalResponse> => ({
        approved: true,
      });

      const hilAgent = new HumanInLoopAgent({
        agent,
        approvalFunc,
        approvalThreshold: 0.8,
      });

      const adapter = new AGUIHumanInLoopAdapter(hilAgent, {
        emitInterrupts: true,
      });

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        events.push(event);
      }

      const interrupt = events.find((e) => e instanceof Interrupt);
      expect(interrupt).toBeUndefined();
    });

    it('should not emit interrupt when emitInterrupts is false', async () => {
      const agent = new ConfidenceAgent(0.6);
      const approvalFunc = async (_req: ApprovalRequest): Promise<ApprovalResponse> => ({
        approved: true,
      });

      const hilAgent = new HumanInLoopAgent({
        agent,
        approvalFunc,
        approvalThreshold: 0.8,
      });

      const adapter = new AGUIHumanInLoopAdapter(hilAgent, {
        emitInterrupts: false,
      });

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        events.push(event);
      }

      const interrupt = events.find((e) => e instanceof Interrupt);
      expect(interrupt).toBeUndefined();
    });
  });

  describe('Interrupt details', () => {
    it('should include confidence in interrupt context', async () => {
      const agent = new ConfidenceAgent(0.6);
      const approvalFunc = async (_req: ApprovalRequest): Promise<ApprovalResponse> => ({
        approved: true,
      });

      const hilAgent = new HumanInLoopAgent({
        agent,
        approvalFunc,
        approvalThreshold: 0.8,
      });

      const adapter = new AGUIHumanInLoopAdapter(hilAgent, {
        emitInterrupts: true,
      });

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        if (event instanceof Interrupt) {
          events.push(event);
        }
      }

      const interrupt = events[0] as Interrupt;
      expect(interrupt.context).toHaveProperty('confidence');
      expect(interrupt.context?.confidence).toBe(0.6);
    });

    it('should include approval threshold in interrupt context', async () => {
      const agent = new ConfidenceAgent(0.6);
      const approvalFunc = async (_req: ApprovalRequest): Promise<ApprovalResponse> => ({
        approved: true,
      });

      const hilAgent = new HumanInLoopAgent({
        agent,
        approvalFunc,
        approvalThreshold: 0.8,
      });

      const adapter = new AGUIHumanInLoopAdapter(hilAgent, {
        emitInterrupts: true,
      });

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        if (event instanceof Interrupt) {
          events.push(event);
        }
      }

      const interrupt = events[0] as Interrupt;
      expect(interrupt.context).toHaveProperty('approval_threshold');
      expect(interrupt.context?.approval_threshold).toBe(0.8);
    });

    it('should include approval status in interrupt context', async () => {
      const agent = new ConfidenceAgent(0.6);
      const approvalFunc = async (_req: ApprovalRequest): Promise<ApprovalResponse> => ({
        approved: true,
        feedback: 'Looks good',
      });

      const hilAgent = new HumanInLoopAgent({
        agent,
        approvalFunc,
        approvalThreshold: 0.8,
      });

      const adapter = new AGUIHumanInLoopAdapter(hilAgent, {
        emitInterrupts: true,
      });

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        if (event instanceof Interrupt) {
          events.push(event);
        }
      }

      const interrupt = events[0] as Interrupt;
      expect(interrupt.context).toHaveProperty('approval_status');
    });
  });

  describe('Metadata event', () => {
    it('should include HITL metadata when using HumanInLoopAgent', async () => {
      const agent = new ConfidenceAgent(0.9);
      const approvalFunc = async (_req: ApprovalRequest): Promise<ApprovalResponse> => ({
        approved: true,
      });

      const hilAgent = new HumanInLoopAgent({
        agent,
        approvalFunc,
        approvalThreshold: 0.8,
      });

      const adapter = new AGUIHumanInLoopAdapter(hilAgent, {
        emitInterrupts: true,
      });

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, true)) {
        if (event instanceof MetadataEvent) {
          events.push(event);
        }
      }

      const metadata = events[0] as MetadataEvent;
      expect(metadata.data.capabilities).toHaveProperty('interrupts', true);
    });
  });

  describe('Regular agent behavior', () => {
    it('should work with non-HITL agent', async () => {
      const agent = new ConfidenceAgent(0.9);
      const adapter = new AGUIHumanInLoopAdapter(agent as any, {
        emitInterrupts: true,
      });

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        events.push(event);
      }

      const complete = events.find((e) => e instanceof TextMessageComplete);
      expect(complete).toBeDefined();
    });

    it('should not emit interrupts for non-HITL agent', async () => {
      const agent = new ConfidenceAgent(0.6);
      const adapter = new AGUIHumanInLoopAdapter(agent as any, {
        emitInterrupts: true,
      });

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        events.push(event);
      }

      const interrupt = events.find((e) => e instanceof Interrupt);
      expect(interrupt).toBeUndefined();
    });
  });

  describe('Approval workflow', () => {
    it('should call approval function when confidence is low', async () => {
      const agent = new ConfidenceAgent(0.6);
      const approvalFunc = vi.fn(async (_req: ApprovalRequest): Promise<ApprovalResponse> => ({
        approved: true,
      }));

      const hilAgent = new HumanInLoopAgent({
        agent,
        approvalFunc,
        approvalThreshold: 0.8,
      });

      const adapter = new AGUIHumanInLoopAdapter(hilAgent, {
        emitInterrupts: true,
      });

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        events.push(event);
      }

      expect(approvalFunc).toHaveBeenCalled();
    });

    it('should not call approval function when confidence is high', async () => {
      const agent = new ConfidenceAgent(0.95);
      const approvalFunc = vi.fn(async (_req: ApprovalRequest): Promise<ApprovalResponse> => ({
        approved: true,
      }));

      const hilAgent = new HumanInLoopAgent({
        agent,
        approvalFunc,
        approvalThreshold: 0.8,
      });

      const adapter = new AGUIHumanInLoopAdapter(hilAgent, {
        emitInterrupts: true,
      });

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        events.push(event);
      }

      expect(approvalFunc).not.toHaveBeenCalled();
    });

    it('should stream response after approval', async () => {
      const agent = new ConfidenceAgent(0.6);
      const approvalFunc = async (_req: ApprovalRequest): Promise<ApprovalResponse> => ({
        approved: true,
        feedback: 'Approved',
      });

      const hilAgent = new HumanInLoopAgent({
        agent,
        approvalFunc,
        approvalThreshold: 0.8,
      });

      const adapter = new AGUIHumanInLoopAdapter(hilAgent, {
        emitInterrupts: true,
      });

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        events.push(event);
      }

      const complete = events.find((e) => e instanceof TextMessageComplete);
      expect(complete).toBeDefined();
      expect((complete as TextMessageComplete).content).toBe('Response');
    });
  });

  describe('Edge cases', () => {
    it('should handle missing confidence metadata', async () => {
      class NoConfidenceAgent implements Agent {
        readonly name = 'NoConfidenceAgent';

        async process(_message: Message): Promise<Message> {
          return {
            role: 'assistant',
            content: 'Response',
            metadata: {},
            timestamp: new Date().toISOString(),
          };
        }
      }

      const agent = new NoConfidenceAgent();
      const approvalFunc = async (_req: ApprovalRequest): Promise<ApprovalResponse> => ({
        approved: true,
      });

      const hilAgent = new HumanInLoopAgent({
        agent,
        approvalFunc,
        approvalThreshold: 0.8,
      });

      const adapter = new AGUIHumanInLoopAdapter(hilAgent, {
        emitInterrupts: true,
      });

      const message: Message = {
        role: 'user',
        content: 'test',
        timestamp: new Date().toISOString(),
      };

      const events = [];
      for await (const event of adapter.streamEvents(message, undefined, false)) {
        events.push(event);
      }

      // Should complete without errors
      const complete = events.find((e) => e instanceof TextMessageComplete);
      expect(complete).toBeDefined();
    });
  });
});
