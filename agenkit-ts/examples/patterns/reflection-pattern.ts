/**
 * Reflection Pattern Example
 *
 * Demonstrates:
 * - Reflection pattern for iterative improvement
 * - Self-critique and refinement
 * - Quality improvement through multiple iterations
 * - Mock agents for demonstration (no API keys required)
 *
 * WHY use this pattern:
 * ✅ Improve output quality through self-review
 * ✅ Catch and fix errors automatically
 * ✅ Iteratively refine until quality threshold met
 * ✅ Reduce need for manual review cycles
 * ✅ Works with any generator/critic agent pair
 *
 * WHEN to use:
 * - Code generation that needs review
 * - Content creation requiring quality
 * - Multi-draft writing
 * - Error detection and correction
 * - Any task where iteration improves quality
 *
 * Setup:
 *   npm run build
 *   node dist/examples/patterns/reflection-pattern.js
 */

import { ReflectionAgent } from '../../src/patterns/reflection';
import { Agent, Message, createMessage } from '../../src/core/interfaces';

/**
 * Mock code generator that simulates improvement over iterations
 */
class CodeGeneratorAgent implements Agent {
  private iteration = 0;

  name(): string {
    return 'CodeGenerator';
  }

  capabilities(): string[] {
    return ['code_generation'];
  }

  async process(message: Message): Promise<Message> {
    this.iteration++;

    // Simulate improving output based on critique
    let code: string;

    if (this.iteration === 1) {
      // Initial attempt - has issues
      code = `function isPalindrome(str) {
  // Bug: doesn't handle empty strings or case sensitivity
  return str === str.split('').reverse().join('');
}`;
    } else if (this.iteration === 2) {
      // Second attempt - fixed some issues
      code = `function isPalindrome(str) {
  // Better but still missing edge cases
  if (!str) return true;
  const normalized = str.toLowerCase();
  return normalized === normalized.split('').reverse().join('');
}`;
    } else {
      // Final version - all issues fixed
      code = `/**
 * Checks if a string is a palindrome (reads the same forwards and backwards).
 *
 * @param str - The string to check
 * @returns true if the string is a palindrome, false otherwise
 *
 * @example
 * isPalindrome('racecar') // true
 * isPalindrome('hello')   // false
 * isPalindrome('')        // true (empty string is palindrome)
 */
function isPalindrome(str: string): boolean {
  if (!str) return true;

  // Remove non-alphanumeric and convert to lowercase
  const cleaned = str.replace(/[^a-z0-9]/gi, '').toLowerCase();
  const reversed = cleaned.split('').reverse().join('');

  return cleaned === reversed;
}`;
    }

    return createMessage({ role: 'assistant', content: code });
  }
}

/**
 * Mock code critic that evaluates code quality
 */
class CodeCriticAgent implements Agent {
  name(): string {
    return 'CodeCritic';
  }

  capabilities(): string[] {
    return ['code_review'];
  }

  async process(message: Message): Promise<Message> {
    const code = message.content;

    // Simulate quality scoring based on code characteristics
    let score = 0.5; // Base score

    // Check for documentation
    if (code.includes('/**') || code.includes('@param') || code.includes('@returns')) {
      score += 0.2;
    }

    // Check for type annotations
    if (code.includes(': string') || code.includes(': boolean')) {
      score += 0.1;
    }

    // Check for proper cleaning/normalization
    if (code.includes('replace') || code.includes('cleaned')) {
      score += 0.1;
    }

    // Check for edge case handling
    if (code.includes('!str') || code.includes('empty')) {
      score += 0.1;
    }

    score = Math.min(1.0, score);

    // Generate feedback based on score
    let feedback: string;
    if (score < 0.7) {
      feedback = 'Issues found:\n' +
        '1. Missing comprehensive documentation\n' +
        '2. No type annotations for TypeScript\n' +
        '3. Doesn\'t handle non-alphanumeric characters\n' +
        '4. Case sensitivity not properly addressed';
    } else if (score < 0.9) {
      feedback = 'Good progress! Minor improvements needed:\n' +
        '1. Add JSDoc comments with examples\n' +
        '2. Consider TypeScript type annotations';
    } else {
      feedback = 'Excellent! Code is well-documented, handles edge cases, and follows best practices.';
    }

    const critique = JSON.stringify({ score, feedback });
    return createMessage({ role: 'assistant', content: critique });
  }
}

async function main() {
  console.log('='.repeat(60));
  console.log('AgentKit TypeScript - Reflection Pattern Example');
  console.log('='.repeat(60));
  console.log();

  console.log('✓ Using mock agents (no API keys required)');
  console.log();

  // Example 1: Basic reflection
  console.log('-'.repeat(60));
  console.log('Example 1: Basic Reflection - Code Generation');
  console.log('-'.repeat(60));
  console.log();

  const generator = new CodeGeneratorAgent();
  const critic = new CodeCriticAgent();

  const codeAgent = new ReflectionAgent({
    agent: generator,
    reflector: critic,
    maxIterations: 3,
  });

  const codePrompt = createMessage({
    role: 'user',
    content: 'Write a TypeScript function to check if a string is a palindrome.',
  });

  console.log(`Task: ${codePrompt.content}`);
  console.log();
  console.log('Starting reflection process (max 3 iterations)...');
  console.log();

  const codeResult = await codeAgent.process(codePrompt);

  console.log('Final refined code:');
  console.log('-'.repeat(60));
  console.log(codeResult.content);
  console.log('-'.repeat(60));
  console.log();

  if (codeResult.metadata?.reflectionIterations) {
    console.log(`Completed in ${codeResult.metadata.reflectionIterations} iterations`);
  }
  console.log();

  console.log('-'.repeat(60));
  console.log('✓ Reflection pattern example completed!');
  console.log();
  console.log('Key Takeaways:');
  console.log('  • Reflection improves quality through iteration');
  console.log('  • Generator creates output, critic provides feedback');
  console.log('  • Refinement continues until quality threshold met');
  console.log('  • Works with any generator/critic agent pair');
  console.log('  • Suitable for code, content, analysis, and more');
  console.log();
  console.log('Production Usage:');
  console.log('  Replace mock agents with real LLM adapters:');
  console.log('  - AnthropicAdapter (Claude)');
  console.log('  - OpenAIAdapter (GPT-4)');
  console.log('  - Or any custom Agent implementation');
  console.log();
  console.log('Pattern examples demonstrate the workflow without API costs!');
  console.log('-'.repeat(60));
}

main().catch((error) => {
  console.error('Error:', error.message);
  process.exit(1);
});
