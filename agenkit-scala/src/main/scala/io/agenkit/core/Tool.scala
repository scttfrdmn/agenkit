package io.agenkit.core

import scala.concurrent.{ExecutionContext, Future}

/** A callable tool that agents can invoke. */
trait Tool:
  def name: String
  def description: String
  def execute(parameters: Map[String, Any])(using ExecutionContext): Future[ToolResult]
