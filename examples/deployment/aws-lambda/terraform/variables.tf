# ============================================================
# Core Configuration
# ============================================================

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod"
  }
}

variable "function_name_prefix" {
  description = "Prefix for Lambda function name"
  type        = string
  default     = "agenkit"
}

variable "agent_type" {
  description = "Type of agent to deploy (react, conversational, router)"
  type        = string
  default     = "react"

  validation {
    condition     = contains(["react", "conversational", "router"], var.agent_type)
    error_message = "Agent type must be one of: react, conversational, router"
  }
}

variable "runtime" {
  description = "Lambda runtime to use (python or go)"
  type        = string
  default     = "python"

  validation {
    condition     = contains(["python", "go"], var.runtime)
    error_message = "Runtime must be either 'python' or 'go'"
  }
}

# ============================================================
# Lambda Configuration
# ============================================================

variable "python_runtime" {
  description = "Python runtime version"
  type        = string
  default     = "python3.12"
}

variable "memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 512

  validation {
    condition     = var.memory_size >= 128 && var.memory_size <= 10240
    error_message = "Memory size must be between 128 and 10240 MB"
  }
}

variable "timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 30

  validation {
    condition     = var.timeout >= 1 && var.timeout <= 900
    error_message = "Timeout must be between 1 and 900 seconds"
  }
}

variable "log_level" {
  description = "Logging level (DEBUG, INFO, WARNING, ERROR)"
  type        = string
  default     = "INFO"

  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR"], var.log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARNING, ERROR"
  }
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30

  validation {
    condition = contains([
      1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180,
      365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653
    ], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period"
  }
}

variable "environment_variables" {
  description = "Additional environment variables for Lambda function"
  type        = map(string)
  default     = {}
}

# ============================================================
# IAM Configuration
# ============================================================

variable "enable_bedrock" {
  description = "Enable AWS Bedrock access for Lambda function"
  type        = bool
  default     = false
}

variable "enable_secrets_manager" {
  description = "Enable Secrets Manager access for Lambda function"
  type        = bool
  default     = false
}

# ============================================================
# Lambda Function URL Configuration
# ============================================================

variable "enable_function_url" {
  description = "Enable Lambda Function URL"
  type        = bool
  default     = true
}

variable "function_url_auth_type" {
  description = "Function URL authorization type (NONE or AWS_IAM)"
  type        = string
  default     = "NONE"

  validation {
    condition     = contains(["NONE", "AWS_IAM"], var.function_url_auth_type)
    error_message = "Function URL auth type must be either 'NONE' or 'AWS_IAM'"
  }
}

variable "function_url_cors_origins" {
  description = "CORS allowed origins for Function URL"
  type        = list(string)
  default     = ["*"]
}

# ============================================================
# API Gateway Configuration
# ============================================================

variable "enable_api_gateway" {
  description = "Enable API Gateway integration"
  type        = bool
  default     = true
}

variable "api_gateway_auth_type" {
  description = "API Gateway authorization type (NONE, AWS_IAM, CUSTOM, COGNITO_USER_POOLS)"
  type        = string
  default     = "NONE"

  validation {
    condition     = contains(["NONE", "AWS_IAM", "CUSTOM", "COGNITO_USER_POOLS"], var.api_gateway_auth_type)
    error_message = "API Gateway auth type must be one of: NONE, AWS_IAM, CUSTOM, COGNITO_USER_POOLS"
  }
}

# ============================================================
# CloudWatch Alarms Configuration
# ============================================================

variable "enable_alarms" {
  description = "Enable CloudWatch alarms"
  type        = bool
  default     = false
}

variable "alarm_error_threshold" {
  description = "Error count threshold for alarm"
  type        = number
  default     = 10
}

variable "alarm_throttle_threshold" {
  description = "Throttle count threshold for alarm"
  type        = number
  default     = 5
}

variable "alarm_duration_threshold" {
  description = "Duration threshold in milliseconds for alarm"
  type        = number
  default     = 25000
}

variable "alarm_sns_topic_arn" {
  description = "SNS topic ARN for alarm notifications"
  type        = string
  default     = ""
}

# ============================================================
# Tags
# ============================================================

variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
