import { describe, it, expect } from 'vitest';
import {
  ReasoningGraph,
  NodeType,
  EdgeType,
  ThoughtNode,
  LogicalEdge,
} from './reasoning-graph';

describe('ReasoningGraph', () => {
  describe('node creation', () => {
    it('should add a node and return an incremented ID', () => {
      const graph = new ReasoningGraph();
      const id0 = graph.addNode('first premise', NodeType.PREMISE);
      const id1 = graph.addNode('second premise', NodeType.PREMISE);

      expect(id0).toBe(0);
      expect(id1).toBe(1);
    });

    it('should store node content and type correctly', () => {
      const graph = new ReasoningGraph();
      const id = graph.addNode('Some thought', NodeType.INTERMEDIATE, 0.7);

      const node = graph.getNode(id);
      expect(node).toBeDefined();
      expect(node!.content).toBe('Some thought');
      expect(node!.nodeType).toBe(NodeType.INTERMEDIATE);
      expect(node!.confidence).toBeCloseTo(0.7);
    });

    it('should default confidence to 1.0', () => {
      const graph = new ReasoningGraph();
      const id = graph.addNode('premise', NodeType.PREMISE);
      expect(graph.getNode(id)!.confidence).toBe(1.0);
    });

    it('should store optional metadata', () => {
      const graph = new ReasoningGraph();
      const meta = { source: 'test', weight: 42 };
      const id = graph.addNode('node with meta', NodeType.CONCLUSION, 0.9, meta);

      const node = graph.getNode(id);
      expect(node!.metadata).toEqual(meta);
    });

    it('should return undefined for unknown node ID', () => {
      const graph = new ReasoningGraph();
      expect(graph.getNode(999)).toBeUndefined();
    });

    it('should retrieve all premise nodes', () => {
      const graph = new ReasoningGraph();
      graph.addNode('p1', NodeType.PREMISE);
      graph.addNode('intermediate', NodeType.INTERMEDIATE);
      graph.addNode('p2', NodeType.PREMISE);
      graph.addNode('conclusion', NodeType.CONCLUSION);

      const premises = graph.getPremises();
      expect(premises).toHaveLength(2);
      expect(premises.every((n: ThoughtNode) => n.nodeType === NodeType.PREMISE)).toBe(true);
    });

    it('should retrieve all conclusion nodes', () => {
      const graph = new ReasoningGraph();
      graph.addNode('premise', NodeType.PREMISE);
      graph.addNode('c1', NodeType.CONCLUSION);
      graph.addNode('c2', NodeType.CONCLUSION);

      const conclusions = graph.getConclusions();
      expect(conclusions).toHaveLength(2);
      expect(conclusions.every((n: ThoughtNode) => n.nodeType === NodeType.CONCLUSION)).toBe(true);
    });

    it('getNodes() should return all nodes', () => {
      const graph = new ReasoningGraph();
      graph.addNode('a', NodeType.PREMISE);
      graph.addNode('b', NodeType.INTERMEDIATE);
      graph.addNode('c', NodeType.CONCLUSION);

      expect(graph.getNodes()).toHaveLength(3);
    });
  });

  describe('edge construction', () => {
    it('should add an edge between existing nodes', () => {
      const graph = new ReasoningGraph();
      const a = graph.addNode('A', NodeType.PREMISE);
      const b = graph.addNode('B', NodeType.CONCLUSION);

      expect(() => graph.addEdge(a, b, EdgeType.SUPPORTS)).not.toThrow();
      expect(graph.getEdges()).toHaveLength(1);
    });

    it('should store edge type and strength correctly', () => {
      const graph = new ReasoningGraph();
      const a = graph.addNode('A', NodeType.PREMISE);
      const b = graph.addNode('B', NodeType.CONCLUSION);
      graph.addEdge(a, b, EdgeType.DEPENDS_ON, 0.6);

      const edges = graph.getEdges();
      expect(edges[0].edgeType).toBe(EdgeType.DEPENDS_ON);
      expect(edges[0].strength).toBeCloseTo(0.6);
    });

    it('should default edge strength to 1.0', () => {
      const graph = new ReasoningGraph();
      const a = graph.addNode('A', NodeType.PREMISE);
      const b = graph.addNode('B', NodeType.CONCLUSION);
      graph.addEdge(a, b, EdgeType.SUPPORTS);

      expect(graph.getEdges()[0].strength).toBe(1.0);
    });

    it('should store edge metadata', () => {
      const graph = new ReasoningGraph();
      const a = graph.addNode('A', NodeType.PREMISE);
      const b = graph.addNode('B', NodeType.CONCLUSION);
      graph.addEdge(a, b, EdgeType.REFINES, 0.8, { reason: 'refinement' });

      const edge: LogicalEdge = graph.getEdges()[0];
      expect(edge.metadata).toEqual({ reason: 'refinement' });
    });

    it('should throw if source node does not exist', () => {
      const graph = new ReasoningGraph();
      const b = graph.addNode('B', NodeType.CONCLUSION);
      expect(() => graph.addEdge(999, b, EdgeType.SUPPORTS)).toThrow(
        'Both nodes must exist in graph',
      );
    });

    it('should throw if target node does not exist', () => {
      const graph = new ReasoningGraph();
      const a = graph.addNode('A', NodeType.PREMISE);
      expect(() => graph.addEdge(a, 999, EdgeType.SUPPORTS)).toThrow(
        'Both nodes must exist in graph',
      );
    });

    it('getEdges() returns a copy, not the internal array', () => {
      const graph = new ReasoningGraph();
      const a = graph.addNode('A', NodeType.PREMISE);
      const b = graph.addNode('B', NodeType.CONCLUSION);
      graph.addEdge(a, b, EdgeType.SUPPORTS);

      const edges = graph.getEdges();
      edges.pop(); // mutate the returned copy
      expect(graph.getEdges()).toHaveLength(1); // original unaffected
    });
  });

  describe('graph traversal — findPaths', () => {
    it('should find direct path between adjacent nodes', () => {
      const graph = new ReasoningGraph();
      const a = graph.addNode('A', NodeType.PREMISE);
      const b = graph.addNode('B', NodeType.CONCLUSION);
      graph.addEdge(a, b, EdgeType.SUPPORTS);

      const paths = graph.findPaths(a, b);
      expect(paths).toHaveLength(1);
      expect(paths[0]).toEqual([a, b]);
    });

    it('should find multi-hop path', () => {
      const graph = new ReasoningGraph();
      const a = graph.addNode('A', NodeType.PREMISE);
      const b = graph.addNode('B', NodeType.INTERMEDIATE);
      const c = graph.addNode('C', NodeType.CONCLUSION);
      graph.addEdge(a, b, EdgeType.SUPPORTS);
      graph.addEdge(b, c, EdgeType.SUPPORTS);

      const paths = graph.findPaths(a, c);
      expect(paths).toHaveLength(1);
      expect(paths[0]).toEqual([a, b, c]);
    });

    it('should find multiple paths', () => {
      const graph = new ReasoningGraph();
      const a = graph.addNode('A', NodeType.PREMISE);
      const b = graph.addNode('B', NodeType.INTERMEDIATE);
      const c = graph.addNode('C', NodeType.CONCLUSION);
      graph.addEdge(a, b, EdgeType.SUPPORTS);
      graph.addEdge(b, c, EdgeType.SUPPORTS);
      graph.addEdge(a, c, EdgeType.SUPPORTS); // direct path too

      const paths = graph.findPaths(a, c);
      expect(paths.length).toBeGreaterThanOrEqual(2);
    });

    it('should return empty array when no path exists', () => {
      const graph = new ReasoningGraph();
      const a = graph.addNode('A', NodeType.PREMISE);
      const b = graph.addNode('B', NodeType.CONCLUSION);
      // no edge between a and b

      expect(graph.findPaths(a, b)).toHaveLength(0);
    });

    it('should respect maxLength limit', () => {
      const graph = new ReasoningGraph();
      // Chain of 5 nodes
      const ids: number[] = [];
      for (let i = 0; i < 5; i++) {
        ids.push(graph.addNode(`node${i}`, NodeType.INTERMEDIATE));
      }
      for (let i = 0; i < 4; i++) {
        graph.addEdge(ids[i], ids[i + 1], EdgeType.SUPPORTS);
      }

      // maxLength=2 — no path of length 4 should appear
      const paths = graph.findPaths(ids[0], ids[4], 2);
      expect(paths).toHaveLength(0);
    });
  });

  describe('cycle detection', () => {
    it('should detect no cycles in a DAG', () => {
      const graph = new ReasoningGraph();
      const a = graph.addNode('A', NodeType.PREMISE);
      const b = graph.addNode('B', NodeType.INTERMEDIATE);
      const c = graph.addNode('C', NodeType.CONCLUSION);
      graph.addEdge(a, b, EdgeType.SUPPORTS);
      graph.addEdge(b, c, EdgeType.SUPPORTS);

      expect(graph.hasCycle()).toBe(false);
    });

    it('should detect a direct cycle', () => {
      const graph = new ReasoningGraph();
      const a = graph.addNode('A', NodeType.PREMISE);
      const b = graph.addNode('B', NodeType.CONCLUSION);
      graph.addEdge(a, b, EdgeType.SUPPORTS);
      graph.addEdge(b, a, EdgeType.CONTRADICTS); // cycle

      expect(graph.hasCycle()).toBe(true);
    });

    it('should detect an indirect cycle', () => {
      const graph = new ReasoningGraph();
      const a = graph.addNode('A', NodeType.PREMISE);
      const b = graph.addNode('B', NodeType.INTERMEDIATE);
      const c = graph.addNode('C', NodeType.CONCLUSION);
      graph.addEdge(a, b, EdgeType.SUPPORTS);
      graph.addEdge(b, c, EdgeType.SUPPORTS);
      graph.addEdge(c, a, EdgeType.DEPENDS_ON); // cycle back to start

      expect(graph.hasCycle()).toBe(true);
    });

    it('should return false for an empty graph', () => {
      const graph = new ReasoningGraph();
      expect(graph.hasCycle()).toBe(false);
    });
  });

  describe('path scoring', () => {
    it('should score a single-node path using confidence', () => {
      const graph = new ReasoningGraph();
      const a = graph.addNode('A', NodeType.CONCLUSION, 0.8);

      const score = graph.getPathScore([a]);
      expect(score).toBeCloseTo(0.8);
    });

    it('should sum confidence and edge strength for a path', () => {
      const graph = new ReasoningGraph();
      const a = graph.addNode('A', NodeType.PREMISE, 1.0);
      const b = graph.addNode('B', NodeType.CONCLUSION, 0.9);
      graph.addEdge(a, b, EdgeType.SUPPORTS, 0.7);

      // score = confidence(a) + confidence(b) + edge_strength(a→b)
      const score = graph.getPathScore([a, b]);
      expect(score).toBeCloseTo(1.0 + 0.9 + 0.7);
    });

    it('should return 0 for empty path', () => {
      const graph = new ReasoningGraph();
      expect(graph.getPathScore([])).toBe(0);
    });
  });

  describe('graph statistics', () => {
    it('should report correct node and edge counts', () => {
      const graph = new ReasoningGraph();
      const a = graph.addNode('A', NodeType.PREMISE);
      const b = graph.addNode('B', NodeType.INTERMEDIATE);
      const c = graph.addNode('C', NodeType.CONCLUSION);
      graph.addEdge(a, b, EdgeType.SUPPORTS);
      graph.addEdge(b, c, EdgeType.DEPENDS_ON);

      const stats = graph.statistics();
      expect(stats.numNodes).toBe(3);
      expect(stats.numEdges).toBe(2);
    });

    it('should count node types correctly', () => {
      const graph = new ReasoningGraph();
      graph.addNode('p1', NodeType.PREMISE);
      graph.addNode('p2', NodeType.PREMISE);
      graph.addNode('i1', NodeType.INTERMEDIATE);
      graph.addNode('c1', NodeType.CONCLUSION);

      const stats = graph.statistics();
      expect(stats.nodeTypes[NodeType.PREMISE]).toBe(2);
      expect(stats.nodeTypes[NodeType.INTERMEDIATE]).toBe(1);
      expect(stats.nodeTypes[NodeType.CONCLUSION]).toBe(1);
    });

    it('should count edge types correctly', () => {
      const graph = new ReasoningGraph();
      const a = graph.addNode('A', NodeType.PREMISE);
      const b = graph.addNode('B', NodeType.INTERMEDIATE);
      const c = graph.addNode('C', NodeType.CONCLUSION);
      const d = graph.addNode('D', NodeType.CONCLUSION);
      graph.addEdge(a, b, EdgeType.SUPPORTS);
      graph.addEdge(b, c, EdgeType.DEPENDS_ON);
      graph.addEdge(a, d, EdgeType.SUPPORTS);

      const stats = graph.statistics();
      expect(stats.edgeTypes[EdgeType.SUPPORTS]).toBe(2);
      expect(stats.edgeTypes[EdgeType.DEPENDS_ON]).toBe(1);
      expect(stats.edgeTypes[EdgeType.CONTRADICTS]).toBe(0);
      expect(stats.edgeTypes[EdgeType.REFINES]).toBe(0);
    });

    it('should report hasCycles correctly in statistics', () => {
      const graphNoCycle = new ReasoningGraph();
      const a1 = graphNoCycle.addNode('A', NodeType.PREMISE);
      const b1 = graphNoCycle.addNode('B', NodeType.CONCLUSION);
      graphNoCycle.addEdge(a1, b1, EdgeType.SUPPORTS);
      expect(graphNoCycle.statistics().hasCycles).toBe(false);

      const graphWithCycle = new ReasoningGraph();
      const a2 = graphWithCycle.addNode('A', NodeType.PREMISE);
      const b2 = graphWithCycle.addNode('B', NodeType.CONCLUSION);
      graphWithCycle.addEdge(a2, b2, EdgeType.SUPPORTS);
      graphWithCycle.addEdge(b2, a2, EdgeType.CONTRADICTS);
      expect(graphWithCycle.statistics().hasCycles).toBe(true);
    });

    it('should return zero counts for an empty graph', () => {
      const stats = new ReasoningGraph().statistics();
      expect(stats.numNodes).toBe(0);
      expect(stats.numEdges).toBe(0);
      expect(stats.hasCycles).toBe(false);
    });
  });
});
