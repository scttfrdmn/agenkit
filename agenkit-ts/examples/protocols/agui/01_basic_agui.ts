/**
 * Basic AG-UI Example
 *
 * Demonstrates core AG-UI protocol usage with streaming events.
 *
 * This example shows:
 * - Creating an AG-UI adapter from an agent
 * - Streaming AG-UI events from agent responses
 * - Handling different event types (TextMessageStart, Chunk, Complete)
 * - Metadata event emission
 *
 * Run:
 *   npx ts-node examples/protocols/agui/01_basic_agui.ts
 */

import { Agent, Message } from '../../../src/core/interfaces.js';
import {
  AGUIAdapter,
  TextMessageStart,
  TextMessageChunk,
  TextMessageComplete,
  MetadataEvent,
} from '../../../src/protocols/agui/index.js';

/**
 * Simple echo agent for demonstration
 */
class EchoAgent implements Agent {
  readonly name = 'EchoAgent';

  async process(message: Message): Promise<Message> {
    const content = String(message.content);
    return {
      role: 'assistant',
      content: `Echo: ${content}`,
      metadata: {
        confidence: 1.0,
        processing_time: 10,
      },
      timestamp: new Date().toISOString(),
    };
  }

  readonly capabilities = ['echo', 'text-processing'];
}

/**
 * Main demonstration function
 */
async function main() {
  console.log('='.repeat(60));
  console.log('Basic AG-UI Protocol Example');
  console.log('='.repeat(60));
  console.log();

  // Create agent
  const agent = new EchoAgent();
  console.log('✓ Created EchoAgent');

  // Wrap with AG-UI adapter
  const aguiAdapter = new AGUIAdapter(agent);
  console.log('✓ Created AG-UI adapter');
  console.log();

  // Create user message
  const userMessage: Message = {
    role: 'user',
    content: 'Hello, AG-UI!',
    timestamp: new Date().toISOString(),
  };

  console.log(`User: ${userMessage.content}`);
  console.log();

  // Stream AG-UI events
  console.log('AG-UI Events:');
  console.log('-'.repeat(60));

  let eventCount = 0;
  let fullContent = '';

  for await (const event of aguiAdapter.streamEvents(userMessage)) {
    eventCount++;

    if (event instanceof MetadataEvent) {
      console.log(`[${eventCount}] MetadataEvent:`);
      console.log(`    Agent: ${event.data.agent_name}`);
      console.log(`    Protocol: ${event.data.protocol}`);
      console.log(`    Capabilities: ${JSON.stringify(event.data.capabilities)}`);
      console.log();
    } else if (event instanceof TextMessageStart) {
      console.log(`[${eventCount}] TextMessageStart:`);
      console.log(`    Role: ${event.role}`);
      console.log(`    Message ID: ${event.message_id}`);
      console.log();
    } else if (event instanceof TextMessageChunk) {
      console.log(`[${eventCount}] TextMessageChunk:`);
      console.log(`    Content: "${event.content}"`);
      fullContent += event.content;
    } else if (event instanceof TextMessageComplete) {
      console.log();
      console.log(`[${eventCount}] TextMessageComplete:`);
      console.log(`    Finish Reason: ${event.finish_reason}`);
      console.log(`    Full Content: "${event.content}"`);
      console.log(`    Metadata: ${JSON.stringify(event.metadata, null, 2)}`);
    }
  }

  console.log();
  console.log('-'.repeat(60));
  console.log(`Total events: ${eventCount}`);
  console.log(`Streamed content: "${fullContent}"`);
  console.log();

  console.log('='.repeat(60));
  console.log('✅ Example completed successfully!');
  console.log('='.repeat(60));
}

// Run example
main().catch((error) => {
  console.error('Error:', error);
  process.exit(1);
});
