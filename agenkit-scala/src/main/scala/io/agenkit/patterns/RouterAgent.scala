package io.agenkit.patterns

import io.agenkit.adapters.LlmClient
import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** Classifies a message and dispatches it to the matching specialist agent. */
class RouterAgent(
  val name: String,
  llm: LlmClient,
  routes: Map[String, Agent],
  defaultAgent: Option[Agent] = None
) extends Agent:
  private val _processedCount = new AtomicLong(0)

  def capabilities: List[String] = List("routing", "classification")

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    val routeNames = routes.keys.mkString(", ")
    val classifyPrompt = Message.system(
      s"Classify the user message into exactly one of these categories: $routeNames. Respond with only the category name."
    )
    llm.complete(List(classifyPrompt, message)).flatMap { classification =>
      val route = classification.contentString.trim.toLowerCase
      routes.find { case (k, _) => k.toLowerCase == route }.map(_._2)
        .orElse(defaultAgent)
        .map(_.process(message))
        .getOrElse(Future.successful(Message.of("assistant", s"No route found for: $route")))
    }

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("routes" -> routes.keys.toList),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
