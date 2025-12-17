FROM golang:1.21-alpine AS builder
WORKDIR /build
RUN apk add --no-cache git
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o scraper ./cmd/worker
RUN wget -qO/bin/grpc_health_probe https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/v0.4.19/grpc_health_probe-linux-amd64 && chmod +x /bin/grpc_health_probe

FROM alpine:latest
WORKDIR /app
RUN apk --no-cache add ca-certificates
COPY --from=builder /build/scraper .
COPY --from=builder /bin/grpc_health_probe /bin/
EXPOSE 50051
HEALTHCHECK CMD /bin/grpc_health_probe -addr=:50051 || exit 1
CMD ["./scraper"]
