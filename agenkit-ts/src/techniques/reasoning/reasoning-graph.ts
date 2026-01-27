/**
 * Reasoning Graph Data Structure for Graph-of-Thought
 *
 * Provides a directed graph structure for representing reasoning as nodes
 * (thoughts/conclusions) connected by edges (logical relationships).
 *
 * This is more flexible than tree-based approaches, allowing for:
 * - Multiple reasoning paths
 * - Complex dependencies
 * - Cycle detection for circular reasoning
 * - Path aggregation
 *
 * Reference:
 * - Graph-of-Thought paper: https://arxiv.org/abs/2308.09687
 */

/**
 * Type of thought node in the graph.
 */
export enum NodeType {
  /** Starting assumption or fact */
  PREMISE = 'premise',
  /** Intermediate conclusion */
  INTERMEDIATE = 'intermediate',
  /** Final conclusion */
  CONCLUSION = 'conclusion',
}

/**
 * Type of logical connection between nodes.
 */
export enum EdgeType {
  /** Node supports another */
  SUPPORTS = 'supports',
  /** Node depends on another */
  DEPENDS_ON = 'depends_on',
  /** Node contradicts another */
  CONTRADICTS = 'contradicts',
  /** Node refines/improves another */
  REFINES = 'refines',
}

/**
 * A single thought or conclusion in the reasoning graph.
 */
export interface ThoughtNode {
  /** Unique node identifier */
  id: number;
  /** Thought/conclusion text */
  content: string;
  /** Type of node */
  nodeType: NodeType;
  /** Confidence score (0.0-1.0) */
  confidence: number;
  /** Additional node-specific data */
  metadata?: Record<string, unknown>;
}

/**
 * A logical connection between two thoughts.
 */
export interface LogicalEdge {
  /** Source node ID */
  fromNode: number;
  /** Target node ID */
  toNode: number;
  /** Type of logical connection */
  edgeType: EdgeType;
  /** Connection strength (0.0-1.0) */
  strength: number;
  /** Additional edge-specific data */
  metadata?: Record<string, unknown>;
}

/**
 * Graph statistics for analysis.
 */
export interface GraphStatistics {
  /** Number of nodes in graph */
  numNodes: number;
  /** Number of edges in graph */
  numEdges: number;
  /** Whether graph contains cycles */
  hasCycles: boolean;
  /** Count of each node type */
  nodeTypes: Record<NodeType, number>;
  /** Count of each edge type */
  edgeTypes: Record<EdgeType, number>;
}

/**
 * Directed graph for representing reasoning structures.
 *
 * Nodes represent thoughts, conclusions, or premises.
 * Edges represent logical connections and dependencies.
 *
 * Supports:
 * - Adding nodes and edges
 * - Path finding between nodes
 * - Cycle detection
 * - Graph statistics
 */
export class ReasoningGraph {
  private nodes: Map<number, ThoughtNode> = new Map();
  private edges: LogicalEdge[] = [];
  private nextId = 0;

  // Adjacency lists for efficient traversal
  private outgoing: Map<number, number[]> = new Map();
  private incoming: Map<number, number[]> = new Map();

  /**
   * Add a thought node to the graph.
   *
   * @param content - The thought/conclusion content
   * @param nodeType - Type of node (premise, intermediate, conclusion)
   * @param confidence - Confidence score 0.0 to 1.0
   * @param metadata - Optional metadata
   * @returns Node ID
   */
  addNode(
    content: string,
    nodeType: NodeType,
    confidence = 1.0,
    metadata?: Record<string, unknown>
  ): number {
    const nodeId = this.nextId++;

    const node: ThoughtNode = {
      id: nodeId,
      content,
      nodeType,
      confidence,
      metadata: metadata || {},
    };

    this.nodes.set(nodeId, node);
    this.outgoing.set(nodeId, []);
    this.incoming.set(nodeId, []);

    return nodeId;
  }

  /**
   * Add a logical edge between two nodes.
   *
   * @param fromNode - Source node ID
   * @param toNode - Target node ID
   * @param edgeType - Type of logical connection
   * @param strength - Connection strength 0.0 to 1.0
   * @param metadata - Optional metadata
   */
  addEdge(
    fromNode: number,
    toNode: number,
    edgeType: EdgeType,
    strength = 1.0,
    metadata?: Record<string, unknown>
  ): void {
    if (!this.nodes.has(fromNode) || !this.nodes.has(toNode)) {
      throw new Error('Both nodes must exist in graph');
    }

    const edge: LogicalEdge = {
      fromNode,
      toNode,
      edgeType,
      strength,
      metadata: metadata || {},
    };

    this.edges.push(edge);
    this.outgoing.get(fromNode)!.push(toNode);
    this.incoming.get(toNode)!.push(fromNode);
  }

  /**
   * Get node by ID.
   *
   * @param nodeId - Node ID
   * @returns Node or undefined if not found
   */
  getNode(nodeId: number): ThoughtNode | undefined {
    return this.nodes.get(nodeId);
  }

  /**
   * Get all premise nodes.
   *
   * @returns Array of premise nodes
   */
  getPremises(): ThoughtNode[] {
    return Array.from(this.nodes.values()).filter(
      (n) => n.nodeType === NodeType.PREMISE
    );
  }

  /**
   * Get all conclusion nodes.
   *
   * @returns Array of conclusion nodes
   */
  getConclusions(): ThoughtNode[] {
    return Array.from(this.nodes.values()).filter(
      (n) => n.nodeType === NodeType.CONCLUSION
    );
  }

  /**
   * Find all paths from start to end node.
   *
   * @param start - Start node ID
   * @param end - End node ID
   * @param maxLength - Maximum path length
   * @returns Array of paths (each path is array of node IDs)
   */
  findPaths(start: number, end: number, maxLength = 10): number[][] {
    const paths: number[][] = [];
    const visited = new Set<number>();

    const dfs = (current: number, path: number[]): void => {
      if (path.length > maxLength) {
        return;
      }

      if (current === end) {
        paths.push([...path, current]);
        return;
      }

      if (visited.has(current)) {
        return;
      }

      visited.add(current);
      path.push(current);

      const neighbors = this.outgoing.get(current) || [];
      for (const neighbor of neighbors) {
        dfs(neighbor, path);
      }

      path.pop();
      visited.delete(current);
    };

    dfs(start, []);
    return paths;
  }

  /**
   * Check if graph contains cycles.
   *
   * @returns True if cycles detected
   */
  hasCycle(): boolean {
    const visited = new Set<number>();
    const recStack = new Set<number>();

    const hasCycleDFS = (nodeId: number): boolean => {
      visited.add(nodeId);
      recStack.add(nodeId);

      const neighbors = this.outgoing.get(nodeId) || [];
      for (const neighbor of neighbors) {
        if (!visited.has(neighbor)) {
          if (hasCycleDFS(neighbor)) {
            return true;
          }
        } else if (recStack.has(neighbor)) {
          return true;
        }
      }

      recStack.delete(nodeId);
      return false;
    };

    for (const nodeId of this.nodes.keys()) {
      if (!visited.has(nodeId)) {
        if (hasCycleDFS(nodeId)) {
          return true;
        }
      }
    }

    return false;
  }

  /**
   * Calculate score for a reasoning path.
   *
   * @param path - Array of node IDs
   * @returns Path score (higher is better)
   */
  getPathScore(path: number[]): number {
    let score = 0;

    // Add confidence scores
    for (const nodeId of path) {
      const node = this.nodes.get(nodeId);
      if (node) {
        score += node.confidence;
      }
    }

    // Add edge strengths
    for (let i = 0; i < path.length - 1; i++) {
      const fromNode = path[i];
      const toNode = path[i + 1];

      const edge = this.edges.find(
        (e) => e.fromNode === fromNode && e.toNode === toNode
      );

      if (edge) {
        score += edge.strength;
      }
    }

    return score;
  }

  /**
   * Get graph statistics for analysis.
   *
   * @returns Graph statistics
   */
  statistics(): GraphStatistics {
    const nodeTypes: Record<NodeType, number> = {
      [NodeType.PREMISE]: 0,
      [NodeType.INTERMEDIATE]: 0,
      [NodeType.CONCLUSION]: 0,
    };

    const edgeTypes: Record<EdgeType, number> = {
      [EdgeType.SUPPORTS]: 0,
      [EdgeType.DEPENDS_ON]: 0,
      [EdgeType.CONTRADICTS]: 0,
      [EdgeType.REFINES]: 0,
    };

    for (const node of this.nodes.values()) {
      nodeTypes[node.nodeType]++;
    }

    for (const edge of this.edges) {
      edgeTypes[edge.edgeType]++;
    }

    return {
      numNodes: this.nodes.size,
      numEdges: this.edges.length,
      hasCycles: this.hasCycle(),
      nodeTypes,
      edgeTypes,
    };
  }

  /**
   * Get all nodes in the graph.
   *
   * @returns Array of all nodes
   */
  getNodes(): ThoughtNode[] {
    return Array.from(this.nodes.values());
  }

  /**
   * Get all edges in the graph.
   *
   * @returns Array of all edges
   */
  getEdges(): LogicalEdge[] {
    return [...this.edges];
  }
}
