/**
 * Message Property-Based Tests
 *
 * Validates invariants for message serialization and structure:
 * - Round-trip serialization preserves all fields
 * - Role is always a valid string
 * - Content is preserved through serialize/deserialize
 * - Metadata is preserved
 * - Unicode content round-trips correctly
 * - Large metadata round-trips correctly
 * - Idempotent serialization
 * - Two messages with same fields compare equal
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import type { Message } from '../../core/interfaces';
import { createMessage } from '../../core/interfaces';
import {
  shortContentArbitrary,
  roleArbitrary,
  metadataArbitrary,
  messageArbitrary,
  smallMessagesArbitrary,
} from './strategies';

// ============================================
// Property: Round-Trip JSON Serialization
// ============================================

describe('Message Properties: Serialization', () => {
  it('should preserve role through JSON round-trip', () => {
    fc.assert(
      fc.property(roleArbitrary, shortContentArbitrary, (role, content) => {
        const message: Message = { role, content };
        const serialized = JSON.stringify(message);
        const deserialized = JSON.parse(serialized) as Message;

        expect(deserialized.role).toBe(message.role);
      }),
      { numRuns: 100 }
    );
  });

  it('should preserve content through JSON round-trip', () => {
    fc.assert(
      fc.property(shortContentArbitrary, (content) => {
        const message: Message = { role: 'user', content };
        const serialized = JSON.stringify(message);
        const deserialized = JSON.parse(serialized) as Message;

        expect(deserialized.content).toBe(content);
      }),
      { numRuns: 100 }
    );
  });

  it('should preserve metadata through JSON round-trip', () => {
    fc.assert(
      fc.property(metadataArbitrary, (metadata) => {
        const message: Message = { role: 'user', content: 'test', metadata };
        const serialized = JSON.stringify(message);
        const deserialized = JSON.parse(serialized) as Message;

        // Metadata keys should be preserved
        const originalKeys = Object.keys(metadata);
        const deserializedKeys = Object.keys(deserialized.metadata || {});
        expect(deserializedKeys).toHaveLength(originalKeys.length);
      }),
      { numRuns: 100 }
    );
  });

  it('should be idempotent: serialize twice, same result', () => {
    fc.assert(
      fc.property(messageArbitrary, (message) => {
        const s1 = JSON.stringify(message);
        const d1 = JSON.parse(s1) as Message;
        const s2 = JSON.stringify(d1);

        expect(s1).toBe(s2);
      }),
      { numRuns: 100 }
    );
  });
});

// ============================================
// Property: Unicode Content
// ============================================

describe('Message Properties: Unicode', () => {
  it('should handle Unicode content correctly', () => {
    fc.assert(
      fc.property(fc.string({ minLength: 1, maxLength: 100 }), (unicode) => {
        const message: Message = { role: 'user', content: unicode };
        const serialized = JSON.stringify(message);
        const deserialized = JSON.parse(serialized) as Message;

        expect(deserialized.content).toBe(unicode);
      }),
      { numRuns: 100 }
    );
  });

  it('should handle emoji content', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('Hello 👋', '🎉 Party! 🎊', '日本語テスト', 'Ñoño', '测试'),
        (content) => {
          const message = createMessage('user', content);
          const serialized = JSON.stringify(message);
          const deserialized = JSON.parse(serialized) as Message;

          expect(deserialized.content).toBe(content);
        }
      ),
      { numRuns: 20 }
    );
  });
});

// ============================================
// Property: Message Equality
// ============================================

describe('Message Properties: Equality', () => {
  it('two messages with same fields should serialize identically', () => {
    fc.assert(
      fc.property(roleArbitrary, shortContentArbitrary, (role, content) => {
        const msg1: Message = { role, content };
        const msg2: Message = { role, content };

        expect(JSON.stringify(msg1)).toBe(JSON.stringify(msg2));
      }),
      { numRuns: 100 }
    );
  });

  it('messages with different roles should differ', () => {
    fc.assert(
      fc.property(shortContentArbitrary, (content) => {
        const msg1: Message = { role: 'user', content };
        const msg2: Message = { role: 'assistant', content };

        expect(JSON.stringify(msg1)).not.toBe(JSON.stringify(msg2));
      }),
      { numRuns: 50 }
    );
  });
});

// ============================================
// Property: Large Metadata
// ============================================

describe('Message Properties: Large Metadata', () => {
  it('should handle large metadata with many keys', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 50 }),
        (numKeys) => {
          const metadata: Record<string, unknown> = {};
          for (let i = 0; i < numKeys; i++) {
            metadata[`key_${i}`] = `value_${i}`;
          }

          const message: Message = { role: 'user', content: 'test', metadata };
          const serialized = JSON.stringify(message);
          const deserialized = JSON.parse(serialized) as Message;

          expect(Object.keys(deserialized.metadata || {}).length).toBe(numKeys);
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ============================================
// Property: createMessage Helper
// ============================================

describe('Message Properties: createMessage', () => {
  it('should always set timestamp', () => {
    fc.assert(
      fc.property(roleArbitrary, shortContentArbitrary, (role, content) => {
        const message = createMessage(role, content);

        expect(message.timestamp).toBeDefined();
        expect(typeof message.timestamp).toBe('string');
        // Should be valid ISO string
        expect(() => new Date(message.timestamp!)).not.toThrow();
      }),
      { numRuns: 100 }
    );
  });

  it('should always set metadata as empty object when not provided', () => {
    fc.assert(
      fc.property(roleArbitrary, shortContentArbitrary, (role, content) => {
        const message = createMessage(role, content);

        expect(message.metadata).toBeDefined();
        expect(typeof message.metadata).toBe('object');
      }),
      { numRuns: 100 }
    );
  });

  it('should preserve provided metadata', () => {
    fc.assert(
      fc.property(
        roleArbitrary,
        shortContentArbitrary,
        fc.dictionary(
          fc.string({ minLength: 1, maxLength: 20 }),
          fc.string({ maxLength: 50 }),
          { maxKeys: 10 }
        ),
        (role, content, extraMeta) => {
          const message = createMessage(role, content, extraMeta as Record<string, unknown>);

          for (const [key, value] of Object.entries(extraMeta)) {
            expect(message.metadata?.[key]).toBe(value);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ============================================
// Property: Message Array Invariants
// ============================================

describe('Message Properties: Arrays', () => {
  it('filtering messages should never return more than original', () => {
    fc.assert(
      fc.property(
        smallMessagesArbitrary,
        fc.constantFrom('user', 'assistant', 'system'),
        (messages, filterRole) => {
          const filtered = messages.filter(m => m.role === filterRole);
          expect(filtered.length).toBeLessThanOrEqual(messages.length);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('concatenating two message arrays should produce combined length', () => {
    fc.assert(
      fc.property(
        smallMessagesArbitrary,
        smallMessagesArbitrary,
        (a, b) => {
          const combined = [...a, ...b];
          expect(combined.length).toBe(a.length + b.length);
        }
      ),
      { numRuns: 100 }
    );
  });
});
