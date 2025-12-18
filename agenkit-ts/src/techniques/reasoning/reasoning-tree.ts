/**
 * Reasoning Tree Data Structure
 *
 * Provides tree structures for representing branching reasoning paths
 * used by Tree-of-Thought and related techniques.
 *
 * This module defines:
 * - NodeState: State enum for reasoning nodes
 * - ReasoningNode: Individual node in reasoning tree
 * - ReasoningTree: Complete tree structure with search/traversal methods
 */

/**
 * State of a reasoning node during search.
 */
export enum NodeState {
  /** Not yet explored */
  Open = 'open',
  /** Currently being explored */
  Active = 'active',
  /** Evaluated, may have children */
  Evaluated = 'evaluated',
  /** Pruned from search */
  Pruned = 'pruned',
  /** Leaf node (complete reasoning path) */
  Terminal = 'terminal',
}

/**
 * Node in a reasoning tree.
 *
 * Represents a single reasoning step in a multi-step reasoning path.
 * Nodes can branch into multiple child nodes, forming a tree structure.
 */
export interface ReasoningNode {
  /** Unique node identifier */
  id: number;

  /** Reasoning text for this step */
  content: string;

  /** ID of parent node (null for root) */
  parentId: number | null;

  /** List of child node IDs */
  childrenIds: number[];

  /** Depth in tree (0 for root) */
  depth: number;

  /** Evaluation score (0.0-1.0, higher is better) */
  score: number;

  /** Current state in search process */
  state: NodeState;

  /** Additional node-specific data */
  metadata: Record<string, unknown>;
}

/**
 * Statistics about a reasoning tree.
 */
export interface TreeStatistics {
  /** Total number of nodes in tree */
  totalNodes: number;

  /** Maximum depth reached */
  maxDepth: number;

  /** Number of leaf nodes */
  numLeaves: number;

  /** Number of evaluated nodes */
  numEvaluated: number;

  /** Number of pruned nodes */
  numPruned: number;

  /** Average score across leaf nodes */
  avgScore: number;

  /** Best score among leaf nodes */
  bestScore: number;
}

/**
 * Tree structure for branching reasoning paths.
 *
 * Manages a tree of reasoning nodes with methods for building,
 * searching, and analyzing reasoning paths.
 *
 * @example
 * ```typescript
 * const tree = new ReasoningTree();
 * const rootId = tree.createRoot('Initial query');
 * const childId = tree.addChild(rootId, 'First reasoning step', 0.8);
 * const path = tree.getPath(childId);
 * console.log(tree.getPathText(childId));
 * ```
 */
export class ReasoningTree {
  private nodes: Map<number, ReasoningNode>;
  private rootId: number | null;
  private nextId: number;
  public maxDepth: number;

  constructor() {
    this.nodes = new Map();
    this.rootId = null;
    this.nextId = 0;
    this.maxDepth = 0;
  }

  /**
   * Create root node and return its ID.
   *
   * @param content Content for root node
   * @param metadata Optional metadata object
   * @returns Root node ID
   *
   * @example
   * ```typescript
   * const tree = new ReasoningTree();
   * const rootId = tree.createRoot('What is 2+2?', { query: true });
   * ```
   */
  createRoot(content: string, metadata: Record<string, unknown> = {}): number {
    const nodeId = this.nextId;
    this.nextId += 1;

    const node: ReasoningNode = {
      id: nodeId,
      content,
      parentId: null,
      childrenIds: [],
      depth: 0,
      score: 0.0,
      state: NodeState.Open,
      metadata,
    };

    this.nodes.set(nodeId, node);
    this.rootId = nodeId;
    return nodeId;
  }

  /**
   * Add child node to parent and return child ID.
   *
   * @param parentId ID of parent node
   * @param content Content for new child node
   * @param score Evaluation score for child (0.0-1.0)
   * @param metadata Optional metadata object
   * @returns New child node ID
   * @throws Error if parent node not found
   *
   * @example
   * ```typescript
   * const childId = tree.addChild(rootId, 'Step 1: analyze problem', 0.9);
   * ```
   */
  addChild(
    parentId: number,
    content: string,
    score: number = 0.0,
    metadata: Record<string, unknown> = {},
  ): number {
    const parent = this.nodes.get(parentId);
    if (!parent) {
      throw new Error(`Parent node ${parentId} not found`);
    }

    const childId = this.nextId;
    this.nextId += 1;

    const child: ReasoningNode = {
      id: childId,
      content,
      parentId,
      childrenIds: [],
      depth: parent.depth + 1,
      score,
      state: NodeState.Open,
      metadata,
    };

    this.nodes.set(childId, child);
    parent.childrenIds.push(childId);

    // Update max depth
    if (child.depth > this.maxDepth) {
      this.maxDepth = child.depth;
    }

    return childId;
  }

  /**
   * Get node by ID.
   *
   * @param nodeId Node ID to retrieve
   * @returns Node or undefined if not found
   */
  getNode(nodeId: number): ReasoningNode | undefined {
    return this.nodes.get(nodeId);
  }

  /**
   * Get all children of a node.
   *
   * @param nodeId Parent node ID
   * @returns Array of child nodes
   */
  getChildren(nodeId: number): ReasoningNode[] {
    const node = this.nodes.get(nodeId);
    if (!node) {
      return [];
    }

    return node.childrenIds
      .map((childId) => this.nodes.get(childId))
      .filter((child): child is ReasoningNode => child !== undefined);
  }

  /**
   * Get path from root to node.
   *
   * @param nodeId Target node ID
   * @returns Array of nodes from root to target (inclusive)
   *
   * @example
   * ```typescript
   * const path = tree.getPath(leafNodeId);
   * console.log(`Path length: ${path.length}`);
   * ```
   */
  getPath(nodeId: number): ReasoningNode[] {
    const path: ReasoningNode[] = [];
    let currentId: number | null = nodeId;

    while (currentId !== null) {
      const node = this.nodes.get(currentId);
      if (!node) {
        break;
      }
      path.unshift(node);
      currentId = node.parentId;
    }

    return path;
  }

  /**
   * Get concatenated text of path from root to node.
   *
   * @param nodeId Target node ID
   * @param delimiter Delimiter between steps (default: "\n")
   * @returns Concatenated path text
   *
   * @example
   * ```typescript
   * const pathText = tree.getPathText(leafId, ' -> ');
   * console.log(pathText);
   * ```
   */
  getPathText(nodeId: number, delimiter: string = '\n'): string {
    const path = this.getPath(nodeId);
    return path.map((node) => node.content).join(delimiter);
  }

  /**
   * Get all leaf nodes (nodes with no children).
   *
   * @returns Array of leaf nodes
   */
  getLeaves(): ReasoningNode[] {
    return Array.from(this.nodes.values()).filter((node) => node.childrenIds.length === 0);
  }

  /**
   * Get leaf node with highest score.
   *
   * @returns Best leaf node or undefined if no leaves exist
   *
   * @example
   * ```typescript
   * const bestLeaf = tree.getBestLeaf();
   * if (bestLeaf) {
   *   console.log(`Best score: ${bestLeaf.score}`);
   * }
   * ```
   */
  getBestLeaf(): ReasoningNode | undefined {
    const leaves = this.getLeaves();
    if (leaves.length === 0) {
      return undefined;
    }

    return leaves.reduce((best, current) => (current.score > best.score ? current : best));
  }

  /**
   * Mark node as pruned.
   *
   * @param nodeId ID of node to prune
   *
   * @example
   * ```typescript
   * if (node.score < threshold) {
   *   tree.pruneNode(node.id);
   * }
   * ```
   */
  pruneNode(nodeId: number): void {
    const node = this.nodes.get(nodeId);
    if (node) {
      node.state = NodeState.Pruned;
    }
  }

  /**
   * Get tree statistics.
   *
   * @returns Statistics object with counts and scores
   *
   * @example
   * ```typescript
   * const stats = tree.getStatistics();
   * console.log(`Total nodes: ${stats.totalNodes}`);
   * console.log(`Best score: ${stats.bestScore}`);
   * ```
   */
  getStatistics(): TreeStatistics {
    const leaves = this.getLeaves();
    const evaluated = Array.from(this.nodes.values()).filter(
      (n) => n.state === NodeState.Evaluated,
    );
    const pruned = Array.from(this.nodes.values()).filter((n) => n.state === NodeState.Pruned);

    const avgScore =
      leaves.length > 0 ? leaves.reduce((sum, n) => sum + n.score, 0) / leaves.length : 0.0;

    const bestScore = leaves.length > 0 ? Math.max(...leaves.map((n) => n.score)) : 0.0;

    return {
      totalNodes: this.nodes.size,
      maxDepth: this.maxDepth,
      numLeaves: leaves.length,
      numEvaluated: evaluated.length,
      numPruned: pruned.length,
      avgScore,
      bestScore,
    };
  }

  /**
   * Check if a node is a leaf (has no children).
   *
   * @param nodeId Node ID to check
   * @returns True if node is a leaf
   */
  isLeaf(nodeId: number): boolean {
    const node = this.nodes.get(nodeId);
    return node ? node.childrenIds.length === 0 : false;
  }

  /**
   * Check if a node is the root (has no parent).
   *
   * @param nodeId Node ID to check
   * @returns True if node is the root
   */
  isRoot(nodeId: number): boolean {
    const node = this.nodes.get(nodeId);
    return node ? node.parentId === null : false;
  }

  /**
   * Get the root node ID.
   *
   * @returns Root node ID or null if tree is empty
   */
  getRootId(): number | null {
    return this.rootId;
  }

  /**
   * Get total number of nodes in tree.
   *
   * @returns Node count
   */
  size(): number {
    return this.nodes.size;
  }
}
