package io.agenkit.adapters

import io.agenkit.core.Message
import scala.concurrent.{ExecutionContext, Future}

/** Anthropic Messages API adapter.
  *
  * Calls `POST {baseUrl}/v1/messages` with `x-api-key` + `anthropic-version`
  * headers. The Anthropic API takes the system prompt as a top-level field
  * (not a message role), so any `system` messages are concatenated and sent
  * separately; the rest go in `messages`. The reply text is read from
  * `content[0].text`.
  */
class AnthropicAdapter(
  apiKey: String,
  model: String = "claude-opus-4-6",
  baseUrl: String = "https://api.anthropic.com",
  maxTokens: Int = 4096,
  anthropicVersion: String = "2023-06-01"
) extends LlmClient:

  def complete(messages: List[Message])(using ExecutionContext): Future[Message] =
    val (systemMsgs, convoMsgs) = messages.partition(_.role == "system")
    val systemPrompt = systemMsgs.map(_.contentString).filter(_.nonEmpty).mkString("\n")

    val payload = ujson.Obj(
      "model" -> model,
      "max_tokens" -> maxTokens,
      "messages" -> ujson.Arr.from(
        convoMsgs.map(m => ujson.Obj("role" -> m.role, "content" -> m.contentString))
      )
    )
    if systemPrompt.nonEmpty then payload("system") = systemPrompt

    HttpLlm
      .postJson(
        s"$baseUrl/v1/messages",
        ujson.write(payload),
        Map("x-api-key" -> apiKey, "anthropic-version" -> anthropicVersion)
      )
      .map { body =>
        val json = ujson.read(body)
        val content = json("content").arr
        if content.isEmpty then throw new RuntimeException("Anthropic response contained no content")
        val text = content(0)("text").str

        // Surface token usage so metering layers can read it via
        // TokenUsage.fromMessage. Anthropic uses the input/output_tokens convention.
        val usageMeta = json.obj.get("usage").map(_.obj).map { u =>
          val inputTokens = u.get("input_tokens").map(_.num.toLong).getOrElse(0L)
          val outputTokens = u.get("output_tokens").map(_.num.toLong).getOrElse(0L)
          val base = Map[String, Any](
            "input_tokens" -> inputTokens,
            "output_tokens" -> outputTokens,
            "total_tokens" -> (inputTokens + outputTokens)
          )
          val withRead = u.get("cache_read_input_tokens")
            .map(v => base + ("cache_read_tokens" -> v.num.toLong)).getOrElse(base)
          u.get("cache_creation_input_tokens")
            .map(v => withRead + ("cache_creation_tokens" -> v.num.toLong)).getOrElse(withRead)
        }

        usageMeta match
          case Some(meta) => Message.of("assistant", text).copy(metadata = Map("usage" -> meta))
          case None       => Message.of("assistant", text)
      }
