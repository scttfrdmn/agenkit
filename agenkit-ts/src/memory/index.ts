/**
 * Memory systems for agent conversation management.
 *
 * This package provides interfaces and implementations for agent memory,
 * enabling context management beyond raw message lists.
 *
 * Classes:
 *   Memory: Abstract base interface for memory systems
 *   InMemoryMemory: Simple in-memory storage with LRU eviction
 *   HierarchyMemory: 3-tier hierarchy adapter (backward compatible)
 *   RedisMemory: Redis-backed persistent memory with TTL support
 *   VectorMemory: Semantic retrieval using embeddings and vector similarity
 *
 * Example:
 *   import { InMemoryMemory } from 'agenkit';
 *
 *   const memory = new InMemoryMemory({ maxSize: 1000 });
 *   await memory.store('session-123', message);
 *   const messages = await memory.retrieve('session-123', { limit: 10 });
 */

export { Memory } from './base';
export { InMemoryMemory } from './in-memory';
export { HierarchyMemory, HierarchyConfig } from './hierarchyMemory';
export { RedisMemory, RedisMemoryOptions } from './redisMemory';
export {
  VectorMemory,
  InMemoryVectorStore,
  EmbeddingProvider,
  VectorStore,
  MessageSearchResult,
  MessageWithMetadata,
} from './vector-memory';
export { OpenAIEmbeddings, ChromaDBVectorStore } from './integrations';
