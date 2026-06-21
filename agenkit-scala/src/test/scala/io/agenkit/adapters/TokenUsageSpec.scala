package io.agenkit.adapters

import io.agenkit.core.Message
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers

class TokenUsageSpec extends AnyFunSuite with Matchers:

  private def msgWith(usage: Map[String, Any]): Message =
    Message.of("assistant", "hi").copy(metadata = Map("usage" -> usage))

  test("None when no usage metadata"):
    TokenUsage.fromMessage(Message.of("assistant", "hi")) shouldBe None

  test("prompt/completion convention"):
    val u = TokenUsage.fromMessage(
      msgWith(Map("prompt_tokens" -> 10, "completion_tokens" -> 5, "total_tokens" -> 15))
    )
    u shouldBe defined
    u.get.promptTokens shouldBe 10
    u.get.completionTokens shouldBe 5
    u.get.totalTokens shouldBe 15

  test("anthropic input/output convention derives total"):
    val u = TokenUsage.fromMessage(msgWith(Map("input_tokens" -> 30, "output_tokens" -> 7)))
    u shouldBe defined
    u.get.promptTokens shouldBe 30
    u.get.completionTokens shouldBe 7
    u.get.totalTokens shouldBe 37

  test("normalized cache keys"):
    val u = TokenUsage.fromMessage(msgWith(Map(
      "prompt_tokens" -> 1000, "completion_tokens" -> 50, "total_tokens" -> 1050,
      "cache_read_tokens" -> 900, "cache_creation_tokens" -> 100
    )))
    u shouldBe defined
    u.get.cacheReadTokens shouldBe 900
    u.get.cacheCreationTokens shouldBe 100

  test("raw provider cache aliases"):
    val u = TokenUsage.fromMessage(msgWith(Map(
      "input_tokens" -> 20, "output_tokens" -> 4,
      "cache_read_input_tokens" -> 15, "cache_creation_input_tokens" -> 5
    )))
    u shouldBe Some(TokenUsage(20, 4, 24, 15, 5))

  test("ignores non-numeric values"):
    val u = TokenUsage.fromMessage(msgWith(Map("prompt_tokens" -> "x", "completion_tokens" -> 5)))
    u shouldBe defined
    u.get.promptTokens shouldBe 0
    u.get.completionTokens shouldBe 5
