/**
 * Router Agent
 *
 * Intelligently routes requests to specialized agents based on content.
 */

import { ReActAgent } from './react';
import { ConversationalAgent } from './conversational';

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

interface SpecialistAgent {
  name: string;
  keywords: string[];
  agent: ReActAgent | ConversationalAgent;
}

export class RouterAgent {
  private specialists: SpecialistAgent[];
  private defaultAgent: ConversationalAgent;

  constructor() {
    // Initialize specialist agents
    this.specialists = [
      {
        name: 'react',
        keywords: [
          'calculate',
          'compute',
          'math',
          'solve',
          'equation',
          'sum',
          'multiply',
          'divide',
          'add',
          'subtract',
        ],
        agent: new ReActAgent(),
      },
      {
        name: 'conversational',
        keywords: [
          'hello',
          'hi',
          'how are you',
          'chat',
          'talk',
          'conversation',
          'discuss',
        ],
        agent: new ConversationalAgent(),
      },
    ];

    // Default fallback
    this.defaultAgent = new ConversationalAgent();
  }

  async process(message: Message, options: ProcessOptions = {}): Promise<AgentResponse> {
    // Route based on message content
    const routedAgent = this.route(message.content);

    // Process with selected agent
    const response = await routedAgent.agent.process(message, options);

    // Add routing metadata
    return {
      content: response.content,
      metadata: {
        ...response.metadata,
        router_decision: routedAgent.name,
        routing_confidence: this.calculateConfidence(message.content, routedAgent),
      },
    };
  }

  private route(content: string): SpecialistAgent {
    const lowerContent = content.toLowerCase();

    // Score each specialist
    const scores = this.specialists.map((specialist) => ({
      specialist,
      score: this.calculateScore(lowerContent, specialist.keywords),
    }));

    // Find highest scoring specialist
    const best = scores.reduce((max, current) =>
      current.score > max.score ? current : max
    );

    // Use specialist if score is above threshold, otherwise default
    const threshold = 0.3;
    if (best.score >= threshold) {
      return best.specialist;
    }

    // Return default as a specialist structure
    return {
      name: 'default',
      keywords: [],
      agent: this.defaultAgent,
    };
  }

  private calculateScore(content: string, keywords: string[]): number {
    let matches = 0;
    for (const keyword of keywords) {
      if (content.includes(keyword)) {
        matches++;
      }
    }
    return keywords.length > 0 ? matches / keywords.length : 0;
  }

  private calculateConfidence(
    content: string,
    routedAgent: SpecialistAgent
  ): number {
    if (routedAgent.name === 'default') {
      return 0.5; // Neutral confidence for default routing
    }

    const score = this.calculateScore(content.toLowerCase(), routedAgent.keywords);
    return Math.min(0.5 + score * 0.5, 1.0); // Scale to 0.5-1.0 range
  }
}
