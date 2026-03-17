package io.agenkit.checkpointing

import io.agenkit.core.Message
import java.time.Instant
import java.util.concurrent.ConcurrentHashMap
import scala.jdk.CollectionConverters.*

case class Checkpoint(
  id: String,
  agentName: String,
  messages: List[Message],
  metadata: Map[String, Any],
  createdAt: Instant = Instant.now()
)

/** Thread-safe in-memory checkpoint store. */
class CheckpointManager:
  private val checkpoints = new ConcurrentHashMap[String, Checkpoint]()

  def save(checkpoint: Checkpoint): Unit =
    checkpoints.put(checkpoint.id, checkpoint)
    ()

  def load(id: String): Option[Checkpoint] =
    Option(checkpoints.get(id))

  def list(agentName: String): List[Checkpoint] =
    checkpoints.values().asScala
      .filter(_.agentName == agentName)
      .toList
      .sortBy(_.createdAt)

  def delete(id: String): Boolean =
    checkpoints.remove(id) != null

  def count: Int = checkpoints.size()
