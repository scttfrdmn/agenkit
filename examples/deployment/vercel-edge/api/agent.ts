/**
 * Agenkit Vercel Edge Function
 *
 * Edge-native agent API with:
 * - Global distribution via Vercel Edge Network
 * - Sub-50ms cold starts
 * - Vercel KV for state management
 * - Vercel Postgres for persistence
 */

import { NextRequest, NextResponse } from 'next/server';
import { kv } from '@vercel/kv';
import { ReActAgent } from '../lib/agents/react';
import { ConversationalAgent } from '../lib/agents/conversational';
import { RouterAgent } from '../lib/agents/router';

export const config = {
  runtime: 'edge',
};

// ============================================================
// Types
// ============================================================

interface AgentRequest {
  agent_type: 'react' | 'conversational' | 'router';
  message: {
    role: string;
    content: string;
    metadata?: Record<string, any>;
  };
  session_id?: string;
}

interface AgentResponse {
  role: string;
  content: string;
  metadata: Record<string, any>;
  session_id: string;
}

interface SessionState {
  sessionId: string;
  agentType: string;
  messages: Array<{
    role: string;
    content: string;
    timestamp: number;
  }>;
  metadata: Record<string, any>;
  createdAt: number;
  lastAccessedAt: number;
}

// ============================================================
// Main Handler
// ============================================================

export default async function handler(req: NextRequest) {
  // Only allow POST requests
  if (req.method !== 'POST') {
    return NextResponse.json(
      { error: 'Method not allowed' },
      { status: 405 }
    );
  }

  try {
    // Parse request body
    const body = await req.json() as AgentRequest;

    // Validate request
    if (!body.agent_type || !body.message) {
      return NextResponse.json(
        {
          error: 'Invalid request',
          message: 'agent_type and message are required'
        },
        { status: 400 }
      );
    }

    // Get or create session ID
    const sessionId = body.session_id || crypto.randomUUID();

    // Get or create session state
    let session = await getSession(sessionId);
    if (!session) {
      session = {
        sessionId,
        agentType: body.agent_type,
        messages: [],
        metadata: {},
        createdAt: Date.now(),
        lastAccessedAt: Date.now()
      };
    }

    // Update last accessed time
    session.lastAccessedAt = Date.now();

    // Add user message to history
    session.messages.push({
      role: body.message.role,
      content: body.message.content,
      timestamp: Date.now()
    });

    // Create agent instance
    const agent = createAgent(body.agent_type);

    // Process message
    const startTime = Date.now();
    const response = await agent.process(body.message, {
      history: session.messages,
      metadata: session.metadata,
      env: {
        OPENAI_API_KEY: process.env.OPENAI_API_KEY,
        ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY
      }
    });
    const duration = Date.now() - startTime;

    // Add assistant message to history
    session.messages.push({
      role: 'assistant',
      content: response.content,
      timestamp: Date.now()
    });

    // Trim history if too long (keep last 20 messages)
    if (session.messages.length > 20) {
      session.messages = session.messages.slice(-20);
    }

    // Save session state to KV
    await saveSession(sessionId, session);

    // Track metrics (fire and forget)
    trackMetrics({
      agent_type: body.agent_type,
      duration_ms: duration,
      status: 'success',
      session_id: sessionId
    }).catch(console.error);

    // Return response
    const result: AgentResponse = {
      role: 'assistant',
      content: response.content,
      metadata: {
        ...response.metadata,
        session_id: sessionId,
        duration_ms: duration
      },
      session_id: sessionId
    };

    return NextResponse.json(result, {
      headers: {
        'X-Session-ID': sessionId,
        'X-Agent-Type': body.agent_type,
        'X-Duration-Ms': duration.toString()
      }
    });

  } catch (error) {
    console.error('Agent error:', error);

    // Track error metrics
    trackMetrics({
      agent_type: 'unknown',
      duration_ms: 0,
      status: 'error',
      session_id: 'unknown',
      error: error instanceof Error ? error.message : 'Unknown error'
    }).catch(console.error);

    return NextResponse.json(
      {
        error: 'Internal server error',
        message: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}

// ============================================================
// Helper Functions
// ============================================================

function createAgent(agentType: string) {
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

async function getSession(sessionId: string): Promise<SessionState | null> {
  try {
    const session = await kv.get<SessionState>(`session:${sessionId}`);
    return session;
  } catch (error) {
    console.error('Failed to get session:', error);
    return null;
  }
}

async function saveSession(sessionId: string, session: SessionState): Promise<void> {
  try {
    // Save with 1 hour expiration
    await kv.set(`session:${sessionId}`, session, { ex: 3600 });
  } catch (error) {
    console.error('Failed to save session:', error);
  }
}

async function trackMetrics(metrics: {
  agent_type: string;
  duration_ms: number;
  status: string;
  session_id: string;
  error?: string;
}): Promise<void> {
  try {
    // Store metrics in KV (for simple tracking)
    const timestamp = Date.now();
    const key = `metrics:${timestamp}:${metrics.session_id}`;

    await kv.set(key, {
      ...metrics,
      timestamp,
      created_at: new Date(timestamp).toISOString()
    }, { ex: 86400 }); // 24 hour retention

    // Increment counters
    await kv.incr(`counter:${metrics.agent_type}:${metrics.status}`);

  } catch (error) {
    console.error('Failed to track metrics:', error);
  }
}
