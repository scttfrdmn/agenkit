// Standalone module so this example is actually compiled by something. It was in
// no module at all, so `go build ./...` never saw it and it had rotted into
// importing a package that does not exist (#857).
module github.com/scttfrdmn/agenkit/examples/infrastructure-go

go 1.25.12

require github.com/scttfrdmn/agenkit/agenkit-go v0.0.0

// Build against the in-repo agenkit-go (monorepo); not a separately published module.
replace github.com/scttfrdmn/agenkit/agenkit-go => ../../../agenkit-go
