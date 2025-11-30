/**
 * Router Pattern Usage Example
 *
 * Conditional agent selection based on input classification
 *
 * Use cases:
 * - Intent-based routing
 * - Specialized agent dispatch
 * - Dynamic workflow selection
 */

import { Agent, Message } from '../../src/core';
import { RouterAgent } from '../../src/patterns';

class SimpleAgent implements Agent {
  constructor(private agentName: string) {}

  name(): string {
    return this.agentName;
  }

  capabilities(): string[] {
    return ['demo'];
  }

  async process(message: Message): Promise<Message> {
    console.log(`   🤖 ${this.agentName} processing...`);

    return {
      role: 'agent',
      content: `${this.agentName} processed: ${message.content}`,
      metadata: {},
    };
  }
}

async function main() {
  console.log('=== Router Pattern Demo ===\n');

  const agent1 = new SimpleAgent('Agent1');
  const agent2 = new SimpleAgent('Agent2');
  const agent3 = new SimpleAgent('Agent3');

  // Create pattern (adjust based on pattern type)
  // const pattern = new RouterAgent(...);

  console.log('\n✅ Router pattern example');
  console.log('\nNote: This is a minimal template.');
  console.log('See Python examples for complete implementations.');
}

main().catch(console.error);
