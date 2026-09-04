# Agenkit on AWS Lambda - Go Implementation

Deploy Agenkit agents as high-performance serverless functions on AWS Lambda with API Gateway integration, CloudWatch logging, and X-Ray tracing.

## Features

- ✅ **Multiple Agent Types**: ReAct, Conversational, Router patterns
- ✅ **High Performance**: Go's native compilation for fast cold starts
- ✅ **API Gateway Integration**: RESTful API for agent invocation
- ✅ **Lambda Function URLs**: Direct HTTPS endpoints
- ✅ **X-Ray Tracing**: Distributed tracing with subsegments
- ✅ **CloudWatch Logging**: Structured logging
- ✅ **SAM Deployment**: Infrastructure as Code
- ✅ **Minimal Cold Start**: ~100ms with Go's native binary

## Quick Start

### Prerequisites

- AWS CLI configured (`aws configure`)
- AWS SAM CLI installed (`brew install aws-sam-cli`)
- Go 1.25.14+
- Make
- Active AWS account

### 1. Build and Deploy

```bash
# Build the Lambda function
make build

# Deploy with guided setup (first time)
make deploy-guided

# For subsequent deployments
make deploy
```

**Guided deployment prompts:**
- Stack Name: `agenkit-lambda-go-dev`
- AWS Region: `us-east-1`
- Parameter Environment: `dev`
- Parameter AgentType: `react`
- Confirm changes before deploy: `Y`
- Allow SAM CLI IAM role creation: `Y`
- Save arguments to samconfig.toml: `Y`

### 2. Test the Deployment

```bash
# Show stack outputs (API endpoint, Function URL)
make outputs

# Invoke via API Gateway
make invoke

# Or manually with curl
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name agenkit-lambda-go-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)

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

### 3. Test with Function URL (Direct)

```bash
# Get Function URL from outputs
FUNCTION_URL=$(aws cloudformation describe-stacks \
  --stack-name agenkit-lambda-go-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`FunctionUrl`].OutputValue' \
  --output text)

# Invoke directly
curl -X POST $FUNCTION_URL \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "conversational",
    "message": {
      "role": "user",
      "content": "Hello! How are you?"
    }
  }'
```

## Configuration

### Environment Variables

Configure in `template.yaml`:

```yaml
Environment:
  Variables:
    ENVIRONMENT: dev
    AGENT_TYPE: react
    LOG_LEVEL: INFO
    # Add LLM API keys (or use Secrets Manager)
    # OPENAI_API_KEY: !Ref OpenAIAPIKey
    # ANTHROPIC_API_KEY: !Ref AnthropicAPIKey
```

Or override during deployment:

```bash
ENVIRONMENT=staging AGENT_TYPE=conversational make deploy
```

### Memory and Timeout

Adjust in `template.yaml`:

```yaml
Globals:
  Function:
    Timeout: 30          # Seconds
    MemorySize: 512      # MB
```

**Recommendations:**
- **Simple agents**: 256 MB, 10s timeout
- **LLM agents**: 512 MB, 30s timeout
- **Complex workflows**: 1024 MB, 60s timeout

### LLM Integration

#### OpenAI

Replace `MockLLM` in `main.go`:

```go
import "github.com/sashabaranov/go-openai"

type OpenAILLM struct {
    client *openai.Client
}

func (o *OpenAILLM) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
    resp, err := o.client.CreateChatCompletion(ctx, openai.ChatCompletionRequest{
        Model: openai.GPT4,
        Messages: []openai.ChatCompletionMessage{
            {Role: "user", Content: message.Content},
        },
    })
    if err != nil {
        return nil, fmt.Errorf("openai request failed: %w", err)
    }

    return &agenkit.Message{
        Role:    "assistant",
        Content: resp.Choices[0].Message.Content,
        Metadata: map[string]interface{}{
            "model": resp.Model,
            "tokens": resp.Usage.TotalTokens,
        },
    }, nil
}
```

#### AWS Bedrock

```go
import (
    "github.com/aws/aws-sdk-go-v2/config"
    "github.com/aws/aws-sdk-go-v2/service/bedrockruntime"
)

type BedrockLLM struct {
    client *bedrockruntime.Client
}

func NewBedrockLLM(ctx context.Context) (*BedrockLLM, error) {
    cfg, err := config.LoadDefaultConfig(ctx)
    if err != nil {
        return nil, err
    }

    return &BedrockLLM{
        client: bedrockruntime.NewFromConfig(cfg),
    }, nil
}

func (b *BedrockLLM) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
    // Invoke Claude on Bedrock
    // ...
}
```

## Monitoring

### CloudWatch Logs

```bash
# View logs with SAM
make logs

# Or with AWS CLI
aws logs tail /aws/lambda/agenkit-go-dev-react --follow
```

### X-Ray Tracing

The Go implementation includes detailed X-Ray subsegments:

1. Open AWS X-Ray Console
2. View Service Map: `https://console.aws.amazon.com/xray/home#/service-map`
3. View traces with subsegments:
   - `create-agent-{type}` - Agent creation time
   - `agent-execution` - Agent processing time

### Metrics

Key CloudWatch metrics:
- `Invocations` - Request count
- `Duration` - Execution time (typically 50-200ms with Go)
- `Errors` - Error count
- `Throttles` - Rate limiting
- `ConcurrentExecutions` - Concurrent invocations

## Performance Optimization

### Cold Start Performance

Go typically has the fastest cold starts among Lambda runtimes:

| Runtime | Typical Cold Start |
|---------|-------------------|
| **Go (custom runtime)** | **100-200ms** |
| Python 3.12 | 200-400ms |
| Node.js 20 | 150-300ms |
| Java 21 | 1-3s |

### Further Optimization

1. **Increase Memory**: More memory = faster CPU
   ```yaml
   MemorySize: 1024  # Instead of 512
   ```

2. **Provisioned Concurrency**: Keep instances warm
   ```yaml
   ProvisionedConcurrencyConfig:
     ProvisionedConcurrentExecutions: 5
   ```

3. **Reduce Binary Size**:
   ```bash
   # Build with size optimization
   GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o bootstrap main.go

   # Use UPX compression (optional)
   upx --best --lzma bootstrap
   ```

4. **Connection Pooling**: Initialize clients outside handler
   ```go
   // Global HTTP client
   var httpClient = &http.Client{
       Timeout: 30 * time.Second,
   }

   func main() {
       lambda.Start(handleRequest)  // Reuses httpClient
   }
   ```

## Cost Optimization

### Pricing Model

**Lambda Costs:**
- Requests: $0.20 per 1M requests
- Duration: $0.0000166667 per GB-second

**Example Cost (512 MB, 50ms average):**
- 1M requests/month
- Compute: 1M × 0.05s × 0.5 GB × $0.0000166667 = $0.42
- Requests: 1M × $0.20/1M = $0.20
- **Total: ~$0.62/month** (vs $1.03 for Python)

### Cost Reduction Strategies

1. **Right-size Memory**: Go performs well with less memory
2. **Leverage Fast Execution**: 50ms avg saves 50% vs 100ms
3. **Use Reserved Concurrency**: For predictable workloads
4. **Enable Lambda Insights**: Monitor and optimize

## Security

### IAM Roles

Required policies:
- `AWSLambdaBasicExecutionRole` - CloudWatch Logs
- `AWSXRayDaemonWriteAccess` - X-Ray tracing
- `AmazonBedrockFullAccess` - If using Bedrock
- `SecretsManagerReadWrite` - For API keys

### API Authentication

Enable API Gateway authentication in `template.yaml`:

```yaml
Events:
  ApiEvent:
    Type: Api
    Properties:
      Path: /agent
      Method: POST
      Auth:
        ApiKeyRequired: true
```

Or use AWS IAM:

```yaml
Auth:
  DefaultAuthorizer: AWS_IAM
```

### Secrets Management

Use AWS Secrets Manager for API keys:

```go
import (
    "github.com/aws/aws-sdk-go-v2/service/secretsmanager"
)

func getSecret(ctx context.Context, secretName string) (string, error) {
    cfg, err := config.LoadDefaultConfig(ctx)
    if err != nil {
        return "", err
    }

    client := secretsmanager.NewFromConfig(cfg)
    result, err := client.GetSecretValue(ctx, &secretsmanager.GetSecretValueInput{
        SecretId: &secretName,
    })
    if err != nil {
        return "", err
    }

    return *result.SecretString, nil
}
```

## Troubleshooting

### Common Issues

**Issue**: "exec format error" during local testing
**Solution**: Ensure you build for Linux: `GOOS=linux GOARCH=amd64 go build`

**Issue**: Cold start timeouts
**Solution**: Increase memory, reduce binary size, use provisioned concurrency

**Issue**: Permission errors
**Solution**: Add required IAM policies to Lambda execution role in `template.yaml`

**Issue**: X-Ray not showing traces
**Solution**: Enable tracing in Lambda and API Gateway, check IAM permissions include `AWSXRayDaemonWriteAccess`

**Issue**: Import errors for agenkit-go
**Solution**: Ensure `go.mod` has correct module path and `go mod tidy` is run

## Local Development

### Test Locally with SAM

```bash
# Start local API
make test-local

# In another terminal, test the local endpoint
curl -X POST http://localhost:3000/agent \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "react",
    "message": {
      "role": "user",
      "content": "Calculate 5 + 3"
    }
  }'
```

### Invoke Function Locally

```bash
# Create test event
mkdir -p events
cat > events/test-event.json << 'EOF'
{
  "body": "{\"agent_type\": \"react\", \"message\": {\"role\": \"user\", \"content\": \"Hello\"}}"
}
EOF

# Invoke locally
make invoke-local
```

### Debug with Delve

```bash
# Build with debug symbols
go build -gcflags="all=-N -l" -o bootstrap main.go

# Run with delve
dlv exec ./bootstrap
```

## Build Automation

The `Makefile` provides convenient targets:

```bash
make build          # Build Lambda binary
make clean          # Remove build artifacts
make package        # Create .zip for manual upload
make deploy         # Deploy with SAM
make deploy-guided  # Interactive deployment
make test-local     # Start local API
make invoke-local   # Test locally
make invoke         # Test deployed function
make logs           # Tail CloudWatch logs
make outputs        # Show stack outputs
make delete         # Delete CloudFormation stack
make help           # Show all available targets
```

## Cleanup

```bash
# Delete the stack
make delete

# Or with SAM
sam delete --stack-name agenkit-lambda-go-dev
```

## Next Steps

- Add real LLM integration (OpenAI, Anthropic, Bedrock)
- Implement custom agents for your use case
- Set up CI/CD pipeline for automated deployments
- Configure VPC access for database connections
- Enable API Gateway caching for frequently accessed responses
- Set up CloudWatch alarms for monitoring
- Add Lambda Layers for shared dependencies

## Performance Comparison

| Metric | Go | Python |
|--------|-----|--------|
| Cold Start | 100-200ms | 200-400ms |
| Warm Execution | 10-50ms | 50-150ms |
| Memory Usage | 128-256 MB | 256-512 MB |
| Package Size | 10-20 MB | 30-50 MB |
| Cost (1M req) | ~$0.62 | ~$1.03 |

## Support

For issues and questions:
- GitHub Issues: https://github.com/scttfrdmn/agenkit/issues
- Documentation: https://docs.agenkit.dev
