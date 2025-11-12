/*
Transport protocol benchmarks for agenkit-go.

These benchmarks measure the performance differences between transport protocols:
- HTTP/1.1 (http://)
- HTTP/2 cleartext (h2c://)

Methodology:
1. Start agent servers for each protocol
2. Measure latency and throughput with go test -bench
3. Test with different message sizes
4. Compare against Python benchmarks

Target: Establish baselines and compare Go vs Python performance
*/

package benchmarks

import (
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"fmt"
	"math/big"
	"net"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/agenkit/agenkit-go/adapter/http"
	"github.com/agenkit/agenkit-go/adapter/remote"
	"github.com/agenkit/agenkit-go/adapter/transport"
	"github.com/agenkit/agenkit-go/agenkit"
)

// ============================================
// Test Agents
// ============================================

// EchoAgent is a test agent that echoes messages back.
type EchoAgent struct{}

func (a *EchoAgent) Name() string {
	return "echo-agent"
}

func (a *EchoAgent) Capabilities() []string {
	return []string{"echo"}
}

func (a *EchoAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return agenkit.NewMessage("agent", "Echo: "+message.Content), nil
}

// SlowAgent simulates processing time.
type SlowAgent struct {
	delayMs int
}

func (a *SlowAgent) Name() string {
	return "slow-agent"
}

func (a *SlowAgent) Capabilities() []string {
	return []string{"slow"}
}

func (a *SlowAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(time.Duration(a.delayMs) * time.Millisecond)
	return agenkit.NewMessage("agent", "Processed: "+message.Content), nil
}

// ============================================
// TLS Certificate Generation
// ============================================

// generateSelfSignedCert generates a self-signed TLS certificate for localhost testing.
// Returns a tls.Certificate that can be used for HTTPS and HTTP/3 servers.
func generateSelfSignedCert() (tls.Certificate, error) {
	// Generate private key
	privateKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return tls.Certificate{}, err
	}

	// Create certificate template
	template := x509.Certificate{
		SerialNumber: big.NewInt(1),
		Subject: pkix.Name{
			Organization: []string{"Agenkit Benchmarks"},
			CommonName:   "localhost",
		},
		NotBefore:             time.Now(),
		NotAfter:              time.Now().Add(365 * 24 * time.Hour), // 1 year validity
		KeyUsage:              x509.KeyUsageKeyEncipherment | x509.KeyUsageDigitalSignature,
		ExtKeyUsage:           []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
		BasicConstraintsValid: true,
		DNSNames:              []string{"localhost"},
		IPAddresses:           []net.IP{net.ParseIP("127.0.0.1"), net.ParseIP("::1")},
	}

	// Create self-signed certificate
	certDER, err := x509.CreateCertificate(rand.Reader, &template, &template, &privateKey.PublicKey, privateKey)
	if err != nil {
		return tls.Certificate{}, err
	}

	// Encode certificate and key to PEM format
	certPEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: certDER})
	keyPEM := pem.EncodeToMemory(&pem.Block{Type: "RSA PRIVATE KEY", Bytes: x509.MarshalPKCS1PrivateKey(privateKey)})

	// Load as tls.Certificate
	cert, err := tls.X509KeyPair(certPEM, keyPEM)
	if err != nil {
		return tls.Certificate{}, err
	}

	return cert, nil
}

// ============================================
// Server Management
// ============================================

// ServerManager handles starting and stopping test servers.
type ServerManager struct {
	servers []*http.HTTPAgent
	mu      sync.Mutex
}

func NewServerManager() *ServerManager {
	return &ServerManager{
		servers: make([]*http.HTTPAgent, 0),
	}
}

// StartServer starts an HTTP server with the given configuration.
// Supports protocols: "http" (HTTP/1.1), "h2c" (HTTP/2 cleartext), "h3" (HTTP/3 over QUIC)
func (sm *ServerManager) StartServer(agent agenkit.Agent, protocol string, port int) (string, error) {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	addr := fmt.Sprintf("localhost:%d", port)
	enableHTTP2 := strings.HasPrefix(protocol, "h2")
	enableHTTP3 := strings.HasPrefix(protocol, "h3")

	var tlsConfig *tls.Config
	if enableHTTP3 {
		// HTTP/3 requires TLS - generate self-signed cert
		cert, err := generateSelfSignedCert()
		if err != nil {
			return "", fmt.Errorf("failed to generate TLS certificate: %w", err)
		}
		tlsConfig = &tls.Config{
			Certificates: []tls.Certificate{cert},
			NextProtos:   []string{"h3"}, // HTTP/3 ALPN
		}
	}

	server := http.NewHTTPAgentWithOptions(agent, addr, http.ServerOptions{
		EnableHTTP2: enableHTTP2,
		EnableHTTP3: enableHTTP3,
		TLSConfig:   tlsConfig,
		HTTP3Addr:   addr, // Use same address for HTTP/3
	})

	if err := server.Start(context.Background()); err != nil {
		return "", err
	}

	// Wait for server to be ready
	time.Sleep(200 * time.Millisecond)

	sm.servers = append(sm.servers, server)
	return fmt.Sprintf("%s://%s", protocol, addr), nil
}

// Shutdown stops all running servers.
func (sm *ServerManager) Shutdown() {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	for _, server := range sm.servers {
		server.Stop()
	}
	sm.servers = nil

	// Wait for UDP ports to be fully released by OS (important for HTTP/3)
	// This prevents "address already in use" errors when benchmarks are run multiple times
	time.Sleep(500 * time.Millisecond)
}

// ============================================
// HTTP/1.1 Latency Benchmarks
// ============================================

// BenchmarkHTTP1Latency measures HTTP/1.1 latency baseline.
//
// Target: <5ms per request for local HTTP
func BenchmarkHTTP1Latency(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &EchoAgent{}
	endpoint, err := sm.StartServer(agent, "http", 9100)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("echo-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "test message")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := client.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkHTTP2Latency measures HTTP/2 latency.
//
// Target: <5ms per request for local HTTP/2
func BenchmarkHTTP2Latency(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &EchoAgent{}
	endpoint, err := sm.StartServer(agent, "h2c", 9101)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("echo-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "test message")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := client.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// ============================================
// Message Size Benchmarks
// ============================================

// BenchmarkHTTP1SmallMessage measures HTTP/1.1 with small messages (100B).
func BenchmarkHTTP1SmallMessage(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &EchoAgent{}
	endpoint, err := sm.StartServer(agent, "http", 9110)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("echo-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", strings.Repeat("x", 100))

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := client.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkHTTP2SmallMessage measures HTTP/2 with small messages (100B).
func BenchmarkHTTP2SmallMessage(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &EchoAgent{}
	endpoint, err := sm.StartServer(agent, "h2c", 9111)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("echo-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", strings.Repeat("x", 100))

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := client.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkHTTP1MediumMessage measures HTTP/1.1 with medium messages (10KB).
func BenchmarkHTTP1MediumMessage(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &EchoAgent{}
	endpoint, err := sm.StartServer(agent, "http", 9112)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("echo-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", strings.Repeat("x", 10000))

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := client.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkHTTP2MediumMessage measures HTTP/2 with medium messages (10KB).
func BenchmarkHTTP2MediumMessage(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &EchoAgent{}
	endpoint, err := sm.StartServer(agent, "h2c", 9113)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("echo-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", strings.Repeat("x", 10000))

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := client.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkHTTP1LargeMessage measures HTTP/1.1 with large messages (1MB).
func BenchmarkHTTP1LargeMessage(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &EchoAgent{}
	endpoint, err := sm.StartServer(agent, "http", 9114)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("echo-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", strings.Repeat("x", 1000000))

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := client.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkHTTP2LargeMessage measures HTTP/2 with large messages (1MB).
func BenchmarkHTTP2LargeMessage(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &EchoAgent{}
	endpoint, err := sm.StartServer(agent, "h2c", 9115)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("echo-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", strings.Repeat("x", 1000000))

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := client.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// ============================================
// Concurrent Load Benchmarks
// ============================================

// BenchmarkHTTP1Concurrent10 measures HTTP/1.1 with 10 concurrent requests.
func BenchmarkHTTP1Concurrent10(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &EchoAgent{}
	endpoint, err := sm.StartServer(agent, "http", 9120)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("echo-agent", trans, 30*time.Second)
	defer client.Close()

	msg := agenkit.NewMessage("user", "test message")

	b.ResetTimer()
	b.RunParallel(func(pb *testing.PB) {
		ctx := context.Background()
		for pb.Next() {
			_, err := client.Process(ctx, msg)
			if err != nil {
				b.Fatal(err)
			}
		}
	})
}

// BenchmarkHTTP2Concurrent10 measures HTTP/2 with 10 concurrent requests.
func BenchmarkHTTP2Concurrent10(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &EchoAgent{}
	endpoint, err := sm.StartServer(agent, "h2c", 9121)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("echo-agent", trans, 30*time.Second)
	defer client.Close()

	msg := agenkit.NewMessage("user", "test message")

	b.ResetTimer()
	b.RunParallel(func(pb *testing.PB) {
		ctx := context.Background()
		for pb.Next() {
			_, err := client.Process(ctx, msg)
			if err != nil {
				b.Fatal(err)
			}
		}
	})
}

// ============================================
// Realistic Workload Benchmarks
// ============================================

// BenchmarkHTTP1RealisticWorkload measures HTTP/1.1 with simulated agent processing (10ms).
func BenchmarkHTTP1RealisticWorkload(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &SlowAgent{delayMs: 10}
	endpoint, err := sm.StartServer(agent, "http", 9130)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("slow-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "process this")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := client.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkHTTP2RealisticWorkload measures HTTP/2 with simulated agent processing (10ms).
func BenchmarkHTTP2RealisticWorkload(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &SlowAgent{delayMs: 10}
	endpoint, err := sm.StartServer(agent, "h2c", 9131)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("slow-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "process this")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := client.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// ============================================
// Parallel Benchmarks for Maximum Throughput
// ============================================

// BenchmarkHTTP1Parallel measures HTTP/1.1 maximum throughput with parallel requests.
func BenchmarkHTTP1Parallel(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &EchoAgent{}
	endpoint, err := sm.StartServer(agent, "http", 9140)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("echo-agent", trans, 30*time.Second)
	defer client.Close()

	msg := agenkit.NewMessage("user", "test")

	b.ResetTimer()
	b.RunParallel(func(pb *testing.PB) {
		ctx := context.Background()
		for pb.Next() {
			_, err := client.Process(ctx, msg)
			if err != nil {
				b.Fatal(err)
			}
		}
	})
}

// BenchmarkHTTP2Parallel measures HTTP/2 maximum throughput with parallel requests.
func BenchmarkHTTP2Parallel(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &EchoAgent{}
	endpoint, err := sm.StartServer(agent, "h2c", 9141)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("echo-agent", trans, 30*time.Second)
	defer client.Close()

	msg := agenkit.NewMessage("user", "test")

	b.ResetTimer()
	b.RunParallel(func(pb *testing.PB) {
		ctx := context.Background()
		for pb.Next() {
			_, err := client.Process(ctx, msg)
			if err != nil {
				b.Fatal(err)
			}
		}
	})
}

// ============================================
// HTTP/3 over QUIC Benchmarks
// ============================================
//
// Note: HTTP/3 benchmarks use self-signed TLS certificates for local testing.
// The transport is configured with InsecureSkipVerify=true for benchmark purposes only.
// Production deployments should use proper CA-signed certificates.

// BenchmarkHTTP3Latency measures HTTP/3 over QUIC latency.
//
// Target: <5ms per request for local HTTP/3
func BenchmarkHTTP3Latency(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &EchoAgent{}
	endpoint, err := sm.StartServer(agent, "h3", 9200)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("echo-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "test message")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := client.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkHTTP3SmallMessage measures HTTP/3 with small messages (100B).
func BenchmarkHTTP3SmallMessage(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &EchoAgent{}
	endpoint, err := sm.StartServer(agent, "h3", 9201)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("echo-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", strings.Repeat("x", 100))

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := client.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkHTTP3MediumMessage measures HTTP/3 with medium messages (10KB).
func BenchmarkHTTP3MediumMessage(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &EchoAgent{}
	endpoint, err := sm.StartServer(agent, "h3", 9202)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("echo-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", strings.Repeat("x", 10000))

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := client.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkHTTP3LargeMessage measures HTTP/3 with large messages (1MB).
func BenchmarkHTTP3LargeMessage(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &EchoAgent{}
	endpoint, err := sm.StartServer(agent, "h3", 9203)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("echo-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", strings.Repeat("x", 1000000))

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := client.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkHTTP3Concurrent10 measures HTTP/3 with 10 concurrent requests.
func BenchmarkHTTP3Concurrent10(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &EchoAgent{}
	endpoint, err := sm.StartServer(agent, "h3", 9204)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("echo-agent", trans, 30*time.Second)
	defer client.Close()

	msg := agenkit.NewMessage("user", "test message")

	b.ResetTimer()
	b.RunParallel(func(pb *testing.PB) {
		ctx := context.Background()
		for pb.Next() {
			_, err := client.Process(ctx, msg)
			if err != nil {
				b.Fatal(err)
			}
		}
	})
}

// BenchmarkHTTP3RealisticWorkload measures HTTP/3 with simulated agent processing (10ms).
func BenchmarkHTTP3RealisticWorkload(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &SlowAgent{delayMs: 10}
	endpoint, err := sm.StartServer(agent, "h3", 9205)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("slow-agent", trans, 30*time.Second)
	defer client.Close()

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "process this")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := client.Process(ctx, msg)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkHTTP3Parallel measures HTTP/3 maximum throughput with parallel requests.
func BenchmarkHTTP3Parallel(b *testing.B) {
	sm := NewServerManager()
	defer sm.Shutdown()

	agent := &EchoAgent{}
	endpoint, err := sm.StartServer(agent, "h3", 9206)
	if err != nil {
		b.Fatal(err)
	}

	trans := transport.NewHTTPTransport(endpoint)
	client := remote.NewRemoteAgentWithTransport("echo-agent", trans, 30*time.Second)
	defer client.Close()

	msg := agenkit.NewMessage("user", "test")

	b.ResetTimer()
	b.RunParallel(func(pb *testing.PB) {
		ctx := context.Background()
		for pb.Next() {
			_, err := client.Process(ctx, msg)
			if err != nil {
				b.Fatal(err)
			}
		}
	})
}
