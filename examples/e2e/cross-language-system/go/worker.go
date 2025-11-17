// Package main provides a high-performance image processing worker in Go.
//
// This worker demonstrates AgentKit's cross-language capabilities by:
// - Receiving jobs from Python orchestrator via gRPC
// - Performing CPU-intensive image processing tasks
// - Returning results with rich metadata
//
// WHY GO FOR IMAGE PROCESSING?
// ============================
//
// Go provides 10-100x performance improvements for CPU-intensive tasks:
//   • Native compiled code (vs Python interpreted)
//   • Efficient memory management
//   • Built-in concurrency with goroutines
//   • Low garbage collection overhead
//
// PRODUCTION BENEFITS:
// ====================
//
//   • Cost savings: Process 10x more images with same hardware
//   • Latency: Sub-10ms response times vs 100ms+ in Python
//   • Scalability: Handle 1000+ concurrent requests per worker
//   • Resource efficiency: Lower CPU and memory usage

package main

import (
	"context"
	"crypto/md5"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"os"
	"strconv"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/grpc"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/observability"
)

// ImageProcessorAgent handles image processing tasks with high performance.
type ImageProcessorAgent struct {
	workerID string
	started  time.Time
	stats    ProcessingStats
}

// ProcessingStats tracks worker performance.
type ProcessingStats struct {
	TotalTasks      int64
	SuccessfulTasks int64
	FailedTasks     int64
	TotalTimeMs     float64
	TaskCounts      map[string]int64
}

// NewImageProcessorAgent creates a new image processing worker.
func NewImageProcessorAgent(workerID string) *ImageProcessorAgent {
	return &ImageProcessorAgent{
		workerID: workerID,
		started:  time.Now(),
		stats: ProcessingStats{
			TaskCounts: make(map[string]int64),
		},
	}
}

// Name returns the agent name.
func (a *ImageProcessorAgent) Name() string {
	return fmt.Sprintf("image-processor-%s", a.workerID)
}

// Capabilities returns the supported processing tasks.
func (a *ImageProcessorAgent) Capabilities() []string {
	return []string{
		"metadata_extract",
		"thumbnail",
		"optimize",
		"watermark",
		"analyze",
	}
}

// Process handles image processing requests.
func (a *ImageProcessorAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	startTime := time.Now()

	// Extract request metadata
	metadata, ok := message.Metadata.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("invalid metadata format")
	}

	jobID := getStringFromMetadata(metadata, "job_id", "unknown")
	task := getStringFromMetadata(metadata, "task", "unknown")
	imagePath := getStringFromMetadata(metadata, "image_path", "")
	priority := getStringFromMetadata(metadata, "priority", "medium")

	log.Printf("[%s] Processing: job=%s task=%s image=%s priority=%s",
		a.workerID, jobID, task, imagePath, priority)

	// Update stats
	a.stats.TotalTasks++
	a.stats.TaskCounts[task]++

	// Route to appropriate processing function
	var result map[string]interface{}
	var err error

	switch task {
	case "metadata_extract":
		result, err = a.extractMetadata(ctx, imagePath)
	case "thumbnail":
		result, err = a.generateThumbnail(ctx, imagePath)
	case "optimize":
		result, err = a.optimizeImage(ctx, imagePath)
	case "watermark":
		result, err = a.addWatermark(ctx, imagePath)
	case "analyze":
		result, err = a.analyzeImage(ctx, imagePath)
	default:
		err = fmt.Errorf("unsupported task: %s", task)
	}

	processingTime := time.Since(startTime).Milliseconds()
	a.stats.TotalTimeMs += float64(processingTime)

	if err != nil {
		a.stats.FailedTasks++
		log.Printf("[%s] Failed: job=%s task=%s error=%v time=%dms",
			a.workerID, jobID, task, err, processingTime)
		return nil, err
	}

	a.stats.SuccessfulTasks++

	// Build response with metadata
	responseMetadata := map[string]interface{}{
		"job_id":           jobID,
		"task":             task,
		"worker_id":        a.workerID,
		"worker_language":  "go",
		"processing_time_ms": processingTime,
		"timestamp":        time.Now().Unix(),
		"result":           result,
	}

	// Merge result into metadata
	for k, v := range result {
		responseMetadata[k] = v
	}

	log.Printf("[%s] Success: job=%s task=%s time=%dms",
		a.workerID, jobID, task, processingTime)

	return &agenkit.Message{
		Role:     "agent",
		Content:  fmt.Sprintf("Processed: %s", task),
		Metadata: responseMetadata,
	}, nil
}

// extractMetadata simulates EXIF and metadata extraction.
//
// In production, this would use libraries like:
//   - github.com/rwcarlsen/goexif/exif
//   - github.com/h2non/bimg (libvips binding)
func (a *ImageProcessorAgent) extractMetadata(ctx context.Context, imagePath string) (map[string]interface{}, error) {
	// Simulate processing time (real processing would be 5-20ms)
	time.Sleep(time.Millisecond * time.Duration(5+rand.Intn(15)))

	// Generate simulated metadata
	metadata := map[string]interface{}{
		"width":       1920,
		"height":      1080,
		"format":      "JPEG",
		"color_space": "sRGB",
		"dpi":         72,
		"file_size":   2457600, // bytes
		"checksum":    fmt.Sprintf("%x", md5.Sum([]byte(imagePath))),
		"exif": map[string]interface{}{
			"camera":       "Canon EOS R5",
			"focal_length": "50mm",
			"aperture":     "f/1.8",
			"iso":          400,
			"date_taken":   "2024-01-15T14:30:00Z",
		},
	}

	return metadata, nil
}

// generateThumbnail simulates thumbnail generation.
//
// In production, this would use image processing libraries.
func (a *ImageProcessorAgent) generateThumbnail(ctx context.Context, imagePath string) (map[string]interface{}, error) {
	// Simulate processing time (real processing would be 10-30ms)
	time.Sleep(time.Millisecond * time.Duration(10+rand.Intn(20)))

	result := map[string]interface{}{
		"thumbnail_path":   imagePath + ".thumb.jpg",
		"thumbnail_width":  320,
		"thumbnail_height": 240,
		"quality":          85,
		"file_size":        45600,
	}

	return result, nil
}

// optimizeImage simulates image optimization.
//
// In production, this would use optimization tools.
func (a *ImageProcessorAgent) optimizeImage(ctx context.Context, imagePath string) (map[string]interface{}, error) {
	// Simulate processing time (real processing would be 50-200ms)
	time.Sleep(time.Millisecond * time.Duration(50+rand.Intn(150)))

	originalSize := 2457600
	optimizedSize := int(float64(originalSize) * 0.65) // 35% reduction

	result := map[string]interface{}{
		"optimized_path":  imagePath + ".optimized.jpg",
		"original_size":   originalSize,
		"optimized_size":  optimizedSize,
		"compression":     "mozjpeg",
		"size_reduction":  fmt.Sprintf("%.1f%%", 35.0),
	}

	return result, nil
}

// addWatermark simulates watermark addition.
func (a *ImageProcessorAgent) addWatermark(ctx context.Context, imagePath string) (map[string]interface{}, error) {
	// Simulate processing time
	time.Sleep(time.Millisecond * time.Duration(20+rand.Intn(30)))

	result := map[string]interface{}{
		"watermarked_path": imagePath + ".watermarked.jpg",
		"watermark_text":   "© 2024",
		"position":         "bottom-right",
		"opacity":          0.7,
	}

	return result, nil
}

// analyzeImage simulates ML-based image analysis.
//
// In production, this might call Python ML services or use Go ML libraries.
func (a *ImageProcessorAgent) analyzeImage(ctx context.Context, imagePath string) (map[string]interface{}, error) {
	// Simulate processing time (ML inference)
	time.Sleep(time.Millisecond * time.Duration(100+rand.Intn(200)))

	result := map[string]interface{}{
		"scene":      "outdoor",
		"objects":    []string{"person", "tree", "sky", "building"},
		"faces":      2,
		"quality":    "high",
		"brightness": 0.75,
		"contrast":   0.68,
		"sharpness":  0.82,
	}

	return result, nil
}

// GetStats returns worker statistics.
func (a *ImageProcessorAgent) GetStats() ProcessingStats {
	return a.stats
}

// Helper function to safely extract string from metadata
func getStringFromMetadata(metadata map[string]interface{}, key string, defaultValue string) string {
	if val, ok := metadata[key]; ok {
		if str, ok := val.(string); ok {
			return str
		}
	}
	return defaultValue
}

// PrintStats prints worker statistics.
func (a *ImageProcessorAgent) PrintStats() {
	uptime := time.Since(a.started)
	avgTime := float64(0)
	if a.stats.TotalTasks > 0 {
		avgTime = a.stats.TotalTimeMs / float64(a.stats.TotalTasks)
	}

	fmt.Println()
	fmt.Println("=" + repeat("=", 69))
	fmt.Println("WORKER STATISTICS")
	fmt.Println("=" + repeat("=", 69))
	fmt.Printf("Worker ID:        %s\n", a.workerID)
	fmt.Printf("Uptime:           %s\n", uptime.Round(time.Second))
	fmt.Printf("Total tasks:      %d\n", a.stats.TotalTasks)
	fmt.Printf("Successful:       %d\n", a.stats.SuccessfulTasks)
	fmt.Printf("Failed:           %d\n", a.stats.FailedTasks)
	fmt.Printf("Success rate:     %.1f%%\n",
		float64(a.stats.SuccessfulTasks)/float64(a.stats.TotalTasks)*100)
	fmt.Printf("Avg time/task:    %.1fms\n", avgTime)
	fmt.Println()

	if len(a.stats.TaskCounts) > 0 {
		fmt.Println("Tasks by type:")
		for task, count := range a.stats.TaskCounts {
			fmt.Printf("  %-20s %d\n", task+":", count)
		}
		fmt.Println()
	}
}

// Helper function to repeat a string
func repeat(s string, n int) string {
	result := ""
	for i := 0; i < n; i++ {
		result += s
	}
	return result
}

// main starts the Go image processing worker.
func main() {
	// Get port from command line or use default
	port := 50051
	if len(os.Args) > 1 {
		var err error
		port, err = strconv.Atoi(os.Args[1])
		if err != nil {
			// Try parsing as --port=N
			for _, arg := range os.Args[1:] {
				if len(arg) > 7 && arg[:7] == "--port=" {
					port, err = strconv.Atoi(arg[7:])
					if err != nil {
						log.Fatalf("Invalid port: %v", err)
					}
					break
				}
			}
		}
	}

	workerID := fmt.Sprintf("worker-%d", port)

	// Initialize tracing
	_, err := observability.InitTracing(
		fmt.Sprintf("image-processor-%s", workerID),
		"",  // No exporter endpoint for demo
		false, // No console exporter
	)
	if err != nil {
		log.Printf("Warning: Failed to initialize tracing: %v", err)
	}

	// Create agent
	agent := NewImageProcessorAgent(workerID)

	// Wrap with tracing middleware
	tracedAgent := observability.NewTracingMiddleware(agent, "")

	// Create gRPC server
	addr := fmt.Sprintf("localhost:%d", port)
	server, err := grpc.NewGRPCServer(tracedAgent, addr)
	if err != nil {
		log.Fatalf("Failed to create gRPC server: %v", err)
	}

	fmt.Println()
	fmt.Println("╔" + repeat("═", 68) + "╗")
	fmt.Println("║" + repeat(" ", 15) + "Go Image Processing Worker" + repeat(" ", 26) + "║")
	fmt.Println("╚" + repeat("═", 68) + "╝")
	fmt.Println()
	fmt.Printf("Worker ID:      %s\n", workerID)
	fmt.Printf("Address:        %s\n", addr)
	fmt.Printf("Agent Name:     %s\n", agent.Name())
	fmt.Printf("Capabilities:   %v\n", agent.Capabilities())
	fmt.Println()
	fmt.Println("Ready to process image jobs from Python orchestrator!")
	fmt.Println("Press Ctrl+C to stop")
	fmt.Println()

	// Start server
	if err := server.Start(); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}

	// Handle shutdown gracefully
	// (In production, you'd handle signals properly)
	select {}
}
