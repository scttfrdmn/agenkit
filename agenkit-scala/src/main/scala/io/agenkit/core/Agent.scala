package io.agenkit.core

import scala.concurrent.{ExecutionContext, Future}

/** Core agent interface.  All patterns implement this trait. */
trait Agent:
  def name: String
  def capabilities: List[String]
  def process(message: Message)(using ExecutionContext): Future[Message]
  def introspect(): IntrospectionResult
