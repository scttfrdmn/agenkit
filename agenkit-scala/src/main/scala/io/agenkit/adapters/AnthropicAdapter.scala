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
        Message.of("assistant", text)
      }
