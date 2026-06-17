package io.agenkit.adapters

import java.net.URI
import java.net.http.{HttpClient, HttpRequest, HttpResponse}
import java.time.Duration
import scala.concurrent.{ExecutionContext, Future}
import scala.jdk.FutureConverters.*

/** Shared HTTP plumbing for the real LLM adapters.
  *
  * Uses the JDK's built-in `java.net.http.HttpClient` (JDK 11+) so the core
  * library needs no third-party HTTP dependency. JSON is handled by upickle,
  * which the project already depends on.
  */
private[adapters] object HttpLlm:
  /** A lazily-created, shared async client. */
  private lazy val client: HttpClient =
    HttpClient
      .newBuilder()
      .connectTimeout(Duration.ofSeconds(30))
      .build()

  /** POST a JSON body to `url` with the given headers and return the response
    * body as a string, failing the Future on any non-2xx status.
    */
  def postJson(
    url: String,
    body: String,
    headers: Map[String, String],
    timeout: Duration = Duration.ofSeconds(60)
  )(using ExecutionContext): Future[String] =
    var builder = HttpRequest
      .newBuilder()
      .uri(URI.create(url))
      .timeout(timeout)
      .header("content-type", "application/json")
      .POST(HttpRequest.BodyPublishers.ofString(body))
    headers.foreach { case (k, v) => builder = builder.header(k, v) }

    client
      .sendAsync(builder.build(), HttpResponse.BodyHandlers.ofString())
      .asScala
      .map { resp =>
        if resp.statusCode() >= 200 && resp.statusCode() < 300 then resp.body()
        else
          throw new RuntimeException(
            s"LLM HTTP request to $url failed: ${resp.statusCode()} ${resp.body()}"
          )
      }
