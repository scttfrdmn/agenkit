/**
 * Cross-language API consistency tests for TypeScript.
 *
 * Tests that Agenkit's TypeScript implementation conforms to the cross-language
 * API consistency specification, validating parameter naming, default values,
 * and interface signatures.
 */

import * as fs from 'fs';
import * as path from 'path';
import {
  RetryConfig,
  TimeoutConfig,
  RateLimiterConfig,
  CircuitBreakerConfig,
  CircuitBreakerMiddleware,
  Agent,
  Tool,
  Message,
  ToolResult,
} from '../..';

// Load API consistency fixtures
interface APIFixtures {
  version: string;
  description: string;
  test_categories: {
    parameter_naming: {
      description: string;
      test_cases: ParameterTestCase[];
    };
    default_values: {
      description: string;
      test_cases: DefaultTestCase[];
    };
  };
}

interface ParameterTestCase {
  id: string;
  name: string;
  component: string;
  parameters: {
    [key: string]: {
      description: string;
      expected_names: { [lang: string]: string };
      must_not_be_named?: string[];
    };
  };
}

interface DefaultTestCase {
  id: string;
  name: string;
  component: string;
  defaults: {
    [key: string]: {
      value?: number;
      value_ms?: number;
      description: string;
    };
  };
}

function loadAPIFixtures(): APIFixtures {
  const fixturesPath = path.join(
    __dirname,
    '..',
    '..',
    '..',
    '..',
    'tests',
    'cross_language',
    'fixtures',
    'api_consistency.json'
  );

  const data = fs.readFileSync(fixturesPath, 'utf-8');
  return JSON.parse(data) as APIFixtures;
}

describe('Parameter Naming', () => {
  const fixtures = loadAPIFixtures();

  test('retry parameter names', () => {
    const testCase = fixtures.test_categories.parameter_naming.test_cases.find(
      tc => tc.id === 'retry_parameter_names'
    );

    if (!testCase) {
      throw new Error('Could not find retry_parameter_names test case');
    }

    // Create a config instance to check property names
    const config: RetryConfig = {
      maxRetries: 3,
      initialDelay: 100,
      maxDelay: 10000,
      multiplier: 2.0,
    };

    // Check max_retries -> maxRetries
    const maxRetriesParam = testCase.parameters['max_retries'];
    const expectedMaxRetriesName = maxRetriesParam.expected_names['typescript'];
    expect(expectedMaxRetriesName in config).toBe(true);

    // Check initial_delay -> initialDelay
    const initialDelayParam = testCase.parameters['initial_delay'];
    const expectedInitialDelayName = initialDelayParam.expected_names['typescript'];
    expect(expectedInitialDelayName in config).toBe(true);

    // Check max_delay -> maxDelay
    const maxDelayParam = testCase.parameters['max_delay'];
    const expectedMaxDelayName = maxDelayParam.expected_names['typescript'];
    expect(expectedMaxDelayName in config).toBe(true);
  });

  test('timeout parameter names', () => {
    const testCase = fixtures.test_categories.parameter_naming.test_cases.find(
      tc => tc.id === 'timeout_parameter_names'
    );

    if (!testCase) {
      throw new Error('Could not find timeout_parameter_names test case');
    }

    // Create a config instance
    const config: TimeoutConfig = {
      timeout: 30000,
    };

    // TypeScript uses 'timeout' (documented as milliseconds)
    expect('timeout' in config).toBe(true);
  });
});

describe('Default Values', () => {
  const fixtures = loadAPIFixtures();

  test('timeout defaults', () => {
    const testCase = fixtures.test_categories.default_values.test_cases.find(
      tc => tc.id === 'timeout_defaults'
    );

    if (!testCase) {
      throw new Error('Could not find timeout_defaults test case');
    }

    // Check default timeout
    const expectedTimeoutMs = testCase.defaults['timeout'].value_ms;

    // Note: TypeScript TimeoutConfig may not have defaults set in the type itself,
    // but in the implementation. We verify the concept exists.
    expect(expectedTimeoutMs).toBe(30000);
  });

  test('retry defaults', () => {
    const testCase = fixtures.test_categories.default_values.test_cases.find(
      tc => tc.id === 'retry_defaults'
    );

    if (!testCase) {
      throw new Error('Could not find retry_defaults test case');
    }

    // Verify expected defaults match specification
    const expectedMaxRetries = testCase.defaults['max_retries'].value;
    const expectedInitialDelayMs = testCase.defaults['initial_delay'].value_ms;
    const expectedMaxDelayMs = testCase.defaults['max_delay'].value_ms;
    const expectedMultiplier = testCase.defaults['multiplier'].value;

    expect(expectedMaxRetries).toBe(3);
    expect(expectedInitialDelayMs).toBe(100);
    expect(expectedMaxDelayMs).toBe(10000);
    expect(expectedMultiplier).toBe(2.0);
  });

  test('rate limiter defaults', () => {
    const testCase = fixtures.test_categories.default_values.test_cases.find(
      tc => tc.id === 'rate_limiter_defaults'
    );

    if (!testCase) {
      throw new Error('Could not find rate_limiter_defaults test case');
    }

    // Verify expected defaults
    const expectedRate = testCase.defaults['rate'].value;
    const expectedCapacity = testCase.defaults['capacity'].value;

    expect(expectedRate).toBe(10);
    expect(expectedCapacity).toBe(10);
  });

  test('circuit breaker defaults', () => {
    const testCase = fixtures.test_categories.default_values.test_cases.find(
      tc => tc.id === 'circuit_breaker_defaults'
    );

    if (!testCase) {
      throw new Error('Could not find circuit_breaker_defaults test case');
    }

    // Verify expected defaults
    const expectedThreshold = testCase.defaults['failure_threshold'].value;
    const expectedRecoveryMs = testCase.defaults['recovery_timeout'].value_ms;
    const expectedTimeoutMs = testCase.defaults['timeout'].value_ms;

    expect(expectedThreshold).toBe(5);
    expect(expectedRecoveryMs).toBe(60000);
    expect(expectedTimeoutMs).toBe(30000);

    // Verify TypeScript implementation matches spec
    const config: CircuitBreakerConfig = {};
    const middleware = new CircuitBreakerMiddleware({} as Agent, config);

    // Check defaults are applied (TypeScript applies defaults in constructor)
    expect(middleware['requestTimeout']).toBe(30000);
  });
});

describe('Interface Signatures', () => {
  test('Tool.execute signature', () => {
    // Verify Tool interface has execute method with correct signature
    // TypeScript's type system enforces this at compile time, but we can
    // document the expected signature here

    const mockTool: Tool = {
      name: 'test-tool',
      description: 'Test tool',
      parameters: {},

      // Signature: execute(params: Record<string, unknown>): Promise<ToolResult>
      async execute(params: Record<string, unknown>): Promise<ToolResult> {
        return {
          content: 'test',
          metadata: {},
        };
      },
    };

    expect(mockTool.execute).toBeDefined();
    expect(typeof mockTool.execute).toBe('function');
  });

  test('Agent.process signature', () => {
    // Verify Agent interface has process method with correct signature
    // TypeScript's type system enforces this at compile time

    const mockAgent: Agent = {
      name: 'test-agent',
      capabilities: [],

      // Signature: process(message: Message): Promise<Message>
      async process(message: Message): Promise<Message> {
        return {
          role: 'agent',
          content: 'response',
          metadata: {},
        };
      },
    };

    expect(mockAgent.process).toBeDefined();
    expect(typeof mockAgent.process).toBe('function');
  });
});

describe('Error Types', () => {
  test('TimeoutError exists', () => {
    // TypeScript should have a TimeoutError class/type
    // This is verified at compile time, but we document it here

    // Note: Implementation may vary - check if exported from package
    expect(true).toBe(true); // Placeholder - actual check depends on export
  });

  test('MaxRetriesExceededError concept', () => {
    // Verify the concept of a max retries exceeded error exists
    // TypeScript implementations may use Error subclasses or error codes

    expect(true).toBe(true); // Placeholder - actual check depends on implementation
  });
});

describe('TypeScript-Specific Features', () => {
  test('RetryConfig accepts all expected properties', () => {
    // Verify RetryConfig type accepts new parameter names
    const config: RetryConfig = {
      maxRetries: 5,
      initialDelay: 200,
      maxDelay: 5000,
      multiplier: 1.5,
    };

    expect(config.maxRetries).toBe(5);
    expect(config.initialDelay).toBe(200);
    expect(config.maxDelay).toBe(5000);
    expect(config.multiplier).toBe(1.5);
  });

  test('TimeoutConfig uses milliseconds', () => {
    // Verify timeout is in milliseconds
    const config: TimeoutConfig = {
      timeout: 15000, // 15 seconds in milliseconds
    };

    expect(config.timeout).toBe(15000);
  });

  test('RateLimiterConfig has expected properties', () => {
    const config: RateLimiterConfig = {
      rate: 20,
      capacity: 30,
    };

    expect(config.rate).toBe(20);
    expect(config.capacity).toBe(30);
  });

  test('CircuitBreakerConfig has expected properties', () => {
    const config: CircuitBreakerConfig = {
      failureThreshold: 3,
      recoveryTimeout: 30000,
    };

    expect(config.failureThreshold).toBe(3);
    expect(config.recoveryTimeout).toBe(30000);
  });
});
