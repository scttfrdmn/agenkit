package io.agenkit.safety

import io.agenkit.core.Message
import org.slf4j.LoggerFactory
import java.time.Instant

case class AuditEntry(
  timestamp: Instant,
  userId: String,
  action: String,
  messagePreview: String
)

/** Append-only audit log for agent interactions. */
class AuditLogger:
  private val logger  = LoggerFactory.getLogger(getClass)
  private val entries = collection.mutable.ListBuffer[AuditEntry]()

  def log(message: Message, action: String): Unit =
    val userId = message.metadata.get("user_id").map(_.toString).getOrElse("anonymous")
    val entry  = AuditEntry(
      timestamp      = Instant.now(),
      userId         = userId,
      action         = action,
      messagePreview = message.contentString.take(100)
    )
    entries += entry
    logger.info(s"AUDIT: action=$action userId=$userId preview=${entry.messagePreview}")

  def getEntries: List[AuditEntry] = entries.toList
  def clearEntries(): Unit         = entries.clear()
