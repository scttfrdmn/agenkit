# Build context is the REPOSITORY ROOT, not this directory — see the
# `go-scraper` service in ../docker-compose.yml.
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

WORKDIR /src
RUN apk add --no-cache git

# Copy the replace target and this module's manifests, so dependency download is
# still cached independently of the source.
COPY agenkit-go/ ./agenkit-go/
COPY examples/apps/research-assistant/go/go.mod examples/apps/research-assistant/go/go.sum ./examples/apps/research-assistant/go/
WORKDIR /src/examples/apps/research-assistant/go
RUN go mod download

COPY examples/apps/research-assistant/go/ ./
RUN CGO_ENABLED=0 go build -o /build/scraper ./cmd/worker

RUN wget -qO/bin/grpc_health_probe https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/v0.4.19/grpc_health_probe-linux-amd64 && chmod +x /bin/grpc_health_probe

FROM alpine:latest
WORKDIR /app
RUN apk --no-cache add ca-certificates
COPY --from=builder /build/scraper .
COPY --from=builder /bin/grpc_health_probe /bin/
EXPOSE 50051
HEALTHCHECK CMD /bin/grpc_health_probe -addr=:50051 || exit 1
CMD ["./scraper"]
