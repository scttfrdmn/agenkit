package safety

import (
	"context"
	"hash/fnv"
	"log"
	"math"
	"sync"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// SecurityEvent represents types of security events.
type SecurityEvent string

const (
	// Rate anomalies
	HighRequestRate SecurityEvent = "high_request_rate"
	BurstDetected   SecurityEvent = "burst_detected"

	// Pattern anomalies
	RepeatedFailures      SecurityEvent = "repeated_failures"
	PermissionDeniedSpike SecurityEvent = "permission_denied_spike"
	ValidationFailures    SecurityEvent = "validation_failures"

	// Behavior anomalies
	UnusualInputSize      SecurityEvent = "unusual_input_size"
	UnusualOutputSize     SecurityEvent = "unusual_output_size"
	UnusualProcessingTime SecurityEvent = "unusual_processing_time"

	// Content anomalies
	SuspiciousContentPattern SecurityEvent = "suspicious_content_pattern"
	RepetitiveContent        SecurityEvent = "repetitive_content"
)

// AnomalyDetector detects anomalous agent behavior.
//
// Uses statistical methods and heuristics to identify:
//   - Rate-based anomalies
//   - Pattern-based anomalies
//   - Content-based anomalies
//
// Example:
//
//	detector := NewAnomalyDetector()
//	detector.MaxRequestsPerMinute = 100
//	anomaly := detector.DetectRateAnomaly("user123")
type AnomalyDetector struct {
	// Rate limiting thresholds
	MaxRequestsPerMinute int
	MaxBurstSize         int // requests in 1 second

	// Size thresholds (standard deviations)
	InputSizeThreshold  float64 // 3 sigma
	OutputSizeThreshold float64

	// Processing time threshold (seconds)
	ProcessingTimeThreshold float64

	// Failure rate threshold (percentage)
	FailureRateThreshold float64 // 0.5 = 50%

	// Tracking data structures
	mu                sync.RWMutex
	requestTimestamps map[string][]float64
	failureCounts     map[string]int
	successCounts     map[string]int

	// Statistics (rolling averages)
	inputSizes      []int
	outputSizes     []int
	processingTimes []float64

	// Content tracking (for repetition detection)
	recentContent map[string][]uint64
}

// NewAnomalyDetector creates a new anomaly detector with default settings.
//
// Example:
//
//	detector := NewAnomalyDetector()
func NewAnomalyDetector() *AnomalyDetector {
	return &AnomalyDetector{
		MaxRequestsPerMinute:    60,
		MaxBurstSize:            10,
		InputSizeThreshold:      3.0,
		OutputSizeThreshold:     3.0,
		ProcessingTimeThreshold: 30.0,
		FailureRateThreshold:    0.5,
		requestTimestamps:       make(map[string][]float64),
		failureCounts:           make(map[string]int),
		successCounts:           make(map[string]int),
		inputSizes:              make([]int, 0, 100),
		outputSizes:             make([]int, 0, 100),
		processingTimes:         make([]float64, 0, 100),
		recentContent:           make(map[string][]uint64),
	}
}

// DetectRateAnomaly detects rate-based anomalies.
//
// Args:
//
//	userID: User identifier
//
// Returns:
//
//	event: SecurityEvent if anomaly detected, empty string otherwise
//	details: Details about the anomaly
func (d *AnomalyDetector) DetectRateAnomaly(userID string) (SecurityEvent, map[string]interface{}) {
	d.mu.Lock()
	defer d.mu.Unlock()

	now := time.Now().Unix()
	nowFloat := float64(now)

	// Record request
	if d.requestTimestamps[userID] == nil {
		d.requestTimestamps[userID] = make([]float64, 0, 1000)
	}
	d.requestTimestamps[userID] = append(d.requestTimestamps[userID], nowFloat)

	// Clean old timestamps (> 60 seconds)
	cleaned := make([]float64, 0, len(d.requestTimestamps[userID]))
	for _, ts := range d.requestTimestamps[userID] {
		if nowFloat-ts <= 60.0 {
			cleaned = append(cleaned, ts)
		}
	}
	d.requestTimestamps[userID] = cleaned

	// Keep only last 1000 timestamps
	if len(d.requestTimestamps[userID]) > 1000 {
		d.requestTimestamps[userID] = d.requestTimestamps[userID][len(d.requestTimestamps[userID])-1000:]
	}

	// Check request rate (per minute)
	requestsPerMinute := len(d.requestTimestamps[userID])
	if requestsPerMinute > d.MaxRequestsPerMinute {
		return HighRequestRate, map[string]interface{}{
			"user_id":             userID,
			"requests_per_minute": requestsPerMinute,
			"threshold":           d.MaxRequestsPerMinute,
		}
	}

	// Check burst rate (per second)
	recent := 0
	for _, ts := range d.requestTimestamps[userID] {
		if nowFloat-ts < 1.0 {
			recent++
		}
	}
	if recent > d.MaxBurstSize {
		return BurstDetected, map[string]interface{}{
			"user_id":    userID,
			"burst_size": recent,
			"threshold":  d.MaxBurstSize,
		}
	}

	return "", nil
}

// DetectFailureAnomaly detects failure rate anomalies.
//
// Args:
//
//	userID: User identifier
//	isFailure: Whether current request failed
//
// Returns:
//
//	event: SecurityEvent if anomaly detected, empty string otherwise
//	details: Details about the anomaly
func (d *AnomalyDetector) DetectFailureAnomaly(userID string, isFailure bool) (SecurityEvent, map[string]interface{}) {
	d.mu.Lock()
	defer d.mu.Unlock()

	// Update counts
	if isFailure {
		d.failureCounts[userID]++
	} else {
		d.successCounts[userID]++
	}

	// Calculate failure rate
	total := d.failureCounts[userID] + d.successCounts[userID]
	if total >= 10 { // Need at least 10 requests for meaningful rate
		failureRate := float64(d.failureCounts[userID]) / float64(total)

		if failureRate > d.FailureRateThreshold {
			return RepeatedFailures, map[string]interface{}{
				"user_id":      userID,
				"failure_rate": failureRate,
				"failures":     d.failureCounts[userID],
				"total":        total,
			}
		}
	}

	return "", nil
}

// DetectSizeAnomaly detects unusual input/output sizes.
//
// Args:
//
//	inputSize: Input message size
//	outputSize: Output message size
//
// Returns:
//
//	event: SecurityEvent if anomaly detected, empty string otherwise
//	details: Details about the anomaly
func (d *AnomalyDetector) DetectSizeAnomaly(inputSize, outputSize int) (SecurityEvent, map[string]interface{}) {
	d.mu.Lock()
	defer d.mu.Unlock()

	// Track sizes
	d.inputSizes = append(d.inputSizes, inputSize)
	d.outputSizes = append(d.outputSizes, outputSize)

	// Keep only last 100 entries
	if len(d.inputSizes) > 100 {
		d.inputSizes = d.inputSizes[len(d.inputSizes)-100:]
	}
	if len(d.outputSizes) > 100 {
		d.outputSizes = d.outputSizes[len(d.outputSizes)-100:]
	}

	// Need enough data points for statistics
	if len(d.inputSizes) < 20 {
		return "", nil
	}

	// Calculate mean and std dev for input
	inputMean := mean(d.inputSizes)
	inputStdev := stdev(d.inputSizes, inputMean)

	// Calculate mean and std dev for output
	outputMean := mean(d.outputSizes)
	outputStdev := stdev(d.outputSizes, outputMean)

	// Check input size anomaly (> threshold std devs from mean)
	if inputStdev > 0 {
		inputZScore := math.Abs(float64(inputSize)-inputMean) / inputStdev
		if inputZScore > d.InputSizeThreshold {
			return UnusualInputSize, map[string]interface{}{
				"input_size": inputSize,
				"mean":       inputMean,
				"stdev":      inputStdev,
				"z_score":    inputZScore,
			}
		}
	}

	// Check output size anomaly
	if outputStdev > 0 {
		outputZScore := math.Abs(float64(outputSize)-outputMean) / outputStdev
		if outputZScore > d.OutputSizeThreshold {
			return UnusualOutputSize, map[string]interface{}{
				"output_size": outputSize,
				"mean":        outputMean,
				"stdev":       outputStdev,
				"z_score":     outputZScore,
			}
		}
	}

	return "", nil
}

// DetectContentAnomaly detects content-based anomalies.
//
// Args:
//
//	userID: User identifier
//	content: Message content
//
// Returns:
//
//	event: SecurityEvent if anomaly detected, empty string otherwise
//	details: Details about the anomaly
func (d *AnomalyDetector) DetectContentAnomaly(userID string, content string) (SecurityEvent, map[string]interface{}) {
	d.mu.Lock()
	defer d.mu.Unlock()

	// Hash content (first 500 chars)
	contentToHash := content
	if len(contentToHash) > 500 {
		contentToHash = contentToHash[:500]
	}
	contentHash := hashString(contentToHash)

	// Track recent content
	if d.recentContent[userID] == nil {
		d.recentContent[userID] = make([]uint64, 0, 10)
	}
	d.recentContent[userID] = append(d.recentContent[userID], contentHash)

	// Keep only last 10 entries
	if len(d.recentContent[userID]) > 10 {
		d.recentContent[userID] = d.recentContent[userID][len(d.recentContent[userID])-10:]
	}

	// Check for repetitive content (same content repeated)
	if len(d.recentContent[userID]) >= 5 {
		recent5 := d.recentContent[userID][len(d.recentContent[userID])-5:]

		// Check if all 5 are the same
		allSame := true
		firstHash := recent5[0]
		for _, h := range recent5[1:] {
			if h != firstHash {
				allSame = false
				break
			}
		}

		if allSame {
			return RepetitiveContent, map[string]interface{}{
				"user_id":     userID,
				"repetitions": 5,
			}
		}
	}

	return "", nil
}

// Helper functions

// mean calculates the mean of a slice of integers.
func mean(values []int) float64 {
	if len(values) == 0 {
		return 0
	}
	sum := 0
	for _, v := range values {
		sum += v
	}
	return float64(sum) / float64(len(values))
}

// stdev calculates the standard deviation of a slice of integers.
func stdev(values []int, mean float64) float64 {
	if len(values) <= 1 {
		return 0
	}
	sumSquares := 0.0
	for _, v := range values {
		diff := float64(v) - mean
		sumSquares += diff * diff
	}
	variance := sumSquares / float64(len(values)-1)
	return math.Sqrt(variance)
}

// hashString hashes a string to uint64.
func hashString(s string) uint64 {
	h := fnv.New64a()
	h.Write([]byte(s))
	return h.Sum64()
}

// AnomalyCallback is the callback function signature for anomaly events.
type AnomalyCallback func(event SecurityEvent, details map[string]interface{})

// AnomalyDetectionMiddleware provides middleware for anomaly detection.
//
// Monitors agent interactions and detects:
//   - Rate anomalies
//   - Failure patterns
//   - Size anomalies
//   - Content anomalies
//
// Example:
//
//	detector := NewAnomalyDetector()
//	detector.MaxRequestsPerMinute = 100
//
//	middleware := NewAnomalyDetectionMiddleware(
//	    baseAgent,
//	    detector,
//	    "user123",
//	    func(event SecurityEvent, details map[string]interface{}) {
//	        log.Printf("ANOMALY: %s - %v", event, details)
//	    },
//	)
type AnomalyDetectionMiddleware struct {
	agent     agenkit.Agent
	detector  *AnomalyDetector
	userID    string
	onAnomaly AnomalyCallback
}

// NewAnomalyDetectionMiddleware creates a new anomaly detection middleware.
//
// Args:
//
//	agent: Agent to wrap
//	detector: Anomaly detector (nil = default detector)
//	userID: User identifier for tracking
//	onAnomaly: Callback function for anomaly events (nil = default handler)
//
// Example:
//
//	middleware := NewAnomalyDetectionMiddleware(
//	    agent,
//	    NewAnomalyDetector(),
//	    "user123",
//	    func(event SecurityEvent, details map[string]interface{}) {
//	        log.Printf("SECURITY ANOMALY: %s", event)
//	    },
//	)
func NewAnomalyDetectionMiddleware(
	agent agenkit.Agent,
	detector *AnomalyDetector,
	userID string,
	onAnomaly AnomalyCallback,
) *AnomalyDetectionMiddleware {
	if detector == nil {
		detector = NewAnomalyDetector()
	}

	if onAnomaly == nil {
		onAnomaly = defaultAnomalyHandler
	}

	return &AnomalyDetectionMiddleware{
		agent:     agent,
		detector:  detector,
		userID:    userID,
		onAnomaly: onAnomaly,
	}
}

// defaultAnomalyHandler is the default anomaly handler that logs to console.
func defaultAnomalyHandler(event SecurityEvent, details map[string]interface{}) {
	log.Printf("SECURITY ANOMALY DETECTED: %s", event)
	log.Printf("Details: %v", details)
}

// Name returns the name of the underlying agent.
func (m *AnomalyDetectionMiddleware) Name() string {
	return m.agent.Name()
}

// Capabilities returns capabilities of the underlying agent.
func (m *AnomalyDetectionMiddleware) Capabilities() []string {
	return m.agent.Capabilities()
}

// Process processes message with anomaly detection.
func (m *AnomalyDetectionMiddleware) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	startTime := time.Now()

	// 1. Check rate anomaly
	if event, details := m.detector.DetectRateAnomaly(m.userID); event != "" {
		m.onAnomaly(event, details)
	}

	// 2. Check content anomaly
	contentStr := message.Content
	if event, details := m.detector.DetectContentAnomaly(m.userID, contentStr); event != "" {
		m.onAnomaly(event, details)
	}

	// 3. Process with wrapped agent
	isFailure := false
	var response *agenkit.Message
	var processErr error

	response, processErr = m.agent.Process(ctx, message)
	if processErr != nil {
		isFailure = true
	}

	// 4. Check failure anomaly
	if event, details := m.detector.DetectFailureAnomaly(m.userID, isFailure); event != "" {
		m.onAnomaly(event, details)
	}

	// 5. Check size and timing anomalies (if succeeded)
	if response != nil {
		processingTime := time.Since(startTime).Seconds()
		inputSize := len(contentStr)
		outputSize := len(response.Content)

		// Check size anomaly
		if event, details := m.detector.DetectSizeAnomaly(inputSize, outputSize); event != "" {
			m.onAnomaly(event, details)
		}

		// Check processing time
		if processingTime > m.detector.ProcessingTimeThreshold {
			m.onAnomaly(UnusualProcessingTime, map[string]interface{}{
				"user_id":         m.userID,
				"processing_time": processingTime,
				"threshold":       m.detector.ProcessingTimeThreshold,
			})
		}
	}

	// Return original error if any
	if processErr != nil {
		return nil, processErr
	}

	return response, nil
}
