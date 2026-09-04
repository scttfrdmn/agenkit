# Go Agenkit Base Image
# Multi-stage build for minimal production image

# Build stage
# Must be >= the `go` directive in agenkit-go/go.mod (1.26.8). This was pinned to
# 1.21-alpine, so `go mod download` failed outright with
# `go.mod requires go >= 1.25.12 (running go 1.21.13; GOTOOLCHAIN=local)` — the
# image had not built since the toolchain moved (#856). Keep this in step with the
# `go-version:` pins in .github/workflows/.
FROM golang:1.26.8-alpine AS builder

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

# Build a sample binary (users will override this in their own Dockerfiles).
#
# This was `A || B && C`, which sh parses left-associative as `(A || B) && C`, so C
# ran on *every* path: when A succeeded, B was skipped and C still tried to compile
# a /tmp/dummy.go that was never written. The fallback also produced the only binary
# CMD referenced (/app/agenkit-go), so a successful build yielded an image whose
# entrypoint did not exist. No fallback now — if the example stops compiling the
# build must fail loudly rather than silently ship a dummy (#856).
#
# examples/basic/main.go carries `//go:build ignore`, so it is named directly here
# rather than reached via ./... — gofmt and `go build <file>` see it, `go build ./...`
# does not (#843/#848).
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-w -s" \
    -o /app/agenkit-go ./examples/basic/main.go

# Runtime stage
FROM alpine:3.19

# Taken from the root VERSION file at build time rather than hardcoded. The label
# read "0.1.0" for 86 releases; a literal here would be a 20th version declaration
# for #842's guard to police, so pass it instead:
#   docker build --build-arg VERSION="$(cat VERSION)" -f docker/agenkit-go.Dockerfile .
ARG VERSION=dev

LABEL org.opencontainers.image.title="Agenkit Go"
LABEL org.opencontainers.image.description="Foundation layer for AI agents - Go runtime"
LABEL org.opencontainers.image.authors="Scott Friedman <scttfrdmn@users.noreply.github.com>"
LABEL org.opencontainers.image.source="https://github.com/scttfrdmn/agenkit"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache ca-certificates tzdata && \
    adduser -D -u 1000 agenkit

# Copy binary from builder
COPY --from=builder /app/agenkit-go /app/

# Switch to non-root user
USER agenkit

# Default command
CMD ["/app/agenkit-go"]
