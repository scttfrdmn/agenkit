# ============================================================
# Agenkit Go Agent - Production Dockerfile
# ============================================================

# Must be >= the `go` directive in go.mod (1.25.14); 1.21/1.22 could not build
# these modules at all, so every one of these image builds failed at `go mod
# download` (#857).
FROM golang:1.25-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git ca-certificates tzdata

WORKDIR /build

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download && go mod verify

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags='-w -s -extldflags "-static"' \
    -a -installsuffix cgo \
    -o agenkit-agent \
    ./cmd/agent

# ============================================================
# Runtime Stage
# ============================================================

FROM scratch

# Copy timezone data
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo

# Copy SSL certificates
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Copy the binary
COPY --from=builder /build/agenkit-agent /agenkit-agent

# Create non-root user (numeric UID for scratch)
USER 65534:65534

# Health check (requires a health check sidecar or external monitoring)
# HEALTHCHECK cannot be used with scratch base image

# Expose ports
EXPOSE 8000 8002

# Run the application
ENTRYPOINT ["/agenkit-agent"]
