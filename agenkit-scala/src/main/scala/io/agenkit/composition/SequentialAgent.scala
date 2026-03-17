package io.agenkit.composition

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** Pipes the output of each stage as input to the next stage. */
class SequentialAgent(
  val name: String,
  stages: List[Agent]
) extends Agent:
  private val _processedCount = new AtomicLong(0)

  def capabilities: List[String] = List("sequential", "pipeline")

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    stages.foldLeft(Future.successful(message)) { (msgFut, stage) =>
      msgFut.flatMap(stage.process)
    }

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("stageCount" -> stages.size, "stages" -> stages.map(_.name)),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
