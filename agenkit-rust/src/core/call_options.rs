//! Per-call inference options.
//!
//! The channel a caller uses to influence *how* one call runs, as opposed to
//! [`Message`], which carries *what* the call is about. It exists because wrappers
//! need to vary inference settings per invocation of an agent they did not
//! construct: `SelfConsistencyAgent` samples the same prompt N times and takes a
//! majority vote, so sample diversity *is* the technique, and temperature is the
//! knob that produces it (#801).

use super::{Agent, AgentError, Message};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

/// Per-call inference options for a single agent invocation.
///
/// Passed via the optional [`OptionsAgent`] capability rather than by widening
/// [`Agent::process`]: adding a parameter there would touch every agent
/// implementation in the toolkit — roughly 500 across the nine cores, every one of
/// Rust's at compile time — to add something most agents have nothing to do with.
///
/// Every field is optional and `None` means "unset", not a default. This is the
/// distinction that matters: an agent must be able to tell "the caller did not ask
/// for a temperature" from "the caller asked for 0.0". Forwarding an unset option
/// as its zero value would make every call through a wrapper silently override
/// whatever the agent or provider was configured with, and a `temperature` of 0.0
/// (greedy decoding) is a real request that must still be forwarded.
///
/// The fields are public and `Default` is derived, so a struct literal works the
/// same way the `*Config` types in this crate do. That path skips the builders'
/// range checks, so anything that accepts a caller-supplied `CallOptions` should
/// call [`CallOptions::validate`].
///
/// # Example
/// ```
/// use agenkit::core::CallOptions;
///
/// let options = CallOptions::new().with_temperature(0.9).with_max_tokens(256);
/// assert_eq!(options.temperature, Some(0.9));
///
/// // Struct-literal form, for consistency with the crate's config types.
/// let options = CallOptions {
///     temperature: Some(0.0), // greedy decoding — a request, not "unset"
///     ..Default::default()
/// };
/// assert!(!options.is_empty());
/// ```
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct CallOptions {
    /// Sampling temperature, 0.0-2.0. Higher is more random. `None` means unset.
    pub temperature: Option<f64>,

    /// Maximum tokens to generate. Must be positive. `None` means unset.
    pub max_tokens: Option<u32>,

    /// Nucleus sampling probability mass, 0.0-1.0. `None` means unset.
    pub top_p: Option<f64>,

    /// Provider-side sampling seed, for reproducible sampling where the provider
    /// supports it. `None` means unset.
    pub seed: Option<u64>,

    /// Sequences that end generation. `None` means unset.
    pub stop: Option<Vec<String>>,

    /// Provider-specific options with no cross-provider meaning, passed through
    /// verbatim. Kept separate from the named fields so a typo in a portable
    /// option is a compile error rather than a silently ignored key.
    #[serde(default, skip_serializing_if = "Map::is_empty")]
    pub extra: Map<String, Value>,
}

impl CallOptions {
    /// Create an empty set of options.
    pub fn new() -> Self {
        Self::default()
    }

    /// Set the sampling temperature (0.0-2.0).
    ///
    /// # Panics
    /// If `temperature` is outside 0.0-2.0 or is NaN. Panicking here rather than
    /// deferring to [`validate`](Self::validate) makes a bad value fail at the call
    /// site that set it, where the fix is, instead of several layers down. This
    /// mirrors the `panic!` in [`crate::adapters`] constructors for the same class
    /// of invalid sampling parameter.
    pub fn with_temperature(mut self, temperature: f64) -> Self {
        if !(0.0..=2.0).contains(&temperature) {
            panic!("temperature must be between 0 and 2, got {}", temperature);
        }
        self.temperature = Some(temperature);
        self
    }

    /// Set the maximum number of tokens to generate.
    ///
    /// # Panics
    /// If `max_tokens` is zero.
    pub fn with_max_tokens(mut self, max_tokens: u32) -> Self {
        if max_tokens == 0 {
            panic!("max_tokens must be positive, got {}", max_tokens);
        }
        self.max_tokens = Some(max_tokens);
        self
    }

    /// Set the nucleus sampling parameter (0.0-1.0).
    ///
    /// # Panics
    /// If `top_p` is outside 0.0-1.0 or is NaN.
    pub fn with_top_p(mut self, top_p: f64) -> Self {
        if !(0.0..=1.0).contains(&top_p) {
            panic!("top_p must be between 0 and 1, got {}", top_p);
        }
        self.top_p = Some(top_p);
        self
    }

    /// Set the provider-side sampling seed.
    pub fn with_seed(mut self, seed: u64) -> Self {
        self.seed = Some(seed);
        self
    }

    /// Set the sequences that end generation.
    pub fn with_stop(mut self, stop: Vec<String>) -> Self {
        self.stop = Some(stop);
        self
    }

    /// Add a provider-specific option.
    pub fn with_extra(mut self, key: impl Into<String>, value: Value) -> Self {
        self.extra.insert(key.into(), value);
        self
    }

    /// Validate every set option against its documented range.
    ///
    /// The builders check as they go, so this only matters for options built by
    /// struct literal or deserialized from a wire format. Anything that accepts a
    /// caller-supplied `CallOptions` should call it, and should reuse it rather
    /// than re-spelling the bounds, so the two spellings cannot drift apart.
    ///
    /// # Errors
    /// [`AgentError::InvalidInput`] if any option is outside its range. A NaN
    /// `temperature` or `top_p` is rejected: it is outside every range.
    pub fn validate(&self) -> Result<(), AgentError> {
        if let Some(temperature) = self.temperature {
            if !(0.0..=2.0).contains(&temperature) {
                return Err(AgentError::InvalidInput(format!(
                    "temperature must be between 0 and 2, got {}",
                    temperature
                )));
            }
        }

        if let Some(max_tokens) = self.max_tokens {
            if max_tokens == 0 {
                return Err(AgentError::InvalidInput(
                    "max_tokens must be positive, got 0".to_string(),
                ));
            }
        }

        if let Some(top_p) = self.top_p {
            if !(0.0..=1.0).contains(&top_p) {
                return Err(AgentError::InvalidInput(format!(
                    "top_p must be between 0 and 1, got {}",
                    top_p
                )));
            }
        }

        Ok(())
    }

    /// Report whether no option is set.
    ///
    /// Lets a caller skip the [`OptionsAgent`] path entirely when it has nothing to
    /// say, rather than handing an agent an all-`None` options object. A
    /// `temperature` of `Some(0.0)` is *not* empty — a falsy-but-present value is a
    /// request that must survive this check and reach the provider.
    pub fn is_empty(&self) -> bool {
        self.temperature.is_none()
            && self.max_tokens.is_none()
            && self.top_p.is_none()
            && self.seed.is_none()
            && self.stop.is_none()
            && self.extra.is_empty()
    }

    /// Render as provider request parameters.
    ///
    /// Unset fields are omitted rather than emitted as `null`, so an option the
    /// caller never set cannot override the provider's own default. Keys are the
    /// snake_case names every adapter in this crate already uses.
    pub fn to_params(&self) -> Map<String, Value> {
        let mut params = Map::new();

        if let Some(temperature) = self.temperature {
            params.insert("temperature".to_string(), Value::from(temperature));
        }
        if let Some(max_tokens) = self.max_tokens {
            params.insert("max_tokens".to_string(), Value::from(max_tokens));
        }
        if let Some(top_p) = self.top_p {
            params.insert("top_p".to_string(), Value::from(top_p));
        }
        if let Some(seed) = self.seed {
            params.insert("seed".to_string(), Value::from(seed));
        }
        if let Some(stop) = &self.stop {
            params.insert("stop".to_string(), Value::from(stop.clone()));
        }
        for (key, value) in &self.extra {
            params.insert(key.clone(), value.clone());
        }

        params
    }

    /// Merge `overrides` over `self`, with `overrides` winning where it is set.
    ///
    /// Merged field by field rather than by replacing whole structs: a `None` in
    /// `overrides` means "did not ask", not "clear it", so it must leave `self`'s
    /// value in place. That is the common shape in practice — an `Option` variable
    /// forwarded straight into the struct — and collapsing the two meanings is the
    /// same silent-wrong failure as forwarding an unset option as zero.
    ///
    /// `extra` merges key by key, so a provider-specific option set by one side
    /// survives the other setting a different one.
    pub fn merge(&self, overrides: &CallOptions) -> CallOptions {
        let mut merged = self.clone();

        if overrides.temperature.is_some() {
            merged.temperature = overrides.temperature;
        }
        if overrides.max_tokens.is_some() {
            merged.max_tokens = overrides.max_tokens;
        }
        if overrides.top_p.is_some() {
            merged.top_p = overrides.top_p;
        }
        if overrides.seed.is_some() {
            merged.seed = overrides.seed;
        }
        if let Some(stop) = &overrides.stop {
            merged.stop = Some(stop.clone());
        }
        for (key, value) in &overrides.extra {
            merged.extra.insert(key.clone(), value.clone());
        }

        merged
    }
}

/// Extension trait for agents that honour per-call inference options.
///
/// An optional capability, in the same spirit as [`Agent::process_stream`]: the
/// core contract stays `process(message)`, and an agent that can apply per-call
/// options advertises that by implementing this trait *and* returning `Some(self)`
/// from [`Agent::as_options_agent`].
///
/// Both halves are needed because Rust cannot ask a `dyn Agent` whether its
/// concrete type implements another trait — there is no equivalent of Go's type
/// assertion or TypeScript's `typeof agent.processWith === 'function'`. Coupling
/// the two through `as_options_agent` is what keeps them from drifting: the body
/// `Some(self)` does not compile unless the type really does implement
/// `OptionsAgent`, so the capability cannot be advertised falsely.
///
/// The rejected alternative was a `process_with` default method on `Agent` that
/// discards its options. That compiles for every existing agent, which is the
/// appeal, but it makes an unhonoured option indistinguishable from an honoured
/// one — the silent drop this was filed about.
///
/// # Example
/// ```
/// use agenkit::core::{Agent, AgentError, CallOptions, Message, OptionsAgent};
/// use async_trait::async_trait;
///
/// struct Tunable;
///
/// #[async_trait]
/// impl Agent for Tunable {
///     fn name(&self) -> &str {
///         "tunable"
///     }
///
///     async fn process(&self, message: Message) -> Result<Message, AgentError> {
///         self.process_with(message, &CallOptions::new()).await
///     }
///
///     fn as_options_agent(&self) -> Option<&dyn OptionsAgent> {
///         Some(self)
///     }
/// }
///
/// #[async_trait]
/// impl OptionsAgent for Tunable {
///     async fn process_with(
///         &self,
///         _message: Message,
///         options: &CallOptions,
///     ) -> Result<Message, AgentError> {
///         // An unset field must leave the provider setting alone.
///         let temperature = options.temperature.unwrap_or(0.7);
///         Ok(Message::with_text("assistant", format!("temp={}", temperature)))
///     }
/// }
/// ```
#[async_trait::async_trait]
pub trait OptionsAgent: Agent {
    /// Process a message with per-call inference options.
    ///
    /// An unset (`None`) field must be omitted from the downstream call rather
    /// than forwarded as a zero value, so an option the caller did not set does
    /// not override whatever the agent or provider was configured with. A
    /// `temperature` of `Some(0.0)` is a real request and must still be forwarded.
    async fn process_with(
        &self,
        message: Message,
        options: &CallOptions,
    ) -> Result<Message, AgentError>;
}

/// Report whether an agent honours per-call options.
///
/// A caller that needs its options to actually take effect should check this
/// rather than assume, since a plain [`Agent`] has nowhere to put them. Exposed as
/// a helper so the check is spelled one way everywhere.
pub fn supports_options(agent: &dyn Agent) -> bool {
    agent.as_options_agent().is_some()
}

/// Forward a message to an agent, applying options if it can.
///
/// The single place that resolves "can this agent take options", so the pattern is
/// not re-derived at each wrapper call site. When the agent is not an
/// [`OptionsAgent`] the options are dropped — deliberately, since a plain [`Agent`]
/// has nowhere to put them — so a caller that needs to know whether that happened
/// must check [`supports_options`] first. That is exactly why the reasoning
/// techniques expose a `temperature_applied` accessor (#801).
///
/// Empty options skip the capability check entirely: an empty set is
/// indistinguishable from not asking, and an `OptionsAgent` should not be handed an
/// empty `CallOptions` just because this helper was used.
pub async fn process_with_options(
    agent: &dyn Agent,
    message: Message,
    options: &CallOptions,
) -> Result<Message, AgentError> {
    if options.is_empty() {
        return agent.process(message).await;
    }
    match agent.as_options_agent() {
        Some(options_agent) => options_agent.process_with(message, options).await,
        None => agent.process(message).await,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use async_trait::async_trait;
    use std::sync::Mutex;

    /// An agent that records which path it was entered by and what it carried.
    ///
    /// Recording the path matters as much as recording the options: the bug guarded
    /// against is a caller that takes the plain `process` path and silently drops
    /// what it was handed, which a test inspecting only the returned message cannot
    /// distinguish from success.
    struct RecordingAgent {
        process_calls: Mutex<usize>,
        process_with_calls: Mutex<usize>,
        last_options: Mutex<Option<CallOptions>>,
    }

    impl RecordingAgent {
        fn new() -> Self {
            Self {
                process_calls: Mutex::new(0),
                process_with_calls: Mutex::new(0),
                last_options: Mutex::new(None),
            }
        }
    }

    #[async_trait]
    impl Agent for RecordingAgent {
        fn name(&self) -> &str {
            "recording"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            *self.process_calls.lock().unwrap() += 1;
            Ok(Message::with_text("assistant", "plain"))
        }

        fn as_options_agent(&self) -> Option<&dyn OptionsAgent> {
            Some(self)
        }
    }

    #[async_trait]
    impl OptionsAgent for RecordingAgent {
        async fn process_with(
            &self,
            _message: Message,
            options: &CallOptions,
        ) -> Result<Message, AgentError> {
            *self.process_with_calls.lock().unwrap() += 1;
            *self.last_options.lock().unwrap() = Some(options.clone());
            Ok(Message::with_text("assistant", "with-options"))
        }
    }

    /// An agent with no options capability.
    struct PlainAgent {
        process_calls: Mutex<usize>,
    }

    #[async_trait]
    impl Agent for PlainAgent {
        fn name(&self) -> &str {
            "plain"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            *self.process_calls.lock().unwrap() += 1;
            Ok(Message::with_text("assistant", "plain"))
        }
    }

    #[test]
    fn test_new_is_empty() {
        assert!(CallOptions::new().is_empty());
        assert!(CallOptions::default().is_empty());
    }

    #[test]
    fn test_temperature_zero_is_set() {
        // The whole point of "None means unset": a falsy-but-present value is a
        // request that must survive the empty check and reach the provider.
        let options = CallOptions::new().with_temperature(0.0);
        assert_eq!(options.temperature, Some(0.0));
        assert!(!options.is_empty());
    }

    #[test]
    fn test_each_field_makes_it_non_empty() {
        assert!(!CallOptions::new().with_temperature(0.7).is_empty());
        assert!(!CallOptions::new().with_max_tokens(32).is_empty());
        assert!(!CallOptions::new().with_top_p(0.9).is_empty());
        assert!(!CallOptions::new().with_seed(42).is_empty());
        assert!(!CallOptions::new()
            .with_stop(vec!["\n".to_string()])
            .is_empty());
        assert!(!CallOptions::new()
            .with_extra("logit_bias", Value::Null)
            .is_empty());
    }

    #[test]
    fn test_builders_accept_boundaries() {
        let options = CallOptions::new()
            .with_temperature(2.0)
            .with_top_p(1.0)
            .with_max_tokens(1)
            .with_seed(0);
        assert!(options.validate().is_ok());
    }

    #[test]
    #[should_panic(expected = "temperature must be between 0 and 2")]
    fn test_with_temperature_rejects_above_range() {
        CallOptions::new().with_temperature(2.1);
    }

    #[test]
    #[should_panic(expected = "temperature must be between 0 and 2")]
    fn test_with_temperature_rejects_below_range() {
        CallOptions::new().with_temperature(-0.1);
    }

    #[test]
    #[should_panic(expected = "temperature must be between 0 and 2")]
    fn test_with_temperature_rejects_nan() {
        CallOptions::new().with_temperature(f64::NAN);
    }

    #[test]
    #[should_panic(expected = "max_tokens must be positive")]
    fn test_with_max_tokens_rejects_zero() {
        CallOptions::new().with_max_tokens(0);
    }

    #[test]
    #[should_panic(expected = "top_p must be between 0 and 1")]
    fn test_with_top_p_rejects_above_range() {
        CallOptions::new().with_top_p(1.1);
    }

    #[test]
    fn test_validate_accepts_temperature_zero() {
        // Greedy decoding. Validation must not confuse the zero value with "unset".
        let options = CallOptions {
            temperature: Some(0.0),
            ..Default::default()
        };
        assert!(options.validate().is_ok());
    }

    #[test]
    fn test_validate_rejects_struct_literal_out_of_range() {
        // The struct-literal path skips the builders, so validate() is the only
        // thing standing between a bad value and the provider.
        for temperature in [-0.1, 2.1, f64::NAN] {
            let options = CallOptions {
                temperature: Some(temperature),
                ..Default::default()
            };
            let err = options.validate().unwrap_err();
            assert!(
                err.to_string()
                    .contains("temperature must be between 0 and 2"),
                "unexpected error for {}: {}",
                temperature,
                err
            );
        }
    }

    #[test]
    fn test_validate_rejects_zero_max_tokens_and_bad_top_p() {
        let err = CallOptions {
            max_tokens: Some(0),
            ..Default::default()
        }
        .validate()
        .unwrap_err();
        assert!(err.to_string().contains("max_tokens must be positive"));

        let err = CallOptions {
            top_p: Some(1.1),
            ..Default::default()
        }
        .validate()
        .unwrap_err();
        assert!(err.to_string().contains("top_p must be between 0 and 1"));
    }

    #[test]
    fn test_to_params_omits_unset_fields() {
        // A key present with a null value would still override a provider default
        // in most HTTP clients, so absence has to mean absence.
        let params = CallOptions::new().with_temperature(0.7).to_params();
        assert_eq!(params.len(), 1);
        assert_eq!(params["temperature"], Value::from(0.7));
    }

    #[test]
    fn test_to_params_emits_temperature_zero() {
        let params = CallOptions::new().with_temperature(0.0).to_params();
        assert_eq!(params["temperature"], Value::from(0.0));
    }

    #[test]
    fn test_to_params_uses_snake_case_keys() {
        let params = CallOptions::new()
            .with_max_tokens(100)
            .with_top_p(0.9)
            .to_params();
        assert_eq!(params["max_tokens"], Value::from(100));
        assert_eq!(params["top_p"], Value::from(0.9));
    }

    #[test]
    fn test_to_params_passes_extra_through_by_key() {
        let params = CallOptions::new()
            .with_extra("frequency_penalty", Value::from(0.5))
            .to_params();
        assert_eq!(params["frequency_penalty"], Value::from(0.5));
    }

    #[test]
    fn test_to_params_empty_for_no_options() {
        assert!(CallOptions::new().to_params().is_empty());
    }

    #[test]
    fn test_merge_lets_a_set_override_win() {
        let merged = CallOptions::new()
            .with_temperature(0.2)
            .merge(&CallOptions::new().with_temperature(0.9));
        assert_eq!(merged.temperature, Some(0.9));
    }

    #[test]
    fn test_merge_lets_an_override_of_zero_win() {
        let merged = CallOptions::new()
            .with_temperature(0.9)
            .merge(&CallOptions::new().with_temperature(0.0));
        assert_eq!(merged.temperature, Some(0.0));
    }

    #[test]
    fn test_merge_does_not_let_an_unset_override_erase_the_base() {
        // None means "did not ask", not "clear it". Replacing whole structs, or
        // taking the override wholesale, wipes the base here — and this is the
        // common shape: an Option variable forwarded straight into the struct.
        let base = CallOptions::new().with_temperature(0.5).with_max_tokens(10);
        let overrides = CallOptions {
            temperature: None,
            max_tokens: Some(20),
            ..Default::default()
        };
        let merged = base.merge(&overrides);
        assert_eq!(merged.temperature, Some(0.5));
        assert_eq!(merged.max_tokens, Some(20));
    }

    #[test]
    fn test_merge_merges_extra_key_by_key() {
        let base = CallOptions::new()
            .with_extra("a", Value::from(1))
            .with_extra("b", Value::from(2));
        let merged = base.merge(&CallOptions::new().with_extra("b", Value::from(3)));
        assert_eq!(merged.extra["a"], Value::from(1));
        assert_eq!(merged.extra["b"], Value::from(3));
    }

    #[test]
    fn test_merge_does_not_mutate_either_input() {
        let base = CallOptions::new().with_temperature(0.2);
        let overrides = CallOptions::new().with_temperature(0.9);
        let _ = base.merge(&overrides);
        assert_eq!(base.temperature, Some(0.2));
        assert_eq!(overrides.temperature, Some(0.9));
    }

    #[test]
    fn test_merge_of_two_empties_is_empty() {
        assert!(CallOptions::new().merge(&CallOptions::new()).is_empty());
    }

    #[test]
    fn test_supports_options() {
        assert!(supports_options(&RecordingAgent::new()));
        assert!(!supports_options(&PlainAgent {
            process_calls: Mutex::new(0)
        }));
    }

    #[tokio::test]
    async fn test_process_with_options_routes_to_process_with() {
        let agent = RecordingAgent::new();
        let options = CallOptions::new().with_temperature(0.0).with_max_tokens(32);

        let response = process_with_options(&agent, Message::with_text("user", "Q"), &options)
            .await
            .unwrap();

        assert_eq!(*agent.process_with_calls.lock().unwrap(), 1);
        assert_eq!(*agent.process_calls.lock().unwrap(), 0);
        assert_eq!(response.content_as_str(), Some("with-options"));
        let seen = agent.last_options.lock().unwrap().clone().unwrap();
        assert_eq!(seen.temperature, Some(0.0));
        assert_eq!(seen.max_tokens, Some(32));
    }

    #[tokio::test]
    async fn test_process_with_options_takes_plain_path_for_empty_options() {
        // An empty options set is indistinguishable from not asking, so an agent
        // must not be handed one just because this helper was used.
        let agent = RecordingAgent::new();

        process_with_options(&agent, Message::with_text("user", "Q"), &CallOptions::new())
            .await
            .unwrap();

        assert_eq!(*agent.process_with_calls.lock().unwrap(), 0);
        assert_eq!(*agent.process_calls.lock().unwrap(), 1);
    }

    #[tokio::test]
    async fn test_process_with_options_still_processes_a_plain_agent() {
        // The options cannot be applied, but the call must succeed. Callers that
        // need to know whether they landed check supports_options; that is what
        // makes the drop visible rather than silent.
        let agent = PlainAgent {
            process_calls: Mutex::new(0),
        };
        let options = CallOptions::new().with_temperature(0.7);

        let response = process_with_options(&agent, Message::with_text("user", "Q"), &options)
            .await
            .unwrap();

        assert_eq!(*agent.process_calls.lock().unwrap(), 1);
        assert_eq!(response.content_as_str(), Some("plain"));
    }
}
