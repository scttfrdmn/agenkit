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

  test("RouterAgent returns assistant role"):
    val llm    = MockLlmClient(_ => "route-a")
    val target = MockAgent(name = "route-a", response = "routed")
    val agent  = RouterAgent("router", llm, routes = Map("route-a" -> target))
    val result = Await.result(agent.process(Message.user("go")), 5.seconds)
    result.role shouldBe "assistant"

  test("RouterAgent name getter"):
    val agent = RouterAgent("my-router", MockLlmClient(), routes = Map("a" -> MockAgent()))
    agent.name shouldBe "my-router"

  test("RouterAgent capabilities contain routing"):
    val agent = RouterAgent("router", MockLlmClient(), routes = Map("a" -> MockAgent()))
    agent.capabilities should contain("routing")

  test("RouterAgent introspect returns name"):
    val agent = RouterAgent("router-agent", MockLlmClient(), routes = Map("a" -> MockAgent()))
    agent.introspect().name shouldBe "router-agent"

  test("RouterAgent routes only to matched agent"):
    val llm    = MockLlmClient(_ => "a")
    val agentA = MockAgent(name = "a", response = "from A")
    val agentB = MockAgent(name = "b", response = "from B")
    val agent  = RouterAgent("router", llm, routes = Map("a" -> agentA, "b" -> agentB))
    val result = Await.result(agent.process(Message.user("test")), 5.seconds)
    result.contentString shouldBe "from A"
    agentA.callCount shouldBe 1
    agentB.callCount shouldBe 0
