// Package transport provides network transport abstractions for the protocol adapter.
package transport

import (
	"context"
	"encoding/binary"
	"fmt"
	"io"
	"net"
	"os"
	"path/filepath"

	"github.com/agenkit/agenkit-go/adapter/errors"
)

// Transport defines the interface for network communication.
type Transport interface {
	// Connect establishes a connection to the remote endpoint.
	Connect(ctx context.Context) error

	// SendFramed sends a framed message (length-prefixed).
	SendFramed(ctx context.Context, data []byte) error

	// ReceiveFramed receives a framed message (length-prefixed).
	ReceiveFramed(ctx context.Context) ([]byte, error)

	// Close closes the connection.
	Close() error

	// IsConnected returns whether the transport is currently connected.
	IsConnected() bool
}

// UnixSocketTransport implements transport over Unix domain sockets.
type UnixSocketTransport struct {
	path string
	conn net.Conn
}

// NewUnixSocketTransport creates a new Unix socket transport.
func NewUnixSocketTransport(socketPath string) *UnixSocketTransport {
	return &UnixSocketTransport{
		path: socketPath,
	}
}

// Connect establishes connection to Unix socket.
func (t *UnixSocketTransport) Connect(ctx context.Context) error {
	var d net.Dialer
	conn, err := d.DialContext(ctx, "unix", t.path)
	if err != nil {
		return errors.NewConnectionError(fmt.Sprintf("failed to connect to %s", t.path), err)
	}
	t.conn = conn
	return nil
}

// SendFramed sends a length-prefixed message over the Unix socket.
func (t *UnixSocketTransport) SendFramed(ctx context.Context, data []byte) error {
	if t.conn == nil {
		return errors.NewConnectionError("not connected", nil)
	}

	// Write length prefix (4 bytes, big-endian)
	length := uint32(len(data))
	if err := binary.Write(t.conn, binary.BigEndian, length); err != nil {
		return errors.NewConnectionError("failed to write length prefix", err)
	}

	// Write payload
	if _, err := t.conn.Write(data); err != nil {
		return errors.NewConnectionError("failed to write payload", err)
	}

	return nil
}

// ReceiveFramed receives a length-prefixed message from the Unix socket.
func (t *UnixSocketTransport) ReceiveFramed(ctx context.Context) ([]byte, error) {
	if t.conn == nil {
		return nil, errors.NewConnectionError("not connected", nil)
	}

	// Read length prefix (4 bytes, big-endian)
	var length uint32
	if err := binary.Read(t.conn, binary.BigEndian, &length); err != nil {
		if err == io.EOF {
			return nil, errors.NewConnectionError("connection closed", err)
		}
		return nil, errors.NewConnectionError("failed to read length prefix", err)
	}

	// Read payload
	data := make([]byte, length)
	if _, err := io.ReadFull(t.conn, data); err != nil {
		return nil, errors.NewConnectionError("failed to read payload", err)
	}

	return data, nil
}

// Close closes the Unix socket connection.
func (t *UnixSocketTransport) Close() error {
	if t.conn != nil {
		err := t.conn.Close()
		t.conn = nil
		return err
	}
	return nil
}

// IsConnected returns whether the transport is connected.
func (t *UnixSocketTransport) IsConnected() bool {
	return t.conn != nil
}

// TCPTransport implements transport over TCP.
type TCPTransport struct {
	host string
	port int
	conn net.Conn
}

// NewTCPTransport creates a new TCP transport.
func NewTCPTransport(host string, port int) *TCPTransport {
	return &TCPTransport{
		host: host,
		port: port,
	}
}

// Connect establishes connection to TCP endpoint.
func (t *TCPTransport) Connect(ctx context.Context) error {
	address := fmt.Sprintf("%s:%d", t.host, t.port)
	var d net.Dialer
	conn, err := d.DialContext(ctx, "tcp", address)
	if err != nil {
		return errors.NewConnectionError(fmt.Sprintf("failed to connect to %s", address), err)
	}
	t.conn = conn
	return nil
}

// SendFramed sends a length-prefixed message over TCP.
func (t *TCPTransport) SendFramed(ctx context.Context, data []byte) error {
	if t.conn == nil {
		return errors.NewConnectionError("not connected", nil)
	}

	// Write length prefix (4 bytes, big-endian)
	length := uint32(len(data))
	if err := binary.Write(t.conn, binary.BigEndian, length); err != nil {
		return errors.NewConnectionError("failed to write length prefix", err)
	}

	// Write payload
	if _, err := t.conn.Write(data); err != nil {
		return errors.NewConnectionError("failed to write payload", err)
	}

	return nil
}

// ReceiveFramed receives a length-prefixed message from TCP.
func (t *TCPTransport) ReceiveFramed(ctx context.Context) ([]byte, error) {
	if t.conn == nil {
		return nil, errors.NewConnectionError("not connected", nil)
	}

	// Read length prefix (4 bytes, big-endian)
	var length uint32
	if err := binary.Read(t.conn, binary.BigEndian, &length); err != nil {
		if err == io.EOF {
			return nil, errors.NewConnectionError("connection closed", err)
		}
		return nil, errors.NewConnectionError("failed to read length prefix", err)
	}

	// Read payload
	data := make([]byte, length)
	if _, err := io.ReadFull(t.conn, data); err != nil {
		return nil, errors.NewConnectionError("failed to read payload", err)
	}

	return data, nil
}

// Close closes the TCP connection.
func (t *TCPTransport) Close() error {
	if t.conn != nil {
		err := t.conn.Close()
		t.conn = nil
		return err
	}
	return nil
}

// IsConnected returns whether the transport is connected.
func (t *TCPTransport) IsConnected() bool {
	return t.conn != nil
}

// ParseEndpoint parses an endpoint string and returns the appropriate transport.
// Supported formats:
//   - unix:///path/to/socket
//   - tcp://host:port
//   - grpc://host:port
//   - http://host:port or https://host:port
//   - ws://host:port or wss://host:port
func ParseEndpoint(endpoint string) (Transport, error) {
	if len(endpoint) == 0 {
		return nil, fmt.Errorf("empty endpoint")
	}

	// Unix socket
	if len(endpoint) >= 7 && endpoint[:7] == "unix://" {
		socketPath := endpoint[7:]
		return NewUnixSocketTransport(socketPath), nil
	}

	// TCP
	if len(endpoint) >= 6 && endpoint[:6] == "tcp://" {
		tcpPart := endpoint[6:]
		// Find last colon to split host:port
		lastColon := -1
		for i := len(tcpPart) - 1; i >= 0; i-- {
			if tcpPart[i] == ':' {
				lastColon = i
				break
			}
		}
		if lastColon == -1 {
			return nil, fmt.Errorf("invalid TCP endpoint format: %s", endpoint)
		}
		host := tcpPart[:lastColon]
		portStr := tcpPart[lastColon+1:]
		port := 0
		if _, err := fmt.Sscanf(portStr, "%d", &port); err != nil {
			return nil, fmt.Errorf("invalid port in TCP endpoint: %s", endpoint)
		}
		if port <= 0 || port > 65535 {
			return nil, fmt.Errorf("invalid port in endpoint: %s", endpoint)
		}
		return NewTCPTransport(host, port), nil
	}

	// gRPC
	if len(endpoint) >= 7 && endpoint[:7] == "grpc://" {
		return NewGRPCTransport(endpoint)
	}

	// WebSocket
	if len(endpoint) >= 6 && endpoint[:6] == "wss://" {
		return NewWebSocketTransport(endpoint), nil
	}
	if len(endpoint) >= 5 && endpoint[:5] == "ws://" {
		return NewWebSocketTransport(endpoint), nil
	}

	// HTTP/HTTPS/H2C/H3
	if len(endpoint) >= 8 && endpoint[:8] == "https://" {
		return NewHTTPTransport(endpoint), nil
	}
	if len(endpoint) >= 7 && endpoint[:7] == "http://" {
		return NewHTTPTransport(endpoint), nil
	}
	if len(endpoint) >= 6 && endpoint[:6] == "h2c://" {
		return NewHTTPTransport(endpoint), nil
	}
	if len(endpoint) >= 5 && endpoint[:5] == "h3://" {
		return NewHTTPTransport(endpoint), nil
	}

	return nil, fmt.Errorf("unsupported endpoint format: %s", endpoint)
}

// CreateUnixSocketServer creates a Unix socket listener.
func CreateUnixSocketServer(socketPath string) (net.Listener, error) {
	// Ensure directory exists
	dir := filepath.Dir(socketPath)
	if err := os.MkdirAll(dir, 0700); err != nil {
		return nil, fmt.Errorf("failed to create socket directory: %w", err)
	}

	// Remove existing socket file if present
	if err := os.Remove(socketPath); err != nil && !os.IsNotExist(err) {
		return nil, fmt.Errorf("failed to remove existing socket: %w", err)
	}

	// Create listener
	listener, err := net.Listen("unix", socketPath)
	if err != nil {
		return nil, fmt.Errorf("failed to create Unix socket listener: %w", err)
	}

	// Set socket permissions
	if err := os.Chmod(socketPath, 0600); err != nil {
		listener.Close()
		return nil, fmt.Errorf("failed to set socket permissions: %w", err)
	}

	return listener, nil
}

// CreateTCPServer creates a TCP listener.
func CreateTCPServer(host string, port int) (net.Listener, error) {
	address := fmt.Sprintf("%s:%d", host, port)
	listener, err := net.Listen("tcp", address)
	if err != nil {
		return nil, fmt.Errorf("failed to create TCP listener: %w", err)
	}
	return listener, nil
}
