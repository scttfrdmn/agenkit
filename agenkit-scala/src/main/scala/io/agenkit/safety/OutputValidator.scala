package io.agenkit.safety

import io.agenkit.core.Message

/** Validates outgoing messages against length and required-field rules. */
class OutputValidator(
  maxLength: Int = 50000,
  requiredFields: List[String] = List.empty
):
  def validate(message: Message): Either[String, Message] =
    val content = message.contentString
    if content.length > maxLength then
      Left(s"Output too long: ${content.length} > $maxLength")
    else if requiredFields.exists(f => !content.contains(f)) then
      Left("Output missing required fields")
    else
      Right(message)
