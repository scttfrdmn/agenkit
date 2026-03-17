package io.agenkit.checkpointing

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.UUID
import java.util.concurrent.atomic.AtomicLong

/** Wraps an agent and periodically snapshots its message history to a CheckpointManager. */
class DurableAgent(
  inner: Agent,
  checkpointManager: CheckpointManager,
  checkpointInterval: Int = 10
) extends Agent:
  private val _processedCount = new AtomicLong(0)
  private val history         = collection.mutable.ListBuffer[Message]()

  def name: String               = s"durable(${inner.name})"
  def capabilities: List[String] = inner.capabilities :+ "checkpointing" :+ "durable"

  def process(message: Message)(using ExecutionContext): Future[Message] =
    val count = _processedCount.incrementAndGet()
    history += message
    inner.process(message).map { response =>
      history += response
      if count % checkpointInterval == 0 then
        checkpointManager.save(Checkpoint(
          id        = UUID.randomUUID().toString,
          agentName = inner.name,
          messages  = history.toList,
          metadata  = Map("processedCount" -> count)
        ))
      response
    }

  def restoreFromCheckpoint(id: String): Boolean =
    checkpointManager.load(id) match
      case Some(cp) =>
        history.clear()
        history ++= cp.messages
        true
      case None => false

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("historySize" -> history.size, "checkpointInterval" -> checkpointInterval),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
