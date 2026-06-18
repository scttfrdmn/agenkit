/**
 * Error tracking infrastructure — per-step error rate and failure compounding.
 *
 * Long-running agents execute many steps; even a small per-step error rate
 * compounds into a high probability of at least one failure over a long run.
 * `ErrorTracker` records the outcome of each step and exposes the two core
 * quantities from the agent-failure-rate analysis:
 *
 * - `p_a` ({@link ErrorTracker.perStepErrorRate}) — the per-step error rate,
 *   `failedSteps / totalSteps`.
 * - `P_error` ({@link ErrorTracker.cumulativeFailureProbability}) — the
 *   probability of at least one failure across `n` independent steps,
 *   `1 - (1 - p_a) ** n`. With no argument, `n` is the number of recorded
 *   steps (observed cumulative failure probability); pass `steps=N` to project
 *   the compounding over a planned run of `N` steps.
 *
 * Tracking is opt-in: construct an `ErrorTracker(true)` and call
 * {@link ErrorTracker.recordStep} as steps complete. When disabled,
 * `recordStep` is a no-op and the metrics report zero, so the tracker is cheap
 * to leave wired in.
 *
 * Example:
 * ```typescript
 * const tracker = new ErrorTracker(true);
 * tracker.recordStep(true);
 * tracker.recordStep(false, { error: 'timeout' });
 * tracker.perStepErrorRate(); // 0.5
 * tracker.cumulativeFailureProbability(10); // ~0.999
 * ```
 */

/**
 * Outcome of a single agent step.
 */
export interface StepResult {
  /** Whether the step completed without error. */
  success: boolean;
  /** Optional step label (useful for per-step breakdowns later). */
  name?: string;
  /** Optional error description when `success` is `false`. */
  error?: string;
}

/**
 * Options for recording a step outcome.
 */
export interface RecordStepOptions {
  /** Optional step label. */
  name?: string;
  /** Optional error description for a failed step. */
  error?: string;
}

/**
 * Records step outcomes and computes error-rate / compounding metrics.
 *
 * When disabled (the default), {@link ErrorTracker.recordStep} is a no-op and
 * all metrics report `0` / `0.0` — tracking is strictly opt-in.
 */
export class ErrorTracker {
  private readonly stepResults: StepResult[] = [];

  /**
   * @param enabled When `false` (the default), `recordStep` is a no-op and all
   *   metrics report `0`/`0.0`.
   */
  constructor(public readonly enabled: boolean = false) {}

  /**
   * Record the outcome of one step (no-op when disabled).
   *
   * @param success Whether the step succeeded.
   * @param options Optional step label and error description.
   */
  recordStep(success: boolean, options: RecordStepOptions = {}): void {
    if (!this.enabled) {
      return;
    }
    this.stepResults.push({
      success,
      name: options.name,
      error: options.error,
    });
  }

  /** Number of recorded steps. */
  get totalSteps(): number {
    return this.stepResults.length;
  }

  /** Number of recorded steps that failed. */
  get failedSteps(): number {
    return this.stepResults.filter((r) => !r.success).length;
  }

  /**
   * Per-step error rate `p_a` = failedSteps / totalSteps.
   *
   * @returns `0.0` when no steps have been recorded.
   */
  perStepErrorRate(): number {
    if (this.totalSteps === 0) {
      return 0.0;
    }
    return this.failedSteps / this.totalSteps;
  }

  /**
   * Probability of at least one failure over `steps` steps.
   *
   * `P_error = 1 - (1 - p_a) ** n` where `n` is `steps` if given, otherwise the
   * number of recorded steps. Models error compounding: independent steps each
   * succeed with probability `1 - p_a`, so the run succeeds only if all `n`
   * succeed.
   *
   * @param steps Project the compounding over this many steps. Defaults to the
   *   number of recorded steps (observed cumulative probability).
   * @returns A probability in `[0.0, 1.0]`. Returns `0.0` if `p_a` is 0 or
   *   `n <= 0`.
   */
  cumulativeFailureProbability(steps?: number): number {
    const n = steps === undefined ? this.totalSteps : steps;
    if (n <= 0) {
      return 0.0;
    }
    const pA = this.perStepErrorRate();
    return 1.0 - (1.0 - pA) ** n;
  }

  /** Clear all recorded step results. */
  reset(): void {
    this.stepResults.length = 0;
  }
}
