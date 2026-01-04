.PHONY: build clean deploy test invoke logs

# Build configuration
BINARY_NAME=bootstrap
PACKAGE_NAME=agenkit-lambda-go
LAMBDA_ARCH=amd64
GOOS=linux
GOARCH=amd64

# AWS configuration
STACK_NAME ?= agenkit-lambda-go-dev
REGION ?= us-east-1
ENVIRONMENT ?= dev
AGENT_TYPE ?= react

# Build the Lambda function
build:
	@echo "Building Lambda function..."
	GOOS=$(GOOS) GOARCH=$(GOARCH) go build -tags lambda.norpc -o $(BINARY_NAME) main.go
	@echo "Build complete: $(BINARY_NAME)"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -f $(BINARY_NAME)
	rm -f $(PACKAGE_NAME).zip
	rm -rf .aws-sam
	@echo "Clean complete"

# Package for Lambda deployment
package: clean build
	@echo "Creating deployment package..."
	zip $(PACKAGE_NAME).zip $(BINARY_NAME)
	@echo "Package created: $(PACKAGE_NAME).zip"

# Deploy with SAM
deploy: build
	@echo "Deploying with SAM..."
	sam deploy \
		--stack-name $(STACK_NAME) \
		--region $(REGION) \
		--parameter-overrides \
			Environment=$(ENVIRONMENT) \
			AgentType=$(AGENT_TYPE) \
		--resolve-s3 \
		--capabilities CAPABILITY_IAM
	@echo "Deployment complete"

# Deploy with guided setup (first time)
deploy-guided: build
	@echo "Starting guided deployment..."
	sam deploy --guided

# Test locally with SAM
test-local:
	@echo "Testing locally with SAM..."
	sam local start-api

# Invoke function locally
invoke-local:
	@echo "Invoking function locally..."
	sam local invoke AgenkitFunction -e events/test-event.json

# Create test event if it doesn't exist
events/test-event.json:
	@mkdir -p events
	@echo '{"body": "{\"agent_type\": \"react\", \"message\": {\"role\": \"user\", \"content\": \"Calculate 10 + 5\"}}"}' > events/test-event.json

# View CloudWatch logs
logs:
	@echo "Fetching logs..."
	sam logs -n AgenkitFunction --stack-name $(STACK_NAME) --tail

# Run Go tests
test:
	@echo "Running tests..."
	go test -v ./...

# Format code
fmt:
	@echo "Formatting code..."
	go fmt ./...

# Run linter
lint:
	@echo "Running linter..."
	golangci-lint run

# Get dependencies
deps:
	@echo "Installing dependencies..."
	go mod download
	go mod tidy

# Show stack outputs
outputs:
	@echo "Stack outputs:"
	@aws cloudformation describe-stacks \
		--stack-name $(STACK_NAME) \
		--region $(REGION) \
		--query 'Stacks[0].Outputs' \
		--output table

# Invoke deployed function
invoke:
	@echo "Invoking deployed function..."
	@API_ENDPOINT=$$(aws cloudformation describe-stacks \
		--stack-name $(STACK_NAME) \
		--region $(REGION) \
		--query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
		--output text); \
	curl -X POST $$API_ENDPOINT \
		-H "Content-Type: application/json" \
		-d '{"agent_type": "react", "message": {"role": "user", "content": "Calculate 10 + 5"}}'

# Delete stack
delete:
	@echo "Deleting stack..."
	sam delete --stack-name $(STACK_NAME) --region $(REGION) --no-prompts

# Help
help:
	@echo "Available targets:"
	@echo "  build          - Build the Lambda function binary"
	@echo "  clean          - Remove build artifacts"
	@echo "  package        - Create deployment package (.zip)"
	@echo "  deploy         - Deploy with SAM (uses defaults)"
	@echo "  deploy-guided  - Deploy with interactive prompts"
	@echo "  test-local     - Start local API for testing"
	@echo "  invoke-local   - Invoke function locally"
	@echo "  invoke         - Invoke deployed function via API"
	@echo "  logs           - Tail CloudWatch logs"
	@echo "  test           - Run Go tests"
	@echo "  fmt            - Format Go code"
	@echo "  lint           - Run golangci-lint"
	@echo "  deps           - Download dependencies"
	@echo "  outputs        - Show stack outputs"
	@echo "  delete         - Delete CloudFormation stack"
	@echo ""
	@echo "Configuration (override with environment variables):"
	@echo "  STACK_NAME=$(STACK_NAME)"
	@echo "  REGION=$(REGION)"
	@echo "  ENVIRONMENT=$(ENVIRONMENT)"
	@echo "  AGENT_TYPE=$(AGENT_TYPE)"
