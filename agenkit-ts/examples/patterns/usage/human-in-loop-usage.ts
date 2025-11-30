/**
 * Human-in-loop Pattern Usage Example
 *
 * Human approval gates for high-stakes decisions
 *
 * Use cases:
 * - Financial approvals
 * - Content moderation
 * - Critical system changes
 */

import { Agent, Message } from '../../src/core';
import { HumaninloopAgent } from '../../src/patterns';

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
  console.log('=== Human-in-loop Pattern Demo ===\n');

  const agent1 = new SimpleAgent('Agent1');
  const agent2 = new SimpleAgent('Agent2');
  const agent3 = new SimpleAgent('Agent3');

  // Create pattern (adjust based on pattern type)
  // const pattern = new HumaninloopAgent(...);

  console.log('\n✅ Human-in-loop pattern example');
  console.log('\nNote: This is a minimal template.');
  console.log('See Python examples for complete implementations.');
}

main().catch(console.error);
