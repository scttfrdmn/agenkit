//! Model pricing database and cost calculation.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Pricing information for a model.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelPricingInfo {
    /// Model identifier
    pub model: String,

    /// Provider (e.g., "openai", "anthropic", "google")
    pub provider: String,

    /// Input cost per 1M tokens (USD)
    pub input_cost_per_million: f64,

    /// Output cost per 1M tokens (USD)
    pub output_cost_per_million: f64,

    /// Optional metadata
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<serde_json::Value>,
}

impl ModelPricingInfo {
    /// Calculate cost for given token counts.
    pub fn calculate_cost(&self, input_tokens: usize, output_tokens: usize) -> f64 {
        let input_cost = (input_tokens as f64 / 1_000_000.0) * self.input_cost_per_million;
        let output_cost = (output_tokens as f64 / 1_000_000.0) * self.output_cost_per_million;
        input_cost + output_cost
    }
}

/// Centralized model pricing database.
#[derive(Clone)]
pub struct ModelPricing {
    pricing: Arc<RwLock<HashMap<String, ModelPricingInfo>>>,
}

impl ModelPricing {
    /// Create a new pricing database with default models.
    pub fn new() -> Self {
        let mut pricing = HashMap::new();

        // OpenAI models
        pricing.insert(
            "gpt-4".to_string(),
            ModelPricingInfo {
                model: "gpt-4".to_string(),
                provider: "openai".to_string(),
                input_cost_per_million: 30.0,
                output_cost_per_million: 60.0,
                metadata: None,
            },
        );

        pricing.insert(
            "gpt-4-turbo".to_string(),
            ModelPricingInfo {
                model: "gpt-4-turbo".to_string(),
                provider: "openai".to_string(),
                input_cost_per_million: 10.0,
                output_cost_per_million: 30.0,
                metadata: None,
            },
        );

        pricing.insert(
            "gpt-3.5-turbo".to_string(),
            ModelPricingInfo {
                model: "gpt-3.5-turbo".to_string(),
                provider: "openai".to_string(),
                input_cost_per_million: 0.5,
                output_cost_per_million: 1.5,
                metadata: None,
            },
        );

        // Anthropic models
        pricing.insert(
            "claude-3-opus".to_string(),
            ModelPricingInfo {
                model: "claude-3-opus".to_string(),
                provider: "anthropic".to_string(),
                input_cost_per_million: 15.0,
                output_cost_per_million: 75.0,
                metadata: None,
            },
        );

        pricing.insert(
            "claude-3-sonnet".to_string(),
            ModelPricingInfo {
                model: "claude-3-sonnet".to_string(),
                provider: "anthropic".to_string(),
                input_cost_per_million: 3.0,
                output_cost_per_million: 15.0,
                metadata: None,
            },
        );

        pricing.insert(
            "claude-3-haiku".to_string(),
            ModelPricingInfo {
                model: "claude-3-haiku".to_string(),
                provider: "anthropic".to_string(),
                input_cost_per_million: 0.25,
                output_cost_per_million: 1.25,
                metadata: None,
            },
        );

        // Google models
        pricing.insert(
            "gemini-pro".to_string(),
            ModelPricingInfo {
                model: "gemini-pro".to_string(),
                provider: "google".to_string(),
                input_cost_per_million: 0.5,
                output_cost_per_million: 1.5,
                metadata: None,
            },
        );

        pricing.insert(
            "gemini-ultra".to_string(),
            ModelPricingInfo {
                model: "gemini-ultra".to_string(),
                provider: "google".to_string(),
                input_cost_per_million: 10.0,
                output_cost_per_million: 30.0,
                metadata: None,
            },
        );

        Self {
            pricing: Arc::new(RwLock::new(pricing)),
        }
    }

    /// Create an empty pricing database.
    pub fn empty() -> Self {
        Self {
            pricing: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Calculate cost for a model.
    pub async fn calculate(
        &self,
        model: &str,
        input_tokens: usize,
        output_tokens: usize,
    ) -> Result<f64, String> {
        let pricing = self.pricing.read().await;

        if let Some(info) = pricing.get(model) {
            Ok(info.calculate_cost(input_tokens, output_tokens))
        } else {
            Err(format!("Unknown model: {}", model))
        }
    }

    /// Get pricing info for a model.
    pub async fn get_model_pricing(&self, model: &str) -> Option<ModelPricingInfo> {
        let pricing = self.pricing.read().await;
        pricing.get(model).cloned()
    }

    /// List all models.
    pub async fn list_models(&self) -> Vec<String> {
        let pricing = self.pricing.read().await;
        pricing.keys().cloned().collect()
    }

    /// List models by provider.
    pub async fn list_models_by_provider(&self, provider: &str) -> Vec<String> {
        let pricing = self.pricing.read().await;
        pricing
            .values()
            .filter(|info| info.provider == provider)
            .map(|info| info.model.clone())
            .collect()
    }

    /// Update pricing for a model.
    pub async fn update_pricing(&self, info: ModelPricingInfo) {
        let mut pricing = self.pricing.write().await;
        pricing.insert(info.model.clone(), info);
    }

    /// Remove a model from pricing.
    pub async fn remove_model(&self, model: &str) -> bool {
        let mut pricing = self.pricing.write().await;
        pricing.remove(model).is_some()
    }

    /// Get all pricing information.
    pub async fn get_all_pricing(&self) -> HashMap<String, ModelPricingInfo> {
        let pricing = self.pricing.read().await;
        pricing.clone()
    }
}

impl Default for ModelPricing {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_pricing_calculation() {
        let pricing = ModelPricing::new();

        // Test GPT-4: $30/1M input, $60/1M output
        let cost = pricing.calculate("gpt-4", 1_000_000, 500_000).await.unwrap();
        assert!((cost - 60.0).abs() < 0.01); // $30 + $30 = $60

        // Test GPT-3.5: $0.5/1M input, $1.5/1M output
        let cost = pricing.calculate("gpt-3.5-turbo", 1_000_000, 1_000_000).await.unwrap();
        assert!((cost - 2.0).abs() < 0.01); // $0.5 + $1.5 = $2
    }

    #[tokio::test]
    async fn test_list_models() {
        let pricing = ModelPricing::new();
        let models = pricing.list_models().await;
        assert!(models.len() >= 8); // At least 8 default models
        assert!(models.contains(&"gpt-4".to_string()));
        assert!(models.contains(&"claude-3-opus".to_string()));
    }

    #[tokio::test]
    async fn test_list_models_by_provider() {
        let pricing = ModelPricing::new();
        let openai_models = pricing.list_models_by_provider("openai").await;
        assert!(openai_models.contains(&"gpt-4".to_string()));
        assert!(openai_models.contains(&"gpt-3.5-turbo".to_string()));

        let anthropic_models = pricing.list_models_by_provider("anthropic").await;
        assert!(anthropic_models.contains(&"claude-3-opus".to_string()));
        assert!(anthropic_models.contains(&"claude-3-haiku".to_string()));
    }

    #[tokio::test]
    async fn test_update_pricing() {
        let pricing = ModelPricing::new();

        let custom_info = ModelPricingInfo {
            model: "custom-model".to_string(),
            provider: "custom".to_string(),
            input_cost_per_million: 5.0,
            output_cost_per_million: 10.0,
            metadata: None,
        };

        pricing.update_pricing(custom_info).await;

        let cost = pricing.calculate("custom-model", 1_000_000, 1_000_000).await.unwrap();
        assert!((cost - 15.0).abs() < 0.01);
    }

    #[tokio::test]
    async fn test_unknown_model() {
        let pricing = ModelPricing::new();
        let result = pricing.calculate("unknown-model", 1000, 500).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_small_token_counts() {
        let pricing = ModelPricing::new();

        // Test with small token counts (typical API call)
        let cost = pricing.calculate("gpt-4", 1000, 500).await.unwrap();
        // (1000/1M * $30) + (500/1M * $60) = $0.03 + $0.03 = $0.06
        assert!((cost - 0.06).abs() < 0.001);
    }
}
