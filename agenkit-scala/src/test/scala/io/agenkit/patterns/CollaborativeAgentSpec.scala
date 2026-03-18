package io.agenkit.patterns

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class CollaborativeAgentSpec extends AnyFunSuite with Matchers:
  test("CollaborativeAgent fans out to all peers"):
    val peer1  = MockAgent(name = "peer1", response = "response A")
    val peer2  = MockAgent(name = "peer2", response = "response B")
    val agent  = CollaborativeAgent("collab", List(peer1, peer2))
    val result = Await.result(agent.process(Message.user("hello")), 5.seconds)
    result.contentString should include("response A")
    result.contentString should include("response B")
    peer1.callCount shouldBe 1
    peer2.callCount shouldBe 1

  test("CollaborativeAgent custom merge strategy"):
    val peer  = MockAgent(name = "peer", response = "peerResp")
    val agent = CollaborativeAgent("collab", List(peer), mergeStrategy = _.mkString("|"))
    val result = Await.result(agent.process(Message.user("test")), 5.seconds)
    result.contentString shouldBe "peerResp"

  test("CollaborativeAgent introspect"):
    val agent = CollaborativeAgent("collab", List(MockAgent(), MockAgent()))
    val r     = agent.introspect()
    r.name shouldBe "collab"
    r.capabilities should contain("collaboration")

  test("CollaborativeAgent returns assistant role"):
    val peer   = MockAgent(name = "p1", response = "some answer")
    val agent  = CollaborativeAgent("collab", List(peer))
    val result = Await.result(agent.process(Message.user("hi")), 5.seconds)
    result.role shouldBe "assistant"

  test("CollaborativeAgent name getter"):
    val agent = CollaborativeAgent("my-collab", List(MockAgent()))
    agent.name shouldBe "my-collab"

  test("CollaborativeAgent capabilities contain collaboration"):
    val agent = CollaborativeAgent("collab", List(MockAgent()))
    agent.capabilities should contain("collaboration")

  test("CollaborativeAgent introspect returns name"):
    val agent = CollaborativeAgent("collab-agent", List(MockAgent()))
    agent.introspect().name shouldBe "collab-agent"

  test("CollaborativeAgent works with single peer"):
    val peer   = MockAgent(name = "solo", response = "solo response")
    val agent  = CollaborativeAgent("collab", List(peer))
    val result = Await.result(agent.process(Message.user("only one")), 5.seconds)
    result.contentString should include("solo response")

  test("CollaborativeAgent multiple sequential calls"):
    val peer  = MockAgent(name = "p", response = "resp")
    val agent = CollaborativeAgent("collab", List(peer))
    val r1    = Await.result(agent.process(Message.user("first")), 5.seconds)
    val r2    = Await.result(agent.process(Message.user("second")), 5.seconds)
    r1.role shouldBe "assistant"
    r2.role shouldBe "assistant"
    peer.callCount shouldBe 2
