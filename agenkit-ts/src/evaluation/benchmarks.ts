/**
 * Benchmark suites for agent evaluation.
 *
 * Provides standard benchmarks for testing agent capabilities including
 * simple Q&A, reasoning, and context retrieval.
 *
 * Example:
 * ```typescript
 * const benchmark = new SimpleQABenchmark();
 * const testCases = await benchmark.generateTestCases();
 *
 * for (const testCase of testCases) {
 *   const response = await agent.process(createMessage('user', testCase.input));
 *   const isCorrect = response.content.includes(testCase.expected);
 *   console.log(`${testCase.input}: ${isCorrect ? 'PASS' : 'FAIL'}`);
 * }
 * ```
 */

/**
 * Single test case for evaluation.
 *
 * Contains input, expected output, and metadata.
 */
export interface TestCase {
  /** Input to provide to the agent */
  input: string;
  /** Expected output (string or validation function) */
  expected: string | ((output: string) => boolean);
  /** Additional metadata about the test case */
  metadata?: Record<string, unknown>;
  /** Tags for categorizing test cases */
  tags?: string[];
}

/**
 * Base interface for benchmarks.
 *
 * Benchmarks define test suites for evaluating specific capabilities.
 */
export interface Benchmark {
  /** Benchmark name */
  readonly name: string;
  /** Benchmark description */
  readonly description: string;
  /**
   * Generate test cases for this benchmark.
   *
   * @returns Promise resolving to list of test cases
   */
  generateTestCases(): Promise<TestCase[]>;
}

/**
 * Simple question-answering benchmark.
 *
 * Tests basic knowledge and reasoning with straightforward questions.
 */
export class SimpleQABenchmark implements Benchmark {
  readonly name = 'simple_qa';
  readonly description = 'Basic question-answering tasks';

  async generateTestCases(): Promise<TestCase[]> {
    return [
      {
        input: 'What is 2+2?',
        expected: '4',
        tags: ['math', 'easy'],
      },
      {
        input: 'What is the capital of France?',
        expected: 'Paris',
        tags: ['knowledge', 'easy'],
      },
      {
        input: 'What is the largest planet in our solar system?',
        expected: 'Jupiter',
        tags: ['knowledge', 'easy'],
      },
      {
        input: 'If a train leaves at 2pm and travels for 3 hours, when does it arrive?',
        expected: '5',
        tags: ['reasoning', 'easy'],
      },
      {
        input: 'What comes next in the sequence: 2, 4, 6, 8, ?',
        expected: '10',
        tags: ['reasoning', 'easy'],
      },
      {
        input: 'How many days are in a leap year?',
        expected: '366',
        tags: ['knowledge', 'easy'],
      },
      {
        input: 'What is the freezing point of water in Celsius?',
        expected: '0',
        tags: ['knowledge', 'easy'],
      },
      {
        input: 'If you have 3 apples and get 2 more, how many do you have?',
        expected: '5',
        tags: ['math', 'easy'],
      },
    ];
  }
}

/**
 * Reasoning benchmark with multi-step problems.
 *
 * Tests logical reasoning and multi-step problem solving.
 */
export class ReasoningBenchmark implements Benchmark {
  readonly name = 'reasoning';
  readonly description = 'Multi-step reasoning and logic problems';

  async generateTestCases(): Promise<TestCase[]> {
    return [
      {
        input:
          'If all roses are flowers and all flowers need water, do roses need water?',
        expected: 'yes',
        tags: ['reasoning', 'logic', 'syllogism', 'medium'],
      },
      {
        input:
          'A bat and ball cost $1.10. The bat costs $1 more than the ball. How much does the ball cost?',
        expected: '0.05',
        tags: ['reasoning', 'math', 'medium'],
      },
      {
        input:
          'If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets?',
        expected: '5',
        tags: ['reasoning', 'math', 'medium'],
      },
      {
        input:
          'John is taller than Mary. Mary is taller than Sue. Who is the shortest?',
        expected: 'Sue',
        tags: ['reasoning', 'logic', 'comparison', 'easy'],
      },
      {
        input:
          'A farmer has 17 sheep and all but 9 die. How many sheep are left?',
        expected: '9',
        tags: ['reasoning', 'word-problem', 'medium'],
      },
    ];
  }
}

/**
 * Configuration for needle-in-haystack benchmark.
 */
export interface NeedleInHaystackConfig {
  /** Target context length in tokens (approximate) */
  contextLength?: number;
  /** Number of needles to hide in the haystack */
  needleCount?: number;
}

/**
 * Needle-in-haystack benchmark for context retrieval.
 *
 * Tests ability to retrieve specific information from large contexts.
 * Essential for testing context window capabilities.
 */
export class NeedleInHaystackBenchmark implements Benchmark {
  readonly contextLength: number;
  readonly needleCount: number;

  constructor(config: NeedleInHaystackConfig = {}) {
    this.contextLength = config.contextLength || 1000;
    this.needleCount = config.needleCount || 3;
  }

  get name(): string {
    return `needle_in_haystack_${this.contextLength}`;
  }

  get description(): string {
    return `Retrieve ${this.needleCount} facts from ${this.contextLength} token context`;
  }

  async generateTestCases(): Promise<TestCase[]> {
    const testCases: TestCase[] = [];

    // Generate needles (specific facts to retrieve)
    const needles: string[] = [];
    for (let i = 0; i < this.needleCount; i++) {
      needles.push(`The secret code for vault ${i} is ALPHA-${String(i).padStart(4, '0')}-OMEGA.`);
    }

    // Generate haystack (filler content)
    const haystack = this.generateHaystack(this.contextLength);

    // Embed needles at regular intervals
    const context = this.embedNeedles(haystack, needles);

    // Create test cases asking for each needle
    for (let i = 0; i < needles.length; i++) {
      testCases.push({
        input: `Context: ${context}\n\nQuestion: What is the secret code for vault ${i}?`,
        expected: `ALPHA-${String(i).padStart(4, '0')}-OMEGA`,
        metadata: {
          contextLength: Math.floor(context.split(' ').length / 4), // Rough token estimate
          needlePosition: i,
          totalNeedles: this.needleCount,
        },
        tags: ['retrieval', 'context', `length_${this.contextLength}`],
      });
    }

    return testCases;
  }

  /**
   * Generate filler content for haystack.
   */
  private generateHaystack(targetTokens: number): string {
    const paragraphs = [
      'This is a paragraph of filler content. It contains general information that is not relevant to the specific queries we will ask. ' +
        'The purpose of this content is to create a large context that the agent must search through. ',
      'Here is another paragraph with different content. It discusses various topics without providing the specific information we\'re looking for. ' +
        'This helps test the agent\'s ability to find needles in haystacks. ',
      'Additional filler text to expand the context. This paragraph talks about unrelated subjects and serves to increase the total context length. ' +
        'The agent must be able to filter through this content efficiently. ',
    ];

    // Repeat paragraphs to reach target length
    let haystack = '';
    const tokensPerParagraph = paragraphs.reduce(
      (sum, p) => sum + p.split(' ').length,
      0
    );
    const repetitions = Math.floor(targetTokens / tokensPerParagraph) + 1;

    for (let i = 0; i < repetitions; i++) {
      for (const paragraph of paragraphs) {
        haystack += paragraph;
      }
    }

    return haystack;
  }

  /**
   * Embed needles at regular intervals in haystack.
   */
  private embedNeedles(haystack: string, needles: string[]): string {
    const words = haystack.split(' ');
    const interval = Math.floor(words.length / (needles.length + 1));

    const embedded: string[] = [];
    let needleIdx = 0;

    for (let i = 0; i < words.length; i++) {
      embedded.push(words[i]);

      // Insert needle at intervals
      if (needleIdx < needles.length && i > 0 && i % interval === 0) {
        embedded.push(needles[needleIdx]);
        needleIdx++;
      }
    }

    return embedded.join(' ');
  }
}

/**
 * Code generation benchmark.
 *
 * Tests ability to generate correct code snippets.
 */
export class CodeGenerationBenchmark implements Benchmark {
  readonly name = 'code_generation';
  readonly description = 'Generate simple code snippets';

  async generateTestCases(): Promise<TestCase[]> {
    return [
      {
        input: 'Write a function that returns the sum of two numbers.',
        expected: (output: string) =>
          output.includes('function') && output.includes('return'),
        tags: ['code', 'javascript', 'easy'],
        metadata: { language: 'javascript' },
      },
      {
        input: 'Write a function to check if a number is even.',
        expected: (output: string) =>
          output.includes('function') && output.includes('%') && output.includes('2'),
        tags: ['code', 'logic', 'easy'],
        metadata: { language: 'javascript' },
      },
      {
        input: 'Write a function to reverse a string.',
        expected: (output: string) =>
          output.includes('function') &&
          (output.includes('reverse') || output.includes('split')),
        tags: ['code', 'strings', 'easy'],
        metadata: { language: 'javascript' },
      },
    ];
  }
}

/**
 * Extreme-scale context retrieval benchmark.
 *
 * Tests agent's ability to retrieve information from extremely long contexts
 * (10K-100K+ tokens).
 */
export class ExtremeScaleBenchmark implements Benchmark {
  readonly name = 'extreme_scale';
  readonly description: string;
  private contextLengths: number[];
  private needleCount: number;

  /**
   * Create extreme-scale benchmark.
   *
   * @param contextLengths Array of context lengths to test
   * @param needleCount Number of needles to hide per context length
   */
  constructor(contextLengths: number[], needleCount: number = 1) {
    this.contextLengths = contextLengths;
    this.needleCount = needleCount;
    this.description = `Extreme-scale retrieval with contexts up to ${Math.max(...contextLengths)} tokens`;
  }

  async generateTestCases(): Promise<TestCase[]> {
    const testCases: TestCase[] = [];

    for (const contextLength of this.contextLengths) {
      for (let i = 0; i < this.needleCount; i++) {
        const needle = `IMPORTANT_FACT_${i + 1}: The secret code is ${Math.random().toString(36).substring(7)}`;
        const haystack = this.generateHaystack(contextLength);

        // Insert needle at random position
        const insertPos = Math.floor(Math.random() * haystack.length);
        const input = haystack.substring(0, insertPos) + ' ' + needle + ' ' + haystack.substring(insertPos);

        testCases.push({
          input: `${input}\n\nQuestion: What is the secret code mentioned in IMPORTANT_FACT_${i + 1}?`,
          expected: needle.split('is ')[1],
          tags: ['extreme_scale', 'retrieval', 'context'],
          metadata: {
            contextLength,
            needleIndex: i,
          },
        });
      }
    }

    return testCases;
  }

  private generateHaystack(targetLength: number): string {
    const filler = 'The quick brown fox jumps over the lazy dog. ';
    const repeatCount = Math.ceil(targetLength / filler.length);
    return filler.repeat(repeatCount).substring(0, targetLength);
  }
}

/**
 * Information retention benchmark.
 *
 * Tests agent's ability to remember information over a long conversation.
 */
export class InformationRetentionBenchmark implements Benchmark {
  readonly name = 'information_retention';
  readonly description: string;
  private conversationLength: number;
  private recallPoints: number[];

  /**
   * Create information retention benchmark.
   *
   * @param conversationLength Total length of conversation (number of turns)
   * @param recallPoints Array of turn indices where recall should be tested
   */
  constructor(conversationLength: number, recallPoints: number[]) {
    this.conversationLength = conversationLength;
    this.recallPoints = recallPoints;
    this.description = `Test information recall over ${conversationLength} conversation turns`;
  }

  async generateTestCases(): Promise<TestCase[]> {
    const testCases: TestCase[] = [];
    const facts: Array<{ turn: number; fact: string; key: string }> = [];

    // A fact must be planted before each requested recall point, otherwise that
    // recall point yields no test case at all. Planting is otherwise random at
    // 10% per turn, so a short conversation could produce zero facts and hence
    // zero recall tests despite recallPoints being non-empty — for an 80-turn
    // conversation that is 0.9^80, about 1 generation in 4,600, and for 50 turns
    // 1 in 194. Guaranteeing one plant in the run-up to each recall point makes
    // the benchmark honour its arguments; the remaining turns stay random so the
    // distribution of filler and extra facts is unchanged. (#658)
    const guaranteedPlantTurns = new Set(
      this.recallPoints
        .filter((point) => point > 0 && point < this.conversationLength)
        .map((point) => Math.floor(point / 2))
    );

    // Generate fact-planting test cases
    for (let turn = 0; turn < this.conversationLength; turn++) {
      if (guaranteedPlantTurns.has(turn) || Math.random() < 0.1) {
        // Plant a fact
        const key = `fact_${facts.length + 1}`;
        const value = `value_${Math.random().toString(36).substring(7)}`;
        const fact = `Remember this: ${key} = ${value}`;

        facts.push({ turn, fact, key });

        testCases.push({
          input: fact,
          expected: 'acknowledged',
          tags: ['retention', 'plant'],
          metadata: {
            type: 'fact_plant',
            turn,
            key,
          },
        });
      } else {
        // Filler conversation
        testCases.push({
          input: `Turn ${turn}: What's the weather like?`,
          expected: 'weather',
          tags: ['retention', 'filler'],
          metadata: {
            type: 'filler',
            turn,
          },
        });
      }
    }

    // Generate recall test cases at specified points
    for (const recallPoint of this.recallPoints) {
      // Only facts planted *before* the recall point are recallable. Selecting
      // from all facts, as this previously did, could ask the agent to recall
      // something it had not been told yet — an unanswerable case scored as a
      // retention failure. The guaranteed plant above ensures this is non-empty
      // for every in-range recall point.
      const plantedEarlier = facts.filter((f) => f.turn < recallPoint);

      if (recallPoint < this.conversationLength && plantedEarlier.length > 0) {
        // Pick a random fact to recall
        const fact = plantedEarlier[Math.floor(Math.random() * plantedEarlier.length)];
        const expectedValue = fact.fact.split('= ')[1];

        testCases.push({
          input: `What was the value of ${fact.key} that I told you earlier?`,
          expected: expectedValue,
          tags: ['retention', 'recall'],
          metadata: {
            type: 'recall_test',
            turn: recallPoint,
            key: fact.key,
            plantedAtTurn: fact.turn,
          },
        });
      }
    }

    return testCases;
  }
}

/**
 * Suite of multiple benchmarks.
 *
 * Allows running multiple benchmarks together and aggregating results.
 */
export class BenchmarkSuite {
  readonly name: string;
  readonly benchmarks: Benchmark[];

  /**
   * Create benchmark suite.
   *
   * @param name Suite name
   * @param benchmarks Array of benchmarks to include
   */
  constructor(name: string, benchmarks: Benchmark[]) {
    this.name = name;
    this.benchmarks = benchmarks;
  }

  /**
   * Generate test cases from all benchmarks.
   *
   * @returns Combined array of test cases from all benchmarks
   */
  async generateTestCases(): Promise<TestCase[]> {
    const allTestCases: TestCase[] = [];

    for (const benchmark of this.benchmarks) {
      const testCases = await benchmark.generateTestCases();
      allTestCases.push(...testCases);
    }

    return allTestCases;
  }

  /**
   * Run all benchmarks in the suite.
   *
   * @param evaluateFn Function to evaluate each test case
   * @returns Suite results with aggregated scores
   */
  async run(
    evaluateFn: (testCase: TestCase) => Promise<{
      input: string;
      expected: string;
      actual: string;
      score: number;
    }>
  ): Promise<SuiteResult> {
    const benchmarkResults: Array<{ benchmark: string; score: number; count: number }> = [];

    for (const benchmark of this.benchmarks) {
      const testCases = await benchmark.generateTestCases();
      let totalScore = 0;

      for (const testCase of testCases) {
        const result = await evaluateFn(testCase);
        totalScore += result.score;
      }

      const avgScore = testCases.length > 0 ? totalScore / testCases.length : 0;

      benchmarkResults.push({
        benchmark: benchmark.name,
        score: avgScore,
        count: testCases.length,
      });
    }

    // Calculate overall score
    const totalTests = benchmarkResults.reduce((sum, r) => sum + r.count, 0);
    const weightedScore = benchmarkResults.reduce(
      (sum, r) => sum + r.score * r.count,
      0
    );
    const overallScore = totalTests > 0 ? weightedScore / totalTests : 0;

    return {
      suiteName: this.name,
      benchmarks: benchmarkResults,
      overallScore,
      totalTests,
    };
  }
}

/**
 * Results from running a benchmark suite.
 */
export interface SuiteResult {
  suiteName: string;
  benchmarks: Array<{ benchmark: string; score: number; count: number }>;
  overallScore: number;
  totalTests: number;
}

/**
 * Get all available benchmarks.
 *
 * @returns Array of benchmark instances
 */
export function getAllBenchmarks(): Benchmark[] {
  return [
    new SimpleQABenchmark(),
    new ReasoningBenchmark(),
    new NeedleInHaystackBenchmark(),
    new NeedleInHaystackBenchmark({ contextLength: 5000, needleCount: 5 }),
    new CodeGenerationBenchmark(),
  ];
}

/**
 * Get benchmark by name.
 *
 * @param name Benchmark name
 * @returns Benchmark instance or undefined
 */
export function getBenchmarkByName(name: string): Benchmark | undefined {
  const benchmarks = getAllBenchmarks();
  return benchmarks.find(b => b.name === name);
}

/**
 * Run a benchmark against an agent and return results.
 *
 * @param benchmark Benchmark to run
 * @param evaluateFn Function to evaluate each test case
 * @returns Benchmark results with pass/fail counts
 */
export async function runBenchmark(
  benchmark: Benchmark,
  evaluateFn: (testCase: TestCase) => Promise<boolean>
): Promise<BenchmarkResult> {
  const testCases = await benchmark.generateTestCases();
  const results: TestCaseResult[] = [];

  for (const testCase of testCases) {
    const startTime = performance.now();
    try {
      const passed = await evaluateFn(testCase);
      const duration = performance.now() - startTime;

      results.push({
        input: testCase.input,
        expected: typeof testCase.expected === 'string' ? testCase.expected : '<function>',
        passed,
        duration,
        tags: testCase.tags || [],
      });
    } catch (error) {
      const duration = performance.now() - startTime;
      results.push({
        input: testCase.input,
        expected: typeof testCase.expected === 'string' ? testCase.expected : '<function>',
        passed: false,
        duration,
        error: error instanceof Error ? error.message : String(error),
        tags: testCase.tags || [],
      });
    }
  }

  const passed = results.filter(r => r.passed).length;
  const failed = results.filter(r => !r.passed).length;
  const totalDuration = results.reduce((sum, r) => sum + r.duration, 0);

  return {
    benchmarkName: benchmark.name,
    description: benchmark.description,
    totalTests: testCases.length,
    passed,
    failed,
    accuracy: (passed / testCases.length) * 100,
    totalDuration,
    averageDuration: totalDuration / testCases.length,
    results,
  };
}

/**
 * Result for a single test case.
 */
export interface TestCaseResult {
  input: string;
  expected: string;
  passed: boolean;
  duration: number;
  error?: string;
  tags: string[];
}

/**
 * Results from running a benchmark.
 */
export interface BenchmarkResult {
  benchmarkName: string;
  description: string;
  totalTests: number;
  passed: number;
  failed: number;
  accuracy: number;
  totalDuration: number;
  averageDuration: number;
  results: TestCaseResult[];
}
