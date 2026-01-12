package transport

import (
	"context"
	"crypto/tls"
	"fmt"
	"net/url"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/trace"

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/errors"
	"github.com/scttfrdmn/agenkit/agenkit-go/observability"
)

// WebSocketTransport implements transport over WebSocket with automatic reconnection and keepalive.
type WebSocketTransport struct {
	url               string
	conn              *websocket.Conn
	mu                sync.Mutex
	maxRetries        int
	initialRetryDelay time.Duration
	pingInterval      time.Duration
	pingTimeout       time.Duration
	maxMessageSize    int64
	dialer            *websocket.Dialer
	connected         bool
	reconnectMu       sync.Mutex
	stopPing          chan struct{}
	pingDone          chan struct{}
	tracer            trace.Tracer
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
		tracer:            observability.GetTracer("agenkit.transport.websocket"),
	}
}

// Connect establishes WebSocket connection with retry logic.
func (t *WebSocketTransport) Connect(ctx context.Context) error {
	return t.connectWithRetry(ctx)
}

// connectWithRetry connects with exponential backoff retry logic.
func (t *WebSocketTransport) connectWithRetry(ctx context.Context) error {
	ctx, span := t.tracer.Start(ctx, "websocket.connect", trace.WithSpanKind(trace.SpanKindClient))
	defer span.End()

	// Parse URL for span attributes
	parsedURL, _ := url.Parse(t.url)
	scheme := parsedURL.Scheme
	host := parsedURL.Hostname()
	port := parsedURL.Port()
	if port == "" {
		if scheme == "wss" {
			port = "443"
		} else {
			port = "80"
		}
	}

	span.SetAttributes(
		attribute.String("net.protocol.name", "websocket"),
		attribute.String("url.scheme", scheme),
		attribute.String("server.address", host),
		attribute.String("server.port", port),
		attribute.Int("retry.max_attempts", t.maxRetries),
	)

	var lastErr error
	retryDelay := t.initialRetryDelay

	for attempt := 0; attempt < t.maxRetries; attempt++ {
		if attempt > 0 {
			span.AddEvent("retry_attempt", trace.WithAttributes(
				attribute.Int("attempt", attempt),
				attribute.String("retry_delay", retryDelay.String()),
			))

			// Wait before retrying
			select {
			case <-time.After(retryDelay):
			case <-ctx.Done():
				span.RecordError(ctx.Err())
				span.SetStatus(codes.Error, "connection cancelled")
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
			_ = conn.SetReadDeadline(time.Now().Add(t.pingTimeout))
			return nil
		})

		t.mu.Lock()
		t.conn = conn
		t.connected = true
		t.mu.Unlock()

		// Start ping loop
		t.startPingLoop()

		span.SetStatus(codes.Ok, "connected")
		return nil
	}

	err := errors.NewConnectionError(
		fmt.Sprintf("failed to connect to %s after %d attempts", t.url, t.maxRetries),
		lastErr,
	)
	span.RecordError(err)
	span.SetStatus(codes.Error, fmt.Sprintf("failed after %d attempts", t.maxRetries))
	return err
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
				_ = conn.SetWriteDeadline(time.Time{})

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
	ctx, span := t.tracer.Start(ctx, "websocket.send", trace.WithSpanKind(trace.SpanKindClient))
	defer span.End()

	span.SetAttributes(
		attribute.Int("message.size", len(data)),
	)

	if err := t.ensureConnected(ctx); err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, "not connected")
		return err
	}

	// Check size limit
	if int64(len(data)) > t.maxMessageSize {
		err := errors.NewInvalidMessageError(
			fmt.Sprintf("message size %d exceeds maximum %d", len(data), t.maxMessageSize),
			nil,
		)
		span.RecordError(err)
		span.SetStatus(codes.Error, "message too large")
		return err
	}

	t.mu.Lock()
	defer t.mu.Unlock()

	if t.conn == nil {
		err := errors.NewConnectionError("not connected", nil)
		span.RecordError(err)
		span.SetStatus(codes.Error, "not connected")
		return err
	}

	// Set write deadline based on context
	deadline, ok := ctx.Deadline()
	if ok {
		if err := t.conn.SetWriteDeadline(deadline); err != nil {
			span.RecordError(err)
			span.SetStatus(codes.Error, "failed to set deadline")
			return errors.NewConnectionError("failed to set write deadline", err)
		}
	}

	// Send binary message
	if err := t.conn.WriteMessage(websocket.BinaryMessage, data); err != nil {
		t.connected = false
		span.RecordError(err)
		span.SetStatus(codes.Error, "send failed")
		return errors.NewConnectionError("failed to send message", err)
	}

	// Reset write deadline
	if ok {
		_ = t.conn.SetWriteDeadline(time.Time{})
	}

	span.SetStatus(codes.Ok, "sent")
	return nil
}

// ReceiveFramed receives data from WebSocket (no length prefix needed - WebSocket handles framing).
func (t *WebSocketTransport) ReceiveFramed(ctx context.Context) ([]byte, error) {
	ctx, span := t.tracer.Start(ctx, "websocket.receive", trace.WithSpanKind(trace.SpanKindClient))
	defer span.End()

	if err := t.ensureConnected(ctx); err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, "not connected")
		return nil, err
	}

	t.mu.Lock()
	defer t.mu.Unlock()

	if t.conn == nil {
		err := errors.NewConnectionError("not connected", nil)
		span.RecordError(err)
		span.SetStatus(codes.Error, "not connected")
		return nil, err
	}

	// Set read deadline based on context
	deadline, ok := ctx.Deadline()
	if ok {
		if err := t.conn.SetReadDeadline(deadline); err != nil {
			span.RecordError(err)
			span.SetStatus(codes.Error, "failed to set deadline")
			return nil, errors.NewConnectionError("failed to set read deadline", err)
		}
	}

	// Read message
	messageType, data, err := t.conn.ReadMessage()
	if err != nil {
		t.connected = false
		span.RecordError(err)
		if websocket.IsCloseError(err, websocket.CloseNormalClosure, websocket.CloseGoingAway) {
			span.SetStatus(codes.Error, "connection closed")
			return nil, errors.NewConnectionError("connection closed", err)
		}
		span.SetStatus(codes.Error, "receive failed")
		return nil, errors.NewConnectionError("failed to receive message", err)
	}

	// Reset read deadline
	if ok {
		_ = t.conn.SetReadDeadline(time.Time{})
	}

	span.SetAttributes(
		attribute.Int("message.size", len(data)),
		attribute.String("message.type", messageTypeToString(messageType)),
	)

	// Handle different message types
	switch messageType {
	case websocket.BinaryMessage:
		// Check size limit
		if int64(len(data)) > t.maxMessageSize {
			err := errors.NewInvalidMessageError(
				fmt.Sprintf("message size %d exceeds maximum %d", len(data), t.maxMessageSize),
				nil,
			)
			span.RecordError(err)
			span.SetStatus(codes.Error, "message too large")
			return nil, err
		}
		span.SetStatus(codes.Ok, "received")
		return data, nil
	case websocket.TextMessage:
		// Convert text to binary
		if int64(len(data)) > t.maxMessageSize {
			err := errors.NewInvalidMessageError(
				fmt.Sprintf("message size %d exceeds maximum %d", len(data), t.maxMessageSize),
				nil,
			)
			span.RecordError(err)
			span.SetStatus(codes.Error, "message too large")
			return nil, err
		}
		span.SetStatus(codes.Ok, "received")
		return data, nil
	default:
		err := errors.NewInvalidMessageError(
			fmt.Sprintf("unexpected message type: %d", messageType),
			nil,
		)
		span.RecordError(err)
		span.SetStatus(codes.Error, "unexpected message type")
		return nil, err
	}
}

// messageTypeToString converts WebSocket message type to string.
func messageTypeToString(messageType int) string {
	switch messageType {
	case websocket.BinaryMessage:
		return "binary"
	case websocket.TextMessage:
		return "text"
	case websocket.PingMessage:
		return "ping"
	case websocket.PongMessage:
		return "pong"
	case websocket.CloseMessage:
		return "close"
	default:
		return fmt.Sprintf("unknown(%d)", messageType)
	}
}

// Close closes the WebSocket connection gracefully.
func (t *WebSocketTransport) Close() error {
	_, span := t.tracer.Start(context.Background(), "websocket.close", trace.WithSpanKind(trace.SpanKindClient))
	defer span.End()

	t.mu.Lock()
	defer t.mu.Unlock()

	if t.conn == nil {
		span.SetStatus(codes.Ok, "already closed")
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
		span.RecordError(err)
		span.SetStatus(codes.Error, "close message failed")
		return err
	}
	if closeErr != nil {
		span.RecordError(closeErr)
		span.SetStatus(codes.Error, "close failed")
		return closeErr
	}

	span.SetStatus(codes.Ok, "closed")
	return nil
}

// IsConnected returns whether the transport is connected.
func (t *WebSocketTransport) IsConnected() bool {
	t.mu.Lock()
	defer t.mu.Unlock()
	return t.connected && t.conn != nil
}
