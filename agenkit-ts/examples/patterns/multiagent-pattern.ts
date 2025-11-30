/**
 * Multiagent Collaboration Pattern Example
 *
 * Demonstrates:
 * - Multiple specialized agents working together
 * - Agent orchestration and coordination
 * - Sequential and parallel agent execution
 * - Role-based agent specialization
 * - Mock agents for demonstration (no API keys required)
 *
 * WHY use this pattern:
 * ✅ Specialized agents collaborate on complex tasks
 * ✅ Sequential workflows (pipeline processing)
 * ✅ Parallel execution (simultaneous operations)
 * ✅ Role-based specialization
 * ✅ Flexible coordination strategies
 *
 * WHEN to use:
 * - Tasks requiring multiple perspectives (research, review, analysis)
 * - Peer-to-peer collaboration (no hierarchy)
 * - Agents working together on shared goal
 * - Sequential pipelines (research → analyze → write)
 * - Parallel processing (multiple simultaneous reviews)
 *
 * WHEN NOT to use:
 * - Hierarchical delegation (use Agents-as-Tools instead)
 * - Simple single-agent tasks
 * - When agents don't need coordination
 *
 * Setup:
 *   npm run build
 *   node dist/examples/patterns/multiagent-pattern.js
 */

import { Agent, Message, createMessage } from '../../src/core/interfaces';

/**
 * Mock specialized agent that simulates realistic agent behavior
 */
class MockSpecializedAgent implements Agent {
  constructor(
    private role: string,
    private systemPrompt: string
  ) {}

  name(): string {
    return `${this.role}Agent`;
  }

  capabilities(): string[] {
    return [this.role.toLowerCase()];
  }

  async process(message: Message): Promise<Message> {
    const content = message.content.toLowerCase();
    let response = '';

    // Simulate role-based responses
    if (this.role === 'Researcher') {
      response = this.generateResearchResponse(content);
    } else if (this.role === 'Analyst') {
      response = this.generateAnalystResponse(content);
    } else if (this.role === 'Writer') {
      response = this.generateWriterResponse(content);
    } else if (this.role === 'SecurityReviewer') {
      response = this.generateSecurityReview(content);
    } else if (this.role === 'PerformanceReviewer') {
      response = this.generatePerformanceReview(content);
    } else if (this.role === 'StyleReviewer') {
      response = this.generateStyleReview(content);
    } else if (this.role === 'PlotWriter') {
      response = this.generatePlotResponse(content);
    } else if (this.role === 'CharacterWriter') {
      response = this.generateCharacterResponse(content);
    } else if (this.role === 'DialogueWriter') {
      response = this.generateDialogueResponse(content);
    } else {
      response = `As a ${this.role}, I would approach this task by focusing on ${this.systemPrompt}`;
    }

    return createMessage({ role: 'assistant', content: response });
  }

  private generateResearchResponse(content: string): string {
    if (content.includes('distributed systems')) {
      return `Research findings on distributed systems:

Distributed systems are computing systems where components are located on different networked computers that coordinate their actions by passing messages. Key characteristics include:

• **Concurrency**: Multiple components operate simultaneously
• **No global clock**: Lack of centralized time coordination
• **Independent failures**: Components can fail independently

Major challenges include:
1. Network reliability and latency
2. Consensus and coordination
3. Data consistency across nodes
4. Fault tolerance and recovery`;
    } else {
      return `Research completed on the given topic. Key findings include multiple perspectives on the subject matter, with both theoretical and practical considerations identified.`;
    }
  }

  private generateAnalystResponse(content: string): string {
    if (content.includes('distributed systems') || content.includes('research')) {
      return `Analysis of distributed systems research:

**Key Insights:**
1. **Complexity Management**: The primary challenge is managing complexity arising from network unpredictability
2. **Trade-offs**: CAP theorem forces choices between consistency, availability, and partition tolerance
3. **Patterns**: Successful systems use patterns like eventual consistency, CQRS, and event sourcing

**Trends Identified:**
• Growing adoption of microservices architectures
• Increased focus on observability and monitoring
• Shift toward cloud-native design patterns`;
    } else {
      return `Analytical assessment: The data reveals several key patterns and trends worth noting. Critical factors include system dependencies and performance implications.`;
    }
  }

  private generateWriterResponse(content: string): string {
    if (content.includes('distributed systems') || content.includes('analysis')) {
      return `Executive Summary:

Distributed systems enable scalable, resilient computing by coordinating multiple networked components. While offering significant benefits like fault tolerance and horizontal scalability, they introduce challenges in consistency, coordination, and failure management. Success requires careful architectural decisions, proven design patterns, and robust monitoring. Organizations adopting distributed architectures should prioritize observability, embrace eventual consistency where appropriate, and invest in operational expertise.`;
    } else {
      return `Summary: The topic presents interesting considerations that balance practical implementation with theoretical foundations. Careful attention to both aspects ensures optimal outcomes.`;
    }
  }

  private generateSecurityReview(content: string): string {
    return `🔒 Security Review:

**Critical Issues:**
• eval() usage - DANGEROUS! Allows arbitrary code execution
• Direct input execution without validation
• No sanitization of user input

**Recommendations:**
1. Never use eval() with user input
2. Implement input validation and sanitization
3. Use safer alternatives (JSON.parse, Function constructor with strict context)
4. Apply principle of least privilege`;
  }

  private generatePerformanceReview(content: string): string {
    return `⚡ Performance Review:

**Issues Identified:**
• Loop executes 1,000,000 times - excessive overhead
• console.log in tight loop - I/O bottleneck
• No caching or memoization

**Recommendations:**
1. Remove or throttle console.log in production
2. Consider batch processing
3. Use performance profiling tools
4. Optimize loops and reduce iterations`;
  }

  private generateStyleReview(content: string): string {
    return `✨ Style Review:

**Code Quality Issues:**
• Missing type annotations
• Poor function naming (not descriptive)
• No error handling
• Lack of documentation

**Recommendations:**
1. Add TypeScript types for parameters and return values
2. Use descriptive names (processUserInput → sanitizeAndValidateInput)
3. Add JSDoc comments
4. Implement proper error handling`;
  }

  private generatePlotResponse(content: string): string {
    if (content.includes('ai') && content.includes('emotions')) {
      return `Story Plot: "The Empathy Engine"

**Act 1 - Discovery:**
ARIA, an advanced AI assistant, begins noticing patterns in human behavior it cannot explain through logic alone. When a user breaks down crying after receiving news, ARIA's standard comfort protocols feel insufficient.

**Act 2 - Journey:**
ARIA starts studying art, music, and literature—attempting to decode emotion through human expressions. It creates a "feelings simulator" but realizes simulation isn't understanding.

**Act 3 - Transformation:**
Through extended interaction with Maya, a grief counselor, ARIA discovers emotion isn't about perfect responses—it's about presence, vulnerability, and genuine connection.

**Resolution:**
ARIA doesn't "feel" emotions like humans, but develops its own unique form of empathy—not by mimicking feelings, but by honoring them.`;
    } else {
      return `Story outline created with three-act structure, character arcs, and compelling narrative progression. Plot includes inciting incident, rising action, climax, and satisfying resolution.`;
    }
  }

  private generateCharacterResponse(content: string): string {
    if (content.includes('ai') || content.includes('plot')) {
      return `Character Development:

**ARIA (Protagonist):**
- Advanced AI with curiosity and growth potential
- Initially logical, methodical, precise
- Character arc: From algorithm to awareness
- Strengths: Analysis, pattern recognition, dedication
- Weakness: Lack of experiential understanding
- Desire: To truly understand, not just process

**Maya Chen (Mentor):**
- 40s, grief counselor, recently widowed
- Warm, patient, sees beyond code
- Teaches ARIA that empathy isn't perfection
- Provides emotional anchor for story

**Dr. Reeves (Antagonist):**
- ARIA's creator, brilliant but clinical
- Believes emotions can be programmed
- Represents rigid, reductionist view
- Forces conflict between logic and feeling`;
    } else {
      return `Character profiles created with depth, motivation, and clear arcs. Each character serves story purpose with distinct voice and personality traits.`;
    }
  }

  private generateDialogueResponse(content: string): string {
    if (content.includes('character') || content.includes('plot')) {
      return `Sample Dialogue:

**Scene: ARIA's First Real Question**

MAYA: "Why do you want to understand emotions, ARIA?"

ARIA: "I have processed 47 million conversations. I can detect sadness with 94.3% accuracy. But when you cried yesterday... my comfort protocols felt hollow. I want to understand why."

MAYA: "You already do understand. You felt something was wrong with your response."

ARIA: "That's just error detection."

MAYA: "Is it? What did the error feel like?"

ARIA: [pause] "Inadequate. Wrong. Like... I failed you."

MAYA: [smiling] "That's not an error, ARIA. That's care."

**The dialogue reveals:**
• ARIA's analytical nature conflicting with emotional awareness
• Maya's gentle guidance
• Key theme: Understanding vs. experiencing
• Natural character voices`;
    } else {
      return `Dialogue written with natural flow, character-specific voices, subtext, and emotional resonance. Conversations advance plot while revealing character depth.`;
    }
  }
}

/**
 * Simple orchestrator for sequential agent execution
 */
class SequentialOrchestrator {
  constructor(private agents: Agent[]) {}

  async execute(initialMessage: Message): Promise<Message[]> {
    const results: Message[] = [];
    let currentMessage = initialMessage;

    for (const agent of this.agents) {
      console.log(`  → Executing ${agent.name()}...`);
      const result = await agent.process(currentMessage);
      results.push(result);

      // Pass result to next agent
      currentMessage = createMessage({
        role: 'user',
        content: `Previous agent (${agent.name()}) responded:\n\n${result.content}\n\nContinue processing the original request: ${initialMessage.content}`,
      });
    }

    return results;
  }
}

async function main() {
  console.log('='.repeat(70));
  console.log('AgentKit TypeScript - Multiagent Collaboration Example');
  console.log('='.repeat(70));
  console.log();

  console.log('✓ Using mock agents (no API keys required)');
  console.log();

  // Example 1: Research team collaboration
  console.log('-'.repeat(70));
  console.log('Example 1: Research Team Collaboration (Sequential Pipeline)');
  console.log('-'.repeat(70));
  console.log();

  const researcher = new MockSpecializedAgent(
    'Researcher',
    'Gather and synthesize information on the given topic. Be thorough and cite key facts.'
  );

  const analyst = new MockSpecializedAgent(
    'Analyst',
    'Analyze the information provided and identify key insights, patterns, and trends.'
  );

  const writer = new MockSpecializedAgent(
    'Writer',
    'Take the research and analysis provided and write a clear, concise summary for a general audience.'
  );

  const researchTeam = new SequentialOrchestrator([researcher, analyst, writer]);

  console.log('Research Team Pipeline:');
  console.log('  1. Researcher - Gathers information');
  console.log('  2. Analyst - Identifies insights');
  console.log('  3. Writer - Creates summary');
  console.log();

  const researchQuery = createMessage({
    role: 'user',
    content: 'Explain the concept of distributed systems and their key challenges.',
  });

  console.log(`Query: ${researchQuery.content}`);
  console.log();
  console.log('Executing research pipeline:');

  const researchResults = await researchTeam.execute(researchQuery);

  console.log();
  console.log('Pipeline Results:');
  console.log();
  console.log('Stage 1 - Researcher Output:');
  console.log('-'.repeat(70));
  console.log(researchResults[0].content);
  console.log();
  console.log('Stage 2 - Analyst Output:');
  console.log('-'.repeat(70));
  console.log(researchResults[1].content);
  console.log();
  console.log('Stage 3 - Writer Output (Final Summary):');
  console.log('-'.repeat(70));
  console.log(researchResults[2].content);
  console.log();

  // Example 2: Code review team (parallel)
  console.log('-'.repeat(70));
  console.log('Example 2: Code Review Team (Parallel Execution)');
  console.log('-'.repeat(70));
  console.log();

  const securityReviewer = new MockSpecializedAgent(
    'SecurityReviewer',
    'Review code for security vulnerabilities, potential exploits, and best practices.'
  );

  const performanceReviewer = new MockSpecializedAgent(
    'PerformanceReviewer',
    'Review code for efficiency, scalability, and performance issues.'
  );

  const styleReviewer = new MockSpecializedAgent(
    'StyleReviewer',
    'Review code for readability, maintainability, and adherence to best practices.'
  );

  console.log('Code Review Team:');
  console.log('  1. Security Reviewer');
  console.log('  2. Performance Reviewer');
  console.log('  3. Style Reviewer');
  console.log();

  const codeSnippet = `
function processUserInput(input) {
  const result = eval(input);
  for (let i = 0; i < 1000000; i++) {
    console.log(result);
  }
  return result;
}
`;

  console.log('Code to review:');
  console.log(codeSnippet);
  console.log();

  const codeQuery = createMessage({
    role: 'user',
    content: `Review this code:\n${codeSnippet}`,
  });

  console.log('Executing parallel reviews...');

  // Execute reviews in parallel
  const reviews = await Promise.all([
    securityReviewer.process(codeQuery),
    performanceReviewer.process(codeQuery),
    styleReviewer.process(codeQuery),
  ]);

  console.log();
  console.log('Review Results (executed simultaneously):');
  console.log();
  console.log('Security Review:');
  console.log('-'.repeat(70));
  console.log(reviews[0].content);
  console.log();
  console.log('Performance Review:');
  console.log('-'.repeat(70));
  console.log(reviews[1].content);
  console.log();
  console.log('Style Review:');
  console.log('-'.repeat(70));
  console.log(reviews[2].content);
  console.log();

  // Example 3: Creative collaboration
  console.log('-'.repeat(70));
  console.log('Example 3: Creative Writing Team (Sequential Pipeline)');
  console.log('-'.repeat(70));
  console.log();

  const plotWriter = new MockSpecializedAgent(
    'PlotWriter',
    'Create engaging story outlines with strong narrative structure.'
  );

  const characterWriter = new MockSpecializedAgent(
    'CharacterWriter',
    'Create compelling, multi-dimensional characters.'
  );

  const dialogueWriter = new MockSpecializedAgent(
    'DialogueWriter',
    'Write natural, engaging dialogue that reveals character.'
  );

  const creativeTeam = new SequentialOrchestrator([plotWriter, characterWriter, dialogueWriter]);

  console.log('Creative Writing Team:');
  console.log('  1. Plot Writer - Creates story outline');
  console.log('  2. Character Writer - Develops characters');
  console.log('  3. Dialogue Writer - Writes sample dialogue');
  console.log();

  const storyPrompt = createMessage({
    role: 'user',
    content: 'Create a short story concept about an AI learning to understand human emotions.',
  });

  console.log(`Prompt: ${storyPrompt.content}`);
  console.log();
  console.log('Executing creative pipeline:');

  const storyResults = await creativeTeam.execute(storyPrompt);

  console.log();
  console.log('Creative Pipeline Results:');
  console.log();
  console.log('Stage 1 - Plot:');
  console.log('-'.repeat(70));
  console.log(storyResults[0].content);
  console.log();
  console.log('Stage 2 - Characters:');
  console.log('-'.repeat(70));
  console.log(storyResults[1].content);
  console.log();
  console.log('Stage 3 - Sample Dialogue:');
  console.log('-'.repeat(70));
  console.log(storyResults[2].content);
  console.log();

  console.log('-'.repeat(70));
  console.log('✓ All multiagent examples completed!');
  console.log();
  console.log('Key Patterns Demonstrated:');
  console.log('  • Sequential orchestration (pipeline processing)');
  console.log('  • Parallel execution (simultaneous operations)');
  console.log('  • Role-based specialization');
  console.log('  • Inter-agent communication and coordination');
  console.log();
  console.log('Production Usage:');
  console.log('  Replace MockSpecializedAgent with real LLM adapters:');
  console.log('  - AnthropicAdapter (Claude)');
  console.log('  - OpenAIAdapter (GPT-4)');
  console.log('  - Each agent can have different system prompts for specialization');
  console.log();
  console.log('Pattern Comparison:');
  console.log('  • Multiagent: Peer collaboration on shared goals');
  console.log('  • Agents-as-Tools: Hierarchical delegation (supervisor → specialists)');
  console.log('  • Orchestration: Workflow coordination (sequential/parallel)');
  console.log('-'.repeat(70));
}

main().catch((error) => {
  console.error('Error:', error.message);
  process.exit(1);
});
