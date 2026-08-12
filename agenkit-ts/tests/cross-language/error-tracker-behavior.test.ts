/**
 * Cross-language error tracker behavior tests for TypeScript.
 *
 * Validates that Agenkit's TypeScript ErrorTracker (p_a / P_error) behaves
 * consistently with the cross-language error tracker behavior specification
 * (#652, follow-up to #321).
 */

import { describe, it, expect, beforeAll } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import { ErrorTracker } from '../../src/evaluation/error-tracker';

interface ErrorTrackerTestCase {
  id: string;
  name: string;
  steps?: boolean[];
  steps_spec?: { fail: number; success: number };
  expected: {
    total_steps: number;
    failed_steps: number;
    per_step_error_rate: number;
    cumulative_failure_probability_observed?: number;
    cumulative_failure_probability_steps: Record<string, number>;
    tolerance?: number;
  };
}

interface ErrorTrackerFixtures {
  version: string;
  description: string;
  test_cases: ErrorTrackerTestCase[];
}

let fixtures: ErrorTrackerFixtures;

beforeAll(() => {
  // Path from agenkit-ts/tests/cross-language to agenkit/tests/cross_language
  const fixturesPath = path.join(
    __dirname,
    '..',
    '..',
    '..',
    'tests',
    'cross_language',
    'fixtures',
    'error_tracker_behavior.json'
  );
  const fixturesData = fs.readFileSync(fixturesPath, 'utf-8');
  fixtures = JSON.parse(fixturesData);
});

function buildSteps(testCase: ErrorTrackerTestCase): boolean[] {
  if (testCase.steps) {
    return testCase.steps;
  }
  const spec = testCase.steps_spec!;
  return [...Array(spec.fail).fill(false), ...Array(spec.success).fill(true)];
}

describe('Error Tracker Behavior', () => {
  it('matches the shared error tracker fixture for every test case', () => {
    for (const testCase of fixtures.test_cases) {
      const expected = testCase.expected;
      const tolerance = expected.tolerance ?? 1e-6;

      const tracker = new ErrorTracker(true);
      for (const success of buildSteps(testCase)) {
        tracker.recordStep(success);
      }

      expect(tracker.totalSteps, `[${testCase.id}] total_steps`).toBe(expected.total_steps);
      expect(tracker.failedSteps, `[${testCase.id}] failed_steps`).toBe(expected.failed_steps);
      expect(
        tracker.perStepErrorRate(),
        `[${testCase.id}] per_step_error_rate`
      ).toBeCloseTo(expected.per_step_error_rate, tolerancePrecision(tolerance));

      if (expected.cumulative_failure_probability_observed !== undefined) {
        expect(
          tracker.cumulativeFailureProbability(),
          `[${testCase.id}] cumulative_failure_probability_observed`
        ).toBeCloseTo(expected.cumulative_failure_probability_observed, tolerancePrecision(tolerance));
      }

      for (const [stepsStr, expectedP] of Object.entries(expected.cumulative_failure_probability_steps)) {
        const n = parseInt(stepsStr, 10);
        expect(
          tracker.cumulativeFailureProbability(n),
          `[${testCase.id}] cumulative_failure_probability_steps[${n}]`
        ).toBeCloseTo(expectedP, tolerancePrecision(tolerance));
      }
    }
  });
});

/**
 * Convert an absolute tolerance into the `numDigits` precision argument
 * expected by vitest's `toBeCloseTo` (which checks |a - b| < 0.5 * 10^-precision).
 */
function tolerancePrecision(tolerance: number): number {
  if (tolerance <= 0) {
    return 9;
  }
  return Math.max(0, Math.floor(-Math.log10(tolerance)));
}
