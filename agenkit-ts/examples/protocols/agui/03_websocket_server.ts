/**
 * AG-UI WebSocket Server Example
 *
 * Demonstrates AG-UI protocol over WebSocket with HITL support.
 *
 * This example shows:
 * - Creating a WebSocket server with AG-UI handler
 * - Bidirectional communication (client <-> server)
 * - Human-in-the-loop integration with Interrupt events
 * - Real-time event streaming over WebSocket
 * - Connection management and heartbeat
 *
 * Run:
 *   npx ts-node examples/protocols/agui/03_websocket_server.ts
 *
 * Then test with websocat:
 *   echo '{"type": "message", "content": "Should I proceed?"}' | websocat ws://localhost:8765
 *
 * Or test with wscat (npm install -g wscat):
 *   wscat -c ws://localhost:8765
 *   > {"type": "message", "content": "Make a critical decision"}
 */

import { WebSocketServer, WebSocket } from 'ws';
import { Agent, Message } from '../../../src/core/interfaces.js';
import { HumanInLoopAgent, ApprovalRequest, ApprovalResponse } from '../../../src/patterns/human-in-loop.js';
import {
  AGUIHumanInLoopAdapter,
  createWebSocketHandler,
  Interrupt,
} from '../../../src/protocols/agui/index.js';

/**
 * Decision agent that makes decisions with varying confidence levels
 */
class DecisionAgent implements Agent {
  readonly name = 'DecisionAgent';

  async process(message: Message): Promise<Message> {
    const content = String(message.content).toLowerCase();

    // Analyze request complexity
    let confidence: number;
    let responseText: string;
    let decisionType: string;

    if (content.includes('critical') || content.includes('important') || content.includes('should')) {
      confidence = 0.5; // Low confidence for critical decisions
      responseText = 'This requires careful consideration.';
      decisionType = 'critical';
    } else if (content.includes('simple') || content.includes('easy')) {
      confidence = 0.95; // High confidence for simple decisions
      responseText = 'This is straightforward.';
      decisionType = 'routine';
    } else {
      confidence = 0.7;
      responseText = "I'll analyze this carefully.";
      decisionType = 'routine';
    }

    return {
      role: 'assistant',
      content: `${responseText} Regarding: ${message.content}`,
      metadata: {
        confidence,
        decision_type: decisionType,
        processing_time: Math.random() * 100,
      },
      timestamp: new Date().toISOString(),
    };
  }

  readonly capabilities = ['decision-making', 'analysis'];
}

/**
 * Approval function with detailed logging
 */
async function approvalFunc(request: ApprovalRequest): Promise<ApprovalResponse> {
  const confidence = request.confidence || 0;
  const decisionType = request.context?.decision_type || 'unknown';

  console.log('\n[Approval System]');
  console.log(`  Confidence: ${confidence.toFixed(2)}`);
  console.log(`  Decision Type: ${decisionType}`);
  console.log(`  Threshold: ${request.context?.approval_threshold}`);

  if (request.context?.confidence_shortfall) {
    console.log(`  Shortfall: ${(request.context.confidence_shortfall as number).toFixed(2)}`);
  }

  // Simulate human review
  await new Promise((resolve) => setTimeout(resolve, 300));

  // For demo, auto-approve
  const approved = true;
  const feedback = `Approved by supervisor (confidence: ${confidence.toFixed(2)})`;

  if (approved) {
    console.log('  Decision: ✅ Approved');
  } else {
    console.log('  Decision: ❌ Rejected');
  }
  console.log(`  Feedback: ${feedback}\n`);

  return {
    approved,
    feedback,
  };
}

/**
 * Main server setup
 */
async function main() {
  console.log('='.repeat(60));
  console.log('AG-UI WebSocket Server with HITL Example');
  console.log('='.repeat(60));
  console.log();

  // Create decision agent
  const decisionAgent = new DecisionAgent();
  console.log(`✓ Created ${decisionAgent.name}`);

  // Wrap with HumanInLoopAgent
  const hilAgent = new HumanInLoopAgent({
    agent: decisionAgent,
    approvalFunc,
    approvalThreshold: 0.8, // Require approval when confidence < 0.8
  });
  console.log('✓ Created HumanInLoopAgent (threshold: 0.8)');

  // Create HITL adapter
  const aguiAdapter = new AGUIHumanInLoopAdapter(hilAgent, {
    agentName: 'WebSocket-DecisionAgent',
    emitInterrupts: true,
  });
  console.log('✓ Created AGUIHumanInLoopAdapter');

  // Create WebSocket server
  const wss = new WebSocketServer({ port: 8765 });
  console.log('✓ Created WebSocket server');
  console.log();

  // Handle connections
  wss.on('connection', (ws: WebSocket) => {
    const clientId = ws.url || 'unknown';
    console.log(`\n[WebSocket] Client ${clientId} connected`);

    // Use the createWebSocketHandler utility
    const handler = createWebSocketHandler(hilAgent, {
      agentName: 'WebSocket-DecisionAgent',
      sendMetadata: true,
      heartbeatInterval: 10,
    });

    handler(ws);

    ws.on('close', () => {
      console.log(`[WebSocket] Client ${clientId} disconnected`);
    });

    ws.on('error', (error: Error) => {
      console.error(`[WebSocket] Error: ${error.message}`);
    });
  });

  // Server info
  console.log('🚀 Server started successfully!');
  console.log();
  console.log('   WebSocket endpoint: ws://localhost:8765');
  console.log();
  console.log('Test with websocat:');
  console.log('   echo \'{"type": "message", "content": "Should I proceed?"}\' | websocat ws://localhost:8765');
  console.log();
  console.log('   # Low confidence (triggers approval):');
  console.log('   echo \'{"type": "message", "content": "Make a critical decision"}\' | websocat ws://localhost:8765');
  console.log();
  console.log('   # High confidence (bypasses approval):');
  console.log('   echo \'{"type": "message", "content": "Simple task"}\' | websocat ws://localhost:8765');
  console.log();
  console.log('Press Ctrl+C to stop');
  console.log('='.repeat(60));

  // Graceful shutdown
  process.on('SIGINT', () => {
    console.log('\n\n🛑 Shutting down server...');
    wss.close(() => {
      console.log('✅ Server stopped gracefully');
      process.exit(0);
    });
  });
}

// Run server
main().catch((error) => {
  console.error('Error:', error);
  process.exit(1);
});
