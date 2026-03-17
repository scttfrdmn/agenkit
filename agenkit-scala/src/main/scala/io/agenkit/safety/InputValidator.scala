package io.agenkit.safety

import io.agenkit.core.Message

/** Validates incoming messages against length and content rules. */
class InputValidator(
  maxLength: Int = 10000,
  blockedPatterns: List[String] = List.empty
):
  def validate(message: Message): Either[String, Message] =
    val content = message.contentString
    if content.length > maxLength then
      Left(s"Message too long: ${content.length} > $maxLength")
    else if blockedPatterns.exists(p => content.contains(p)) then
      Left("Message contains blocked content")
    else
      Right(message)
