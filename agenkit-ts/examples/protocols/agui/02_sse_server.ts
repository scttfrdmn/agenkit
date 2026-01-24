/**
 * AG-UI HTTP/SSE Server Example
 *
 * Demonstrates AG-UI protocol over Server-Sent Events (HTTP/SSE).
 *
 * This example shows:
 * - Creating an Express server with AG-UI SSE endpoint
 * - CORS configuration for web frontends
 * - Streaming events to browser clients
 * - Error handling and connection management
 *
 * Run:
 *   npx ts-node examples/protocols/agui/02_sse_server.ts
 *
 * Then test with:
 *   curl -X POST http://localhost:3000/chat \
 *     -H "Content-Type: application/json" \
 *     -d '{"message": "Hello!"}' \
 *     -N
 */

import express from 'express';
import { Agent, Message } from '../../../src/core/interfaces.js';
import { createSSEHandler } from '../../../src/protocols/agui/index.js';

/**
 * Demo agent that responds with helpful messages
 */
class AssistantAgent implements Agent {
  readonly name = 'AssistantAgent';

  async process(message: Message): Promise<Message> {
    const content = String(message.content);
    const lowerContent = content.toLowerCase();

    // Determine confidence based on content
    let confidence = 0.9;
    let responseText: string;

    if (lowerContent.includes('hello') || lowerContent.includes('hi')) {
      responseText = 'Hello! How can I assist you today?';
      confidence = 0.95;
    } else if (lowerContent.includes('help')) {
      responseText = 'I\'m here to help! What do you need assistance with?';
      confidence = 0.9;
    } else if (lowerContent.includes('bye') || lowerContent.includes('goodbye')) {
      responseText = 'Goodbye! Have a great day!';
      confidence = 0.95;
    } else {
      responseText = `I received your message: "${content}". How can I help you with that?`;
      confidence = 0.7;
    }

    return {
      role: 'assistant',
      content: responseText,
      metadata: {
        confidence,
        processing_time: Math.random() * 100,
        timestamp: new Date().toISOString(),
      },
      timestamp: new Date().toISOString(),
    };
  }

  readonly capabilities = ['conversation', 'assistance', 'text-processing'];
}

/**
 * Main server setup
 */
function main() {
  console.log('='.repeat(60));
  console.log('AG-UI HTTP/SSE Server Example');
  console.log('='.repeat(60));
  console.log();

  // Create Express app
  const app = express();
  app.use(express.json());

  // Create agent
  const agent = new AssistantAgent();
  console.log('✓ Created AssistantAgent');

  // Create SSE handler with CORS
  const sseHandler = createSSEHandler(agent, {
    corsOrigins: ['*'], // Allow all origins (restrict in production)
    timeout: 30000, // 30 second timeout
    pingInterval: 15, // Ping every 15 seconds
  });

  // Add SSE endpoint
  app.post('/chat', sseHandler);
  console.log('✓ Configured /chat endpoint with SSE handler');

  // Add health check endpoint
  app.get('/health', (req, res) => {
    res.json({
      status: 'ok',
      service: 'agui-sse-server',
      timestamp: new Date().toISOString(),
    });
  });
  console.log('✓ Added /health endpoint');
  console.log();

  // Start server
  const PORT = 3000;
  app.listen(PORT, () => {
    console.log('🚀 Server started successfully!');
    console.log();
    console.log(`   HTTP/SSE endpoint: http://localhost:${PORT}/chat`);
    console.log(`   Health check:      http://localhost:${PORT}/health`);
    console.log();
    console.log('Test with curl:');
    console.log(`   curl -X POST http://localhost:${PORT}/chat \\`);
    console.log(`     -H "Content-Type: application/json" \\`);
    console.log(`     -d '{"message": "Hello!"}' \\`);
    console.log(`     -N`);
    console.log();
    console.log('Press Ctrl+C to stop');
    console.log('='.repeat(60));
  });
}

// Run server
main();
