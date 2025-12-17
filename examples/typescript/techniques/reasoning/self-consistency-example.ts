/**
 * Self-Consistency Reasoning Example
 *
 * This example demonstrates the Self-Consistency reasoning technique,
 * which improves reliability by generating multiple independent reasoning
 * paths and using voting to select the most consistent answer.
 *
 * Reference: "Self-Consistency Improves Chain of Thought Reasoning in Language Models"
 * Wang et al., 2022 - https://arxiv.org/abs/2203.11171
 */

import { Agent, Message, createMessage } from '../../../../agenkit-ts/src/core/interfaces';
import { SelfConsistencyAgent } from '../../../../agenkit-ts/src/techniques/reasoning/self-consistency';

/**
 * Simple mock agent that simulates varying responses.
 */
class SimpleAgent implements Agent {
  readonly name: string;
  readonly capabilities: string[];
  private readonly responses: string[];
  private index: number;

  constructor(responses: string[]) {
    this.name = 'simple_agent';
    this.capabilities = ['reasoning'];
    this.responses = responses;
    this.index = 0;
  }

  async process(message: Message): Promise<Message> {
    const response = this.responses[this.index % this.responses.length];
    this.index++;
    return createMessage('assistant', response);
  }
}

/**
 * Example 1: Basic Self-Consistency with Majority Voting
 */
async function example1(): Promise<void> {
  console.log('Example 1: Basic Self-Consistency with Majority Voting');
  console.log('-'.repeat(60));

  // Create a base agent that provides varying answers
  const baseAgent = new SimpleAgent([
    'After calculation, the answer is 42.',
    "Let me think... I believe it's 43.",
    'The answer is 42.',
    'Definitely 42.',
    'I think the answer is 42.',
  ]);

  // Wrap with Self-Consistency using majority voting
  const sc = new SelfConsistencyAgent(baseAgent, {
    numSamples: 5,
    votingStrategy: 'majority',
  });

  const message = createMessage('user', 'What is 6 * 7?');
  const response = await sc.process(message);

  console.log(`Question: ${message.content}`);
  console.log(`Consensus Answer: ${response.content}`);
  console.log(`Consistency Score: ${(response.metadata?.consistency_score as number).toFixed(2)}`);
  console.log(`Number of Samples: ${response.metadata?.num_samples}`);

  // Show individual samples
  const samples = response.metadata?.samples as string[];
  console.log('\nIndividual Samples:');
  samples.forEach((sample, i) => {
    console.log(`  ${i + 1}. ${sample}`);
  });

  // Show extracted answers
  const extractedAnswers = response.metadata?.extracted_answers as string[];
  console.log('\nExtracted Answers:');
  extractedAnswers.forEach((answer, i) => {
    console.log(`  ${i + 1}. ${answer}`);
  });

  console.log();
}

/**
 * Example 2: Weighted Voting Strategy
 */
async function example2(): Promise<void> {
  console.log('Example 2: Weighted Voting Strategy');
  console.log('-'.repeat(60));

  // Create agent with responses of varying lengths
  const baseAgent = new SimpleAgent([
    'Paris.',
    'Paris.',
    'Paris.',
    'After extensive analysis of historical data, geographical considerations, and political significance, I can confidently conclude that the capital of France is London.',
  ]);

  // Use weighted voting (longer responses get more weight)
  const sc = new SelfConsistencyAgent(baseAgent, {
    numSamples: 4,
    votingStrategy: 'weighted',
  });

  const message = createMessage('user', 'What is the capital of France?');
  const response = await sc.process(message);

  console.log(`Question: ${message.content}`);
  console.log(`Weighted Consensus: ${response.content}`);
  console.log(`Consistency Score: ${(response.metadata?.consistency_score as number).toFixed(2)}`);

  console.log('\nNote: Weighted voting can favor more detailed responses,');
  console.log('which may not always be correct. In this case, the longer');
  console.log('response outweighs three shorter correct answers.');

  console.log();
}

/**
 * Example 3: Custom Answer Extractor
 */
async function example3(): Promise<void> {
  console.log('Example 3: Custom Answer Extractor');
  console.log('-'.repeat(60));

  // Create agent with structured output format
  const baseAgent = new SimpleAgent([
    'Analysis: Step 1, Step 2. FINAL_ANSWER: 42',
    'Let me calculate... FINAL_ANSWER: 42',
    'After thinking through this... FINAL_ANSWER: 43',
    'My conclusion is FINAL_ANSWER: 42',
    'The result is FINAL_ANSWER: 42',
  ]);

  // Custom extractor for "FINAL_ANSWER: X" pattern
  const customExtractor = (text: string): string => {
    const match = text.match(/FINAL_ANSWER:\s*(\S+)/);
    return match ? match[1] : text;
  };

  const sc = new SelfConsistencyAgent(baseAgent, {
    numSamples: 5,
    votingStrategy: 'majority',
    answerExtractor: customExtractor,
  });

  const message = createMessage('user', 'Calculate 6 * 7');
  const response = await sc.process(message);

  console.log(`Question: ${message.content}`);
  console.log(`Consensus Answer: ${response.content}`);
  console.log(
    `Consistency Score: ${(response.metadata?.consistency_score as number).toFixed(2)} (4/5 agreed on '42')`,
  );

  const extractedAnswers = response.metadata?.extracted_answers as string[];
  console.log('\nExtracted Answers:');
  extractedAnswers.forEach((answer, i) => {
    console.log(`  ${i + 1}. ${answer}`);
  });

  console.log();
}

/**
 * Example 4: High vs Low Consistency
 */
async function example4(): Promise<void> {
  console.log('Example 4: High vs Low Consistency Comparison');
  console.log('-'.repeat(60));

  // High consistency case
  console.log('Case A: High Consistency');
  const highConsAgent = new SimpleAgent([
    'The answer is 42.',
    'The answer is 42.',
    'The answer is 42.',
    'The answer is 42.',
    'The answer is 42.',
  ]);

  const scHigh = new SelfConsistencyAgent(highConsAgent, {
    numSamples: 5,
    votingStrategy: 'majority',
  });

  const message = createMessage('user', 'What is the answer?');
  const responseHigh = await scHigh.process(message);

  console.log(`Consensus Answer: ${responseHigh.content}`);
  console.log(
    `Consistency Score: ${(responseHigh.metadata?.consistency_score as number).toFixed(2)} (perfect agreement)`,
  );

  // Low consistency case
  console.log('\nCase B: Low Consistency');
  const lowConsAgent = new SimpleAgent([
    'The answer is 40.',
    'The answer is 41.',
    'The answer is 42.',
    'The answer is 43.',
    'The answer is 44.',
  ]);

  const scLow = new SelfConsistencyAgent(lowConsAgent, {
    numSamples: 5,
    votingStrategy: 'majority',
  });

  const responseLow = await scLow.process(message);

  console.log(`Consensus Answer: ${responseLow.content}`);
  console.log(
    `Consistency Score: ${(responseLow.metadata?.consistency_score as number).toFixed(2)} (no agreement)`,
  );

  console.log('\nInterpretation:');
  console.log('- High consistency (>0.7): Strong confidence in the answer');
  console.log('- Medium consistency (0.4-0.7): Some agreement, moderate confidence');
  console.log('- Low consistency (<0.4): Little agreement, low confidence');
  console.log('\nLow consistency scores may indicate:');
  console.log('  - Ambiguous or underspecified questions');
  console.log('  - Multiple valid interpretations');
  console.log('  - Need for more samples or better prompting');

  console.log();
}

/**
 * Main function to run all examples.
 */
async function main(): Promise<void> {
  console.log('=== Self-Consistency Reasoning Examples ===\n');

  await example1();
  await example2();
  await example3();
  await example4();
}

// Run examples
main().catch(error => {
  console.error('Error running examples:', error);
  process.exit(1);
});
