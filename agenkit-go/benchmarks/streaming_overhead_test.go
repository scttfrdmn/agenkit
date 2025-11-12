/*
Streaming overhead benchmarks for agenkit-go.

These benchmarks measure the performance of streaming responses vs batch responses,
and compare streaming performance across HTTP/1.1, HTTP/2, and HTTP/3.

Methodology:
1. Time to First Chunk (TTFC): Measure latency until first chunk arrives
2. Chunk Throughput: Measure chunks received per second
3. Total Streaming Time: Measure complete stream duration
4. Streaming Overhead: Compare streaming vs batch for same data
5. Protocol Comparison: HTTP/1.1, HTTP/2, HTTP/3 streaming performance

Key Metrics:
- TTFC (Time to First Chunk): <100ms target
- Chunk Throughput: >100 chunks/sec target
- Streaming Overhead: <20% vs batch target

Real-World Context:
- LLM token streaming: ~10-50 tokens/sec (~10-50 chunks/sec)
- Streaming adds incremental response capability at minimal cost
- HTTP/3's parallel streams should show advantage for concurrent streaming

Run benchmarks with: go test -bench='Streaming' ./benchmarks -benchmem
*/

package benchmarks

import (
	"context"
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/agenkit/agenkit-go/adapter/remote"
	"github.com/agenkit/agenkit-go/adapter/transport"
	"github.com/agenkit/agenkit-go/agenkit"
)

// ============================================
// Benchmark Streaming Agents
// ============================================

// StreamingChunkAgent streams a configurable number of chunks with optional delays.
// This simulates LLM token generation or other incremental processing.
type StreamingChunkAgent struct {
	name         string
	chunkCount   int
	chunkSize    int
	delayPerChunk time.Duration
}

func NewStreamingChunkAgent(name string, chunkCount, chunkSize int, delay time.Duration) *StreamingChunkAgent {
	return &StreamingChunkAgent{
		name:          name,
		chunkCount:    chunkCount,
		chunkSize:     chunkSize,
		delayPerChunk: delay,
	}
}

func (s *StreamingChunkAgent) Name() string {
	return s.name
}

func (s *StreamingChunkAgent) Capabilities() []string {
	return []string{"streaming"}
}

func (s *StreamingChunkAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// For batch mode, return all chunks as single message
	var content strings.Builder
	for i := 0; i < s.chunkCount; i++ {
		chunk := fmt.Sprintf("Chunk %d: %s\n", i+1, strings.Repeat("x", s.chunkSize))
		content.WriteString(chunk)
	}
	return agenkit.NewMessage("agent", content.String()), nil
}

func (s *StreamingChunkAgent) Stream(ctx context.Context, message *agenkit.Message) (<-chan *agenkit.Message, <-chan error) {
	messageChan := make(chan *agenkit.Message, s.chunkCount)
	errorChan := make(chan error, 1)

	go func() {
		defer close(messageChan)
		defer close(errorChan)

		for i := 0; i < s.chunkCount; i++ {
			select {
			case <-ctx.Done():
				errorChan <- ctx.Err()
				return
			default:
				// Simulate delay (e.g., LLM token generation)
				if s.delayPerChunk > 0 {
					time.Sleep(s.delayPerChunk)
				}

				chunk := fmt.Sprintf("Chunk %d: %s", i+1, strings.Repeat("x", s.chunkSize))
				messageChan <- agenkit.NewMessage("agent", chunk)
			}
		}
	}()

	return messageChan, errorChan
}

// ============================================
// Streaming Metrics Helper
// ============================================

type StreamingMetrics struct {
	TTFC             time.Duration // Time to first chunk
	TotalTime        time.Duration // Total streaming time
	ChunksReceived   int
	BytesReceived    int
	ChunkThroughput  float64 // Chunks per second
}

func measureStreaming(ctx context.Context, client *remote.RemoteAgent, message *agenkit.Message) (*StreamingMetrics, error) {
	startTime := time.Now()
	var ttfc time.Duration
	chunksReceived := 0
	bytesReceived := 0
	firstChunk := true

	messageChan, errorChan := client.Stream(ctx, message)

	for {
		select {
		case chunk, ok := <-messageChan:
			if !ok {
				// Stream complete
				totalTime := time.Since(startTime)
				throughput := float64(chunksReceived) / totalTime.Seconds()
				return &StreamingMetrics{
					TTFC:            ttfc,
					TotalTime:       totalTime,
					ChunksReceived:  chunksReceived,
					BytesReceived:   bytesReceived,
					ChunkThroughput: throughput,
				}, nil
			}

			if firstChunk {
				ttfc = time.Since(startTime)
				firstChunk = false
			}

			chunksReceived++
			bytesReceived += len(chunk.Content)

		case err := <-errorChan:
			if err != nil {
				return nil, err
			}

		case <-ctx.Done():
			return nil, ctx.Err()
		}
	}
}

// ============================================
// HTTP/1.1 Streaming Benchmarks
// ============================================

// BenchmarkHTTP1StreamingLatency measures HTTP/1.1 streaming latency (TTFC).
//
// Target: TTFC <100ms for first chunk
func BenchmarkHTTP1StreamingLatency(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := NewStreamingChunkAgent("streaming-agent", 10, 100, 0)
	endpoint, err := sm.StartServer(agent, "http", 9300)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("streaming-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "stream test")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		metrics, err := measureStreaming(ctx, client, msg)
		if err != nil {
			b.Fatal(err)
		}
		if metrics.ChunksReceived != 10 {
			b.Fatalf("expected 10 chunks, got %d", metrics.ChunksReceived)
		}
	}
}

// BenchmarkHTTP1Streaming10Chunks measures HTTP/1.1 streaming with 10 chunks.
func BenchmarkHTTP1Streaming10Chunks(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := NewStreamingChunkAgent("streaming-agent", 10, 100, 0)
	endpoint, err := sm.StartServer(agent, "http", 9301)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("streaming-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "stream test")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		metrics, err := measureStreaming(ctx, client, msg)
		if err != nil {
			b.Fatal(err)
		}
		if metrics.ChunksReceived != 10 {
			b.Fatalf("expected 10 chunks, got %d", metrics.ChunksReceived)
		}
	}
}

// BenchmarkHTTP1Streaming50Chunks measures HTTP/1.1 streaming with 50 chunks.
func BenchmarkHTTP1Streaming50Chunks(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := NewStreamingChunkAgent("streaming-agent", 50, 100, 0)
	endpoint, err := sm.StartServer(agent, "http", 9302)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("streaming-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "stream test")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		metrics, err := measureStreaming(ctx, client, msg)
		if err != nil {
			b.Fatal(err)
		}
		if metrics.ChunksReceived != 50 {
			b.Fatalf("expected 50 chunks, got %d", metrics.ChunksReceived)
		}
	}
}

// BenchmarkHTTP1StreamingVsBatch compares HTTP/1.1 streaming vs batch.
func BenchmarkHTTP1StreamingVsBatch(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := NewStreamingChunkAgent("streaming-agent", 10, 100, 0)
	endpoint, err := sm.StartServer(agent, "http", 9303)
	if err != nil {
		b.Fatal(err)
	}

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "stream test")

	b.Run("Streaming", func(b *testing.B) {
		// Create dedicated client for streaming
		trans := transport.NewHTTPTransport(endpoint)
		client := remote.NewRemoteAgentWithTransport("streaming-agent", trans, 30*time.Second)
		defer client.Close()

		for i := 0; i < b.N; i++ {
			_, err := measureStreaming(ctx, client, msg)
			if err != nil {
				b.Fatal(err)
			}
		}
	})

	b.Run("Batch", func(b *testing.B) {
		// Create dedicated client for batch
		trans := transport.NewHTTPTransport(endpoint)
		client := remote.NewRemoteAgentWithTransport("streaming-agent", trans, 30*time.Second)
		defer client.Close()

		for i := 0; i < b.N; i++ {
			_, err := client.Process(ctx, msg)
			if err != nil {
				b.Fatal(err)
			}
		}
	})
}

// BenchmarkHTTP1StreamingRealistic simulates realistic LLM token streaming.
//
// Simulates 50 tokens at 20 tokens/sec (50ms delay between tokens)
func BenchmarkHTTP1StreamingRealistic(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	// Simulate LLM: 50 tokens, ~20 tokens/sec
	agent := NewStreamingChunkAgent("streaming-agent", 50, 20, 50*time.Millisecond)
	endpoint, err := sm.StartServer(agent, "http", 9304)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("streaming-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "stream test")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		metrics, err := measureStreaming(ctx, client, msg)
		if err != nil {
			b.Fatal(err)
		}
		if metrics.ChunksReceived != 50 {
			b.Fatalf("expected 50 chunks, got %d", metrics.ChunksReceived)
		}
	}
}

// ============================================
// HTTP/2 Streaming Benchmarks
// ============================================

// BenchmarkHTTP2StreamingLatency measures HTTP/2 streaming latency (TTFC).
func BenchmarkHTTP2StreamingLatency(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := NewStreamingChunkAgent("streaming-agent", 10, 100, 0)
	endpoint, err := sm.StartServer(agent, "h2c", 9310)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("streaming-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "stream test")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		metrics, err := measureStreaming(ctx, client, msg)
		if err != nil {
			b.Fatal(err)
		}
		if metrics.ChunksReceived != 10 {
			b.Fatalf("expected 10 chunks, got %d", metrics.ChunksReceived)
		}
	}
}

// BenchmarkHTTP2Streaming50Chunks measures HTTP/2 streaming with 50 chunks.
func BenchmarkHTTP2Streaming50Chunks(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := NewStreamingChunkAgent("streaming-agent", 50, 100, 0)
	endpoint, err := sm.StartServer(agent, "h2c", 9311)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("streaming-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "stream test")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		metrics, err := measureStreaming(ctx, client, msg)
		if err != nil {
			b.Fatal(err)
		}
		if metrics.ChunksReceived != 50 {
			b.Fatalf("expected 50 chunks, got %d", metrics.ChunksReceived)
		}
	}
}

// BenchmarkHTTP2StreamingVsBatch compares HTTP/2 streaming vs batch.
func BenchmarkHTTP2StreamingVsBatch(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := NewStreamingChunkAgent("streaming-agent", 10, 100, 0)
	endpoint, err := sm.StartServer(agent, "h2c", 9312)
	if err != nil {
		b.Fatal(err)
	}

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "stream test")

	b.Run("Streaming", func(b *testing.B) {
		// Create dedicated client for streaming
		trans := transport.NewHTTPTransport(endpoint)
		client := remote.NewRemoteAgentWithTransport("streaming-agent", trans, 30*time.Second)
		defer client.Close()

		for i := 0; i < b.N; i++ {
			_, err := measureStreaming(ctx, client, msg)
			if err != nil {
				b.Fatal(err)
			}
		}
	})

	b.Run("Batch", func(b *testing.B) {
		// Create dedicated client for batch
		trans := transport.NewHTTPTransport(endpoint)
		client := remote.NewRemoteAgentWithTransport("streaming-agent", trans, 30*time.Second)
		defer client.Close()

		for i := 0; i < b.N; i++ {
			_, err := client.Process(ctx, msg)
			if err != nil {
				b.Fatal(err)
			}
		}
	})
}

// ============================================
// HTTP/3 Streaming Benchmarks
// ============================================

// BenchmarkHTTP3StreamingLatency measures HTTP/3 streaming latency (TTFC).
func BenchmarkHTTP3StreamingLatency(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := NewStreamingChunkAgent("streaming-agent", 10, 100, 0)
	endpoint, err := sm.StartServer(agent, "h3", 9320)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("streaming-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "stream test")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		metrics, err := measureStreaming(ctx, client, msg)
		if err != nil {
			b.Fatal(err)
		}
		if metrics.ChunksReceived != 10 {
			b.Fatalf("expected 10 chunks, got %d", metrics.ChunksReceived)
		}
	}
}

// BenchmarkHTTP3Streaming50Chunks measures HTTP/3 streaming with 50 chunks.
func BenchmarkHTTP3Streaming50Chunks(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := NewStreamingChunkAgent("streaming-agent", 50, 100, 0)
	endpoint, err := sm.StartServer(agent, "h3", 9321)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("streaming-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "stream test")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		metrics, err := measureStreaming(ctx, client, msg)
		if err != nil {
			b.Fatal(err)
		}
		if metrics.ChunksReceived != 50 {
			b.Fatalf("expected 50 chunks, got %d", metrics.ChunksReceived)
		}
	}
}

// BenchmarkHTTP3StreamingVsBatch compares HTTP/3 streaming vs batch.
func BenchmarkHTTP3StreamingVsBatch(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := NewStreamingChunkAgent("streaming-agent", 10, 100, 0)
	endpoint, err := sm.StartServer(agent, "h3", 9322)
	if err != nil {
		b.Fatal(err)
	}

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "stream test")

	b.Run("Streaming", func(b *testing.B) {
		// Create dedicated client for streaming
		trans := transport.NewHTTPTransport(endpoint)
		client := remote.NewRemoteAgentWithTransport("streaming-agent", trans, 30*time.Second)
		defer client.Close()

		for i := 0; i < b.N; i++ {
			_, err := measureStreaming(ctx, client, msg)
			if err != nil {
				b.Fatal(err)
			}
		}
	})

	b.Run("Batch", func(b *testing.B) {
		// Create dedicated client for batch
		trans := transport.NewHTTPTransport(endpoint)
		client := remote.NewRemoteAgentWithTransport("streaming-agent", trans, 30*time.Second)
		defer client.Close()

		for i := 0; i < b.N; i++ {
			_, err := client.Process(ctx, msg)
			if err != nil {
				b.Fatal(err)
			}
		}
	})
}
