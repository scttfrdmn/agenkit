# Agenkit on AWS Lambda - Python Implementation

Deploy Agenkit agents as serverless functions on AWS Lambda with API Gateway integration, CloudWatch logging, and X-Ray tracing.

## Features

- ✅ **Multiple Agent Types**: ReAct, Conversational, Router patterns
- ✅ **API Gateway Integration**: RESTful API for agent invocation
- ✅ **Lambda Function URLs**: Direct HTTPS endpoints
- ✅ **X-Ray Tracing**: Distributed tracing with AWS X-Ray
- ✅ **CloudWatch Logging**: Centralized logging
- ✅ **SAM Deployment**: Infrastructure as Code
- ✅ **Cold Start Optimization**: Optimized for serverless

## Quick Start

### Prerequisites

- AWS CLI configured (`aws configure`)
- AWS SAM CLI installed (`brew install aws-sam-cli` or `pip install aws-sam-cli`)
- Python 3.12+
- Active AWS account

### 1. Deploy with SAM

```bash
# Build the function
sam build

# Deploy (guided first time)
sam deploy --guided

# For subsequent deployments
sam deploy
```

**Guided deployment prompts:**
- Stack Name: `agenkit-lambda-dev`
- AWS Region: `us-east-1`
- Parameter Environment: `dev`
- Parameter AgentType: `react`
- Confirm changes before deploy: `Y`
- Allow SAM CLI IAM role creation: `Y`
- Save arguments to samconfig.toml: `Y`

### 2. Test the Deployment

```bash
# Get the API endpoint from stack outputs
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name agenkit-lambda-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)

# Test the agent
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
# Get Function URL
FUNCTION_URL=$(aws cloudformation describe-stacks \
  --stack-name agenkit-lambda-dev \
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

```python
# In handler.py
import openai

openai.api_key = os.environ["OPENAI_API_KEY"]

class OpenAILLM:
    async def process(self, message: Message) -> Message:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{"role": "user", "content": message.content}]
        )
        return Message(
            role="assistant",
            content=response.choices[0].message.content
        )
```

#### AWS Bedrock

```python
import boto3

bedrock = boto3.client('bedrock-runtime')

class BedrockLLM:
    async def process(self, message: Message) -> Message:
        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-sonnet',
            body=json.dumps({
                "messages": [{"role": "user", "content": message.content}],
                "max_tokens": 1024
            })
        )
        # Parse and return response
```

## Monitoring

### CloudWatch Logs

```bash
# View logs
sam logs -n AgenkitFunction --tail

# Or with AWS CLI
aws logs tail /aws/lambda/agenkit-dev-react --follow
```

### X-Ray Tracing

1. Open AWS X-Ray Console
2. View Service Map: `https://console.aws.amazon.com/xray/home#/service-map`
3. Analyze traces for performance insights

### Metrics

Key CloudWatch metrics:
- `Invocations` - Request count
- `Duration` - Execution time
- `Errors` - Error count
- `Throttles` - Rate limiting
- `ConcurrentExecutions` - Concurrent invocations

## Performance Optimization

### Cold Start Reduction

1. **Increase Memory**: More memory = faster CPU = faster cold starts
   ```yaml
   MemorySize: 1024  # Instead of 512
   ```

2. **Provisioned Concurrency**: Keep instances warm
   ```yaml
   ProvisionedConcurrencyConfig:
     ProvisionedConcurrentExecutions: 5
   ```

3. **Lambda SnapStart** (Java only - for future JVM support)

### Reduce Package Size

```bash
# Use slim dependencies
pip install --target ./package agenkit --no-deps
pip install --target ./package -r requirements-slim.txt
```

### Connection Pooling

Reuse connections across invocations:

```python
# Initialize outside handler
import httpx

http_client = httpx.AsyncClient()

def lambda_handler(event, context):
    # Reuse http_client
    ...
```

## Cost Optimization

### Pricing Model

**Lambda Costs:**
- Requests: $0.20 per 1M requests
- Duration: $0.0000166667 per GB-second

**Example Cost (512 MB, 100ms average):**
- 1M requests/month
- Compute: 1M * 0.1s * 0.5 GB * $0.0000166667 = $0.83
- Requests: 1M * $0.20/1M = $0.20
- **Total: ~$1.03/month**

### Cost Reduction Strategies

1. **Right-size Memory**: Start with 256 MB, increase if needed
2. **Optimize Cold Starts**: Faster = cheaper
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

Enable API Gateway authentication:

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

```python
import boto3

secrets_client = boto3.client('secretsmanager')

def get_secret(secret_name):
    response = secrets_client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

OPENAI_API_KEY = get_secret('prod/openai/api_key')['api_key']
```

## Troubleshooting

### Common Issues

**Issue**: Cold start timeouts
**Solution**: Increase memory, reduce package size, use provisioned concurrency

**Issue**: Permission errors
**Solution**: Add required IAM policies to Lambda execution role

**Issue**: Import errors
**Solution**: Ensure all dependencies are in `requirements.txt` and packaged

**Issue**: X-Ray not showing traces
**Solution**: Enable tracing in Lambda and API Gateway, check IAM permissions

## Local Development

### Test Locally with SAM

```bash
# Start local API
sam local start-api

# Invoke function locally
sam local invoke AgenkitFunction -e events/test-event.json
```

### Create Test Event

`events/test-event.json`:
```json
{
  "body": "{\"agent_type\": \"react\", \"message\": {\"role\": \"user\", \"content\": \"Hello\"}}"
}
```

## Cleanup

```bash
# Delete the stack
sam delete

# Or with CloudFormation
aws cloudformation delete-stack --stack-name agenkit-lambda-dev
```

## Next Steps

- Add real LLM integration (OpenAI, Anthropic, Bedrock)
- Implement custom agents for your use case
- Set up CI/CD pipeline for automated deployments
- Configure VPC access for database connections
- Enable API Gateway caching for frequently accessed responses
- Set up CloudWatch alarms for monitoring

## Support

For issues and questions:
- GitHub Issues: https://github.com/agenkit/agenkit/issues
- Documentation: https://docs.agenkit.dev
