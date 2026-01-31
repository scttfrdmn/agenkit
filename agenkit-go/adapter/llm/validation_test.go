package llm

import (
	"testing"
)

// TestWithTemperatureValidation tests temperature parameter validation
func TestWithTemperatureValidation(t *testing.T) {
	tests := []struct {
		name        string
		temperature float64
		shouldPanic bool
		errorMsg    string
	}{
		{
			name:        "valid temperature 0.0",
			temperature: 0.0,
			shouldPanic: false,
		},
		{
			name:        "valid temperature 1.0",
			temperature: 1.0,
			shouldPanic: false,
		},
		{
			name:        "valid temperature 2.0",
			temperature: 2.0,
			shouldPanic: false,
		},
		{
			name:        "invalid temperature -0.5",
			temperature: -0.5,
			shouldPanic: true,
			errorMsg:    "temperature must be between 0 and 2",
		},
		{
			name:        "invalid temperature 3.0",
			temperature: 3.0,
			shouldPanic: true,
			errorMsg:    "temperature must be between 0 and 2",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.shouldPanic {
				defer func() {
					if r := recover(); r == nil {
						t.Errorf("WithTemperature(%v) should have panicked", tt.temperature)
					}
				}()
			}
			_ = WithTemperature(tt.temperature)
		})
	}
}

// TestWithMaxTokensValidation tests max_tokens parameter validation
func TestWithMaxTokensValidation(t *testing.T) {
	tests := []struct {
		name        string
		maxTokens   int
		shouldPanic bool
		errorMsg    string
	}{
		{
			name:        "valid max_tokens 1",
			maxTokens:   1,
			shouldPanic: false,
		},
		{
			name:        "valid max_tokens 100",
			maxTokens:   100,
			shouldPanic: false,
		},
		{
			name:        "valid max_tokens 4096",
			maxTokens:   4096,
			shouldPanic: false,
		},
		{
			name:        "invalid max_tokens 0",
			maxTokens:   0,
			shouldPanic: true,
			errorMsg:    "max_tokens must be positive",
		},
		{
			name:        "invalid max_tokens -10",
			maxTokens:   -10,
			shouldPanic: true,
			errorMsg:    "max_tokens must be positive",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.shouldPanic {
				defer func() {
					if r := recover(); r == nil {
						t.Errorf("WithMaxTokens(%v) should have panicked", tt.maxTokens)
					}
				}()
			}
			_ = WithMaxTokens(tt.maxTokens)
		})
	}
}

// TestWithTopPValidation tests top_p parameter validation
func TestWithTopPValidation(t *testing.T) {
	tests := []struct {
		name        string
		topP        float64
		shouldPanic bool
		errorMsg    string
	}{
		{
			name:        "valid top_p 0.0",
			topP:        0.0,
			shouldPanic: false,
		},
		{
			name:        "valid top_p 0.5",
			topP:        0.5,
			shouldPanic: false,
		},
		{
			name:        "valid top_p 1.0",
			topP:        1.0,
			shouldPanic: false,
		},
		{
			name:        "invalid top_p -0.1",
			topP:        -0.1,
			shouldPanic: true,
			errorMsg:    "top_p must be between 0 and 1",
		},
		{
			name:        "invalid top_p 1.5",
			topP:        1.5,
			shouldPanic: true,
			errorMsg:    "top_p must be between 0 and 1",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.shouldPanic {
				defer func() {
					if r := recover(); r == nil {
						t.Errorf("WithTopP(%v) should have panicked", tt.topP)
					}
				}()
			}
			_ = WithTopP(tt.topP)
		})
	}
}

// TestValidParameterCombinations tests that valid parameter combinations work
func TestValidParameterCombinations(t *testing.T) {
	// Should not panic with all valid parameters
	opts := BuildCallOptions(
		WithTemperature(0.7),
		WithMaxTokens(1024),
		WithTopP(0.9),
	)

	if opts.Temperature == nil || *opts.Temperature != 0.7 {
		t.Errorf("Temperature not set correctly")
	}
	if opts.MaxTokens == nil || *opts.MaxTokens != 1024 {
		t.Errorf("MaxTokens not set correctly")
	}
	if opts.TopP == nil || *opts.TopP != 0.9 {
		t.Errorf("TopP not set correctly")
	}
}

// TestBoundaryValues tests edge cases at boundaries
func TestBoundaryValues(t *testing.T) {
	t.Run("temperature exactly 0", func(t *testing.T) {
		opt := WithTemperature(0.0)
		opts := &CallOptions{}
		opt(opts)
		if opts.Temperature == nil || *opts.Temperature != 0.0 {
			t.Error("Temperature 0.0 should be valid")
		}
	})

	t.Run("temperature exactly 2", func(t *testing.T) {
		opt := WithTemperature(2.0)
		opts := &CallOptions{}
		opt(opts)
		if opts.Temperature == nil || *opts.Temperature != 2.0 {
			t.Error("Temperature 2.0 should be valid")
		}
	})

	t.Run("max_tokens exactly 1", func(t *testing.T) {
		opt := WithMaxTokens(1)
		opts := &CallOptions{}
		opt(opts)
		if opts.MaxTokens == nil || *opts.MaxTokens != 1 {
			t.Error("MaxTokens 1 should be valid")
		}
	})

	t.Run("top_p exactly 0", func(t *testing.T) {
		opt := WithTopP(0.0)
		opts := &CallOptions{}
		opt(opts)
		if opts.TopP == nil || *opts.TopP != 0.0 {
			t.Error("TopP 0.0 should be valid")
		}
	})

	t.Run("top_p exactly 1", func(t *testing.T) {
		opt := WithTopP(1.0)
		opts := &CallOptions{}
		opt(opts)
		if opts.TopP == nil || *opts.TopP != 1.0 {
			t.Error("TopP 1.0 should be valid")
		}
	})
}

// TestWithFrequencyPenaltyValidation tests frequency_penalty parameter validation
func TestWithFrequencyPenaltyValidation(t *testing.T) {
	tests := []struct {
		name             string
		frequencyPenalty float64
		shouldPanic      bool
		errorMsg         string
	}{
		{
			name:             "valid frequency_penalty -2.0",
			frequencyPenalty: -2.0,
			shouldPanic:      false,
		},
		{
			name:             "valid frequency_penalty 0.0",
			frequencyPenalty: 0.0,
			shouldPanic:      false,
		},
		{
			name:             "valid frequency_penalty 2.0",
			frequencyPenalty: 2.0,
			shouldPanic:      false,
		},
		{
			name:             "invalid frequency_penalty -2.1",
			frequencyPenalty: -2.1,
			shouldPanic:      true,
			errorMsg:         "frequency_penalty must be between -2 and 2",
		},
		{
			name:             "invalid frequency_penalty 2.5",
			frequencyPenalty: 2.5,
			shouldPanic:      true,
			errorMsg:         "frequency_penalty must be between -2 and 2",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.shouldPanic {
				defer func() {
					if r := recover(); r == nil {
						t.Errorf("WithFrequencyPenalty(%v) should have panicked", tt.frequencyPenalty)
					}
				}()
			}
			_ = WithFrequencyPenalty(tt.frequencyPenalty)
		})
	}
}

// TestWithPresencePenaltyValidation tests presence_penalty parameter validation
func TestWithPresencePenaltyValidation(t *testing.T) {
	tests := []struct {
		name            string
		presencePenalty float64
		shouldPanic     bool
		errorMsg        string
	}{
		{
			name:            "valid presence_penalty -2.0",
			presencePenalty: -2.0,
			shouldPanic:     false,
		},
		{
			name:            "valid presence_penalty 0.0",
			presencePenalty: 0.0,
			shouldPanic:     false,
		},
		{
			name:            "valid presence_penalty 2.0",
			presencePenalty: 2.0,
			shouldPanic:     false,
		},
		{
			name:            "invalid presence_penalty -2.1",
			presencePenalty: -2.1,
			shouldPanic:     true,
			errorMsg:        "presence_penalty must be between -2 and 2",
		},
		{
			name:            "invalid presence_penalty 2.5",
			presencePenalty: 2.5,
			shouldPanic:     true,
			errorMsg:        "presence_penalty must be between -2 and 2",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.shouldPanic {
				defer func() {
					if r := recover(); r == nil {
						t.Errorf("WithPresencePenalty(%v) should have panicked", tt.presencePenalty)
					}
				}()
			}
			_ = WithPresencePenalty(tt.presencePenalty)
		})
	}
}
