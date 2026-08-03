package agenkit

import (
	"context"
	"fmt"
)

// CallOptions holds per-call inference options for an LLM call.
//
// These live in the core package rather than in adapter/llm because the patterns
// need to name them in an interface. adapter/llm transitively pulls in the AWS SDK
// (via the Bedrock adapter, ~20 packages), and making every importer of a pattern
// depend on a cloud SDK is not acceptable — patterns depends on this package alone.
//
// adapter/llm keeps aliases (llm.CallOptions, llm.CallOption, llm.WithTemperature,
// ...) so existing code is unaffected.
//
// Pointer fields carry the distinction between "unset" and "set to the zero value":
// nil means the caller did not ask, so the option is omitted from the provider
// request entirely rather than sent as 0. A Temperature of 0.0 is a real request
// (greedy decoding) and must still be forwarded. Forwarding unset options as zero
// would make every call through a wrapper override whatever the adapter or provider
// was configured with.
type CallOptions struct {
	// Temperature is the sampling temperature (0.0-2.0). Nil means unset.
	Temperature *float64
	// MaxTokens is the maximum number of tokens to generate. Nil means unset.
	MaxTokens *int
	// TopP is the nucleus sampling parameter (0.0-1.0). Nil means unset.
	TopP *float64

	// Extra holds provider-specific options passed through verbatim.
	Extra map[string]interface{}
}

// IsEmpty reports whether no option is set.
//
// Callers use this to skip the options path entirely rather than send an empty
// options object, so a client that cannot honour options is not handed one.
func (o *CallOptions) IsEmpty() bool {
	if o == nil {
		return true
	}
	return o.Temperature == nil && o.MaxTokens == nil && o.TopP == nil && len(o.Extra) == 0
}

// CallOption is a functional option for configuring an LLM call.
type CallOption func(*CallOptions)

// WithTemperature sets the sampling temperature (0.0-2.0).
// Panics if temperature is outside the valid range.
func WithTemperature(temperature float64) CallOption {
	if temperature < 0.0 || temperature > 2.0 {
		panic(fmt.Sprintf("temperature must be between 0 and 2, got %v", temperature))
	}
	return func(opts *CallOptions) {
		opts.Temperature = &temperature
	}
}

// WithMaxTokens sets the maximum number of tokens to generate.
// Panics if maxTokens is not positive.
func WithMaxTokens(maxTokens int) CallOption {
	if maxTokens <= 0 {
		panic(fmt.Sprintf("max_tokens must be positive, got %d", maxTokens))
	}
	return func(opts *CallOptions) {
		opts.MaxTokens = &maxTokens
	}
}

// WithTopP sets the nucleus sampling parameter (0.0-1.0).
// Panics if topP is outside the valid range.
func WithTopP(topP float64) CallOption {
	if topP < 0.0 || topP > 1.0 {
		panic(fmt.Sprintf("top_p must be between 0 and 1, got %v", topP))
	}
	return func(opts *CallOptions) {
		opts.TopP = &topP
	}
}

// WithFrequencyPenalty sets the frequency penalty (-2.0 to 2.0).
// Panics if frequencyPenalty is outside the valid range.
func WithFrequencyPenalty(frequencyPenalty float64) CallOption {
	if frequencyPenalty < -2.0 || frequencyPenalty > 2.0 {
		panic(fmt.Sprintf("frequency_penalty must be between -2 and 2, got %v", frequencyPenalty))
	}
	return func(opts *CallOptions) {
		if opts.Extra == nil {
			opts.Extra = make(map[string]interface{})
		}
		opts.Extra["frequency_penalty"] = frequencyPenalty
	}
}

// WithPresencePenalty sets the presence penalty (-2.0 to 2.0).
// Panics if presencePenalty is outside the valid range.
func WithPresencePenalty(presencePenalty float64) CallOption {
	if presencePenalty < -2.0 || presencePenalty > 2.0 {
		panic(fmt.Sprintf("presence_penalty must be between -2 and 2, got %v", presencePenalty))
	}
	return func(opts *CallOptions) {
		if opts.Extra == nil {
			opts.Extra = make(map[string]interface{})
		}
		opts.Extra["presence_penalty"] = presencePenalty
	}
}

// WithExtra adds a provider-specific option.
func WithExtra(key string, value interface{}) CallOption {
	return func(opts *CallOptions) {
		if opts.Extra == nil {
			opts.Extra = make(map[string]interface{})
		}
		opts.Extra[key] = value
	}
}

// BuildCallOptions creates CallOptions from functional options.
func BuildCallOptions(opts ...CallOption) *CallOptions {
	options := &CallOptions{
		Extra: make(map[string]interface{}),
	}
	for _, opt := range opts {
		opt(options)
	}
	return options
}

// SupportsOptions reports whether an agent honours per-call options.
//
// A caller that needs its options to actually take effect should check this
// rather than assume, since a plain Agent has no way to apply them. Exposed as a
// helper so the type assertion is spelled one way everywhere and callers do not
// each reinvent it.
func SupportsOptions(agent Agent) bool {
	_, ok := agent.(OptionsAgent)
	return ok
}

// ProcessWithOptions forwards a message to an agent, applying options if it can.
//
// The single place that resolves "can this agent take options", so the pattern is
// not re-derived at each of the wrapper call sites in techniques/reasoning. When
// the agent is not an OptionsAgent the options are dropped — deliberately, since
// a plain Agent has nowhere to put them — so a caller that needs to know whether
// that happened must check SupportsOptions first. That is exactly why the
// reasoning techniques expose a TemperatureApplied accessor (#801).
//
// Passing no options skips the assertion entirely: an empty options set is
// indistinguishable from not asking, and an OptionsAgent should not be handed an
// empty CallOptions just because the helper was used.
func ProcessWithOptions(
	ctx context.Context,
	agent Agent,
	message *Message,
	opts ...CallOption,
) (*Message, error) {
	if len(opts) == 0 {
		return agent.Process(ctx, message)
	}
	if oa, ok := agent.(OptionsAgent); ok {
		return oa.ProcessWith(ctx, message, opts...)
	}
	return agent.Process(ctx, message)
}
