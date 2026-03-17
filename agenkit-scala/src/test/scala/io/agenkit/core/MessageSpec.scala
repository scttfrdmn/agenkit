package io.agenkit.core

import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers

class MessageSpec extends AnyFunSuite with Matchers:
  test("Message.of creates message with correct role and content"):
    val msg = Message.of("user", "hello")
    msg.role shouldBe "user"
    msg.content shouldBe Some("hello")
    msg.contentString shouldBe "hello"

  test("Message.user creates user message"):
    val msg = Message.user("test")
    msg.role shouldBe "user"
    msg.contentString shouldBe "test"

  test("Message.assistant creates assistant message"):
    val msg = Message.assistant("response")
    msg.role shouldBe "assistant"
    msg.contentString shouldBe "response"

  test("Message.system creates system message"):
    val msg = Message.system("prompt")
    msg.role shouldBe "system"
    msg.contentString shouldBe "prompt"

  test("Message with no content returns empty string"):
    val msg = Message(role = "user", content = None)
    msg.contentString shouldBe ""

  test("Message metadata defaults to empty map"):
    val msg = Message.of("user", "hello")
    msg.metadata shouldBe Map.empty

  test("Message with metadata"):
    val msg = Message(role = "user", content = Some("hi"), metadata = Map("user_id" -> "123"))
    msg.metadata("user_id") shouldBe "123"

  test("Message copy preserves fields"):
    val original = Message.user("original")
    val copy     = original.copy(content = Some("updated"))
    copy.role shouldBe "user"
    copy.contentString shouldBe "updated"
