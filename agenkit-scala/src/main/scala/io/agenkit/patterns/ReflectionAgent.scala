package io.agenkit.patterns

import io.agenkit.adapters.LlmClient
import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** Generates an initial response then iteratively self-critiques and improves it. */
class ReflectionAgent(
  val name: String,
  llm: LlmClient,
  reflectionRounds: Int = 1
) extends Agent:
  private val _processedCount = new AtomicLong(0)

  def capabilities: List[String] = List("reflection", "self-critique")

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    llm.complete(List(message)).flatMap(initial => refine(message, initial, reflectionRounds))

  private def refine(original: Message, current: Message, rounds: Int)(using ExecutionContext): Future[Message] =
    if rounds <= 0 then Future.successful(current)
    else
      val critiquePrompt = Message.user(
        s"Critique this response and provide an improved version:\n${current.contentString}"
      )
      llm.complete(List(original, current, critiquePrompt))
        .flatMap(improved => refine(original, improved, rounds - 1))

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("reflectionRounds" -> reflectionRounds),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
