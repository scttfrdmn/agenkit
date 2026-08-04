# Agenkit on AWS Lambda

Deploy Agenkit agents as serverless functions on AWS Lambda with multiple deployment options and runtimes.

## Overview

This directory contains production-ready templates for deploying Agenkit agents on AWS Lambda with:

- ✅ **Multiple Runtimes**: Python 3.12 and Go (custom runtime)
- ✅ **Multiple Deployment Tools**: AWS SAM or Terraform
- ✅ **API Gateway Integration**: RESTful API with throttling and CORS
- ✅ **Lambda Function URLs**: Direct HTTPS endpoints
- ✅ **CloudWatch Logs**: Centralized logging with retention
- ✅ **X-Ray Tracing**: Distributed tracing and performance monitoring
- ✅ **Multiple Agent Types**: ReAct, Conversational, Router patterns
- ✅ **Production-Ready**: IAM roles, alarms, cost optimization

## Directory Structure

```
aws-lambda/
├── README.md                    # This file
├── .env.example                 # Environment variable template
├── python/                      # Python implementation
│   ├── handler.py              # Lambda handler with 3 agent types
│   ├── requirements.txt        # Python dependencies
│   ├── template.yaml           # SAM template
│   └── README.md               # Python deployment guide
├── go/                          # Go implementation
│   ├── main.go                 # Lambda handler with 3 agent types
│   ├── Makefile                # Build automation
│   ├── template.yaml           # SAM template
│   └── README.md               # Go deployment guide
└── terraform/                   # Terraform IaC
    ├── main.tf                 # Main Terraform configuration
    ├── variables.tf            # Input variables
    ├── outputs.tf              # Output values
    └── README.md               # Terraform deployment guide
```

## Quick Decision Matrix

Choose your deployment based on:

| Criterion | Python + SAM | Go + SAM | Terraform |
|-----------|--------------|----------|-----------|
| **Cold Start** | 200-400ms | 100-200ms | Depends on runtime |
| **Ease of Setup** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Performance** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Depends on runtime |
| **Cost (1M req)** | ~$1.03 | ~$0.62 | Depends on config |
| **IaC Maturity** | Good | Good | Excellent |
| **Learning Curve** | Low | Medium | Medium-High |
| **Best For** | Rapid prototyping | Production scale | Multi-service deployments |

## Quick Start

### Option 1: Python with SAM (Fastest Setup)

```bash
cd python

# Deploy with guided setup
sam deploy --guided

# Test deployment
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name agenkit-lambda-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)

curl -X POST $API_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{"agent_type": "react", "message": {"role": "user", "content": "Calculate 10 + 5"}}'
```

**See [python/README.md](python/README.md) for detailed instructions.**

### Option 2: Go with SAM (Best Performance)

```bash
cd go

# Build Lambda binary
make build

# Deploy with guided setup
make deploy-guided

# Test deployment
make invoke
```

**See [go/README.md](go/README.md) for detailed instructions.**

### Option 3: Terraform (Infrastructure as Code)

```bash
cd terraform

# Initialize Terraform
terraform init

# Deploy (defaults to Python)
terraform apply

# Or deploy Go runtime
terraform apply -var="runtime=go" -var="agent_type=router"

# Test deployment
terraform output -raw curl_test_command | bash
```

**See [terraform/README.md](terraform/README.md) for detailed instructions.**

## Runtime Comparison

### Python Implementation

**Pros:**
- ✅ Fastest to get started
- ✅ Rich LLM SDK ecosystem (OpenAI, Anthropic, LangChain)
- ✅ Easy debugging and iteration
- ✅ Smaller binary size

**Cons:**
- ❌ Slower cold starts (200-400ms)
- ❌ Higher memory usage
- ❌ Slightly higher cost

**Best for:**
- Rapid prototyping
- Development environments
- Teams familiar with Python
- Projects using Python-based LLM libraries

### Go Implementation

**Pros:**
- ✅ Fastest cold starts (100-200ms)
- ✅ Lowest memory usage
- ✅ Best performance
- ✅ ~40% cost savings vs Python

**Cons:**
- ❌ Requires compilation step
- ❌ Smaller LLM SDK ecosystem
- ❌ More verbose code

**Best for:**
- Production deployments
- High-traffic applications
- Cost-sensitive workloads
- Teams familiar with Go
- Performance-critical use cases

## Deployment Tools Comparison

### AWS SAM (Serverless Application Model)

**Pros:**
- ✅ Purpose-built for serverless
- ✅ Local testing with `sam local`
- ✅ Simple YAML templates
- ✅ Faster iteration

**Cons:**
- ❌ Limited to AWS Lambda
- ❌ Less flexibility for complex infrastructure

**Best for:**
- Lambda-only deployments
- Quick prototypes
- Teams new to IaC
- Local development and testing

### Terraform

**Pros:**
- ✅ Full infrastructure control
- ✅ Multi-cloud support
- ✅ Advanced features (modules, workspaces)
- ✅ Better for complex architectures

**Cons:**
- ❌ Steeper learning curve
- ❌ More configuration needed
- ❌ No built-in local testing

**Best for:**
- Production environments
- Multi-service deployments
- Organizations using Terraform
- Complex infrastructure needs

## Agent Types

All implementations support three agent patterns:

### 1. ReAct Agent
- Reasoning and tool use
- Best for: Computational tasks, API calls, structured workflows
- Example: Calculator, weather lookup, database queries

### 2. Conversational Agent
- Multi-turn conversations with memory
- Best for: Chatbots, customer support, interactive assistants
- Example: FAQ bot, support agent, virtual assistant

### 3. Router Agent
- Intelligent routing to specialist agents
- Best for: Complex tasks requiring multiple capabilities
- Example: Multi-domain support, task classification, orchestration

## Configuration

### Environment Variables

Copy `.env.example` and customize:

```bash
cp .env.example .env
```

**Key variables:**
- `ENVIRONMENT` - dev, staging, prod
- `AGENT_TYPE` - react, conversational, router
- `LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR
- `OPENAI_API_KEY` - OpenAI API key (if using OpenAI)
- `ANTHROPIC_API_KEY` - Anthropic API key (if using Claude)

### LLM Integration

Replace mock implementations with real LLMs:

**Python:**
```python
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

class OpenAILLM:
    async def process(self, message: Message) -> Message:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": message.content}]
        )
        return Message(
            role="assistant",
            content=response.choices[0].message.content
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
    // ...
}
```

## Monitoring

### CloudWatch Logs

**Python:**
```bash
sam logs -n AgenkitFunction --tail
```

**Go:**
```bash
make logs
```

**Terraform:**
```bash
terraform output -raw cloudwatch_logs_command | bash
```

### X-Ray Tracing

1. Open AWS X-Ray Console: https://console.aws.amazon.com/xray/
2. View Service Map for request flow
3. Analyze traces for:
   - Cold start duration
   - Agent execution time
   - API call latency
   - Error rates

### CloudWatch Metrics

Key metrics to monitor:
- **Invocations**: Total request count
- **Duration**: Execution time (target: <1000ms)
- **Errors**: Error rate (target: <1%)
- **Throttles**: Rate limiting events
- **ConcurrentExecutions**: Concurrent invocations

## Cost Optimization

### Estimated Costs (1M requests/month)

| Runtime | Memory | Avg Duration | Compute Cost | Request Cost | Total |
|---------|--------|--------------|--------------|--------------|-------|
| Python  | 512 MB | 100ms        | $0.83        | $0.20        | $1.03 |
| Go      | 512 MB | 50ms         | $0.42        | $0.20        | $0.62 |
| Go      | 256 MB | 50ms         | $0.21        | $0.20        | $0.41 |

### Cost Reduction Strategies

1. **Right-size Memory**: Start with 256 MB, increase if needed
2. **Use Lambda Function URLs**: Save $3.50/M requests vs API Gateway
3. **Optimize Cold Starts**: Faster = cheaper
4. **Use Provisioned Concurrency**: Only for high-traffic, predictable workloads
5. **Choose Go Runtime**: 40-60% cost savings vs Python

## Security

### Best Practices

1. **Use Secrets Manager** for API keys
2. **Enable IAM authentication** for API Gateway/Function URLs
3. **Restrict CORS origins** (don't use `*` in production)
4. **Enable CloudWatch Alarms** for anomaly detection
5. **Use VPC** if accessing private resources
6. **Enable CloudTrail** for audit logging

### IAM Permissions

Required policies:
- `AWSLambdaBasicExecutionRole` - CloudWatch Logs
- `AWSXRayDaemonWriteAccess` - X-Ray tracing

Optional policies:
- `AmazonBedrockFullAccess` - AWS Bedrock LLMs
- `SecretsManagerReadWrite` - Secrets Manager

## Testing

### Local Testing

**Python:**
```bash
python handler.py  # Run directly
```

**Go:**
```bash
go run main.go  # Local test
```

**SAM Local:**
```bash
sam local start-api  # Start local API
sam local invoke AgenkitFunction -e events/test-event.json
```

### Integration Testing

```bash
# Test deployed endpoint
API_ENDPOINT="https://..."

curl -X POST $API_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "react",
    "message": {
      "role": "user",
      "content": "Calculate 15 * 3"
    }
  }'
```

### Load Testing

```bash
# Use Apache Bench
ab -n 1000 -c 10 -T application/json -p request.json $API_ENDPOINT

# Or use Artillery
artillery quick --count 100 --num 10 $API_ENDPOINT
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Cold start timeouts | Increase memory, reduce package size |
| Permission errors | Check IAM role policies |
| Import errors | Verify dependencies in requirements.txt/go.mod |
| X-Ray not showing traces | Enable tracing in Lambda and API Gateway |
| 502 Bad Gateway | Check Lambda logs for errors |

### Debug Commands

```bash
# View CloudWatch logs
aws logs tail /aws/lambda/agenkit-dev-react --follow

# Invoke directly with AWS CLI
aws lambda invoke \
  --function-name agenkit-dev-react \
  --payload '{"body": "..."}' \
  response.json

# Check function configuration
aws lambda get-function-configuration \
  --function-name agenkit-dev-react
```

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Deploy Lambda

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      # Python deployment
      - name: Deploy Python with SAM
        run: |
          cd examples/deployment/aws-lambda/python
          sam deploy --no-confirm-changeset --no-fail-on-empty-changeset

      # Go deployment
      - name: Deploy Go with SAM
        run: |
          cd examples/deployment/aws-lambda/go
          make build
          sam deploy --no-confirm-changeset

      # Terraform deployment
      - name: Deploy with Terraform
        run: |
          cd examples/deployment/aws-lambda/terraform
          terraform init
          terraform apply -auto-approve
```

## Next Steps

1. **Choose your runtime** (Python for speed, Go for performance)
2. **Choose your deployment tool** (SAM for simplicity, Terraform for flexibility)
3. **Replace mock LLMs** with real implementations (OpenAI, Anthropic, Bedrock)
4. **Configure monitoring** (CloudWatch dashboards, X-Ray traces)
5. **Set up CI/CD** (GitHub Actions, GitLab CI, etc.)
6. **Enable alarms** (error rates, duration, throttles)
7. **Optimize costs** (right-size memory, use Function URLs)

## Support

For issues and questions:
- GitHub Issues: https://github.com/scttfrdmn/agenkit/issues
- Documentation: https://docs.agenkit.dev
- Examples: https://github.com/scttfrdmn/agenkit/tree/main/examples
