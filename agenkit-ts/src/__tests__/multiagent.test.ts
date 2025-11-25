/**
 * Tests for Multi-Agent Collaboration patterns.
 */

import {
  MultiAgentOrchestrator,
  ConsensusAgent,
  AgentTask,
  TaskStatus,
} from '../patterns/multiagent';
import { Agent, Message, createMessage } from '../core/interfaces';

// ============================================================================
// Mock Agents
// ============================================================================

/**
 * Mock agent for testing.
 */
class MockAgent implements Agent {
  readonly name: string;
  private response: string;
  public callCount: number;
  public lastMessage?: Message;

  constructor(name: string, response: string = 'Mock response') {
    this.name = name;
    this.response = response;
    this.callCount = 0;
  }

  async process(message: Message): Promise<Message> {
    this.callCount++;
    this.lastMessage = message;
    return createMessage('assistant', this.response);
  }
}

/**
 * Agent that always fails.
 */
class FailingAgent implements Agent {
  readonly name = 'FailingAgent';

  async process(message: Message): Promise<Message> {
    throw new Error('Simulated failure');
  }
}

// ============================================================================
// AgentTask Tests
// ============================================================================

describe('AgentTask', () => {
  it('should have correct structure', () => {
    const task: AgentTask = {
      agentName: 'test_agent',
      description: 'Test task',
      status: 'pending',
    };

    expect(task.agentName).toBe('test_agent');
    expect(task.description).toBe('Test task');
    expect(task.status).toBe('pending');
    expect(task.result).toBeUndefined();
    expect(task.error).toBeUndefined();
  });

  it('should support result field', () => {
    const task: AgentTask = {
      agentName: 'test_agent',
      description: 'Test task',
      result: 'Task result',
      status: 'completed',
    };

    expect(task.result).toBe('Task result');
    expect(task.status).toBe('completed');
  });

  it('should support error field', () => {
    const task: AgentTask = {
      agentName: 'test_agent',
      description: 'Test task',
      error: 'Error message',
      status: 'failed',
    };

    expect(task.error).toBe('Error message');
    expect(task.status).toBe('failed');
  });
});

// ============================================================================
// MultiAgentOrchestrator Tests
// ============================================================================

describe('MultiAgentOrchestrator', () => {
  describe('Configuration', () => {
    it('should create with default configuration', () => {
      const orchestrator = new MultiAgentOrchestrator();

      expect(orchestrator.name).toBe('MultiAgentOrchestrator');
      expect(orchestrator.strategy).toBe('sequential');
      expect(orchestrator.listAgents()).toHaveLength(0);
      expect(orchestrator.getTasks()).toHaveLength(0);
    });

    it('should create with custom strategy', () => {
      const orchestrator = new MultiAgentOrchestrator('parallel');

      expect(orchestrator.strategy).toBe('parallel');
    });

    it('should support sequential strategy', () => {
      const orchestrator = new MultiAgentOrchestrator('sequential');

      expect(orchestrator.strategy).toBe('sequential');
    });

    it('should support delegate strategy', () => {
      const orchestrator = new MultiAgentOrchestrator('delegate');

      expect(orchestrator.strategy).toBe('delegate');
    });
  });

  describe('Agent Registration', () => {
    it('should register an agent', () => {
      const orchestrator = new MultiAgentOrchestrator();
      const agent = new MockAgent('test_agent');

      orchestrator.registerAgent('test', agent);

      const agents = orchestrator.listAgents();
      expect(agents).toContain('test');
      expect(agents).toHaveLength(1);
    });

    it('should register multiple agents', () => {
      const orchestrator = new MultiAgentOrchestrator();
      const agent1 = new MockAgent('agent1');
      const agent2 = new MockAgent('agent2');

      orchestrator.registerAgent('first', agent1);
      orchestrator.registerAgent('second', agent2);

      const agents = orchestrator.listAgents();
      expect(agents).toHaveLength(2);
      expect(agents).toContain('first');
      expect(agents).toContain('second');
    });

    it('should unregister an agent', () => {
      const orchestrator = new MultiAgentOrchestrator();
      const agent = new MockAgent('test_agent');

      orchestrator.registerAgent('test', agent);
      expect(orchestrator.listAgents()).toContain('test');

      orchestrator.unregisterAgent('test');
      expect(orchestrator.listAgents()).not.toContain('test');
    });

    it('should handle unregistering nonexistent agent', () => {
      const orchestrator = new MultiAgentOrchestrator();

      // Should not throw
      expect(() => orchestrator.unregisterAgent('nonexistent')).not.toThrow();
    });

    it('should allow re-registering with same name', () => {
      const orchestrator = new MultiAgentOrchestrator();
      const agent1 = new MockAgent('agent1', 'Response 1');
      const agent2 = new MockAgent('agent2', 'Response 2');

      orchestrator.registerAgent('test', agent1);
      orchestrator.registerAgent('test', agent2); // Overwrite

      expect(orchestrator.listAgents()).toHaveLength(1);
    });
  });

  describe('Processing', () => {
    it('should process with single agent', async () => {
      const orchestrator = new MultiAgentOrchestrator();
      const agent = new MockAgent('test_agent', 'Agent response');

      orchestrator.registerAgent('test', agent);

      const result = await orchestrator.process(createMessage('user', 'Test message'));

      expect(result.content).toContain('Agent response');
      expect(agent.callCount).toBe(1);
      expect(agent.lastMessage?.content).toBe('Test message');
    });

    it('should process with multiple agents', async () => {
      const orchestrator = new MultiAgentOrchestrator();
      const agent1 = new MockAgent('agent1', 'Response 1');
      const agent2 = new MockAgent('agent2', 'Response 2');

      orchestrator.registerAgent('first', agent1);
      orchestrator.registerAgent('second', agent2);

      const result = await orchestrator.process(createMessage('user', 'Test'));

      expect(result.content).toContain('Response 1');
      expect(result.content).toContain('Response 2');
      expect(agent1.callCount).toBe(1);
      expect(agent2.callCount).toBe(1);
    });

    it('should handle empty agent list', async () => {
      const orchestrator = new MultiAgentOrchestrator();

      const result = await orchestrator.process(createMessage('user', 'Test'));

      expect(result.content).toBe('');
      expect(orchestrator.getTasks()).toHaveLength(0);
    });

    it('should format agent responses with names', async () => {
      const orchestrator = new MultiAgentOrchestrator();
      const agent1 = new MockAgent('agent1', 'Response 1');
      const agent2 = new MockAgent('agent2', 'Response 2');

      orchestrator.registerAgent('first', agent1);
      orchestrator.registerAgent('second', agent2);

      const result = await orchestrator.process(createMessage('user', 'Test'));

      expect(result.content).toContain('first:');
      expect(result.content).toContain('second:');
    });
  });

  describe('Task Tracking', () => {
    it('should track tasks', async () => {
      const orchestrator = new MultiAgentOrchestrator();
      const agent = new MockAgent('test_agent');

      orchestrator.registerAgent('test', agent);

      await orchestrator.process(createMessage('user', 'Task 1'));
      await orchestrator.process(createMessage('user', 'Task 2'));

      const tasks = orchestrator.getTasks();
      expect(tasks).toHaveLength(2);
      expect(tasks[0].description).toBe('Task 1');
      expect(tasks[1].description).toBe('Task 2');
    });

    it('should mark completed tasks correctly', async () => {
      const orchestrator = new MultiAgentOrchestrator();
      const agent = new MockAgent('test_agent', 'Success');

      orchestrator.registerAgent('test', agent);

      await orchestrator.process(createMessage('user', 'Test'));

      const tasks = orchestrator.getTasks();
      expect(tasks).toHaveLength(1);
      expect(tasks[0].status).toBe('completed');
      expect(tasks[0].result).toBe('Success');
      expect(tasks[0].error).toBeUndefined();
    });

    it('should return copy of tasks', () => {
      const orchestrator = new MultiAgentOrchestrator();
      const task: AgentTask = {
        agentName: 'test',
        description: 'Test',
        status: 'pending',
      };
      // Access private field for testing
      (orchestrator as any)._tasks.push(task);

      const tasks = orchestrator.getTasks();
      tasks.push({
        agentName: 'other',
        description: 'Other',
        status: 'pending',
      });

      // Original should be unchanged
      expect((orchestrator as any)._tasks).toHaveLength(1);
    });
  });

  describe('Error Handling', () => {
    it('should handle agent failure', async () => {
      const orchestrator = new MultiAgentOrchestrator();
      const failingAgent = new FailingAgent();
      const goodAgent = new MockAgent('good_agent', 'Success');

      orchestrator.registerAgent('failing', failingAgent);
      orchestrator.registerAgent('good', goodAgent);

      const result = await orchestrator.process(createMessage('user', 'Test'));

      // Both agents should have run
      expect(result.content).toContain('Failed');
      expect(result.content).toContain('Success');
    });

    it('should track failed task status', async () => {
      const orchestrator = new MultiAgentOrchestrator();
      const failingAgent = new FailingAgent();
      const goodAgent = new MockAgent('good_agent', 'Success');

      orchestrator.registerAgent('failing', failingAgent);
      orchestrator.registerAgent('good', goodAgent);

      await orchestrator.process(createMessage('user', 'Test'));

      const tasks = orchestrator.getTasks();
      expect(tasks).toHaveLength(2);

      const failedTasks = tasks.filter(t => t.status === 'failed');
      const completedTasks = tasks.filter(t => t.status === 'completed');

      expect(failedTasks).toHaveLength(1);
      expect(completedTasks).toHaveLength(1);
      expect(failedTasks[0].error).toContain('Simulated failure');
    });

    it('should continue processing after failure', async () => {
      const orchestrator = new MultiAgentOrchestrator();
      const failingAgent = new FailingAgent();
      const agent1 = new MockAgent('agent1', 'Before failure');
      const agent2 = new MockAgent('agent2', 'After failure');

      orchestrator.registerAgent('agent1', agent1);
      orchestrator.registerAgent('failing', failingAgent);
      orchestrator.registerAgent('agent2', agent2);

      const result = await orchestrator.process(createMessage('user', 'Test'));

      expect(result.content).toContain('Before failure');
      expect(result.content).toContain('Failed');
      expect(result.content).toContain('After failure');
      expect(agent1.callCount).toBe(1);
      expect(agent2.callCount).toBe(1);
    });
  });
});

// ============================================================================
// ConsensusAgent Tests
// ============================================================================

describe('ConsensusAgent', () => {
  describe('Configuration', () => {
    it('should create with default configuration', () => {
      const consensus = new ConsensusAgent();

      expect(consensus.name).toBe('ConsensusAgent');
      expect(consensus.votingStrategy).toBe('majority');
      expect(consensus.agents).toHaveLength(0);
    });

    it('should create with custom voting strategy', () => {
      const consensus = new ConsensusAgent('unanimous');

      expect(consensus.votingStrategy).toBe('unanimous');
    });

    it('should support weighted strategy', () => {
      const consensus = new ConsensusAgent('weighted');

      expect(consensus.votingStrategy).toBe('weighted');
    });
  });

  describe('Agent Management', () => {
    it('should add an agent', () => {
      const consensus = new ConsensusAgent();
      const agent = new MockAgent('test_agent');

      consensus.addAgent(agent);

      expect(consensus.agents).toHaveLength(1);
      expect(consensus.agents[0]).toBe(agent);
    });

    it('should add multiple agents', () => {
      const consensus = new ConsensusAgent();
      const agent1 = new MockAgent('agent1');
      const agent2 = new MockAgent('agent2');
      const agent3 = new MockAgent('agent3');

      consensus.addAgent(agent1);
      consensus.addAgent(agent2);
      consensus.addAgent(agent3);

      expect(consensus.agents).toHaveLength(3);
    });
  });

  describe('Processing', () => {
    it('should process with single agent', async () => {
      const consensus = new ConsensusAgent();
      const agent = new MockAgent('test_agent', 'Single response');

      consensus.addAgent(agent);

      const result = await consensus.process(createMessage('user', 'Test'));

      expect(result.content).toContain('Consensus from 1 agents');
      expect(result.content).toContain('Single response');
    });

    it('should process with multiple agents', async () => {
      const consensus = new ConsensusAgent();
      const agent1 = new MockAgent('agent1', 'Response 1');
      const agent2 = new MockAgent('agent2', 'Response 2');
      const agent3 = new MockAgent('agent3', 'Response 3');

      consensus.addAgent(agent1);
      consensus.addAgent(agent2);
      consensus.addAgent(agent3);

      const result = await consensus.process(createMessage('user', 'Test'));

      expect(result.content).toContain('Consensus from 3 agents');
      expect(result.content).toContain('Response 1');
      expect(result.content).toContain('Response 2');
      expect(result.content).toContain('Response 3');
    });

    it('should format responses correctly', async () => {
      const consensus = new ConsensusAgent();
      consensus.addAgent(new MockAgent('agent1', 'First'));
      consensus.addAgent(new MockAgent('agent2', 'Second'));

      const result = await consensus.process(createMessage('user', 'Test'));

      expect(result.content).toContain('Agent 1:');
      expect(result.content).toContain('Agent 2:');
    });

    it('should handle empty agent list', async () => {
      const consensus = new ConsensusAgent();

      const result = await consensus.process(createMessage('user', 'Test'));

      expect(result.content).toContain('Consensus from 0 agents');
    });

    it('should send same message to all agents', async () => {
      const consensus = new ConsensusAgent();
      const agent1 = new MockAgent('agent1');
      const agent2 = new MockAgent('agent2');

      consensus.addAgent(agent1);
      consensus.addAgent(agent2);

      const message = createMessage('user', 'Test message');
      await consensus.process(message);

      expect(agent1.lastMessage?.content).toBe('Test message');
      expect(agent2.lastMessage?.content).toBe('Test message');
    });
  });
});

// ============================================================================
// Integration Tests
// ============================================================================

describe('Integration', () => {
  it('should use ConsensusAgent within orchestrator', async () => {
    // Create a consensus agent
    const consensus = new ConsensusAgent();
    consensus.addAgent(new MockAgent('reviewer1', 'Looks good'));
    consensus.addAgent(new MockAgent('reviewer2', 'Approved'));

    // Create orchestrator
    const orchestrator = new MultiAgentOrchestrator();
    orchestrator.registerAgent('consensus', consensus);
    orchestrator.registerAgent('writer', new MockAgent('writer', 'Report written'));

    const result = await orchestrator.process(createMessage('user', 'Review report'));

    // Both agents should have run
    expect(result.content).toContain('Looks good');
    expect(result.content).toContain('Approved');
    expect(result.content).toContain('Report written');
  });

  it('should support nested orchestration', async () => {
    // Inner orchestrator
    const inner = new MultiAgentOrchestrator();
    inner.registerAgent('agent1', new MockAgent('agent1', 'Inner 1'));
    inner.registerAgent('agent2', new MockAgent('agent2', 'Inner 2'));

    // Outer orchestrator
    const outer = new MultiAgentOrchestrator();
    outer.registerAgent('inner_team', inner);
    outer.registerAgent('agent3', new MockAgent('agent3', 'Outer'));

    const result = await outer.process(createMessage('user', 'Test'));

    expect(result.content).toContain('Inner 1');
    expect(result.content).toContain('Inner 2');
    expect(result.content).toContain('Outer');
  });

  it('should compose multiple consensus agents', async () => {
    const consensus1 = new ConsensusAgent();
    consensus1.addAgent(new MockAgent('agent1', 'Opinion A'));
    consensus1.addAgent(new MockAgent('agent2', 'Opinion B'));

    const consensus2 = new ConsensusAgent();
    consensus2.addAgent(new MockAgent('agent3', 'Opinion C'));
    consensus2.addAgent(new MockAgent('agent4', 'Opinion D'));

    const orchestrator = new MultiAgentOrchestrator();
    orchestrator.registerAgent('team1', consensus1);
    orchestrator.registerAgent('team2', consensus2);

    const result = await orchestrator.process(createMessage('user', 'What do you think?'));

    expect(result.content).toContain('Opinion A');
    expect(result.content).toContain('Opinion B');
    expect(result.content).toContain('Opinion C');
    expect(result.content).toContain('Opinion D');
  });
});
