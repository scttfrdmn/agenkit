package io.agenkit.memory

import io.agenkit.core.Message

/** Minimal memory interface shared by all storage backends. */
trait Memory:
  def store(message: Message): Unit
  def retrieve(query: String, limit: Int = 10): List[Message]
  def clear(): Unit
  def size: Int
