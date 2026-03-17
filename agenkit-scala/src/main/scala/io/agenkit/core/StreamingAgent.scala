package io.agenkit.core

import scala.concurrent.ExecutionContext

/** Agent variant that emits a lazy stream of partial messages. */
trait StreamingAgent extends Agent:
  def stream(message: Message)(using ExecutionContext): LazyList[Message]
