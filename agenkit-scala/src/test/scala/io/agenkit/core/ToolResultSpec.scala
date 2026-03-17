package io.agenkit.core

import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers

class ToolResultSpec extends AnyFunSuite with Matchers:
  test("ToolResult.ok creates ToolOk"):
    ToolResult.ok("data") shouldBe a[ToolOk]
    ToolResult.ok("data").asInstanceOf[ToolOk].data shouldBe "data"

  test("ToolResult.fail creates ToolFail"):
    ToolResult.fail("error") shouldBe a[ToolFail]
    ToolResult.fail("error").asInstanceOf[ToolFail].error shouldBe "error"

  test("ToolOk pattern match"):
    ToolResult.ok(42) match
      case ToolOk(data) => data shouldBe 42
      case _            => fail("Expected ToolOk")

  test("ToolFail pattern match"):
    ToolResult.fail("oops") match
      case ToolFail(error) => error shouldBe "oops"
      case _               => fail("Expected ToolFail")

  test("ToolOk with complex data"):
    val result = ToolOk(Map("key" -> "value"))
    result.data.asInstanceOf[Map[?, ?]]("key") shouldBe "value"
