/**
 * Pattern-specific benchmarks for evaluating agent patterns.
 *
 * This module provides a comprehensive benchmark framework for evaluating all 18 core
 * agent patterns. It leverages the existing cross-language YAML test specifications
 * to automatically generate standardized test suites with validators, metrics, and
 * performance tracking.
 *
 * Key Features:
 * - Automatic conversion of YAML test specs to executable benchmarks
 * - Pattern-specific test cases with validators
 * - Performance measurement (latency, throughput)
 * - Behavioral validation (turns, tool calls, metadata)
 * - Support for all 18 core patterns
 *
 * Classes:
 * - PatternBenchmark: Pattern-specific benchmark extending base Benchmark
 * - YAMLBenchmarkLoader: Loads benchmarks from YAML specification files
 * - PatternBenchmarkSuite: Collection of pattern benchmarks with execution support
 *
 * Usage Example:
 * ```typescript
 * import { PatternBenchmarkSuite } from './pattern-benchmarks';
 * import { resolve } from 'path';
 *
 * // Load all pattern benchmarks from YAML specs
 * const specsDir = resolve(__dirname, '../../../tests/cross_language/specs');
 * const suite = await PatternBenchmarkSuite.fromYamlSpecs(specsDir);
 *
 * // Get specific pattern benchmark
 * const reflection = suite.getBenchmark('reflection');
 * console.log(`Benchmark: ${reflection?.name}`);
 * console.log(`Test cases: ${(await reflection?.generateTestCases())?.length}`);
 *
 * // Run benchmark on agent
 * const results = await suite.runBenchmark(reflection!, (config) => {
 *   return new MyReflectionAgent(config);
 * });
 * console.log(`Pass rate: ${results.summary.passed}/${results.summary.total}`);
 * ```
 *
 * Pattern Coverage:
 * The framework supports benchmarks for all 18 core patterns:
 * 1. Reflection - Iterative self-improvement
 * 2. ReAct - Reasoning and acting with tools
 * 3. Sequential - Pipeline execution
 * 4. Parallel - Concurrent execution
 * 5. Router - Dynamic routing
 * 6. Planning - Task decomposition
 * 7. Conversational - Context-aware dialogue
 * 8. Task - Lifecycle management
 * 9. Multiagent - Agent collaboration
 * 10. Autonomous - Goal-driven behavior
 * 11. Memory Hierarchy - Multi-tier memory
 * 12. Agents-as-Tools - Agent delegation
 * 13. Fallback - Error recovery
 * 14. Collaborative - Consensus building
 * 15. Human-in-Loop - Approval workflows
 * 16. Supervisor - Task distribution
 * 17. Orchestration - Complex workflows
 * 18. Reasoning-with-Tools - Interleaved reasoning
 */

import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import type { Agent, Message } from '../index';
import type { Benchmark } from './benchmarks';

/**
 * Test case for pattern benchmarks (extends base TestCase with Message validator).
 */
export interface PatternTestCase {
  /** Input to provide to the agent */
  input: string;
  /** Expected output validator (takes Message, not string) */
  expected: string | ((msg: Message) => boolean);
  /** Additional metadata about the test case */
  metadata?: Record<string, unknown>;
  /** Tags for categorizing test cases */
  tags?: string[];
}

/**
 * Pattern-specific benchmark for agent patterns.
 *
 * Provides pattern-specific validation and performance measurement.
 * Uses PatternTestCase with Message validators instead of string validators.
 */
export class PatternBenchmark {
  private _patternName: string;
  private _description: string;
  private _testCases: PatternTestCase[];

  /**
   * Create a new pattern benchmark.
   *
   * @param patternName - Name of the pattern (e.g., "reflection", "sequential")
   * @param description - Human-readable description
   * @param testCases - Pre-generated test cases for this pattern
   */
  constructor(patternName: string, description: string, testCases: PatternTestCase[]) {
    this._patternName = patternName;
    this._description = description;
    this._testCases = testCases;
  }

  /** Pattern benchmark name */
  get name(): string {
    return `${this._patternName}_benchmark`;
  }

  /** Pattern benchmark description */
  get description(): string {
    return this._description;
  }

  /** Get pattern name */
  get patternName(): string {
    return this._patternName;
  }

  /**
   * Generate test cases for this pattern.
   *
   * @returns Promise resolving to list of test cases
   */
  async generateTestCases(): Promise<PatternTestCase[]> {
    return this._testCases;
  }
}

/**
 * Expected message specification from YAML.
 */
interface ExpectedMessage {
  role?: string;
  content_contains?: string[];
  metadata?: Record<string, unknown>;
}

/**
 * Expected behavior specification from YAML.
 */
interface ExpectedBehavior {
  min_turns?: number;
  max_turns?: number;
  tool_calls?: string[];
}

/**
 * YAML test scenario structure.
 */
interface YAMLScenario {
  id: string;
  name: string;
  description?: string;
  input: {
    message: {
      content: string;
    };
    config?: Record<string, unknown>;
  };
  expected_output: {
    message: ExpectedMessage;
    behavior?: ExpectedBehavior;
  };
}

/**
 * YAML specification structure.
 */
interface YAMLSpec {
  pattern: {
    name: string;
    description: string;
  };
  test_scenarios: YAMLScenario[];
}

/**
 * Load pattern benchmarks from YAML specifications.
 *
 * Converts YAML test scenarios into Benchmark objects compatible with
 * the evaluation framework.
 */
export class YAMLBenchmarkLoader {
  private specsDir: string;

  /**
   * Initialize YAML benchmark loader.
   *
   * @param specsDir - Directory containing YAML specification files
   * @throws Error if specs directory not found
   */
  constructor(specsDir: string) {
    this.specsDir = specsDir;
    if (!fs.existsSync(this.specsDir)) {
      throw new Error(`Specs directory not found: ${this.specsDir}`);
    }
  }

  /**
   * Load benchmark for a specific pattern.
   *
   * @param patternName - Pattern name (e.g., "reflection", "sequential")
   * @returns PatternBenchmark loaded from YAML specification
   * @throws Error if YAML spec file not found or invalid
   */
  loadPatternBenchmark(patternName: string): PatternBenchmark {
    // Find YAML file
    const yamlFile = path.join(this.specsDir, `${patternName}.yaml`);
    if (!fs.existsSync(yamlFile)) {
      throw new Error(`YAML spec not found: ${yamlFile}`);
    }

    // Load YAML
    const content = fs.readFileSync(yamlFile, 'utf8');
    const spec = yaml.load(content) as YAMLSpec;

    // Extract pattern info
    const patternInfo = spec.pattern || { name: '', description: '' };
    const patternDisplayName = patternInfo.name || patternName;
    const patternDescription =
      patternInfo.description || `Benchmark for ${patternDisplayName} pattern`;

    // Convert scenarios to test cases
    const testCases: PatternTestCase[] = [];
    for (const scenario of spec.test_scenarios || []) {
      const testCase = this.scenarioToTestCase(scenario, patternName);
      testCases.push(testCase);
    }

    return new PatternBenchmark(patternName, patternDescription, testCases);
  }

  /**
   * Load benchmarks for all patterns in specs directory.
   *
   * @returns Array of all pattern benchmarks
   */
  loadAllPatternBenchmarks(): PatternBenchmark[] {
    const benchmarks: PatternBenchmark[] = [];

    // Find all YAML files
    const files = fs.readdirSync(this.specsDir);
    for (const file of files) {
      if (file.endsWith('.yaml')) {
        const patternName = file.replace('.yaml', '');
        try {
          const benchmark = this.loadPatternBenchmark(patternName);
          benchmarks.push(benchmark);
        } catch (e) {
          console.warn(`Warning: Failed to load benchmark for ${patternName}:`, e);
        }
      }
    }

    return benchmarks;
  }

  /**
   * Convert YAML test scenario to PatternTestCase.
   *
   * @param scenario - Scenario dictionary from YAML
   * @param patternName - Name of the pattern
   * @returns PatternTestCase object
   */
  private scenarioToTestCase(scenario: YAMLScenario, patternName: string): PatternTestCase {
    const scenarioId = scenario.id || 'unknown';
    const scenarioName = scenario.name || scenarioId;

    // Extract input
    const inputData = scenario.input || {};
    const inputMessage = inputData.message || {};
    const inputContent = inputMessage.content || '';

    // Extract expected output
    const expectedOutput = scenario.expected_output || {};
    const expectedMessage = expectedOutput.message || {};

    // Create validation function from expected output
    const expected = this.createValidator(expectedMessage, expectedOutput.behavior || {});

    // Build metadata
    const metadata: Record<string, unknown> = {
      scenario_id: scenarioId,
      scenario_name: scenarioName,
      pattern: patternName,
      config: inputData.config || {},
    };

    // Extract behavior expectations
    const behavior = expectedOutput.behavior || {};
    if (Object.keys(behavior).length > 0) {
      metadata.expected_behavior = behavior;
    }

    // Extract tags
    const tags = [patternName, 'yaml_generated'];
    if (scenario.description) {
      // Extract complexity tags
      const description = scenario.description.toLowerCase();
      if (description.includes('basic') || description.includes('simple')) {
        tags.push('basic');
      } else if (description.includes('complex') || description.includes('advanced')) {
        tags.push('complex');
      }
    }

    return {
      input: inputContent,
      expected,
      metadata,
      tags,
    };
  }

  /**
   * Create validation function from expected output specification.
   *
   * @param expectedMessage - Expected message properties
   * @param expectedBehavior - Expected behavioral properties
   * @returns Validation function that checks if a Message meets expectations
   */
  private createValidator(
    expectedMessage: ExpectedMessage,
    expectedBehavior: ExpectedBehavior
  ): (msg: Message) => boolean {
    return (msg: Message): boolean => {
      // Check role
      if (expectedMessage.role) {
        if (msg.role !== expectedMessage.role) {
          return false;
        }
      }

      // Check content contains
      if (expectedMessage.content_contains) {
        const content = String(msg.content).toLowerCase();
        for (const substring of expectedMessage.content_contains) {
          if (!content.includes(substring.toLowerCase())) {
            return false;
          }
        }
      }

      // Check metadata
      if (expectedMessage.metadata) {
        for (const [key, expectedValue] of Object.entries(expectedMessage.metadata)) {
          const actualValue = msg.metadata?.[key];

          // For numeric values, check minimum
          if (typeof expectedValue === 'number') {
            if (actualValue === undefined || (actualValue as number) < expectedValue) {
              return false;
            }
          }
          // For boolean values, check exact match
          else if (typeof expectedValue === 'boolean') {
            if (actualValue !== expectedValue) {
              return false;
            }
          }
        }
      }

      // Check behavioral properties (stored in metadata by harnesses)
      if (expectedBehavior) {
        // Min turns
        if (expectedBehavior.min_turns !== undefined) {
          const turns = (msg.metadata?.turns as number) || 0;
          if (turns < expectedBehavior.min_turns) {
            return false;
          }
        }

        // Max turns
        if (expectedBehavior.max_turns !== undefined) {
          const turns = (msg.metadata?.turns as number) || 0;
          if (turns > expectedBehavior.max_turns) {
            return false;
          }
        }

        // Tool calls
        if (expectedBehavior.tool_calls) {
          const actualTools = (msg.metadata?.tool_calls as string[]) || [];
          for (const expectedTool of expectedBehavior.tool_calls) {
            if (!actualTools.includes(expectedTool)) {
              return false;
            }
          }
        }
      }

      return true;
    };
  }
}

/**
 * Test case result from benchmark execution.
 */
export interface TestCaseResult {
  scenario_id: string;
  passed: boolean;
  time_ms: number;
  output_length?: number;
  error?: string;
}

/**
 * Benchmark execution results.
 */
export interface BenchmarkResult {
  pattern: string;
  test_cases: TestCaseResult[];
  summary: {
    total: number;
    passed: number;
    failed: number;
    total_time_ms: number;
  };
}

/**
 * Results from running all benchmarks.
 */
export interface SuiteResult {
  benchmarks: BenchmarkResult[];
  summary: {
    total_patterns: number;
    total_test_cases: number;
    total_passed: number;
    total_failed: number;
    total_time_ms: number;
  };
}

/**
 * Suite of pattern benchmarks for comprehensive evaluation.
 *
 * Provides convenience methods for running benchmarks on all patterns
 * or specific subsets.
 */
export class PatternBenchmarkSuite {
  private benchmarks: PatternBenchmark[];

  /**
   * Initialize pattern benchmark suite.
   *
   * @param benchmarks - List of pattern benchmarks
   */
  constructor(benchmarks: PatternBenchmark[] = []) {
    this.benchmarks = benchmarks;
  }

  /**
   * Create suite from YAML specifications directory.
   *
   * @param specsDir - Directory containing YAML spec files
   * @returns PatternBenchmarkSuite with all patterns loaded
   */
  static fromYamlSpecs(specsDir: string): PatternBenchmarkSuite {
    const loader = new YAMLBenchmarkLoader(specsDir);
    const benchmarks = loader.loadAllPatternBenchmarks();
    return new PatternBenchmarkSuite(benchmarks);
  }

  /**
   * Create suite with standard pattern benchmarks.
   *
   * Loads from the default specs location (tests/cross_language/specs).
   *
   * @returns Suite with all standard patterns
   */
  static standardPatterns(): PatternBenchmarkSuite {
    // Default specs location
    const specsDir = path.resolve(__dirname, '../../../../tests/cross_language/specs');
    if (fs.existsSync(specsDir)) {
      return PatternBenchmarkSuite.fromYamlSpecs(specsDir);
    }
    return new PatternBenchmarkSuite([]);
  }

  /**
   * Get benchmark for specific pattern.
   *
   * @param patternName - Name of the pattern
   * @returns PatternBenchmark if found, undefined otherwise
   */
  getBenchmark(patternName: string): PatternBenchmark | undefined {
    return this.benchmarks.find((b) => b.patternName === patternName);
  }

  /**
   * Get all benchmarks in the suite.
   *
   * @returns Array of all pattern benchmarks
   */
  getAllBenchmarks(): PatternBenchmark[] {
    return this.benchmarks;
  }

  /**
   * Get benchmarks that have test cases with specific tag.
   *
   * @param tag - Tag to filter by (e.g., "basic", "complex")
   * @returns Array of benchmarks containing the tag
   */
  getBenchmarksByTag(tag: string): PatternBenchmark[] {
    const matching: PatternBenchmark[] = [];
    for (const benchmark of this.benchmarks) {
      for (const testCase of benchmark['_testCases']) {
        if (testCase.tags?.includes(tag)) {
          matching.push(benchmark);
          break;
        }
      }
    }
    return matching;
  }

  /**
   * Run a benchmark and collect results.
   *
   * @param benchmark - Benchmark to run
   * @param agentFactory - Function that creates agent from config
   * @returns Promise resolving to benchmark results
   */
  async runBenchmark(
    benchmark: PatternBenchmark,
    agentFactory: (config: Record<string, unknown>) => Agent
  ): Promise<BenchmarkResult> {
    const results: BenchmarkResult = {
      pattern: benchmark.patternName,
      test_cases: [],
      summary: {
        total: 0,
        passed: 0,
        failed: 0,
        total_time_ms: 0,
      },
    };

    const testCases = await benchmark.generateTestCases();

    for (const testCase of testCases) {
      // Create agent with config from test case
      const config = (testCase.metadata?.config as Record<string, unknown>) || {};
      const agent = agentFactory(config);

      // Run test case
      const startTime = performance.now();

      try {
        // Create input message
        const inputMsg: Message = {
          role: 'user',
          content: testCase.input,
          metadata: {},
        };

        // Process with agent
        const outputMsg = await agent.process(inputMsg);

        // Measure time
        const elapsedMs = performance.now() - startTime;

        // Validate output
        let passed: boolean;
        if (typeof testCase.expected === 'function') {
          passed = testCase.expected(outputMsg);
        } else {
          passed = String(outputMsg.content) === String(testCase.expected);
        }

        results.test_cases.push({
          scenario_id: (testCase.metadata?.scenario_id as string) || 'unknown',
          passed,
          time_ms: elapsedMs,
          output_length: String(outputMsg.content).length,
        });

        if (passed) {
          results.summary.passed += 1;
        } else {
          results.summary.failed += 1;
        }

        results.summary.total_time_ms += elapsedMs;
      } catch (e) {
        const elapsedMs = performance.now() - startTime;

        results.test_cases.push({
          scenario_id: (testCase.metadata?.scenario_id as string) || 'unknown',
          passed: false,
          error: String(e),
          time_ms: elapsedMs,
        });

        results.summary.failed += 1;
        results.summary.total_time_ms += elapsedMs;
      }

      results.summary.total += 1;
    }

    return results;
  }

  /**
   * Run all benchmarks in the suite.
   *
   * @param agentFactory - Function that creates agent from (pattern_name, config)
   * @returns Promise resolving to all benchmark results
   */
  async runAllBenchmarks(
    agentFactory: (patternName: string, config: Record<string, unknown>) => Agent
  ): Promise<SuiteResult> {
    const allResults: SuiteResult = {
      benchmarks: [],
      summary: {
        total_patterns: this.benchmarks.length,
        total_test_cases: 0,
        total_passed: 0,
        total_failed: 0,
        total_time_ms: 0,
      },
    };

    for (const benchmark of this.benchmarks) {
      // Create pattern-specific agent factory
      const patternAgentFactory = (config: Record<string, unknown>) =>
        agentFactory(benchmark.patternName, config);

      // Run benchmark
      const results = await this.runBenchmark(benchmark, patternAgentFactory);
      allResults.benchmarks.push(results);

      // Update summary
      allResults.summary.total_test_cases += results.summary.total;
      allResults.summary.total_passed += results.summary.passed;
      allResults.summary.total_failed += results.summary.failed;
      allResults.summary.total_time_ms += results.summary.total_time_ms;
    }

    return allResults;
  }

  /**
   * Convert suite to dictionary.
   *
   * @returns Object representation of the suite
   */
  toDict(): Record<string, unknown> {
    return {
      patterns: this.benchmarks.map((b) => b.patternName),
      total_benchmarks: this.benchmarks.length,
      descriptions: Object.fromEntries(
        this.benchmarks.map((b) => [b.patternName, b.description])
      ),
    };
  }
}
