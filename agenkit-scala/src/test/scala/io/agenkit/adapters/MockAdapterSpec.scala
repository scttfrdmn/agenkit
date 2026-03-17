package io.agenkit.adapters

import io.agenkit.core.Message
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class MockAdapterSpec extends AnyFunSuite with Matchers:
  test("MockAdapter returns configured response"):
    val adapter  = MockAdapter("hello world")
    val response = Await.result(adapter.complete(List(Message.user("hi"))), 5.seconds)
    response.role shouldBe "assistant"
    response.contentString shouldBe "hello world"

  test("MockAdapter default response"):
    val adapter  = MockAdapter()
    val response = Await.result(adapter.complete(List.empty), 5.seconds)
    response.contentString shouldBe "mock adapter response"

  test("OpenAiAdapter fails with UnsupportedOperationException"):
    val adapter = OpenAiAdapter("key")
    val result  = adapter.complete(List(Message.user("hi"))).failed
    val ex      = Await.result(result, 5.seconds)
    ex shouldBe a[UnsupportedOperationException]

  test("AnthropicAdapter fails with UnsupportedOperationException"):
    val adapter = AnthropicAdapter("key")
    val result  = adapter.complete(List(Message.user("hi"))).failed
    val ex      = Await.result(result, 5.seconds)
    ex shouldBe a[UnsupportedOperationException]
