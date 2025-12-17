FROM golang:1.21-alpine AS builder

WORKDIR /build

RUN apk add --no-cache git

# Copy go.mod and go.sum
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build
RUN CGO_ENABLED=0 go build -o analyzer ./cmd/worker

# Download health probe
RUN wget -qO/bin/grpc_health_probe https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/v0.4.19/grpc_health_probe-linux-amd64 && \
    chmod +x /bin/grpc_health_probe

FROM alpine:latest

WORKDIR /app

RUN apk --no-cache add ca-certificates

COPY --from=builder /build/analyzer .
COPY --from=builder /bin/grpc_health_probe /bin/

EXPOSE 50051

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD /bin/grpc_health_probe -addr=:50051 || exit 1

CMD ["./analyzer"]
