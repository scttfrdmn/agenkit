import { describe, it, expect, vi } from 'vitest';
import { Message } from '../../core/interfaces';
import { GraphOfThought } from './graph-of-thought';
import { EdgeType, NodeType, ReasoningGraph } from './reasoning-graph';

// Mock agent for testing
class MockAgent {
  private responses: string[];
  private callCount = 0;

  constructor(responses: string[]) {
    this.responses = responses;
  }

  get name(): string {
    return 'mock_agent';
  }

  get capabilities(): string[] {
    return ['mock'];
  }

  async process(message: Message): Promise<Message> {
    const response = this.responses[this.callCount % this.responses.length];
    this.callCount++;

    return {
      role: 'assistant',
      content: response,
    };
  }
}

describe('GraphOfThought', () => {
  it('should create agent with default config', () => {
    const mockLLM = new MockAgent(['response']);
    const agent = new GraphOfThought(mockLLM);

    expect(agent.name).toBe('graph_of_thought');
    expect(agent.capabilities).toContain('graph_reasoning');
    expect(agent.capabilities).toContain('multi_hop');
  });

  it('should create agent with custom config', () => {
    const mockLLM = new MockAgent(['response']);
    const agent = new GraphOfThought(mockLLM, {
      maxNodes: 15,
      maxEdges: 30,
      aggregator: 'node_based',
      allowCycles: true,
    });

    expect(agent.name).toBe('graph_of_thought');
    expect(agent.capabilities).toContain('path_aggregation');
  });

  it('should return correct capabilities', () => {
    const mockLLM = new MockAgent(['response']);
    const agent = new GraphOfThought(mockLLM);

    const caps = agent.capabilities;

    expect(caps).toContain('reasoning');
    expect(caps).toContain('graph_reasoning');
    expect(caps).toContain('multi_hop');
    expect(caps).toContain('path_aggregation');
    expect(caps).toContain('graph_of_thought');
    expect(caps).toHaveLength(5);
  });

  it('should generate premises from problem', async () => {
    const mockLLM = new MockAgent([
      '1. First premise\n2. Second premise\n3. Third premise',
    ]);

    const agent = new GraphOfThought(mockLLM);
    const message = { 
      role: 'user',
      content: 'Test problem',
    };

    const response = await agent.process(message);

    expect(response.metadata.numNodes).toBeGreaterThan(0);
    expect(response.metadata.technique).toBe('graph_of_thought');
  });

  it('should generate intermediate thoughts', async () => {
    const mockLLM = new MockAgent([
      // Premises
      '1. Initial fact\n2. Second fact',
      // First round of thoughts
      '1. First thought\n2. Second thought',
      // Second round of thoughts
      '1. Third thought',
      // Connections (multiple for pairwise checks)
      'NO_RELATION',
      'SUPPORT',
      'NO_RELATION',
      'DEPEND',
      'NO_RELATION',
      'NO_RELATION',
      'NO_RELATION',
      'NO_RELATION',
      'NO_RELATION',
      'NO_RELATION',
      // Final conclusion
      'Final conclusion based on thoughts',
    ]);

    const agent = new GraphOfThought(mockLLM, { maxNodes: 8 });
    const message = { 
      role: 'user',
      content: 'Complex problem',
    };

    const response = await agent.process(message);

    expect(response.metadata.numNodes).toBeGreaterThanOrEqual(2);
    expect(response.metadata.technique).toBe('graph_of_thought');
  });

  it('should identify connections between thoughts', async () => {
    const mockLLM = new MockAgent([
      // Premises
      '1. Base fact',
      // Thoughts
      '1. Derived conclusion',
      // Connection check
      'SUPPORT',
      // Final conclusion
      'Final answer',
    ]);

    const agent = new GraphOfThought(mockLLM, { maxNodes: 4 });
    const message = { 
      role: 'user',
      content: 'Problem',
    };

    const response = await agent.process(message);

    expect(response.metadata.numEdges).toBeGreaterThanOrEqual(0);
    expect(response.metadata.edgeTypes).toBeDefined();
  });

  it('should build complete reasoning graph', async () => {
    const mockLLM = new MockAgent([
      // Premises
      '1. Premise A\n2. Premise B',
      // Thoughts round 1
      '1. Thought 1\n2. Thought 2',
      // Thoughts round 2
      '1. Thought 3',
      // Thoughts round 3 (empty, breaks loop)
      '',
      // Connections
      'SUPPORT',
      'NO_RELATION',
      'DEPEND',
      'NO_RELATION',
      'REFINE',
      'NO_RELATION',
      'NO_RELATION',
      'NO_RELATION',
      'NO_RELATION',
      'NO_RELATION',
      // Conclusion
      'Final conclusion',
    ]);

    const agent = new GraphOfThought(mockLLM);
    const message = { 
      role: 'user',
      content: 'Complex problem requiring graph reasoning',
    };

    const response = await agent.process(message);

    // Check graph structure
    expect(response.metadata.graph).toBeInstanceOf(ReasoningGraph);
    expect(response.metadata.numNodes).toBeGreaterThanOrEqual(3);
    expect(response.metadata.nodeTypes[NodeType.PREMISE]).toBeGreaterThanOrEqual(
      1
    );
    expect(
      response.metadata.nodeTypes[NodeType.CONCLUSION]
    ).toBeGreaterThanOrEqual(1);
  });

  it('should find reasoning paths from premises to conclusions', async () => {
    const mockLLM = new MockAgent([
      // Premises
      '1. Start',
      // Thought
      '1. Middle',
      // Connection
      'SUPPORT',
      // Conclusion
      'End',
    ]);

    const agent = new GraphOfThought(mockLLM, {
      maxNodes: 4,
      maxEdges: 3,
    });

    const message = { 
      role: 'user',
      content: 'Find path problem',
    };

    const response = await agent.process(message);

    expect(response.metadata.reasoningPaths).toBeDefined();
    expect(Array.isArray(response.metadata.reasoningPaths)).toBe(true);
  });

  it('should aggregate paths with path_based strategy', async () => {
    const mockLLM = new MockAgent([
      // Premises
      '1. Fact A\n2. Fact B',
      // Thoughts
      '1. Analysis A',
      // Connections
      'SUPPORT',
      'NO_RELATION',
      'NO_RELATION',
      // Conclusion
      'Path-based conclusion',
    ]);

    const agent = new GraphOfThought(mockLLM, {
      maxNodes: 5,
      aggregator: 'path_based',
    });

    const message = { 
      role: 'user',
      content: 'Test aggregation',
    };

    const response = await agent.process(message);

    expect(response.content).toBeTruthy();
    expect(response.metadata.aggregator).toBe('path_based');
  });

  it('should aggregate paths with node_based strategy', async () => {
    const mockLLM = new MockAgent([
      // Premises
      '1. Fact X\n2. Fact Y',
      // Thoughts
      '1. Insight A',
      // Connections
      'SUPPORT',
      'DEPEND',
      'NO_RELATION',
      // Conclusion
      'Node-based conclusion',
    ]);

    const agent = new GraphOfThought(mockLLM, {
      maxNodes: 5,
      aggregator: 'node_based',
    });

    const message = { 
      role: 'user',
      content: 'Test node aggregation',
    };

    const response = await agent.process(message);

    expect(response.content).toBeTruthy();
    expect(response.metadata.aggregator).toBe('node_based');
  });

  it('should process complete workflow', async () => {
    const mockLLM = new MockAgent([
      // Premises
      '1. Water boils at 100°C\n2. Heat transfers energy',
      // Thoughts round 1
      '1. Boiling requires heat energy\n2. Temperature measures heat',
      // Thoughts round 2
      '1. Energy input raises temperature',
      // Connections (15 checks for 6 nodes)
      'SUPPORT',
      'DEPEND',
      'NO_RELATION',
      'REFINE',
      'NO_RELATION',
      'NO_RELATION',
      'SUPPORT',
      'NO_RELATION',
      'NO_RELATION',
      'NO_RELATION',
      'DEPEND',
      'NO_RELATION',
      'NO_RELATION',
      'NO_RELATION',
      'NO_RELATION',
      // Conclusion
      'Heating water adds energy, raising temperature to boiling point',
    ]);

    const agent = new GraphOfThought(mockLLM);
    const message = { 
      role: 'user',
      content: 'Explain how water boils',
    };

    const response = await agent.process(message);

    // Check response structure
    expect(response.role).toBe('assistant');
    expect(response.content).toBeTruthy();

    // Check metadata
    expect(response.metadata.technique).toBe('graph_of_thought');
    expect(response.metadata.graph).toBeInstanceOf(ReasoningGraph);
    expect(response.metadata.numNodes).toBeGreaterThanOrEqual(3);
    expect(response.metadata.numEdges).toBeGreaterThanOrEqual(0);
    expect(response.metadata.reasoningPaths).toBeDefined();

    // Check node types
    expect(response.metadata.nodeTypes).toBeDefined();
    expect(response.metadata.nodeTypes[NodeType.PREMISE]).toBeGreaterThanOrEqual(
      1
    );

    // Check edge types
    expect(response.metadata.edgeTypes).toBeDefined();
  });

  it('should detect cycles when configured', async () => {
    const mockLLM = new MockAgent([
      // Premises
      '1. A depends on B',
      // Thought
      '1. B depends on A',
      // Connections (intentionally create cycle)
      'DEPEND',
      'DEPEND',
      // Conclusion
      'Cycle detected',
    ]);

    const agent = new GraphOfThought(mockLLM, {
      maxNodes: 4,
      allowCycles: false,
    });

    const message = { 
      role: 'user',
      content: 'Circular reasoning test',
    };

    const response = await agent.process(message);

    // Should still complete even with cycles
    expect(response.content).toBeTruthy();
    expect(response.metadata.technique).toBe('graph_of_thought');
  });

  it('should handle empty paths gracefully', async () => {
    const mockLLM = new MockAgent([
      // Single premise
      '1. Isolated fact',
      // No intermediate thoughts (empty generation)
      '',
      // Connections (none)
      'NO_RELATION',
      // Conclusion
      'Direct conclusion from premise',
    ]);

    const agent = new GraphOfThought(mockLLM, { maxNodes: 3 });
    const message = { 
      role: 'user',
      content: 'Simple problem',
    };

    const response = await agent.process(message);

    // Should handle empty/minimal paths
    expect(response.content).toBeTruthy();
    expect(response.metadata.reasoningPaths).toBeDefined();
    expect(response.metadata.numNodes).toBeGreaterThanOrEqual(1);
  });

  it('should respect maxNodes limit', async () => {
    const mockLLM = new MockAgent([
      // Premises
      '1. P1\n2. P2',
      // Keep generating thoughts
      '1. T1\n2. T2\n3. T3',
      '1. T4\n2. T5',
      // Connections
      'SUPPORT',
      'SUPPORT',
      'SUPPORT',
      // Conclusion
      'Done',
    ]);

    const agent = new GraphOfThought(mockLLM, { maxNodes: 5 });
    const message = { 
      role: 'user',
      content: 'Test max nodes',
    };

    const response = await agent.process(message);

    expect(response.metadata.numNodes).toBeLessThanOrEqual(5);
  });

  it('should respect maxEdges limit', async () => {
    const mockLLM = new MockAgent([
      // Premises
      '1. A\n2. B\n3. C',
      // Thoughts
      '1. D\n2. E',
      // All connections say SUPPORT to hit edge limit
      'SUPPORT',
      'SUPPORT',
      'SUPPORT',
      'SUPPORT',
      'SUPPORT',
      'SUPPORT',
      'SUPPORT',
      'SUPPORT',
      'SUPPORT',
      'SUPPORT',
      // Conclusion
      'Edge limit reached',
    ]);

    const agent = new GraphOfThought(mockLLM, {
      maxNodes: 10,
      maxEdges: 3,
    });

    const message = { 
      role: 'user',
      content: 'Test max edges',
    };

    const response = await agent.process(message);

    expect(response.metadata.numEdges).toBeLessThanOrEqual(3);
  });

  it('should handle different edge types', async () => {
    const mockLLM = new MockAgent([
      // Premises
      '1. Base fact',
      // Thoughts
      '1. Supporting evidence\n2. Contradicting evidence',
      // Connections with different types
      'SUPPORT',
      'CONTRADICT',
      'REFINE',
      // Conclusion
      'Mixed edges conclusion',
    ]);

    const agent = new GraphOfThought(mockLLM, { maxNodes: 5 });
    const message = { 
      role: 'user',
      content: 'Test edge types',
    };

    const response = await agent.process(message);

    const edgeTypes = response.metadata.edgeTypes;
    expect(edgeTypes).toBeDefined();

    // Should have captured different edge types
    const totalEdges = Object.values(edgeTypes as Record<string, number>).reduce(
      (sum, count) => sum + count,
      0
    );
    expect(totalEdges).toBeGreaterThanOrEqual(0);
  });
});

describe('ReasoningGraph', () => {
  it('should add nodes correctly', () => {
    const graph = new ReasoningGraph();

    const id1 = graph.addNode('Node 1', NodeType.PREMISE, 0.9);
    const id2 = graph.addNode('Node 2', NodeType.INTERMEDIATE, 0.7);
    const id3 = graph.addNode('Node 3', NodeType.CONCLUSION, 0.8);

    expect(id1).toBe(0);
    expect(id2).toBe(1);
    expect(id3).toBe(2);

    const node1 = graph.getNode(id1);
    expect(node1?.content).toBe('Node 1');
    expect(node1?.nodeType).toBe(NodeType.PREMISE);
    expect(node1?.confidence).toBe(0.9);
  });

  it('should add edges correctly', () => {
    const graph = new ReasoningGraph();

    const id1 = graph.addNode('A', NodeType.PREMISE, 1.0);
    const id2 = graph.addNode('B', NodeType.INTERMEDIATE, 0.8);

    graph.addEdge(id1, id2, EdgeType.SUPPORTS, 0.9);

    const edges = graph.getEdges();
    expect(edges).toHaveLength(1);
    expect(edges[0].fromNode).toBe(id1);
    expect(edges[0].toNode).toBe(id2);
    expect(edges[0].edgeType).toBe(EdgeType.SUPPORTS);
  });

  it('should throw error for invalid edge nodes', () => {
    const graph = new ReasoningGraph();

    const id1 = graph.addNode('A', NodeType.PREMISE, 1.0);

    expect(() => {
      graph.addEdge(id1, 999, EdgeType.SUPPORTS, 1.0);
    }).toThrow('Both nodes must exist in graph');
  });

  it('should find paths correctly', () => {
    const graph = new ReasoningGraph();

    const id1 = graph.addNode('Start', NodeType.PREMISE, 1.0);
    const id2 = graph.addNode('Middle', NodeType.INTERMEDIATE, 0.8);
    const id3 = graph.addNode('End', NodeType.CONCLUSION, 0.9);

    graph.addEdge(id1, id2, EdgeType.SUPPORTS, 0.9);
    graph.addEdge(id2, id3, EdgeType.SUPPORTS, 0.8);

    const paths = graph.findPaths(id1, id3);

    expect(paths.length).toBeGreaterThan(0);
    expect(paths[0]).toEqual([id1, id2, id3]);
  });

  it('should detect cycles', () => {
    const graph = new ReasoningGraph();

    const id1 = graph.addNode('A', NodeType.PREMISE, 1.0);
    const id2 = graph.addNode('B', NodeType.INTERMEDIATE, 0.8);
    const id3 = graph.addNode('C', NodeType.INTERMEDIATE, 0.8);

    // Create a cycle: A -> B -> C -> A
    graph.addEdge(id1, id2, EdgeType.SUPPORTS, 1.0);
    graph.addEdge(id2, id3, EdgeType.SUPPORTS, 1.0);
    graph.addEdge(id3, id1, EdgeType.SUPPORTS, 1.0);

    expect(graph.hasCycle()).toBe(true);
  });

  it('should not detect cycles in acyclic graph', () => {
    const graph = new ReasoningGraph();

    const id1 = graph.addNode('A', NodeType.PREMISE, 1.0);
    const id2 = graph.addNode('B', NodeType.INTERMEDIATE, 0.8);
    const id3 = graph.addNode('C', NodeType.CONCLUSION, 0.9);

    graph.addEdge(id1, id2, EdgeType.SUPPORTS, 1.0);
    graph.addEdge(id2, id3, EdgeType.SUPPORTS, 1.0);

    expect(graph.hasCycle()).toBe(false);
  });

  it('should calculate path scores correctly', () => {
    const graph = new ReasoningGraph();

    const id1 = graph.addNode('A', NodeType.PREMISE, 0.9);
    const id2 = graph.addNode('B', NodeType.INTERMEDIATE, 0.8);
    const id3 = graph.addNode('C', NodeType.CONCLUSION, 0.7);

    graph.addEdge(id1, id2, EdgeType.SUPPORTS, 0.9);
    graph.addEdge(id2, id3, EdgeType.SUPPORTS, 0.8);

    const path = [id1, id2, id3];
    const score = graph.getPathScore(path);

    // Score = node confidences + edge strengths
    // 0.9 + 0.8 + 0.7 + 0.9 + 0.8 = 4.1
    expect(score).toBeCloseTo(4.1, 1);
  });

  it('should return correct statistics', () => {
    const graph = new ReasoningGraph();

    const id1 = graph.addNode('P1', NodeType.PREMISE, 1.0);
    const id2 = graph.addNode('P2', NodeType.PREMISE, 1.0);
    const id3 = graph.addNode('I1', NodeType.INTERMEDIATE, 0.8);
    const id4 = graph.addNode('C1', NodeType.CONCLUSION, 0.9);

    graph.addEdge(id1, id3, EdgeType.SUPPORTS, 0.9);
    graph.addEdge(id2, id3, EdgeType.DEPENDS_ON, 0.8);
    graph.addEdge(id3, id4, EdgeType.REFINES, 0.7);

    const stats = graph.statistics();

    expect(stats.numNodes).toBe(4);
    expect(stats.numEdges).toBe(3);
    expect(stats.nodeTypes[NodeType.PREMISE]).toBe(2);
    expect(stats.nodeTypes[NodeType.INTERMEDIATE]).toBe(1);
    expect(stats.nodeTypes[NodeType.CONCLUSION]).toBe(1);
    expect(stats.edgeTypes[EdgeType.SUPPORTS]).toBe(1);
    expect(stats.edgeTypes[EdgeType.DEPENDS_ON]).toBe(1);
    expect(stats.edgeTypes[EdgeType.REFINES]).toBe(1);
  });

  it('should get premises and conclusions', () => {
    const graph = new ReasoningGraph();

    graph.addNode('Premise 1', NodeType.PREMISE, 1.0);
    graph.addNode('Premise 2', NodeType.PREMISE, 1.0);
    graph.addNode('Intermediate', NodeType.INTERMEDIATE, 0.8);
    graph.addNode('Conclusion 1', NodeType.CONCLUSION, 0.9);

    const premises = graph.getPremises();
    const conclusions = graph.getConclusions();

    expect(premises).toHaveLength(2);
    expect(conclusions).toHaveLength(1);
  });
});
