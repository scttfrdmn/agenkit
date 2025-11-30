/**
 * Reasoning with Tools Pattern Example
 *
 * Demonstrates:
 * - Tools available DURING reasoning (not just after)
 * - Interleaved thinking and tool use
 * - Multi-step reasoning with tool integration
 * - Dynamic tool selection during reasoning
 *
 * WHY use this pattern:
 * ✅ Tools available while agent is thinking (not sequential)
 * ✅ More natural problem-solving flow
 * ✅ Agent can check facts mid-reasoning
 * ✅ Reduces errors from incorrect assumptions
 * ✅ Better for complex multi-step problems
 *
 * WHEN to use:
 * - Complex reasoning requiring fact-checking
 * - Problems needing calculations mid-thought
 * - Tasks where assumptions need verification
 * - Multi-step problems with dependencies
 * - When accuracy is critical
 *
 * WHEN NOT to use:
 * - Simple tool calls (use ReAct instead)
 * - When tools are independent of reasoning
 * - Sequential workflows (use Planning instead)
 *
 * Key difference from ReAct:
 * - ReAct: Think → Act → Observe → Think (sequential)
 * - Reasoning with Tools: Think ↔ Act (interleaved)
 *
 * Setup:
 *   npm run build
 *   node dist/examples/patterns/reasoning-with-tools-pattern.js
 */

import { Agent, Message, Tool, ToolResult, createMessage } from '../../src/core/interfaces';

/**
 * Calculator tool for math operations
 */
class CalculatorTool implements Tool {
  name = 'calculator';
  description = 'Performs arithmetic operations: add, subtract, multiply, divide. Example: {"operation": "multiply", "a": 15.99, "b": 3}';
  inputSchema = {
    type: 'object' as const,
    properties: {
      operation: {
        type: 'string' as const,
        enum: ['add', 'subtract', 'multiply', 'divide'],
        description: 'The arithmetic operation to perform',
      },
      a: {
        type: 'number' as const,
        description: 'First number',
      },
      b: {
        type: 'number' as const,
        description: 'Second number',
      },
    },
    required: ['operation', 'a', 'b'],
  };

  async execute(params: Record<string, any>): Promise<ToolResult> {
    const { operation, a, b } = params;

    let result: number;
    switch (operation) {
      case 'add':
        result = a + b;
        break;
      case 'subtract':
        result = a - b;
        break;
      case 'multiply':
        result = a * b;
        break;
      case 'divide':
        if (b === 0) {
          return { output: '', error: 'Division by zero' };
        }
        result = a / b;
        break;
      default:
        return { output: '', error: `Unknown operation: ${operation}` };
    }

    return {
      output: `${a} ${operation} ${b} = ${result}`,
      error: undefined,
    };
  }
}

/**
 * Database lookup tool (simulated)
 */
class DatabaseTool implements Tool {
  name = 'database';
  description = 'Look up product prices from database. Example: {"product": "laptop"}';
  inputSchema = {
    type: 'object' as const,
    properties: {
      product: {
        type: 'string' as const,
        description: 'Product name to look up',
      },
    },
    required: ['product'],
  };

  private prices: Record<string, number> = {
    'laptop': 999.00,
    'mouse': 29.99,
    'keyboard': 79.99,
    'monitor': 349.99,
    'headphones': 149.99,
    'webcam': 89.99,
  };

  async execute(params: Record<string, any>): Promise<ToolResult> {
    const { product } = params;
    const price = this.prices[product.toLowerCase()];

    if (price === undefined) {
      return {
        output: '',
        error: `Product '${product}' not found in database`,
      };
    }

    return {
      output: `${product}: $${price.toFixed(2)}`,
      error: undefined,
    };
  }
}

/**
 * Unit converter tool
 */
class UnitConverterTool implements Tool {
  name = 'unit_converter';
  description = 'Convert between units. Example: {"value": 100, "from_unit": "km", "to_unit": "miles"}';
  inputSchema = {
    type: 'object' as const,
    properties: {
      value: {
        type: 'number' as const,
        description: 'Value to convert',
      },
      from_unit: {
        type: 'string' as const,
        description: 'Unit to convert from (km, miles, kg, lbs, celsius, fahrenheit)',
      },
      to_unit: {
        type: 'string' as const,
        description: 'Unit to convert to',
      },
    },
    required: ['value', 'from_unit', 'to_unit'],
  };

  private conversions: Record<string, Record<string, (v: number) => number>> = {
    'km': {
      'miles': (v) => v * 0.621371,
      'km': (v) => v,
    },
    'miles': {
      'km': (v) => v / 0.621371,
      'miles': (v) => v,
    },
    'kg': {
      'lbs': (v) => v * 2.20462,
      'kg': (v) => v,
    },
    'lbs': {
      'kg': (v) => v / 2.20462,
      'lbs': (v) => v,
    },
    'celsius': {
      'fahrenheit': (v) => (v * 9/5) + 32,
      'celsius': (v) => v,
    },
    'fahrenheit': {
      'celsius': (v) => (v - 32) * 5/9,
      'fahrenheit': (v) => v,
    },
  };

  async execute(params: Record<string, any>): Promise<ToolResult> {
    const { value, from_unit, to_unit } = params;

    const fromConverters = this.conversions[from_unit.toLowerCase()];
    if (!fromConverters) {
      return {
        output: '',
        error: `Unknown unit: ${from_unit}`,
      };
    }

    const converter = fromConverters[to_unit.toLowerCase()];
    if (!converter) {
      return {
        output: '',
        error: `Cannot convert from ${from_unit} to ${to_unit}`,
      };
    }

    const result = converter(value);
    return {
      output: `${value} ${from_unit} = ${result.toFixed(2)} ${to_unit}`,
      error: undefined,
    };
  }
}

/**
 * Weather lookup tool (simulated)
 */
class WeatherTool implements Tool {
  name = 'weather';
  description = 'Get current weather for a city. Example: {"city": "San Francisco"}';
  inputSchema = {
    type: 'object' as const,
    properties: {
      city: {
        type: 'string' as const,
        description: 'City name',
      },
    },
    required: ['city'],
  };

  private weatherData: Record<string, string> = {
    'san francisco': '72°F (22°C), sunny',
    'new york': '65°F (18°C), cloudy',
    'london': '58°F (14°C), rainy',
    'tokyo': '75°F (24°C), clear',
    'paris': '68°F (20°C), partly cloudy',
  };

  async execute(params: Record<string, any>): Promise<ToolResult> {
    const { city } = params;
    const weather = this.weatherData[city.toLowerCase()];

    if (!weather) {
      return {
        output: '',
        error: `Weather data not available for: ${city}`,
      };
    }

    return {
      output: `Weather in ${city}: ${weather}`,
      error: undefined,
    };
  }
}

/**
 * Mock reasoning agent that simulates tool use during reasoning
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

    // Simulate reasoning with tools based on query
    if (query.includes('laptop') && query.includes('mice')) {
      // Example 1: Shopping calculation
      const dbTool = this.tools.get('database');
      const calcTool = this.tools.get('calculator');

      if (dbTool && calcTool) {
        const laptop = await dbTool.execute({ product: 'laptop' });
        const mouse = await dbTool.execute({ product: 'mouse' });

        const laptopTotal = await calcTool.execute({ operation: 'multiply', a: 999, b: 2 });
        const mouseTotal = await calcTool.execute({ operation: 'multiply', a: 29.99, b: 3 });
        const grandTotal = await calcTool.execute({ operation: 'add', a: 1998, b: 89.97 });

        response = `I'll calculate the total cost for you:

**Items:**
- 2 laptops @ $999.00 each = $1,998.00
- 3 mice @ $29.99 each = $89.97

**Total Cost: $2,087.97**

This includes 2 laptops and 3 mice from our product catalog.`;
      }
    } else if (query.includes('km') && query.includes('days') && query.includes('miles')) {
      // Example 2: Distance conversion
      const calcTool = this.tools.get('calculator');
      const converterTool = this.tools.get('unit_converter');

      if (calcTool && converterTool) {
        const totalKm = await calcTool.execute({ operation: 'multiply', a: 250, b: 5 });
        const totalMiles = await converterTool.execute({ value: 1250, from_unit: 'km', to_unit: 'miles' });

        response = `Let me calculate that for you:

**Step 1:** Calculate total distance in km
250 km/day × 5 days = 1,250 km

**Step 2:** Convert to miles
1,250 km = 776.71 miles

**Answer: You would drive 776.71 miles in total.**`;
      }
    } else if (query.includes('tokyo') && query.includes('fahrenheit')) {
      // Example 3: Weather with conversion
      const weatherTool = this.tools.get('weather');

      if (weatherTool) {
        const weather = await weatherTool.execute({ city: 'Tokyo' });

        response = `Let me check the weather in Tokyo:

${weather.output}

The current temperature in Tokyo is already shown in Fahrenheit (75°F) as well as Celsius (24°C).`;
      }
    } else if (query.includes('budget') && query.includes('laptop') && query.includes('monitor')) {
      // Example 4: Complex budget calculation
      const dbTool = this.tools.get('database');
      const calcTool = this.tools.get('calculator');

      if (dbTool && calcTool) {
        const laptop = await dbTool.execute({ product: 'laptop' });
        const monitor = await dbTool.execute({ product: 'monitor' });

        const total = await calcTool.execute({ operation: 'add', a: 999, b: 349.99 });
        const remaining = await calcTool.execute({ operation: 'subtract', a: 1000, b: 1348.99 });

        response = `Let me help you with your budget calculation:

**Purchases:**
- Laptop: $999.00
- Monitor: $349.99
- **Subtotal: $1,348.99**

**Budget Analysis:**
- Original budget: $1,000.00
- Total cost: $1,348.99
- **You're $348.99 over budget**

**Note:** You would need an additional $348.99 to make these purchases.

For EUR conversion (assuming 1 USD = 0.85 EUR):
- Remaining if budget was higher: Would need $348.99 extra = €296.64 EUR`;
      }
    } else {
      response = 'I can help with calculations, database lookups, unit conversions, and weather queries. Please provide more details about what you need.';
    }

    return createMessage({ role: 'assistant', content: response });
  }
}

async function main() {
  console.log('='.repeat(70));
  console.log('AgentKit TypeScript - Reasoning with Tools Pattern Example');
  console.log('='.repeat(70));
  console.log();

  console.log('✓ Using mock agents (no API keys required)');
  console.log();

  // Create tools
  const calculator = new CalculatorTool();
  const database = new DatabaseTool();
  const converter = new UnitConverterTool();
  const weather = new WeatherTool();

  console.log('Available Tools:');
  console.log(`  • ${calculator.name}: Arithmetic operations`);
  console.log(`  • ${database.name}: Product price lookups`);
  console.log(`  • ${converter.name}: Unit conversions`);
  console.log(`  • ${weather.name}: Weather information`);
  console.log();

  // Create mock reasoning agent
  const mockAgent = new MockReasoningAgent([calculator, database, converter, weather]);

  // Example 1: Multi-step calculation with database lookup
  console.log('-'.repeat(70));
  console.log('Example 1: Multi-Step Calculation (Shopping Total)');
  console.log('-'.repeat(70));
  console.log();

  const examples = [
    {
      title: 'Example 1: Multi-Step Calculation (Shopping Total)',
      query: 'I want to buy 2 laptops and 3 mice. What is the total cost?',
    },
    {
      title: 'Example 2: Unit Conversion with Calculation',
      query: 'If I drive 250 km per day for 5 days, how many miles is that in total?',
    },
    {
      title: 'Example 3: Weather with Temperature Conversion',
      query: 'What is the temperature in Tokyo in Fahrenheit?',
    },
    {
      title: 'Example 4: Complex Multi-Tool Problem',
      query: 'I have a budget of 1000 USD. If I buy a laptop and a monitor, how much money will I have left? Express the remaining amount in both USD and what it would be if converted assuming 1 USD = 0.85 EUR.',
    },
  ];

  for (let i = 0; i < examples.length; i++) {
    const example = examples[i];

    if (i > 0) {
      console.log();
    }

    console.log('-'.repeat(70));
    console.log(example.title);
    console.log('-'.repeat(70));
    console.log();

    const query = createMessage({ role: 'user', content: example.query });
    console.log(`Query: ${query.content}`);
    console.log();

    const result = await mockAgent.process(query);

    console.log('Answer:');
    console.log(result.content);
    console.log();
  }

  // Pattern comparison
  console.log('-'.repeat(70));
  console.log('Pattern Comparison: ReAct vs Reasoning with Tools');
  console.log('-'.repeat(70));
  console.log();

  console.log('ReAct Pattern (Sequential):');
  console.log('  1. Observe the situation');
  console.log('  2. Think about what to do');
  console.log('  3. Act (use a tool)');
  console.log('  4. Observe the result');
  console.log('  5. Repeat');
  console.log('  → Good for: Simple tool sequences, independent operations');
  console.log();

  console.log('Reasoning with Tools Pattern (Interleaved):');
  console.log('  • Think and use tools simultaneously');
  console.log('  • Check facts during reasoning');
  console.log('  • More natural problem-solving flow');
  console.log('  • Reduce errors from assumptions');
  console.log('  → Good for: Complex reasoning, fact-checking, multi-step calculations');
  console.log();

  console.log('Example differences:');
  console.log('  ReAct: "Let me calculate this [use calculator] ... Now based on that..."');
  console.log('  Reasoning: "To solve this, I need to [use calculator while reasoning]..."');
  console.log();

  console.log('-'.repeat(70));
  console.log('✓ All reasoning with tools examples completed!');
  console.log();
  console.log('Key Benefits:');
  console.log('  • Tools available during thinking (not after)');
  console.log('  • More accurate results (fact-checking mid-reasoning)');
  console.log('  • Natural problem-solving flow');
  console.log('  • Better for complex multi-step problems');
  console.log('  • Reduces errors from incorrect assumptions');
  console.log();
  console.log('Production Usage:');
  console.log('  Replace MockReasoningAgent with real LLM adapters:');
  console.log('  - AnthropicAdapter (Claude with extended thinking)');
  console.log('  - OpenAIAdapter (GPT-4 with function calling)');
  console.log('  - LLMs will interleave reasoning with tool execution');
  console.log();
  console.log('When to Use:');
  console.log('  • Complex calculations requiring multiple steps');
  console.log('  • Problems needing fact verification during reasoning');
  console.log('  • Multi-step workflows with dependencies');
  console.log('  • When accuracy is critical');
  console.log('  • Tasks requiring database lookups mid-thought');
  console.log();
  console.log('Pattern Comparison:');
  console.log('  • Reasoning with Tools: Interleaved thinking + tool use');
  console.log('  • ReAct: Sequential observe → think → act');
  console.log('  • Planning: Break task into steps first');
  console.log('  • Task: One-shot execution');
  console.log('-'.repeat(70));
}

main().catch((error) => {
  console.error('Error:', error.message);
  process.exit(1);
});
