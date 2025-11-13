# Build Your First Agent

This tutorial walks you through building a practical agent step-by-step.

## The Agent We'll Build

We'll create a **Text Analyzer Agent** that:
- Counts words in a message
- Detects sentiment (positive/negative/neutral)
- Returns structured analysis

## Step 1: Create the Agent Class

=== "Python"

    ```python
    from agenkit import Agent, Message
    from typing import Dict, Any

    class TextAnalyzerAgent(Agent):
        @property
        def name(self) -> str:
            return "text-analyzer"

        @property
        def capabilities(self) -> list[str]:
            return ["text-analysis", "sentiment", "word-count"]

        async def process(self, message: Message) -> Message:
            # We'll implement this next
            pass
    ```

=== "Go"

    ```go
    package main

    import (
        "context"
        "github.com/agenkit/agenkit-go/agenkit"
    )

    type TextAnalyzerAgent struct{}

    func (a *TextAnalyzerAgent) Name() string {
        return "text-analyzer"
    }

    func (a *TextAnalyzerAgent) Capabilities() []string {
        return []string{"text-analysis", "sentiment", "word-count"}
    }

    func (a *TextAnalyzerAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
        // We'll implement this next
        return nil, nil
    }
    ```

## Step 2: Implement Word Counting

=== "Python"

    ```python
    def _count_words(self, text: str) -> int:
        """Count words in the text."""
        return len(text.split())

    def _analyze_sentiment(self, text: str) -> str:
        """Simple sentiment analysis."""
        text_lower = text.lower()

        positive_words = ['good', 'great', 'excellent', 'happy', 'love']
        negative_words = ['bad', 'terrible', 'awful', 'sad', 'hate']

        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    ```

=== "Go"

    ```go
    import "strings"

    func (a *TextAnalyzerAgent) countWords(text string) int {
        return len(strings.Fields(text))
    }

    func (a *TextAnalyzerAgent) analyzeSentiment(text string) string {
        textLower := strings.ToLower(text)

        positiveWords := []string{"good", "great", "excellent", "happy", "love"}
        negativeWords := []string{"bad", "terrible", "awful", "sad", "hate"}

        positiveCount := 0
        for _, word := range positiveWords {
            if strings.Contains(textLower, word) {
                positiveCount++
            }
        }

        negativeCount := 0
        for _, word := range negativeWords {
            if strings.Contains(textLower, word) {
                negativeCount++
            }
        }

        if positiveCount > negativeCount {
            return "positive"
        } else if negativeCount > positiveCount {
            return "negative"
        }
        return "neutral"
    }
    ```

## Step 3: Complete the Process Method

=== "Python"

    ```python
    async def process(self, message: Message) -> Message:
        # Extract text from message
        text = str(message.content)

        # Analyze the text
        word_count = self._count_words(text)
        sentiment = self._analyze_sentiment(text)

        # Create response with analysis
        analysis = {
            "word_count": word_count,
            "sentiment": sentiment,
            "text_preview": text[:50] + "..." if len(text) > 50 else text
        }

        return Message(
            role="agent",
            content=analysis,
            metadata={
                "agent": self.name,
                "analysis_type": "text"
            }
        )
    ```

=== "Go"

    ```go
    func (a *TextAnalyzerAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
        // Extract text from message
        text := fmt.Sprintf("%v", msg.Content)

        // Analyze the text
        wordCount := a.countWords(text)
        sentiment := a.analyzeSentiment(text)

        // Create response with analysis
        analysis := map[string]interface{}{
            "word_count": wordCount,
            "sentiment":  sentiment,
            "text_preview": text,
        }

        if len(text) > 50 {
            analysis["text_preview"] = text[:50] + "..."
        }

        return &agenkit.Message{
            Role:    "agent",
            Content: analysis,
            Metadata: map[string]interface{}{
                "agent":         a.Name(),
                "analysis_type": "text",
            },
        }, nil
    }
    ```

## Step 4: Test Your Agent

=== "Python"

    ```python
    import asyncio

    async def main():
        # Create the agent
        agent = TextAnalyzerAgent()

        # Test messages
        test_messages = [
            "This is a great and excellent day!",
            "I feel terrible and sad about this.",
            "The weather is normal today."
        ]

        for text in test_messages:
            message = Message(role="user", content=text)
            response = await agent.process(message)

            print(f"\nInput: {text}")
            print(f"Analysis: {response.content}")

    if __name__ == "__main__":
        asyncio.run(main())
    ```

    Output:
    ```
    Input: This is a great and excellent day!
    Analysis: {'word_count': 7, 'sentiment': 'positive', 'text_preview': 'This is a great and excellent day!'}

    Input: I feel terrible and sad about this.
    Analysis: {'word_count': 7, 'sentiment': 'negative', 'text_preview': 'I feel terrible and sad about this.'}

    Input: The weather is normal today.
    Analysis: {'word_count': 5, 'sentiment': 'neutral', 'text_preview': 'The weather is normal today.'}
    ```

=== "Go"

    ```go
    func main() {
        agent := &TextAnalyzerAgent{}

        testMessages := []string{
            "This is a great and excellent day!",
            "I feel terrible and sad about this.",
            "The weather is normal today.",
        }

        for _, text := range testMessages {
            message := &agenkit.Message{
                Role:    "user",
                Content: text,
            }

            response, err := agent.Process(context.Background(), message)
            if err != nil {
                panic(err)
            }

            fmt.Printf("\nInput: %s\n", text)
            fmt.Printf("Analysis: %+v\n", response.Content)
        }
    }
    ```

## Step 5: Add Error Handling

=== "Python"

    ```python
    async def process(self, message: Message) -> Message:
        try:
            # Validate input
            if not message.content:
                return Message(
                    role="agent",
                    content={"error": "Empty message content"},
                    metadata={"status": "error"}
                )

            text = str(message.content)

            # Analyze
            word_count = self._count_words(text)
            sentiment = self._analyze_sentiment(text)

            analysis = {
                "word_count": word_count,
                "sentiment": sentiment,
                "text_preview": text[:50] + "..." if len(text) > 50 else text
            }

            return Message(
                role="agent",
                content=analysis,
                metadata={"agent": self.name, "status": "success"}
            )

        except Exception as e:
            return Message(
                role="agent",
                content={"error": str(e)},
                metadata={"status": "error"}
            )
    ```

=== "Go"

    ```go
    func (a *TextAnalyzerAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
        // Validate input
        if msg.Content == nil || msg.Content == "" {
            return &agenkit.Message{
                Role:    "agent",
                Content: map[string]interface{}{"error": "Empty message content"},
                Metadata: map[string]interface{}{"status": "error"},
            }, nil
        }

        text := fmt.Sprintf("%v", msg.Content)

        // Analyze
        wordCount := a.countWords(text)
        sentiment := a.analyzeSentiment(text)

        analysis := map[string]interface{}{
            "word_count":   wordCount,
            "sentiment":    sentiment,
            "text_preview": text,
        }

        if len(text) > 50 {
            analysis["text_preview"] = text[:50] + "..."
        }

        return &agenkit.Message{
            Role:    "agent",
            Content: analysis,
            Metadata: map[string]interface{}{
                "agent":  a.Name(),
                "status": "success",
            },
        }, nil
    }
    ```

## 🎉 Complete!

You've built a fully functional text analyzer agent!

## What You Learned

✅ Implementing the `Agent` interface
✅ Processing messages and returning responses
✅ Using metadata for extra information
✅ Error handling in agents
✅ Testing your agent

## Next Steps

- **Add middleware** - Wrap your agent with [retry](../features/middleware.md#retry) or [caching](../features/middleware.md#caching)
- **Compose agents** - Combine multiple agents using [composition patterns](../features/composition.md)
- **Go remote** - Connect agents across processes with [transports](../features/transport.md)
- **Add observability** - Track performance with [tracing and metrics](../features/observability.md)

Explore more in our [Examples](../examples/index.md) section!
