package io.agenkit.middleware

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import scala.concurrent.duration.*
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicLong

private[middleware] case class CacheEntry(message: Message, expiresAt: Long)

/** Caches responses keyed on message content; entries expire after `ttl`. */
class CachingMiddleware(
  inner: Agent,
  ttl: FiniteDuration
) extends Agent:
  private val cache           = new ConcurrentHashMap[String, CacheEntry]()
  private val _processedCount = new AtomicLong(0)

  def name: String               = s"caching(${inner.name})"
  def capabilities: List[String] = inner.capabilities :+ "caching"

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    val key = message.contentString
    val now = System.currentTimeMillis()
    Option(cache.get(key)).filter(_.expiresAt > now) match
      case Some(entry) => Future.successful(entry.message)
      case None =>
        inner.process(message).map { response =>
          cache.put(key, CacheEntry(response, now + ttl.toMillis))
          response
        }

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("cacheSize" -> cache.size(), "ttl" -> ttl.toString),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
