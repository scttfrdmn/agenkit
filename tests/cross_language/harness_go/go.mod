module github.com/scttfrdmn/agenkit/tests/cross_language/harness_go

go 1.26.8

replace github.com/scttfrdmn/agenkit/agenkit-go => ../../../agenkit-go

require github.com/scttfrdmn/agenkit/agenkit-go v0.0.0-00010101000000-000000000000

require (
	github.com/google/uuid v1.6.0 // indirect
	gonum.org/v1/gonum v0.17.0 // indirect
)
