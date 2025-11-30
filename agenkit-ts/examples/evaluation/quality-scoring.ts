/**
 * Quality Scoring Example
 *
 * Quality scoring measures how well an agent performs across multiple dimensions:
 * - Accuracy: Does it give correct answers?
 * - Relevance: Are responses on-topic?
 * - Completeness: Does it answer all parts of the question?
 * - Coherence: Is the response well-structured?
 *
 * This example shows how to use AccuracyMetric, QualityMetrics, and
 * PrecisionRecallMetric to comprehensively evaluate agent quality.
 *
 * Run with: npx tsx examples/evaluation/quality-scoring.ts
 */

import {
  Evaluator,
  AccuracyMetric,
  QualityMetrics,
  PrecisionRecallMetric,
} from '../../src/evaluation';
import { Agent, Message } from '../../src/core/interfaces';

/**
 * Quiz agent that simulates answering quiz questions.
 */
class QuizAgent implements Agent {
  getName(): string {
    return 'quiz-agent';
  }

  getCapabilities(): string[] {
    return ['qa'];
  }

  async process(message: Message, sessionId?: string): Promise<Message> {
    // Simple rule-based responses for demo
    const query = message.content.toLowerCase();
    let response: string;

    if (query.includes('capital of france')) {
      response =
        'The capital of France is Paris, a beautiful city known for its art, culture, and the Eiffel Tower.';
    } else if (query.includes('2+2')) {
      response = '2+2 equals 4.';
    } else if (query.includes('largest ocean')) {
      response =
        'The Pacific Ocean is the largest ocean on Earth, covering more than 63 million square miles.';
    } else if (query.includes('python language')) {
      response =
        "Python is a high-level programming language created by Guido van Rossum. It's known for its simplicity and readability.";
    } else if (query.includes('photosynthesis')) {
      response =
        'Photosynthesis is the process by which plants convert light energy into chemical energy, producing oxygen as a byproduct.';
    } else {
      response = "I'm not sure about that. Could you rephrase the question?";
    }

    return {
      role: 'assistant',
      content: response,
      metadata: {},
    };
  }
}

async function main() {
  console.log('Quality Scoring Example');
  console.log('=======================\n');

  // Step 1: Create agent and metrics
  console.log('Step 1: Setting Up Evaluation');
  console.log('------------------------------');
  const agent = new QuizAgent();

  const accuracyMetric = new AccuracyMetric({ caseSensitive: false });
  const qualityMetric = new QualityMetrics({ useLLMJudge: false });
  const precisionRecallMetric = new PrecisionRecallMetric();

  const evaluator = new Evaluator(
    agent,
    [accuracyMetric, qualityMetric, precisionRecallMetric],
    'quality-eval'
  );

  console.log('✓ Agent created: quiz-agent');
  console.log('✓ Metrics configured: accuracy, quality, precision/recall\n');

  // Step 2: Define test cases
  console.log('Step 2: Defining Test Cases');
  console.log('----------------------------');
  const testCases = [
    {
      input: 'What is the capital of France?',
      expected: 'Paris',
      true_label: true,
      predicted_label: true,
    },
    {
      input: 'What is 2+2?',
      expected: '4',
      true_label: true,
      predicted_label: true,
    },
    {
      input: 'What is the largest ocean?',
      expected: 'Pacific',
      true_label: true,
      predicted_label: true,
    },
    {
      input: 'Tell me about the Python programming language',
      expected: 'Python',
      true_label: true,
      predicted_label: true,
    },
    {
      input: 'Explain photosynthesis',
      expected: 'photosynthesis',
      true_label: true,
      predicted_label: true,
    },
    {
      input: 'What is the meaning of life?',
      expected: '42', // Agent will fail this
      true_label: false,
      predicted_label: false,
    },
  ];

  console.log(`Test cases defined: ${testCases.length}\n`);

  // Step 3: Run evaluation
  console.log('Step 3: Running Evaluation');
  console.log('---------------------------');
  const result = await evaluator.evaluate(testCases, 'quality-eval-001');

  console.log('✓ Evaluation complete');
  console.log(`  Tests Run: ${result.totalTests}`);
  console.log(`  Passed: ${result.passedTests}`);
  console.log(`  Failed: ${result.failedTests}\n`);

  // Step 4: Analyze accuracy results
  console.log('Step 4: Accuracy Analysis');
  console.log('-------------------------');
  const accuracyStats = result.aggregatedMetrics.get('accuracy');
  if (accuracyStats) {
    const accuracy = accuracyStats.mean;
    const correct = accuracyStats.count * accuracy;
    const incorrect = accuracyStats.count * (1 - accuracy);

    console.log(`Overall Accuracy: ${(accuracy * 100).toFixed(1)}%`);
    console.log(`Correct: ${correct.toFixed(0)}`);
    console.log(`Incorrect: ${incorrect.toFixed(0)}`);
    console.log(`Total: ${accuracyStats.count}\n`);
  }

  // Step 5: Analyze quality scores
  console.log('Step 5: Quality Analysis');
  console.log('------------------------');
  const qualityStats = result.aggregatedMetrics.get('quality');
  if (qualityStats) {
    console.log('Quality Metrics:');
    console.log(`  Mean Quality Score: ${qualityStats.mean.toFixed(3)} (0.0-1.0 scale)`);
    console.log(`  Min Score: ${qualityStats.min.toFixed(3)}`);
    console.log(`  Max Score: ${qualityStats.max.toFixed(3)}`);
    console.log(`  Std Deviation: ${qualityStats.std.toFixed(3)}\n`);

    // Interpretation
    const meanQuality = qualityStats.mean;
    console.log('Interpretation:');
    if (meanQuality >= 0.8) {
      console.log('  ✓ Excellent: Agent responses are high quality');
    } else if (meanQuality >= 0.6) {
      console.log('  ⚠ Good: Agent responses are acceptable but could improve');
    } else if (meanQuality >= 0.4) {
      console.log('  ⚠ Fair: Agent responses need significant improvement');
    } else {
      console.log('  ✗ Poor: Agent responses are low quality');
    }
    console.log();
  }

  // Step 6: Analyze precision/recall
  console.log('Step 6: Precision/Recall Analysis');
  console.log('----------------------------------');
  const prStats = result.aggregatedMetrics.get('precision_recall');
  if (prStats) {
    // PrecisionRecallMetric stores multiple values, we need to extract them
    const measurements = result.metrics.get('precision_recall') || [];
    if (measurements.length > 0) {
      // Calculate from all measurements
      let tp = 0,
        fp = 0,
        tn = 0,
        fn = 0;
      testCases.forEach((tc, i) => {
        const trueLabel = tc.true_label;
        const predLabel = tc.predicted_label;
        if (trueLabel && predLabel) tp++;
        else if (!trueLabel && predLabel) fp++;
        else if (!trueLabel && !predLabel) tn++;
        else if (trueLabel && !predLabel) fn++;
      });

      const precision = tp + fp > 0 ? tp / (tp + fp) : 0;
      const recall = tp + fn > 0 ? tp / (tp + fn) : 0;
      const f1 = precision + recall > 0 ? (2 * precision * recall) / (precision + recall) : 0;

      console.log('Classification Metrics:');
      console.log(`  Precision: ${precision.toFixed(3)}`);
      console.log(`  Recall: ${recall.toFixed(3)}`);
      console.log(`  F1 Score: ${f1.toFixed(3)}\n`);

      console.log('Confusion Matrix:');
      console.log(`  True Positives: ${tp}`);
      console.log(`  False Positives: ${fp}`);
      console.log(`  True Negatives: ${tn}`);
      console.log(`  False Negatives: ${fn}\n`);
    }
  }

  // Step 7: Individual test case analysis
  console.log('Step 7: Individual Test Case Analysis');
  console.log('--------------------------------------');
  console.log('\nDetailed Results for Each Test Case:\n');

  const accuracyMeasurements = result.metrics.get('accuracy') || [];
  const qualityMeasurements = result.metrics.get('quality') || [];

  testCases.forEach((testCase, i) => {
    console.log(`${i + 1}. Input: ${testCase.input}`);
    console.log(`   Expected: ${testCase.expected}`);

    if (i < accuracyMeasurements.length) {
      const accuracy = accuracyMeasurements[i];
      const status = accuracy === 1.0 ? '✓ Correct' : '✗ Incorrect';
      console.log(`   Accuracy: ${status}`);
    }

    if (i < qualityMeasurements.length) {
      const quality = qualityMeasurements[i];
      console.log(`   Quality Score: ${quality.toFixed(3)}`);
    }
    console.log();
  });

  // Summary
  console.log('='.repeat(70));
  console.log('Summary: Quality Scoring');
  console.log('='.repeat(70));

  console.log('\nMetrics Available:');
  console.log('1. AccuracyMetric: Binary correct/incorrect classification');
  console.log('   - Use for: Factual QA, math problems, classification tasks');
  console.log('   - Output: 0.0 (incorrect) or 1.0 (correct)');

  console.log('\n2. QualityMetrics: Multi-dimensional quality assessment');
  console.log('   - Relevance: Does response address the query?');
  console.log('   - Completeness: Is the answer complete?');
  console.log('   - Coherence: Is it well-structured?');
  console.log('   - Accuracy: Is it factually correct?');
  console.log('   - Output: 0.0-1.0 weighted score');

  console.log('\n3. PrecisionRecallMetric: Classification performance');
  console.log('   - Precision: Of predicted positives, how many were correct?');
  console.log('   - Recall: Of actual positives, how many were found?');
  console.log('   - F1 Score: Harmonic mean of precision and recall');
  console.log('   - Use for: Binary classification tasks');

  console.log('\nCustom Validators:');
  console.log('AccuracyMetric supports custom validation functions:');
  console.log('  const customValidator = (expected, actual) => {');
  console.log('    // Your custom logic here');
  console.log('    return actual.includes(expected);');
  console.log('  };');
  console.log('  const metric = new AccuracyMetric({ validator: customValidator });');

  console.log('\nBest Practices:');
  console.log('1. Use multiple metrics for comprehensive evaluation');
  console.log('2. Combine accuracy (correctness) with quality (completeness)');
  console.log('3. Set realistic expectations (80% accuracy is often good)');
  console.log('4. Analyze failures to identify patterns');
  console.log('5. Track metrics over time to detect regressions');
  console.log('6. Use precision/recall for imbalanced datasets');

  console.log('\nReal-World Applications:');
  console.log('- Customer Service: Measure response relevance and completeness');
  console.log('- QA Systems: Verify factual accuracy of answers');
  console.log('- Classification: Precision/recall for filtering tasks');
  console.log('- Content Generation: Quality scoring for generated text');
  console.log('- Code Generation: Accuracy for syntax, quality for style');
}

main().catch(console.error);
