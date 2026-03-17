/**
 * Comprehensive tests for MultiAgentOrchestrator and ConsensusAgent patterns.
 *
 * Tests cover:
 * - Agent registration and management
 * - Sequential orchestration
 * - Task tracking
 * - ConsensusAgent voting strategies
 * - Error handling
 */

import { describe, it, expect } from 'vitest';
import {
  MultiAgentOrchestrator,
  ConsensusAgent,
  type OrchestrationStrategy,
} from '../../patterns/multiagent';
import { createMessage } from '../../core/interfaces';
import { createMockAgent, createErrorAgent, validateMessage } from './test-helpers';

describe('MultiAgentOrchestrator', () => {
  describe('Constructor', () => {
    it('should create orchestrator with default sequential strategy', () => {
      const orchestrator = new MultiAgentOrchestrator();

      expect(orchestrator.name).toBe('MultiAgentOrchestrator');
      expect(orchestrator.strategy).toBe('sequential');
    });

    it('should accept custom strategy', () => {
      const orchestrator = new MultiAgentOrchestrator('parallel');

      expect(orchestrator.strategy).toBe('parallel');
    });

    it('should start with empty agent registry', () => {
      const orchestrator = new MultiAgentOrchestrator();

      expect(orchestrator.listAgents()).toHaveLength(0);
    });
  });

  describe('registerAgent', () => {
    it('should register an agent', () => {
      const orchestrator = new MultiAgentOrchestrator();
      const agent = createMockAgent('researcher', 'research result');

      orchestrator.registerAgent('researcher', agent);

      expect(orchestrator.listAgents()).toContain('researcher');
    });

    it('should register multiple agents', () => {
      const orchestrator = new MultiAgentOrchestrator();

      orchestrator.registerAgent('a1', createMockAgent('a1', 'r1'));
      orchestrator.registerAgent('a2', createMockAgent('a2', 'r2'));
      orchestrator.registerAgent('a3', createMockAgent('a3', 'r3'));

      expect(orchestrator.listAgents()).toHaveLength(3);
    });

    it('should overwrite agent with same name', () => {
      const orchestrator = new MultiAgentOrchestrator();

      orchestrator.registerAgent('agent', createMockAgent('v1', 'result1'));
      orchestrator.registerAgent('agent', createMockAgent('v2', 'result2'));

      expect(orchestrator.listAgents()).toHaveLength(1);
    });
  });

  describe('unregisterAgent', () => {
    it('should remove a registered agent', () => {
      const orchestrator = new MultiAgentOrchestrator();
      orchestrator.registerAgent('agent', createMockAgent('a', 'r'));

      orchestrator.unregisterAgent('agent');

      expect(orchestrator.listAgents()).toHaveLength(0);
    });

    it('should be idempotent for missing agents', () => {
      const orchestrator = new MultiAgentOrchestrator();

      // Should not throw
      orchestrator.unregisterAgent('nonexistent');

      expect(orchestrator.listAgents()).toHaveLength(0);
    });
  });

  describe('listAgents', () => {
    it('should return names of all registered agents', () => {
      const orchestrator = new MultiAgentOrchestrator();
      orchestrator.registerAgent('researcher', createMockAgent('r', 'r'));
      orchestrator.registerAgent('writer', createMockAgent('w', 'w'));

      const names = orchestrator.listAgents();
      expect(names).toContain('researcher');
      expect(names).toContain('writer');
    });
  });

  describe('process', () => {
    it('should process message through all registered agents', async () => {
      const orchestrator = new MultiAgentOrchestrator();
      orchestrator.registerAgent('agent1', createMockAgent('a1', 'result from agent1'));
      orchestrator.registerAgent('agent2', createMockAgent('a2', 'result from agent2'));

      const result = await orchestrator.process(createMessage('user', 'Test message'));

      validateMessage(result);
      expect(String(result.content)).toContain('result from agent1');
      expect(String(result.content)).toContain('result from agent2');
    });

    it('should return empty result when no agents registered', async () => {
      const orchestrator = new MultiAgentOrchestrator();

      const result = await orchestrator.process(createMessage('user', 'Test'));

      validateMessage(result);
    });

    it('should handle agent errors gracefully', async () => {
      const orchestrator = new MultiAgentOrchestrator();
      orchestrator.registerAgent('good', createMockAgent('good', 'success'));
      orchestrator.registerAgent('bad', createErrorAgent('bad', 'agent crashed'));

      const result = await orchestrator.process(createMessage('user', 'Test'));

      // Should still return a result, with error info
      validateMessage(result);
      expect(String(result.content)).toContain('Failed');
    });

    it('should format combined result with agent names', async () => {
      const orchestrator = new MultiAgentOrchestrator();
      orchestrator.registerAgent('alice', createMockAgent('alice', 'Alice says hi'));

      const result = await orchestrator.process(createMessage('user', 'Hello'));

      expect(String(result.content)).toContain('alice');
    });
  });

  describe('getTasks', () => {
    it('should return empty tasks before processing', () => {
      const orchestrator = new MultiAgentOrchestrator();

      expect(orchestrator.getTasks()).toHaveLength(0);
    });

    it('should return tasks after processing', async () => {
      const orchestrator = new MultiAgentOrchestrator();
      orchestrator.registerAgent('agent1', createMockAgent('a1', 'r1'));
      orchestrator.registerAgent('agent2', createMockAgent('a2', 'r2'));

      await orchestrator.process(createMessage('user', 'Test'));

      const tasks = orchestrator.getTasks();
      expect(tasks).toHaveLength(2);
    });

    it('should mark completed tasks as completed', async () => {
      const orchestrator = new MultiAgentOrchestrator();
      orchestrator.registerAgent('agent', createMockAgent('a', 'result'));

      await orchestrator.process(createMessage('user', 'Test'));

      const tasks = orchestrator.getTasks();
      expect(tasks[0].status).toBe('completed');
    });

    it('should mark failed tasks as failed', async () => {
      const orchestrator = new MultiAgentOrchestrator();
      orchestrator.registerAgent('bad', createErrorAgent('bad', 'error'));

      await orchestrator.process(createMessage('user', 'Test'));

      const tasks = orchestrator.getTasks();
      expect(tasks[0].status).toBe('failed');
    });

    it('should return copy of tasks (not internal reference)', async () => {
      const orchestrator = new MultiAgentOrchestrator();
      orchestrator.registerAgent('agent', createMockAgent('a', 'r'));

      await orchestrator.process(createMessage('user', 'Test'));

      const tasks1 = orchestrator.getTasks();
      const tasks2 = orchestrator.getTasks();

      expect(tasks1).not.toBe(tasks2);
      expect(tasks1).toEqual(tasks2);
    });
  });
});

describe('ConsensusAgent', () => {
  describe('Constructor', () => {
    it('should create with default majority strategy', () => {
      const consensus = new ConsensusAgent();

      expect(consensus.name).toBe('ConsensusAgent');
      expect(consensus.votingStrategy).toBe('majority');
    });

    it('should accept unanimous strategy', () => {
      const consensus = new ConsensusAgent('unanimous');

      expect(consensus.votingStrategy).toBe('unanimous');
    });

    it('should accept weighted strategy', () => {
      const consensus = new ConsensusAgent('weighted');

      expect(consensus.votingStrategy).toBe('weighted');
    });

    it('should start with empty agents list', () => {
      const consensus = new ConsensusAgent();

      expect(consensus.agents).toHaveLength(0);
    });
  });

  describe('addAgent', () => {
    it('should add agents to the consensus group', () => {
      const consensus = new ConsensusAgent();
      consensus.addAgent(createMockAgent('a1', 'r1'));
      consensus.addAgent(createMockAgent('a2', 'r2'));

      expect(consensus.agents).toHaveLength(2);
    });
  });

  describe('process', () => {
    it('should combine responses from all agents', async () => {
      const consensus = new ConsensusAgent();
      consensus.addAgent(createMockAgent('conservative', 'Option A'));
      consensus.addAgent(createMockAgent('creative', 'Option B'));
      consensus.addAgent(createMockAgent('analytical', 'Option C'));

      const result = await consensus.process(createMessage('user', 'What should we do?'));

      validateMessage(result);
      expect(String(result.content)).toContain('Option A');
      expect(String(result.content)).toContain('Option B');
      expect(String(result.content)).toContain('Option C');
    });

    it('should mention agent count in result', async () => {
      const consensus = new ConsensusAgent();
      consensus.addAgent(createMockAgent('a1', 'view1'));
      consensus.addAgent(createMockAgent('a2', 'view2'));

      const result = await consensus.process(createMessage('user', 'Question'));

      expect(String(result.content)).toContain('2');
    });

    it('should return valid message with no agents', async () => {
      const consensus = new ConsensusAgent();

      const result = await consensus.process(createMessage('user', 'Question'));

      validateMessage(result);
    });
  });
});
