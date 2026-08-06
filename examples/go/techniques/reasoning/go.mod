// Standalone module: this example was in no Go module, so nothing compiled it (#857).
module github.com/scttfrdmn/agenkit/examples/go-techniques-reasoning

go 1.25.12

require github.com/scttfrdmn/agenkit/agenkit-go v0.0.0

require (
	github.com/cespare/xxhash/v2 v2.3.0 // indirect
	github.com/google/uuid v1.6.0 // indirect
	github.com/redis/go-redis/v9 v9.21.0 // indirect
	go.uber.org/atomic v1.11.0 // indirect
)

// Build against the in-repo agenkit-go (monorepo); not a separately published module.
replace github.com/scttfrdmn/agenkit/agenkit-go => ../../../../agenkit-go
