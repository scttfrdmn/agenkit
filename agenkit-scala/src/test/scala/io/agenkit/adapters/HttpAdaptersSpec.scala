package io.agenkit.adapters

import com.sun.net.httpserver.{HttpExchange, HttpServer}
import io.agenkit.core.Message
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import java.net.InetSocketAddress
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

/** Hermetic tests for the real HTTP adapters. A local JDK HttpServer stands in
  * for the provider API on an ephemeral port — no network, no API keys — so we
  * exercise the actual request building + response parsing.
  */
class HttpAdaptersSpec extends AnyFunSuite with Matchers:

  /** Start a one-shot stub server that captures the request body and returns
    * `responseJson`. Returns (baseUrl, capturedBody-thunk, stop-thunk).
    */
  private def withStub(path: String, responseJson: String)(
    body: (String, () => String) => Unit
  ): Unit =
    val server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0)
    @volatile var captured: String = ""
    server.createContext(
      path,
      (ex: HttpExchange) =>
        captured = new String(ex.getRequestBody.readAllBytes(), "UTF-8")
        val bytes = responseJson.getBytes("UTF-8")
        ex.sendResponseHeaders(200, bytes.length.toLong)
        ex.getResponseBody.write(bytes)
        ex.getResponseBody.close()
    )
    server.start()
    try
      val baseUrl = s"http://127.0.0.1:${server.getAddress.getPort}"
      body(baseUrl, () => captured)
    finally server.stop(0)

  test("OpenAiAdapter sends chat/completions and parses the first choice"):
    val resp =
      """{"choices":[{"message":{"role":"assistant","content":"hi from openai"}}]}"""
    withStub("/chat/completions", resp): (baseUrl, captured) =>
      val adapter = OpenAiAdapter(apiKey = "test-key", model = "gpt-4o", baseUrl = baseUrl)
      val out =
        Await.result(adapter.complete(List(Message.user("hello"))), 10.seconds)
      out.role shouldBe "assistant"
      out.contentString shouldBe "hi from openai"
      // Request shape
      val sent = ujson.read(captured())
      sent("model").str shouldBe "gpt-4o"
      sent("messages").arr should have size 1
      sent("messages")(0)("role").str shouldBe "user"
      sent("messages")(0)("content").str shouldBe "hello"

  test("AnthropicAdapter sends v1/messages, lifts system prompt, parses content"):
    val resp = """{"content":[{"type":"text","text":"hi from claude"}]}"""
    withStub("/v1/messages", resp): (baseUrl, captured) =>
      val adapter =
        AnthropicAdapter(apiKey = "test-key", model = "claude-opus-4-6", baseUrl = baseUrl)
      val msgs = List(Message.system("be terse"), Message.user("hello"))
      val out  = Await.result(adapter.complete(msgs), 10.seconds)
      out.contentString shouldBe "hi from claude"
      val sent = ujson.read(captured())
      sent("system").str shouldBe "be terse" // system lifted out of messages
      sent("messages").arr should have size 1 // only the user message remains
      sent("messages")(0)("role").str shouldBe "user"
      sent("max_tokens").num shouldBe 4096

  test("OpenAiAdapter fails the Future on a non-2xx response"):
    val server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0)
    server.createContext(
      "/chat/completions",
      (ex: HttpExchange) =>
        val bytes = """{"error":"bad request"}""".getBytes("UTF-8")
        ex.sendResponseHeaders(400, bytes.length.toLong)
        ex.getResponseBody.write(bytes)
        ex.getResponseBody.close()
    )
    server.start()
    try
      val baseUrl = s"http://127.0.0.1:${server.getAddress.getPort}"
      val adapter = OpenAiAdapter(apiKey = "k", baseUrl = baseUrl)
      val ex = Await.result(adapter.complete(List(Message.user("hi"))).failed, 10.seconds)
      ex shouldBe a[RuntimeException]
      ex.getMessage should include("400")
    finally server.stop(0)
