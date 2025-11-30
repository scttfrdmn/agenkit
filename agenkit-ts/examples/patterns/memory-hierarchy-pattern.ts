/**
 * Memory Hierarchy Pattern Example
 *
 * Demonstrates:
 * - Conversational agent with memory
 * - Context preservation across turns
 * - Working memory management
 * - Multi-turn dialogue
 * - Mock agents for demonstration (no API keys required)
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
 *   node dist/examples/patterns/memory-hierarchy-pattern.js
 */

import { ConversationalAgent } from '../../src/patterns/conversational';
import { Agent, Message, createMessage } from '../../src/core/interfaces';

/**
 * Mock conversational LLM that remembers context
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

    // Context-aware responses
    if (userMessage.toLowerCase().includes('name') && userMessage.includes('?')) {
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
      const projectContext = this.context.find(msg =>
        msg.toLowerCase().includes('working on') || msg.toLowerCase().includes('project')
      );
      if (projectContext) {
        response = `Based on our earlier conversation, you're working on projects related to ${projectContext.substring(0, 50)}...`;
      } else {
        response = "I don't recall what you're working on. Can you tell me more?";
      }
    } else if (userMessage.toLowerCase().includes('design') && userMessage.includes('?')) {
      const designContext = this.context.find(msg =>
        msg.toLowerCase().includes('microservices') || msg.toLowerCase().includes('architecture')
      );
      if (designContext) {
        response = "You mentioned you need a microservices architecture. For that scale, I'd recommend considering service mesh patterns, API gateways, and distributed tracing for observability.";
      } else {
        response = "Could you provide more context about your design requirements?";
      }
    } else if (userMessage.toLowerCase().includes('database') && userMessage.includes('?')) {
      const scaleContext = this.context.find(msg => msg.includes('10,000') || msg.includes('requests'));
      if (scaleContext) {
        response = "Given your requirement for 10,000 requests per second, I'd recommend a combination of PostgreSQL for transactional data with Redis for caching. Consider read replicas and connection pooling for scalability.";
      } else {
        response = "What are your specific database requirements?";
      }
    } else if (userMessage.toLowerCase().includes('authentication') && userMessage.includes('?')) {
      const microservicesContext = this.context.find(msg => msg.toLowerCase().includes('microservices'));
      if (microservicesContext) {
        response = "For authentication across microservices, I recommend using JWT tokens with a centralized auth service. Consider OAuth 2.0 for third-party integrations and implement token refresh mechanisms. Each service should validate tokens but authentication happens centrally.";
      } else {
        response = "What type of authentication system are you looking to implement?";
      }
    } else if (userMessage.toLowerCase().includes('interfaces') && userMessage.includes('?')) {
      response = "Interfaces in TypeScript define the structure of objects. They're contracts that specify what properties and methods an object should have, enabling type checking and better IDE support. Think of them as blueprints for objects.";
    } else if (userMessage.toLowerCase().includes('example') && userMessage.includes('?')) {
      const interfaceContext = this.context.find(msg => msg.toLowerCase().includes('interfaces'));
      if (interfaceContext) {
        response = `Sure! Here's a simple interface example:

\`\`\`typescript
interface User {
  name: string;
  age: number;
  email?: string;  // optional property
}

const user: User = {
  name: "Alice",
  age: 30
};
\`\`\`

This ensures that any User object has the required structure.`;
      } else {
        response = "I'd be happy to provide an example. What topic would you like to see?";
      }
    } else if (userMessage.toLowerCase().includes('types') && userMessage.includes('?')) {
      response = "Interfaces and types are similar but have subtle differences. Interfaces can be extended and merged, making them better for object shapes. Types are more flexible and can represent unions, intersections, and primitives. For object definitions, interfaces are conventional.";
    } else {
      response = this.context.length > 1
        ? "Got it! I'll keep that in mind as we continue our conversation."
        : "Hello! How can I help you today?";
    }

    return createMessage({ role: 'assistant', content: response });
  }
}

async function main() {
  console.log('='.repeat(70));
  console.log('AgentKit TypeScript - Memory Hierarchy Pattern Example');
  console.log('='.repeat(70));
  console.log();

  console.log('✓ Using mock agents (no API keys required)');
  console.log();

  // Example 1: Personal assistant with memory
  console.log('-'.repeat(70));
  console.log('Example 1: Personal Assistant Conversation');
  console.log('-'.repeat(70));
  console.log();

  const mockLLM1 = new MockConversationalLLM();
  const assistant = new ConversationalAgent({
    agent: mockLLM1,
    systemPrompt: 'You are a helpful personal assistant. Remember details about the user and reference them in future responses.',
    maxHistoryLength: 10,
  });

  console.log('System: You are a helpful personal assistant.');
  console.log('Max history: 10 messages');
  console.log();

  // Turn 1
  console.log('User: My name is Alex and I\'m a software engineer.');
  let response = await assistant.process(
    createMessage({ role: 'user', content: 'My name is Alex and I\'m a software engineer.' })
  );
  console.log(`Assistant: ${response.content}`);
  console.log();

  // Turn 2
  console.log('User: I\'m working on a TypeScript project using AgentKit.');
  response = await assistant.process(
    createMessage({ role: 'user', content: 'I\'m working on a TypeScript project using AgentKit.' })
  );
  console.log(`Assistant: ${response.content}`);
  console.log();

  // Turn 3 - Test memory
  console.log('User: What was my name again?');
  response = await assistant.process(
    createMessage({ role: 'user', content: 'What was my name again?' })
  );
  console.log(`Assistant: ${response.content}`);
  console.log();

  // Turn 4 - Test memory
  console.log('User: What am I working on?');
  response = await assistant.process(
    createMessage({ role: 'user', content: 'What am I working on?' })
  );
  console.log(`Assistant: ${response.content}`);
  console.log();

  // Example 2: Technical advisor conversation
  console.log('-'.repeat(70));
  console.log('Example 2: Technical Advisor Conversation');
  console.log('-'.repeat(70));
  console.log();

  const mockLLM2 = new MockConversationalLLM();
  const advisor = new ConversationalAgent({
    agent: mockLLM2,
    systemPrompt: 'You are a technical advisor specializing in system design. Build on previous context in your responses.',
    maxHistoryLength: 15,
  });

  console.log('System: Technical advisor specializing in system design.');
  console.log();

  // Turn 1
  console.log('User: I need to design a microservices architecture.');
  response = await advisor.process(
    createMessage({ role: 'user', content: 'I need to design a microservices architecture.' })
  );
  console.log(`Advisor: ${response.content}`);
  console.log();

  // Turn 2
  console.log('User: The system needs to handle 10,000 requests per second.');
  response = await advisor.process(
    createMessage({ role: 'user', content: 'The system needs to handle 10,000 requests per second.' })
  );
  console.log(`Advisor: ${response.content}`);
  console.log();

  // Turn 3
  console.log('User: What database would you recommend?');
  response = await advisor.process(
    createMessage({ role: 'user', content: 'What database would you recommend?' })
  );
  console.log(`Advisor: ${response.content}`);
  console.log();

  // Turn 4
  console.log('User: How should I handle authentication across services?');
  response = await advisor.process(
    createMessage({ role: 'user', content: 'How should I handle authentication across services?' })
  );
  console.log(`Advisor: ${response.content}`);
  console.log();

  // Example 3: Tutoring session with context
  console.log('-'.repeat(70));
  console.log('Example 3: Programming Tutor Session');
  console.log('-'.repeat(70));
  console.log();

  const mockLLM3 = new MockConversationalLLM();
  const tutor = new ConversationalAgent({
    agent: mockLLM3,
    systemPrompt: 'You are a patient programming tutor. Build on previous questions and adapt explanations to the student\'s level.',
    maxHistoryLength: 20,
  });

  console.log('System: Patient programming tutor.');
  console.log();

  // Turn 1
  console.log('User: I\'m new to TypeScript. What are interfaces?');
  response = await tutor.process(
    createMessage({ role: 'user', content: 'I\'m new to TypeScript. What are interfaces?' })
  );
  console.log(`Tutor: ${response.content}`);
  console.log();

  // Turn 2
  console.log('User: Can you give me a simple example?');
  response = await tutor.process(
    createMessage({ role: 'user', content: 'Can you give me a simple example?' })
  );
  console.log(`Tutor: ${response.content}`);
  console.log();

  // Turn 3
  console.log('User: How are interfaces different from types?');
  response = await tutor.process(
    createMessage({ role: 'user', content: 'How are interfaces different from types?' })
  );
  console.log(`Tutor: ${response.content}`);
  console.log();

  console.log('-'.repeat(70));
  console.log('✓ All memory/conversation examples completed!');
  console.log();
  console.log('Key Features Demonstrated:');
  console.log('  • Context preservation across turns');
  console.log('  • Memory of previous interactions');
  console.log('  • Natural multi-turn dialogue');
  console.log('  • Progressive context building');
  console.log('  • Working memory with history limits');
  console.log();
  console.log('Production Usage:');
  console.log('  Replace MockConversationalLLM with real LLM adapters:');
  console.log('  - AnthropicAdapter (Claude for conversations)');
  console.log('  - OpenAIAdapter (GPT-4 for chat)');
  console.log('  - LLMs will provide natural, context-aware responses');
  console.log();
  console.log('Use Cases:');
  console.log('  • Personal assistants');
  console.log('  • Customer support chatbots');
  console.log('  • Technical advisors');
  console.log('  • Educational tutors');
  console.log('  • Interactive troubleshooting');
  console.log();
  console.log('Pattern Comparison:');
  console.log('  • Conversational: Multi-turn with memory');
  console.log('  • Task: One-shot without memory');
  console.log('  • Planning: Multi-step with dependencies');
  console.log('  • Autonomous: Self-directed goal pursuit');
  console.log('-'.repeat(70));
}

main().catch((error) => {
  console.error('Error:', error.message);
  process.exit(1);
});
