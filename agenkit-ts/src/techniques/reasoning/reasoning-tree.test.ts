/**
 * Comprehensive tests for ReasoningTree data structure
 *
 * Tests cover:
 * - Node creation and tree building
 * - Path operations and traversal
 * - State management and pruning
 * - Statistics and analysis
 * - Edge cases and error handling
 */

import { describe, it, expect } from 'vitest';
import { ReasoningTree, NodeState, type ReasoningNode } from './reasoning-tree';

// ============================================
// Tree Creation Tests
// ============================================

describe('ReasoningTree: Creation', () => {
  it('should create empty tree', () => {
    const tree = new ReasoningTree();

    expect(tree.size()).toBe(0);
    expect(tree.getRootId()).toBeNull();
    expect(tree.maxDepth).toBe(0);
  });

  it('should create root node', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('What is 2+2?');

    expect(tree.size()).toBe(1);
    expect(tree.getRootId()).toBe(rootId);
    expect(rootId).toBe(0);
  });

  it('should create root with metadata', () => {
    const tree = new ReasoningTree();
    const metadata = { query: true, priority: 'high' };
    const rootId = tree.createRoot('Query', metadata);

    const root = tree.getNode(rootId);
    expect(root).toBeDefined();
    expect(root!.metadata).toEqual(metadata);
  });

  it('should initialize root node correctly', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root content');
    const root = tree.getNode(rootId);

    expect(root).toBeDefined();
    expect(root!.id).toBe(rootId);
    expect(root!.content).toBe('Root content');
    expect(root!.parentId).toBeNull();
    expect(root!.childrenIds).toEqual([]);
    expect(root!.depth).toBe(0);
    expect(root!.score).toBe(0.0);
    expect(root!.state).toBe(NodeState.Open);
  });
});

// ============================================
// Child Node Tests
// ============================================

describe('ReasoningTree: Adding Children', () => {
  it('should add child to root', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const childId = tree.addChild(rootId, 'Child', 0.8);

    expect(tree.size()).toBe(2);
    expect(childId).toBe(1);

    const root = tree.getNode(rootId);
    expect(root!.childrenIds).toContain(childId);
  });

  it('should set child properties correctly', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const childId = tree.addChild(rootId, 'Child content', 0.75);

    const child = tree.getNode(childId);
    expect(child).toBeDefined();
    expect(child!.content).toBe('Child content');
    expect(child!.parentId).toBe(rootId);
    expect(child!.depth).toBe(1);
    expect(child!.score).toBe(0.75);
    expect(child!.childrenIds).toEqual([]);
  });

  it('should add multiple children to same parent', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');

    const child1 = tree.addChild(rootId, 'Child 1', 0.7);
    const child2 = tree.addChild(rootId, 'Child 2', 0.8);
    const child3 = tree.addChild(rootId, 'Child 3', 0.6);

    const root = tree.getNode(rootId);
    expect(root!.childrenIds).toEqual([child1, child2, child3]);
    expect(tree.size()).toBe(4);
  });

  it('should create multi-level tree', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const level1 = tree.addChild(rootId, 'Level 1', 0.8);
    const level2 = tree.addChild(level1, 'Level 2', 0.7);
    const level3 = tree.addChild(level2, 'Level 3', 0.9);

    expect(tree.size()).toBe(4);
    expect(tree.maxDepth).toBe(3);

    const leaf = tree.getNode(level3);
    expect(leaf!.depth).toBe(3);
  });

  it('should throw error for invalid parent', () => {
    const tree = new ReasoningTree();
    tree.createRoot('Root');

    expect(() => {
      tree.addChild(999, 'Child', 0.5);
    }).toThrow('Parent node 999 not found');
  });

  it('should handle child with metadata', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const metadata = { type: 'reasoning', step: 1 };
    const childId = tree.addChild(rootId, 'Child', 0.8, metadata);

    const child = tree.getNode(childId);
    expect(child!.metadata).toEqual(metadata);
  });

  it('should update max depth correctly', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');

    expect(tree.maxDepth).toBe(0);

    const child1 = tree.addChild(rootId, 'Level 1', 0.5);
    expect(tree.maxDepth).toBe(1);

    const child2 = tree.addChild(child1, 'Level 2', 0.5);
    expect(tree.maxDepth).toBe(2);

    // Adding sibling shouldn't change max depth
    tree.addChild(rootId, 'Another Level 1', 0.5);
    expect(tree.maxDepth).toBe(2);
  });
});

// ============================================
// Node Retrieval Tests
// ============================================

describe('ReasoningTree: Node Retrieval', () => {
  it('should get node by ID', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const childId = tree.addChild(rootId, 'Child', 0.8);

    const root = tree.getNode(rootId);
    const child = tree.getNode(childId);

    expect(root).toBeDefined();
    expect(child).toBeDefined();
    expect(root!.id).toBe(rootId);
    expect(child!.id).toBe(childId);
  });

  it('should return undefined for invalid ID', () => {
    const tree = new ReasoningTree();
    tree.createRoot('Root');

    const node = tree.getNode(999);
    expect(node).toBeUndefined();
  });

  it('should get all children of node', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const child1 = tree.addChild(rootId, 'Child 1', 0.7);
    const child2 = tree.addChild(rootId, 'Child 2', 0.8);

    const children = tree.getChildren(rootId);
    expect(children).toHaveLength(2);
    expect(children.map((c) => c.id)).toEqual([child1, child2]);
  });

  it('should return empty array for leaf node children', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const childId = tree.addChild(rootId, 'Child', 0.8);

    const children = tree.getChildren(childId);
    expect(children).toEqual([]);
  });

  it('should return empty array for invalid node ID', () => {
    const tree = new ReasoningTree();
    tree.createRoot('Root');

    const children = tree.getChildren(999);
    expect(children).toEqual([]);
  });
});

// ============================================
// Path Operations Tests
// ============================================

describe('ReasoningTree: Path Operations', () => {
  it('should get path from root to leaf', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const child1 = tree.addChild(rootId, 'Step 1', 0.8);
    const child2 = tree.addChild(child1, 'Step 2', 0.7);
    const child3 = tree.addChild(child2, 'Step 3', 0.9);

    const path = tree.getPath(child3);
    expect(path).toHaveLength(4);
    expect(path.map((n) => n.content)).toEqual(['Root', 'Step 1', 'Step 2', 'Step 3']);
  });

  it('should get path for root node', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');

    const path = tree.getPath(rootId);
    expect(path).toHaveLength(1);
    expect(path[0].content).toBe('Root');
  });

  it('should get path text with default delimiter', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const child1 = tree.addChild(rootId, 'Step 1', 0.8);
    const child2 = tree.addChild(child1, 'Step 2', 0.7);

    const pathText = tree.getPathText(child2);
    expect(pathText).toBe('Root\nStep 1\nStep 2');
  });

  it('should get path text with custom delimiter', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const child1 = tree.addChild(rootId, 'Step 1', 0.8);
    const child2 = tree.addChild(child1, 'Step 2', 0.7);

    const pathText = tree.getPathText(child2, ' -> ');
    expect(pathText).toBe('Root -> Step 1 -> Step 2');
  });

  it('should handle path for invalid node', () => {
    const tree = new ReasoningTree();
    tree.createRoot('Root');

    const path = tree.getPath(999);
    expect(path).toEqual([]);
  });
});

// ============================================
// Leaf Operations Tests
// ============================================

describe('ReasoningTree: Leaf Operations', () => {
  it('should get all leaf nodes', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const branch1 = tree.addChild(rootId, 'Branch 1', 0.7);
    const leaf1 = tree.addChild(branch1, 'Leaf 1', 0.8);
    const branch2 = tree.addChild(rootId, 'Branch 2', 0.6);
    const leaf2 = tree.addChild(branch2, 'Leaf 2', 0.9);

    const leaves = tree.getLeaves();
    expect(leaves).toHaveLength(2);
    expect(leaves.map((l) => l.id).sort()).toEqual([leaf1, leaf2].sort());
  });

  it('should return root as leaf if no children', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');

    const leaves = tree.getLeaves();
    expect(leaves).toHaveLength(1);
    expect(leaves[0].id).toBe(rootId);
  });

  it('should get best scoring leaf', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const child1 = tree.addChild(rootId, 'Leaf 1', 0.7);
    const child2 = tree.addChild(rootId, 'Leaf 2', 0.9); // Best
    const child3 = tree.addChild(rootId, 'Leaf 3', 0.6);

    const bestLeaf = tree.getBestLeaf();
    expect(bestLeaf).toBeDefined();
    expect(bestLeaf!.id).toBe(child2);
    expect(bestLeaf!.score).toBe(0.9);
  });

  it('should return undefined for best leaf in empty tree', () => {
    const tree = new ReasoningTree();

    const bestLeaf = tree.getBestLeaf();
    expect(bestLeaf).toBeUndefined();
  });

  it('should check if node is leaf', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const childId = tree.addChild(rootId, 'Child', 0.8);

    expect(tree.isLeaf(rootId)).toBe(false);
    expect(tree.isLeaf(childId)).toBe(true);
  });

  it('should return false for invalid node in isLeaf', () => {
    const tree = new ReasoningTree();
    tree.createRoot('Root');

    expect(tree.isLeaf(999)).toBe(false);
  });
});

// ============================================
// Pruning Tests
// ============================================

describe('ReasoningTree: Pruning', () => {
  it('should mark node as pruned', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const childId = tree.addChild(rootId, 'Child', 0.3);

    tree.pruneNode(childId);

    const child = tree.getNode(childId);
    expect(child!.state).toBe(NodeState.Pruned);
  });

  it('should handle pruning invalid node gracefully', () => {
    const tree = new ReasoningTree();
    tree.createRoot('Root');

    // Should not throw
    expect(() => tree.pruneNode(999)).not.toThrow();
  });

  it('should count pruned nodes in statistics', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const child1 = tree.addChild(rootId, 'Child 1', 0.3);
    const child2 = tree.addChild(rootId, 'Child 2', 0.8);

    tree.pruneNode(child1);

    const stats = tree.getStatistics();
    expect(stats.numPruned).toBe(1);
  });
});

// ============================================
// Statistics Tests
// ============================================

describe('ReasoningTree: Statistics', () => {
  it('should compute correct statistics', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const child1 = tree.addChild(rootId, 'Child 1', 0.7);
    const child2 = tree.addChild(rootId, 'Child 2', 0.9);

    const stats = tree.getStatistics();
    expect(stats.totalNodes).toBe(3);
    expect(stats.maxDepth).toBe(1);
    expect(stats.numLeaves).toBe(2);
    expect(stats.avgScore).toBeCloseTo(0.8, 1); // (0.7 + 0.9) / 2
    expect(stats.bestScore).toBe(0.9);
  });

  it('should compute stats for empty tree', () => {
    const tree = new ReasoningTree();

    const stats = tree.getStatistics();
    expect(stats.totalNodes).toBe(0);
    expect(stats.maxDepth).toBe(0);
    expect(stats.numLeaves).toBe(0);
    expect(stats.numEvaluated).toBe(0);
    expect(stats.numPruned).toBe(0);
    expect(stats.avgScore).toBe(0.0);
    expect(stats.bestScore).toBe(0.0);
  });

  it('should compute stats for single root', () => {
    const tree = new ReasoningTree();
    tree.createRoot('Root');

    const stats = tree.getStatistics();
    expect(stats.totalNodes).toBe(1);
    expect(stats.maxDepth).toBe(0);
    expect(stats.numLeaves).toBe(1);
    expect(stats.avgScore).toBe(0.0);
    expect(stats.bestScore).toBe(0.0);
  });

  it('should track evaluated nodes', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const childId = tree.addChild(rootId, 'Child', 0.8);

    // Manually set state to evaluated (would normally be done by search algorithm)
    const child = tree.getNode(childId);
    child!.state = NodeState.Evaluated;

    const stats = tree.getStatistics();
    expect(stats.numEvaluated).toBe(1);
  });
});

// ============================================
// Helper Method Tests
// ============================================

describe('ReasoningTree: Helper Methods', () => {
  it('should check if node is root', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const childId = tree.addChild(rootId, 'Child', 0.8);

    expect(tree.isRoot(rootId)).toBe(true);
    expect(tree.isRoot(childId)).toBe(false);
  });

  it('should return false for invalid node in isRoot', () => {
    const tree = new ReasoningTree();
    tree.createRoot('Root');

    expect(tree.isRoot(999)).toBe(false);
  });

  it('should get root ID', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');

    expect(tree.getRootId()).toBe(rootId);
  });

  it('should return null for root ID in empty tree', () => {
    const tree = new ReasoningTree();

    expect(tree.getRootId()).toBeNull();
  });

  it('should return correct size', () => {
    const tree = new ReasoningTree();

    expect(tree.size()).toBe(0);

    const rootId = tree.createRoot('Root');
    expect(tree.size()).toBe(1);

    tree.addChild(rootId, 'Child 1', 0.7);
    expect(tree.size()).toBe(2);

    tree.addChild(rootId, 'Child 2', 0.8);
    expect(tree.size()).toBe(3);
  });
});

// ============================================
// Node State Tests
// ============================================

describe('ReasoningTree: Node States', () => {
  it('should initialize nodes as Open', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');
    const childId = tree.addChild(rootId, 'Child', 0.8);

    const root = tree.getNode(rootId);
    const child = tree.getNode(childId);

    expect(root!.state).toBe(NodeState.Open);
    expect(child!.state).toBe(NodeState.Open);
  });

  it('should support all node states', () => {
    const tree = new ReasoningTree();
    const rootId = tree.createRoot('Root');

    const node = tree.getNode(rootId);
    node!.state = NodeState.Active;
    expect(node!.state).toBe(NodeState.Active);

    node!.state = NodeState.Evaluated;
    expect(node!.state).toBe(NodeState.Evaluated);

    node!.state = NodeState.Pruned;
    expect(node!.state).toBe(NodeState.Pruned);

    node!.state = NodeState.Terminal;
    expect(node!.state).toBe(NodeState.Terminal);
  });
});
