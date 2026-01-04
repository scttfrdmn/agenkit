# Agenkit AWS Lambda - Terraform Configuration

Infrastructure as Code for deploying Agenkit agents on AWS Lambda using Terraform. Supports both Python and Go runtimes with API Gateway, CloudWatch, and X-Ray integration.

## Features

- ✅ **Multi-Runtime Support**: Deploy Python or Go Lambda functions
- ✅ **API Gateway Integration**: RESTful API with throttling and CORS
- ✅ **Lambda Function URLs**: Direct HTTPS endpoints (alternative to API Gateway)
- ✅ **CloudWatch Logs**: Automatic log group creation with retention
- ✅ **X-Ray Tracing**: Distributed tracing enabled by default
- ✅ **CloudWatch Alarms**: Optional error, throttle, and duration alarms
- ✅ **IAM Roles**: Least-privilege execution roles with optional Bedrock/Secrets access
- ✅ **Environment Flexibility**: Support for dev, staging, prod environments

## Prerequisites

- Terraform >= 1.5
- AWS CLI configured with credentials
- For Python: `requirements.txt` with dependencies
- For Go: Pre-built `bootstrap` binary in `../go/` directory

## Quick Start

### 1. Initialize Terraform

```bash
cd examples/deployment/aws-lambda/terraform
terraform init
```

### 2. Deploy with Default Configuration

```bash
# Deploy Python runtime with ReAct agent
terraform apply

# Or with custom configuration
terraform apply \
  -var="runtime=go" \
  -var="agent_type=conversational" \
  -var="environment=staging"
```

### 3. Test the Deployment

```bash
# Get endpoint from outputs
terraform output api_gateway_invoke_url

# Use generated curl command
terraform output -raw curl_test_command | bash

# Or invoke directly via AWS CLI
terraform output -raw aws_cli_invoke_command | bash
```

### 4. View Logs

```bash
# Tail CloudWatch logs
terraform output -raw cloudwatch_logs_command | bash
```

## Configuration

### Basic Variables

Create a `terraform.tfvars` file:

```hcl
# Core settings
aws_region   = "us-east-1"
environment  = "dev"
runtime      = "python"  # or "go"
agent_type   = "react"   # react, conversational, router

# Lambda configuration
memory_size = 512
timeout     = 30
log_level   = "INFO"

# Feature flags
enable_function_url  = true
enable_api_gateway   = true
enable_alarms        = false
enable_bedrock       = false
enable_secrets_manager = false
```

### Advanced Configuration

#### Environment Variables

Pass custom environment variables to Lambda:

```hcl
environment_variables = {
  OPENAI_API_KEY     = "sk-..."          # Not recommended - use Secrets Manager
  MODEL_NAME         = "gpt-4"
  MAX_RETRIES        = "3"
  CUSTOM_SETTING     = "value"
}
```

#### Enable CloudWatch Alarms

```hcl
enable_alarms = true
alarm_error_threshold    = 10   # Errors per minute
alarm_throttle_threshold = 5    # Throttles per minute
alarm_duration_threshold = 25000  # Duration in ms
alarm_sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:my-alerts"
```

#### Enable AWS Services Access

```hcl
# For AWS Bedrock LLMs
enable_bedrock = true

# For Secrets Manager API keys
enable_secrets_manager = true
```

#### API Gateway Authentication

```hcl
api_gateway_auth_type = "AWS_IAM"  # Require IAM authentication

# Or for Cognito
api_gateway_auth_type = "COGNITO_USER_POOLS"
```

#### Function URL Configuration

```hcl
enable_function_url = true
function_url_auth_type = "AWS_IAM"  # Require IAM for Function URL
function_url_cors_origins = [
  "https://myapp.example.com",
  "https://api.example.com"
]
```

## Deployment Examples

### Development Environment (Python)

```bash
terraform apply \
  -var="environment=dev" \
  -var="runtime=python" \
  -var="agent_type=react" \
  -var="memory_size=256" \
  -var="enable_api_gateway=true" \
  -var="enable_function_url=true"
```

### Production Environment (Go)

```bash
terraform apply \
  -var="environment=prod" \
  -var="runtime=go" \
  -var="agent_type=router" \
  -var="memory_size=1024" \
  -var="enable_alarms=true" \
  -var="enable_bedrock=true" \
  -var="alarm_sns_topic_arn=arn:aws:sns:us-east-1:123456789012:prod-alerts"
```

### Multi-Environment Setup

Use workspaces for managing multiple environments:

```bash
# Create dev workspace
terraform workspace new dev
terraform apply -var-file="dev.tfvars"

# Create prod workspace
terraform workspace new prod
terraform apply -var-file="prod.tfvars"

# Switch between workspaces
terraform workspace select dev
terraform workspace select prod
```

## Outputs

After successful deployment, Terraform provides useful outputs:

```bash
# View all outputs
terraform output

# Specific outputs
terraform output lambda_function_name
terraform output api_gateway_invoke_url
terraform output function_url

# Use outputs in scripts
API_URL=$(terraform output -raw api_gateway_invoke_url)
curl -X POST $API_URL -H "Content-Type: application/json" -d '...'
```

### Available Outputs

- `lambda_function_name` - Lambda function name
- `lambda_function_arn` - Lambda ARN
- `function_url` - Lambda Function URL (if enabled)
- `api_gateway_invoke_url` - Full API Gateway URL (if enabled)
- `lambda_log_group_name` - CloudWatch log group name
- `deployment_config` - Summary of deployment configuration
- `curl_test_command` - Ready-to-use curl command
- `aws_cli_invoke_command` - AWS CLI invoke command
- `cloudwatch_logs_command` - Log tailing command

## Remote State

For team collaboration, use remote state storage:

### S3 Backend Configuration

Uncomment the backend block in `main.tf`:

```hcl
backend "s3" {
  bucket         = "my-terraform-state-bucket"
  key            = "agenkit-lambda/terraform.tfstate"
  region         = "us-east-1"
  encrypt        = true
  dynamodb_table = "terraform-state-lock"
}
```

### Create Backend Resources

```bash
# Create S3 bucket for state
aws s3api create-bucket \
  --bucket my-terraform-state-bucket \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket my-terraform-state-bucket \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for locking
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

## Building Lambda Functions

### Python Lambda

```bash
cd ../python

# Install dependencies
pip install -r requirements.txt -t .

# Terraform will automatically package the directory
```

### Go Lambda

```bash
cd ../go

# Build for Lambda (Linux x86_64)
GOOS=linux GOARCH=amd64 go build -tags lambda.norpc -o bootstrap main.go

# Or use Makefile
make build

# Terraform will package the bootstrap binary
```

## Monitoring

### CloudWatch Logs

```bash
# View logs
aws logs tail /aws/lambda/agenkit-dev-react --follow

# Or use Terraform output
$(terraform output -raw cloudwatch_logs_command)
```

### X-Ray Tracing

1. Open AWS X-Ray Console: https://console.aws.amazon.com/xray/
2. View Service Map for visual trace topology
3. Analyze traces for performance bottlenecks

### CloudWatch Metrics

Key metrics available in CloudWatch:
- `Invocations` - Total invocation count
- `Errors` - Error count
- `Duration` - Execution time
- `Throttles` - Throttle count
- `ConcurrentExecutions` - Concurrent invocations

### CloudWatch Alarms

If `enable_alarms = true`, three alarms are created:
1. **Error Alarm**: Triggers when error count exceeds threshold
2. **Throttle Alarm**: Triggers when throttle count exceeds threshold
3. **Duration Alarm**: Triggers when average duration exceeds threshold

## Cost Estimation

Use AWS Cost Explorer or estimate with:

**Lambda Costs (1M requests/month, 512 MB, 100ms avg):**
- Requests: 1M × $0.20/1M = $0.20
- Compute: 1M × 0.1s × 0.5 GB × $0.0000166667 = $0.83
- **Total: ~$1.03/month**

**API Gateway Costs:**
- Requests: 1M × $3.50/1M = $3.50
- **Total with API Gateway: ~$4.53/month**

**Cost Optimization:**
- Use Lambda Function URLs instead of API Gateway ($3.50 savings)
- Right-size memory (256 MB for simple agents)
- Set appropriate timeout (lower = cheaper)

## Security Best Practices

### 1. Use Secrets Manager for API Keys

```hcl
enable_secrets_manager = true

environment_variables = {
  OPENAI_SECRET_ARN = "arn:aws:secretsmanager:us-east-1:123456789012:secret:openai-key"
}
```

Then in your Lambda code, retrieve the secret:

```python
import boto3
import json

secrets = boto3.client('secretsmanager')
secret = secrets.get_secret_value(SecretId=os.environ['OPENAI_SECRET_ARN'])
api_key = json.loads(secret['SecretString'])['api_key']
```

### 2. Enable IAM Authentication

```hcl
api_gateway_auth_type = "AWS_IAM"
function_url_auth_type = "AWS_IAM"
```

### 3. Restrict CORS Origins

```hcl
function_url_cors_origins = [
  "https://myapp.example.com"  # Not "*"
]
```

### 4. Enable CloudWatch Alarms

```hcl
enable_alarms = true
alarm_sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:security-alerts"
```

## Troubleshooting

### Issue: Terraform can't find Lambda package

**Solution**: Ensure Lambda function is built before running Terraform:

```bash
# For Python
cd ../python && pip install -r requirements.txt -t .

# For Go
cd ../go && make build
```

### Issue: Permission denied errors

**Solution**: Check IAM role policies in `main.tf`. Enable required services:

```hcl
enable_bedrock = true
enable_secrets_manager = true
```

### Issue: API Gateway returning 502

**Solution**: Check Lambda execution role has correct permissions and Lambda is running successfully. View logs:

```bash
terraform output -raw cloudwatch_logs_command | bash
```

### Issue: Function timing out

**Solution**: Increase timeout and/or memory:

```hcl
timeout = 60
memory_size = 1024
```

## Cleanup

```bash
# Destroy all resources
terraform destroy

# Or destroy specific resources
terraform destroy -target=aws_api_gateway_rest_api.agenkit_api
```

## Module Usage

Use this configuration as a Terraform module:

```hcl
module "agenkit_lambda" {
  source = "./path/to/examples/deployment/aws-lambda/terraform"

  environment = "prod"
  runtime     = "go"
  agent_type  = "router"
  memory_size = 1024

  enable_alarms          = true
  enable_bedrock         = true
  enable_secrets_manager = true

  alarm_sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:alerts"
}

output "api_endpoint" {
  value = module.agenkit_lambda.api_gateway_invoke_url
}
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/agenkit/agenkit/issues
- Documentation: https://docs.agenkit.dev
