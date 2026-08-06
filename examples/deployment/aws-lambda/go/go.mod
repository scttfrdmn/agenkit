// Standalone module: this tree ships a Makefile, template.yaml and a 10 KB README
// but had no go.mod, so the `make build` documented in
// docs/deployment/AWS_LAMBDA.md failed on its first step (#857).
module github.com/scttfrdmn/agenkit/examples/aws-lambda-go

go 1.25.12

require (
	github.com/aws/aws-lambda-go v1.54.0
	github.com/aws/aws-xray-sdk-go v1.8.5
	github.com/scttfrdmn/agenkit/agenkit-go v0.0.0
)

require (
	github.com/andybalholm/brotli v1.1.0 // indirect
	github.com/aws/aws-sdk-go v1.47.9 // indirect
	github.com/google/uuid v1.6.0 // indirect
	github.com/jmespath/go-jmespath v0.4.0 // indirect
	github.com/klauspost/compress v1.17.6 // indirect
	github.com/pkg/errors v0.9.1 // indirect
	github.com/valyala/bytebufferpool v1.0.0 // indirect
	github.com/valyala/fasthttp v1.52.0 // indirect
	golang.org/x/net v0.57.0 // indirect
	golang.org/x/sys v0.47.0 // indirect
	golang.org/x/text v0.40.0 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20260724162435-b2f20204f0df // indirect
	google.golang.org/grpc v1.82.1 // indirect
	google.golang.org/protobuf v1.36.11 // indirect
)

// Build against the in-repo agenkit-go (monorepo); not a separately published module.
replace github.com/scttfrdmn/agenkit/agenkit-go => ../../../../agenkit-go
