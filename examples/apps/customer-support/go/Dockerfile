# Build context is the REPOSITORY ROOT, not this directory — see the Go worker
# service in ../docker-compose.yml.
#
# go.mod has `replace github.com/scttfrdmn/agenkit/agenkit-go => ../../../../agenkit-go`
# because this is a monorepo. A context of ./go puts that target outside the
# context, so `go mod download` failed with
#   reading /agenkit-go/go.mod: no such file or directory
# no matter which Go version the builder used (#857).
#
# Must be >= the `go` directive in go.mod (1.25.12); this used to pin
# golang:1.21-alpine, which could not build the module at all.
FROM golang:1.25-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git

# Set working directory
WORKDIR /src

# Copy the replace target and this module's manifests, so dependency download stays
# cached independently of the source.
COPY agenkit-go/ ./agenkit-go/
COPY examples/apps/customer-support/go/go.mod examples/apps/customer-support/go/go.sum ./examples/apps/customer-support/go/
WORKDIR /src/examples/apps/customer-support/go

# Download dependencies
RUN go mod download

# Copy source code
COPY examples/apps/customer-support/go/ ./

# Build binary
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o /build/worker ./cmd/worker

# Install grpc_health_probe
RUN GRPC_HEALTH_PROBE_VERSION=v0.4.19 && \
    wget -qO/bin/grpc_health_probe \
    https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VERSION}/grpc_health_probe-linux-amd64 && \
    chmod +x /bin/grpc_health_probe

# Final stage
FROM alpine:latest

# Install runtime dependencies
RUN apk --no-cache add ca-certificates

WORKDIR /app

# Copy binary from builder
COPY --from=builder /build/worker .
COPY --from=builder /bin/grpc_health_probe /bin/grpc_health_probe

# Expose gRPC port
EXPOSE 50051

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD /bin/grpc_health_probe -addr=:50051 || exit 1

# Run worker
CMD ["./worker"]
