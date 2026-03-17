package io.agenkit.composition

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** Routes each message to one of two agents based on a predicate. */
class ConditionalAgent(
  val name: String,
  condition: Message => Boolean,
  ifTrue: Agent,
  ifFalse: Agent
) extends Agent:
  private val _processedCount = new AtomicLong(0)

  def capabilities: List[String] = List("conditional", "branching")

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    if condition(message) then ifTrue.process(message)
    else ifFalse.process(message)

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("trueBranch" -> ifTrue.name, "falseBranch" -> ifFalse.name),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
