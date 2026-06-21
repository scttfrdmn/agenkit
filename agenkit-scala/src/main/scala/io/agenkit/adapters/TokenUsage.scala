package io.agenkit.adapters

import io.agenkit.core.Message

/** Normalized, typed token usage for LLM adapter responses.
  *
  * Adapters record token counts in `Message.metadata("usage")` as a map, but
  * key names differ between the `prompt_tokens`/`completion_tokens` convention
  * and the Anthropic `input_tokens`/`output_tokens` convention.
  * [[TokenUsage.fromMessage]] normalizes both into one type so cost-metering and
  * budgeting layers consume a single shape.
  *
  * Fields are `0` when the provider does not report them. The cache fields are
  * provider-dependent (e.g. Anthropic prompt caching, including via Bedrock) and
  * are `0` when caching is inactive.
  *
  * Mirrors the Go reference (`agenkit-go/adapter/llm/usage.go`).
  */
case class TokenUsage(
  promptTokens: Long,
  completionTokens: Long,
  totalTokens: Long,
  cacheReadTokens: Long,
  cacheCreationTokens: Long
)

object TokenUsage:

  /** Extracts normalized token usage from an adapter response message.
    *
    * Reads the `metadata("usage")` map, normalizing both naming conventions
    * (`prompt_tokens`/`completion_tokens` and Anthropic's
    * `input_tokens`/`output_tokens`) and the cache keys
    * (`cache_read_tokens`/`cache_creation_tokens`, plus the raw provider aliases
    * `cache_read_input_tokens`/`cache_creation_input_tokens`).
    *
    * @return the usage, or `None` when no usage metadata is present. When
    *   `total_tokens` is absent it is derived as prompt + completion.
    */
  def fromMessage(message: Message): Option[TokenUsage] =
    message.metadata.get("usage").collect { case usage: Map[?, ?] =>
      val m = usage.asInstanceOf[Map[String, Any]]

      def pick(keys: String*): Long =
        keys.iterator.flatMap(k => m.get(k)).map(toLong).find(_ != 0L).getOrElse(0L)

      val prompt = pick("prompt_tokens", "input_tokens")
      val completion = pick("completion_tokens", "output_tokens")
      val total = pick("total_tokens") match
        case 0L => prompt + completion
        case t  => t

      TokenUsage(
        promptTokens = prompt,
        completionTokens = completion,
        totalTokens = total,
        cacheReadTokens = pick("cache_read_tokens", "cache_read_input_tokens"),
        cacheCreationTokens =
          pick("cache_creation_tokens", "cache_creation_input_tokens", "cache_write_tokens")
      )
    }

  /** Coerce a numeric metadata value to Long; 0 for non-numbers. */
  private def toLong(v: Any): Long = v match
    case n: Int    => n.toLong
    case n: Long   => n
    case n: Short  => n.toLong
    case n: Byte   => n.toLong
    case n: Double => n.toLong
    case n: Float  => n.toLong
    case _         => 0L
