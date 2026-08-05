// Server lifecycle tests for #844: cancelling the context passed to Start must
// shut the server down.
//
// These exist because nothing tested it. HTTPAgent.Start has accepted a
// context.Context since it was written and never read it — renaming the parameter
// to `_` compiled cleanly — so a caller could cancel their context and keep
// serving indefinitely while believing they had shut down. GRPCServer.Start took
// no context at all, so the same shutdown code was correct for one server and
// silently insufficient for the other.
//
// A signature that promises cancellation and doesn't deliver is worse than one
// that never promised it, so each test here asserts the promise is kept: after
// cancel(), the server must stop answering.
package adapter_test

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"testing"
	"time"

	agkgrpc "github.com/scttfrdmn/agenkit/agenkit-go/adapter/grpc"
	agkhttp "github.com/scttfrdmn/agenkit/agenkit-go/adapter/http"
	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/remote"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// freePort binds :0, reads back the assigned port and releases it. Hardcoded
// ports collide on the self-hosted runners (6 parallel runners share a host).
// HTTPAgent takes an address rather than a listener, so unlike the gRPC tests it
// cannot hold the listener open — a race is possible in principle but the window
// is microseconds and the alternative is changing the constructor.
func freePort(t *testing.T) int {
	t.Helper()
	l, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	port := l.Addr().(*net.TCPAddr).Port
	if err := l.Close(); err != nil {
		t.Fatal(err)
	}
	return port
}

// waitUntil polls cond until it holds or the deadline passes. Shutdown is
// asynchronous — Start's context watcher runs in its own goroutine — so the
// assertion has to tolerate latency without a fixed sleep that is either flaky
// or slow.
func waitUntil(cond func() bool, timeout time.Duration) bool {
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		if cond() {
			return true
		}
		time.Sleep(10 * time.Millisecond)
	}
	return cond()
}

func TestHTTPAgentStartHonoursContextCancellation(t *testing.T) {
	addr := fmt.Sprintf("127.0.0.1:%d", freePort(t))
	server := agkhttp.NewHTTPAgent(&EchoAgent{}, addr)

	ctx, cancel := context.WithCancel(context.Background())
	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	// Stop() is idempotent, so this is safe even though cancel() below also stops
	// the server. It also guarantees cleanup if an assertion fails early.
	defer func() { _ = server.Stop() }()

	healthURL := fmt.Sprintf("http://%s/health", addr)
	client := &http.Client{Timeout: 500 * time.Millisecond}

	serving := func() bool {
		resp, err := client.Get(healthURL)
		if err != nil {
			return false
		}
		_ = resp.Body.Close()
		return true
	}

	if !waitUntil(serving, 3*time.Second) {
		t.Fatal("server never became reachable")
	}

	cancel()

	// The negative assertion is the point of the test: before #844 the server kept
	// answering here forever, because Start ignored ctx entirely.
	if !waitUntil(func() bool { return !serving() }, 5*time.Second) {
		t.Fatal("server still serving after its context was cancelled — Start is ignoring ctx (#844)")
	}
}

func TestGRPCServerStartHonoursContextCancellation(t *testing.T) {
	server, err := agkgrpc.NewGRPCServer(&EchoAgent{}, "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	endpoint := fmt.Sprintf("grpc://%s", server.Address())

	ctx, cancel := context.WithCancel(context.Background())
	if err := server.Start(ctx); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = server.Stop() }()

	message := agenkit.NewMessage("user", "Hello")

	// Reachability is probed with a fresh client each time: RemoteAgent caches its
	// connection, so a client created while the server was up would report success
	// from a stale connection rather than the server's current state.
	serving := func() bool {
		client, err := remote.NewRemoteAgent("echo", endpoint, 500*time.Millisecond)
		if err != nil {
			return false
		}
		defer func() { _ = client.Close() }()
		_, err = client.Process(context.Background(), message)
		return err == nil
	}

	if !waitUntil(serving, 3*time.Second) {
		t.Fatal("server never became reachable")
	}

	cancel()

	if !waitUntil(func() bool { return !serving() }, 5*time.Second) {
		t.Fatal("server still serving after its context was cancelled — Start is ignoring ctx (#844)")
	}
}

// TestServerStopIsIdempotent guards the mechanism that makes ctx cancellation
// safe to combine with an explicit `defer Stop()`. Both servers close a channel
// to release Start's context watcher, and closing a closed channel panics, so
// without the sync.Once guard the ordinary Start(ctx)/defer Stop()/cancel()
// pattern would crash the process.
func TestServerStopIsIdempotent(t *testing.T) {
	t.Run("http", func(t *testing.T) {
		addr := fmt.Sprintf("127.0.0.1:%d", freePort(t))
		server := agkhttp.NewHTTPAgent(&EchoAgent{}, addr)
		if err := server.Start(context.Background()); err != nil {
			t.Fatal(err)
		}
		for i := 0; i < 3; i++ {
			if err := server.Stop(); err != nil {
				t.Fatalf("Stop call %d: %v", i+1, err)
			}
		}
	})

	t.Run("grpc", func(t *testing.T) {
		server, err := agkgrpc.NewGRPCServer(&EchoAgent{}, "127.0.0.1:0")
		if err != nil {
			t.Fatal(err)
		}
		if err := server.Start(context.Background()); err != nil {
			t.Fatal(err)
		}
		for i := 0; i < 3; i++ {
			if err := server.Stop(); err != nil {
				t.Fatalf("Stop call %d: %v", i+1, err)
			}
		}
	})
}

// TestServerStopThenCancelDoesNotPanic covers the reverse order: the server is
// stopped explicitly first, then the context is cancelled. The watcher goroutine
// is still selecting at that moment, and if it took the ctx.Done() branch and
// called a Stop that closed the channel unconditionally, the panic would land on
// a background goroutine — unrecoverable, and attributed to whichever test was
// running at the time.
func TestServerStopThenCancelDoesNotPanic(t *testing.T) {
	t.Run("http", func(t *testing.T) {
		addr := fmt.Sprintf("127.0.0.1:%d", freePort(t))
		server := agkhttp.NewHTTPAgent(&EchoAgent{}, addr)
		ctx, cancel := context.WithCancel(context.Background())
		if err := server.Start(ctx); err != nil {
			t.Fatal(err)
		}
		if err := server.Stop(); err != nil {
			t.Fatal(err)
		}
		cancel()
		time.Sleep(200 * time.Millisecond) // let the watcher goroutine run out
	})

	t.Run("grpc", func(t *testing.T) {
		server, err := agkgrpc.NewGRPCServer(&EchoAgent{}, "127.0.0.1:0")
		if err != nil {
			t.Fatal(err)
		}
		ctx, cancel := context.WithCancel(context.Background())
		if err := server.Start(ctx); err != nil {
			t.Fatal(err)
		}
		if err := server.Stop(); err != nil {
			t.Fatal(err)
		}
		cancel()
		time.Sleep(200 * time.Millisecond)
	})
}
