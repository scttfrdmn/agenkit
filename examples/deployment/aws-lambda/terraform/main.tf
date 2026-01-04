terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  # Uncomment for remote state
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "agenkit-lambda/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-state-lock"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "agenkit"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ============================================================
# Data Sources
# ============================================================

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# ============================================================
# IAM Role for Lambda
# ============================================================

resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.function_name_prefix}-${var.environment}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# Basic execution policy for CloudWatch Logs
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# X-Ray tracing policy
resource "aws_iam_role_policy_attachment" "lambda_xray" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Optional: Bedrock access
resource "aws_iam_role_policy_attachment" "lambda_bedrock" {
  count      = var.enable_bedrock ? 1 : 0
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
}

# Optional: Secrets Manager access
resource "aws_iam_role_policy_attachment" "lambda_secrets" {
  count      = var.enable_secrets_manager ? 1 : 0
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
}

# ============================================================
# CloudWatch Log Groups
# ============================================================

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.function_name_prefix}-${var.environment}-${var.agent_type}"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "api_gateway_logs" {
  name              = "/aws/apigateway/${var.function_name_prefix}-${var.environment}"
  retention_in_days = var.log_retention_days
}

# ============================================================
# Lambda Function (Python)
# ============================================================

data "archive_file" "python_lambda_package" {
  count       = var.runtime == "python" ? 1 : 0
  type        = "zip"
  source_dir  = "${path.module}/../python"
  output_path = "${path.module}/lambda_function_python.zip"
  excludes    = ["__pycache__", "*.pyc", ".pytest_cache", "tests"]
}

resource "aws_lambda_function" "agenkit_python" {
  count = var.runtime == "python" ? 1 : 0

  filename         = data.archive_file.python_lambda_package[0].output_path
  function_name    = "${var.function_name_prefix}-${var.environment}-${var.agent_type}"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.python_lambda_package[0].output_base64sha256
  runtime          = var.python_runtime
  memory_size      = var.memory_size
  timeout          = var.timeout

  environment {
    variables = merge(
      {
        ENVIRONMENT          = var.environment
        AGENT_TYPE           = var.agent_type
        LOG_LEVEL            = var.log_level
        POWERTOOLS_SERVICE_NAME = "agenkit-lambda"
      },
      var.environment_variables
    )
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs,
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy_attachment.lambda_xray
  ]
}

# ============================================================
# Lambda Function (Go)
# ============================================================

data "archive_file" "go_lambda_package" {
  count       = var.runtime == "go" ? 1 : 0
  type        = "zip"
  source_file = "${path.module}/../go/bootstrap"
  output_path = "${path.module}/lambda_function_go.zip"
}

resource "aws_lambda_function" "agenkit_go" {
  count = var.runtime == "go" ? 1 : 0

  filename         = data.archive_file.go_lambda_package[0].output_path
  function_name    = "${var.function_name_prefix}-${var.environment}-${var.agent_type}"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "bootstrap"
  source_code_hash = data.archive_file.go_lambda_package[0].output_base64sha256
  runtime          = "provided.al2023"
  architectures    = ["x86_64"]
  memory_size      = var.memory_size
  timeout          = var.timeout

  environment {
    variables = merge(
      {
        ENVIRONMENT          = var.environment
        AGENT_TYPE           = var.agent_type
        LOG_LEVEL            = var.log_level
        POWERTOOLS_SERVICE_NAME = "agenkit-lambda-go"
      },
      var.environment_variables
    )
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs,
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy_attachment.lambda_xray
  ]
}

# Locals to reference the correct Lambda function
locals {
  lambda_function_arn  = var.runtime == "python" ? aws_lambda_function.agenkit_python[0].arn : aws_lambda_function.agenkit_go[0].arn
  lambda_function_name = var.runtime == "python" ? aws_lambda_function.agenkit_python[0].function_name : aws_lambda_function.agenkit_go[0].function_name
  lambda_invoke_arn    = var.runtime == "python" ? aws_lambda_function.agenkit_python[0].invoke_arn : aws_lambda_function.agenkit_go[0].invoke_arn
}

# ============================================================
# Lambda Function URL (Optional)
# ============================================================

resource "aws_lambda_function_url" "agenkit_url" {
  count = var.enable_function_url ? 1 : 0

  function_name      = local.lambda_function_name
  authorization_type = var.function_url_auth_type

  cors {
    allow_origins     = var.function_url_cors_origins
    allow_methods     = ["POST"]
    allow_headers     = ["*"]
    max_age           = 86400
  }
}

# ============================================================
# API Gateway REST API
# ============================================================

resource "aws_api_gateway_rest_api" "agenkit_api" {
  count = var.enable_api_gateway ? 1 : 0

  name        = "${var.function_name_prefix}-api-${var.environment}"
  description = "Agenkit Agent API (${var.runtime})"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_resource" "agent_resource" {
  count = var.enable_api_gateway ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.agenkit_api[0].id
  parent_id   = aws_api_gateway_rest_api.agenkit_api[0].root_resource_id
  path_part   = "agent"
}

resource "aws_api_gateway_method" "agent_post" {
  count = var.enable_api_gateway ? 1 : 0

  rest_api_id   = aws_api_gateway_rest_api.agenkit_api[0].id
  resource_id   = aws_api_gateway_resource.agent_resource[0].id
  http_method   = "POST"
  authorization = var.api_gateway_auth_type
}

resource "aws_api_gateway_integration" "lambda_integration" {
  count = var.enable_api_gateway ? 1 : 0

  rest_api_id             = aws_api_gateway_rest_api.agenkit_api[0].id
  resource_id             = aws_api_gateway_resource.agent_resource[0].id
  http_method             = aws_api_gateway_method.agent_post[0].http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = local.lambda_invoke_arn
}

resource "aws_api_gateway_deployment" "api_deployment" {
  count = var.enable_api_gateway ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.agenkit_api[0].id
  stage_name  = var.environment

  depends_on = [
    aws_api_gateway_integration.lambda_integration
  ]

  lifecycle {
    create_before_destroy = true
  }
}

# Enable X-Ray tracing for API Gateway
resource "aws_api_gateway_stage" "api_stage" {
  count = var.enable_api_gateway ? 1 : 0

  rest_api_id   = aws_api_gateway_rest_api.agenkit_api[0].id
  stage_name    = var.environment
  deployment_id = aws_api_gateway_deployment.api_deployment[0].id

  xray_tracing_enabled = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_logs.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }

  depends_on = [
    aws_api_gateway_deployment.api_deployment
  ]
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gateway_invoke" {
  count = var.enable_api_gateway ? 1 : 0

  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = local.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.agenkit_api[0].execution_arn}/*/*"
}

# ============================================================
# CloudWatch Alarms (Optional)
# ============================================================

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  count = var.enable_alarms ? 1 : 0

  alarm_name          = "${local.lambda_function_name}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = var.alarm_error_threshold
  alarm_description   = "Lambda function error rate is too high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = local.lambda_function_name
  }

  alarm_actions = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  count = var.enable_alarms ? 1 : 0

  alarm_name          = "${local.lambda_function_name}-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = var.alarm_throttle_threshold
  alarm_description   = "Lambda function is being throttled"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = local.lambda_function_name
  }

  alarm_actions = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  count = var.enable_alarms ? 1 : 0

  alarm_name          = "${local.lambda_function_name}-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Average"
  threshold           = var.alarm_duration_threshold
  alarm_description   = "Lambda function duration is too high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = local.lambda_function_name
  }

  alarm_actions = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []
}
