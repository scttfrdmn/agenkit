/**
 * Collaborative Pattern
 *
 * Implements peer-to-peer agent collaboration with iterative refinement.
 * Multiple agents work together, each contributing their perspective and
 * refining the collective output through rounds.
 *
 * Key concepts:
 * - Peer-to-peer collaboration (no hierarchy)
 * - Iterative refinement through rounds
 * - Consensus detection or max rounds limit
 * - Each agent sees all previous responses
 *
 * Performance characteristics:
 * - Time: O(rounds * n agents) worst case
 * - Memory: O(rounds * n agents * message size)
 * - Early termination on consensus
 *
 * Example use cases:
 * - Code review: multiple reviewers provide feedback
 * - Document editing: iterative improvements from editors
 * - Decision making: collaborative analysis and consensus
 * - Creative writing: multiple perspectives and refinement
 * - Research: peer review and iteration
 *
 * Example:
 * ```typescript
 * const collaborative = new CollaborativeAgent({
 *   agents: [reviewer1, reviewer2, reviewer3],
 *   maxRounds: 3,
 *   consensusFunc: DefaultConsensusFunc.majorityAgreement,
 *   mergeFunc: DefaultMergeFunc.vote
 * });
 *
 * const result = await collaborative.process(
 *   createMessage('user', 'Review this code')
 * );
 * // Agents collaborate through multiple rounds until consensus
 * ```
 */

import { Agent, Message, createMessage } from '../core/interfaces';

/**
 * Function that determines if agents have reached consensus.
 *
 * Common strategies include:
 * - Content similarity threshold
 * - Voting on same answer
 * - Agreement indicators in responses
 * - Convergence metrics
 */
export type ConsensusFunc = (messages: Message[]) => boolean;

/**
 * Function that combines multiple agent responses into a single result.
 *
 * Common strategies include:
 * - Voting/majority rule
 * - Weighted combination
 * - Concatenation with synthesis
 * - Best response selection
 */
export type MergeFunc = (messages: Message[]) => Message;

/**
 * Configuration for CollaborativeAgent.
 */
export interface CollaborativeConfig {
  /** Agents participating in collaboration */
  agents: Agent[];
  /** MaxRounds limits iteration (default: 3) */
  maxRounds?: number;
  /** ConsensusFunc detects agreement (optional) */
  consensusFunc?: ConsensusFunc;
  /** MergeFunc combines responses (required) */
  mergeFunc: MergeFunc;
}

/**
 * Round result information.
 */
interface RoundResult {
  /** Round number */
  round: number;
  /** Agent responses in this round */
  responses: Message[];
  /** Whether consensus was reached */
  consensus: boolean;
}

/**
 * Collaborative agent that enables peer collaboration with iterative refinement.
 *
 * Agents work together in rounds, each seeing previous responses and
 * contributing refinements. The process continues until consensus is
 * reached or maximum rounds are exhausted.
 *
 * The collaborative pattern is ideal when multiple perspectives improve
 * output quality through discussion and refinement.
 *
 * @example
 * ```typescript
 * const collaborative = new CollaborativeAgent({
 *   agents: [expertA, expertB, expertC],
 *   maxRounds: 5,
 *   consensusFunc: DefaultConsensusFunc.exactMatch,
 *   mergeFunc: DefaultMergeFunc.concatenate
 * });
 *
 * const result = await collaborative.process(
 *   createMessage('user', 'Solve this problem')
 * );
 * ```
 */
export class CollaborativeAgent implements Agent {
  readonly name = 'CollaborativeAgent';
  private agents: Agent[];
  private maxRounds: number;
  private consensusFunc?: ConsensusFunc;
  private mergeFunc: MergeFunc;

  /**
   * Creates a new collaborative agent.
   *
   * @param config - Configuration with agents and collaboration settings
   * @throws Error if config invalid, less than 2 agents, or merge function missing
   *
   * @example
   * ```typescript
   * const collaborative = new CollaborativeAgent({
   *   agents: [agent1, agent2],
   *   mergeFunc: DefaultMergeFunc.vote
   * });
   * ```
   */
  constructor(config: CollaborativeConfig) {
    if (!config) {
      throw new Error('config is required');
    }
    if (!config.agents || config.agents.length < 2) {
      throw new Error('at least two agents are required for collaboration');
    }
    if (!config.mergeFunc) {
      throw new Error('merge function is required');
    }

    this.agents = config.agents;
    this.maxRounds = config.maxRounds || 3;
    this.consensusFunc = config.consensusFunc;
    this.mergeFunc = config.mergeFunc;
  }

  /**
   * Returns the combined capabilities of all agents.
   */
  get capabilities(): string[] {
    const capSet = new Set<string>();

    for (const agent of this.agents) {
      if (agent.capabilities) {
        for (const cap of agent.capabilities) {
          capSet.add(cap);
        }
      }
    }

    capSet.add('collaborative');
    capSet.add('iterative');
    capSet.add('consensus');

    return Array.from(capSet);
  }

  /**
   * Executes collaborative refinement through multiple rounds.
   *
   * The process follows these steps for each round:
   * 1. Each agent processes the current context (original + previous responses)
   * 2. All responses are collected
   * 3. Consensus is checked (if function provided)
   * 4. If consensus or max rounds, merge and return
   * 5. Otherwise, prepare next round with all responses as context
   *
   * The final message includes metadata about rounds, consensus, and participation.
   *
   * @param message - Input message to process
   * @returns Merged final response
   * @throws Error if message invalid or any agent fails
   *
   * @example
   * ```typescript
   * const result = await collaborative.process(
   *   createMessage('user', 'Collaborate on this')
   * );
   *
   * // Access collaboration metadata
   * console.log(result.metadata?.collaboration_rounds);
   * console.log(result.metadata?.stop_reason);
   * console.log(result.metadata?.rounds);
   * ```
   */
  async process(message: Message): Promise<Message> {
    if (!message) {
      throw new Error('message cannot be nil');
    }

    const rounds: RoundResult[] = [];
    let currentContext: Message[] = [message];

    for (let round = 0; round < this.maxRounds; round++) {
      // Collect responses from all agents
      const responses: Message[] = [];

      for (const agent of this.agents) {
        // Build context message with conversation history
        const contextMsg = this.buildContextMessage(currentContext, round, agent.name);

        // Get agent response
        try {
          const response = await agent.process(contextMsg);
          responses.push(response);
        } catch (error) {
          const errorMsg = error instanceof Error ? error.message : String(error);
          throw new Error(`agent ${agent.name} failed in round ${round}: ${errorMsg}`);
        }
      }

      // Check for consensus
      const hasConsensus = this.consensusFunc ? this.consensusFunc(responses) : false;

      // Record round
      rounds.push({
        round,
        responses,
        consensus: hasConsensus,
      });

      // Stop if consensus reached
      if (hasConsensus) {
        return this.buildFinalResult(rounds, 'consensus');
      }

      // Prepare next round context
      currentContext = [...currentContext, ...responses];
    }

    // Max rounds reached
    return this.buildFinalResult(rounds, 'max_rounds');
  }

  /**
   * Creates a message with full conversation context.
   */
  private buildContextMessage(context: Message[], round: number, agentName: string): Message {
    const parts: string[] = [];

    // Add round information
    parts.push(`=== Collaboration Round ${round} ===`);
    parts.push(`Agent: ${agentName}\n`);

    // Add conversation history
    if (round === 0) {
      parts.push('Original Request:');
      parts.push(String(context[0].content));
    } else {
      parts.push('Original Request:');
      parts.push(String(context[0].content));
      parts.push('\n--- Previous Responses ---\n');

      for (let i = 1; i < context.length; i++) {
        parts.push(`Response ${i}:\n${String(context[i].content)}\n`);
      }

      parts.push('--- Your Turn ---');
      parts.push('Please review the above responses and provide your refined contribution.');
    }

    return createMessage('user', parts.join('\n'));
  }

  /**
   * Merges all responses and adds metadata.
   */
  private buildFinalResult(rounds: RoundResult[], stopReason: string): Message {
    // Collect all responses from final round
    const finalRound = rounds[rounds.length - 1];
    const merged = this.mergeFunc(finalRound.responses);

    // Add collaboration metadata
    if (!merged.metadata) {
      merged.metadata = {};
    }

    merged.metadata.collaboration_rounds = rounds.length;
    merged.metadata.collaboration_agents = this.agents.length;
    merged.metadata.stop_reason = stopReason;

    // Add round details
    const roundDetails = rounds.map((r) => ({
      round: r.round,
      responses: r.responses.length,
      consensus: r.consensus,
    }));
    merged.metadata.rounds = roundDetails;

    return merged;
  }
}

/**
 * Common consensus detection strategies.
 */
export const DefaultConsensusFunc = {
  /**
   * Requires all responses to be identical.
   */
  exactMatch: (messages: Message[]): boolean => {
    if (messages.length <= 1) {
      return true;
    }

    const first = String(messages[0].content);
    for (let i = 1; i < messages.length; i++) {
      if (String(messages[i].content) !== first) {
        return false;
      }
    }
    return true;
  },

  /**
   * Requires responses to be similar (simple string comparison).
   *
   * @param threshold - Similarity threshold (0.0 to 1.0)
   */
  similarityThreshold: (threshold: number): ConsensusFunc => {
    return (messages: Message[]): boolean => {
      if (messages.length <= 1) {
        return true;
      }

      // Simple similarity: compare common words
      // In production, use proper similarity metrics
      const first = String(messages[0].content).toLowerCase();
      for (let i = 1; i < messages.length; i++) {
        const current = String(messages[i].content).toLowerCase();
        const previewLen = Math.min(current.length, 20);
        if (!first.includes(current.substring(0, previewLen))) {
          return false;
        }
      }
      return true;
    };
  },

  /**
   * Requires majority of responses to match.
   */
  majorityAgreement: (messages: Message[]): boolean => {
    if (messages.length <= 1) {
      return true;
    }

    // Count identical responses
    const contentCount = new Map<string, number>();
    for (const msg of messages) {
      const content = String(msg.content);
      contentCount.set(content, (contentCount.get(content) || 0) + 1);
    }

    // Check if any content has majority
    const majority = Math.floor(messages.length / 2) + 1;
    for (const count of Array.from(contentCount.values())) {
      if (count >= majority) {
        return true;
      }
    }

    return false;
  },
};

/**
 * Common merge strategies for combining responses.
 */
export const DefaultMergeFunc = {
  /**
   * Combines all responses with separators.
   */
  concatenate: (messages: Message[]): Message => {
    if (messages.length === 0) {
      return createMessage('assistant', 'No responses to merge');
    }

    const combined = messages
      .map((msg) => String(msg.content))
      .join('\n\n---\n\n');

    return createMessage('assistant', combined);
  },

  /**
   * Returns most common response.
   */
  vote: (messages: Message[]): Message => {
    if (messages.length === 0) {
      return createMessage('assistant', 'No responses to merge');
    }

    // Count votes
    const votes = new Map<string, number>();
    const msgByContent = new Map<string, Message>();

    for (const msg of messages) {
      const content = String(msg.content);
      votes.set(content, (votes.get(content) || 0) + 1);
      msgByContent.set(content, msg);
    }

    // Find winner
    let maxVotes = 0;
    let winner = '';
    for (const [content, count] of Array.from(votes.entries())) {
      if (count > maxVotes) {
        maxVotes = count;
        winner = content;
      }
    }

    const result = msgByContent.get(winner)!;
    if (!result.metadata) {
      result.metadata = {};
    }
    result.metadata.votes = maxVotes;
    result.metadata.total = messages.length;

    return result;
  },

  /**
   * Returns first response.
   */
  first: (messages: Message[]): Message => {
    if (messages.length === 0) {
      return createMessage('assistant', 'No responses to merge');
    }
    return messages[0];
  },

  /**
   * Returns last response.
   */
  last: (messages: Message[]): Message => {
    if (messages.length === 0) {
      return createMessage('assistant', 'No responses to merge');
    }
    return messages[messages.length - 1];
  },
};
