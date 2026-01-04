# ============================================================
# Lambda Function Outputs
# ============================================================

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = local.lambda_function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = local.lambda_function_arn
}

output "lambda_function_invoke_arn" {
  description = "Invoke ARN of the Lambda function"
  value       = local.lambda_invoke_arn
}

output "lambda_execution_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution_role.arn
}

output "lambda_execution_role_name" {
  description = "Name of the Lambda execution role"
  value       = aws_iam_role.lambda_execution_role.name
}

# ============================================================
# Lambda Function URL Outputs
# ============================================================

output "function_url" {
  description = "Lambda Function URL for direct invocation"
  value       = var.enable_function_url ? aws_lambda_function_url.agenkit_url[0].function_url : null
}

output "function_url_id" {
  description = "ID of the Lambda Function URL configuration"
  value       = var.enable_function_url ? aws_lambda_function_url.agenkit_url[0].url_id : null
}

# ============================================================
# API Gateway Outputs
# ============================================================

output "api_gateway_id" {
  description = "ID of the API Gateway REST API"
  value       = var.enable_api_gateway ? aws_api_gateway_rest_api.agenkit_api[0].id : null
}

output "api_gateway_endpoint" {
  description = "API Gateway endpoint URL"
  value = var.enable_api_gateway ? "${aws_api_gateway_rest_api.agenkit_api[0].execution_arn}/${var.environment}/agent" : null
}

output "api_gateway_invoke_url" {
  description = "Full API Gateway invoke URL"
  value = var.enable_api_gateway ? "https://${aws_api_gateway_rest_api.agenkit_api[0].id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${var.environment}/agent" : null
}

# ============================================================
# CloudWatch Outputs
# ============================================================

output "lambda_log_group_name" {
  description = "Name of the Lambda CloudWatch log group"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "lambda_log_group_arn" {
  description = "ARN of the Lambda CloudWatch log group"
  value       = aws_cloudwatch_log_group.lambda_logs.arn
}

output "api_gateway_log_group_name" {
  description = "Name of the API Gateway CloudWatch log group"
  value       = aws_cloudwatch_log_group.api_gateway_logs.name
}

output "api_gateway_log_group_arn" {
  description = "ARN of the API Gateway CloudWatch log group"
  value       = aws_cloudwatch_log_group.api_gateway_logs.arn
}

# ============================================================
# Alarm Outputs
# ============================================================

output "alarm_error_arn" {
  description = "ARN of the Lambda error alarm"
  value       = var.enable_alarms ? aws_cloudwatch_metric_alarm.lambda_errors[0].arn : null
}

output "alarm_throttle_arn" {
  description = "ARN of the Lambda throttle alarm"
  value       = var.enable_alarms ? aws_cloudwatch_metric_alarm.lambda_throttles[0].arn : null
}

output "alarm_duration_arn" {
  description = "ARN of the Lambda duration alarm"
  value       = var.enable_alarms ? aws_cloudwatch_metric_alarm.lambda_duration[0].arn : null
}

# ============================================================
# Configuration Outputs
# ============================================================

output "deployment_config" {
  description = "Deployment configuration summary"
  value = {
    environment      = var.environment
    runtime          = var.runtime
    agent_type       = var.agent_type
    memory_size      = var.memory_size
    timeout          = var.timeout
    function_url     = var.enable_function_url
    api_gateway      = var.enable_api_gateway
    alarms_enabled   = var.enable_alarms
    bedrock_enabled  = var.enable_bedrock
    secrets_enabled  = var.enable_secrets_manager
  }
}

# ============================================================
# Testing Helper Outputs
# ============================================================

output "curl_test_command" {
  description = "Example curl command to test the deployed function"
  value = var.enable_api_gateway ? <<-EOT
    curl -X POST https://${aws_api_gateway_rest_api.agenkit_api[0].id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${var.environment}/agent \
      -H "Content-Type: application/json" \
      -d '{"agent_type": "${var.agent_type}", "message": {"role": "user", "content": "Hello!"}}'
  EOT : (var.enable_function_url ? <<-EOT
    curl -X POST ${aws_lambda_function_url.agenkit_url[0].function_url} \
      -H "Content-Type: application/json" \
      -d '{"agent_type": "${var.agent_type}", "message": {"role": "user", "content": "Hello!"}}'
  EOT : "No endpoints enabled")
}

output "aws_cli_invoke_command" {
  description = "AWS CLI command to invoke the Lambda function directly"
  value = <<-EOT
    aws lambda invoke \
      --function-name ${local.lambda_function_name} \
      --payload '{"body": "{\"agent_type\": \"${var.agent_type}\", \"message\": {\"role\": \"user\", \"content\": \"Hello!\"}}"}' \
      --region ${data.aws_region.current.name} \
      response.json
  EOT
}

output "cloudwatch_logs_command" {
  description = "AWS CLI command to tail CloudWatch logs"
  value = <<-EOT
    aws logs tail ${aws_cloudwatch_log_group.lambda_logs.name} --follow --region ${data.aws_region.current.name}
  EOT
}
