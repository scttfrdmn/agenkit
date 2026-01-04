/**
 * Conversational Agent
 *
 * Multi-turn conversational agent with context awareness.
 * Integrates with OpenAI API (with mock fallback).
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

export class ConversationalAgent {
  private maxHistory: number;

  constructor(maxHistory: number = 10) {
    this.maxHistory = maxHistory;
  }

  async process(message: Message, options: ProcessOptions = {}): Promise<AgentResponse> {
    const history = options.history || [];
    const env = options.env || {};

    // Try OpenAI API if key is available
    if (env.OPENAI_API_KEY) {
      try {
        return await this.processWithOpenAI(message, history, env.OPENAI_API_KEY);
      } catch (error) {
        console.warn('OpenAI API failed, falling back to mock:', error);
        // Fall through to mock implementation
      }
    }

    // Mock implementation for demo/testing
    return this.processWithMock(message, history);
  }

  private async processWithOpenAI(
    message: Message,
    history: Array<{ role: string; content: string; timestamp: number }>,
    apiKey: string
  ): Promise<AgentResponse> {
    // Build conversation messages
    const messages = [
      {
        role: 'system',
        content:
          'You are a helpful AI assistant. Provide concise, friendly responses.',
      },
      ...history.slice(-this.maxHistory).map((msg) => ({
        role: msg.role,
        content: msg.content,
      })),
      { role: message.role, content: message.content },
    ];

    // Call OpenAI API
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: 'gpt-3.5-turbo',
        messages,
        temperature: 0.7,
        max_tokens: 500,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`OpenAI API error: ${error}`);
    }

    const data = await response.json();
    const content = data.choices[0].message.content;

    return {
      content,
      metadata: {
        agent_type: 'conversational',
        model: 'gpt-3.5-turbo',
        history_length: history.length,
        provider: 'openai',
      },
    };
  }

  private processWithMock(
    message: Message,
    history: Array<{ role: string; content: string; timestamp: number }>
  ): AgentResponse {
    const content = message.content.toLowerCase();

    // Context-aware responses based on history
    let response: string;

    if (history.length === 0) {
      // First message
      if (content.includes('hello') || content.includes('hi')) {
        response =
          "Hello! I'm a conversational agent. I can remember our conversation and provide context-aware responses. How can I help you today?";
      } else if (content.includes('help')) {
        response =
          "I'm here to help! I can:\n- Have natural conversations\n- Remember context from our chat\n- Answer questions\n- Provide assistance\n\nWhat would you like to talk about?";
      } else {
        response =
          "Nice to meet you! I'm a conversational AI agent. I'll remember our conversation as we chat. What would you like to discuss?";
      }
    } else {
      // Continuing conversation
      const recentMessages = history.slice(-3);
      const hasGreeting = recentMessages.some((msg) =>
        msg.content.toLowerCase().match(/hello|hi|hey/)
      );

      if (content.includes('remember')) {
        response = `Yes, I remember our conversation! We've exchanged ${history.length} messages so far. I'm keeping track of our discussion context.`;
      } else if (content.includes('thank')) {
        response = "You're welcome! Is there anything else I can help you with?";
      } else if (content.includes('bye') || content.includes('goodbye')) {
        response = `Goodbye! It was nice chatting with you. We had ${history.length + 1} messages in this conversation.`;
      } else if (hasGreeting) {
        response = "We've already said hello! How can I assist you further?";
      } else {
        response = `I understand. Based on our conversation so far (${history.length} previous messages), I'll do my best to help. Could you provide more details?`;
      }
    }

    return {
      content: response,
      metadata: {
        agent_type: 'conversational',
        history_length: history.length,
        max_history: this.maxHistory,
        provider: 'mock',
      },
    };
  }
}
