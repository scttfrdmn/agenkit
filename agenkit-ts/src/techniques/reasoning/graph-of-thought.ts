/**
 * Graph-of-Thought Reasoning Technique
 *
 * Represents reasoning as a directed graph where nodes are thoughts/conclusions
 * and edges represent logical connections. More flexible than tree-based
 * approaches, allows for complex multi-hop reasoning and thought combination.
 *
 * This technique is particularly effective for:
 * - Multi-hop reasoning problems
 * - Problems with multiple interconnected concepts
 * - Situations requiring synthesis of multiple reasoning chains
 *
 * Reference:
 * - Paper: https://arxiv.org/abs/2308.09687
 * - "Graph of Thoughts: Solving Elaborate Problems with Large Language Models"
 *
 * @example
 * ```typescript
 * import { GraphOfThought } from '@agenkit/core/techniques/reasoning';
 * import { Message } from '@agenkit/core';
 *
 * const agent = new GraphOfThought(baseLLM, {
 *   maxNodes: 20,
 *   maxEdges: 40,
 *   aggregator: 'path_based',
 * });
 *
 * const response = await agent.process(new Message({
 *   role: 'user',
 *   content: 'Multi-hop reasoning problem...',
 * }));
 *
 * // Access reasoning graph
 * const graph = response.metadata.graph;
 * const paths = response.metadata.reasoningPaths;
 * ```
 */

import type { Agent, Message } from '../../core/interfaces';
import {
  EdgeType,
  NodeType,
  ReasoningGraph,
  ThoughtNode,
} from './reasoning-graph';

/**
 * Aggregation strategy for combining reasoning paths.
 */
export type AggregatorType = 'path_based' | 'node_based';

/**
 * Configuration options for GraphOfThought agent.
 */
export interface GraphOfThoughtConfig {
  /** Maximum number of nodes in reasoning graph */
  maxNodes?: number;
  /** Maximum number of edges in reasoning graph */
  maxEdges?: number;
  /** Aggregation strategy for combining paths */
  aggregator?: AggregatorType;
  /** Whether to allow cycles in reasoning graph */
  allowCycles?: boolean;
}

/**
 * Graph-of-Thought reasoning technique.
 *
 * Builds a directed graph of reasoning steps, explores connections,
 * and aggregates multiple reasoning paths to reach conclusions.
 *
 * This technique is particularly effective for:
 * - Multi-hop reasoning with complex dependencies
 * - Problems requiring synthesis of multiple chains of thought
 * - Situations where thoughts may support, contradict, or refine each other
 * - Complex knowledge integration tasks
 */
export class GraphOfThought implements Agent {
  private readonly llm: Agent;
  private readonly maxNodes: number;
  private readonly maxEdges: number;
  private readonly aggregator: AggregatorType;
  private readonly allowCycles: boolean;

  /**
   * Create a new GraphOfThought agent.
   *
   * @param llm - LLM agent for generating responses
   * @param config - Configuration options
   *
   * @example
   * ```typescript
   * const agent = new GraphOfThought(baseLLM, {
   *   maxNodes: 20,
   *   aggregator: 'path_based',
   * });
   * ```
   */
  constructor(llm: Agent, config: GraphOfThoughtConfig = {}) {
    this.llm = llm;
    this.maxNodes = config.maxNodes ?? 20;
    this.maxEdges = config.maxEdges ?? 40;
    this.aggregator = config.aggregator ?? 'path_based';
    this.allowCycles = config.allowCycles ?? false;
  }

  /**
   * Agent name.
   */
  get name(): string {
    return 'graph_of_thought';
  }

  /**
   * Agent capabilities.
   */
  get capabilities(): string[] {
    return [
      'reasoning',
      'graph_reasoning',
      'multi_hop',
      'path_aggregation',
      'graph_of_thought',
    ];
  }

  /**
   * Call LLM with prompt.
   */
  private async llmCall(prompt: string): Promise<string> {
    const response = await this.llm.process({
      role: 'user',
      content: prompt,
    });
    return String(response.content);
  }

  /**
   * Generate initial premises/facts for the problem.
   *
   * @param problem - Problem to generate premises for
   * @returns Array of premise statements
   */
  private async generatePremises(problem: string): Promise<string[]> {
    const prompt = `Identify the key facts and premises for this problem.
List 2-4 foundational facts or assumptions, one per line.

Problem: ${problem}

Premises:`;

    const response = await this.llmCall(prompt);

    // Parse premises
    const premises: string[] = [];
    for (const line of response.trim().split('\n')) {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#')) {
        // Remove numbering and bullets
        const cleaned = trimmed.replace(/^[•\-*\d]+[.)\\s]*/, '').trim();
        if (cleaned) {
          premises.push(cleaned);
        }
      }
    }

    return premises.slice(0, 4); // Limit to 4 premises
  }

  /**
   * Generate new intermediate thoughts based on existing ones.
   *
   * @param problem - Original problem
   * @param existingThoughts - List of existing thoughts
   * @param maxNew - Maximum number of new thoughts to generate
   * @returns Array of new thought statements
   */
  private async generateThoughts(
    problem: string,
    existingThoughts: string[],
    maxNew = 3
  ): Promise<string[]> {
    let prompt: string;

    if (existingThoughts.length > 0) {
      const context = existingThoughts.map((t) => `- ${t}`).join('\n');
      prompt = `Given this problem and existing thoughts, generate ${maxNew} new insights or conclusions.

Problem: ${problem}

Existing thoughts:
${context}

New thoughts (one per line):`;
    } else {
      prompt = `Generate ${maxNew} initial thoughts or insights about this problem.

Problem: ${problem}

Thoughts (one per line):`;
    }

    const response = await this.llmCall(prompt);

    // Parse new thoughts
    const thoughts: string[] = [];
    for (const line of response.trim().split('\n')) {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#')) {
        const cleaned = trimmed.replace(/^[•\-*\d]+[.)\\s]*/, '').trim();
        if (cleaned && thoughts.length < maxNew) {
          thoughts.push(cleaned);
        }
      }
    }

    return thoughts;
  }

  /**
   * Identify logical connection between two thoughts.
   *
   * @param thought1 - First thought
   * @param thought2 - Second thought
   * @returns EdgeType if connection exists, null otherwise
   */
  private async identifyConnection(
    thought1: string,
    thought2: string
  ): Promise<EdgeType | null> {
    const prompt = `Analyze the logical relationship between these two statements.

Statement 1: ${thought1}

Statement 2: ${thought2}

Does statement 2:
- SUPPORT statement 1 (provides evidence or reasoning for it)
- DEPEND on statement 1 (requires it to be true)
- CONTRADICT statement 1 (conflicts with it)
- REFINE statement 1 (improves or clarifies it)
- NO_RELATION (no clear logical connection)

Answer with one word: SUPPORT, DEPEND, CONTRADICT, REFINE, or NO_RELATION`;

    const response = await this.llmCall(prompt);
    const responseUpper = response.trim().toUpperCase();

    if (responseUpper.includes('SUPPORT')) {
      return EdgeType.SUPPORTS;
    } else if (responseUpper.includes('DEPEND')) {
      return EdgeType.DEPENDS_ON;
    } else if (responseUpper.includes('CONTRADICT')) {
      return EdgeType.CONTRADICTS;
    } else if (responseUpper.includes('REFINE')) {
      return EdgeType.REFINES;
    }

    return null;
  }

  /**
   * Build reasoning graph for the problem.
   *
   * @param problem - Problem to build graph for
   * @returns Constructed ReasoningGraph
   */
  private async buildGraph(problem: string): Promise<ReasoningGraph> {
    const graph = new ReasoningGraph();

    // Step 1: Generate premises
    const premises = await this.generatePremises(problem);
    const premiseIds: number[] = [];
    for (const premise of premises) {
      const nodeId = graph.addNode(premise, NodeType.PREMISE, 0.9);
      premiseIds.push(nodeId);
    }

    // Step 2: Generate intermediate thoughts
    const allThoughts = [...premises];
    const nodeIds = [...premiseIds];

    while (graph.getNodes().length < this.maxNodes) {
      // Generate new thoughts based on existing ones
      const maxNew = Math.min(3, this.maxNodes - graph.getNodes().length);
      if (maxNew <= 0) {
        break;
      }

      const newThoughts = await this.generateThoughts(
        problem,
        allThoughts,
        maxNew
      );

      if (newThoughts.length === 0) {
        break;
      }

      // Add new thoughts as intermediate nodes
      for (const thought of newThoughts) {
        if (graph.getNodes().length >= this.maxNodes) {
          break;
        }

        const nodeId = graph.addNode(thought, NodeType.INTERMEDIATE, 0.7);
        allThoughts.push(thought);
        nodeIds.push(nodeId);
      }
    }

    // Step 3: Identify connections between thoughts
    let edgeCount = 0;
    for (let i = 0; i < nodeIds.length; i++) {
      for (let j = i + 1; j < nodeIds.length; j++) {
        if (edgeCount >= this.maxEdges) {
          break;
        }

        const node1Id = nodeIds[i];
        const node2Id = nodeIds[j];

        const thought1 = graph.getNode(node1Id)!.content;
        const thought2 = graph.getNode(node2Id)!.content;

        // Check connection from node1 to node2
        const edgeType = await this.identifyConnection(thought1, thought2);
        if (edgeType) {
          graph.addEdge(node1Id, node2Id, edgeType, 0.8);
          edgeCount++;
        }
      }

      if (edgeCount >= this.maxEdges) {
        break;
      }
    }

    // Step 4: Generate final conclusion
    if (graph.getNodes().length < this.maxNodes) {
      const conclusionPrompt = `Based on all these thoughts, what is the final conclusion?

Problem: ${problem}

Thoughts:
${allThoughts.map((t) => `- ${t}`).join('\n')}

Final conclusion:`;

      const conclusion = await this.llmCall(conclusionPrompt);
      const conclusionId = graph.addNode(
        conclusion.trim(),
        NodeType.CONCLUSION,
        0.8
      );

      // Connect conclusion to recent thoughts
      const recentIds = nodeIds.slice(-3);
      for (const recentId of recentIds) {
        if (edgeCount < this.maxEdges) {
          graph.addEdge(recentId, conclusionId, EdgeType.SUPPORTS, 0.9);
          edgeCount++;
        }
      }
    }

    return graph;
  }

  /**
   * Find reasoning paths from premises to conclusions.
   *
   * @param graph - Reasoning graph
   * @returns Array of paths (each path is array of node IDs)
   */
  private findReasoningPaths(graph: ReasoningGraph): number[][] {
    const premises = graph.getPremises().map((n) => n.id);
    const conclusions = graph.getConclusions().map((n) => n.id);

    const allPaths: number[][] = [];
    for (const premiseId of premises) {
      for (const conclusionId of conclusions) {
        const paths = graph.findPaths(premiseId, conclusionId, 6);
        allPaths.push(...paths);
      }
    }

    return allPaths;
  }

  /**
   * Aggregate multiple reasoning paths into final answer.
   *
   * @param graph - Reasoning graph
   * @param paths - List of reasoning paths
   * @returns Final aggregated answer
   */
  private aggregatePaths(
    graph: ReasoningGraph,
    paths: number[][]
  ): string {
    if (paths.length === 0) {
      // No paths found - use conclusion nodes directly
      const conclusions = graph.getConclusions();
      if (conclusions.length > 0) {
        return conclusions[0].content;
      }
      // Fallback to any node
      const nodes = graph.getNodes();
      if (nodes.length > 0) {
        return nodes[nodes.length - 1].content;
      }
      return 'Unable to reach conclusion';
    }

    if (this.aggregator === 'path_based') {
      // Aggregate by considering complete paths
      // Find highest scoring path
      const bestPath = paths.reduce((best, path) => {
        const pathScore = graph.getPathScore(path);
        const bestScore = graph.getPathScore(best);
        return pathScore > bestScore ? path : best;
      });

      // Get conclusion from best path
      const conclusionNode = graph.getNode(bestPath[bestPath.length - 1])!;
      return conclusionNode.content;
    } else if (this.aggregator === 'node_based') {
      // Aggregate by considering individual nodes
      // Count node appearances across paths
      const nodeCounts = new Map<number, number>();
      for (const path of paths) {
        for (const nodeId of path) {
          nodeCounts.set(nodeId, (nodeCounts.get(nodeId) || 0) + 1);
        }
      }

      // Weight by confidence
      const nodeScores = new Map<number, number>();
      for (const [nodeId, count] of nodeCounts.entries()) {
        const node = graph.getNode(nodeId)!;
        nodeScores.set(nodeId, count * node.confidence);
      }

      // Return highest scoring node's content
      let bestNodeId = 0;
      let bestScore = -1;
      for (const [nodeId, score] of nodeScores.entries()) {
        if (score > bestScore) {
          bestScore = score;
          bestNodeId = nodeId;
        }
      }

      return graph.getNode(bestNodeId)!.content;
    }

    throw new Error(`Unknown aggregator: ${this.aggregator}`);
  }

  /**
   * Process message with Graph-of-Thought reasoning.
   *
   * Builds a reasoning graph, finds paths, and aggregates them
   * into a final answer.
   *
   * @param message - Input message with problem
   * @returns Message with final answer and metadata
   *
   * Metadata includes:
   * - graph: The reasoning graph
   * - reasoningPaths: List of reasoning paths
   * - numNodes: Number of nodes in graph
   * - numEdges: Number of edges in graph
   * - hasCycles: Whether graph contains cycles
   * - aggregator: Aggregation strategy used
   * - technique: Always "graph_of_thought"
   *
   * @example
   * ```typescript
   * const response = await agent.process(new Message({
   *   role: 'user',
   *   content: 'Complex reasoning problem',
   * }));
   *
   * console.log(response.metadata.numNodes);
   * console.log(response.metadata.reasoningPaths);
   * ```
   */
  async process(message: Message): Promise<Message> {
    const problem = String(message.content);

    // Step 1: Build reasoning graph
    const graph = await this.buildGraph(problem);

    // Step 2: Check for cycles (if not allowed)
    if (!this.allowCycles && graph.hasCycle()) {
      // For now, just continue - cycles detected but not removed
      // Could implement cycle removal in future
    }

    // Step 3: Find reasoning paths
    const reasoningPaths = this.findReasoningPaths(graph);

    // Step 4: Aggregate paths to final answer
    const finalAnswer = this.aggregatePaths(graph, reasoningPaths);

    // Get statistics
    const stats = graph.statistics();

    return {
      role: 'assistant',
      content: finalAnswer,
      metadata: {
        technique: 'graph_of_thought',
        graph,
        reasoningPaths,
        numNodes: stats.numNodes,
        numEdges: stats.numEdges,
        hasCycles: stats.hasCycles,
        nodeTypes: stats.nodeTypes,
        edgeTypes: stats.edgeTypes,
        aggregator: this.aggregator,
      },
    };
  }
}
