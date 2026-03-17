package io.agenkit.middleware

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicLong

private[middleware] case class UserBucket(tokens: AtomicLong, lastRefill: AtomicLong)

/** Per-user token-bucket rate limiter keyed on the `user_id` metadata field. */
class PerUserRateLimiterMiddleware(
  inner: Agent,
  requestsPerSecond: Int = 10
) extends Agent:
  private val userBuckets     = new ConcurrentHashMap[String, UserBucket]()
  private val _processedCount = new AtomicLong(0)

  def name: String               = s"per-user-rate-limiter(${inner.name})"
  def capabilities: List[String] = inner.capabilities :+ "per-user-rate-limiting"

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    val userId = message.metadata.get("user_id").map(_.toString).getOrElse("default")
    val bucket = userBuckets.computeIfAbsent(
      userId,
      _ => UserBucket(new AtomicLong(requestsPerSecond), new AtomicLong(System.currentTimeMillis()))
    )
    refillBucket(bucket)
    val available = bucket.tokens.get()
    if available > 0 && bucket.tokens.compareAndSet(available, available - 1) then
      inner.process(message)
    else
      Future.failed(new RuntimeException(s"Rate limit exceeded for user: $userId"))

  private def refillBucket(bucket: UserBucket): Unit =
    val now     = System.currentTimeMillis()
    val last    = bucket.lastRefill.get()
    val elapsed = now - last
    if elapsed >= 1000 && bucket.lastRefill.compareAndSet(last, now) then
      bucket.tokens.set(requestsPerSecond)

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("rps" -> requestsPerSecond, "userCount" -> userBuckets.size()),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
