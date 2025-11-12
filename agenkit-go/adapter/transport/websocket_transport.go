package transport

import (
	"context"
	"crypto/tls"
	"fmt"
	"net/url"
	"sync"
	"time"

	"github.com/gorilla/websocket"

	"github.com/agenkit/agenkit-go/adapter/errors"
)

// WebSocketTransport implements transport over WebSocket with automatic reconnection and keepalive.
type WebSocketTransport struct {
	url                string
	conn               *websocket.Conn
	mu                 sync.Mutex
	maxRetries         int
	initialRetryDelay  time.Duration
	pingInterval       time.Duration
	pingTimeout        time.Duration
	maxMessageSize     int64
	dialer             *websocket.Dialer
	connected          bool
	reconnectMu        sync.Mutex
	stopPing           chan struct{}
	pingDone           chan struct{}
}

const (
	defaultMaxRetries        = 5
	defaultInitialRetryDelay = 1 * time.Second
	defaultPingInterval      = 30 * time.Second
	defaultPingTimeout       = 10 * time.Second
	defaultMaxMessageSize    = 10 * 1024 * 1024 // 10 MB
)

// NewWebSocketTransport creates a new WebSocket transport.
func NewWebSocketTransport(urlStr string) *WebSocketTransport {
	return NewWebSocketTransportWithOptions(urlStr, WebSocketOptions{
		MaxRetries:        defaultMaxRetries,
		InitialRetryDelay: defaultInitialRetryDelay,
		PingInterval:      defaultPingInterval,
		PingTimeout:       defaultPingTimeout,
		MaxMessageSize:    defaultMaxMessageSize,
	})
}

// WebSocketOptions configures WebSocket transport behavior.
type WebSocketOptions struct {
	MaxRetries        int
	InitialRetryDelay time.Duration
	PingInterval      time.Duration
	PingTimeout       time.Duration
	MaxMessageSize    int64
}

// NewWebSocketTransportWithOptions creates a new WebSocket transport with custom options.
func NewWebSocketTransportWithOptions(urlStr string, opts WebSocketOptions) *WebSocketTransport {
	// Create dialer with appropriate TLS config
	dialer := &websocket.Dialer{
		HandshakeTimeout: 45 * time.Second,
		ReadBufferSize:   4096,
		WriteBufferSize:  4096,
	}

	// Parse URL to check if it's wss://
	parsedURL, err := url.Parse(urlStr)
	if err == nil && parsedURL.Scheme == "wss" {
		dialer.TLSClientConfig = &tls.Config{
			InsecureSkipVerify: false, // Production should verify certificates
		}
	}

	return &WebSocketTransport{
		url:               urlStr,
		maxRetries:        opts.MaxRetries,
		initialRetryDelay: opts.InitialRetryDelay,
		pingInterval:      opts.PingInterval,
		pingTimeout:       opts.PingTimeout,
		maxMessageSize:    opts.MaxMessageSize,
		dialer:            dialer,
		stopPing:          make(chan struct{}),
		pingDone:          make(chan struct{}),
	}
}

// Connect establishes WebSocket connection with retry logic.
func (t *WebSocketTransport) Connect(ctx context.Context) error {
	return t.connectWithRetry(ctx)
}

// connectWithRetry connects with exponential backoff retry logic.
func (t *WebSocketTransport) connectWithRetry(ctx context.Context) error {
	var lastErr error
	retryDelay := t.initialRetryDelay

	for attempt := 0; attempt < t.maxRetries; attempt++ {
		if attempt > 0 {
			// Wait before retrying
			select {
			case <-time.After(retryDelay):
			case <-ctx.Done():
				return errors.NewConnectionError("connection cancelled", ctx.Err())
			}
			retryDelay *= 2 // Exponential backoff
		}

		// Attempt connection
		conn, _, err := t.dialer.DialContext(ctx, t.url, nil)
		if err != nil {
			lastErr = err
			continue
		}

		// Configure connection
		conn.SetReadLimit(t.maxMessageSize)

		// Set pong handler
		conn.SetPongHandler(func(string) error {
			conn.SetReadDeadline(time.Now().Add(t.pingTimeout))
			return nil
		})

		t.mu.Lock()
		t.conn = conn
		t.connected = true
		t.mu.Unlock()

		// Start ping loop
		t.startPingLoop()

		return nil
	}

	return errors.NewConnectionError(
		fmt.Sprintf("failed to connect to %s after %d attempts", t.url, t.maxRetries),
		lastErr,
	)
}

// startPingLoop starts the ping/pong keepalive loop.
func (t *WebSocketTransport) startPingLoop() {
	// Reset channels
	t.stopPing = make(chan struct{})
	t.pingDone = make(chan struct{})

	go func() {
		defer close(t.pingDone)
		ticker := time.NewTicker(t.pingInterval)
		defer ticker.Stop()

		for {
			select {
			case <-ticker.C:
				t.mu.Lock()
				conn := t.conn
				t.mu.Unlock()

				if conn == nil {
					return
				}

				// Set write deadline for ping
				if err := conn.SetWriteDeadline(time.Now().Add(t.pingTimeout)); err != nil {
					return
				}

				// Send ping
				if err := conn.WriteMessage(websocket.PingMessage, nil); err != nil {
					t.mu.Lock()
					t.connected = false
					t.mu.Unlock()
					return
				}

				// Reset write deadline
				conn.SetWriteDeadline(time.Time{})

			case <-t.stopPing:
				return
			}
		}
	}()
}

// stopPingLoop stops the ping/pong keepalive loop.
func (t *WebSocketTransport) stopPingLoop() {
	close(t.stopPing)
	<-t.pingDone
}

// ensureConnected ensures connection is established, reconnects if necessary.
func (t *WebSocketTransport) ensureConnected(ctx context.Context) error {
	if t.IsConnected() {
		return nil
	}

	t.reconnectMu.Lock()
	defer t.reconnectMu.Unlock()

	// Double-check after acquiring lock
	if t.IsConnected() {
		return nil
	}

	return t.connectWithRetry(ctx)
}

// SendFramed sends data over WebSocket (no length prefix needed - WebSocket handles framing).
func (t *WebSocketTransport) SendFramed(ctx context.Context, data []byte) error {
	if err := t.ensureConnected(ctx); err != nil {
		return err
	}

	// Check size limit
	if int64(len(data)) > t.maxMessageSize {
		return errors.NewInvalidMessageError(
			fmt.Sprintf("message size %d exceeds maximum %d", len(data), t.maxMessageSize),
			nil,
		)
	}

	t.mu.Lock()
	defer t.mu.Unlock()

	if t.conn == nil {
		return errors.NewConnectionError("not connected", nil)
	}

	// Set write deadline based on context
	deadline, ok := ctx.Deadline()
	if ok {
		if err := t.conn.SetWriteDeadline(deadline); err != nil {
			return errors.NewConnectionError("failed to set write deadline", err)
		}
	}

	// Send binary message
	if err := t.conn.WriteMessage(websocket.BinaryMessage, data); err != nil {
		t.connected = false
		return errors.NewConnectionError("failed to send message", err)
	}

	// Reset write deadline
	if ok {
		t.conn.SetWriteDeadline(time.Time{})
	}

	return nil
}

// ReceiveFramed receives data from WebSocket (no length prefix needed - WebSocket handles framing).
func (t *WebSocketTransport) ReceiveFramed(ctx context.Context) ([]byte, error) {
	if err := t.ensureConnected(ctx); err != nil {
		return nil, err
	}

	t.mu.Lock()
	defer t.mu.Unlock()

	if t.conn == nil {
		return nil, errors.NewConnectionError("not connected", nil)
	}

	// Set read deadline based on context
	deadline, ok := ctx.Deadline()
	if ok {
		if err := t.conn.SetReadDeadline(deadline); err != nil {
			return nil, errors.NewConnectionError("failed to set read deadline", err)
		}
	}

	// Read message
	messageType, data, err := t.conn.ReadMessage()
	if err != nil {
		t.connected = false
		if websocket.IsCloseError(err, websocket.CloseNormalClosure, websocket.CloseGoingAway) {
			return nil, errors.NewConnectionError("connection closed", err)
		}
		return nil, errors.NewConnectionError("failed to receive message", err)
	}

	// Reset read deadline
	if ok {
		t.conn.SetReadDeadline(time.Time{})
	}

	// Handle different message types
	switch messageType {
	case websocket.BinaryMessage:
		// Check size limit
		if int64(len(data)) > t.maxMessageSize {
			return nil, errors.NewInvalidMessageError(
				fmt.Sprintf("message size %d exceeds maximum %d", len(data), t.maxMessageSize),
				nil,
			)
		}
		return data, nil
	case websocket.TextMessage:
		// Convert text to binary
		if int64(len(data)) > t.maxMessageSize {
			return nil, errors.NewInvalidMessageError(
				fmt.Sprintf("message size %d exceeds maximum %d", len(data), t.maxMessageSize),
				nil,
			)
		}
		return data, nil
	default:
		return nil, errors.NewInvalidMessageError(
			fmt.Sprintf("unexpected message type: %d", messageType),
			nil,
		)
	}
}

// Close closes the WebSocket connection gracefully.
func (t *WebSocketTransport) Close() error {
	t.mu.Lock()
	defer t.mu.Unlock()

	if t.conn == nil {
		return nil
	}

	// Stop ping loop
	t.stopPingLoop()

	// Send close message
	err := t.conn.WriteMessage(
		websocket.CloseMessage,
		websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""),
	)

	// Close connection
	closeErr := t.conn.Close()
	t.conn = nil
	t.connected = false

	// Return first error encountered
	if err != nil {
		return err
	}
	return closeErr
}

// IsConnected returns whether the transport is connected.
func (t *WebSocketTransport) IsConnected() bool {
	t.mu.Lock()
	defer t.mu.Unlock()
	return t.connected && t.conn != nil
}
