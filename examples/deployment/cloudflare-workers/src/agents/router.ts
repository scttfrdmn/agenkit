/**
 * Router Agent Implementation for Cloudflare Workers
 *
 * Intelligent routing to specialist agents
 */

import { ReActAgent } from './react';
import { ConversationalAgent } from './conversational';

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

export class RouterAgent {
  private reactAgent = new ReActAgent();
  private conversationalAgent = new ConversationalAgent();

  async process(message: Message, context: ProcessContext): Promise<AgentResponse> {
    // Determine which agent to use
    const route = this.routeMessage(message);

    // Route to appropriate agent
    let response: AgentResponse;
    switch (route) {
      case 'react':
        response = await this.reactAgent.process(message, context);
        break;
      case 'conversational':
        response = await this.conversationalAgent.process(message, context);
        break;
      default:
        response = await this.conversationalAgent.process(message, context);
    }

    // Add routing metadata
    response.metadata = {
      ...response.metadata,
      agent_type: 'router',
      routed_to: route,
      routing_confidence: this.getRoutingConfidence(message, route)
    };

    return response;
  }

  private routeMessage(message: Message): 'react' | 'conversational' {
    const content = message.content.toLowerCase();

    // Keywords that suggest ReAct agent (tool use)
    const reactKeywords = [
      'calculate', 'compute', 'math', 'solve',
      'search', 'lookup', 'find data', 'api',
      'execute', 'run', 'perform'
    ];

    // Keywords that suggest Conversational agent
    const conversationalKeywords = [
      'chat', 'talk', 'tell me', 'explain',
      'hello', 'hi', 'how are you', 'what is',
      'help', 'assist', 'advice'
    ];

    // Check for ReAct keywords
    for (const keyword of reactKeywords) {
      if (content.includes(keyword)) {
        return 'react';
      }
    }

    // Check for Conversational keywords
    for (const keyword of conversationalKeywords) {
      if (content.includes(keyword)) {
        return 'conversational';
      }
    }

    // Default to conversational
    return 'conversational';
  }

  private getRoutingConfidence(message: Message, route: string): number {
    // Simple confidence scoring based on keyword matching
    const content = message.content.toLowerCase();

    if (route === 'react') {
      const reactKeywords = ['calculate', 'compute', 'math', 'solve'];
      const matches = reactKeywords.filter(k => content.includes(k)).length;
      return Math.min(0.5 + (matches * 0.2), 1.0);
    }

    if (route === 'conversational') {
      const convKeywords = ['chat', 'talk', 'tell', 'explain'];
      const matches = convKeywords.filter(k => content.includes(k)).length;
      return Math.min(0.5 + (matches * 0.2), 1.0);
    }

    return 0.5;
  }
}
