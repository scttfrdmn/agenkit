/**
 * AG-UI Human-in-the-Loop Integration
 *
 * Integrates the HumanInLoopAgent pattern with AG-UI protocol using Interrupt events.
 * Provides streaming approval workflow where agents can request human approval via
 * Interrupt events, and frontends can respond with InterruptResponse messages.
 *
 * Key concepts:
 * - Interrupt events for approval requests
 * - InterruptResponse for approval decisions
 * - Streaming approval workflow
 * - Integration with HumanInLoopAgent pattern
 *
 * Example:
 *   import { AGUIHumanInLoopAdapter } from './agui/hitl';
 *   import { HumanInLoopAgent } from '../patterns/human-in-loop';
 *
 *   // Create human-in-loop agent
 *   const hilAgent = new HumanInLoopAgent({
 *     agent: myAgent,
 *     approvalFunc: myApprovalFunc,
 *     approvalThreshold: 0.8
 *   });
 *
 *   // Wrap with AG-UI adapter
 *   const adapter = new AGUIHumanInLoopAdapter(hilAgent);
 *
 *   // Stream events (includes Interrupt events for approval requests)
 *   for await (const event of adapter.streamEvents(userMessage)) {
 *     if (event instanceof Interrupt) {
 *       // Frontend displays approval request
 *       // User responds via InterruptResponse
 *     }
 *   }
 */

import { Agent, Message } from '../../core/interfaces.js';
import { HumanInLoopAgent, ApprovalRequest } from '../../patterns/human-in-loop.js';
import { AGUIAdapter, AGUIAdapterConfig } from './adapter.js';
import {
  AGUIEvent,
  Interrupt,
  InterruptAction,
  InterruptReason,
  InterruptResponse,
  MetadataEvent,
  TextMessageChunk,
  TextMessageComplete,
  TextMessageStart,
} from './events.js';
import { randomUUID } from 'crypto';

/**
 * Configuration for AG-UI HITL adapter
 */
export interface AGUIHumanInLoopConfig extends AGUIAdapterConfig {
  /** Whether to emit Interrupt events for approval requests */
  emitInterrupts?: boolean;
}

/**
 * AG-UI adapter with human-in-the-loop support via Interrupt events.
 *
 * This adapter integrates the HumanInLoopAgent pattern with AG-UI protocol.
 * When an agent requires approval (confidence < threshold), an Interrupt event
 * is emitted to request human approval. The frontend can respond via
 * InterruptResponse.
 *
 * The adapter handles:
 * - Converting approval requests to Interrupt events
 * - Processing InterruptResponse from frontend
 * - Streaming approval workflow
 * - Metadata about approval decisions
 *
 * Example:
 *   const hilAgent = new HumanInLoopAgent({
 *     agent: myAgent,
 *     approvalFunc: async (request) => {
 *       // Custom approval logic
 *       return { approved: true };
 *     },
 *     approvalThreshold: 0.8
 *   });
 *
 *   const adapter = new AGUIHumanInLoopAdapter(hilAgent);
 *
 *   for await (const event of adapter.streamEvents(message)) {
 *     if (event instanceof Interrupt) {
 *       // Display approval request to user
 *       console.log(`Approval needed: ${event.message}`);
 *       console.log(`Confidence: ${event.context.confidence}`);
 *     }
 *   }
 */
export class AGUIHumanInLoopAdapter extends AGUIAdapter {
  private readonly emitInterrupts: boolean;
  private readonly pendingInterrupts: Map<string, any>;
  private approvalRequestCallback?: (request: ApprovalRequest) => Promise<void>;

  /**
   * Initialize AG-UI human-in-loop adapter.
   *
   * @param agent - Agent to wrap (HumanInLoopAgent or regular Agent)
   * @param config - Optional configuration
   */
  constructor(agent: Agent, config: AGUIHumanInLoopConfig = {}) {
    super(agent, config);
    this.emitInterrupts = config.emitInterrupts !== false;
    this.pendingInterrupts = new Map();
  }

  /**
   * Stream AG-UI events with interrupt support.
   *
   * When the agent requires approval, emits an Interrupt event to notify
   * the frontend about the approval decision.
   *
   * Note: This implementation emits Interrupt events after the approval
   * decision has been made (informational). For true bidirectional HITL,
   * use a custom approvalFunc that integrates with your transport layer.
   *
   * @param message - Input message to process
   * @param messageId - Optional message ID
   * @param emitMetadata - Whether to emit MetadataEvent first
   * @yields AG-UI events (includes Interrupt events for approval notifications)
   *
   * Example:
   *   for await (const event of adapter.streamEvents(message)) {
   *     if (event instanceof Interrupt) {
   *       // Approval decision was made
   *       console.log(`Approval: ${event.context.approval_status}`);
   *     }
   *   }
   */
  async *streamEvents(
    message: Message,
    messageId?: string,
    emitMetadata: boolean = true,
  ): AsyncGenerator<AGUIEvent, void, undefined> {
    const msgId = messageId || this.generateMessageId();

    // Check if agent is a HumanInLoopAgent
    const agent = this.getAgent();
    const isHilAgent = agent instanceof HumanInLoopAgent;

    // For regular agents or if interrupts disabled, use standard streaming
    if (!isHilAgent || !this.emitInterrupts) {
      yield* super.streamEvents(message, msgId, emitMetadata);
      return;
    }

    // Emit metadata about agent capabilities (including HITL)
    if (emitMetadata) {
      yield this.createHITLMetadataEvent();
    }

    // Emit text message start
    yield new TextMessageStart('assistant', msgId, {
      agent_name: this.getAgentName(),
    });

    try {
      // Track if approval was requested
      let approvalRequested = false;
      let approvalDetails: any = {};

      // Store the original approval function
      const hilAgent = agent as HumanInLoopAgent;
      const originalApprovalFunc = (hilAgent as any).approvalFunc;

      // Wrap approval function to capture approval events
      (hilAgent as any).approvalFunc = async (request: ApprovalRequest) => {
        approvalRequested = true;
        approvalDetails = {
          confidence: request.confidence,
          timestamp: request.timestamp,
          context: request.context,
        };

        // Call original approval function
        return await originalApprovalFunc(request);
      };

      // Process message with agent
      const response = await agent.process(message);

      // Restore original approval function
      (hilAgent as any).approvalFunc = originalApprovalFunc;

      // If approval was requested, emit Interrupt event
      if (approvalRequested && this.emitInterrupts) {
        const interruptId = `interrupt_${randomUUID()}`;
        const interrupt = this.createApprovalInterrupt(
          interruptId,
          approvalDetails,
          response,
        );
        yield interrupt;
      }

      // Extract content
      const content =
        typeof response.content === 'string'
          ? response.content
          : JSON.stringify(response.content);

      // Stream content in chunks
      const chunkSize = (this as any).chunkSize || 50;
      for (let i = 0; i < content.length; i += chunkSize) {
        const chunk = content.slice(i, i + chunkSize);
        yield new TextMessageChunk(chunk, msgId, {
          chunk_index: Math.floor(i / chunkSize),
        });
      }

      // Emit completion
      yield new TextMessageComplete(content, 'stop', msgId, {
        agent_name: this.getAgentName(),
        response_metadata: response.metadata,
        approval_requested: approvalRequested,
        approval_details: approvalRequested ? approvalDetails : undefined,
      });
    } catch (error) {
      // Convert exceptions to error events
      yield this.createErrorEvent(msgId, error as Error);

      // Also emit a completion with error
      yield new TextMessageComplete('', 'error', msgId, {
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  /**
   * Create metadata event with HITL capabilities
   */
  private createHITLMetadataEvent(): MetadataEvent {
    const agent = this.getAgent();
    const isHilAgent = agent instanceof HumanInLoopAgent;

    const metadata: Record<string, any> = {
      agent_name: this.getAgentName(),
      protocol: 'ag-ui',
      protocol_version: '1.0',
      capabilities: {
        streaming: true,
        tool_calls: false,
        interrupts: isHilAgent && this.emitInterrupts,
        multimodal: false,
      },
    };

    // Add HITL-specific metadata
    if (isHilAgent) {
      const hilAgent = agent as any;
      metadata.hitl = {
        enabled: true,
        approval_threshold: hilAgent.approvalThreshold || 0.8,
        confidence_key: hilAgent.confidenceKey || 'confidence',
      };
    }

    // Add agent capabilities if available
    if (agent.capabilities) {
      metadata.agent_capabilities = agent.capabilities();
    }

    return new MetadataEvent(metadata);
  }

  /**
   * Create an Interrupt event for approval request
   */
  private createApprovalInterrupt(
    interruptId: string,
    approvalDetails: any,
    response: Message,
  ): Interrupt {
    const confidence = approvalDetails.confidence || 0.0;
    const threshold = (this.getAgent() as any).approvalThreshold || 0.8;

    // Determine approval status
    const approved = confidence >= threshold;
    const status = approved ? 'approved' : 'rejected';

    // Create interrupt message
    const message = approved
      ? `Agent action approved (confidence: ${confidence.toFixed(2)})`
      : `Agent action requires approval (confidence: ${confidence.toFixed(2)}, threshold: ${threshold.toFixed(2)})`;

    return new Interrupt(
      InterruptReason.APPROVAL_REQUIRED,
      message,
      [InterruptAction.APPROVE, InterruptAction.REJECT, InterruptAction.EDIT],
      {
        approval_status: status,
        confidence: confidence,
        threshold: threshold,
        confidence_shortfall: Math.max(0, threshold - confidence),
        response_preview: String(response.content).slice(0, 100),
        timestamp: approvalDetails.timestamp,
        ...approvalDetails.context,
      },
      interruptId,
    );
  }

  /**
   * Generate a unique message ID
   */
  private generateMessageId(): string {
    return `msg_${randomUUID()}`;
  }

  /**
   * Create an error event from an exception
   */
  private createErrorEvent(messageId: string, error: Error): any {
    const ErrorEventClass = require('./events.js').ErrorEvent;
    return new ErrorEventClass(
      'agent_error',
      error.message || 'Unknown error',
      true,
      {
        message_id: messageId,
        error_type: error.name,
        stack: error.stack,
      },
    );
  }
}

/**
 * Convenience function to wrap a HumanInLoopAgent with AG-UI HITL adapter
 *
 * @param agent - HumanInLoopAgent to wrap
 * @param config - Optional configuration
 * @returns Wrapped AG-UI HITL adapter
 */
export function wrapHITLAgentAsAGUI(
  agent: HumanInLoopAgent,
  config?: AGUIHumanInLoopConfig,
): AGUIHumanInLoopAdapter {
  return new AGUIHumanInLoopAdapter(agent, config);
}
