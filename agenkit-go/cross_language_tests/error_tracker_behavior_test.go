package tests

import (
	"encoding/json"
	"math"
	"os"
	"path/filepath"
	"strconv"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/evaluation"
	"github.com/stretchr/testify/require"
)

// ErrorTrackerTestCase represents an error tracker test case from fixtures.
type ErrorTrackerTestCase struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	Steps     []bool `json:"steps,omitempty"`
	StepsSpec *struct {
		Fail    int `json:"fail"`
		Success int `json:"success"`
	} `json:"steps_spec,omitempty"`
	Expected struct {
		TotalSteps                        int                `json:"total_steps"`
		FailedSteps                       int                `json:"failed_steps"`
		PerStepErrorRate                  float64            `json:"per_step_error_rate"`
		CumulativeFailureProbabilityObs   *float64           `json:"cumulative_failure_probability_observed,omitempty"`
		CumulativeFailureProbabilitySteps map[string]float64 `json:"cumulative_failure_probability_steps"`
		Tolerance                         *float64           `json:"tolerance,omitempty"`
	} `json:"expected"`
}

// ErrorTrackerFixtures represents the error tracker test fixtures file.
type ErrorTrackerFixtures struct {
	Version     string                 `json:"version"`
	Description string                 `json:"description"`
	TestCases   []ErrorTrackerTestCase `json:"test_cases"`
}

func loadErrorTrackerFixtures(t *testing.T) *ErrorTrackerFixtures {
	fixturesPath := filepath.Join("..", "..", "tests", "cross_language", "fixtures", "error_tracker_behavior.json")
	data, err := os.ReadFile(fixturesPath)
	require.NoError(t, err, "Failed to read fixtures file")

	var fixtures ErrorTrackerFixtures
	err = json.Unmarshal(data, &fixtures)
	require.NoError(t, err, "Failed to parse fixtures JSON")

	return &fixtures
}

// buildErrorTrackerSteps expands a test case's steps or steps_spec into a
// concrete sequence of success/failure outcomes.
func buildErrorTrackerSteps(tc *ErrorTrackerTestCase) []bool {
	if tc.Steps != nil {
		return tc.Steps
	}
	steps := make([]bool, 0, tc.StepsSpec.Fail+tc.StepsSpec.Success)
	for i := 0; i < tc.StepsSpec.Fail; i++ {
		steps = append(steps, false)
	}
	for i := 0; i < tc.StepsSpec.Success; i++ {
		steps = append(steps, true)
	}
	return steps
}

func TestErrorTrackerBehavior(t *testing.T) {
	fixtures := loadErrorTrackerFixtures(t)
	require.NotEmpty(t, fixtures.TestCases)

	for _, tc := range fixtures.TestCases {
		tc := tc
		t.Run(tc.ID, func(t *testing.T) {
			tolerance := 1e-6
			if tc.Expected.Tolerance != nil {
				tolerance = *tc.Expected.Tolerance
			}

			tracker := &evaluation.ErrorTracker{Enabled: true}
			for _, success := range buildErrorTrackerSteps(&tc) {
				tracker.RecordStep(success)
			}

			require.Equal(t, tc.Expected.TotalSteps, tracker.TotalSteps())
			require.Equal(t, tc.Expected.FailedSteps, tracker.FailedSteps())
			require.InDelta(t, tc.Expected.PerStepErrorRate, tracker.PerStepErrorRate(), tolerance)

			if tc.Expected.CumulativeFailureProbabilityObs != nil {
				require.InDelta(t, *tc.Expected.CumulativeFailureProbabilityObs, tracker.CumulativeFailureProbability(), tolerance)
			}

			for stepsStr, expectedP := range tc.Expected.CumulativeFailureProbabilitySteps {
				n, err := strconv.Atoi(stepsStr)
				require.NoError(t, err)
				got := tracker.CumulativeFailureProbabilityOver(n)
				require.InDelta(t, expectedP, got, tolerance,
					"n=%d: expected %v, got %v (diff %v)", n, expectedP, got, math.Abs(expectedP-got))
			}
		})
	}
}
