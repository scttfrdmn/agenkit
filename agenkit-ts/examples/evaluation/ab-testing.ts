/**
 * A/B Testing Example
 *
 * A/B testing compares two versions of an agent on identical inputs
 * to determine which performs better. This is essential for:
 * - Validating improvements before deployment
 * - Comparing different LLM models
 * - Testing prompt variations
 * - Evaluating configuration changes
 *
 * This example demonstrates:
 * - Recording baseline session with control agent (V1)
 * - Replaying with variant agent (V2)
 * - Comparing outputs, latency, and quality
 * - Making data-driven deployment decisions
 *
 * Run with: npx tsx examples/evaluation/ab-testing.ts
 */

import {
  SessionRecorder,
  InMemoryRecordingStorage,
  SessionReplay,
  QualityMetrics,
} from '../../src/evaluation';
import { Agent, Message } from '../../src/core/interfaces';

/**
 * Agent V1 - Current production version.
 */
class AgentV1 implements Agent {
  getName(): string {
    return 'agent-v1';
  }

  getCapabilities(): string[] {
    return ['qa'];
  }

  async process(message: Message, sessionId?: string): Promise<Message> {
    // Simple responses
    const query = message.content.toLowerCase();
    let response: string;

    if (query.includes('weather')) {
      response = "I don't have access to weather information.";
    } else if (query.includes('help')) {
      response = 'I can assist you with questions.';
    } else {
      response = "I'll help you with that.";
    }

    return {
      role: 'assistant',
      content: response,
      metadata: {},
    };
  }
}

/**
 * Agent V2 - New candidate version with improved responses.
 */
class AgentV2 implements Agent {
  getName(): string {
    return 'agent-v2';
  }

  getCapabilities(): string[] {
    return ['qa'];
  }

  async process(message: Message, sessionId?: string): Promise<Message> {
    // Improved responses with more detail
    const query = message.content.toLowerCase();
    let response: string;

    if (query.includes('weather')) {
      response =
        "I don't currently have access to real-time weather information. However, I recommend checking weather.com or your local weather service for the most accurate forecast.";
    } else if (query.includes('help')) {
      response =
        "I'd be happy to help! I can answer questions, provide information, and assist with various tasks. What would you like to know?";
    } else {
      response =
        "I'll be glad to assist you with that. Could you provide more details so I can give you the most helpful response?";
    }

    return {
      role: 'assistant',
      content: response,
      metadata: {},
    };
  }
}

async function main() {
  console.log('A/B Testing Example');
  console.log('===================\n');

  // Step 1: Setup agents and test suite
  console.log('Step 1: Setting Up A/B Test');
  console.log('---------------------------');

  const agentV1 = new AgentV1();
  const agentV2 = new AgentV2();

  const testCases = [
    { input: "What's the weather like today?" },
    { input: 'Can you help me?' },
    { input: 'I need assistance with my order' },
    { input: 'Tell me about your capabilities' },
    { input: 'How do I reset my password?' },
  ];

  console.log(`Agent A (Control): ${agentV1.getName()}`);
  console.log(`Agent B (Variant): ${agentV2.getName()}`);
  console.log(`Test Cases: ${testCases.length}\n`);

  // Step 2: Record baseline session (V1)
  console.log('Step 2: Recording Baseline Session (Agent V1)');
  console.log('----------------------------------------------');

  const recorderV1 = new SessionRecorder(new InMemoryRecordingStorage());
  const wrappedV1 = recorderV1.wrap(agentV1);

  const sessionId = 'ab-test-session';
  for (let i = 0; i < testCases.length; i++) {
    const input = testCases[i].input;
    const message: Message = {
      role: 'user',
      content: input,
      metadata: {
        session_id: sessionId,
      },
    };

    const response = await wrappedV1.process(message, sessionId);
    console.log(`  ${i + 1}. Input: ${input}`);
    console.log(`     V1: ${response.content}`);
  }

  const recordingV1 = await recorderV1.finalizeSession(sessionId);
  console.log(`\n✓ Baseline recorded: ${recordingV1.interactions.length} interactions\n`);

  // Step 3: Replay with V2
  console.log('Step 3: Replaying with Agent V2');
  console.log('--------------------------------');

  const replay = new SessionReplay();
  const resultsV1 = await replay.replay(recordingV1, agentV1);
  const resultsV2 = await replay.replay(recordingV1, agentV2);

  console.log('Comparing outputs:');

  for (let i = 0; i < resultsV1.interactions.length; i++) {
    const interactionV1 = resultsV1.interactions[i];
    const interactionV2 = resultsV2.interactions[i];

    const outputV1 = interactionV1.replayOutput.content;
    const outputV2 = interactionV2.replayOutput.content;
    const input = interactionV1.originalInput.content;

    console.log(`\n  ${i + 1}. Input: ${input}`);
    console.log(`     V1: ${outputV1}`);
    console.log(`     V2: ${outputV2}`);

    if (outputV2.length > outputV1.length) {
      const improvement = ((outputV2.length - outputV1.length) / outputV1.length) * 100;
      console.log(`     📈 V2 is ${improvement.toFixed(0)}% longer (more detailed)`);
    }
  }

  // Step 4: Compare metrics
  console.log('\n\nStep 4: Comparing Performance Metrics');
  console.log('--------------------------------------');
  const comparison = replay.compare(resultsV1, resultsV2);

  console.log(`Interaction Count: ${comparison.interactionCount}`);
  console.log(
    `Latency Difference: ${comparison.latencyDiffMs.toFixed(0)}ms (${comparison.latencyDiffPercent.toFixed(1)}%)`
  );

  const outputDiffPercent =
    (comparison.outputDifferences.length / comparison.interactionCount) * 100;
  console.log(
    `Output Differences: ${comparison.outputDifferences.length}/${comparison.interactionCount} (${outputDiffPercent.toFixed(0)}%)`
  );

  // Step 5: Quality evaluation
  console.log('\n\nStep 5: Quality Evaluation');
  console.log('--------------------------');

  const qualityMetric = new QualityMetrics({ useLLMJudge: false });

  let totalQualityV1 = 0;
  let totalQualityV2 = 0;

  for (let i = 0; i < testCases.length; i++) {
    const inputMsg: Message = {
      role: 'user',
      content: testCases[i].input,
      metadata: {},
    };

    // V1 quality
    const outputV1: Message = {
      role: 'assistant',
      content: resultsV1.interactions[i].replayOutput.content,
      metadata: {},
    };
    const qualityV1 = await qualityMetric.measure(agentV1, inputMsg, outputV1, {});
    totalQualityV1 += qualityV1;

    // V2 quality
    const outputV2: Message = {
      role: 'assistant',
      content: resultsV2.interactions[i].replayOutput.content,
      metadata: {},
    };
    const qualityV2 = await qualityMetric.measure(agentV2, inputMsg, outputV2, {});
    totalQualityV2 += qualityV2;
  }

  const avgQualityV1 = totalQualityV1 / testCases.length;
  const avgQualityV2 = totalQualityV2 / testCases.length;

  console.log('Average Quality Scores:');
  console.log(`  V1 (Control): ${avgQualityV1.toFixed(3)}`);
  console.log(`  V2 (Variant): ${avgQualityV2.toFixed(3)}`);

  const qualityImprovement = ((avgQualityV2 - avgQualityV1) / avgQualityV1) * 100;
  if (qualityImprovement > 0) {
    console.log(`  📈 V2 is ${qualityImprovement.toFixed(1)}% better`);
  } else {
    console.log(`  📉 V2 is ${Math.abs(qualityImprovement).toFixed(1)}% worse`);
  }

  // Step 6: Recommendation
  console.log('\n\nStep 6: Deployment Recommendation');
  console.log('----------------------------------');

  const shouldDeploy = avgQualityV2 > avgQualityV1;
  const latencyIncrease = comparison.latencyDiffPercent;

  console.log('Analysis:');
  if (shouldDeploy) {
    console.log('  ✓ V2 shows quality improvement');
  } else {
    console.log('  ✗ V2 does not show quality improvement');
  }

  if (latencyIncrease < 10) {
    console.log('  ✓ Latency increase is acceptable (<10%)');
  } else {
    console.log(`  ⚠ Latency increased by ${latencyIncrease.toFixed(1)}% (review required)`);
  }

  console.log('\nRecommendation:');
  if (shouldDeploy && latencyIncrease < 10) {
    console.log('  🚀 DEPLOY V2 - Shows improvement without significant latency cost');
  } else if (shouldDeploy) {
    console.log('  ⚠ CONDITIONAL DEPLOY - Improvement present but review latency impact');
  } else {
    console.log('  ❌ DO NOT DEPLOY - V2 does not show improvement over V1');
  }

  // Summary
  console.log('\n' + '='.repeat(70));
  console.log('Summary: A/B Testing');
  console.log('='.repeat(70));

  console.log('\nA/B Testing Process:');
  console.log('1. Record baseline session with control agent (V1)');
  console.log('2. Replay session with variant agent (V2)');
  console.log('3. Compare outputs, latency, and quality');
  console.log('4. Make data-driven deployment decision');

  console.log('\nMetrics to Compare:');
  console.log('- Quality Score: Rule-based or LLM-as-judge');
  console.log('- Accuracy: Correctness on known answers');
  console.log('- Latency: Response time (P50, P95, P99)');
  console.log('- Cost: Token usage and API costs');
  console.log('- Output Differences: Semantic similarity');

  console.log('\nBest Practices:');
  console.log('1. Use diverse test cases covering edge cases');
  console.log('2. Run on production-like data, not synthetic');
  console.log('3. Test with sufficient sample size (50+ interactions)');
  console.log('4. Consider multiple metrics, not just one');
  console.log('5. Set acceptance criteria before testing');
  console.log('6. Run multiple trials for statistical significance');

  console.log('\nDecision Criteria:');
  console.log('Deploy if:');
  console.log('  - Quality improvement >5%');
  console.log('  - Latency increase <10%');
  console.log('  - No increase in error rate');
  console.log('  - Cost increase justified by quality gain');

  console.log('\nReal-World Applications:');
  console.log('- Model Selection: GPT-4 vs Claude vs Gemini');
  console.log('- Prompt Engineering: Compare prompt variations');
  console.log('- Configuration Tuning: Temperature, top_p, etc.');
  console.log('- Feature Validation: New capabilities vs baseline');
  console.log('- Cost Optimization: Cheaper model with same quality');

  console.log('\nStatistical Significance:');
  console.log('For production A/B tests, consider:');
  console.log('- Sample size: At least 100 interactions per variant');
  console.log('- Confidence level: 95% or higher');
  console.log('- Effect size: Minimum detectable difference');
  console.log('- Use chi-square test for categorical metrics');
  console.log('- Use t-test for continuous metrics');
}

main().catch(console.error);
