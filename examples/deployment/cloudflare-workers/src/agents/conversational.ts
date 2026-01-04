/**
 * Conversational Agent Implementation for Cloudflare Workers
 *
 * Multi-turn conversation agent with memory
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

export class ConversationalAgent {
  private maxHistory = 10;
  private systemPrompt = 'You are a helpful AI assistant running on Cloudflare Workers at the edge.';

  async process(message: Message, context: ProcessContext): Promise<AgentResponse> {
    // Get recent conversation history
    const recentHistory = this.getRecentHistory(context.history);

    // Generate response
    const response = await this.generateResponse(message, recentHistory, context);

    return {
      content: response,
      metadata: {
        agent_type: 'conversational',
        history_length: recentHistory.length,
        system_prompt: this.systemPrompt
      }
    };
  }

  private getRecentHistory(history: Message[]): Message[] {
    // Get last N messages (excluding current)
    return history.slice(Math.max(0, history.length - this.maxHistory - 1), -1);
  }

  private async generateResponse(
    message: Message,
    history: Message[],
    context: ProcessContext
  ): Promise<string> {
    // Simplified mock implementation
    // In production, call LLM API with conversation history

    const { env } = context;

    // Example: Call OpenAI API (requires OPENAI_API_KEY in env)
    if (env.OPENAI_API_KEY) {
      try {
        const messages = [
          { role: 'system', content: this.systemPrompt },
          ...history.map(h => ({ role: h.role, content: h.content })),
          { role: message.role, content: message.content }
        ];

        const response = await fetch('https://api.openai.com/v1/chat/completions', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${env.OPENAI_API_KEY}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            model: 'gpt-4',
            messages: messages,
            max_tokens: 500,
            temperature: 0.7
          })
        });

        if (response.ok) {
          const data = await response.json() as any;
          return data.choices[0].message.content;
        }
      } catch (error) {
        console.error('OpenAI API error:', error);
      }
    }

    // Fallback mock response
    return this.generateMockResponse(message, history);
  }

  private generateMockResponse(message: Message, history: Message[]): string {
    const content = message.content.toLowerCase();

    // Simple pattern matching for demo
    if (content.includes('hello') || content.includes('hi')) {
      return 'Hello! How can I assist you today?';
    }

    if (content.includes('how are you')) {
      return "I'm functioning well, thank you! I'm running on Cloudflare's edge network, which means I can respond quickly from anywhere in the world. How can I help you?";
    }

    if (content.includes('what can you do')) {
      return 'I can help you with various tasks including answering questions, providing information, and having natural conversations. I maintain context from our conversation history to provide more relevant responses.';
    }

    if (content.includes('bye') || content.includes('goodbye')) {
      return 'Goodbye! Feel free to come back anytime you need assistance.';
    }

    // Context-aware response if there's history
    if (history.length > 0) {
      return `I understand you're asking about "${message.content}". Based on our conversation so far, I'd be happy to help you with that.`;
    }

    // Default response
    return `I received your message: "${message.content}". I'm currently running in demo mode. In production, I would process this using a real LLM API.`;
  }
}
