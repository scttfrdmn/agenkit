/**
 * Conversational Pattern Example
 *
 * Demonstrates:
 * - Conversational agent with memory
 * - Context preservation across multiple turns
 * - Working memory management with history pruning
 * - Mock agent for demonstration (no API keys required)
 *
 * WHY use this pattern:
 * ✅ Maintains conversation context across turns
 * ✅ Remembers previous exchanges automatically
 * ✅ Manages memory efficiently with history limits
 * ✅ Natural multi-turn interactions
 * ✅ Simple API - just call process() repeatedly
 *
 * WHEN to use:
 * - Chatbots and conversational assistants
 * - Customer support agents
 * - Technical advisors that need context
 * - Interactive tutors and coaches
 * - Multi-turn troubleshooting workflows
 *
 * Setup:
 *   npm run build
 *   node dist/examples/patterns/conversational-pattern.js
 */

import { ConversationalAgent } from '../../src/patterns/conversational';
import { Agent, Message, createMessage } from '../../src/core/interfaces';

/**
 * Mock conversational agent that remembers context
 */
class MockConversationalLLM implements Agent {
  private context: string[] = [];

  name(): string {
    return 'MockConversational';
  }

  capabilities(): string[] {
    return ['conversation', 'memory'];
  }

  async process(message: Message): Promise<Message> {
    const userMessage = message.content;
    this.context.push(userMessage);

    let response = '';

    // Simple context-aware responses
    if (userMessage.toLowerCase().includes('name') && userMessage.includes('?')) {
      // Looking for remembered name
      const nameContext = this.context.find(msg =>
        msg.toLowerCase().includes('name is') || msg.toLowerCase().includes("i'm ")
      );
      if (nameContext) {
        const nameMatch = nameContext.match(/name is (\w+)/i) || nameContext.match(/i'm (\w+)/i);
        if (nameMatch) {
          response = `Your name is ${nameMatch[1]}.`;
        }
      } else {
        response = "I don't recall your name. Could you remind me?";
      }
    } else if (userMessage.toLowerCase().includes('working on') && userMessage.includes('?')) {
      // Looking for remembered project
      const projectContext = this.context.find(msg =>
        msg.toLowerCase().includes('working on') || msg.toLowerCase().includes('project')
      );
      if (projectContext) {
        response = `Based on our earlier conversation, you're working on projects related to ${projectContext.substring(0, 50)}...`;
      } else {
        response = "I don't recall what you're working on. Can you tell me more?";
      }
    } else if (userMessage.toLowerCase().includes('hello') || userMessage.toLowerCase().includes('hi')) {
      response = 'Hello! How can I help you today?';
    } else {
      // Default acknowledgment that incorporates context
      const contextSummary = this.context.length > 1
        ? `Thank you for sharing. I've noted that in our conversation.`
        : `Got it! I'll remember that.`;
      response = contextSummary;
    }

    return createMessage({ role: 'assistant', content: response });
  }
}

async function main() {
  console.log('='.repeat(60));
  console.log('AgentKit TypeScript - Conversational Pattern Example');
  console.log('='.repeat(60));
  console.log();

  console.log('✓ Using mock agents (no API keys required)');
  console.log();

  // Example 1: Personal assistant with memory
  console.log('-'.repeat(60));
  console.log('Example 1: Personal Assistant Conversation');
  console.log('-'.repeat(60));
  console.log();

  const llm = new MockConversationalLLM();
  const assistant = new ConversationalAgent({
    llmClient: llm,
    maxHistory: 10,
    systemPrompt: 'You are a helpful personal assistant. Remember details about the user.',
  });

  console.log('System: You are a helpful personal assistant.');
  console.log('Max history: 10 messages');
  console.log();

  // Turn 1 - User introduces themselves
  console.log('User: My name is Alex and I\'m a software engineer working with TypeScript.');
  let response = await assistant.process(
    createMessage({ role: 'user', content: 'My name is Alex and I\'m a software engineer working with TypeScript.' })
  );
  console.log(`Assistant: ${response.content}`);
  console.log(`[History: ${assistant.historyLength} messages]`);
  console.log();

  // Turn 2 - User shares more context
  console.log('User: I\'m currently building an AI agent system called AgentKit.');
  response = await assistant.process(
    createMessage({ role: 'user', content: 'I\'m currently building an AI agent system called AgentKit.' })
  );
  console.log(`Assistant: ${response.content}`);
  console.log(`[History: ${assistant.historyLength} messages]`);
  console.log();

  // Turn 3 - Test memory recall
  console.log('User: What was my name again?');
  response = await assistant.process(
    createMessage({ role: 'user', content: 'What was my name again?' })
  );
  console.log(`Assistant: ${response.content}`);
  console.log(`[History: ${assistant.historyLength} messages]`);
  console.log();

  // Turn 4 - Test memory recall of project
  console.log('User: What project am I working on?');
  response = await assistant.process(
    createMessage({ role: 'user', content: 'What project am I working on?' })
  );
  console.log(`Assistant: ${response.content}`);
  console.log(`[History: ${assistant.historyLength} messages]`);
  console.log();

  console.log('-'.repeat(60));
  console.log('✓ Conversational example completed!');
  console.log();
  console.log('Key Features Demonstrated:');
  console.log('  • Context preservation across turns');
  console.log('  • Memory of previous interactions');
  console.log('  • Natural multi-turn dialogue');
  console.log('  • Automatic history management');
  console.log();
  console.log('Production Usage:');
  console.log('  Replace MockConversationalLLM with real LLM adapters:');
  console.log('  - AnthropicAdapter (Claude for conversations)');
  console.log('  - OpenAIAdapter (GPT-4 for chatbots)');
  console.log('  - LLMs will use full conversation history for context');
  console.log();
  console.log('Use Cases:');
  console.log('  • Personal assistants');
  console.log('  • Customer support chatbots');
  console.log('  • Technical advisors');
  console.log('  • Educational tutors');
  console.log('  • Interactive troubleshooting');
  console.log('-'.repeat(60));
}

main().catch((error) => {
  console.error('Error:', error.message);
  process.exit(1);
});
