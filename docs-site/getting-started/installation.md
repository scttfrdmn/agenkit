# Installation

## Python Installation {#python}

### Using pip

The easiest way to install Agenkit is via pip:

```bash
pip install agenkit
```

### From Source

For development or to get the latest changes:

```bash
# Clone the repository
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

### Verify Installation

```python
import agenkit
print(agenkit.__version__)
```

---

## Go Installation {#go}

### Using go get

```bash
go get github.com/agenkit/agenkit-go
```

### From Source

```bash
# Clone the repository
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit/agenkit-go

# Download dependencies
go mod download

# Run tests to verify
go test ./...
```

### Verify Installation

```go
package main

import (
    "fmt"
    "github.com/agenkit/agenkit-go/agenkit"
)

func main() {
    fmt.Println("Agenkit for Go installed successfully!")
}
```

---

## Docker Installation

Pull the official Docker images:

=== "Python Image"

    ```bash
    docker pull agenkit/python:1.0.0
    ```

=== "Go Image"

    ```bash
    docker pull agenkit/go:1.0.0
    ```

=== "Docker Compose"

    ```bash
    # Clone repository
    git clone https://github.com/scttfrdmn/agenkit.git
    cd agenkit

    # Start full stack
    docker-compose up -d
    ```

---

## Optional Dependencies

### For Observability

=== "Python"

    ```bash
    # Install OpenTelemetry dependencies
    pip install opentelemetry-api opentelemetry-sdk
    pip install opentelemetry-exporter-otlp
    pip install prometheus-client
    ```

=== "Go"

    ```bash
    # Already included in go.mod
    go get go.opentelemetry.io/otel
    go get github.com/prometheus/client_golang
    ```

### For gRPC Transport

=== "Python"

    ```bash
    pip install grpcio grpcio-tools
    ```

=== "Go"

    ```bash
    go get google.golang.org/grpc
    ```

### For HTTP/3 Support

=== "Python"

    ```bash
    pip install aioquic
    ```

=== "Go"

    ```bash
    go get github.com/quic-go/quic-go
    ```

---

## Development Dependencies

For contributing or running tests:

=== "Python"

    ```bash
    # Install development dependencies
    pip install -e ".[dev]"

    # This includes:
    # - pytest (testing)
    # - mypy (type checking)
    # - black (formatting)
    # - ruff (linting)
    # - hypothesis (property-based testing)
    ```

=== "Go"

    ```bash
    # Install golangci-lint
    go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

    # Run tests
    go test ./...

    # Run linter
    golangci-lint run
    ```

---

## Next Steps

Now that you have Agenkit installed, proceed to the [Quick Start](quick-start.md) guide to build your first agent!
