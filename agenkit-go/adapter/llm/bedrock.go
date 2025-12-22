package llm

import (
	"context"
	"fmt"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/bedrockruntime"
	"github.com/aws/aws-sdk-go-v2/service/bedrockruntime/types"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// BedrockLLM is an adapter for Amazon Bedrock foundation models.
//
// Provides enterprise-grade AWS integration for foundation models available
// through Amazon Bedrock (Claude, Llama, Mistral, Titan, etc.).
//
// Supports full AWS credential chain:
//   - Explicit credentials (access key ID, secret access key)
//   - AWS profiles (~/.aws/config)
//   - Environment variables (AWS_ACCESS_KEY_ID, etc.)
//   - IAM roles (EC2, ECS, EKS)
//   - STS assume role
//
// Example:
//
//	// Use IAM role (ECS/EKS/EC2)
//	llm, err := NewBedrockLLM(context.Background(), BedrockConfig{
//	    ModelID: "anthropic.claude-3-5-sonnet-20241022-v2:0",
//	})
//
//	// Use AWS profile
//	llm, err := NewBedrockLLM(context.Background(), BedrockConfig{
//	    ModelID: "anthropic.claude-3-5-sonnet-20241022-v2:0",
//	    Profile: "production",
//	})
//
//	// Use explicit credentials
//	llm, err := NewBedrockLLM(context.Background(), BedrockConfig{
//	    ModelID:         "anthropic.claude-3-5-sonnet-20241022-v2:0",
//	    AccessKeyID:     "...",
//	    SecretAccessKey: "...",
//	})
//
// Popular model IDs:
//   - anthropic.claude-3-5-sonnet-20241022-v2:0 - Claude 3.5 Sonnet
//   - anthropic.claude-3-haiku-20240307-v1:0 - Claude 3 Haiku
//   - meta.llama3-70b-instruct-v1:0 - Llama 3 70B
//   - mistral.mistral-large-2402-v1:0 - Mistral Large
//   - amazon.titan-text-premier-v1:0 - Amazon Titan
type BedrockLLM struct {
	client  *bedrockruntime.Client
	modelID string
}

// BedrockConfig holds configuration for creating a Bedrock LLM adapter.
type BedrockConfig struct {
	// ModelID is the Bedrock model identifier (e.g., "anthropic.claude-3-5-sonnet-20241022-v2:0")
	ModelID string

	// Region is the AWS region (default: us-east-1)
	Region string

	// Profile is the AWS profile name (optional)
	Profile string

	// AccessKeyID is the AWS access key (optional)
	AccessKeyID string

	// SecretAccessKey is the AWS secret key (optional)
	SecretAccessKey string

	// SessionToken is the AWS session token (optional)
	SessionToken string

	// EndpointURL is a custom endpoint URL for VPC endpoints (optional)
	EndpointURL string
}

// NewBedrockLLM creates a new Bedrock LLM adapter.
//
// Parameters:
//   - ctx: Context for loading AWS configuration
//   - cfg: Configuration for the Bedrock client
//
// Returns:
//   - *BedrockLLM: The configured adapter
//   - error: Any error during initialization
//
// Example:
//
//	llm, err := NewBedrockLLM(context.Background(), BedrockConfig{
//	    ModelID: "anthropic.claude-3-5-sonnet-20241022-v2:0",
//	    Region:  "us-west-2",
//	})
//	if err != nil {
//	    log.Fatal(err)
//	}
func NewBedrockLLM(ctx context.Context, cfg BedrockConfig) (*BedrockLLM, error) {
	// Set defaults
	if cfg.ModelID == "" {
		cfg.ModelID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
	}
	if cfg.Region == "" {
		cfg.Region = "us-east-1"
	}

	// Build AWS config options
	var configOpts []func(*config.LoadOptions) error

	// Region
	configOpts = append(configOpts, config.WithRegion(cfg.Region))

	// Profile
	if cfg.Profile != "" {
		configOpts = append(configOpts, config.WithSharedConfigProfile(cfg.Profile))
	}

	// Explicit credentials
	if cfg.AccessKeyID != "" && cfg.SecretAccessKey != "" {
		configOpts = append(configOpts, config.WithCredentialsProvider(
			credentials.NewStaticCredentialsProvider(
				cfg.AccessKeyID,
				cfg.SecretAccessKey,
				cfg.SessionToken,
			),
		))
	}

	// Load AWS config
	awsConfig, err := config.LoadDefaultConfig(ctx, configOpts...)
	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	// Build Bedrock client options
	var clientOpts []func(*bedrockruntime.Options)

	// Custom endpoint
	if cfg.EndpointURL != "" {
		clientOpts = append(clientOpts, func(o *bedrockruntime.Options) {
			o.BaseEndpoint = aws.String(cfg.EndpointURL)
		})
	}

	// Create Bedrock runtime client
	client := bedrockruntime.NewFromConfig(awsConfig, clientOpts...)

	return &BedrockLLM{
		client:  client,
		modelID: cfg.ModelID,
	}, nil
}

// Model returns the model identifier.
func (b *BedrockLLM) Model() string {
	return b.modelID
}

// Complete generates a completion from Bedrock.
//
// Parameters:
//   - ctx: Context for cancellation and deadlines
//   - messages: Conversation history as Agenkit Messages
//   - opts: Options like temperature, max_tokens, etc.
//
// Returns:
//   - Response as Agenkit Message with metadata including:
//   - model: Model ID used
//   - usage: Token counts (input, output, total)
//   - stop_reason: Why generation stopped
//
// Example:
//
//	messages := []*agenkit.Message{
//	    agenkit.NewMessage("system", "You are a helpful assistant."),
//	    agenkit.NewMessage("user", "What is 2+2?"),
//	}
//	response, err := llm.Complete(ctx, messages, WithTemperature(0.2))
//	if err != nil {
//	    log.Fatal(err)
//	}
//	fmt.Println(response.Content)
//	fmt.Printf("Usage: %+v\n", response.Metadata["usage"])
func (b *BedrockLLM) Complete(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (*agenkit.Message, error) {
	// Build options
	options := BuildCallOptions(opts...)

	// Convert messages and extract system prompts
	bedrockMessages, systemPrompts := b.convertMessages(messages)

	// Build inference configuration
	inferenceConfig := &types.InferenceConfiguration{}

	if options.Temperature != nil {
		inferenceConfig.Temperature = aws.Float32(float32(*options.Temperature))
	}

	maxTokens := 4096
	if options.MaxTokens != nil {
		maxTokens = *options.MaxTokens
	}
	inferenceConfig.MaxTokens = aws.Int32(int32(maxTokens))

	if options.TopP != nil {
		inferenceConfig.TopP = aws.Float32(float32(*options.TopP))
	}

	// Build converse input
	input := &bedrockruntime.ConverseInput{
		ModelId:         aws.String(b.modelID),
		Messages:        bedrockMessages,
		InferenceConfig: inferenceConfig,
	}

	// Add system prompts if present
	if len(systemPrompts) > 0 {
		input.System = systemPrompts
	}

	// Add stop sequences if provided
	if stopSeq, ok := options.Extra["stopSequences"].([]string); ok && len(stopSeq) > 0 {
		inferenceConfig.StopSequences = stopSeq
	}

	// Call Bedrock API
	output, err := b.client.Converse(ctx, input)
	if err != nil {
		return nil, fmt.Errorf("bedrock api error: %w", err)
	}

	// Extract text content from output
	var content string
	if output.Output != nil {
		if msg, ok := output.Output.(*types.ConverseOutputMemberMessage); ok {
			for _, block := range msg.Value.Content {
				if textBlock, ok := block.(*types.ContentBlockMemberText); ok {
					content += textBlock.Value
				}
			}
		}
	}

	// Build response message
	response := agenkit.NewMessage("agent", content)
	response.Metadata["model"] = b.modelID

	// Add usage if available
	if output.Usage != nil {
		response.Metadata["usage"] = map[string]interface{}{
			"prompt_tokens":     aws.ToInt32(output.Usage.InputTokens),
			"completion_tokens": aws.ToInt32(output.Usage.OutputTokens),
			"total_tokens":      aws.ToInt32(output.Usage.TotalTokens),
		}
	}

	// Add stop reason
	if output.StopReason != "" {
		response.Metadata["stop_reason"] = string(output.StopReason)
	}

	return response, nil
}

// Stream generates completion chunks from Bedrock.
//
// Parameters:
//   - ctx: Context for cancellation and deadlines
//   - messages: Conversation history as Agenkit Messages
//   - opts: Options like temperature, max_tokens, etc.
//
// Returns:
//   - Channel of Message chunks as they arrive from Bedrock
//   - Error if streaming cannot be initiated
//
// Example:
//
//	messages := []*agenkit.Message{
//	    agenkit.NewMessage("user", "Count to 10"),
//	}
//	stream, err := llm.Stream(ctx, messages)
//	if err != nil {
//	    log.Fatal(err)
//	}
//	for chunk := range stream {
//	    fmt.Print(chunk.Content)
//	}
func (b *BedrockLLM) Stream(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (<-chan *agenkit.Message, error) {
	// Build options
	options := BuildCallOptions(opts...)

	// Convert messages
	bedrockMessages, systemPrompts := b.convertMessages(messages)

	// Build inference configuration
	inferenceConfig := &types.InferenceConfiguration{}

	if options.Temperature != nil {
		inferenceConfig.Temperature = aws.Float32(float32(*options.Temperature))
	}

	maxTokens := 4096
	if options.MaxTokens != nil {
		maxTokens = *options.MaxTokens
	}
	inferenceConfig.MaxTokens = aws.Int32(int32(maxTokens))

	if options.TopP != nil {
		inferenceConfig.TopP = aws.Float32(float32(*options.TopP))
	}

	// Build converse stream input
	input := &bedrockruntime.ConverseStreamInput{
		ModelId:         aws.String(b.modelID),
		Messages:        bedrockMessages,
		InferenceConfig: inferenceConfig,
	}

	// Add system prompts if present
	if len(systemPrompts) > 0 {
		input.System = systemPrompts
	}

	// Add stop sequences if provided
	if stopSeq, ok := options.Extra["stopSequences"].([]string); ok && len(stopSeq) > 0 {
		inferenceConfig.StopSequences = stopSeq
	}

	// Call Bedrock streaming API
	output, err := b.client.ConverseStream(ctx, input)
	if err != nil {
		return nil, fmt.Errorf("bedrock api error: %w", err)
	}

	// Create channel for messages
	messageChan := make(chan *agenkit.Message)

	// Start goroutine to read stream
	go func() {
		defer close(messageChan)

		// Get the event stream
		stream := output.GetStream()

		// Process events
		for event := range stream.Events() {
			switch e := event.(type) {
			case *types.ConverseStreamOutputMemberContentBlockDelta:
				// Extract text from content block delta
				if e.Value.Delta != nil {
					if textDelta, ok := e.Value.Delta.(*types.ContentBlockDeltaMemberText); ok {
						chunk := agenkit.NewMessage("agent", textDelta.Value)
						chunk.Metadata["streaming"] = true
						chunk.Metadata["model"] = b.modelID
						messageChan <- chunk
					}
				}
			}
		}

		// Check for stream errors
		if err := stream.Err(); err != nil {
			errorMsg := agenkit.NewMessage("agent", "")
			errorMsg.Metadata["error"] = err.Error()
			errorMsg.Metadata["streaming"] = true
			messageChan <- errorMsg
		}
	}()

	return messageChan, nil
}

// convertMessages converts Agenkit Messages to Bedrock Converse format.
//
// Bedrock expects:
//   - role: "user" or "assistant"
//   - content: list of content blocks
//
// System messages are handled separately via system parameter.
//
// Returns:
//   - Bedrock messages slice
//   - System prompts slice
func (b *BedrockLLM) convertMessages(messages []*agenkit.Message) ([]types.Message, []types.SystemContentBlock) {
	var bedrockMessages []types.Message
	var systemPrompts []types.SystemContentBlock

	for _, msg := range messages {
		// Handle system messages separately
		if msg.Role == "system" {
			systemPrompts = append(systemPrompts, &types.SystemContentBlockMemberText{
				Value: msg.Content,
			})
			continue
		}

		// Map roles
		var role types.ConversationRole
		if msg.Role == "user" {
			role = types.ConversationRoleUser
		} else {
			// Map "agent" and others to "assistant"
			role = types.ConversationRoleAssistant
		}

		// Create content blocks
		contentBlocks := []types.ContentBlock{
			&types.ContentBlockMemberText{
				Value: msg.Content,
			},
		}

		bedrockMessages = append(bedrockMessages, types.Message{
			Role:    role,
			Content: contentBlocks,
		})
	}

	return bedrockMessages, systemPrompts
}

// Unwrap returns the underlying Bedrock runtime client.
//
// Returns:
//   - The *bedrockruntime.Client for direct API access
//
// Example:
//
//	llm, _ := NewBedrockLLM(ctx, BedrockConfig{...})
//	client := llm.Unwrap().(*bedrockruntime.Client)
//	// Use Bedrock-specific features
//	response, err := client.Converse(...)
func (b *BedrockLLM) Unwrap() interface{} {
	return b.client
}
