/**
 * Orchestration Pattern Example
 *
 * Demonstrates:
 * - Sequential agent execution (pipeline)
 * - Parallel agent execution (concurrent processing)
 * - Result aggregation from multiple agents
 * - Workflow coordination patterns
 * - Mock agents for demonstration (no API keys required)
 *
 * WHY use this pattern:
 * ✅ Coordinate multiple agents working together
 * ✅ Sequential workflows (output of one feeds into next)
 * ✅ Parallel processing (multiple agents work simultaneously)
 * ✅ Result aggregation from multiple sources
 * ✅ Complex multi-agent workflows
 *
 * WHEN to use:
 * - Multi-step workflows where agents build on each other
 * - Parallel processing for speed (reviews, analysis)
 * - Aggregating results from multiple agents
 * - Complex coordination between specialized agents
 * - Pipeline processing (ETL, data transformation)
 *
 * WHEN NOT to use:
 * - Simple single-agent tasks
 * - When agents don't need coordination
 * - Hierarchical delegation (use Agents-as-Tools instead)
 *
 * Setup:
 *   npm run build
 *   node dist/examples/patterns/orchestration-pattern.js
 */

import { Agent, Message, createMessage } from '../../src/core/interfaces';

/**
 * Mock specialized agent for orchestration demonstration
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
    } else if (this.role === 'TechResearcher') {
      response = this.generateTechResearch(content);
    } else if (this.role === 'BusinessResearcher') {
      response = this.generateBusinessResearch(content);
    } else if (this.role === 'Synthesizer') {
      response = this.generateSynthesis(content);
    } else {
      response = `${this.role} response: Processed the request according to ${this.systemPrompt}`;
    }

    return createMessage({ role: 'assistant', content: response });
  }

  private generateResearchResponse(content: string): string {
    if (content.includes('typescript') || content.includes('javascript')) {
      return `Research on TypeScript vs JavaScript:

TypeScript is a superset of JavaScript that adds static typing. Key benefits include:

• **Type Safety**: Catch errors at compile time rather than runtime
• **Better IDE Support**: Enhanced autocomplete and refactoring
• **Self-Documenting**: Types serve as inline documentation
• **Scalability**: Easier to maintain large codebases
• **Modern Features**: Access to latest JavaScript features with transpilation`;
    } else {
      return `Research findings: Comprehensive analysis of the topic reveals multiple important factors and considerations for implementation.`;
    }
  }

  private generateAnalystResponse(content: string): string {
    if (content.includes('typescript') || content.includes('research') || content.includes('previous agent')) {
      return `Analysis of TypeScript benefits:

**Key Insights:**
1. **Developer Productivity**: Type checking reduces debugging time by 15-30%
2. **Code Quality**: Interfaces and types enforce contracts between components
3. **Refactoring Safety**: Types make large-scale refactoring significantly safer

**Patterns Identified:**
• Adoption correlates with team size (larger teams benefit more)
• Learning curve offset by long-term maintainability gains
• Integration with existing tools (Jest, ESLint) is mature`;
    } else {
      return `Analytical assessment: Data analysis reveals key trends and actionable insights for decision-making.`;
    }
  }

  private generateWriterResponse(content: string): string {
    if (content.includes('typescript') || content.includes('analysis') || content.includes('previous agent')) {
      return `Executive Summary: TypeScript significantly improves developer productivity and code quality through static typing, catching errors early and providing superior tooling support. While requiring initial learning investment, its benefits—particularly for larger teams and codebases—make it a compelling choice for modern JavaScript development.`;
    } else {
      return `Written summary: Clear, concise synthesis of findings with actionable recommendations for stakeholders.`;
    }
  }

  private generateSecurityReview(content: string): string {
    return `🔒 Security Review:

**Critical Issues:**
• eval() usage - DANGEROUS! Allows arbitrary code execution
• No input validation or sanitization
• Potential for injection attacks

**Recommendations:**
1. Remove eval() - use JSON.parse or safer alternatives
2. Implement strict input validation
3. Apply Content Security Policy
4. Use parameterized queries for data operations`;
  }

  private generatePerformanceReview(content: string): string {
    return `⚡ Performance Review:

**Issues Identified:**
• 1,000,000 iteration loop - excessive overhead
• console.log in tight loop - major I/O bottleneck
• No performance optimization strategies

**Recommendations:**
1. Reduce loop iterations or use batch processing
2. Remove console.log or use throttling
3. Consider async/await for I/O operations
4. Profile with Chrome DevTools`;
  }

  private generateStyleReview(content: string): string {
    return `✨ Style & Code Quality Review:

**Issues Found:**
• Missing TypeScript type annotations
• Poor function naming (not self-documenting)
• No JSDoc documentation
• Missing error handling

**Recommendations:**
1. Add explicit types for all parameters/returns
2. Rename to descriptive names (processUserInput → validateAndProcessInput)
3. Add comprehensive JSDoc comments
4. Implement try-catch with proper error handling`;
  }

  private generateTechResearch(content: string): string {
    return `Technical Research on AI Agents in Software Development:

**Implementation Perspective:**
• Agents automate repetitive tasks (code review, testing, documentation)
• Integration with CI/CD pipelines for continuous quality checks
• Use of LLMs for code generation and bug detection
• Pattern recognition for security vulnerabilities

**Technical Benefits:**
- 40% reduction in code review time
- Automated test generation
- Consistent code style enforcement
- Real-time documentation generation`;
  }

  private generateBusinessResearch(content: string): string {
    return `Business Analysis of AI Agents in Software Development:

**ROI Perspective:**
• 25-35% increase in developer productivity
• Reduced time-to-market for new features
• Lower maintenance costs through better code quality
• Decreased bug escape rate to production

**Business Value:**
- Faster iteration cycles
- More predictable delivery timelines
- Improved developer satisfaction and retention
- Competitive advantage through automation`;
  }

  private generateSynthesis(content: string): string {
    if (content.includes('technical') && content.includes('business')) {
      return `Synthesis: AI agents in software development offer compelling value from both technical and business perspectives. Technically, they automate repetitive tasks and improve code quality through pattern recognition and real-time analysis. From a business standpoint, this translates to 25-35% productivity gains, faster time-to-market, and reduced maintenance costs. The intersection of technical capability and business value makes AI agents a strategic investment for modern software teams seeking competitive advantage through intelligent automation.`;
    } else {
      return `Balanced synthesis combining multiple perspectives into actionable recommendations.`;
    }
  }
}

/**
 * Sequential orchestrator - runs agents in pipeline
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

/**
 * Parallel orchestrator - runs agents concurrently
 */
class ParallelOrchestrator {
  constructor(private agents: Agent[]) {}

  async execute(message: Message): Promise<Message[]> {
    console.log(`  → Executing ${this.agents.length} agents in parallel...`);

    // Execute all agents concurrently
    const promises = this.agents.map(agent => agent.process(message));
    const results = await Promise.all(promises);

    return results;
  }
}

async function main() {
  console.log('='.repeat(70));
  console.log('AgentKit TypeScript - Orchestration Pattern Example');
  console.log('='.repeat(70));
  console.log();

  console.log('✓ Using mock agents (no API keys required)');
  console.log();

  // Example 1: Sequential orchestration (pipeline)
  console.log('-'.repeat(70));
  console.log('Example 1: Sequential Pipeline (Research → Analysis → Writing)');
  console.log('-'.repeat(70));
  console.log();

  const researcher = new MockSpecializedAgent(
    'Researcher',
    'Gather and synthesize key information on the given topic. Be thorough but concise.'
  );

  const analyst = new MockSpecializedAgent(
    'Analyst',
    'Analyze the information provided and identify key insights, patterns, and trends.'
  );

  const writer = new MockSpecializedAgent(
    'Writer',
    'Take the research and analysis provided and write a clear, concise executive summary.'
  );

  const pipeline = new SequentialOrchestrator([researcher, analyst, writer]);

  console.log('Pipeline stages:');
  console.log('  1. Researcher - Gathers information');
  console.log('  2. Analyst - Identifies insights');
  console.log('  3. Writer - Creates summary');
  console.log();

  const pipelineQuery = createMessage({
    role: 'user',
    content: 'Explain the key benefits of TypeScript over JavaScript.',
  });

  console.log(`Query: ${pipelineQuery.content}`);
  console.log();
  console.log('Executing pipeline:');

  const pipelineResults = await pipeline.execute(pipelineQuery);

  console.log();
  console.log('Pipeline Results:');
  console.log();
  console.log('Stage 1 - Researcher Output:');
  console.log('-'.repeat(70));
  console.log(pipelineResults[0].content);
  console.log();
  console.log('Stage 2 - Analyst Output:');
  console.log('-'.repeat(70));
  console.log(pipelineResults[1].content);
  console.log();
  console.log('Stage 3 - Writer Output (Final):');
  console.log('-'.repeat(70));
  console.log(pipelineResults[2].content);
  console.log();

  // Example 2: Parallel orchestration (concurrent reviews)
  console.log('-'.repeat(70));
  console.log('Example 2: Parallel Reviews (Security, Performance, Style)');
  console.log('-'.repeat(70));
  console.log();

  const securityReviewer = new MockSpecializedAgent(
    'SecurityReviewer',
    'Review code for security vulnerabilities and best practices.'
  );

  const performanceReviewer = new MockSpecializedAgent(
    'PerformanceReviewer',
    'Review code for efficiency and scalability issues.'
  );

  const styleReviewer = new MockSpecializedAgent(
    'StyleReviewer',
    'Review code for readability, maintainability, and style.'
  );

  const parallelReview = new ParallelOrchestrator([
    securityReviewer,
    performanceReviewer,
    styleReviewer,
  ]);

  const codeSnippet = `
function processUserData(data) {
  const result = eval(data);
  for (let i = 0; i < 1000000; i++) {
    console.log(result);
  }
  return result;
}
`;

  console.log('Code to review:');
  console.log(codeSnippet);
  console.log();

  const reviewQuery = createMessage({
    role: 'user',
    content: `Review this JavaScript code:\n${codeSnippet}`,
  });

  const reviews = await parallelReview.execute(reviewQuery);

  console.log();
  console.log('Review Results (executed in parallel):');
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

  // Example 3: Hybrid orchestration (parallel then sequential)
  console.log('-'.repeat(70));
  console.log('Example 3: Hybrid Orchestration (Parallel Research → Sequential Synthesis)');
  console.log('-'.repeat(70));
  console.log();

  const techResearcher = new MockSpecializedAgent(
    'TechResearcher',
    'Focus on technical aspects and implementation details.'
  );

  const businessResearcher = new MockSpecializedAgent(
    'BusinessResearcher',
    'Focus on business value and ROI.'
  );

  const synthesizer = new MockSpecializedAgent(
    'Synthesizer',
    'Combine technical and business perspectives into a balanced summary.'
  );

  console.log('Hybrid workflow:');
  console.log('  Phase 1: Parallel research (technical + business)');
  console.log('  Phase 2: Sequential synthesis');
  console.log();

  const hybridQuery = createMessage({
    role: 'user',
    content: 'What are the benefits of using AI agents in software development?',
  });

  console.log(`Query: ${hybridQuery.content}`);
  console.log();

  // Phase 1: Parallel research
  console.log('Phase 1: Parallel research...');
  const parallelResearch = new ParallelOrchestrator([techResearcher, businessResearcher]);
  const researchResults = await parallelResearch.execute(hybridQuery);

  console.log();
  console.log('Technical Research:');
  console.log('-'.repeat(70));
  console.log(researchResults[0].content);
  console.log();
  console.log('Business Research:');
  console.log('-'.repeat(70));
  console.log(researchResults[1].content);
  console.log();

  // Phase 2: Synthesize results
  console.log('Phase 2: Synthesizing results...');
  const synthesisInput = createMessage({
    role: 'user',
    content: `Synthesize these perspectives:\n\nTechnical:\n${researchResults[0].content}\n\nBusiness:\n${researchResults[1].content}`,
  });

  const finalSynthesis = await synthesizer.process(synthesisInput);

  console.log();
  console.log('Final Synthesis:');
  console.log('-'.repeat(70));
  console.log(finalSynthesis.content);
  console.log();

  // Example 4: Pattern comparison
  console.log('-'.repeat(70));
  console.log('Example 4: Orchestration Patterns Comparison');
  console.log('-'.repeat(70));
  console.log();

  console.log('Sequential Orchestration:');
  console.log('  • Agents run one after another');
  console.log('  • Output of one feeds into next');
  console.log('  • Use for: pipelines, workflows, ETL');
  console.log('  • Example: Research → Analyze → Write');
  console.log();

  console.log('Parallel Orchestration:');
  console.log('  • Agents run concurrently');
  console.log('  • All receive same input');
  console.log('  • Use for: reviews, multi-perspective analysis');
  console.log('  • Example: Security + Performance + Style reviews');
  console.log();

  console.log('Hybrid Orchestration:');
  console.log('  • Combination of sequential and parallel');
  console.log('  • Parallel for independent tasks, sequential for dependencies');
  console.log('  • Use for: complex workflows with mixed patterns');
  console.log('  • Example: Parallel research → Sequential synthesis');
  console.log();

  console.log('-'.repeat(70));
  console.log('✓ All orchestration examples completed!');
  console.log();
  console.log('Key Benefits of Orchestration Pattern:');
  console.log('  • Coordinate multiple agents efficiently');
  console.log('  • Sequential for dependent workflows');
  console.log('  • Parallel for independent tasks (faster)');
  console.log('  • Flexible composition of agents');
  console.log('  • Clear workflow structure');
  console.log();
  console.log('Production Usage:');
  console.log('  Replace MockSpecializedAgent with real LLM adapters:');
  console.log('  - AnthropicAdapter (Claude)');
  console.log('  - OpenAIAdapter (GPT-4)');
  console.log('  - Each agent can have specialized system prompts');
  console.log();
  console.log('Pattern Comparison:');
  console.log('  • Orchestration: Coordinate agent workflows (sequential/parallel)');
  console.log('  • Agents-as-Tools: Hierarchical delegation (supervisor → specialists)');
  console.log('  • Multiagent: Collaborative problem solving');
  console.log('  • Planning: Break tasks into steps with dependencies');
  console.log('-'.repeat(70));
}

main().catch((error) => {
  console.error('Error:', error.message);
  process.exit(1);
});
