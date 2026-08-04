# Deploying Agenkit on AWS Lambda

Complete guide to deploying Agenkit agents as serverless functions on AWS Lambda with production-ready configurations.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Deployment Options](#deployment-options)
- [Runtime Selection](#runtime-selection)
- [Agent Types](#agent-types)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Security](#security)
- [Performance Optimization](#performance-optimization)
- [Cost Analysis](#cost-analysis)
- [Troubleshooting](#troubleshooting)
- [Production Checklist](#production-checklist)

## Overview

AWS Lambda provides a serverless execution environment for Agenkit agents with:

- ✅ **Zero server management**
- ✅ **Automatic scaling** (0 to thousands of concurrent executions)
- ✅ **Pay-per-use pricing** (~$0.40-$1.00 per 1M requests)
- ✅ **Built-in integration** with AWS services (API Gateway, X-Ray, CloudWatch)
- ✅ **High availability** (99.95% SLA)
- ✅ **Fast cold starts** (100-400ms depending on runtime)

## Architecture

### High-Level Architecture

```
┌─────────────┐         ┌──────────────┐         ┌────────────────┐
│   Client    │ ──────> │ API Gateway  │ ──────> │ Lambda Function│
└─────────────┘         └──────────────┘         └────────────────┘
                                │                         │
                                │                         │
                        ┌───────▼────────┐       ┌────────▼────────┐
                        │  CloudWatch    │       │    X-Ray        │
                        │   (Logging)    │       │   (Tracing)     │
                        └────────────────┘       └─────────────────┘
                                │
                        ┌───────▼────────┐
                        │  CloudWatch    │
                        │   (Metrics)    │
                        └────────────────┘
```

### Component Breakdown

1. **API Gateway**: HTTP API endpoint with throttling, CORS, and authentication
2. **Lambda Function**: Serverless compute running Agenkit agent
3. **CloudWatch Logs**: Centralized logging with retention policies
4. **X-Ray**: Distributed tracing for performance analysis
5. **CloudWatch Metrics**: Performance metrics and alarms
6. **Lambda Function URL** (optional): Direct HTTPS endpoint bypassing API Gateway

## Prerequisites

### Required

- **AWS Account** with appropriate permissions
- **AWS CLI** configured (`aws configure`)
- **IAM permissions** for Lambda, API Gateway, CloudWatch, X-Ray

### Deployment Tool (choose one)

**Option 1: AWS SAM** (recommended for beginners)
```bash
# Install SAM CLI
brew install aws-sam-cli

# Or with pip
pip install aws-sam-cli
```

**Option 2: Terraform** (recommended for advanced users)
```bash
# Install Terraform
brew install terraform

# Or download from terraform.io
```

### Runtime-Specific

**Python:**
- Python 3.12+
- pip

**Go:**
- Go 1.25.12+
- Make

## Quick Start

### 1. Choose Your Deployment Path

| Path | Setup Time | Best For | Complexity |
|------|------------|----------|------------|
| Python + SAM | 5 minutes | Rapid prototyping | ⭐ |
| Go + SAM | 10 minutes | Production deployments | ⭐⭐ |
| Terraform | 15 minutes | Infrastructure as Code | ⭐⭐⭐ |

### 2. Deploy

**Python with SAM:**
```bash
cd examples/deployment/aws-lambda/python
sam deploy --guided
```

**Go with SAM:**
```bash
cd examples/deployment/aws-lambda/go
make build
sam deploy --guided
```

**Terraform:**
```bash
cd examples/deployment/aws-lambda/terraform
terraform init
terraform apply
```

### 3. Test

```bash
# Get endpoint
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name agenkit-lambda-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)

# Test request
curl -X POST $API_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "react",
    "message": {
      "role": "user",
      "content": "Calculate 10 + 5"
    }
  }'
```

## Deployment Options

### Option 1: SAM (Serverless Application Model)

**Pros:**
- Purpose-built for Lambda
- Local testing with `sam local`
- Fast iteration
- Simple YAML configuration

**Cons:**
- AWS-specific
- Less flexibility for complex infrastructure

**When to use:**
- Lambda-only projects
- Quick prototypes
- Teams new to IaC

**Example:**
```bash
# Deploy
sam deploy --guided

# Test locally
sam local start-api

# View logs
sam logs -n AgenkitFunction --tail
```

### Option 2: Terraform

**Pros:**
- Full infrastructure control
- Multi-cloud support
- Reusable modules
- Workspace management

**Cons:**
- Steeper learning curve
- More configuration
- No built-in local testing

**When to use:**
- Production environments
- Multi-service deployments
- Organizations using Terraform

**Example:**
```bash
# Deploy
terraform init
terraform apply

# Multiple environments
terraform workspace new staging
terraform apply -var-file=staging.tfvars
```

## Runtime Selection

### Python

**Performance:**
- Cold start: 200-400ms
- Warm execution: 50-150ms
- Memory usage: 256-512 MB
- Package size: 30-50 MB

**Pros:**
- Fastest development
- Rich LLM SDK ecosystem
- Easy debugging

**Cons:**
- Slower cold starts
- Higher memory usage
- Slightly higher cost

**Best for:**
- Rapid prototyping
- Development environments
- Python-based LLM libraries

### Go

**Performance:**
- Cold start: 100-200ms
- Warm execution: 10-50ms
- Memory usage: 128-256 MB
- Package size: 10-20 MB

**Pros:**
- Fastest cold starts
- Lowest memory usage
- Best performance
- ~40% cost savings

**Cons:**
- Compilation required
- Smaller SDK ecosystem
- More verbose

**Best for:**
- Production deployments
- High-traffic applications
- Cost-sensitive workloads

### Performance Comparison

| Metric | Python | Go | Winner |
|--------|--------|-----|--------|
| Cold Start | 300ms | 150ms | Go |
| Warm Execution | 100ms | 30ms | Go |
| Memory Usage | 512 MB | 256 MB | Go |
| Development Speed | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Python |
| Cost (1M req) | $1.03 | $0.62 | Go |

## Agent Types

All deployments support three agent patterns:

### 1. ReAct Agent

**Description:** Reasoning and tool use agent

**Use Cases:**
- Computational tasks (calculator, math)
- API calls (weather, stock prices)
- Database queries
- Structured workflows

**Example Request:**
```json
{
  "agent_type": "react",
  "message": {
    "role": "user",
    "content": "Calculate the square root of 144"
  }
}
```

**Tools Included:**
- Calculator (add, subtract, multiply, divide)
- Extendable to custom tools

### 2. Conversational Agent

**Description:** Multi-turn conversation with memory

**Use Cases:**
- Chatbots
- Customer support
- Interactive assistants
- FAQ systems

**Example Request:**
```json
{
  "agent_type": "conversational",
  "message": {
    "role": "user",
    "content": "Hello! How can you help me?"
  }
}
```

**Features:**
- Conversation history (configurable length)
- System prompt customization
- Context preservation

### 3. Router Agent

**Description:** Intelligent routing to specialist agents

**Use Cases:**
- Multi-domain support
- Task classification
- Orchestration
- Complex workflows

**Example Request:**
```json
{
  "agent_type": "router",
  "message": {
    "role": "user",
    "content": "Calculate 10 + 5 and tell me about the weather"
  }
}
```

**Routing Logic:**
- Keyword-based routing (customizable)
- Routes to ReAct or Conversational specialists
- Fallback to default agent

## Configuration

### Environment Variables

Key configuration options (see `.env.example`):

```bash
# Core settings
ENVIRONMENT=dev                    # dev, staging, prod
AWS_REGION=us-east-1              # AWS region
AGENT_TYPE=react                  # react, conversational, router
RUNTIME=python                    # python or go

# Lambda configuration
MEMORY_SIZE=512                   # MB (128-10240)
TIMEOUT=30                        # seconds (1-900)
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR

# Feature flags
ENABLE_API_GATEWAY=true           # API Gateway integration
ENABLE_FUNCTION_URL=true          # Lambda Function URL
ENABLE_XRAY_TRACING=true          # X-Ray tracing
ENABLE_ALARMS=false               # CloudWatch alarms
```

### LLM Integration

#### OpenAI

**Python:**
```python
import openai
import os

openai.api_key = os.environ["OPENAI_API_KEY"]

class OpenAILLM:
    async def process(self, message: Message) -> Message:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{"role": "user", "content": message.content}]
        )
        return Message(
            role="assistant",
            content=response.choices[0].message.content,
            metadata={"model": "gpt-4", "tokens": response.usage.total_tokens}
        )
```

**Go:**
```go
import "github.com/sashabaranov/go-openai"

type OpenAILLM struct {
    client *openai.Client
}

func (o *OpenAILLM) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    resp, err := o.client.CreateChatCompletion(ctx, openai.ChatCompletionRequest{
        Model: openai.GPT4,
        Messages: []openai.ChatCompletionMessage{
            {Role: "user", Content: msg.Content},
        },
    })
    if err != nil {
        return nil, err
    }

    return &agenkit.Message{
        Role:    "assistant",
        Content: resp.Choices[0].Message.Content,
        Metadata: map[string]interface{}{
            "model":  resp.Model,
            "tokens": resp.Usage.TotalTokens,
        },
    }, nil
}
```

#### AWS Bedrock

**Advantages:**
- No API keys needed (uses IAM)
- Regional data residency
- Enterprise support

**Configuration:**
```hcl
# Terraform
enable_bedrock = true

# Or SAM template.yaml
Policies:
  - AmazonBedrockFullAccess
```

**Python:**
```python
import boto3
import json

bedrock = boto3.client('bedrock-runtime')

class BedrockLLM:
    async def process(self, message: Message) -> Message:
        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps({
                "messages": [{"role": "user", "content": message.content}],
                "max_tokens": 1024,
                "anthropic_version": "bedrock-2023-05-31"
            })
        )
        result = json.loads(response['body'].read())
        return Message(
            role="assistant",
            content=result['content'][0]['text']
        )
```

## Monitoring

### CloudWatch Logs

**View logs:**
```bash
# With SAM
sam logs -n AgenkitFunction --tail

# With AWS CLI
aws logs tail /aws/lambda/agenkit-dev-react --follow

# With Terraform
terraform output -raw cloudwatch_logs_command | bash
```

**Log structure:**
```
START RequestId: abc-123 Version: $LATEST
[INFO] Processing request for agent_type=react
[INFO] Agent execution time: 45ms
[INFO] Response generated successfully
END RequestId: abc-123
REPORT RequestId: abc-123
Duration: 123.45 ms
Billed Duration: 124 ms
Memory Size: 512 MB
Max Memory Used: 89 MB
```

### X-Ray Tracing

**Access X-Ray Console:**
https://console.aws.amazon.com/xray/home#/service-map

**Trace structure:**
1. **Main segment**: `agenkit-lambda` or `agenkit-lambda-go`
2. **Subsegment 1**: `create-agent-{type}` (agent initialization)
3. **Subsegment 2**: `agent-execution` (agent processing)

**Analyze traces for:**
- Cold start duration (first invocation)
- Agent creation time
- Processing time
- Total latency
- Error rates

### CloudWatch Metrics

**Key metrics:**

| Metric | Description | Target |
|--------|-------------|--------|
| Invocations | Total requests | N/A |
| Duration | Execution time | <1000ms |
| Errors | Error count | <1% |
| Throttles | Rate limiting | 0 |
| ConcurrentExecutions | Concurrent invocations | <80% of limit |

**Custom metrics:**
```python
# Python
import boto3

cloudwatch = boto3.client('cloudwatch')

cloudwatch.put_metric_data(
    Namespace='Agenkit',
    MetricData=[{
        'MetricName': 'AgentExecutionTime',
        'Value': execution_time_ms,
        'Unit': 'Milliseconds'
    }]
)
```

### CloudWatch Alarms

**Enable alarms in Terraform:**
```hcl
enable_alarms = true
alarm_error_threshold = 10          # Errors per minute
alarm_throttle_threshold = 5        # Throttles per minute
alarm_duration_threshold = 25000    # Duration in ms
alarm_sns_topic_arn = "arn:aws:sns:..."
```

**Alarm types:**
1. **Error Alarm**: Triggers when error rate exceeds threshold
2. **Throttle Alarm**: Triggers when throttling occurs
3. **Duration Alarm**: Triggers when execution time is too high

## Security

### IAM Roles and Policies

**Minimum required policies:**
- `AWSLambdaBasicExecutionRole` - CloudWatch Logs access
- `AWSXRayDaemonWriteAccess` - X-Ray tracing

**Optional policies:**
- `AmazonBedrockFullAccess` - AWS Bedrock LLMs
- `SecretsManagerReadWrite` - Secrets Manager access

**Best practice:** Use least-privilege access

### API Authentication

**Options:**

1. **NONE** (default for development)
   - No authentication
   - Use only for testing

2. **AWS_IAM**
   - Requires AWS signature
   - Best for AWS-to-AWS communication

3. **API Keys**
   - Simple key-based auth
   - Good for external partners

4. **Cognito User Pools**
   - User authentication
   - Best for end-user applications

**Enable IAM authentication:**
```hcl
# Terraform
api_gateway_auth_type = "AWS_IAM"
function_url_auth_type = "AWS_IAM"
```

### Secrets Management

**Use AWS Secrets Manager for API keys:**

1. **Create secret:**
   ```bash
   aws secretsmanager create-secret \
     --name prod/openai/api_key \
     --secret-string '{"api_key": "sk-..."}'
   ```

2. **Grant Lambda access:**
   ```hcl
   enable_secrets_manager = true
   ```

3. **Retrieve in code:**
   ```python
   import boto3
   import json

   secrets = boto3.client('secretsmanager')
   secret = secrets.get_secret_value(SecretId='prod/openai/api_key')
   api_key = json.loads(secret['SecretString'])['api_key']
   ```

**Do NOT:** Store API keys in environment variables or code

### CORS Configuration

**Development (permissive):**
```yaml
Cors:
  AllowOrigin: "'*'"
  AllowMethods: "'POST, OPTIONS'"
```

**Production (restrictive):**
```hcl
function_url_cors_origins = [
  "https://myapp.example.com",
  "https://api.example.com"
]
```

## Performance Optimization

### Cold Start Reduction

**Strategies:**

1. **Increase Memory** (more memory = faster CPU)
   ```hcl
   memory_size = 1024  # Instead of 512
   ```
   - Effect: 30-50% faster cold starts
   - Cost: +100% (but faster = cheaper per request)

2. **Provisioned Concurrency** (keep instances warm)
   ```yaml
   ProvisionedConcurrencyConfig:
     ProvisionedConcurrentExecutions: 5
   ```
   - Effect: Eliminates cold starts
   - Cost: ~$15/month per instance
   - Use for: Production high-traffic APIs

3. **Reduce Package Size**
   - Python: Use slim dependencies
   - Go: Build with `-ldflags="-s -w"`
   - Effect: 10-20% faster cold starts

4. **Choose Go Runtime**
   - Effect: 50% faster cold starts vs Python
   - Trade-off: More development effort

### Warm Execution Optimization

1. **Connection Pooling**
   ```python
   # Global client (reused across invocations)
   import httpx
   http_client = httpx.AsyncClient()
   ```

2. **Caching**
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=128)
   def expensive_operation(input):
       # Cached across invocations
       pass
   ```

3. **Lazy Initialization**
   - Initialize LLM clients only when needed
   - Cache model weights in `/tmp` (512 MB available)

### Timeout Configuration

**Guidelines:**

| Agent Type | Typical Duration | Recommended Timeout |
|-----------|------------------|---------------------|
| ReAct (simple) | 100-500ms | 10s |
| ReAct (complex) | 1-3s | 30s |
| Conversational | 500ms-2s | 15s |
| Router | 1-5s | 30s |

**Set timeout:**
```hcl
timeout = 30  # seconds
```

**Monitor with CloudWatch Metrics:**
- Review p50, p90, p99 duration
- Set timeout to p99 + 20% buffer

## Cost Analysis

### Pricing Model

**Lambda Costs:**
- **Requests**: $0.20 per 1M requests
- **Duration**: $0.0000166667 per GB-second
- **Formula**: `(requests × $0.20/1M) + (requests × duration × memory_GB × $0.0000166667)`

**API Gateway Costs:**
- **Requests**: $3.50 per 1M requests

**Lambda Function URL Costs:**
- **Requests**: $0.10 per 1M requests (vs $3.50 for API Gateway)

### Cost Examples

#### Example 1: Low Traffic (100K requests/month)

**Python (512 MB, 100ms avg):**
- Requests: 100K × $0.20/1M = $0.02
- Compute: 100K × 0.1s × 0.5 GB × $0.0000166667 = $0.08
- API Gateway: 100K × $3.50/1M = $0.35
- **Total: $0.45/month**

**Go (256 MB, 50ms avg):**
- Requests: 100K × $0.20/1M = $0.02
- Compute: 100K × 0.05s × 0.25 GB × $0.0000166667 = $0.02
- API Gateway: 100K × $3.50/1M = $0.35
- **Total: $0.39/month**

#### Example 2: Medium Traffic (1M requests/month)

**Python (512 MB, 100ms avg):**
- Requests: $0.20
- Compute: $0.83
- API Gateway: $3.50
- **Total: $4.53/month**

**Go (256 MB, 50ms avg):**
- Requests: $0.20
- Compute: $0.21
- API Gateway: $3.50
- **Total: $3.91/month** (14% savings)

#### Example 3: High Traffic (10M requests/month)

**Python (512 MB, 100ms avg):**
- Requests: $2.00
- Compute: $8.33
- API Gateway: $35.00
- **Total: $45.33/month**

**Go (256 MB, 50ms avg):**
- Requests: $2.00
- Compute: $2.08
- API Gateway: $35.00
- **Total: $39.08/month** (14% savings)

### Cost Optimization Strategies

1. **Use Lambda Function URLs instead of API Gateway**
   - Savings: $3.40 per 1M requests (97% on API costs)
   - Trade-off: Fewer features (no throttling, caching)

2. **Choose Go runtime**
   - Savings: ~40% on compute costs
   - Trade-off: More development effort

3. **Right-size memory**
   - Start with 256 MB, increase if needed
   - Monitor with CloudWatch metrics

4. **Optimize execution time**
   - Faster execution = lower cost
   - Use profiling to find bottlenecks

5. **Use provisioned concurrency only when needed**
   - Eliminates cold starts but costs ~$15/month per instance
   - Use for high-traffic, latency-sensitive APIs only

## Troubleshooting

### Common Issues

#### Issue: Cold start timeouts

**Symptoms:**
- Requests failing with timeout errors
- Duration close to configured timeout

**Solutions:**
1. Increase memory (more memory = faster CPU)
2. Reduce package size
3. Use provisioned concurrency
4. Choose Go runtime

**Example:**
```hcl
memory_size = 1024  # Double the memory
timeout = 60        # Increase timeout
```

#### Issue: Permission errors

**Symptoms:**
- "Access denied" errors
- Unable to write to CloudWatch Logs
- Unable to send X-Ray traces

**Solutions:**
1. Check IAM role has required policies
2. Add missing policies in `template.yaml` or `main.tf`

**Example (Terraform):**
```hcl
enable_bedrock = true
enable_secrets_manager = true
```

#### Issue: Import errors

**Symptoms:**
- "ModuleNotFoundError" (Python)
- "undefined: package" (Go)

**Solutions:**
1. Python: Ensure dependencies in `requirements.txt` and installed
2. Go: Run `go mod tidy` and rebuild

**Example:**
```bash
# Python
pip install -r requirements.txt -t .

# Go
cd go && make build
```

#### Issue: X-Ray not showing traces

**Symptoms:**
- No traces in X-Ray console
- Service map empty

**Solutions:**
1. Enable tracing in Lambda function
2. Enable tracing in API Gateway
3. Check IAM role has `AWSXRayDaemonWriteAccess`

**Example (SAM):**
```yaml
Tracing: Active  # Lambda function

TracingEnabled: true  # API Gateway
```

#### Issue: 502 Bad Gateway

**Symptoms:**
- API Gateway returns 502
- "Internal server error"

**Solutions:**
1. Check Lambda execution logs
2. Verify Lambda function is running
3. Check return format matches API Gateway expectations

**Debug:**
```bash
# View logs
aws logs tail /aws/lambda/agenkit-dev-react --follow

# Invoke directly (bypass API Gateway)
aws lambda invoke \
  --function-name agenkit-dev-react \
  --payload '{"body": "..."}' \
  response.json
```

### Debug Tools

**CloudWatch Logs Insights:**
```sql
# Find errors
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 20

# Find slow requests
fields @timestamp, @duration
| filter @duration > 1000
| sort @duration desc
| limit 20
```

**X-Ray Trace Analysis:**
1. Open X-Ray Console
2. Filter by error status
3. Analyze trace timeline
4. Identify bottlenecks

**Local Testing:**
```bash
# SAM
sam local invoke AgenkitFunction -e events/test-event.json

# Manual testing
python handler.py  # Python
go run main.go     # Go
```

## Production Checklist

### Before Deployment

- [ ] LLM integration configured (replace mock implementations)
- [ ] API keys stored in Secrets Manager (not environment variables)
- [ ] IAM authentication enabled (`AWS_IAM`)
- [ ] CORS origins restricted (not `*`)
- [ ] CloudWatch alarms configured
- [ ] Error handling tested
- [ ] Load testing completed
- [ ] Memory and timeout optimized
- [ ] Cost estimation reviewed

### After Deployment

- [ ] API endpoint tested with production data
- [ ] CloudWatch Logs verified
- [ ] X-Ray traces reviewed
- [ ] Metrics dashboard created
- [ ] Alarms tested (trigger and notification)
- [ ] Documentation updated
- [ ] Team trained on monitoring
- [ ] Runbook created for incidents
- [ ] Backup/rollback plan documented

### Ongoing Maintenance

- [ ] Monitor CloudWatch metrics weekly
- [ ] Review X-Ray traces for performance degradation
- [ ] Analyze cost reports monthly
- [ ] Update dependencies quarterly
- [ ] Review security policies quarterly
- [ ] Test disaster recovery annually

## Additional Resources

- **Examples**: `/examples/deployment/aws-lambda/`
- **Python Guide**: `/examples/deployment/aws-lambda/python/README.md`
- **Go Guide**: `/examples/deployment/aws-lambda/go/README.md`
- **Terraform Guide**: `/examples/deployment/aws-lambda/terraform/README.md`
- **GitHub Issues**: https://github.com/scttfrdmn/agenkit/issues
- **Documentation**: https://docs.agenkit.dev

## Support

For issues and questions:
- GitHub Issues: https://github.com/scttfrdmn/agenkit/issues
- Documentation: https://docs.agenkit.dev
- Community Discord: https://discord.gg/agenkit
