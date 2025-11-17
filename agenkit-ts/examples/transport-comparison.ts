/**
 * Transport Comparison - HTTP vs WebSocket vs gRPC
 *
 * Demonstrates the three transport protocols and when to use each:
 * - HTTP: Stateless, simple, universal (REST APIs, webhooks)
 * - WebSocket: Stateful, bidirectional, real-time (chat, notifications)
 * - gRPC: High-performance, typed, efficient (microservices, internal APIs)
 *
 * Run: npx ts-node examples/transport-comparison.ts
 */

import {
  HTTPAgent,
  WebSocketAgent,
  GrpcAgent,
  LocalAgent,
  createMessage,
  Message,
} from '../src/index';

// Simple echo agent for testing
const echoAgent = new LocalAgent(
  async (message: Message) => {
    return createMessage('assistant', `Echo: ${message.content}`);
  },
  { name: 'echo-agent' },
);

async function main() {
  console.log('🚀 Agenkit Transport Comparison\n');

  // ==================================================================
  // Example 1: HTTP Transport (RESTful)
  // ==================================================================
  console.log('📡 HTTP Transport');
  console.log('  ✓ Stateless - Each request is independent');
  console.log('  ✓ Universal - Works everywhere (browsers, curl, Postman)');
  console.log('  ✓ Caching - HTTP caching, CDN support');
  console.log('  ✓ Load balancing - Easy to distribute');
  console.log('  ✗ Overhead - Headers on every request');
  console.log('  ✗ Latency - Connection setup per request\n');

  console.log('  Use cases:');
  console.log('    • REST APIs');
  console.log('    • Webhooks');
  console.log('    • Public APIs');
  console.log('    • Simple request/response patterns\n');

  console.log('  Example:');
  console.log('    const agent = new HTTPAgent({');
  console.log('      baseUrl: "http://api.example.com",');
  console.log('      headers: { "Authorization": "Bearer token" }');
  console.log('    });');
  console.log('    const response = await agent.process(message);\n');

  // ==================================================================
  // Example 2: WebSocket Transport (Real-time)
  // ==================================================================
  console.log('🔌 WebSocket Transport');
  console.log('  ✓ Bidirectional - True full-duplex communication');
  console.log('  ✓ Low latency - Persistent connection, no setup overhead');
  console.log('  ✓ Real-time - Server can push to client anytime');
  console.log('  ✓ Efficient - Binary framing, minimal overhead');
  console.log('  ✗ Stateful - Connection management required');
  console.log('  ✗ Scaling - More complex than HTTP\n');

  console.log('  Use cases:');
  console.log('    • Chat applications');
  console.log('    • Live notifications');
  console.log('    • Collaborative editing');
  console.log('    • Streaming responses\n');

  console.log('  Example:');
  console.log('    const agent = new WebSocketAgent({');
  console.log('      url: "ws://api.example.com",');
  console.log('      reconnect: true');
  console.log('    });');
  console.log('    const response = await agent.process(message);\n');

  // ==================================================================
  // Example 3: gRPC Transport (Microservices)
  // ==================================================================
  console.log('⚡ gRPC Transport');
  console.log('  ✓ Performance - Binary Protocol Buffers, HTTP/2');
  console.log('  ✓ Type safety - Schema-defined contracts');
  console.log('  ✓ Streaming - Unary, server, client, bidirectional');
  console.log('  ✓ Multiplexing - Multiple requests over one connection');
  console.log('  ✗ Complexity - Requires proto files');
  console.log('  ✗ Browser support - Limited (needs grpc-web)\n');

  console.log('  Use cases:');
  console.log('    • Microservices communication');
  console.log('    • High-throughput APIs');
  console.log('    • Internal services');
  console.log('    • Streaming data pipelines\n');

  console.log('  Example:');
  console.log('    const agent = new GrpcAgent("my-service", {');
  console.log('      address: "localhost:50051",');
  console.log('      timeout: 5000');
  console.log('    });');
  console.log('    const response = await agent.process(message);\n');

  // ==================================================================
  // Performance Comparison
  // ==================================================================
  console.log('📊 Performance Comparison (Typical)');
  console.log('');
  console.log('  Metric           | HTTP     | WebSocket | gRPC');
  console.log('  -----------------|----------|-----------|----------');
  console.log('  Latency (ms)     | 50-100   | 10-30     | 5-20');
  console.log('  Throughput       | Medium   | High      | Very High');
  console.log('  Connection Setup | Every req| Once      | Once');
  console.log('  Payload Size     | Large    | Small     | Smallest');
  console.log('  Browser Support  | ✓        | ✓         | ✗ (needs proxy)');
  console.log('');

  // ==================================================================
  // Decision Matrix
  // ==================================================================
  console.log('🎯 When to Use Each Transport');
  console.log('');
  console.log('  Choose HTTP when:');
  console.log('    • Building public APIs');
  console.log('    • Need universal compatibility');
  console.log('    • Stateless operations preferred');
  console.log('    • Using existing HTTP infrastructure\n');

  console.log('  Choose WebSocket when:');
  console.log('    • Need real-time updates');
  console.log('    • Server-initiated messages');
  console.log('    • Browser-based applications');
  console.log('    • Chat, notifications, live data\n');

  console.log('  Choose gRPC when:');
  console.log('    • Internal microservices');
  console.log('    • Need maximum performance');
  console.log('    • Type safety is critical');
  console.log('    • Streaming data pipelines\n');

  // ==================================================================
  // Practical Example: Multi-Transport Agent
  // ==================================================================
  console.log('💡 Practical Tip: Support Multiple Transports');
  console.log('');
  console.log('  Many production systems expose the SAME agent over multiple transports:');
  console.log('    • HTTP for public API');
  console.log('    • WebSocket for web dashboard');
  console.log('    • gRPC for internal services\n');

  console.log('  Example architecture:');
  console.log('');
  console.log('    ┌─────────────┐');
  console.log('    │  Your Agent │');
  console.log('    └──────┬──────┘');
  console.log('           │');
  console.log('    ┌──────┼──────┐');
  console.log('    │      │      │');
  console.log('    HTTP   WS   gRPC');
  console.log('    │      │      │');
  console.log('  Public  Web  Internal\n');

  console.log('✨ Pro Tip: Start with HTTP (simplest), add others as needed');
}

main().catch(console.error);
