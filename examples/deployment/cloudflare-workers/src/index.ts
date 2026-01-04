/**
 * Agenkit Cloudflare Workers Deployment
 *
 * Edge-native agent deployment with:
 * - Global distribution (300+ cities)
 * - Sub-10ms cold starts
 * - Durable Objects for state management
 * - KV storage for caching
 * - D1 database for persistence
 */

import { Router } from 'itty-router';
import { AgentSession } from './agents/session';
import { ReActAgent } from './agents/react';
import { ConversationalAgent } from './agents/conversational';
import { RouterAgent } from './agents/router';

// ============================================================
// Types
// ============================================================

export interface Env {
  // Bindings
  AGENT_SESSIONS: DurableObjectNamespace;
  AGENT_CACHE: KVNamespace;
  AGENT_DB: D1Database;

  // Secrets
  OPENAI_API_KEY: string;
  ANTHROPIC_API_KEY: string;

  // Environment
  ENVIRONMENT: string;
  LOG_LEVEL: string;
}

export interface AgentRequest {
  agent_type: 'react' | 'conversational' | 'router';
  message: {
    role: string;
    content: string;
    metadata?: Record<string, any>;
  };
  session_id?: string;
}

export interface AgentResponse {
  role: string;
  content: string;
  metadata: Record<string, any>;
  session_id: string;
}

// ============================================================
// Router Configuration
// ============================================================

const router = Router();

// ============================================================
// Health Check
// ============================================================

router.get('/health', () => {
  return new Response(JSON.stringify({
    status: 'healthy',
    service: 'agenkit-worker',
    version: '0.45.0',
    timestamp: new Date().toISOString()
  }), {
    headers: { 'Content-Type': 'application/json' }
  });
});

// ============================================================
// Agent API Endpoint
// ============================================================

router.post('/api/agent', async (request: Request, env: Env, ctx: ExecutionContext) => {
  try {
    // Parse request
    const body = await request.json() as AgentRequest;

    // Validate request
    if (!body.agent_type || !body.message) {
      return new Response(JSON.stringify({
        error: 'Invalid request',
        message: 'agent_type and message are required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Get or create session ID
    const sessionId = body.session_id || crypto.randomUUID();

    // Get Durable Object stub
    const id = env.AGENT_SESSIONS.idFromName(sessionId);
    const stub = env.AGENT_SESSIONS.get(id);

    // Forward request to Durable Object
    const response = await stub.fetch(request.url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent_type: body.agent_type,
        message: body.message,
        session_id: sessionId
      })
    });

    // Parse and enhance response
    const result = await response.json() as AgentResponse;

    // Track metrics
    ctx.waitUntil(trackMetrics(env, {
      agent_type: body.agent_type,
      duration_ms: Date.now() - performance.now(),
      status: response.ok ? 'success' : 'error'
    }));

    return new Response(JSON.stringify(result), {
      status: response.status,
      headers: {
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId,
        'X-Agent-Type': body.agent_type
      }
    });

  } catch (error) {
    console.error('Agent error:', error);
    return new Response(JSON.stringify({
      error: 'Internal server error',
      message: error instanceof Error ? error.message : 'Unknown error'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
});

// ============================================================
// Session Management
// ============================================================

router.get('/api/session/:id', async (request: Request, env: Env) => {
  try {
    const url = new URL(request.url);
    const sessionId = url.pathname.split('/').pop();

    if (!sessionId) {
      return new Response(JSON.stringify({
        error: 'Session ID required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Get session from Durable Object
    const id = env.AGENT_SESSIONS.idFromName(sessionId);
    const stub = env.AGENT_SESSIONS.get(id);
    const response = await stub.fetch(`${request.url}/info`);

    return response;

  } catch (error) {
    console.error('Session retrieval error:', error);
    return new Response(JSON.stringify({
      error: 'Session not found'
    }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' }
    });
  }
});

router.delete('/api/session/:id', async (request: Request, env: Env) => {
  try {
    const url = new URL(request.url);
    const sessionId = url.pathname.split('/').pop();

    if (!sessionId) {
      return new Response(JSON.stringify({
        error: 'Session ID required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Delete session
    const id = env.AGENT_SESSIONS.idFromName(sessionId);
    const stub = env.AGENT_SESSIONS.get(id);
    await stub.fetch(`${request.url}/delete`, { method: 'DELETE' });

    return new Response(JSON.stringify({
      message: 'Session deleted',
      session_id: sessionId
    }), {
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Session deletion error:', error);
    return new Response(JSON.stringify({
      error: 'Failed to delete session'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
});

// ============================================================
// Metrics Endpoint
// ============================================================

router.get('/metrics', async (request: Request, env: Env) => {
  try {
    // Get metrics from D1
    const result = await env.AGENT_DB
      .prepare('SELECT * FROM metrics WHERE created_at > datetime("now", "-1 hour")')
      .all();

    return new Response(JSON.stringify({
      metrics: result.results,
      count: result.results?.length || 0
    }), {
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Metrics retrieval error:', error);
    return new Response(JSON.stringify({
      error: 'Failed to retrieve metrics'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
});

// ============================================================
// 404 Handler
// ============================================================

router.all('*', () => {
  return new Response(JSON.stringify({
    error: 'Not found',
    message: 'The requested endpoint does not exist'
  }), {
    status: 404,
    headers: { 'Content-Type': 'application/json' }
  });
});

// ============================================================
// Helper Functions
// ============================================================

async function trackMetrics(env: Env, metrics: {
  agent_type: string;
  duration_ms: number;
  status: string;
}) {
  try {
    await env.AGENT_DB
      .prepare('INSERT INTO metrics (agent_type, duration_ms, status, created_at) VALUES (?, ?, ?, datetime("now"))')
      .bind(metrics.agent_type, metrics.duration_ms, metrics.status)
      .run();
  } catch (error) {
    console.error('Failed to track metrics:', error);
  }
}

// ============================================================
// Worker Export
// ============================================================

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    return router.handle(request, env, ctx).catch((error) => {
      console.error('Router error:', error);
      return new Response(JSON.stringify({
        error: 'Internal server error',
        message: error.message
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    });
  }
};

// ============================================================
// Durable Object Export
// ============================================================

export { AgentSession };
