/**
 * Timing tolerances for tests that assert on real wall-clock elapsed time.
 *
 * Node's `setTimeout` can fire *before* its deadline. libuv compares a timer's
 * deadline against a loop time it caches once per iteration, so a timer whose
 * deadline falls inside the current iteration fires early. Measured on an idle
 * event loop, `await new Promise(r => setTimeout(r, 30))` reports 29ms with
 * `Date.now()` roughly 1 run in 200, and `performance.now()` confirms genuine
 * undershoot of up to ~0.9ms — so this is the timer itself, not `Date.now()`'s
 * integer-millisecond truncation.
 *
 * The consequence is that `expect(elapsed).toBeGreaterThanOrEqual(delayMs)` is
 * not a sound assertion, however large the delay. Several such assertions
 * existed here and flaked at low single-digit rates; nobody noticed because a
 * hanging test in the Anthropic adapter suite meant CI killed the whole run at
 * `timeout 300` and `|| true` swallowed the result (#658).
 */

/**
 * Slack allowed when asserting that at least a given delay elapsed.
 *
 * 5ms rather than the ~1ms observed: the margin also absorbs timer coalescing
 * under a loaded event loop, and it matches the tolerance already used ad hoc
 * elsewhere in these suites (e.g. `delay - 5`). Tests using it are checking
 * that latency was injected at all, not measuring it precisely.
 */
export const TIMER_SLOP_MS = 5;

/**
 * Lower bound to assert against when a test expects `expectedMs` to have
 * elapsed, tolerating early timer firing.
 *
 * Use as `expect(elapsed).toBeGreaterThanOrEqual(atLeastMs(30))` so the
 * assertion — and the fact that it is deliberately tolerant — stays visible at
 * the call site.
 *
 * @param expectedMs Delay that was requested
 * @returns `expectedMs` reduced by the timer slop, floored at 0
 */
export function atLeastMs(expectedMs: number): number {
  return Math.max(0, expectedMs - TIMER_SLOP_MS);
}
