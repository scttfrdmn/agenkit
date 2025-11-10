package adapter_test

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"testing"
	"time"

	"github.com/agenkit/agenkit-go/adapter/local"
	"github.com/agenkit/agenkit-go/adapter/remote"
	"github.com/agenkit/agenkit-go/agenkit"
)

// EmptyStreamAgent yields no chunks
type EmptyStreamAgent struct {
	EchoAgent
}

func (e *EmptyStreamAgent) Stream(ctx context.Context, message *agenkit.Message) (<-chan *agenkit.Message, <-chan error) {
	messageChan := make(chan *agenkit.Message)
	errorChan := make(chan error, 1)

	// Close channels immediately without yielding anything
	close(messageChan)
	close(errorChan)

	return messageChan, errorChan
}

// LargeChunkAgent yields large message chunks
type LargeChunkAgent struct {
	EchoAgent
}

func (l *LargeChunkAgent) Stream(ctx context.Context, message *agenkit.Message) (<-chan *agenkit.Message, <-chan error) {
	messageChan := make(chan *agenkit.Message, 3)
	errorChan := make(chan error, 1)

	go func() {
		defer close(messageChan)
		defer close(errorChan)

		// Yield 3 large chunks (10KB each)
		for i := 0; i < 3; i++ {
			select {
			case <-ctx.Done():
				errorChan <- ctx.Err()
				return
			default:
				largeContent := fmt.Sprintf("Chunk %d: ", i) + string(make([]byte, 10000))
				msg := agenkit.NewMessage("agent", largeContent)
				messageChan <- msg
			}
		}
	}()

	return messageChan, errorChan
}

// ErrorStreamAgent raises an error after yielding one chunk
type ErrorStreamAgent struct {
	EchoAgent
}

func (e *ErrorStreamAgent) Stream(ctx context.Context, message *agenkit.Message) (<-chan *agenkit.Message, <-chan error) {
	messageChan := make(chan *agenkit.Message, 1)
	errorChan := make(chan error, 1)

	go func() {
		defer close(messageChan)
		defer close(errorChan)

		// Yield one chunk
		msg := agenkit.NewMessage("agent", "Chunk 0")
		messageChan <- msg

		// Small delay to ensure chunk is sent first
		time.Sleep(10 * time.Millisecond)

		// Then send error
		errorChan <- fmt.Errorf("Stream error!")
	}()

	return messageChan, errorChan
}

// MetadataStreamAgent yields chunks with metadata
type MetadataStreamAgent struct {
	EchoAgent
}

func (m *MetadataStreamAgent) Stream(ctx context.Context, message *agenkit.Message) (<-chan *agenkit.Message, <-chan error) {
	messageChan := make(chan *agenkit.Message, 3)
	errorChan := make(chan error, 1)

	go func() {
		defer close(messageChan)
		defer close(errorChan)

		// Yield 3 chunks with metadata
		for i := 0; i < 3; i++ {
			select {
			case <-ctx.Done():
				errorChan <- ctx.Err()
				return
			default:
				msg := agenkit.NewMessage("agent", fmt.Sprintf("Chunk %d", i)).
					WithMetadata("chunk_id", i).
					WithMetadata("original", message.Metadata)
				messageChan <- msg
			}
		}
	}()

	return messageChan, errorChan
}

func TestStreamingEmpty(t *testing.T) {
	ctx := context.Background()

	tmpDir, err := os.MkdirTemp("", "agenkit-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	socketPath := filepath.Join(tmpDir, "empty.sock")
	endpoint := fmt.Sprintf("unix://%s", socketPath)

	// Start server with empty stream agent
	agent := &EmptyStreamAgent{}
	server, err := local.NewLocalAgent(agent, endpoint)
	if err != nil {
		t.Fatal(err)
	}

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Connect client
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Stream - should complete without yielding anything
	msg := agenkit.NewMessage("user", "test")
	messageChan, errorChan := client.Stream(ctx, msg)

	chunks := []*agenkit.Message{}
	done := false
	for !done {
		select {
		case chunk, ok := <-messageChan:
			if !ok {
				done = true
			} else {
				chunks = append(chunks, chunk)
			}
		case err, ok := <-errorChan:
			if ok && err != nil {
				t.Fatalf("Stream error: %v", err)
			}
			if !ok {
				done = true
			}
		}
	}

	// Should have received 0 chunks
	if len(chunks) != 0 {
		t.Errorf("Expected 0 chunks, got %d", len(chunks))
	}
}

func TestStreamingLargeChunks(t *testing.T) {
	ctx := context.Background()

	tmpDir, err := os.MkdirTemp("", "agenkit-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	socketPath := filepath.Join(tmpDir, "large.sock")
	endpoint := fmt.Sprintf("unix://%s", socketPath)

	// Start server with large chunk agent
	agent := &LargeChunkAgent{}
	server, err := local.NewLocalAgent(agent, endpoint)
	if err != nil {
		t.Fatal(err)
	}

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Connect client
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Stream large chunks
	msg := agenkit.NewMessage("user", "test")
	messageChan, errorChan := client.Stream(ctx, msg)

	chunks := []*agenkit.Message{}
	done := false
	for !done {
		select {
		case chunk, ok := <-messageChan:
			if !ok {
				done = true
			} else {
				chunks = append(chunks, chunk)
			}
		case err, ok := <-errorChan:
			if ok && err != nil {
				t.Fatalf("Stream error: %v", err)
			}
			if !ok {
				done = true
			}
		}
	}

	// Verify we got 3 large chunks
	if len(chunks) != 3 {
		t.Errorf("Expected 3 chunks, got %d", len(chunks))
	}
	for i, chunk := range chunks {
		expected := fmt.Sprintf("Chunk %d:", i)
		if len(chunk.Content) < len(expected)+10000 {
			t.Errorf("Chunk %d: expected length > %d, got %d", i, len(expected)+10000, len(chunk.Content))
		}
	}
}

func TestStreamingErrorInStream(t *testing.T) {
	ctx := context.Background()

	tmpDir, err := os.MkdirTemp("", "agenkit-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	socketPath := filepath.Join(tmpDir, "error.sock")
	endpoint := fmt.Sprintf("unix://%s", socketPath)

	// Start server with error stream agent
	agent := &ErrorStreamAgent{}
	server, err := local.NewLocalAgent(agent, endpoint)
	if err != nil {
		t.Fatal(err)
	}

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Connect client
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Stream - should get error
	msg := agenkit.NewMessage("user", "test")
	messageChan, errorChan := client.Stream(ctx, msg)

	chunks := []*agenkit.Message{}
	gotError := false

	// Read from both channels
	messagesOpen := true
	errorsOpen := true
	for messagesOpen || errorsOpen {
		select {
		case chunk, ok := <-messageChan:
			if !ok {
				messagesOpen = false
			} else {
				chunks = append(chunks, chunk)
			}
		case err, ok := <-errorChan:
			if !ok {
				errorsOpen = false
			} else if err != nil {
				gotError = true
			}
		}
	}

	// Should have gotten at least one chunk before error
	if len(chunks) < 1 {
		t.Errorf("Expected at least 1 chunk, got %d", len(chunks))
	}

	// Should have gotten an error
	if !gotError {
		t.Error("Expected to receive error, but got none")
	}
}

func TestStreamingMultipleClients(t *testing.T) {
	ctx := context.Background()

	tmpDir, err := os.MkdirTemp("", "agenkit-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	socketPath := filepath.Join(tmpDir, "multi.sock")
	endpoint := fmt.Sprintf("unix://%s", socketPath)

	// Start server with streaming agent
	agent := &StreamingEchoAgent{}
	server, err := local.NewLocalAgent(agent, endpoint)
	if err != nil {
		t.Fatal(err)
	}

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Create multiple clients streaming concurrently
	numClients := 3
	var wg sync.WaitGroup
	results := make(chan []string, numClients)
	errors := make(chan error, numClients)

	for i := 0; i < numClients; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()

			client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
			if err != nil {
				errors <- fmt.Errorf("client %d: failed to connect: %w", id, err)
				return
			}
			defer client.Close()

			msg := agenkit.NewMessage("user", fmt.Sprintf("client_%d", id))
			messageChan, errorChan := client.Stream(ctx, msg)

			chunks := []string{}
			done := false
			for !done {
				select {
				case chunk, ok := <-messageChan:
					if !ok {
						done = true
					} else {
						chunks = append(chunks, chunk.Content)
					}
				case err, ok := <-errorChan:
					if ok && err != nil {
						errors <- fmt.Errorf("client %d: stream error: %w", id, err)
						return
					}
					if !ok {
						done = true
					}
				}
			}

			results <- chunks
		}(i)
	}

	wg.Wait()
	close(results)
	close(errors)

	// Check for errors
	for err := range errors {
		t.Error(err)
	}

	// Each client should get all 5 chunks
	resultCount := 0
	for chunks := range results {
		resultCount++
		if len(chunks) != 5 {
			t.Errorf("Client: expected 5 chunks, got %d", len(chunks))
		}
	}

	if resultCount != numClients {
		t.Errorf("Expected %d results, got %d", numClients, resultCount)
	}
}

func TestNonStreamingAgentError(t *testing.T) {
	ctx := context.Background()

	tmpDir, err := os.MkdirTemp("", "agenkit-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	socketPath := filepath.Join(tmpDir, "nostream.sock")
	endpoint := fmt.Sprintf("unix://%s", socketPath)

	// Start server with non-streaming agent (just EchoAgent, which doesn't implement streaming)
	agent := &EchoAgent{}
	server, err := local.NewLocalAgent(agent, endpoint)
	if err != nil {
		t.Fatal(err)
	}

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Connect client
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Try to stream - should get error
	msg := agenkit.NewMessage("user", "test")
	messageChan, errorChan := client.Stream(ctx, msg)

	gotError := false
	done := false
	for !done {
		select {
		case _, ok := <-messageChan:
			if !ok {
				done = true
			}
		case err, ok := <-errorChan:
			if ok && err != nil {
				gotError = true
				// Verify it's a "not implemented" error
				if err.Error() == "" {
					t.Error("Expected non-empty error message")
				}
			}
			if !ok {
				done = true
			}
		}
	}

	if !gotError {
		t.Error("Expected error when streaming from non-streaming agent")
	}
}

func TestStreamingMetadataPreserved(t *testing.T) {
	ctx := context.Background()

	tmpDir, err := os.MkdirTemp("", "agenkit-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	socketPath := filepath.Join(tmpDir, "meta.sock")
	endpoint := fmt.Sprintf("unix://%s", socketPath)

	// Start server with metadata stream agent
	agent := &MetadataStreamAgent{}
	server, err := local.NewLocalAgent(agent, endpoint)
	if err != nil {
		t.Fatal(err)
	}

	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer server.Stop()

	time.Sleep(50 * time.Millisecond)

	// Connect client
	client, err := remote.NewRemoteAgent("echo", endpoint, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()

	// Send message with metadata
	msg := agenkit.NewMessage("user", "test").WithMetadata("key", "value")
	messageChan, errorChan := client.Stream(ctx, msg)

	chunks := []*agenkit.Message{}
	done := false
	for !done {
		select {
		case chunk, ok := <-messageChan:
			if !ok {
				done = true
			} else {
				chunks = append(chunks, chunk)
			}
		case err, ok := <-errorChan:
			if ok && err != nil {
				t.Fatalf("Stream error: %v", err)
			}
			if !ok {
				done = true
			}
		}
	}

	// Verify we got 3 chunks with metadata
	if len(chunks) != 3 {
		t.Errorf("Expected 3 chunks, got %d", len(chunks))
	}
	for i, chunk := range chunks {
		// Check chunk_id metadata
		chunkID, ok := chunk.Metadata["chunk_id"]
		if !ok {
			t.Errorf("Chunk %d: missing chunk_id metadata", i)
		} else if chunkID != float64(i) { // JSON numbers decode as float64
			t.Errorf("Chunk %d: expected chunk_id %d, got %v", i, i, chunkID)
		}

		// Check original metadata
		original, ok := chunk.Metadata["original"]
		if !ok {
			t.Errorf("Chunk %d: missing original metadata", i)
		} else {
			originalMap, ok := original.(map[string]interface{})
			if !ok {
				t.Errorf("Chunk %d: original metadata not a map", i)
			} else {
				keyVal, ok := originalMap["key"]
				if !ok || keyVal != "value" {
					t.Errorf("Chunk %d: original metadata missing or incorrect key value", i)
				}
			}
		}
	}
}
