/**
 * ReAct Agent Implementation for Cloudflare Workers
 *
 * Reasoning and Action agent with tool use capabilities
 */

interface Message {
  role: string;
  content: string;
  metadata?: Record<string, any>;
}

interface ProcessContext {
  history: Message[];
  metadata: Record<string, any>;
  env: any;
}

interface AgentResponse {
  content: string;
  metadata: Record<string, any>;
}

export class ReActAgent {
  private maxSteps = 5;

  async process(message: Message, context: ProcessContext): Promise<AgentResponse> {
    const tools = this.getTools();
    const steps: any[] = [];

    let currentInput = message.content;
    let stepCount = 0;

    while (stepCount < this.maxSteps) {
      stepCount++;

      // Generate thought and action
      const thought = await this.generateThought(currentInput, steps, context);
      steps.push({ type: 'thought', content: thought });

      // Check if we should stop
      if (thought.includes('FINAL ANSWER:')) {
        const answer = thought.split('FINAL ANSWER:')[1].trim();
        return {
          content: answer,
          metadata: {
            agent_type: 'react',
            steps: steps.length,
            tool_calls: steps.filter(s => s.type === 'tool_call').length
          }
        };
      }

      // Extract action and tool
      const action = this.extractAction(thought);
      if (action) {
        steps.push({ type: 'action', ...action });

        // Execute tool
        const tool = tools.find(t => t.name === action.tool);
        if (tool) {
          const result = await tool.execute(action.input);
          steps.push({ type: 'observation', content: result });
          currentInput = `Previous observation: ${result}`;
        } else {
          steps.push({ type: 'observation', content: `Tool ${action.tool} not found` });
        }
      }
    }

    // Max steps reached
    return {
      content: 'Unable to complete task within maximum steps',
      metadata: {
        agent_type: 'react',
        steps: steps.length,
        max_steps_reached: true
      }
    };
  }

  private async generateThought(input: string, steps: any[], context: ProcessContext): Promise<string> {
    // Simplified mock implementation
    // In production, call LLM API (OpenAI, Anthropic, etc.)

    if (input.toLowerCase().includes('calculate') || input.toLowerCase().includes('math')) {
      const numbers = input.match(/\d+/g);
      if (numbers && numbers.length >= 2) {
        return `ACTION: calculator
INPUT: {"operation": "add", "a": ${numbers[0]}, "b": ${numbers[1]}}`;
      }
    }

    return `FINAL ANSWER: I've processed your request: ${input}`;
  }

  private extractAction(thought: string): { tool: string; input: any } | null {
    const actionMatch = thought.match(/ACTION:\s*(\w+)\s*INPUT:\s*({.*})/s);
    if (actionMatch) {
      try {
        return {
          tool: actionMatch[1],
          input: JSON.parse(actionMatch[2])
        };
      } catch {
        return null;
      }
    }
    return null;
  }

  private getTools() {
    return [
      {
        name: 'calculator',
        description: 'Performs basic arithmetic operations',
        execute: async (input: { operation: string; a: number; b: number }) => {
          const { operation, a, b } = input;
          switch (operation) {
            case 'add':
              return `${a + b}`;
            case 'subtract':
              return `${a - b}`;
            case 'multiply':
              return `${a * b}`;
            case 'divide':
              return b !== 0 ? `${a / b}` : 'Error: Division by zero';
            default:
              return `Unknown operation: ${operation}`;
          }
        }
      }
    ];
  }
}
