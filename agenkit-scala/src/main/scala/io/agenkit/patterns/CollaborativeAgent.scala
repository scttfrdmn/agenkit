package io.agenkit.patterns

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** Fans a message out to all peer agents and merges their responses. */
class CollaborativeAgent(
  val name: String,
  peers: List[Agent],
  mergeStrategy: List[String] => String = responses => responses.mkString("\n\n---\n\n")
) extends Agent:
  private val _processedCount = new AtomicLong(0)

  def capabilities: List[String] = List("collaboration", "consensus", "parallel")

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    Future.sequence(peers.map(_.process(message))).map { responses =>
      val merged = mergeStrategy(responses.map(_.contentString))
      Message.of("assistant", merged)
    }

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("peerCount" -> peers.size, "peers" -> peers.map(_.name)),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
