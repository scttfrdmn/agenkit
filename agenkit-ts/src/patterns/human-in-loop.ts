/**
 * Human-in-Loop Pattern
 *
 * Implements agent execution with human approval for high-stakes decisions.
 * When agent confidence is below a threshold, human approval is requested
 * before proceeding.
 *
 * Key concepts:
 * - Confidence-based approval gates
 * - Human oversight for critical decisions
 * - Configurable approval thresholds
 * - Callback-based approval mechanism
 *
 * Performance characteristics:
 * - Time: O(agent) + human response time (when approval needed)
 * - Memory: O(1) for message passing
 * - Blocking on human input when required
 *
 * Example use cases:
 * - Financial trading: approve large transactions
 * - Content moderation: verify edge cases
 * - Healthcare: approve treatment recommendations
 * - Legal: review contract changes
 * - Security: approve access grants
 *
 * Example:
 * ```typescript
 * const humanInLoop = new HumanInLoopAgent({
 *   agent: tradingAgent,
 *   approvalThreshold: 0.8,
 *   approvalFunc: async (request) => {
 *     // Prompt user for approval
 *     const approved = await promptUser(request);
 *     return { approved };
 *   }
 * });
 *
 * const result = await humanInLoop.process(
 *   createMessage('user', 'Execute large trade')
 * );
 * // Requires approval if confidence < 0.8
 * ```
 */

import { Agent, Message, createMessage } from '../core/interfaces';

/**
 * Information about a pending approval decision.
 */
export interface ApprovalRequest {
  /** Agent's proposed response */
  message: Message;
  /** Agent's confidence level (0.0 to 1.0) */
  confidence: number;
  /** Additional decision context */
  context: Record<string, unknown>;
  /** Timestamp when approval was requested */
  timestamp: string;
}

/**
 * Human's decision on approval request.
 */
export interface ApprovalResponse {
  /** Whether the action is approved */
  approved: boolean;
  /** Optional human feedback */
  feedback?: string;
  /** Optional modified version (if approved with changes) */
  modifiedMessage?: Message;
}

/**
 * Function called when human approval is needed.
 *
 * The function receives an approval request and should return the human's
 * decision. This can be synchronous (blocking for user input) or asynchronous
 * (using a queue/callback system).
 */
export type ApprovalFunc = (request: ApprovalRequest) => Promise<ApprovalResponse>;

/**
 * Configuration for HumanInLoopAgent.
 */
export interface HumanInLoopConfig {
  /** Agent to wrap with human approval */
  agent: Agent;
  /** ApprovalThreshold for requiring approval (0.0 to 1.0, default: 0.8) */
  approvalThreshold?: number;
  /** ApprovalFunc is called when approval is needed */
  approvalFunc: ApprovalFunc;
  /** ConfidenceKey specifies metadata key for confidence (default: "confidence") */
  confidenceKey?: string;
}

/**
 * Human-in-loop agent that wraps an agent with human approval gates.
 *
 * The agent executes normally, but when confidence is below the threshold,
 * human approval is requested before returning the response. This provides
 * oversight for high-stakes decisions while allowing autonomous operation
 * for routine tasks.
 *
 * The human-in-loop pattern is ideal when autonomous operation needs
 * human oversight for critical or uncertain decisions.
 *
 * @example
 * ```typescript
 * const humanInLoop = new HumanInLoopAgent({
 *   agent: myAgent,
 *   approvalThreshold: 0.7,
 *   approvalFunc: async (request) => ({
 *     approved: await getUserApproval(request),
 *     feedback: 'Looks good'
 *   })
 * });
 *
 * const result = await humanInLoop.process(
 *   createMessage('user', 'Critical decision')
 * );
 * ```
 */
export class HumanInLoopAgent implements Agent {
  readonly name = 'HumanInLoopAgent';
  private agent: Agent;
  private approvalThreshold: number;
  private approvalFunc: ApprovalFunc;
  private confidenceKey: string;

  /**
   * Creates a new human-in-loop agent.
   *
   * @param config - Configuration with agent and approval settings
   * @throws Error if config invalid, agent missing, or approval function missing
   *
   * @example
   * ```typescript
   * const humanInLoop = new HumanInLoopAgent({
   *   agent: myAgent,
   *   approvalFunc: simpleApprovalFunc(true)
   * });
   * ```
   */
  constructor(config: HumanInLoopConfig) {
    if (!config) {
      throw new Error('config is required');
    }
    if (!config.agent) {
      throw new Error('agent is required');
    }
    if (!config.approvalFunc) {
      throw new Error('approval function is required');
    }

    const threshold = config.approvalThreshold ?? 0.8;
    if (threshold < 0 || threshold > 1) {
      throw new Error(`approval threshold must be between 0 and 1 (got ${threshold})`);
    }

    this.agent = config.agent;
    this.approvalThreshold = threshold;
    this.approvalFunc = config.approvalFunc;
    this.confidenceKey = config.confidenceKey || 'confidence';
  }

  /**
   * Returns the agent's capabilities plus human-in-loop.
   */
  get capabilities(): string[] {
    const caps = this.agent.capabilities ? [...this.agent.capabilities] : [];
    caps.push('human-in-loop', 'approval', 'oversight');
    return caps;
  }

  /**
   * Executes the agent with human approval when needed.
   *
   * The process follows these steps:
   * 1. Execute underlying agent
   * 2. Extract confidence from response metadata
   * 3. If confidence < threshold, request human approval
   * 4. Return approved response or rejection message
   *
   * If approval is denied, a message indicating rejection is returned.
   * If approval includes modifications, the modified message is returned.
   *
   * The final message includes metadata about the approval process.
   *
   * @param message - Input message to process
   * @returns Approved response or rejection message
   * @throws Error if message invalid, agent execution fails, or approval request fails
   *
   * @example
   * ```typescript
   * const result = await humanInLoop.process(
   *   createMessage('user', 'High-stakes decision')
   * );
   *
   * // Access approval metadata
   * console.log(result.metadata?.approval_needed);
   * console.log(result.metadata?.approval_status);
   * console.log(result.metadata?.confidence);
   * ```
   */
  async process(message: Message): Promise<Message> {
    if (!message) {
      throw new Error('message cannot be nil');
    }

    // Execute underlying agent
    let response: Message;
    try {
      response = await this.agent.process(message);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      throw new Error(`agent execution failed: ${errorMsg}`);
    }

    // Extract confidence from metadata
    const confidence = this.extractConfidence(response);

    // Check if approval needed
    const needsApproval = confidence < this.approvalThreshold;

    // Add approval metadata
    if (!response.metadata) {
      response.metadata = {};
    }
    response.metadata.approval_needed = needsApproval;
    response.metadata.confidence = confidence;
    response.metadata.approval_threshold = this.approvalThreshold;

    // If high confidence, return without approval
    if (!needsApproval) {
      response.metadata.approval_status = 'bypassed';
      return response;
    }

    // Request human approval
    const request: ApprovalRequest = {
      message: response,
      confidence,
      context: {
        agent: this.agent.name,
        approval_threshold: this.approvalThreshold,
        original_message: message.content,
        confidence_shortfall: this.approvalThreshold - confidence,
      },
      timestamp: new Date().toISOString(),
    };

    let approval: ApprovalResponse;
    try {
      approval = await this.approvalFunc(request);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      throw new Error(`approval request failed: ${errorMsg}`);
    }

    // Handle approval decision
    if (!approval.approved) {
      // Request denied
      const rejectionMsg = createMessage('agent', 'Action rejected by human reviewer');

      if (!rejectionMsg.metadata) {
        rejectionMsg.metadata = {};
      }

      if (approval.feedback) {
        rejectionMsg.metadata.rejection_reason = approval.feedback;
      }

      rejectionMsg.metadata.approval_status = 'rejected';
      rejectionMsg.metadata.original_response = response.content;
      rejectionMsg.metadata.confidence = confidence;

      return rejectionMsg;
    }

    // Request approved
    let finalResponse = response;
    if (approval.modifiedMessage) {
      // Use modified version
      finalResponse = approval.modifiedMessage;
      if (!finalResponse.metadata) {
        finalResponse.metadata = {};
      }
      finalResponse.metadata.approval_status = 'approved_with_modifications';
      finalResponse.metadata.original_response = response.content;
    } else {
      if (!finalResponse.metadata) {
        finalResponse.metadata = {};
      }
      finalResponse.metadata.approval_status = 'approved';
    }

    if (approval.feedback) {
      if (!finalResponse.metadata) {
        finalResponse.metadata = {};
      }
      finalResponse.metadata.approval_feedback = approval.feedback;
    }

    return finalResponse;
  }

  /**
   * Extracts confidence value from message metadata.
   */
  private extractConfidence(message: Message): number {
    if (!message.metadata) {
      return 0.0;
    }

    const confidenceVal = message.metadata[this.confidenceKey];
    if (confidenceVal === undefined || confidenceVal === null) {
      return 0.0;
    }

    // Try to convert to number
    const confidence = Number(confidenceVal);
    return isNaN(confidence) ? 0.0 : confidence;
  }
}

/**
 * Creates a basic approval function for testing/demos.
 *
 * This function automatically approves or rejects based on a static decision.
 * For production use, implement a custom ApprovalFunc that prompts humans.
 *
 * @param autoApprove - Whether to automatically approve or reject
 * @returns Approval function
 *
 * @example
 * ```typescript
 * const agent = new HumanInLoopAgent({
 *   agent: myAgent,
 *   approvalFunc: simpleApprovalFunc(true)
 * });
 * ```
 */
export function simpleApprovalFunc(autoApprove: boolean): ApprovalFunc {
  return async (request: ApprovalRequest): Promise<ApprovalResponse> => {
    return {
      approved: autoApprove,
      feedback: `Auto-${autoApprove ? 'approved' : 'rejected'} (confidence: ${request.confidence.toFixed(2)})`,
    };
  };
}

/**
 * Creates an approval function with dynamic thresholds.
 *
 * This allows different approval rules based on confidence levels:
 * - Very low confidence (< rejectBelow): always reject
 * - Low confidence (rejectBelow to autoApproveAbove): require approval
 * - High confidence (>= autoApproveAbove): auto-approve
 *
 * @param rejectBelow - Confidence below this is auto-rejected
 * @param autoApproveAbove - Confidence above this is auto-approved
 * @returns Approval function
 *
 * @example
 * ```typescript
 * const agent = new HumanInLoopAgent({
 *   agent: myAgent,
 *   approvalFunc: confidenceBasedApprovalFunc(0.3, 0.9)
 * });
 * // Auto-rejects below 0.3, auto-approves above 0.9
 * ```
 */
export function confidenceBasedApprovalFunc(
  rejectBelow: number,
  autoApproveAbove: number,
): ApprovalFunc {
  return async (request: ApprovalRequest): Promise<ApprovalResponse> => {
    if (request.confidence < rejectBelow) {
      return {
        approved: false,
        feedback: `Confidence too low (${request.confidence.toFixed(2)} < ${rejectBelow})`,
      };
    }

    if (request.confidence >= autoApproveAbove) {
      return {
        approved: true,
        feedback: `Auto-approved (${request.confidence.toFixed(2)} >= ${autoApproveAbove})`,
      };
    }

    // In this range, you would typically prompt a human
    // For this example, we'll reject to be safe
    return {
      approved: false,
      feedback: `Manual approval required (${request.confidence.toFixed(2)} in threshold range)`,
    };
  };
}
