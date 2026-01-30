/**
 * Cross-language message serialization tests for TypeScript
 *
 * Validates that Agenkit messages serialize/deserialize consistently
 * with the canonical JSON schema across all language implementations.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';
import Ajv from 'ajv';
import type { ValidateFunction } from 'ajv';
import { createMessage, validateMessage as validateMessageCore } from '../../src/core/interfaces.js';
import type { Message } from '../../src/core/interfaces.js';

interface MessageFixtures {
  version: string;
  description: string;
  test_cases: MessageTestCase[];
}

interface MessageTestCase {
  id: string;
  name: string;
  message: {
    role: string;
    content: string | Record<string, unknown>;
    metadata?: Record<string, unknown>;
    timestamp?: string;
  };
  validation: Record<string, unknown>;
}

describe('Cross-Language Message Serialization', () => {
  let fixtures: MessageFixtures;
  let messageSchema: Record<string, unknown>;
  let validateMessage: ValidateFunction;

  beforeAll(() => {
    // Load fixtures
    const fixturesPath = join(__dirname, '../../../tests/cross_language/fixtures/messages.json');
    fixtures = JSON.parse(readFileSync(fixturesPath, 'utf-8'));

    // Load schema
    const schemaPath = join(__dirname, '../../../tests/cross_language/schemas/message.schema.json');
    messageSchema = JSON.parse(readFileSync(schemaPath, 'utf-8'));

    // Create validator
    const ajv = new Ajv();
    validateMessage = ajv.compile(messageSchema);
  });

  describe('Fixtures and Schema', () => {
    it('should load fixtures correctly', () => {
      expect(fixtures.version).toBe('1.0');
      expect(fixtures.test_cases.length).toBeGreaterThan(0);
    });

    it('should validate all fixtures against schema', () => {
      for (const testCase of fixtures.test_cases) {
        const valid = validateMessage(testCase.message);
        if (!valid) {
          console.error(`Validation errors for ${testCase.id}:`, validateMessage.errors);
        }
        expect(valid).toBe(true);
      }
    });
  });

  describe('Message Serialization', () => {
    it('should handle simple user message', () => {
      const testCase = fixtures.test_cases.find(tc => tc.id === 'simple_user_message')!;
      expect(testCase).toBeDefined();

      // Create message from fixture
      const msg = createMessage({
        role: testCase.message.role,
        content: testCase.message.content as string,
        metadata: testCase.message.metadata || {},
      });

      // Validate properties
      expect(msg.role).toBe('user');
      expect(msg.content).toBe('Hello, agent!');
      expect(msg.metadata).toBeDefined();

      // Validate against schema (message is already a plain object)
      expect(validateMessage(msg)).toBe(true);

      // Verify key properties match
      expect(msg.role).toBe(testCase.message.role);
      expect(msg.content).toBe(testCase.message.content);
    });

    it('should handle assistant message with metadata', () => {
      const testCase = fixtures.test_cases.find(tc => tc.id === 'assistant_message_with_metadata')!;
      expect(testCase).toBeDefined();

      const msg = createMessage({
        role: testCase.message.role,
        content: testCase.message.content as string,
        metadata: testCase.message.metadata,
      });

      // Validate
      expect(msg.role).toBe('assistant');
      expect(msg.content).toBe('I can help you with that!');
      expect(Object.keys(msg.metadata || {}).length).toBe(3);
      expect(msg.metadata?.model).toBeDefined();
      expect(msg.metadata?.temperature).toBeDefined();
      expect(msg.metadata?.tokens).toBeDefined();

      // Verify metadata keys
      const validation = testCase.validation as { metadata_keys: string[] };
      const metadataKeys = new Set(Object.keys(msg.metadata || {}));
      for (const key of validation.metadata_keys) {
        expect(metadataKeys.has(key)).toBe(true);
      }

      // Validate against schema
      expect(validateMessage(msg)).toBe(true);
    });

    it('should handle system message', () => {
      const testCase = fixtures.test_cases.find(tc => tc.id === 'system_message')!;
      expect(testCase).toBeDefined();

      const msg = createMessage({
        role: testCase.message.role,
        content: testCase.message.content as string,
      });

      expect(msg.role).toBe('system');
      expect(msg.content).toContain('helpful assistant');

      expect(validateMessage(msg)).toBe(true);
    });

    it('should handle tool message with structured content', () => {
      const testCase = fixtures.test_cases.find(tc => tc.id === 'tool_message_structured')!;
      expect(testCase).toBeDefined();

      const msg = createMessage({
        role: testCase.message.role,
        content: testCase.message.content, // Can be object in TypeScript
        metadata: testCase.message.metadata,
      });

      // Validate structured content
      expect(msg.role).toBe('tool');
      expect(typeof msg.content).toBe('object');
      const contentObj = msg.content as Record<string, unknown>;
      expect(contentObj.tool_name).toBe('calculator');
      expect(contentObj.result).toBe(5);
      expect(contentObj.success).toBe(true);

      // Verify content keys
      const validation = testCase.validation as { content_keys: string[] };
      const contentKeys = new Set(Object.keys(contentObj));
      for (const key of validation.content_keys) {
        expect(contentKeys.has(key)).toBe(true);
      }

      // Serialize and validate
      expect(validateMessage(msg)).toBe(true);
    });

    it('should handle agent message', () => {
      const testCase = fixtures.test_cases.find(tc => tc.id === 'agent_message')!;
      expect(testCase).toBeDefined();

      const msg = createMessage({
        role: testCase.message.role,
        content: testCase.message.content as string,
        metadata: testCase.message.metadata,
      });

      expect(msg.role).toBe('agent');
      expect(msg.content).toContain('reasoning steps');
      expect(msg.metadata?.technique).toBe('chain_of_thought');

      expect(validateMessage(msg)).toBe(true);
    });

    it('should handle empty content', () => {
      const testCase = fixtures.test_cases.find(tc => tc.id === 'empty_content')!;
      expect(testCase).toBeDefined();

      const msg = createMessage({
        role: testCase.message.role,
        content: testCase.message.content as string,
      });

      expect(msg.role).toBe('assistant');
      expect(msg.content).toBe('');
      expect((msg.content as string).length).toBe(0);

      expect(validateMessage(msg)).toBe(true);
    });

    it('should handle large content', () => {
      const testCase = fixtures.test_cases.find(tc => tc.id === 'large_content')!;
      expect(testCase).toBeDefined();

      const msg = createMessage({
        role: testCase.message.role,
        content: testCase.message.content as string,
        metadata: testCase.message.metadata,
      });

      const validation = testCase.validation as { min_content_length: number };
      expect((msg.content as string).length).toBeGreaterThanOrEqual(validation.min_content_length);
      expect(msg.content).toContain('Lorem ipsum');

      expect(validateMessage(msg)).toBe(true);
    });

    it('should handle Unicode content', () => {
      const testCase = fixtures.test_cases.find(tc => tc.id === 'unicode_content')!;
      expect(testCase).toBeDefined();

      const msg = createMessage({
        role: testCase.message.role,
        content: testCase.message.content as string,
        metadata: testCase.message.metadata,
      });

      // Verify Unicode characters preserved
      const validation = testCase.validation as { contains: string[] };
      for (const substring of validation.contains) {
        expect(msg.content).toContain(substring);
      }

      expect(msg.content).toContain('世界');
      expect(msg.content).toContain('🌍');
      expect(msg.content).toContain('мир');

      expect(validateMessage(msg)).toBe(true);
    });

    it('should handle nested metadata', () => {
      const testCase = fixtures.test_cases.find(tc => tc.id === 'nested_metadata')!;
      expect(testCase).toBeDefined();

      const msg = createMessage({
        role: testCase.message.role,
        content: testCase.message.content as string,
        metadata: testCase.message.metadata,
      });

      // Verify nested structure
      expect(msg.metadata?.analysis).toBeDefined();
      expect(typeof msg.metadata?.analysis).toBe('object');
      const analysis = msg.metadata?.analysis as Record<string, unknown>;
      expect(analysis.sentiment).toBe('positive');

      expect(msg.metadata?.processing).toBeDefined();
      expect(typeof msg.metadata?.processing).toBe('object');

      expect(msg.metadata?.tags).toBeDefined();
      expect(Array.isArray(msg.metadata?.tags)).toBe(true);

      expect(validateMessage(msg)).toBe(true);
    });

    it('should handle numeric metadata', () => {
      const testCase = fixtures.test_cases.find(tc => tc.id === 'numeric_metadata')!;
      expect(testCase).toBeDefined();

      const msg = createMessage({
        role: testCase.message.role,
        content: testCase.message.content as string,
        metadata: testCase.message.metadata,
      });

      // Verify numeric types preserved
      expect(typeof msg.metadata?.count).toBe('number');
      expect(msg.metadata?.count).toBe(42);

      expect(typeof msg.metadata?.score).toBe('number');
      expect(Math.abs((msg.metadata?.score as number) - 3.14159)).toBeLessThan(0.0001);

      expect(typeof msg.metadata?.is_final).toBe('boolean');
      expect(msg.metadata?.is_final).toBe(true);

      expect(msg.metadata?.optional_value).toBeNull();

      expect(validateMessage(msg)).toBe(true);
    });

    it('should roundtrip all fixtures correctly', () => {
      for (const testCase of fixtures.test_cases) {
        // Create message
        const msg = createMessage({
          role: testCase.message.role,
          content: testCase.message.content,
          metadata: testCase.message.metadata || {},
        });

        // Validate against schema (message is already a plain object)
        const valid = validateMessage(msg);
        if (!valid) {
          console.error(`Validation failed for ${testCase.id}:`, validateMessage.errors);
        }
        expect(valid).toBe(true);

        // Verify core properties match
        expect(msg.role).toBe(testCase.message.role);
        // Content may be transformed but should be present
        expect(msg.content).toBeDefined();
      }
    });
  });

  describe('Schema Compliance', () => {
    it('should reject invalid roles', () => {
      const msg = createMessage({
        role: 'invalid_role',
        content: 'test',
      });
      // TypeScript interface doesn't validate roles at creation time
      // Schema validation will catch this
      expect(validateMessage(msg)).toBe(false);
    });

    it('should handle metadata structure', () => {
      const msg = createMessage({
        role: 'user',
        content: 'test',
        metadata: { key1: 'value1', key2: 123 },
      });

      expect(validateMessage(msg)).toBe(true);
    });

    it('should verify schema version', () => {
      expect(messageSchema.$schema).toBe('http://json-schema.org/draft-07/schema#');
      expect((messageSchema.$id as string)).toContain('message.json');
    });
  });
});
