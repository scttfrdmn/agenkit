package observability

import (
	"context"

	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/trace"
)

// NodeOptions carries the attributes attached to a tree-node span started by
// StartNode. Fields left at their zero value are treated as "not
// applicable" for that node rather than an explicit zero: Depth 0 is a real
// value (the root), but BaseCaseReason == "" and Gap == "" mean the
// attribute is omitted entirely, keeping "absent" distinguishable from "set
// to the empty string" on the emitted span.
type NodeOptions struct {
	// SpanName overrides the default span name ("agenkit.node.process").
	// Node identity belongs in the NodeID attribute, not the span name — a
	// span name that varies per node id would defeat low-cardinality
	// grouping in most trace backends.
	SpanName string

	// ParentID is the parent node's id. Redundant with span parentage on
	// purpose: it survives sampling that drops the parent span. Leave empty
	// for the root node, which has no parent.
	ParentID string

	// Depth is 0 at the root.
	Depth int

	// State is the node's lifecycle state.
	State string

	// BaseCaseReason explains why recursion stopped at this node. Leave
	// empty for a non-terminal node.
	BaseCaseReason string

	// Gap explains why this node produced no usable result (e.g. truncated,
	// unreturnable). A non-empty Gap also sets the span status to Error —
	// unlike a failed verification, which stays Ok. Leave empty when the
	// node produced a usable result.
	Gap string
}

// StartNode starts a span for a single node in a tree-shaped workload
// (decomposition, map-reduce, multi-agent fan-out). The rule this follows:
// the span tree *is* the workload tree — one span per node, parented to its
// parent node's span, never flattened into siblings and reconstructed from
// attributes.
//
// The span is started live: when the node starts, while the parent's span
// context is already in hand. StartNode never buffers nodes and builds the
// tree after the run — a reconstructed span can carry no real duration, only
// a fabricated or absent one, and a consumer cannot tell an invented
// duration from a measured one. Buffering trades that away for convenience
// when a workload's completion order is inverted (a child finishes before
// its parent), which is exactly the case the parentSpanCtx parameter exists
// to solve without buffering.
//
// parentSpanCtx is taken explicitly rather than derived from ctx, so a
// caller whose node-completion order is inverted can still produce correct
// span parentage: each call carries its own parent's SpanContext forward,
// independent of call order, instead of relying on an ambient "current
// span" in ctx that may belong to the wrong node by the time this runs. Pass
// trace.SpanContext{} (the zero value) for the root node, which has no
// parent.
//
// The caller must end the returned span exactly once (span.End()) — the
// same obligation as any span returned by Tracer.Start.
func StartNode(ctx context.Context, parentSpanCtx trace.SpanContext, nodeID string, opts NodeOptions) (context.Context, trace.Span) {
	spanName := opts.SpanName
	if spanName == "" {
		spanName = "agenkit.node.process"
	}

	parentCtx := ctx
	if parentSpanCtx.IsValid() {
		parentCtx = trace.ContextWithSpanContext(ctx, parentSpanCtx)
	}

	tracer := GetTracer("agenkit.observability")
	childCtx, span := tracer.Start(parentCtx, spanName, trace.WithSpanKind(trace.SpanKindInternal))

	attrs := []attribute.KeyValue{
		attribute.String("agenkit.node.id", nodeID),
		attribute.Int("agenkit.node.depth", opts.Depth),
		attribute.String("agenkit.node.state", opts.State),
	}
	if opts.ParentID != "" {
		attrs = append(attrs, attribute.String("agenkit.node.parent_id", opts.ParentID))
	}
	if opts.BaseCaseReason != "" {
		attrs = append(attrs, attribute.String("agenkit.node.base_case_reason", opts.BaseCaseReason))
	}
	if opts.Gap != "" {
		attrs = append(attrs, attribute.String("agenkit.node.gap", opts.Gap))
	}
	span.SetAttributes(attrs...)

	if opts.Gap != "" {
		// A gap means the node produced no usable result — nothing
		// completed successfully — which is what OTel's Error status
		// means. This differs from a failed verification (which stays Ok):
		// a verifier that ran and returned "failed" did its job correctly.
		span.SetStatus(codes.Error, opts.Gap)
	}

	return childCtx, span
}
