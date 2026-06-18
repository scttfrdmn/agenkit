/**
 * Tests for ErrorTracker — per-step error rate and failure compounding.
 */

import { ErrorTracker } from '../evaluation/error-tracker';

describe('ErrorTracker', () => {
  describe('perStepErrorRate (p_a)', () => {
    it('returns 0 when no steps recorded', () => {
      const tracker = new ErrorTracker(true);
      expect(tracker.perStepErrorRate()).toBeCloseTo(0.0);
      expect(tracker.totalSteps).toBe(0);
      expect(tracker.failedSteps).toBe(0);
    });

    it('returns 0 when all steps pass', () => {
      const tracker = new ErrorTracker(true);
      for (let i = 0; i < 4; i++) {
        tracker.recordStep(true);
      }
      expect(tracker.perStepErrorRate()).toBeCloseTo(0.0);
      expect(tracker.totalSteps).toBe(4);
      expect(tracker.failedSteps).toBe(0);
    });

    it('returns 1 when all steps fail', () => {
      const tracker = new ErrorTracker(true);
      for (let i = 0; i < 4; i++) {
        tracker.recordStep(false, { error: 'boom' });
      }
      expect(tracker.perStepErrorRate()).toBeCloseTo(1.0);
      expect(tracker.totalSteps).toBe(4);
      expect(tracker.failedSteps).toBe(4);
    });

    it('returns 0.25 for a mixed run (1 of 4 failed)', () => {
      const tracker = new ErrorTracker(true);
      tracker.recordStep(true);
      tracker.recordStep(false, { error: 'timeout' });
      tracker.recordStep(true);
      tracker.recordStep(true);
      expect(tracker.perStepErrorRate()).toBeCloseTo(0.25);
      expect(tracker.totalSteps).toBe(4);
      expect(tracker.failedSteps).toBe(1);
    });
  });

  describe('cumulativeFailureProbability (P_error)', () => {
    it('compounds a 1% per-step rate over 100 steps to ~0.634', () => {
      const tracker = new ErrorTracker(true);
      // 1 failure out of 100 steps -> p_a = 0.01
      tracker.recordStep(false);
      for (let i = 0; i < 99; i++) {
        tracker.recordStep(true);
      }
      expect(tracker.perStepErrorRate()).toBeCloseTo(0.01);
      // observed over the 100 recorded steps
      expect(tracker.cumulativeFailureProbability()).toBeCloseTo(0.6340, 3);
    });

    it('projects compounding over a planned number of steps', () => {
      const tracker = new ErrorTracker(true);
      tracker.recordStep(true);
      tracker.recordStep(false);
      // p_a = 0.5, projected over 10 steps -> 1 - 0.5^10 = 0.999023...
      expect(tracker.perStepErrorRate()).toBeCloseTo(0.5);
      expect(tracker.cumulativeFailureProbability(10)).toBeCloseTo(0.999023, 5);
    });

    it('uses recorded step count as n when no argument given (observed)', () => {
      const tracker = new ErrorTracker(true);
      tracker.recordStep(true);
      tracker.recordStep(false);
      tracker.recordStep(true);
      tracker.recordStep(false);
      // p_a = 0.5, n = 4 -> 1 - 0.5^4 = 0.9375
      expect(tracker.cumulativeFailureProbability()).toBeCloseTo(0.9375);
    });

    it('returns 0 when p_a is 0', () => {
      const tracker = new ErrorTracker(true);
      tracker.recordStep(true);
      tracker.recordStep(true);
      expect(tracker.cumulativeFailureProbability()).toBeCloseTo(0.0);
      expect(tracker.cumulativeFailureProbability(1000)).toBeCloseTo(0.0);
    });

    it('returns 1 when p_a is 1 (full failure)', () => {
      const tracker = new ErrorTracker(true);
      tracker.recordStep(false);
      tracker.recordStep(false);
      expect(tracker.cumulativeFailureProbability()).toBeCloseTo(1.0);
      expect(tracker.cumulativeFailureProbability(5)).toBeCloseTo(1.0);
    });

    it('returns 0 for non-positive n', () => {
      const tracker = new ErrorTracker(true);
      tracker.recordStep(false);
      tracker.recordStep(true);
      expect(tracker.cumulativeFailureProbability(0)).toBeCloseTo(0.0);
      expect(tracker.cumulativeFailureProbability(-5)).toBeCloseTo(0.0);
    });

    it('returns 0 when nothing recorded and no steps given', () => {
      const tracker = new ErrorTracker(true);
      expect(tracker.cumulativeFailureProbability()).toBeCloseTo(0.0);
    });

    it('stays within [0, 1] across a range of rates and step counts', () => {
      for (const failures of [0, 1, 3, 7, 10]) {
        const tracker = new ErrorTracker(true);
        for (let i = 0; i < failures; i++) {
          tracker.recordStep(false);
        }
        for (let i = failures; i < 10; i++) {
          tracker.recordStep(true);
        }
        for (const n of [1, 5, 50, 500]) {
          const p = tracker.cumulativeFailureProbability(n);
          expect(p).toBeGreaterThanOrEqual(0.0);
          expect(p).toBeLessThanOrEqual(1.0);
        }
      }
    });
  });

  describe('disabled tracker', () => {
    it('is a no-op by default (recordStep records nothing, metrics are 0)', () => {
      const tracker = new ErrorTracker();
      expect(tracker.enabled).toBe(false);
      tracker.recordStep(false, { error: 'ignored' });
      tracker.recordStep(true);
      expect(tracker.totalSteps).toBe(0);
      expect(tracker.failedSteps).toBe(0);
      expect(tracker.perStepErrorRate()).toBeCloseTo(0.0);
      expect(tracker.cumulativeFailureProbability(100)).toBeCloseTo(0.0);
    });
  });

  describe('reset', () => {
    it('clears all recorded step results', () => {
      const tracker = new ErrorTracker(true);
      tracker.recordStep(false);
      tracker.recordStep(true);
      expect(tracker.totalSteps).toBe(2);

      tracker.reset();
      expect(tracker.totalSteps).toBe(0);
      expect(tracker.failedSteps).toBe(0);
      expect(tracker.perStepErrorRate()).toBeCloseTo(0.0);
      expect(tracker.cumulativeFailureProbability()).toBeCloseTo(0.0);

      // still enabled and usable after reset
      tracker.recordStep(false);
      expect(tracker.totalSteps).toBe(1);
      expect(tracker.perStepErrorRate()).toBeCloseTo(1.0);
    });
  });
});
