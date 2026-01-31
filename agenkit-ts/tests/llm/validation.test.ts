/**
 * Tests for LLM parameter validation
 */

import { describe, it, expect } from 'vitest';
import { validateLLMParams } from '../../src/llm/validation';

describe('LLM Parameter Validation', () => {
  describe('temperature validation', () => {
    it('should accept valid temperature values', () => {
      expect(() => validateLLMParams({ temperature: 0.0 })).not.toThrow();
      expect(() => validateLLMParams({ temperature: 1.0 })).not.toThrow();
      expect(() => validateLLMParams({ temperature: 2.0 })).not.toThrow();
    });

    it('should reject temperature below 0', () => {
      expect(() => validateLLMParams({ temperature: -0.1 })).toThrow(
        'temperature must be between 0 and 2, got -0.1'
      );
    });

    it('should reject temperature above 2', () => {
      expect(() => validateLLMParams({ temperature: 2.1 })).toThrow(
        'temperature must be between 0 and 2, got 2.1'
      );
    });

    it('should reject non-number temperature', () => {
      expect(() => validateLLMParams({ temperature: '1.0' as any })).toThrow(
        'temperature must be between 0 and 2, got 1.0'
      );
    });
  });

  describe('max_tokens validation', () => {
    it('should accept valid max_tokens values', () => {
      expect(() => validateLLMParams({ max_tokens: 1 })).not.toThrow();
      expect(() => validateLLMParams({ max_tokens: 100 })).not.toThrow();
      expect(() => validateLLMParams({ max_tokens: 4096 })).not.toThrow();
    });

    it('should reject max_tokens of 0', () => {
      expect(() => validateLLMParams({ max_tokens: 0 })).toThrow(
        'max_tokens must be positive, got 0'
      );
    });

    it('should reject negative max_tokens', () => {
      expect(() => validateLLMParams({ max_tokens: -100 })).toThrow(
        'max_tokens must be positive, got -100'
      );
    });

    it('should reject non-number max_tokens', () => {
      expect(() => validateLLMParams({ max_tokens: '100' as any })).toThrow(
        'max_tokens must be positive, got 100'
      );
    });
  });

  describe('top_p validation', () => {
    it('should accept valid top_p values', () => {
      expect(() => validateLLMParams({ top_p: 0.0 })).not.toThrow();
      expect(() => validateLLMParams({ top_p: 0.5 })).not.toThrow();
      expect(() => validateLLMParams({ top_p: 1.0 })).not.toThrow();
    });

    it('should reject top_p below 0', () => {
      expect(() => validateLLMParams({ top_p: -0.1 })).toThrow(
        'top_p must be between 0 and 1, got -0.1'
      );
    });

    it('should reject top_p above 1', () => {
      expect(() => validateLLMParams({ top_p: 1.1 })).toThrow(
        'top_p must be between 0 and 1, got 1.1'
      );
    });
  });

  describe('frequency_penalty validation', () => {
    it('should accept valid frequency_penalty values', () => {
      expect(() => validateLLMParams({ frequency_penalty: -2.0 })).not.toThrow();
      expect(() => validateLLMParams({ frequency_penalty: 0.0 })).not.toThrow();
      expect(() => validateLLMParams({ frequency_penalty: 2.0 })).not.toThrow();
    });

    it('should reject frequency_penalty below -2', () => {
      expect(() => validateLLMParams({ frequency_penalty: -2.1 })).toThrow(
        'frequency_penalty must be between -2 and 2, got -2.1'
      );
    });

    it('should reject frequency_penalty above 2', () => {
      expect(() => validateLLMParams({ frequency_penalty: 2.5 })).toThrow(
        'frequency_penalty must be between -2 and 2, got 2.5'
      );
    });
  });

  describe('presence_penalty validation', () => {
    it('should accept valid presence_penalty values', () => {
      expect(() => validateLLMParams({ presence_penalty: -2.0 })).not.toThrow();
      expect(() => validateLLMParams({ presence_penalty: 0.0 })).not.toThrow();
      expect(() => validateLLMParams({ presence_penalty: 2.0 })).not.toThrow();
    });

    it('should reject presence_penalty below -2', () => {
      expect(() => validateLLMParams({ presence_penalty: -2.1 })).toThrow(
        'presence_penalty must be between -2 and 2, got -2.1'
      );
    });

    it('should reject presence_penalty above 2', () => {
      expect(() => validateLLMParams({ presence_penalty: 2.5 })).toThrow(
        'presence_penalty must be between -2 and 2, got 2.5'
      );
    });
  });

  describe('multiple parameters', () => {
    it('should validate all parameters together', () => {
      expect(() =>
        validateLLMParams({
          temperature: 0.7,
          max_tokens: 100,
          top_p: 0.9,
          frequency_penalty: 0.5,
          presence_penalty: -0.5,
        })
      ).not.toThrow();
    });

    it('should fail if any parameter is invalid', () => {
      expect(() =>
        validateLLMParams({
          temperature: 3.0, // Invalid
          max_tokens: 100,
          top_p: 0.9,
        })
      ).toThrow('temperature must be between 0 and 2');
    });
  });

  describe('undefined parameters', () => {
    it('should allow undefined parameters', () => {
      expect(() => validateLLMParams({})).not.toThrow();
      expect(() => validateLLMParams({ temperature: undefined })).not.toThrow();
      expect(() => validateLLMParams({ max_tokens: undefined })).not.toThrow();
    });
  });

  describe('boundary values', () => {
    it('should accept boundary values for temperature', () => {
      expect(() => validateLLMParams({ temperature: 0.0 })).not.toThrow();
      expect(() => validateLLMParams({ temperature: 2.0 })).not.toThrow();
    });

    it('should accept boundary values for top_p', () => {
      expect(() => validateLLMParams({ top_p: 0.0 })).not.toThrow();
      expect(() => validateLLMParams({ top_p: 1.0 })).not.toThrow();
    });

    it('should accept boundary values for penalties', () => {
      expect(() => validateLLMParams({ frequency_penalty: -2.0 })).not.toThrow();
      expect(() => validateLLMParams({ frequency_penalty: 2.0 })).not.toThrow();
      expect(() => validateLLMParams({ presence_penalty: -2.0 })).not.toThrow();
      expect(() => validateLLMParams({ presence_penalty: 2.0 })).not.toThrow();
    });

    it('should accept minimum max_tokens', () => {
      expect(() => validateLLMParams({ max_tokens: 1 })).not.toThrow();
    });
  });
});
