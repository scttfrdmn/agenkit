"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.CodeGenerationBenchmark = exports.NeedleInHaystackBenchmark = exports.ReasoningBenchmark = exports.SimpleQABenchmark = void 0;
exports.getAllBenchmarks = getAllBenchmarks;
exports.getBenchmarkByName = getBenchmarkByName;
exports.runBenchmark = runBenchmark;
/**
 * Simple question-answering benchmark.
 *
 * Tests basic knowledge and reasoning with straightforward questions.
 */
class SimpleQABenchmark {
    constructor() {
        this.name = 'simple_qa';
        this.description = 'Basic question-answering tasks';
    }
    async generateTestCases() {
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
exports.SimpleQABenchmark = SimpleQABenchmark;
/**
 * Reasoning benchmark with multi-step problems.
 *
 * Tests logical reasoning and multi-step problem solving.
 */
class ReasoningBenchmark {
    constructor() {
        this.name = 'reasoning';
        this.description = 'Multi-step reasoning and logic problems';
    }
    async generateTestCases() {
        return [
            {
                input: 'If all roses are flowers and all flowers need water, do roses need water?',
                expected: 'yes',
                tags: ['logic', 'syllogism', 'medium'],
            },
            {
                input: 'A bat and ball cost $1.10. The bat costs $1 more than the ball. How much does the ball cost?',
                expected: '0.05',
                tags: ['math', 'reasoning', 'medium'],
            },
            {
                input: 'If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets?',
                expected: '5',
                tags: ['reasoning', 'math', 'medium'],
            },
            {
                input: 'John is taller than Mary. Mary is taller than Sue. Who is the shortest?',
                expected: 'Sue',
                tags: ['logic', 'comparison', 'easy'],
            },
            {
                input: 'A farmer has 17 sheep and all but 9 die. How many sheep are left?',
                expected: '9',
                tags: ['reasoning', 'word-problem', 'medium'],
            },
        ];
    }
}
exports.ReasoningBenchmark = ReasoningBenchmark;
/**
 * Needle-in-haystack benchmark for context retrieval.
 *
 * Tests ability to retrieve specific information from large contexts.
 * Essential for testing context window capabilities.
 */
class NeedleInHaystackBenchmark {
    constructor(config = {}) {
        this.contextLength = config.contextLength || 1000;
        this.needleCount = config.needleCount || 3;
    }
    get name() {
        return `needle_in_haystack_${this.contextLength}`;
    }
    get description() {
        return `Retrieve ${this.needleCount} facts from ${this.contextLength} token context`;
    }
    async generateTestCases() {
        const testCases = [];
        // Generate needles (specific facts to retrieve)
        const needles = [];
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
    generateHaystack(targetTokens) {
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
        const tokensPerParagraph = paragraphs.reduce((sum, p) => sum + p.split(' ').length, 0);
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
    embedNeedles(haystack, needles) {
        const words = haystack.split(' ');
        const interval = Math.floor(words.length / (needles.length + 1));
        const embedded = [];
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
exports.NeedleInHaystackBenchmark = NeedleInHaystackBenchmark;
/**
 * Code generation benchmark.
 *
 * Tests ability to generate correct code snippets.
 */
class CodeGenerationBenchmark {
    constructor() {
        this.name = 'code_generation';
        this.description = 'Generate simple code snippets';
    }
    async generateTestCases() {
        return [
            {
                input: 'Write a function that returns the sum of two numbers.',
                expected: (output) => output.includes('function') && output.includes('return'),
                tags: ['code', 'javascript', 'easy'],
                metadata: { language: 'javascript' },
            },
            {
                input: 'Write a function to check if a number is even.',
                expected: (output) => output.includes('function') && output.includes('%') && output.includes('2'),
                tags: ['code', 'logic', 'easy'],
                metadata: { language: 'javascript' },
            },
            {
                input: 'Write a function to reverse a string.',
                expected: (output) => output.includes('function') &&
                    (output.includes('reverse') || output.includes('split')),
                tags: ['code', 'strings', 'easy'],
                metadata: { language: 'javascript' },
            },
        ];
    }
}
exports.CodeGenerationBenchmark = CodeGenerationBenchmark;
/**
 * Get all available benchmarks.
 *
 * @returns Array of benchmark instances
 */
function getAllBenchmarks() {
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
function getBenchmarkByName(name) {
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
async function runBenchmark(benchmark, evaluateFn) {
    const testCases = await benchmark.generateTestCases();
    const results = [];
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
        }
        catch (error) {
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
