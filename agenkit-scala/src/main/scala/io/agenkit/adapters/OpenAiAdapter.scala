package io.agenkit.adapters

import io.agenkit.core.Message
import scala.concurrent.{ExecutionContext, Future}

/** OpenAI Chat Completions adapter.
  *
  * Calls `POST {baseUrl}/chat/completions` with bearer auth and maps the first
  * choice's message back into an agenkit [[Message]]. Works against OpenAI and
  * any OpenAI-compatible endpoint (vLLM, llama.cpp, SGLang, …) via `baseUrl`.
  */
class OpenAiAdapter(
  apiKey: String,
  model: String = "gpt-4o",
  baseUrl: String = "https://api.openai.com/v1"
) extends LlmClient:

  def complete(messages: List[Message])(using ExecutionContext): Future[Message] =
    val payload = ujson.Obj(
      "model" -> model,
      "messages" -> ujson.Arr.from(
        messages.map(m => ujson.Obj("role" -> m.role, "content" -> m.contentString))
      )
    )

    HttpLlm
      .postJson(
        s"$baseUrl/chat/completions",
        ujson.write(payload),
        Map("authorization" -> s"Bearer $apiKey")
      )
      .map { body =>
        val json = ujson.read(body)
        val choices = json("choices").arr
        if choices.isEmpty then throw new RuntimeException("OpenAI response contained no choices")
        val content = choices(0)("message")("content").str
        Message.of("assistant", content)
      }
