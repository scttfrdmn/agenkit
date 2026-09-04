module github.com/scttfrdmn/agenkit/examples/customer-support-worker

go 1.25.14

require github.com/scttfrdmn/agenkit/agenkit-go v0.0.0

require (
	github.com/cespare/xxhash/v2 v2.3.0 // indirect
	github.com/google/uuid v1.6.0 // indirect
	github.com/redis/go-redis/v9 v9.22.0 // indirect
	go.uber.org/atomic v1.11.0 // indirect
	golang.org/x/net v0.58.0 // indirect
	golang.org/x/sys v0.47.0 // indirect
	golang.org/x/text v0.41.0 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20260819154853-08b0e4226688 // indirect
	google.golang.org/grpc v1.83.2 // indirect
	google.golang.org/protobuf v1.36.12 // indirect
)

// Build against the in-repo agenkit-go (monorepo); not a separately published module.
replace github.com/scttfrdmn/agenkit/agenkit-go => ../../../../agenkit-go
