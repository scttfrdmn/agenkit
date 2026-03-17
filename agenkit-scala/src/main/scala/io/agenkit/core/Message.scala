package io.agenkit.core

import java.time.Instant

/** An immutable message exchanged between agents and users. */
case class Message(
  role: String,
  content: Option[String] = None,
  metadata: Map[String, Any] = Map.empty,
  timestamp: Instant = Instant.now()
):
  /** Returns the content string, or empty string if content is absent. */
  def contentString: String = content.getOrElse("")

object Message:
  def of(role: String, content: String): Message =
    Message(role, Some(content))

  def user(content: String): Message      = of("user", content)
  def assistant(content: String): Message = of("assistant", content)
  def system(content: String): Message    = of("system", content)
