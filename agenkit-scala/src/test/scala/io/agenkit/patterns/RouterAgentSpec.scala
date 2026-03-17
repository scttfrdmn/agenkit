package io.agenkit.patterns

import io.agenkit.core.*
import io.agenkit.helpers.{MockAgent, MockLlmClient}
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class RouterAgentSpec extends AnyFunSuite with Matchers:
  test("RouterAgent dispatches to correct route"):
    val llm     = MockLlmClient(_ => "chat")
    val chatAgent = MockAgent(name = "chat", response = "chat response")
    val agent   = RouterAgent("router", llm, routes = Map("chat" -> chatAgent))
    val result  = Await.result(agent.process(Message.user("hello")), 5.seconds)
    result.contentString shouldBe "chat response"
    chatAgent.callCount shouldBe 1

  test("RouterAgent uses default agent when no route matches"):
    val llm          = MockLlmClient(_ => "unknown")
    val defaultAgent = MockAgent(name = "default", response = "default response")
    val agent        = RouterAgent("router", llm, routes = Map.empty, defaultAgent = Some(defaultAgent))
    val result       = Await.result(agent.process(Message.user("test")), 5.seconds)
    result.contentString shouldBe "default response"

  test("RouterAgent returns not-found message when no route and no default"):
    val llm   = MockLlmClient(_ => "unknown")
    val agent = RouterAgent("router", llm, routes = Map.empty)
    val result = Await.result(agent.process(Message.user("test")), 5.seconds)
    result.contentString should include("No route found")

  test("RouterAgent introspect"):
    val llm   = MockLlmClient()
    val agent = RouterAgent("router", llm, routes = Map("a" -> MockAgent()))
    val r     = agent.introspect()
    r.name shouldBe "router"
    r.capabilities should contain("routing")
