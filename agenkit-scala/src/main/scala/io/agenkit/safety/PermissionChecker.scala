package io.agenkit.safety

import io.agenkit.core.Message

/** Checks whether a user or wildcard entry is permitted to perform an action. */
class PermissionChecker(
  permissions: Map[String, List[String]] = Map.empty
):
  def check(userId: String, action: String): Boolean =
    permissions.get(userId).exists(_.contains(action)) ||
    permissions.get("*").exists(_.contains(action))

  def checkMessage(message: Message, action: String): Boolean =
    val userId = message.metadata.get("user_id").map(_.toString).getOrElse("anonymous")
    check(userId, action)
