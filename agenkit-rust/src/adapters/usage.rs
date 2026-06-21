//! Typed token usage for LLM adapter responses.
//!
//! Adapters record token counts in `Message.metadata["usage"]` as a
//! `serde_json::Value` object, but key names differ between the
//! `prompt_tokens`/`completion_tokens` convention (OpenAI, Bedrock, Gemini,
//! Ollama, LiteLLM) and the Anthropic `input_tokens`/`output_tokens`
//! convention. [`usage_from_message`] normalizes both into one typed struct so
//! cost-metering and budgeting layers consume a single shape.
//!
//! Mirrors the Go reference (`agenkit-go/adapter/llm/usage.go`).

use crate::core::Message;

/// Normalized, typed token usage. Fields are `0` when the provider does not
/// report them. The cache fields are provider-dependent (e.g. Anthropic prompt
/// caching, including via Bedrock) and are `0` when caching is inactive.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Usage {
    pub prompt_tokens: i64,
    pub completion_tokens: i64,
    pub total_tokens: i64,
    /// Prompt tokens served from a provider cache (billed at a reduced rate).
    pub cache_read_tokens: i64,
    /// Prompt tokens written to a provider cache on this request.
    pub cache_creation_tokens: i64,
}

/// Extract normalized token usage from an adapter response message.
///
/// Reads the `metadata["usage"]` object populated by the adapters, normalizing
/// both naming conventions (`prompt_tokens`/`completion_tokens` and Anthropic's
/// `input_tokens`/`output_tokens`) and the cache keys (`cache_read_tokens` /
/// `cache_creation_tokens`, plus the raw provider aliases
/// `cache_read_input_tokens` / `cache_creation_input_tokens`).
///
/// Returns `None` when the message carries no usage metadata. When
/// `total_tokens` is absent it is derived as prompt + completion.
pub fn usage_from_message(message: &Message) -> Option<Usage> {
    let usage = message.metadata.get("usage")?;
    let obj = usage.as_object()?;

    // pick returns the first present key, coerced to i64.
    let pick = |keys: &[&str]| -> i64 {
        for k in keys {
            if let Some(v) = obj.get(*k) {
                if let Some(n) = as_i64(v) {
                    return n;
                }
            }
        }
        0
    };

    let prompt = pick(&["prompt_tokens", "input_tokens"]);
    let completion = pick(&["completion_tokens", "output_tokens"]);
    let mut total = pick(&["total_tokens"]);
    if total == 0 {
        total = prompt + completion;
    }

    Some(Usage {
        prompt_tokens: prompt,
        completion_tokens: completion,
        total_tokens: total,
        cache_read_tokens: pick(&["cache_read_tokens", "cache_read_input_tokens"]),
        cache_creation_tokens: pick(&[
            "cache_creation_tokens",
            "cache_creation_input_tokens",
            "cache_write_tokens",
        ]),
    })
}

/// Coerce a JSON number (integer or float) to i64; `None` for non-numbers.
fn as_i64(v: &serde_json::Value) -> Option<i64> {
    if let Some(n) = v.as_i64() {
        Some(n)
    } else if let Some(n) = v.as_u64() {
        Some(n as i64)
    } else {
        v.as_f64().map(|f| f as i64)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn msg_with(usage: serde_json::Value) -> Message {
        let mut m = Message::new("assistant", json!("hi"));
        m.metadata.insert("usage".to_string(), usage);
        m
    }

    #[test]
    fn none_when_no_usage() {
        let m = Message::new("assistant", json!("hi"));
        assert_eq!(usage_from_message(&m), None);
    }

    #[test]
    fn prompt_completion_convention() {
        let m = msg_with(json!({
            "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15
        }));
        let u = usage_from_message(&m).unwrap();
        assert_eq!(u.prompt_tokens, 10);
        assert_eq!(u.completion_tokens, 5);
        assert_eq!(u.total_tokens, 15);
    }

    #[test]
    fn anthropic_input_output_convention() {
        let m = msg_with(json!({"input_tokens": 30, "output_tokens": 7}));
        let u = usage_from_message(&m).unwrap();
        assert_eq!(u.prompt_tokens, 30);
        assert_eq!(u.completion_tokens, 7);
        // total derived
        assert_eq!(u.total_tokens, 37);
    }

    #[test]
    fn cache_tokens_normalized_keys() {
        let m = msg_with(json!({
            "prompt_tokens": 1000, "completion_tokens": 50, "total_tokens": 1050,
            "cache_read_tokens": 900, "cache_creation_tokens": 100
        }));
        let u = usage_from_message(&m).unwrap();
        assert_eq!(u.cache_read_tokens, 900);
        assert_eq!(u.cache_creation_tokens, 100);
    }

    #[test]
    fn cache_tokens_raw_aliases() {
        let m = msg_with(json!({
            "input_tokens": 20, "output_tokens": 4,
            "cache_read_input_tokens": 15, "cache_creation_input_tokens": 5
        }));
        let u = usage_from_message(&m).unwrap();
        assert_eq!(
            u,
            Usage {
                prompt_tokens: 20,
                completion_tokens: 4,
                total_tokens: 24,
                cache_read_tokens: 15,
                cache_creation_tokens: 5,
            }
        );
    }

    #[test]
    fn ignores_non_numeric() {
        let m = msg_with(json!({"prompt_tokens": "x", "completion_tokens": 5}));
        let u = usage_from_message(&m).unwrap();
        assert_eq!(u.prompt_tokens, 0);
        assert_eq!(u.completion_tokens, 5);
    }
}
