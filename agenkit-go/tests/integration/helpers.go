package integration

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"os/exec"
	"time"
)

// FindFreePort finds an available port on localhost.
func FindFreePort() (int, error) {
	listener, err := net.Listen("tcp", "localhost:0")
	if err != nil {
		return 0, err
	}
	defer listener.Close()

	addr := listener.Addr().(*net.TCPAddr)
	return addr.Port, nil
}

// WaitForServer waits for a server to become available.
func WaitForServer(url string, timeout time.Duration) error {
	client := &http.Client{
		Timeout: 1 * time.Second,
	}
	defer client.CloseIdleConnections()

	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		resp, err := client.Get(url)
		if err == nil {
			resp.Body.Close()
			if resp.StatusCode < 500 {
				return nil
			}
		}
		time.Sleep(100 * time.Millisecond)
	}

	return fmt.Errorf("server at %s did not become available within %v", url, timeout)
}

// PythonHTTPServer represents a running Python HTTP server.
type PythonHTTPServer struct {
	Port    int
	Cmd     *exec.Cmd
	BaseURL string
}

// StartPythonHTTPServer starts a Python HTTP server for testing.
func StartPythonHTTPServer(port int) (*PythonHTTPServer, error) {
	if port == 0 {
		var err error
		port, err = FindFreePort()
		if err != nil {
			return nil, fmt.Errorf("failed to find free port: %w", err)
		}
	}

	// Start Python server using the test server script
	// This assumes we have a Python test server script
	cmd := exec.Command(
		"python",
		"-m",
		"tests.integration.test_server",
		fmt.Sprintf("%d", port),
	)
	cmd.Dir = "../../.." // Go to root of project

	if err := cmd.Start(); err != nil {
		return nil, fmt.Errorf("failed to start Python server: %w", err)
	}

	server := &PythonHTTPServer{
		Port:    port,
		Cmd:     cmd,
		BaseURL: fmt.Sprintf("http://localhost:%d", port),
	}

	// Wait for server to be ready
	healthURL := fmt.Sprintf("%s/health", server.BaseURL)
	if err := WaitForServer(healthURL, 10*time.Second); err != nil {
		server.Stop()
		return nil, fmt.Errorf("Python server failed to start: %w", err)
	}

	return server, nil
}

// Stop stops the Python HTTP server.
func (s *PythonHTTPServer) Stop() error {
	if s.Cmd != nil && s.Cmd.Process != nil {
		if err := s.Cmd.Process.Kill(); err != nil {
			return fmt.Errorf("failed to kill Python server: %w", err)
		}
		s.Cmd.Wait() // Wait for process to exit
	}
	return nil
}

// GoHTTPServer represents a running Go HTTP server.
type GoHTTPServer struct {
	Port    int
	Server  *http.Server
	BaseURL string
	Done    chan error
}

// StartGoHTTPServer starts a Go HTTP server for testing.
func StartGoHTTPServer(port int) (*GoHTTPServer, error) {
	if port == 0 {
		var err error
		port, err = FindFreePort()
		if err != nil {
			return nil, fmt.Errorf("failed to find free port: %w", err)
		}
	}

	// Create a simple test server
	mux := http.NewServeMux()

	// Health check endpoint
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	// Test endpoint
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok","language":"go"}`))
	})

	server := &http.Server{
		Addr:    fmt.Sprintf("localhost:%d", port),
		Handler: mux,
	}

	goServer := &GoHTTPServer{
		Port:    port,
		Server:  server,
		BaseURL: fmt.Sprintf("http://localhost:%d", port),
		Done:    make(chan error, 1),
	}

	// Start server in background
	go func() {
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			goServer.Done <- err
		}
		close(goServer.Done)
	}()

	// Wait for server to be ready
	healthURL := fmt.Sprintf("%s/health", goServer.BaseURL)
	if err := WaitForServer(healthURL, 10*time.Second); err != nil {
		goServer.Stop(context.Background())
		return nil, fmt.Errorf("Go server failed to start: %w", err)
	}

	return goServer, nil
}

// Stop stops the Go HTTP server.
func (s *GoHTTPServer) Stop(ctx context.Context) error {
	if s.Server != nil {
		return s.Server.Shutdown(ctx)
	}
	return nil
}

// IsPortInUse checks if a port is already in use.
func IsPortInUse(port int) bool {
	listener, err := net.Listen("tcp", fmt.Sprintf("localhost:%d", port))
	if err != nil {
		return true
	}
	listener.Close()
	return false
}
