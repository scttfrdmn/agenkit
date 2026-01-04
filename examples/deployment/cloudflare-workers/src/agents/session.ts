/**
 * AgentSession Durable Object
 *
 * Manages stateful agent sessions with:
 * - Conversation history
 * - Session metadata
 * - Automatic cleanup
 */

import { ReActAgent } from './react';
import { ConversationalAgent } from './conversational';
import { RouterAgent } from './router';

interface Message {
  role: string;
  content: string;
  metadata?: Record<string, any>;
  timestamp: number;
}

interface SessionState {
  sessionId: string;
  agentType: string;
  messages: Message[];
  metadata: Record<string, any>;
  createdAt: number;
  lastAccessedAt: number;
}

export class AgentSession implements DurableObject {
  private state: DurableObjectState;
  private env: any;
  private sessionState?: SessionState;
  private alarm?: number;

  constructor(state: DurableObjectState, env: any) {
    this.state = state;
    this.env = env;

    // Block concurrent requests during state initialization
    this.state.blockConcurrencyWhile(async () => {
      this.sessionState = await this.state.storage.get<SessionState>('session');
    });
  }

  // ============================================================
  // Fetch Handler
  // ============================================================

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    try {
      // Handle different endpoints
      if (url.pathname.endsWith('/info')) {
        return this.handleGetInfo();
      }

      if (url.pathname.endsWith('/delete') && request.method === 'DELETE') {
        return this.handleDelete();
      }

      if (request.method === 'POST') {
        return this.handleAgentRequest(request);
      }

      return new Response(JSON.stringify({
        error: 'Method not allowed'
      }), {
        status: 405,
        headers: { 'Content-Type': 'application/json' }
      });

    } catch (error) {
      console.error('Session error:', error);
      return new Response(JSON.stringify({
        error: 'Session processing error',
        message: error instanceof Error ? error.message : 'Unknown error'
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }

  // ============================================================
  // Request Handlers
  // ============================================================

  private async handleAgentRequest(request: Request): Promise<Response> {
    const body = await request.json() as {
      agent_type: string;
      message: Message;
      session_id: string;
    };

    // Initialize session if needed
    if (!this.sessionState) {
      this.sessionState = {
        sessionId: body.session_id,
        agentType: body.agent_type,
        messages: [],
        metadata: {},
        createdAt: Date.now(),
        lastAccessedAt: Date.now()
      };
    }

    // Update last accessed time
    this.sessionState.lastAccessedAt = Date.now();

    // Add user message to history
    const userMessage: Message = {
      ...body.message,
      timestamp: Date.now()
    };
    this.sessionState.messages.push(userMessage);

    // Create agent instance
    const agent = this.createAgent(body.agent_type);

    // Process message
    const response = await agent.process(userMessage, {
      history: this.sessionState.messages,
      metadata: this.sessionState.metadata,
      env: this.env
    });

    // Add assistant message to history
    const assistantMessage: Message = {
      role: 'assistant',
      content: response.content,
      metadata: response.metadata,
      timestamp: Date.now()
    };
    this.sessionState.messages.push(assistantMessage);

    // Persist state
    await this.state.storage.put('session', this.sessionState);

    // Set cleanup alarm (1 hour inactivity)
    await this.setCleanupAlarm();

    // Return response
    return new Response(JSON.stringify({
      role: assistantMessage.role,
      content: assistantMessage.content,
      metadata: assistantMessage.metadata,
      session_id: this.sessionState.sessionId
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }

  private async handleGetInfo(): Promise<Response> {
    if (!this.sessionState) {
      return new Response(JSON.stringify({
        error: 'Session not found'
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    return new Response(JSON.stringify({
      session_id: this.sessionState.sessionId,
      agent_type: this.sessionState.agentType,
      message_count: this.sessionState.messages.length,
      created_at: new Date(this.sessionState.createdAt).toISOString(),
      last_accessed_at: new Date(this.sessionState.lastAccessedAt).toISOString(),
      metadata: this.sessionState.metadata
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }

  private async handleDelete(): Promise<Response> {
    await this.state.storage.deleteAll();
    this.sessionState = undefined;

    return new Response(JSON.stringify({
      message: 'Session deleted'
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // ============================================================
  // Agent Factory
  // ============================================================

  private createAgent(agentType: string) {
    switch (agentType) {
      case 'react':
        return new ReActAgent();
      case 'conversational':
        return new ConversationalAgent();
      case 'router':
        return new RouterAgent();
      default:
        throw new Error(`Unknown agent type: ${agentType}`);
    }
  }

  // ============================================================
  // Alarm for Cleanup
  // ============================================================

  private async setCleanupAlarm() {
    // Set alarm for 1 hour from now
    const alarmTime = Date.now() + 60 * 60 * 1000;

    if (!this.alarm || this.alarm < alarmTime) {
      await this.state.storage.setAlarm(alarmTime);
      this.alarm = alarmTime;
    }
  }

  async alarm() {
    // Check if session is still active
    if (this.sessionState) {
      const inactiveDuration = Date.now() - this.sessionState.lastAccessedAt;

      // If inactive for more than 1 hour, delete session
      if (inactiveDuration > 60 * 60 * 1000) {
        console.log(`Cleaning up inactive session: ${this.sessionState.sessionId}`);
        await this.state.storage.deleteAll();
        this.sessionState = undefined;
      } else {
        // Reset alarm for next check
        await this.setCleanupAlarm();
      }
    }
  }
}
