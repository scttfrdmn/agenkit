package main

import (
	"encoding/json"
	"fmt"
	"strings"
	"testing"
)

func TestHealthCheck(t *testing.T) {
	// Create test input
	input := `{"protocol_version":"1.0","request_id":"test1","command":"health_check","payload":{}}`

	// Parse request
	var request Request
	if err := json.Unmarshal([]byte(input), &request); err != nil {
		t.Fatalf("Failed to parse request: %v", err)
	}

	// Handle request
	response := handleRequest(request)

	// Check response
	if response.Status != "success" {
		t.Errorf("Expected status 'success', got '%s'", response.Status)
	}

	if response.RequestID != "test1" {
		t.Errorf("Expected request_id 'test1', got '%s'", response.RequestID)
	}

	// Marshal and print
	output, _ := json.MarshalIndent(response, "", "  ")
	fmt.Printf("Health check response:\n%s\n", string(output))
}

func TestGetInfo(t *testing.T) {
	input := `{"protocol_version":"1.0","request_id":"test2","command":"get_info","payload":{}}`

	var request Request
	if err := json.Unmarshal([]byte(input), &request); err != nil {
		t.Fatalf("Failed to parse request: %v", err)
	}

	response := handleRequest(request)

	if response.Status != "success" {
		t.Errorf("Expected status 'success', got '%s'", response.Status)
	}

	// Check patterns supported
	if result, ok := response.Result["language"].(string); !ok || result != "go" {
		t.Errorf("Expected language 'go', got '%v'", response.Result["language"])
	}

	output, _ := json.MarshalIndent(response, "", "  ")
	fmt.Printf("Get info response:\n%s\n", string(output))
}

func TestReflectionPattern(t *testing.T) {
	input := `{
		"protocol_version":"1.0",
		"request_id":"test3",
		"command":"execute_test",
		"payload":{
			"pattern":"Reflection",
			"scenario_id":"reflection_basic",
			"input":{
				"message":{
					"role":"user",
					"content":"Write a poem about technology",
					"metadata":{}
				},
				"config":{
					"max_iterations":3
				}
			}
		}
	}`

	// Remove whitespace for parsing
	input = strings.ReplaceAll(input, "\n", "")
	input = strings.ReplaceAll(input, "\t", "")

	var request Request
	if err := json.Unmarshal([]byte(input), &request); err != nil {
		t.Fatalf("Failed to parse request: %v", err)
	}

	response := handleRequest(request)

	if response.Status != "success" {
		t.Errorf("Expected status 'success', got '%s'. Error: %v", response.Status, response.Error)
	}

	output, _ := json.MarshalIndent(response, "", "  ")
	fmt.Printf("Reflection test response:\n%s\n", string(output))
}

func TestSequentialPattern(t *testing.T) {
	input := `{
		"protocol_version":"1.0",
		"request_id":"test4",
		"command":"execute_test",
		"payload":{
			"pattern":"Sequential",
			"scenario_id":"sequential_basic",
			"input":{
				"message":{
					"role":"user",
					"content":"Process this message",
					"metadata":{}
				},
				"config":{
					"agents":[
						{"name":"agent1","type":"echo"},
						{"name":"agent2","type":"echo"}
					]
				}
			}
		}
	}`

	input = strings.ReplaceAll(input, "\n", "")
	input = strings.ReplaceAll(input, "\t", "")

	var request Request
	if err := json.Unmarshal([]byte(input), &request); err != nil {
		t.Fatalf("Failed to parse request: %v", err)
	}

	response := handleRequest(request)

	if response.Status != "success" {
		t.Errorf("Expected status 'success', got '%s'. Error: %v", response.Status, response.Error)
	}

	// Verify result structure
	if response.Result == nil {
		t.Errorf("Expected result to be non-nil")
	} else {
		// Verify output exists
		if output, ok := response.Result["output"].(map[string]interface{}); ok {
			if message, ok := output["message"].(map[string]interface{}); ok {
				if content, ok := message["content"].(string); ok {
					fmt.Printf("Sequential test - Message content: %s\n", content)
				}
			}
		}
	}

	output, err := json.MarshalIndent(response, "", "  ")
	if err != nil {
		t.Logf("Note: Could not marshal full response (possible circular reference): %v", err)
	} else {
		fmt.Printf("Sequential test response:\n%s\n", string(output))
	}
}
