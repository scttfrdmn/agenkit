/**
 * Chain-of-Thought Reasoning Example
 *
 * This example demonstrates the Chain-of-Thought (CoT) reasoning technique,
 * which encourages step-by-step reasoning through structured prompting,
 * leading to more accurate and explainable results.
 *
 * Reference: "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models"
 * Wei et al., 2022 - https://arxiv.org/abs/2201.11903
 */

import { Agent, Message, createMessage } from '../../../../agenkit-ts/src/core/interfaces';
import { ChainOfThought } from '../../../../agenkit-ts/src/techniques/reasoning/chain-of-thought';

/**
 * Simple mock agent that simulates step-by-step reasoning.
 */
class ReasoningAgent implements Agent {
  readonly name: string;
  readonly capabilities: string[];

  constructor() {
    this.name = 'reasoning_agent';
    this.capabilities = ['reasoning'];
  }

  async process(message: Message): Promise<Message> {
    const query = String(message.content);

    // Simulate step-by-step reasoning based on the query
    let response = '';

    if (query.includes('think step by step')) {
      if (query.includes('15 * 24')) {
        response = `1. First, I'll break down 15 * 24 into easier calculations.
2. 15 * 24 = 15 * (20 + 4)
3. Using the distributive property: (15 * 20) + (15 * 4)
4. Calculate 15 * 20 = 300
5. Calculate 15 * 4 = 60
6. Add them together: 300 + 60 = 360
Therefore, 15 * 24 = 360`;
      } else if (query.includes('oldest person')) {
        response = `1. List the ages given:
   - Alice: 25 years old
   - Bob: 30 years old
   - Charlie: 28 years old
2. Compare the ages:
   - Alice (25) < Bob (30)
   - Charlie (28) < Bob (30)
3. Identify the maximum age: 30
4. Determine who has age 30: Bob
Therefore, Bob is the oldest person at 30 years old.`;
      } else {
        response = `1. I'll analyze the problem systematically
2. Break it down into manageable steps
3. Solve each component carefully
4. Combine results to reach a conclusion
Therefore, the answer has been determined through logical reasoning.`;
      }
    } else {
      response = '360'; // Direct answer without reasoning
    }

    return createMessage('assistant', response);
  }
}

/**
 * Example 1: Basic Chain-of-Thought with Math Problem
 */
async function example1(): Promise<void> {
  console.log('Example 1: Basic Chain-of-Thought with Math Problem');
  console.log('-'.repeat(60));

  const baseAgent = new ReasoningAgent();
  const cot = new ChainOfThought(baseAgent);

  const message = createMessage('user', 'What is 15 * 24?');
  const response = await cot.process(message);

  console.log(`Question: ${message.content}`);
  console.log(`\nReasoning:\n${response.content}`);

  const steps = response.metadata?.reasoning_steps as string[];
  console.log(`\nExtracted Steps (${response.metadata?.num_steps} total):`);
  steps.forEach((step, i) => {
    console.log(`  ${i + 1}. ${step}`);
  });

  console.log();
}

/**
 * Example 2: Custom Prompt Template
 */
async function example2(): Promise<void> {
  console.log('Example 2: Custom Prompt Template');
  console.log('-'.repeat(60));

  const baseAgent = new ReasoningAgent();

  // Use custom prompt template
  const cot = new ChainOfThought(baseAgent, {
    promptTemplate: 'Analyze carefully step by step:\n{query}',
  });

  const message = createMessage('user', 'Who is oldest: Alice (25), Bob (30), or Charlie (28)?');
  const response = await cot.process(message);

  console.log(`Question: ${message.content}`);
  console.log(`\nReasoning:\n${response.content}`);

  const steps = response.metadata?.reasoning_steps as string[];
  console.log(`\nExtracted Steps (${response.metadata?.num_steps} total):`);
  steps.forEach((step, i) => {
    console.log(`  ${i + 1}. ${step.substring(0, 80)}${step.length > 80 ? '...' : ''}`);
  });

  console.log();
}

/**
 * Example 3: Limiting Maximum Steps
 */
async function example3(): Promise<void> {
  console.log('Example 3: Limiting Maximum Steps');
  console.log('-'.repeat(60));

  const baseAgent = new ReasoningAgent();

  // Limit to first 3 steps
  const cot = new ChainOfThought(baseAgent, {
    maxSteps: 3,
  });

  const message = createMessage('user', 'What is 15 * 24?');
  const response = await cot.process(message);

  console.log(`Question: ${message.content}`);
  console.log(`Max Steps: 3`);

  const steps = response.metadata?.reasoning_steps as string[];
  console.log(`\nExtracted Steps (limited to ${response.metadata?.num_steps}):`);
  steps.forEach((step, i) => {
    console.log(`  ${i + 1}. ${step}`);
  });

  console.log('\nNote: Only the first 3 steps are included, even though');
  console.log('the original reasoning had more steps.');

  console.log();
}

/**
 * Example 4: Parsing Different Step Formats
 */
async function example4(): Promise<void> {
  console.log('Example 4: Parsing Different Step Formats');
  console.log('-'.repeat(60));

  // Agent with bullet-point format
  const bulletAgent: Agent = {
    name: 'bullet_agent',
    async process(): Promise<Message> {
      return createMessage(
        'assistant',
        `- First, identify the key information
- Next, set up the equation
- Then, solve step by step
- Finally, verify the answer`,
      );
    },
  };

  const cot = new ChainOfThought(bulletAgent);

  const message = createMessage('user', 'Solve this problem');
  const response = await cot.process(message);

  console.log(`Question: ${message.content}`);
  console.log(`\nFormat: Bullet points`);

  const steps = response.metadata?.reasoning_steps as string[];
  console.log(`\nExtracted Steps:`);
  steps.forEach((step, i) => {
    console.log(`  ${i + 1}. ${step}`);
  });

  console.log('\nCoT automatically detects common formats:');
  console.log('  - Numbered steps (1. 2. 3.)');
  console.log('  - Bullet points (- * •)');
  console.log('  - Custom delimiters');

  console.log();
}

/**
 * Example 5: Comparing With and Without CoT
 */
async function example5(): Promise<void> {
  console.log('Example 5: Comparing With and Without CoT');
  console.log('-'.repeat(60));

  const baseAgent = new ReasoningAgent();

  // Without CoT (direct question)
  console.log('WITHOUT Chain-of-Thought:');
  const directResponse = await baseAgent.process(createMessage('user', 'What is 15 * 24?'));
  console.log(`Answer: ${directResponse.content}`);
  console.log('(No reasoning shown)');

  console.log('\nWITH Chain-of-Thought:');
  const cot = new ChainOfThought(baseAgent);
  const cotResponse = await cot.process(createMessage('user', 'What is 15 * 24?'));

  const steps = cotResponse.metadata?.reasoning_steps as string[];
  console.log(`Answer with reasoning (${steps.length} steps):`);
  steps.slice(0, 3).forEach((step, i) => {
    console.log(`  ${i + 1}. ${step}`);
  });
  console.log('  ...');

  console.log('\nBenefits of CoT:');
  console.log('  ✓ Explainable reasoning process');
  console.log('  ✓ Easier to debug incorrect answers');
  console.log('  ✓ More accurate results through decomposition');
  console.log('  ✓ Better transparency for users');

  console.log();
}

/**
 * Main function to run all examples.
 */
async function main(): Promise<void> {
  console.log('=== Chain-of-Thought Reasoning Examples ===\n');

  await example1();
  await example2();
  await example3();
  await example4();
  await example5();
}

// Run examples
main().catch((error) => {
  console.error('Error running examples:', error);
  process.exit(1);
});
