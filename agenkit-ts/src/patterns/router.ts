/**
 * Router Pattern
 *
 * Implements conditional agent selection based on message classification.
 * A classifier determines the intent/category, then routes the request to
 * an appropriate specialist agent.
 *
 * Key concepts:
 * - Intent/category classification
 * - Conditional routing to specialists
 * - Single agent execution per request
 * - Dynamic agent selection based on input
 *
 * Performance characteristics:
 * - Time: O(classification + selected agent)
 * - Memory: O(1) - only one agent executes
 * - Efficient single-path execution
 *
 * Example use cases:
 * - Customer service: route to billing, technical, account agents
 * - Content moderation: route to spam, abuse, quality agents
 * - Language routing: route to language-specific agents
 * - Skill-based routing: route to domain expert agents
 * - Intent-based chatbots: route to booking, info, support agents
 *
 * Example:
 * ```typescript
 * const classifier = new LLMClassifier(llmAgent, ['billing', 'technical', 'account']);
 * const router = new RouterAgent({
 *   classifier,
 *   agents: {
 *     billing: billingAgent,
 *     technical: technicalAgent,
 *     account: accountAgent
 *   }
 * });
 *
 * const result = await router.process(
 *   createMessage('user', 'I need help with my invoice')
 * );
 * // Routes to billingAgent based on classification
 * ```
 */

import { Agent, Message, createMessage } from '../core/interfaces';

/**
 * Agent responsible for determining routing decisions.
 *
 * The classifier analyzes the input message and returns a category/intent
 * that determines which specialist agent should handle the request.
 */
export interface ClassifierAgent extends Agent {
  /**
   * Determines the category/intent for routing.
   *
   * @param message - Input message to classify
   * @returns Category string that matches a specialist key
   */
  classify(message: Message): Promise<string>;
}

/**
 * Configuration for RouterAgent.
 */
export interface RouterConfig {
  /** Classifier determines which agent to route to */
  classifier: ClassifierAgent;
  /** Agents maps categories to specialist agents */
  agents: Record<string, Agent>;
  /** DefaultKey specifies fallback agent when classification doesn't match (optional) */
  defaultKey?: string;
}

/**
 * Router agent that routes messages to appropriate agents based on classification.
 *
 * The router uses a classifier to determine message intent/category, then
 * delegates to the corresponding specialist agent. This enables efficient
 * conditional processing without executing all agents.
 *
 * The router pattern is ideal when requests have clear categories and
 * different agents handle different types of requests.
 *
 * @example
 * ```typescript
 * const router = new RouterAgent({
 *   classifier: myClassifier,
 *   agents: {
 *     support: supportAgent,
 *     sales: salesAgent,
 *     info: infoAgent
 *   },
 *   defaultKey: 'support'
 * });
 *
 * const result = await router.process(
 *   createMessage('user', 'Tell me about pricing')
 * );
 * // Routes to salesAgent
 * ```
 */
export class RouterAgent implements Agent {
  readonly name = 'RouterAgent';
  private classifier: ClassifierAgent;
  private agents: Record<string, Agent>;
  private defaultKey?: string;

  /**
   * Creates a new router agent.
   *
   * @param config - Router configuration with classifier and agents
   * @throws Error if config invalid, classifier missing, or no agents provided
   *
   * @example
   * ```typescript
   * const router = new RouterAgent({
   *   classifier: myClassifier,
   *   agents: { cat1: agent1, cat2: agent2 }
   * });
   * ```
   */
  constructor(config: RouterConfig) {
    if (!config) {
      throw new Error('config is required');
    }
    if (!config.classifier) {
      throw new Error('classifier is required');
    }
    if (!config.agents || Object.keys(config.agents).length === 0) {
      throw new Error('at least one agent is required');
    }

    // Validate default key if provided
    if (config.defaultKey && !(config.defaultKey in config.agents)) {
      throw new Error(`default key '${config.defaultKey}' not found in agents map`);
    }

    this.classifier = config.classifier;
    this.agents = config.agents;
    this.defaultKey = config.defaultKey;
  }

  /**
   * Returns the combined capabilities of all agents.
   */
  get capabilities(): string[] {
    const capSet = new Set<string>();

    // Add classifier capabilities
    if (this.classifier.capabilities) {
      for (const cap of this.classifier.capabilities) {
        capSet.add(cap);
      }
    }

    // Add agent capabilities
    for (const agent of Object.values(this.agents)) {
      if (agent.capabilities) {
        for (const cap of agent.capabilities) {
          capSet.add(cap);
        }
      }
    }

    capSet.add('router');
    capSet.add('conditional');
    capSet.add('classification');

    return Array.from(capSet);
  }

  /**
   * Classifies the message and routes to appropriate agent.
   *
   * The process follows these steps:
   * 1. Classification: Determine message category/intent
   * 2. Route selection: Look up corresponding agent
   * 3. Execution: Delegate to selected agent
   *
   * If classification fails, an error is thrown. If the classified category
   * doesn't match any agent and no default is configured, an error is thrown.
   *
   * The final message includes metadata about the routing decision.
   *
   * @param message - Input message to process
   * @returns Response from selected agent
   * @throws Error if message invalid, classification fails, or no matching agent
   *
   * @example
   * ```typescript
   * const result = await router.process(
   *   createMessage('user', 'Help me with billing')
   * );
   *
   * // Access routing metadata
   * console.log(result.metadata?.routed_category);
   * console.log(result.metadata?.routed_agent);
   * ```
   */
  async process(message: Message): Promise<Message> {
    if (!message) {
      throw new Error('message cannot be nil');
    }

    // Step 1: Classify the message
    let category: string;
    try {
      category = await this.classifier.classify(message);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      throw new Error(`classification failed: ${errorMsg}`);
    }

    // Step 2: Select agent based on category
    let agent = this.agents[category];
    if (!agent) {
      // Try default agent if configured
      if (this.defaultKey) {
        agent = this.agents[this.defaultKey];
        category = this.defaultKey; // Update category to reflect actual routing
      } else {
        const availableCategories = Object.keys(this.agents);
        throw new Error(
          `no agent found for category '${category}' (available: ${availableCategories.join(', ')})`,
        );
      }
    }

    // Step 3: Execute selected agent
    let result: Message;
    try {
      result = await agent.process(message);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      throw new Error(`agent '${agent.name}' (category: ${category}) failed: ${errorMsg}`);
    }

    // Add routing metadata
    if (!result.metadata) {
      result.metadata = {};
    }
    result.metadata.routed_category = category;
    result.metadata.routed_agent = agent.name;
    result.metadata.available_routes = Object.keys(this.agents).length;

    return result;
  }
}

/**
 * Simple classifier using keyword matching.
 *
 * This classifier uses simple string matching to determine categories.
 * For production use, consider implementing a custom ClassifierAgent with
 * ML-based classification or more sophisticated logic.
 *
 * @example
 * ```typescript
 * const classifier = new SimpleClassifier(fallbackAgent, {
 *   billing: ['invoice', 'payment', 'charge'],
 *   technical: ['bug', 'error', 'broken'],
 *   account: ['password', 'login', 'profile']
 * });
 * ```
 */
export class SimpleClassifier implements ClassifierAgent {
  readonly name = 'SimpleClassifier';
  private agent: Agent;
  private keywords: Record<string, string[]>;

  /**
   * Creates a keyword-based classifier.
   *
   * @param agent - Fallback agent for complex classifications
   * @param keywords - Map of categories to keyword lists
   */
  constructor(agent: Agent, keywords: Record<string, string[]>) {
    this.agent = agent;
    this.keywords = keywords;
  }

  /**
   * Returns the classifier's capabilities.
   */
  get capabilities(): string[] {
    const caps = this.agent.capabilities ? [...this.agent.capabilities] : [];
    caps.push('classification', 'keyword-matching');
    return caps;
  }

  /**
   * Handles direct message processing (delegates to underlying agent).
   *
   * @param message - Input message
   * @returns Agent response
   */
  async process(message: Message): Promise<Message> {
    return this.agent.process(message);
  }

  /**
   * Determines category using keyword matching.
   *
   * @param message - Input message to classify
   * @returns Category with most keyword matches
   * @throws Error if no keyword matches found
   */
  async classify(message: Message): Promise<string> {
    if (!message) {
      throw new Error('message cannot be nil');
    }

    const content = String(message.content).toLowerCase();

    // Check each category's keywords
    let maxMatches = 0;
    let bestCategory = '';

    for (const [category, keywords] of Object.entries(this.keywords)) {
      let matches = 0;
      for (const keyword of keywords) {
        if (content.includes(keyword.toLowerCase())) {
          matches++;
        }
      }

      if (matches > maxMatches) {
        maxMatches = matches;
        bestCategory = category;
      }
    }

    if (!bestCategory) {
      throw new Error('unable to classify message - no keyword matches found');
    }

    return bestCategory;
  }
}

/**
 * LLM-based classifier for classification.
 *
 * This classifier prompts an LLM to determine the category. The LLM is given
 * a list of valid categories and must respond with one of them.
 *
 * @example
 * ```typescript
 * const classifier = new LLMClassifier(
 *   llmAgent,
 *   ['support', 'sales', 'technical']
 * );
 * ```
 */
export class LLMClassifier implements ClassifierAgent {
  readonly name = 'LLMClassifier';
  private agent: Agent;
  private categories: string[];
  private prompt: string;

  /**
   * Creates an LLM-based classifier.
   *
   * @param agent - LLM agent for classification
   * @param categories - List of valid category names
   */
  constructor(agent: Agent, categories: string[]) {
    this.agent = agent;
    this.categories = categories.length > 0 ? categories : ['general'];

    this.prompt = `Classify the following message into one of these categories: ${this.categories.join(', ')}

Reply with ONLY the category name, nothing else.

Message: `;
  }

  /**
   * Returns the classifier's capabilities.
   */
  get capabilities(): string[] {
    const caps = this.agent.capabilities ? [...this.agent.capabilities] : [];
    caps.push('classification', 'llm-classification');
    return caps;
  }

  /**
   * Handles direct message processing (delegates to underlying agent).
   *
   * @param message - Input message
   * @returns Agent response
   */
  async process(message: Message): Promise<Message> {
    return this.agent.process(message);
  }

  /**
   * Uses LLM to determine category.
   *
   * @param message - Input message to classify
   * @returns Category from LLM response
   * @throws Error if classification fails or returns invalid category
   */
  async classify(message: Message): Promise<string> {
    if (!message) {
      throw new Error('message cannot be nil');
    }

    // Build classification prompt
    const classificationMsg = createMessage('user', this.prompt + String(message.content));

    // Get LLM classification
    let result: Message;
    try {
      result = await this.agent.process(classificationMsg);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      throw new Error(`llm classification failed: ${errorMsg}`);
    }

    const category = String(result.content).trim();

    // Validate category is in allowed list
    for (const validCat of this.categories) {
      if (category.toLowerCase() === validCat.toLowerCase()) {
        return validCat;
      }
    }

    throw new Error(
      `llm returned invalid category '${category}' (valid: ${this.categories.join(', ')})`,
    );
  }
}
