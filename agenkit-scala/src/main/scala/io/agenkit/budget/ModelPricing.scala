package io.agenkit.budget

case class ModelPricing(
  inputPricePer1k: Double,
  outputPricePer1k: Double
)

object ModelPricing:
  val pricing: Map[String, ModelPricing] = Map(
    "gpt-4o"            -> ModelPricing(0.005,   0.015),
    "gpt-4o-mini"       -> ModelPricing(0.00015, 0.0006),
    "gpt-3.5-turbo"     -> ModelPricing(0.0005,  0.0015),
    "claude-opus-4-6"   -> ModelPricing(0.015,   0.075),
    "claude-sonnet-4-6" -> ModelPricing(0.003,   0.015),
    "claude-haiku-4-5"  -> ModelPricing(0.00025, 0.00125),
  )

  def get(model: String): Option[ModelPricing] = pricing.get(model)

  def estimateCost(model: String, inputTokens: Int, outputTokens: Int): Double =
    pricing.get(model).map { p =>
      (inputTokens.toDouble / 1000.0) * p.inputPricePer1k +
      (outputTokens.toDouble / 1000.0) * p.outputPricePer1k
    }.getOrElse(0.0)
