/**
 * Agents-as-Tools Pattern Example
 *
 * Demonstrates:
 * - Wrapping specialist agents as tools
 * - Hierarchical agent delegation (supervisor → specialists)
 * - Domain-specific routing
 * - Reusable agent components
 * - Mock agents for demonstration (no API keys required)
 *
 * WHY use this pattern:
 * ✅ Modular specialization (separate agents for different domains)
 * ✅ Hierarchical delegation (supervisor routes to specialists)
 * ✅ Reusable specialist agents (can be called by multiple supervisors)
 * ✅ Standard tool interface (works with existing tool infrastructure)
 * ✅ Clear separation of concerns
 *
 * WHEN to use:
 * - Supervisor agent needs to delegate to domain specialists
 * - Multiple specialized capabilities required (code, data, writing)
 * - Hierarchical multi-agent systems
 * - Agent composition and orchestration
 * - Domain-specific routing (route tasks to the right expert)
 *
 * WHEN NOT to use:
 * - Flat peer-to-peer collaboration (use Multiagent pattern)
 * - Simple single-agent tasks
 * - When all capabilities can fit in one agent
 *
 * Setup:
 *   npm run build
 *   node dist/examples/patterns/agents-as-tools-pattern.js
 */

import { agentAsTool } from '../../src/patterns/agents-as-tools';
import { Agent, Message, Tool, ToolResult, createMessage } from '../../src/core/interfaces';

/**
 * Mock specialist agent for code-related tasks
 */
class CodeSpecialistAgent implements Agent {
  name(): string {
    return 'CodeSpecialist';
  }

  capabilities(): string[] {
    return ['coding', 'debugging', 'code_review'];
  }

  async process(message: Message): Promise<Message> {
    const query = message.content.toLowerCase();
    let response = '';

    if (query.includes('email') || query.includes('validate')) {
      response = `🔧 Code Specialist Response:

\`\`\`typescript
/**
 * Validates email address format
 * @param email - Email address to validate
 * @returns true if valid email format, false otherwise
 */
function validateEmail(email: string): boolean {
  const emailRegex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;

  if (!email || typeof email !== 'string') {
    return false;
  }

  return emailRegex.test(email.trim().toLowerCase());
}

// Example usage:
console.log(validateEmail('user@example.com')); // true
console.log(validateEmail('invalid.email'));    // false
\`\`\`

**Key features:**
• Regex pattern validates basic email structure
• Type checking for input safety
• Trims whitespace and normalizes to lowercase
• Returns boolean for easy conditional logic`;
    } else if (query.includes('fibonacci')) {
      response = `🔧 Code Specialist Response:

\`\`\`typescript
/**
 * Calculate nth Fibonacci number using memoization
 * @param n - Position in Fibonacci sequence (0-indexed)
 * @returns The nth Fibonacci number
 */
function fibonacci(n: number, memo: Map<number, number> = new Map()): number {
  if (n <= 1) return n;

  if (memo.has(n)) {
    return memo.get(n)!;
  }

  const result = fibonacci(n - 1, memo) + fibonacci(n - 2, memo);
  memo.set(n, result);

  return result;
}

// Example usage:
console.log(fibonacci(10)); // 55
console.log(fibonacci(20)); // 6765
\`\`\`

**Implementation notes:**
• Uses memoization for O(n) time complexity
• Avoids redundant calculations
• Handles edge cases (n <= 1)`;
    } else {
      response = `🔧 Code Specialist Response:

I can help with:
• Writing functions and algorithms
• Debugging code issues
• Code review and optimization
• Best practices and design patterns

Please provide more details about what you need.`;
    }

    return createMessage({ role: 'assistant', content: response });
  }
}

/**
 * Mock specialist agent for data analysis tasks
 */
class DataSpecialistAgent implements Agent {
  name(): string {
    return 'DataSpecialist';
  }

  capabilities(): string[] {
    return ['data_analysis', 'sql', 'statistics'];
  }

  async process(message: Message): Promise<Message> {
    const query = message.content.toLowerCase();
    let response = '';

    if (query.includes('sql') || query.includes('customers') || query.includes('revenue')) {
      response = `📊 Data Specialist Response:

\`\`\`sql
-- Find top 10 customers by total revenue
SELECT
  c.customer_id,
  c.customer_name,
  c.email,
  SUM(o.order_total) AS total_revenue,
  COUNT(o.order_id) AS order_count,
  AVG(o.order_total) AS avg_order_value
FROM customers c
INNER JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_date >= DATE_SUB(CURRENT_DATE, INTERVAL 1 YEAR)
  AND o.status = 'completed'
GROUP BY c.customer_id, c.customer_name, c.email
ORDER BY total_revenue DESC
LIMIT 10;
\`\`\`

**Query explanation:**
• Joins customers with their orders
• Filters for last 12 months of completed orders
• Aggregates revenue, order count, and average
• Returns top 10 by total revenue

**Performance tips:**
• Ensure indexes on customer_id and order_date
• Consider materializing for frequent queries`;
    } else if (query.includes('analyze') || query.includes('analysis')) {
      response = `📊 Data Specialist Response:

Data Analysis Workflow:

**1. Data Exploration**
• Summary statistics (mean, median, mode, std dev)
• Distribution analysis (histograms, box plots)
• Identify missing values and outliers

**2. Data Cleaning**
• Handle missing values (imputation or removal)
• Outlier detection and treatment
• Data type validation

**3. Analysis**
• Correlation analysis
• Trend identification
• Segment analysis

**4. Visualization**
• Time series plots
• Scatter plots for relationships
• Bar charts for comparisons

**5. Insights & Recommendations**
• Key findings summary
• Actionable recommendations`;
    } else {
      response = `📊 Data Specialist Response:

I specialize in:
• SQL query writing and optimization
• Data analysis and statistics
• Database design
• ETL pipeline recommendations

What data challenge can I help you solve?`;
    }

    return createMessage({ role: 'assistant', content: response });
  }
}

/**
 * Mock specialist agent for writing and documentation
 */
class WritingSpecialistAgent implements Agent {
  name(): string {
    return 'WritingSpecialist';
  }

  capabilities(): string[] {
    return ['writing', 'documentation', 'editing'];
  }

  async process(message: Message): Promise<Message> {
    const query = message.content.toLowerCase();
    let response = '';

    if (query.includes('readme') || query.includes('typescript project')) {
      response = `✍️  Writing Specialist Response:

# TypeScript Project

## Overview
A modern TypeScript application with type-safe development and excellent developer experience.

## Installation

\`\`\`bash
# Clone the repository
git clone https://github.com/yourusername/your-project.git
cd your-project

# Install dependencies
npm install

# Build the project
npm run build
\`\`\`

## Quick Start

\`\`\`typescript
import { YourClass } from './src';

const instance = new YourClass();
const result = instance.process();
console.log(result);
\`\`\`

## Features

- ✅ **Type Safety** - Full TypeScript coverage
- ✅ **Modern Tooling** - ESLint, Prettier, Jest
- ✅ **Documentation** - Comprehensive API docs
- ✅ **Testing** - Unit and integration tests

## Development

\`\`\`bash
# Run in development mode
npm run dev

# Run tests
npm test

# Run linter
npm run lint
\`\`\`

## API Reference

See [API Documentation](./docs/api.md) for detailed API reference.

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) first.

## License

MIT`;
    } else if (query.includes('article') || query.includes('blog')) {
      response = `✍️  Writing Specialist Response:

Blog Post Structure:

**Title:** [Attention-grabbing headline]

**Introduction** (2-3 paragraphs)
• Hook: Start with a question, statistic, or story
• Context: Why this topic matters now
• Preview: What readers will learn

**Body** (3-5 sections)

**Section 1: Problem Statement**
• Define the challenge
• Provide real-world examples
• Show impact/consequences

**Section 2: Solution Overview**
• Introduce your approach
• Explain key concepts
• Highlight benefits

**Section 3: Implementation**
• Step-by-step guidance
• Code examples or screenshots
• Best practices

**Section 4: Results & Impact**
• Demonstrate outcomes
• Share metrics or case studies
• Address common concerns

**Conclusion** (1-2 paragraphs)
• Recap key points
• Call to action
• Next steps or resources

**Writing Tips:**
• Use clear, concise language
• Include concrete examples
• Break up text with subheadings
• Add visuals where helpful`;
    } else {
      response = `✍️  Writing Specialist Response:

I can help with:
• Technical documentation (README, API docs)
• Blog posts and articles
• User guides and tutorials
• Copywriting and editing

What would you like me to write?`;
    }

    return createMessage({ role: 'assistant', content: response });
  }
}

/**
 * Mock supervisor agent that routes tasks to specialists
 */
class SupervisorAgent implements Agent {
  private tools: Map<string, Tool>;

  constructor(tools: Tool[]) {
    this.tools = new Map(tools.map(tool => [tool.name, tool]));
  }

  name(): string {
    return 'Supervisor';
  }

  capabilities(): string[] {
    return ['routing', 'delegation', 'coordination'];
  }

  async process(message: Message): Promise<Message> {
    const query = message.content.toLowerCase();

    console.log(`\n🎯 Supervisor analyzing: "${message.content}"`);

    // Simple routing logic based on keywords
    let selectedTool: Tool | undefined;

    if (query.includes('code') || query.includes('function') || query.includes('implement') ||
        query.includes('debug') || query.includes('typescript') || query.includes('validate') ||
        query.includes('fibonacci')) {
      console.log('  → Routing to Code Specialist');
      selectedTool = this.tools.get('code_specialist');
    } else if (query.includes('data') || query.includes('sql') || query.includes('query') ||
               query.includes('analyze') || query.includes('statistics') || query.includes('customers') ||
               query.includes('revenue')) {
      console.log('  → Routing to Data Specialist');
      selectedTool = this.tools.get('data_specialist');
    } else if (query.includes('write') || query.includes('document') || query.includes('readme') ||
               query.includes('article') || query.includes('blog') || query.includes('project')) {
      console.log('  → Routing to Writing Specialist');
      selectedTool = this.tools.get('writing_specialist');
    }

    if (!selectedTool) {
      // No specialist matched - provide routing info
      return createMessage({
        role: 'assistant',
        content: 'I can route your request to one of my specialists:\n\n' +
          '• **Code Specialist**: Programming, debugging, code review\n' +
          '• **Data Specialist**: SQL queries, data analysis, statistics\n' +
          '• **Writing Specialist**: Documentation, articles, technical writing\n\n' +
          'Please clarify what you need help with.',
      });
    }

    // Delegate to specialist
    const result = await selectedTool.execute({ query: message.content });

    return createMessage({
      role: 'assistant',
      content: result.output || result.error || 'No response from specialist',
    });
  }
}

async function main() {
  console.log('='.repeat(70));
  console.log('AgentKit TypeScript - Agents-as-Tools Pattern Example');
  console.log('='.repeat(70));
  console.log();

  console.log('✓ Using mock agents (no API keys required)');
  console.log();

  // Example 1: Basic delegation to specialists
  console.log('-'.repeat(70));
  console.log('Example 1: Basic Hierarchical Delegation');
  console.log('-'.repeat(70));
  console.log();

  // Create specialist agents
  const codeAgent = new CodeSpecialistAgent();
  const dataAgent = new DataSpecialistAgent();
  const writingAgent = new WritingSpecialistAgent();

  // Wrap specialists as tools
  const codeTool = agentAsTool(codeAgent, {
    name: 'code_specialist',
    description: 'Expert in programming, code review, and debugging',
    inputKey: 'query',
  });

  const dataTool = agentAsTool(dataAgent, {
    name: 'data_specialist',
    description: 'Expert in data analysis, SQL, and visualization',
    inputKey: 'query',
  });

  const writingTool = agentAsTool(writingAgent, {
    name: 'writing_specialist',
    description: 'Expert in technical writing and documentation',
    inputKey: 'query',
  });

  console.log('🏗️  System Architecture:');
  console.log('  ┌─────────────────┐');
  console.log('  │   Supervisor    │  (Routes to specialists)');
  console.log('  └────────┬────────┘');
  console.log('           │');
  console.log('     ┌─────┴─────────────┬────────────┐');
  console.log('     │                   │            │');
  console.log('┌────▼─────┐      ┌──────▼───┐  ┌────▼──────┐');
  console.log('│   Code   │      │   Data   │  │  Writing  │');
  console.log('│Specialist│      │Specialist│  │ Specialist│');
  console.log('└──────────┘      └──────────┘  └───────────┘');
  console.log();

  // Create supervisor with specialist tools
  const supervisor = new SupervisorAgent([codeTool, dataTool, writingTool]);

  // Test different types of requests
  const requests = [
    'Write a TypeScript function to validate email addresses',
    'Help me write a SQL query to find the top 10 customers by revenue',
    'Create a README for my TypeScript project',
  ];

  for (const request of requests) {
    console.log(`📝 Request: "${request}"`);
    const message = createMessage({ role: 'user', content: request });
    const result = await supervisor.process(message);

    console.log(`\n✅ Response:`);
    // Display full content for readability
    console.log(result.content);
    console.log();
    console.log('-'.repeat(70));
  }

  // Example 2: Direct tool invocation
  console.log();
  console.log('-'.repeat(70));
  console.log('Example 2: Direct Tool Invocation (No Supervisor)');
  console.log('-'.repeat(70));
  console.log();

  console.log('Tool Name: ' + codeTool.name);
  console.log('Description: ' + codeTool.description);
  console.log('Input Schema:', JSON.stringify(codeTool.inputSchema, null, 2));
  console.log();

  console.log('Calling code specialist directly...');
  const directResult = await codeTool.execute({ query: 'Write a function to calculate Fibonacci numbers' });

  console.log('\n✅ Direct invocation result:');
  console.log(directResult.output || directResult.error || 'No output');
  console.log();

  // Example 3: Benefits demonstration
  console.log('-'.repeat(70));
  console.log('Example 3: Pattern Benefits');
  console.log('-'.repeat(70));
  console.log();

  console.log('💡 Benefits of Agents-as-Tools Pattern:');
  console.log('  • **Modular**: Each specialist focuses on its domain');
  console.log('  • **Reusable**: Specialists can be shared across supervisors');
  console.log('  • **Scalable**: Easy to add new specialists');
  console.log('  • **Maintainable**: Clear separation of concerns');
  console.log('  • **Composable**: Build complex systems from simple parts');
  console.log();

  console.log('📌 Use Agents-as-Tools when:');
  console.log('  • Hierarchical delegation (supervisor → specialists)');
  console.log('  • Domain specialization (code, data, writing)');
  console.log('  • Routing based on task type');
  console.log('  • Specialists can be reused by multiple supervisors');
  console.log();

  console.log('📌 Use Multiagent pattern when:');
  console.log('  • Peer-to-peer collaboration (no hierarchy)');
  console.log('  • Agents work together on shared goal');
  console.log('  • No clear supervisor-specialist relationship');
  console.log();

  console.log('-'.repeat(70));
  console.log('✓ All agents-as-tools examples completed!');
  console.log();
  console.log('Key Takeaways:');
  console.log('  1. Wrap specialist agents as tools for hierarchical delegation');
  console.log('  2. Supervisor routes tasks to appropriate specialists');
  console.log('  3. Specialists expose standard tool interface');
  console.log('  4. Enables modular, reusable agent architecture');
  console.log('  5. Clear separation: supervisor routes, specialists execute');
  console.log();
  console.log('Production Usage:');
  console.log('  Replace mock agents with real LLM adapters:');
  console.log('  - AnthropicAdapter (Claude for specialists)');
  console.log('  - OpenAIAdapter (GPT-4 for routing logic)');
  console.log('  - Each specialist can have custom system prompts');
  console.log('-'.repeat(70));
}

main().catch((error) => {
  console.error('Error:', error.message);
  process.exit(1);
});
