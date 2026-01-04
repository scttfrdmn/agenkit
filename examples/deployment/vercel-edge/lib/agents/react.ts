/**
 * ReAct Agent - Reasoning and Acting
 *
 * Combines reasoning with tool use for multi-step problem solving.
 */

export interface Message {
  role: string;
  content: string;
  metadata?: Record<string, any>;
}

export interface ProcessOptions {
  history?: Array<{ role: string; content: string; timestamp: number }>;
  metadata?: Record<string, any>;
  env?: Record<string, string>;
}

export interface AgentResponse {
  content: string;
  metadata: Record<string, any>;
}

export class ReActAgent {
  private maxSteps: number;

  constructor(maxSteps: number = 5) {
    this.maxSteps = maxSteps;
  }

  async process(message: Message, options: ProcessOptions = {}): Promise<AgentResponse> {
    const steps: string[] = [];
    let finalAnswer = '';
    let currentStep = 0;

    // Simple calculator tool
    const calculator = (expression: string): string => {
      try {
        // Safe eval for basic math only
        const sanitized = expression.replace(/[^0-9+\-*/().\s]/g, '');
        const result = Function(`"use strict"; return (${sanitized})`)();
        return String(result);
      } catch (error) {
        return `Error: ${error instanceof Error ? error.message : 'Unknown error'}`;
      }
    };

    // Parse message for calculation requests
    const content = message.content.toLowerCase();

    // Step 1: Thought - Understand the problem
    steps.push(`Thought: I need to solve "${message.content}"`);
    currentStep++;

    // Check if it's a calculation
    const mathPattern = /(?:calculate|compute|what is|what's|solve|find)\s*([\d+\-*/().\s]+)/i;
    const match = message.content.match(mathPattern);

    if (match && currentStep < this.maxSteps) {
      // Step 2: Action - Use calculator
      const expression = match[1].trim();
      steps.push(`Action: calculator("${expression}")`);
      currentStep++;

      // Step 3: Observation - Get result
      const result = calculator(expression);
      steps.push(`Observation: ${result}`);
      currentStep++;

      // Step 4: Final Thought
      steps.push(`Thought: I have the answer`);
      finalAnswer = `The answer is ${result}`;
      currentStep++;
    } else {
      // Non-calculation query
      steps.push(`Thought: This is a conversational query`);
      finalAnswer = this.generateConversationalResponse(message.content);
      currentStep++;
    }

    return {
      content: finalAnswer,
      metadata: {
        agent_type: 'react',
        steps: steps.length,
        reasoning_steps: steps,
        max_steps: this.maxSteps,
        tools_used: match ? ['calculator'] : [],
      },
    };
  }

  private generateConversationalResponse(query: string): string {
    // Simple mock responses
    const lowerQuery = query.toLowerCase();

    if (lowerQuery.includes('hello') || lowerQuery.includes('hi')) {
      return "Hello! I'm a ReAct agent. I can help you with calculations and answer questions. Try asking me to calculate something!";
    }

    if (lowerQuery.includes('help')) {
      return "I'm a ReAct agent that combines reasoning with tool use. I can:\n- Perform calculations (e.g., 'calculate 15 * 3')\n- Answer questions through step-by-step reasoning\n- Explain my thought process";
    }

    if (lowerQuery.includes('who are you') || lowerQuery.includes('what are you')) {
      return "I'm a ReAct agent - I combine Reasoning and Acting to solve problems step by step. I can use tools like a calculator and explain my reasoning process.";
    }

    return "I understand your query. For calculations, try asking 'calculate X + Y'. For other questions, I'll do my best to help!";
  }
}
