# Go Agenkit Base Image
# Multi-stage build for minimal production image

# Build stage
FROM golang:1.21-alpine AS builder

LABEL org.opencontainers.image.title="Agenkit Go Builder"
LABEL org.opencontainers.image.description="Foundation layer for AI agents - Go build environment"

WORKDIR /build

# Install build dependencies
RUN apk add --no-cache git make

# Copy Go module files
COPY agenkit-go/go.mod agenkit-go/go.sum ./
RUN go mod download

# Copy Go source
COPY agenkit-go/ .

# Build a sample binary (users will override this in their own Dockerfiles)
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-w -s" -o /app/agenkit-example ./examples/basic/main.go || \
    echo "package main\n\nfunc main() {}" > /tmp/dummy.go && \
    CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-w -s" -o /app/agenkit-go /tmp/dummy.go

# Runtime stage
FROM alpine:3.19

LABEL org.opencontainers.image.title="Agenkit Go"
LABEL org.opencontainers.image.description="Foundation layer for AI agents - Go runtime"
LABEL org.opencontainers.image.authors="Scott Friedman <scttfrdmn@users.noreply.github.com>"
LABEL org.opencontainers.image.source="https://github.com/agenkit/agenkit"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache ca-certificates tzdata && \
    adduser -D -u 1000 agenkit

# Copy binary from builder
COPY --from=builder /app/agenkit-* /app/

# Switch to non-root user
USER agenkit

# Default command
CMD ["/app/agenkit-go"]
