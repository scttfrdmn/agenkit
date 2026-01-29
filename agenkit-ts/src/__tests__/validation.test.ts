/**
 * Tests for LLM parameter validation.
 *
 * Ensures that temperature, maxTokens, and other parameters are validated
 * at construction time to provide clear errors before API calls.
 */

import { OpenAIAgent } from '../llm/openai';
import { AnthropicAgent } from '../llm/anthropic';

describe('OpenAIAgent parameter validation', () => {
  const validConfig = {
    apiKey: 'sk-test-key',
    model: 'gpt-4o',
  };

  describe('temperature validation', () => {
    it('accepts valid temperature 0.0', () => {
      expect(() => new OpenAIAgent({ ...validConfig, temperature: 0.0 })).not.toThrow();
    });

    it('accepts valid temperature 1.0', () => {
      expect(() => new OpenAIAgent({ ...validConfig, temperature: 1.0 })).not.toThrow();
    });

    it('accepts valid temperature 2.0', () => {
      expect(() => new OpenAIAgent({ ...validConfig, temperature: 2.0 })).not.toThrow();
    });

    it('rejects temperature below 0', () => {
      expect(() => new OpenAIAgent({ ...validConfig, temperature: -0.5 })).toThrow(
        'temperature must be between 0 and 2, got -0.5'
      );
    });

    it('rejects temperature above 2', () => {
      expect(() => new OpenAIAgent({ ...validConfig, temperature: 3.0 })).toThrow(
        'temperature must be between 0 and 2, got 3'
      );
    });

    it('uses default temperature when not provided', () => {
      const agent = new OpenAIAgent(validConfig);
      expect(agent).toBeDefined();
    });
  });

  describe('maxTokens validation', () => {
    it('accepts valid maxTokens 1', () => {
      expect(() => new OpenAIAgent({ ...validConfig, maxTokens: 1 })).not.toThrow();
    });

    it('accepts valid maxTokens 1000', () => {
      expect(() => new OpenAIAgent({ ...validConfig, maxTokens: 1000 })).not.toThrow();
    });

    it('accepts valid maxTokens 4096', () => {
      expect(() => new OpenAIAgent({ ...validConfig, maxTokens: 4096 })).not.toThrow();
    });

    it('rejects maxTokens 0', () => {
      expect(() => new OpenAIAgent({ ...validConfig, maxTokens: 0 })).toThrow(
        'maxTokens must be positive, got 0'
      );
    });

    it('rejects negative maxTokens', () => {
      expect(() => new OpenAIAgent({ ...validConfig, maxTokens: -10 })).toThrow(
        'maxTokens must be positive, got -10'
      );
    });

    it('allows undefined maxTokens', () => {
      expect(() => new OpenAIAgent(validConfig)).not.toThrow();
    });
  });

  describe('combined parameters', () => {
    it('accepts all valid parameters together', () => {
      expect(
        () =>
          new OpenAIAgent({
            ...validConfig,
            temperature: 0.7,
            maxTokens: 1024,
          })
      ).not.toThrow();
    });
  });
});

describe('AnthropicAgent parameter validation', () => {
  const validConfig = {
    apiKey: 'sk-ant-test-key',
    model: 'claude-sonnet-4-20250514',
  };

  describe('temperature validation', () => {
    it('accepts valid temperature 0.0', () => {
      expect(() => new AnthropicAgent({ ...validConfig, temperature: 0.0 })).not.toThrow();
    });

    it('accepts valid temperature 1.0', () => {
      expect(() => new AnthropicAgent({ ...validConfig, temperature: 1.0 })).not.toThrow();
    });

    it('accepts valid temperature 2.0', () => {
      expect(() => new AnthropicAgent({ ...validConfig, temperature: 2.0 })).not.toThrow();
    });

    it('rejects temperature below 0', () => {
      expect(() => new AnthropicAgent({ ...validConfig, temperature: -0.5 })).toThrow(
        'temperature must be between 0 and 2, got -0.5'
      );
    });

    it('rejects temperature above 2', () => {
      expect(() => new AnthropicAgent({ ...validConfig, temperature: 3.0 })).toThrow(
        'temperature must be between 0 and 2, got 3'
      );
    });

    it('uses default temperature when not provided', () => {
      const agent = new AnthropicAgent(validConfig);
      expect(agent).toBeDefined();
    });
  });

  describe('maxTokens validation', () => {
    it('accepts valid maxTokens 1', () => {
      expect(() => new AnthropicAgent({ ...validConfig, maxTokens: 1 })).not.toThrow();
    });

    it('accepts valid maxTokens 4096', () => {
      expect(() => new AnthropicAgent({ ...validConfig, maxTokens: 4096 })).not.toThrow();
    });

    it('rejects maxTokens 0', () => {
      expect(() => new AnthropicAgent({ ...validConfig, maxTokens: 0 })).toThrow(
        'maxTokens must be positive, got 0'
      );
    });

    it('rejects negative maxTokens', () => {
      expect(() => new AnthropicAgent({ ...validConfig, maxTokens: -10 })).toThrow(
        'maxTokens must be positive, got -10'
      );
    });

    it('uses default maxTokens when not provided', () => {
      const agent = new AnthropicAgent(validConfig);
      expect(agent).toBeDefined();
    });
  });

  describe('combined parameters', () => {
    it('accepts all valid parameters together', () => {
      expect(
        () =>
          new AnthropicAgent({
            ...validConfig,
            temperature: 0.7,
            maxTokens: 2048,
          })
      ).not.toThrow();
    });
  });
});

describe('Boundary value tests', () => {
  describe('temperature boundaries', () => {
    it('accepts temperature exactly 0', () => {
      expect(() => new OpenAIAgent({ apiKey: 'test', temperature: 0.0 })).not.toThrow();
    });

    it('accepts temperature exactly 2', () => {
      expect(() => new OpenAIAgent({ apiKey: 'test', temperature: 2.0 })).not.toThrow();
    });
  });

  describe('maxTokens boundaries', () => {
    it('accepts maxTokens exactly 1', () => {
      expect(() => new OpenAIAgent({ apiKey: 'test', maxTokens: 1 })).not.toThrow();
    });
  });
});
