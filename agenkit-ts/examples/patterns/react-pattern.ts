/**
 * ReAct Pattern with Tools Example
 *
 * Demonstrates:
 * - ReAct (Reasoning + Acting) pattern
 * - Tool creation and registration
 * - Multi-step reasoning with tool use
 * - Mock agent for demonstration (no API keys required)
 *
 * WHY use this pattern:
 * ✅ Combines reasoning with tool-based actions
 * ✅ Multi-step problem solving
 * ✅ Access to external tools and APIs
 * ✅ Iterative refinement based on tool results
 * ✅ Works with any LLM adapter
 *
 * WHEN to use:
 * - Tasks requiring external data (weather, calculations, searches)
 * - Multi-step problem solving
 * - When agent needs to use tools to accomplish goals
 * - Interactive workflows with tool feedback
 *
 * Setup:
 *   npm run build
 *   node dist/examples/patterns/react-pattern.js
 */

import { ReActAgent } from '../../src/patterns/react';
import { Tool, ToolResult, Agent, Message, createMessage } from '../../src/core/interfaces';

/**
 * Calculator tool for math operations
 */
class CalculatorTool implements Tool {
  name = 'calculator';
  description = 'Performs basic math operations: +, -, *, /, %. Example: "15 + 25" or "15% of 80"';

  async execute(input: string): Promise<ToolResult> {
    try {
      // Handle percentage calculations: "X% of Y"
      const percentMatch = input.match(/(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)/i);
      if (percentMatch) {
        const percent = parseFloat(percentMatch[1]);
        const value = parseFloat(percentMatch[2]);
        const result = (percent / 100) * value;
        return { success: true, output: result.toString() };
      }

      // Handle basic arithmetic
      const sanitized = input.replace(/[^0-9+\-*/.() ]/g, '');
      const result = eval(sanitized);
      return { success: true, output: result.toString() };
    } catch (error) {
      return {
        success: false,
        error: `Failed to calculate: ${error instanceof Error ? error.message : 'Unknown error'}`,
      };
    }
  }
}

/**
 * Weather tool (simulated)
 */
class WeatherTool implements Tool {
  name = 'weather';
  description = 'Get current weather for a city. Example: "San Francisco" or "London"';

  private weatherData: Record<string, string> = {
    'san francisco': 'Sunny, 72°F (22°C), light breeze',
    'new york': 'Cloudy, 65°F (18°C), chance of rain',
    'london': 'Rainy, 58°F (14°C), windy',
    'tokyo': 'Clear, 75°F (24°C), humid',
    'paris': 'Partly cloudy, 68°F (20°C), calm',
    'sydney': 'Sunny, 82°F (28°C), warm',
    'berlin': 'Overcast, 60°F (16°C), cool',
  };

  async execute(input: string): Promise<ToolResult> {
    const city = input.toLowerCase().trim();
    const weather = this.weatherData[city];

    if (weather) {
      return { success: true, output: `Weather in ${input}: ${weather}` };
    } else {
      return {
        success: false,
        error: `Weather data not available for: ${input}`,
      };
    }
  }
}

/**
 * Search tool (simulated)
 */
class SearchTool implements Tool {
  name = 'search';
  description = 'Search for information on a topic. Example: "ReAct pattern" or "TypeScript features"';

  private knowledge: Record<string, string> = {
    'react pattern': 'ReAct combines reasoning and acting by having LLMs generate both reasoning traces and task-specific actions in an interleaved manner.',
    'typescript': 'TypeScript is a strongly typed programming language that builds on JavaScript, giving you better tooling at any scale.',
    'agenkit': 'AgentKit is a minimal, composable framework for building AI agents with support for multiple languages.',
    'machine learning': 'Machine learning is a subset of AI that enables systems to learn and improve from experience without being explicitly programmed.',
  };

  async execute(input: string): Promise<ToolResult> {
    const query = input.toLowerCase().trim();

    // Find best match
    for (const [key, value] of Object.entries(this.knowledge)) {
      if (query.includes(key) || key.includes(query)) {
        return { success: true, output: value };
      }
    }

    return {
      success: false,
      error: `No information found for: ${input}`,
    };
  }
}

/**
 * Mock reasoning agent that simulates tool use
 */
class MockReasoningAgent implements Agent {
  private tools: Map<string, Tool>;

  constructor(tools: Tool[]) {
    this.tools = new Map(tools.map(t => [t.name, t]));
  }

  name(): string {
    return 'MockReasoningAgent';
  }

  capabilities(): string[] {
    return ['reasoning', 'tool_use'];
  }

  async process(message: Message): Promise<Message> {
    const query = message.content.toLowerCase();
    let response = '';

    // Simple routing logic based on keywords
    if (query.includes('%') || query.includes('tip') || query.includes('calculate') || /\d+.*\d+/.test(query)) {
      // Use calculator
      const calcTool = this.tools.get('calculator');
      if (calcTool) {
        const match = query.match(/(\d+(?:\.\d+)?)\s*%.*?(\d+(?:\.\d+)?)/);
        if (match) {
          const result = await calcTool.execute(`${match[1]}% of ${match[2]}`);
          response = `I'll calculate that for you: ${result.output}. ` +
            `So a ${match[1]}% tip on $${match[2]} is $${result.output}.`;
        } else {
          // Try to extract a mathematical expression
          const mathMatch = query.match(/(\d+(?:\.\d+)?)\s*([\+\-\*\/])\s*(\d+(?:\.\d+)?)/);
          if (mathMatch) {
            const result = await calcTool.execute(`${mathMatch[1]} ${mathMatch[2]} ${mathMatch[3]}`);
            response = `The result is: ${result.output}`;
          }
        }
      }
    } else if (query.includes('weather')) {
      // Use weather tool
      const weatherTool = this.tools.get('weather');
      if (weatherTool) {
        // Extract city name
        const cities = ['san francisco', 'new york', 'london', 'tokyo', 'paris', 'sydney', 'berlin'];
        const city = cities.find(c => query.includes(c)) || 'paris';
        const result = await weatherTool.execute(city);
        response = result.success ? result.output! : `Sorry, ${result.error}`;
      }
    } else if (query.includes('react') || query.includes('search') || query.includes('what is')) {
      // Use search tool
      const searchTool = this.tools.get('search');
      if (searchTool) {
        let searchQuery = 'react pattern';
        if (query.includes('typescript')) searchQuery = 'typescript';
        else if (query.includes('agenkit')) searchQuery = 'agenkit';
        else if (query.includes('machine learning')) searchQuery = 'machine learning';

        const result = await searchTool.execute(searchQuery);
        response = result.success ? result.output! : `I couldn't find information about that.`;
      }
    } else {
      response = 'I can help with calculations, weather lookups, or searching for information. What would you like to know?';
    }

    return createMessage({ role: 'assistant', content: response });
  }
}

async function main() {
  console.log('='.repeat(60));
  console.log('AgentKit TypeScript - ReAct with Tools Example');
  console.log('='.repeat(60));
  console.log();

  console.log('✓ Using mock agents (no API keys required)');
  console.log();

  // Create tools
  const calculator = new CalculatorTool();
  const weather = new WeatherTool();
  const search = new SearchTool();

  console.log('Available Tools:');
  console.log(`  • ${calculator.name}: ${calculator.description}`);
  console.log(`  • ${weather.name}: ${weather.description}`);
  console.log(`  • ${search.name}: ${search.description}`);
  console.log();

  // Create ReAct agent with mock reasoning
  const mockAgent = new MockReasoningAgent([calculator, weather, search]);
  const agent = new ReActAgent({
    agent: mockAgent,
    tools: [calculator, weather, search],
    maxSteps: 5,
  });

  console.log(`✓ Created ReAct agent with max ${5} reasoning steps`);
  console.log();

  // Example 1: Simple calculation
  console.log('-'.repeat(60));
  console.log('Example 1: Calculation with Tool');
  console.log('-'.repeat(60));
  console.log();

  const query1 = 'What is 15% tip on a bill of $47.50?';
  console.log(`Query: ${query1}`);
  console.log();

  const result1 = await agent.process(createMessage({ role: 'user', content: query1 }));
  console.log(`Result: ${result1.content}`);
  console.log();

  // Example 2: Weather lookup
  console.log('-'.repeat(60));
  console.log('Example 2: Weather Lookup');
  console.log('-'.repeat(60));
  console.log();

  const query2 = "What's the weather like in Paris today?";
  console.log(`Query: ${query2}`);
  console.log();

  const result2 = await agent.process(createMessage({ role: 'user', content: query2 }));
  console.log(`Result: ${result2.content}`);
  console.log();

  // Example 3: Search and reasoning
  console.log('-'.repeat(60));
  console.log('Example 3: Information Search');
  console.log('-'.repeat(60));
  console.log();

  const query3 = 'What is the ReAct pattern?';
  console.log(`Query: ${query3}`);
  console.log();

  const result3 = await agent.process(createMessage({ role: 'user', content: query3 }));
  console.log(`Result: ${result3.content}`);
  console.log();

  console.log('-'.repeat(60));
  console.log('✓ All ReAct examples completed!');
  console.log();
  console.log('Key Observations:');
  console.log('  • Agent reasons about which tool to use');
  console.log('  • Can use multiple tools in sequence');
  console.log('  • Combines tool results into coherent answers');
  console.log('  • Handles complex, multi-step problems');
  console.log();
  console.log('Production Usage:');
  console.log('  Replace MockReasoningAgent with real LLM adapters:');
  console.log('  - AnthropicAdapter (Claude with tool use)');
  console.log('  - OpenAIAdapter (GPT-4 with function calling)');
  console.log('  - LLMs will automatically reason and select tools');
  console.log('-'.repeat(60));
}

main().catch((error) => {
  console.error('Error:', error.message);
  process.exit(1);
});
