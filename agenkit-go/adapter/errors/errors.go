// Package errors defines error types for the protocol adapter.
package errors

import "fmt"

// ConnectionError represents a connection failure.
type ConnectionError struct {
	Message string
	Cause   error
}

func (e *ConnectionError) Error() string {
	if e.Cause != nil {
		return fmt.Sprintf("connection error: %s: %v", e.Message, e.Cause)
	}
	return fmt.Sprintf("connection error: %s", e.Message)
}

func (e *ConnectionError) Unwrap() error {
	return e.Cause
}

// NewConnectionError creates a new connection error.
func NewConnectionError(message string, cause error) *ConnectionError {
	return &ConnectionError{Message: message, Cause: cause}
}

// ProtocolError represents a protocol-level error.
type ProtocolError struct {
	Code    string
	Message string
	Details map[string]interface{}
}

func (e *ProtocolError) Error() string {
	if e.Details != nil && len(e.Details) > 0 {
		return fmt.Sprintf("protocol error [%s]: %s (details: %v)", e.Code, e.Message, e.Details)
	}
	return fmt.Sprintf("protocol error [%s]: %s", e.Code, e.Message)
}

// NewProtocolError creates a new protocol error.
func NewProtocolError(code, message string, details map[string]interface{}) *ProtocolError {
	return &ProtocolError{Code: code, Message: message, Details: details}
}

// InvalidMessageError represents an invalid message format.
type InvalidMessageError struct {
	Message string
	Details map[string]interface{}
}

func (e *InvalidMessageError) Error() string {
	if e.Details != nil && len(e.Details) > 0 {
		return fmt.Sprintf("invalid message: %s (details: %v)", e.Message, e.Details)
	}
	return fmt.Sprintf("invalid message: %s", e.Message)
}

// NewInvalidMessageError creates a new invalid message error.
func NewInvalidMessageError(message string, details map[string]interface{}) *InvalidMessageError {
	return &InvalidMessageError{Message: message, Details: details}
}

// RemoteExecutionError represents an error from the remote agent.
type RemoteExecutionError struct {
	AgentName string
	Message   string
	Details   map[string]interface{}
}

func (e *RemoteExecutionError) Error() string {
	if e.Details != nil && len(e.Details) > 0 {
		return fmt.Sprintf("remote execution error in agent '%s': %s (details: %v)", e.AgentName, e.Message, e.Details)
	}
	return fmt.Sprintf("remote execution error in agent '%s': %s", e.AgentName, e.Message)
}

// NewRemoteExecutionError creates a new remote execution error.
func NewRemoteExecutionError(agentName, message string, details map[string]interface{}) *RemoteExecutionError {
	return &RemoteExecutionError{AgentName: agentName, Message: message, Details: details}
}

// AgentTimeoutError represents a timeout waiting for agent response.
type AgentTimeoutError struct {
	AgentName string
	Timeout   float64
}

func (e *AgentTimeoutError) Error() string {
	return fmt.Sprintf("timeout waiting for agent '%s' (timeout: %.1fs)", e.AgentName, e.Timeout)
}

// NewAgentTimeoutError creates a new agent timeout error.
func NewAgentTimeoutError(agentName string, timeout float64) *AgentTimeoutError {
	return &AgentTimeoutError{AgentName: agentName, Timeout: timeout}
}
