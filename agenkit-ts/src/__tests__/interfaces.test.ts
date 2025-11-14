/**
 * Tests for core interfaces.
 */

import { createMessage, validateMessage } from '../core/interfaces';

describe('Core Interfaces', () => {
  describe('createMessage', () => {
    it('should create a message with required fields', () => {
      const message = createMessage('user', 'Hello');

      expect(message.role).toBe('user');
      expect(message.content).toBe('Hello');
      expect(message.timestamp).toBeDefined();
      expect(message.metadata).toEqual({});
    });

    it('should create a message with metadata', () => {
      const metadata = { key: 'value', count: 42 };
      const message = createMessage('assistant', 'Response', metadata);

      expect(message.metadata).toEqual(metadata);
    });

    it('should handle complex content types', () => {
      const complexContent = {
        text: 'Hello',
        data: [1, 2, 3],
        nested: { key: 'value' },
      };

      const message = createMessage('user', complexContent);

      expect(message.content).toEqual(complexContent);
    });

    it('should generate ISO 8601 timestamps', () => {
      const message = createMessage('user', 'Test');

      expect(message.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
    });
  });

  describe('validateMessage', () => {
    it('should validate valid messages', () => {
      const message = createMessage('user', 'Hello');

      expect(() => validateMessage(message)).not.toThrow();
    });

    it('should reject messages with empty role', () => {
      const message = { role: '', content: 'Hello' };

      expect(() => validateMessage(message)).toThrow('Message role must be a non-empty string');
    });

    it('should reject messages with null content', () => {
      const message = { role: 'user', content: null };

      expect(() => validateMessage(message as any)).toThrow(
        'Message content cannot be undefined or null',
      );
    });

    it('should reject messages with undefined content', () => {
      const message = { role: 'user', content: undefined };

      expect(() => validateMessage(message as any)).toThrow(
        'Message content cannot be undefined or null',
      );
    });

    it('should allow content with value 0', () => {
      const message = { role: 'user', content: 0 };

      expect(() => validateMessage(message)).not.toThrow();
    });

    it('should allow content with empty string', () => {
      const message = { role: 'user', content: '' };

      expect(() => validateMessage(message)).not.toThrow();
    });

    it('should allow content with false', () => {
      const message = { role: 'user', content: false };

      expect(() => validateMessage(message)).not.toThrow();
    });
  });
});
