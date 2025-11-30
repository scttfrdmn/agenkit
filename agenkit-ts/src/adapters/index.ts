/**
 * LLM Adapters for AgentKit TypeScript
 */

export { LocalAgent } from './local';
export type { LocalAgentConfig, ProcessFunction, ProcessStreamFunction } from './local';

export { OpenAIAdapter } from './openai';
export type { OpenAIConfig } from './openai';

export { AnthropicAdapter } from './anthropic';
export type { AnthropicConfig } from './anthropic';

export { OllamaAdapter } from './ollama';
export type { OllamaConfig } from './ollama';
