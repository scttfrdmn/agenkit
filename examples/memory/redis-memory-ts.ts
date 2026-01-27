/**
 * Redis Memory Example - TypeScript
 *
 * Demonstrates Redis-backed persistent memory for production deployments.
 *
 * Prerequisites:
 *   docker run -d -p 6379:6379 redis:7-alpine
 *
 * Features:
 * - Persistent storage (survives restarts)
 * - TTL support (automatic expiry)
 * - Multi-instance agents (shared memory)
 * - Filtering (time, importance, tags)
 * - Utilities (session management, stats)
 */

import { RedisMemory, createMessage } from '@agenkit/core';

async function basicUsage() {
  console.log('='.repeat(60));
  console.log('Basic Redis Memory Usage');
  console.log('='.repeat(60));

  // Create Redis memory with 24-hour TTL
  const memory = new RedisMemory({
    redisUrl: 'redis://localhost:6379',
    ttl: 86400, // 24 hours
    keyPrefix: 'agenkit:demo',
  });

  try {
    const sessionId = 'demo-session-1';

    // Store messages with metadata
    console.log('\n📝 Storing messages...');
    await memory.store(sessionId, createMessage('user', 'What is Redis?'), {
      importance: 0.8,
      tags: ['question', 'technical'],
    });

    await memory.store(
      sessionId,
      createMessage(
        'assistant',
        'Redis is an in-memory data structure store used as a database, cache, and message broker.',
      ),
      {
        importance: 0.9,
        tags: ['answer', 'technical'],
      },
    );

    await memory.store(sessionId, createMessage('user', 'Thanks!'), {
      importance: 0.5,
      tags: ['gratitude'],
    });

    // Retrieve recent messages
    console.log('\n📤 Retrieving recent messages...');
    const messages = await memory.retrieve(sessionId, { limit: 3 });

    for (const msg of messages) {
      console.log(`[${msg.role}] ${msg.content}`);
    }

    // Get session count
    const count = await memory.getSessionCount(sessionId);
    console.log(`\n📊 Session has ${count} messages`);
  } finally {
    await memory.close();
  }
}

async function filteringExample() {
  console.log('\n' + '='.repeat(60));
  console.log('Filtering Example');
  console.log('='.repeat(60));

  const memory = new RedisMemory({
    redisUrl: 'redis://localhost:6379',
    keyPrefix: 'agenkit:filter',
  });

  try {
    const sessionId = 'filter-demo';

    // Store messages with different importance and tags
    console.log('\n📝 Storing messages with metadata...');
    await memory.store(sessionId, createMessage('user', 'Hello'), {
      importance: 0.3,
      tags: ['greeting'],
    });

    await memory.store(sessionId, createMessage('user', 'Can you help with Redis?'), {
      importance: 0.8,
      tags: ['question', 'redis'],
    });

    await memory.store(sessionId, createMessage('user', 'How do I scale it?'), {
      importance: 0.9,
      tags: ['question', 'scaling'],
    });

    await memory.store(sessionId, createMessage('user', 'Thanks!'), {
      importance: 0.2,
      tags: ['gratitude'],
    });

    // Filter by importance
    console.log('\n🔍 High-importance messages (>0.5):');
    const important = await memory.retrieve(sessionId, {
      importanceThreshold: 0.5,
      limit: 10,
    });
    for (const msg of important) {
      console.log(`  ${msg.content}`);
    }

    // Filter by tags
    console.log('\n🔍 Question messages:');
    const questions = await memory.retrieve(sessionId, {
      tags: ['question'],
      limit: 10,
    });
    for (const msg of questions) {
      console.log(`  ${msg.content}`);
    }

    // Combined filtering
    console.log('\n🔍 Important questions:');
    const importantQuestions = await memory.retrieve(sessionId, {
      importanceThreshold: 0.8,
      tags: ['question'],
      limit: 10,
    });
    for (const msg of importantQuestions) {
      console.log(`  ${msg.content}`);
    }
  } finally {
    await memory.close();
  }
}

async function multiSessionExample() {
  console.log('\n' + '='.repeat(60));
  console.log('Multi-Session Example');
  console.log('='.repeat(60));

  const memory = new RedisMemory({
    redisUrl: 'redis://localhost:6379',
    keyPrefix: 'agenkit:multi',
  });

  try {
    // Simulate multiple user sessions
    console.log('\n👥 Creating multiple sessions...');
    await memory.store('user-alice', createMessage('user', 'Hello from Alice'));
    await memory.store('user-bob', createMessage('user', 'Hello from Bob'));
    await memory.store('user-charlie', createMessage('user', 'Hello from Charlie'));

    // List all sessions
    console.log('\n📋 All sessions:');
    const sessions = await memory.getAllSessions();
    for (const session of sessions) {
      const count = await memory.getSessionCount(session);
      console.log(`  ${session}: ${count} messages`);
    }

    // Get usage statistics
    console.log('\n📊 Memory usage:');
    const usage = await memory.getMemoryUsage();
    console.log(`  Total sessions: ${usage.totalSessions}`);
    console.log(`  Total messages: ${usage.totalMessages}`);
    console.log(`  TTL: ${usage.ttl} seconds (${usage.ttl / 3600} hours)`);
  } finally {
    await memory.close();
  }
}

async function summarizationExample() {
  console.log('\n' + '='.repeat(60));
  console.log('Summarization Example');
  console.log('='.repeat(60));

  const memory = new RedisMemory({
    redisUrl: 'redis://localhost:6379',
    keyPrefix: 'agenkit:summary',
  });

  try {
    const sessionId = 'conversation';

    // Simulate a long conversation
    console.log('\n💬 Simulating conversation...');
    const conversation = [
      { role: 'user', content: 'What is Redis?' },
      { role: 'assistant', content: 'Redis is an in-memory database...' },
      { role: 'user', content: 'How fast is it?' },
      { role: 'assistant', content: 'Redis can handle millions of ops/sec...' },
      { role: 'user', content: 'Is it persistent?' },
      { role: 'assistant', content: 'Yes, Redis supports persistence...' },
    ];

    for (const msg of conversation) {
      await memory.store(sessionId, createMessage(msg.role, msg.content));
    }

    // Get summary
    console.log('\n📝 Conversation summary:');
    const summary = await memory.summarize(sessionId);
    console.log(summary.content);
  } finally {
    await memory.close();
  }
}

async function timeRangeExample() {
  console.log('\n' + '='.repeat(60));
  console.log('Time Range Filtering Example');
  console.log('='.repeat(60));

  const memory = new RedisMemory({
    redisUrl: 'redis://localhost:6379',
    keyPrefix: 'agenkit:time',
  });

  try {
    const sessionId = 'timeline';

    // Store messages
    console.log('\n📝 Storing messages over time...');
    await memory.store(sessionId, createMessage('user', 'Message 1'));
    await new Promise((resolve) => setTimeout(resolve, 1000)); // 1 second delay
    await memory.store(sessionId, createMessage('user', 'Message 2'));
    await new Promise((resolve) => setTimeout(resolve, 1000));
    await memory.store(sessionId, createMessage('user', 'Message 3'));

    // Get messages from last 2 seconds
    const now = new Date();
    const twoSecondsAgo = new Date(now.getTime() - 2000);

    console.log('\n🔍 Messages from last 2 seconds:');
    const recent = await memory.retrieve(sessionId, {
      timeRange: [twoSecondsAgo, now],
      limit: 10,
    });
    for (const msg of recent) {
      console.log(`  ${msg.content}`);
    }
  } finally {
    await memory.close();
  }
}

async function productionExample() {
  console.log('\n' + '='.repeat(60));
  console.log('Production Deployment Example');
  console.log('='.repeat(60));

  // Production configuration
  const memory = new RedisMemory({
    redisUrl: process.env.REDIS_URL || 'redis://localhost:6379',
    ttl: 7 * 24 * 3600, // 7 days
    keyPrefix: 'prod:agenkit:memory',
  });

  try {
    console.log('\n✅ Production features:');
    console.log('  • Persistent storage (survives restarts)');
    console.log('  • 7-day TTL (automatic cleanup)');
    console.log('  • Multi-instance support (shared memory)');
    console.log('  • Filtering (time, importance, tags)');
    console.log('  • Session management utilities');

    const capabilities = memory.capabilities;
    console.log('\n🎯 Capabilities:');
    for (const capability of capabilities) {
      console.log(`  • ${capability}`);
    }

    console.log('\n💡 Use cases:');
    console.log('  • Long-running agents (persist across restarts)');
    console.log('  • Multi-instance deployments (shared state)');
    console.log('  • Session recovery (restore after failure)');
    console.log('  • Conversation history (queryable archive)');
  } finally {
    await memory.close();
  }
}

async function main() {
  try {
    await basicUsage();
    await filteringExample();
    await multiSessionExample();
    await summarizationExample();
    await timeRangeExample();
    await productionExample();

    console.log('\n' + '='.repeat(60));
    console.log('✅ All examples completed!');
    console.log('='.repeat(60));
  } catch (err) {
    if (err instanceof Error && err.message.includes('ECONNREFUSED')) {
      console.error('\n❌ Error: Redis connection refused');
      console.error('Please start Redis: docker run -d -p 6379:6379 redis:7-alpine');
    } else {
      console.error('\n❌ Error:', err);
    }
    process.exit(1);
  }
}

main();
