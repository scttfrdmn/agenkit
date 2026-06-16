module github.com/scttfrdmn/agenkit/examples/customer-support-worker

go 1.25.0

require github.com/scttfrdmn/agenkit/agenkit-go v0.0.0

require (
	github.com/cespare/xxhash/v2 v2.3.0 // indirect
	github.com/dgryski/go-rendezvous v0.0.0-20200823014737-9f7001d12a5f // indirect
	github.com/google/uuid v1.6.0 // indirect
	github.com/redis/go-redis/v9 v9.16.0 // indirect
	golang.org/x/net v0.55.0 // indirect
	golang.org/x/sys v0.45.0 // indirect
	golang.org/x/text v0.37.0 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20260120221211-b8f7ae30c516 // indirect
	google.golang.org/grpc v1.80.0 // indirect
	google.golang.org/protobuf v1.36.11 // indirect
)

// Build against the in-repo agenkit-go (monorepo); not a separately published module.
replace github.com/scttfrdmn/agenkit/agenkit-go => ../../../../agenkit-go
