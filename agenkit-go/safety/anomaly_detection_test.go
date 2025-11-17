package safety

import (
	"context"
	"testing"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// TestAnomalyDetector tests for AnomalyDetector

func TestAnomalyDetectorHighRequestRate(t *testing.T) {
	detector := NewAnomalyDetector()
	detector.MaxRequestsPerMinute = 10 // Lower threshold for testing
	userID := "user123"

	// Simulate high request rate (no sleeps to ensure they're within same second)
	detected := false
	for i := 0; i < 15; i++ {
		event, details := detector.DetectRateAnomaly(userID)
		if event == HighRequestRate {
			if rate, ok := details["requests_per_minute"].(int); !ok || rate <= 0 {
				t.Error("Expected requests_per_minute in details")
			}
			detected = true
			break
		}
	}

	if !detected {
		t.Error("Expected high request rate detection")
	}
}

func TestAnomalyDetectorBurstDetected(t *testing.T) {
	detector := NewAnomalyDetector()
	userID := "user456"

	// Simulate burst
	for i := 0; i < 25; i++ {
		event, details := detector.DetectRateAnomaly(userID)
		if event == BurstDetected {
			if _, ok := details["burst_size"]; !ok {
				t.Error("Expected burst_size in details")
			}
			return
		}
	}
	t.Error("Expected burst detection after many requests")
}

func TestAnomalyDetectorNormalRequestRate(t *testing.T) {
	detector := NewAnomalyDetector()
	userID := "user789"

	// Simulate normal request rate
	for i := 0; i < 3; i++ {
		event, _ := detector.DetectRateAnomaly(userID)
		if event != "" {
			t.Errorf("Expected no anomaly for normal request rate, got: %s", event)
		}
		time.Sleep(100 * time.Millisecond)
	}
}

func TestAnomalyDetectorRepeatedFailures(t *testing.T) {
	detector := NewAnomalyDetector()
	userID := "user111"

	// Need at least 10 total requests, with >50% failures
	// First 6 failures
	for i := 0; i < 6; i++ {
		detector.DetectFailureAnomaly(userID, true)
	}
	// Then 4 successes to reach 10 total
	for i := 0; i < 4; i++ {
		detector.DetectFailureAnomaly(userID, false)
	}
	// Now test - should detect repeated failures (60% failure rate)
	event, details := detector.DetectFailureAnomaly(userID, true)
	if event != RepeatedFailures {
		t.Errorf("Expected repeated failures detection, got: %s", event)
	}
	if rate, ok := details["failure_rate"].(float64); !ok || rate < 0.5 {
		t.Errorf("Expected failure rate >= 0.5, got: %v", rate)
	}
}

func TestAnomalyDetectorMixedSuccessFailure(t *testing.T) {
	detector := NewAnomalyDetector()
	userID := "user222"

	// Simulate mixed success/failure (no anomaly)
	for i := 0; i < 10; i++ {
		isFailure := i%3 == 0
		event, _ := detector.DetectFailureAnomaly(userID, isFailure)
		if event == RepeatedFailures {
			t.Error("Expected no anomaly for mixed success/failure pattern")
		}
	}
}

func TestAnomalyDetectorUnusualInputSize(t *testing.T) {
	detector := NewAnomalyDetector()

	// Feed normal sizes first (need at least 20 for detection)
	for i := 0; i < 20; i++ {
		detector.DetectSizeAnomaly(100, 200)
	}

	// Then feed an unusually large input
	event, details := detector.DetectSizeAnomaly(10000, 200)

	if event != UnusualInputSize {
		t.Errorf("Expected UnusualInputSize, got: %s", event)
	}
	if _, ok := details["input_size"]; !ok {
		t.Error("Expected input_size in details")
	}
}

func TestAnomalyDetectorUnusualOutputSize(t *testing.T) {
	detector := NewAnomalyDetector()

	// Feed normal sizes first (need at least 20 for detection)
	for i := 0; i < 20; i++ {
		detector.DetectSizeAnomaly(100, 200)
	}

	// Then feed an unusually large output
	event, details := detector.DetectSizeAnomaly(100, 10000)

	if event != UnusualOutputSize {
		t.Errorf("Expected UnusualOutputSize, got: %s", event)
	}
	if _, ok := details["output_size"]; !ok {
		t.Error("Expected output_size in details")
	}
}

func TestAnomalyDetectorNormalSizes(t *testing.T) {
	detector := NewAnomalyDetector()

	// Feed normal sizes
	for i := 0; i < 5; i++ {
		event, _ := detector.DetectSizeAnomaly(100, 200)
		if event != "" {
			t.Errorf("Expected no anomaly for normal sizes, got: %s", event)
		}
	}
}

func TestAnomalyDetectorRepetitiveContent(t *testing.T) {
	detector := NewAnomalyDetector()
	userID := "user333"

	// Send same content multiple times (need 5 identical)
	content := "This is the same content"
	for i := 0; i < 6; i++ {
		event, details := detector.DetectContentAnomaly(userID, content)
		if i >= 4 && event == RepetitiveContent {
			if reps, ok := details["repetitions"].(int); !ok || reps != 5 {
				t.Errorf("Expected 5 repetitions, got: %v", reps)
			}
			return
		}
	}
	t.Error("Expected repetitive content detection")
}

func TestAnomalyDetectorVariedContent(t *testing.T) {
	detector := NewAnomalyDetector()
	userID := "user555"

	// Send varied content (no anomaly)
	for i := 0; i < 10; i++ {
		content := "Content number " + string(rune(i)) + " with some variety"
		event, _ := detector.DetectContentAnomaly(userID, content)
		if event != "" {
			t.Errorf("Expected no anomaly for varied content, got: %s", event)
		}
	}
}

// TestAnomalyDetectionMiddleware tests for middleware

func TestAnomalyDetectionMiddlewareBasic(t *testing.T) {
	agent := &mockAgent{name: "test-agent"}
	detector := NewAnomalyDetector()

	callback := func(event SecurityEvent, details map[string]interface{}) {
		// Callback for anomalies
	}

	middleware := NewAnomalyDetectionMiddleware(agent, detector, "user123", callback)

	message := &agenkit.Message{
		Role:    "user",
		Content: "Test message",
	}

	response, err := middleware.Process(context.Background(), message)

	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
	if response == nil {
		t.Error("Expected response, got nil")
	}
}

func TestAnomalyDetectionMiddlewareDefaultDetector(t *testing.T) {
	agent := &mockAgent{name: "test-agent"}
	middleware := NewAnomalyDetectionMiddleware(agent, nil, "user123", nil)

	if middleware.detector == nil {
		t.Error("Expected default detector to be created")
	}
}

func TestAnomalyDetectionMiddlewareCallbackInvoked(t *testing.T) {
	agent := &mockAgent{name: "test-agent"}
	detector := NewAnomalyDetector()

	eventCaptured := ""
	callback := func(event SecurityEvent, details map[string]interface{}) {
		eventCaptured = string(event)
	}

	middleware := NewAnomalyDetectionMiddleware(agent, detector, "user123", callback)

	// Trigger high request rate
	message := &agenkit.Message{
		Role:    "user",
		Content: "Test",
	}

	for i := 0; i < 15; i++ {
		middleware.Process(context.Background(), message)
		time.Sleep(10 * time.Millisecond)
		if eventCaptured != "" {
			break
		}
	}

	if eventCaptured == "" {
		t.Error("Expected callback to be invoked with anomaly event")
	}
}

func TestAnomalyDetectionMiddlewarePreservesAgentName(t *testing.T) {
	agent := &mockAgent{name: "my-agent"}
	middleware := NewAnomalyDetectionMiddleware(agent, nil, "user123", nil)

	if middleware.Name() != "my-agent" {
		t.Errorf("Expected name 'my-agent', got '%s'", middleware.Name())
	}
}

func TestAnomalyDetectionMiddlewarePreservesCapabilities(t *testing.T) {
	agent := &mockAgent{
		name:         "test-agent",
		capabilities: []string{"chat", "search"},
	}
	middleware := NewAnomalyDetectionMiddleware(agent, nil, "user123", nil)

	capabilities := middleware.Capabilities()
	if len(capabilities) != 2 {
		t.Errorf("Expected 2 capabilities, got %d", len(capabilities))
	}
}

func TestSecurityEventTypes(t *testing.T) {
	// Test that security event constants are defined
	events := []SecurityEvent{
		HighRequestRate,
		BurstDetected,
		RepeatedFailures,
		PermissionDeniedSpike,
		ValidationFailures,
		UnusualInputSize,
		UnusualOutputSize,
		UnusualProcessingTime,
		SuspiciousContentPattern,
		RepetitiveContent,
	}

	for _, event := range events {
		if string(event) == "" {
			t.Error("Security event should not be empty")
		}
	}
}

func TestAnomalyDetectorMultipleUsers(t *testing.T) {
	detector := NewAnomalyDetector()

	// Different users should have independent tracking
	for i := 0; i < 5; i++ {
		detector.DetectRateAnomaly("user_a")
		detector.DetectRateAnomaly("user_b")
		time.Sleep(20 * time.Millisecond)
	}

	// Neither should trigger anomaly yet with moderate rate
	event, _ := detector.DetectRateAnomaly("user_a")
	if event != "" {
		t.Error("Expected no anomaly for user_a with moderate rate")
	}
}
