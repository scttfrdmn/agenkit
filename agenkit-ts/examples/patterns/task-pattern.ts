/**
 * Task Pattern Example
 *
 * Demonstrates:
 * - One-shot agent execution with lifecycle management
 * - Automatic resource cleanup
 * - Timeout and retry support
 * - Prevention of accidental reuse
 *
 * WHY use this pattern:
 * ✅ Explicit one-shot semantics (execute once, then cleanup)
 * ✅ Automatic resource cleanup after completion
 * ✅ Built-in timeout and retry support
 * ✅ Prevention of accidental reuse after completion
 * ✅ Clean API for single-use operations
 *
 * WHEN to use:
 * - One-time operations (summarize document, classify text, extract entities)
 * - Tasks requiring resource cleanup (close connections, release memory)
 * - Operations with timeout requirements
 * - Tasks that need retry logic
 * - Anywhere you need guaranteed cleanup after execution
 *
 * WHEN NOT to use:
 * - Multi-turn conversations (use ConversationalAgent)
 * - Stateful interactions across multiple calls
 * - Long-running background processes
 *
 * Setup:
 *   npm run build
 *   node dist/examples/patterns/task-pattern.js
 */

import { Task } from '../../src/patterns/task';
import { Agent, Message, createMessage } from '../../src/core/interfaces';

/**
 * Mock document summarization agent for demonstration
 */
class DocumentSummarizationAgent implements Agent {
  private connections: string[] = [];

  constructor() {}  // No LLM needed for mock

  name(): string {
    return 'DocumentSummarizer';
  }

  capabilities(): string[] {
    return ['summarization', 'text-processing'];
  }

  async process(message: Message): Promise<Message> {
    // Simulate resource allocation
    this.connections.push(`connection-${Date.now()}`);

    // Mock summarization based on content
    const content = message.content;
    let summary = '';

    if (content.includes('TypeScript')) {
      summary = 'TypeScript is a strongly typed programming language that builds on JavaScript, offering static typing and excellent tooling support. It compiles to clean JavaScript and has gained widespread adoption for its ability to scale to large codebases.';
    } else if (content.includes('AgentKit')) {
      summary = 'AgentKit is a framework for building AI agents with a composable architecture and support for multiple patterns.';
    } else {
      // Generic summary
      const sentences = content.split('. ').filter(s => s.trim());
      summary = sentences.slice(0, 2).join('. ') + (sentences.length > 2 ? '.' : '');
    }

    return createMessage({ role: 'assistant', content: summary });
  }

  async cleanup(): Promise<void> {
    // Clean up resources
    this.connections = [];
    console.log('  🧹 Cleaned up resources');
  }
}

/**
 * Mock text classification agent
 */
class TextClassificationAgent implements Agent {
  constructor() {}

  name(): string {
    return 'TextClassifier';
  }

  capabilities(): string[] {
    return ['classification', 'categorization'];
  }

  async process(message: Message): Promise<Message> {
    const text = message.content.toLowerCase();
    let classification = '';

    if (text.includes('troubleshoot') || text.includes('issue') || text.includes('help') || text.includes('account')) {
      classification = 'Category: Support\n\nThis text contains support-related keywords indicating a customer service inquiry or technical assistance request.';
    } else if (text.includes('revenue') || text.includes('quarter') || text.includes('increased') || text.includes('sales')) {
      classification = 'Category: Business\n\nThis text discusses business metrics, financial performance, or organizational outcomes.';
    } else if (text.includes('machine learning') || text.includes('training data') || text.includes('model')) {
      classification = 'Category: Technical\n\nThis text contains technical terminology related to software engineering, data science, or technology implementation.';
    } else if (text.includes('whitepaper') || text.includes('download') || text.includes('free') || text.includes('learn more')) {
      classification = 'Category: Marketing\n\nThis text uses marketing language and calls-to-action typical of promotional content.';
    } else {
      classification = 'Category: General\n\nThis text does not fit clearly into specialized categories and appears to be general communication.';
    }

    return createMessage({ role: 'assistant', content: classification });
  }
}

/**
 * Mock entity extraction agent
 */
class EntityExtractionAgent implements Agent {
  constructor() {}

  name(): string {
    return 'EntityExtractor';
  }

  capabilities(): string[] {
    return ['entity-extraction', 'ner'];
  }

  async process(message: Message): Promise<Message> {
    const text = message.content;
    let entities = '';

    if (text.includes('Apple') || text.includes('Tim Cook') || text.includes('Austin')) {
      entities = `**Extracted Entities:**

**Organizations:**
• Apple Inc. - Technology company

**People:**
• Tim Cook - CEO of Apple Inc.

**Locations:**
• Austin, Texas - City location for new facility

**Monetary Values:**
• $1 billion - Investment amount

**Dates/Time:**
• "yesterday" - Referenced time
• "next month" - Future timeframe
• "by 2025" - Target completion date

**Numbers:**
• 5,000 - New jobs to be created`;
    } else {
      entities = `**Extracted Entities:**

Based on the provided text, entities would be extracted and categorized by type (Organizations, People, Locations, Dates, etc.).`;
    }

    return createMessage({ role: 'assistant', content: entities });
  }
}

async function main() {
  console.log('='.repeat(70));
  console.log('AgentKit TypeScript - Task Pattern Example');
  console.log('='.repeat(70));
  console.log();

  console.log('✓ Using mock agents (no API keys required)');
  console.log();

  // Example 1: Basic task usage
  console.log('-'.repeat(70));
  console.log('Example 1: Basic Task Usage');
  console.log('-'.repeat(70));
  console.log();

  const summarizer = new DocumentSummarizationAgent();
  const task1 = new Task(summarizer);

  const doc1 = `
TypeScript is a strongly typed programming language that builds on JavaScript.
It adds optional static typing to the language, which helps catch errors during
development. TypeScript code compiles to clean, readable JavaScript that runs
anywhere JavaScript runs. The language has gained widespread adoption in the
web development community due to its excellent tooling support and ability to
scale to large codebases.
`;

  console.log('Document to summarize:');
  console.log(doc1);
  console.log();

  console.log('Executing task...');
  const message1 = createMessage({
    role: 'user',
    content: `Summarize this text:\n\n${doc1}`,
  });

  const result1 = await task1.execute(message1);

  console.log(`\n✅ Summary:`);
  console.log(result1.content);
  console.log();
  console.log(`Task completed: ${task1.isCompleted}`);
  console.log(`Result available: ${task1.result !== null}`);
  console.log();

  // Cleanup
  await task1.cleanup();

  // Example 2: Task prevents reuse
  console.log('-'.repeat(70));
  console.log('Example 2: Task Reuse Prevention');
  console.log('-'.repeat(70));
  console.log();

  const classifier = new TextClassificationAgent();
  const task2 = new Task(classifier);

  const text1 = 'Please help me troubleshoot an issue with my account login.';

  console.log(`Text: "${text1}"`);
  console.log();

  const message2 = createMessage({ role: 'user', content: text1 });
  const result2 = await task2.execute(message2);

  console.log(`✅ Classification: ${result2.content}`);
  console.log();

  // Try to reuse the same task
  console.log('Attempting to reuse the same task...');
  try {
    await task2.execute(message2);
    console.log('✗ Should not reach here');
  } catch (error) {
    console.log(`✓ Reuse prevented: ${error instanceof Error ? error.message : 'Error'}`);
  }
  console.log();

  console.log('Creating a new task for second execution...');
  const task2b = new Task(classifier);
  const text2 = 'Our Q4 revenue increased by 25% compared to last quarter.';
  const message2b = createMessage({ role: 'user', content: text2 });
  const result2b = await task2b.execute(message2b);

  console.log(`Text: "${text2}"`);
  console.log(`✅ Classification: ${result2b.content}`);
  console.log();

  await task2.cleanup();
  await task2b.cleanup();

  // Example 3: Multiple one-shot tasks
  console.log('-'.repeat(70));
  console.log('Example 3: Multiple One-Shot Tasks');
  console.log('-'.repeat(70));
  console.log();

  const documents = [
    'Machine learning models require large amounts of training data.',
    'The company announced a merger with its largest competitor.',
    'Download our free whitepaper to learn more about our solutions.',
  ];

  console.log('Classifying multiple documents using one-shot tasks:');
  console.log();

  for (let i = 0; i < documents.length; i++) {
    const doc = documents[i];
    const agent = new TextClassificationAgent();
    const task = new Task(agent);

    console.log(`${i + 1}. "${doc}"`);

    const message = createMessage({ role: 'user', content: doc });
    const result = await task.execute(message);

    console.log(`   → ${result.content}`);
    console.log();

    await task.cleanup();
  }

  // Example 4: Entity extraction task
  console.log('-'.repeat(70));
  console.log('Example 4: Entity Extraction Task');
  console.log('-'.repeat(70));
  console.log();

  const extractor = new EntityExtractionAgent();
  const task4 = new Task(extractor);

  const newsText = `
Apple Inc. announced yesterday that CEO Tim Cook will visit their new facility
in Austin, Texas next month. The company plans to invest $1 billion in the
expansion, creating 5,000 new jobs by 2025.
`;

  console.log('Text:');
  console.log(newsText);
  console.log();

  console.log('Extracting entities...');
  const message4 = createMessage({
    role: 'user',
    content: `Extract entities from this text:\n\n${newsText}`,
  });

  const result4 = await task4.execute(message4);

  console.log(`\n✅ Extracted entities:`);
  console.log(result4.content);
  console.log();

  await task4.cleanup();

  // Example 5: Task lifecycle demonstration
  console.log('-'.repeat(70));
  console.log('Example 5: Task Lifecycle');
  console.log('-'.repeat(70));
  console.log();

  const lifecycleAgent = new DocumentSummarizationAgent();
  const task5 = new Task(lifecycleAgent);

  console.log('Task states:');
  console.log(`  Initial - Completed: ${task5.isCompleted}, Result: ${task5.result !== null}`);

  const message5 = createMessage({
    role: 'user',
    content: 'Summarize: AgentKit is a framework for building AI agents.',
  });

  await task5.execute(message5);
  console.log(`  After execute - Completed: ${task5.isCompleted}, Result: ${task5.result !== null}`);

  await task5.cleanup();
  console.log(`  After cleanup - Task lifecycle complete`);
  console.log();

  // Example 6: Pattern comparison
  console.log('-'.repeat(70));
  console.log('Example 6: When to Use Task vs Agent');
  console.log('-'.repeat(70));
  console.log();

  console.log('📌 Use Task pattern when:');
  console.log('  • One-shot operation (summarize, classify, extract)');
  console.log('  • Need automatic resource cleanup');
  console.log('  • Want to prevent accidental reuse');
  console.log('  • Have cleanup requirements');
  console.log('  • Processing independent items in a loop');
  console.log();

  console.log('📌 Use Agent directly when:');
  console.log('  • Multi-turn conversation');
  console.log('  • Stateful interaction');
  console.log('  • Need to maintain context across calls');
  console.log('  • Long-running process');
  console.log();

  console.log('💡 Example use cases:');
  console.log('  Task: Batch document summarization, email classification');
  console.log('  Agent: Chatbot, conversational assistant');
  console.log();

  console.log('-'.repeat(70));
  console.log('✓ All task pattern examples completed!');
  console.log();
  console.log('Key Benefits of Task Pattern:');
  console.log('  • One-shot semantics (execute once, cleanup)');
  console.log('  • Automatic resource management');
  console.log('  • Prevents accidental reuse');
  console.log('  • Clean API for single-use operations');
  console.log('  • Perfect for batch processing');
  console.log();
  console.log('Production Usage:');
  console.log('  Replace mock agents with real LLM adapters:');
  console.log('  - AnthropicAdapter (Claude for text processing)');
  console.log('  - OpenAIAdapter (GPT-4 for classification/extraction)');
  console.log('  - LLMs will provide dynamic, high-quality results');
  console.log();
  console.log('When to Use Task Pattern:');
  console.log('  • Document summarization (one doc = one task)');
  console.log('  • Text classification (one text = one task)');
  console.log('  • Entity extraction (one extraction = one task)');
  console.log('  • Any one-shot operation with cleanup needs');
  console.log();
  console.log('Pattern Comparison:');
  console.log('  • Task: One-shot with cleanup');
  console.log('  • Conversational: Multi-turn with memory');
  console.log('  • Planning: Multi-step with dependencies');
  console.log('  • ReAct: Reasoning with tools');
  console.log('-'.repeat(70));
}

main().catch((error) => {
  console.error('Error:', error.message);
  process.exit(1);
});
