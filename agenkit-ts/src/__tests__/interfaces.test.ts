/**
 * Tests for core interfaces.
 */

import {
  createMessage,
  validateMessage,
  createValidatedMessage,
} from '../core/interfaces';

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

    // Size validation tests
    describe('role validation', () => {
      it('should reject role longer than 20 characters', () => {
        const message = createMessage('a'.repeat(21), 'Hello');

        expect(() => validateMessage(message)).toThrow(
          'Message role exceeds maximum length of 20 characters',
        );
      });

      it('should reject invalid role values', () => {
        const message = createMessage('invalid_role', 'Hello');

        expect(() => validateMessage(message)).toThrow(
          'Invalid message role: invalid_role',
        );
      });

      it('should accept all valid role values', () => {
        const validRoles = ['user', 'assistant', 'system', 'tool', 'agent'];

        for (const role of validRoles) {
          const message = createMessage(role, 'Hello');
          expect(() => validateMessage(message)).not.toThrow();
        }
      });
    });

    describe('content size validation', () => {
      it('should accept content under 16MB', () => {
        const content = 'a'.repeat(1024 * 1024); // 1MB
        const message = createMessage('user', content);

        expect(() => validateMessage(message)).not.toThrow();
      });

      it('should reject content over 16MB', () => {
        const content = 'a'.repeat(17 * 1024 * 1024); // 17MB
        const message = createMessage('user', content);

        expect(() => validateMessage(message)).toThrow(
          'Message content exceeds maximum size of',
        );
      });

      it('should validate structured content size', () => {
        // Create a large structured object
        const largeArray = new Array(1000000).fill({ key: 'a'.repeat(20) });
        const message = createMessage('user', largeArray);

        expect(() => validateMessage(message)).toThrow(
          'Message content exceeds maximum size of',
        );
      });
    });

    describe('metadata validation', () => {
      it('should accept metadata with under 100 keys', () => {
        const metadata: Record<string, unknown> = {};
        for (let i = 0; i < 99; i++) {
          metadata[`key${i}`] = 'value';
        }
        const message = createMessage('user', 'Hello', metadata);

        expect(() => validateMessage(message)).not.toThrow();
      });

      it('should reject metadata with over 100 keys', () => {
        const metadata: Record<string, unknown> = {};
        for (let i = 0; i < 101; i++) {
          metadata[`key${i}`] = 'value';
        }
        const message = createMessage('user', 'Hello', metadata);

        expect(() => validateMessage(message)).toThrow(
          'Message metadata exceeds maximum of 100 keys',
        );
      });

      it('should reject metadata keys longer than 50 characters', () => {
        const metadata = { ['a'.repeat(51)]: 'value' };
        const message = createMessage('user', 'Hello', metadata);

        expect(() => validateMessage(message)).toThrow(
          "Metadata key 'aaaaaaaaaaaaaaaaaaaa...' exceeds maximum length of 50 characters",
        );
      });

      it('should accept metadata keys exactly 50 characters', () => {
        const metadata = { ['a'.repeat(50)]: 'value' };
        const message = createMessage('user', 'Hello', metadata);

        expect(() => validateMessage(message)).not.toThrow();
      });

      it('should reject metadata values over 16MB', () => {
        const largeValue = 'a'.repeat(17 * 1024 * 1024); // 17MB
        const metadata = { key: largeValue };
        const message = createMessage('user', 'Hello', metadata);

        expect(() => validateMessage(message)).toThrow(
          "Metadata value for key 'key' exceeds maximum size of",
        );
      });

      it('should accept metadata values under 16MB', () => {
        const largeValue = 'a'.repeat(1024 * 1024); // 1MB
        const metadata = { key: largeValue };
        const message = createMessage('user', 'Hello', metadata);

        expect(() => validateMessage(message)).not.toThrow();
      });

      it('should validate structured metadata values', () => {
        const largeArray = new Array(1000000).fill({ key: 'a'.repeat(20) });
        const metadata = { data: largeArray };
        const message = createMessage('user', 'Hello', metadata);

        expect(() => validateMessage(message)).toThrow(
          "Metadata value for key 'data' exceeds maximum size of",
        );
      });
    });
  });

  describe('createValidatedMessage', () => {
    it('should create and validate a message', () => {
      const message = createValidatedMessage('user', 'Hello', { key: 'value' });

      expect(message.role).toBe('user');
      expect(message.content).toBe('Hello');
      expect(message.metadata).toEqual({ key: 'value' });
    });

    it('should throw on invalid message', () => {
      expect(() => createValidatedMessage('invalid_role', 'Hello')).toThrow(
        'Invalid message role',
      );
    });

    it('should throw on oversized content', () => {
      const largeContent = 'a'.repeat(17 * 1024 * 1024); // 17MB

      expect(() => createValidatedMessage('user', largeContent)).toThrow(
        'Message content exceeds maximum size of',
      );
    });
  });
});
