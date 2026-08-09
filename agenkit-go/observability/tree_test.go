package observability

import (
	"context"
	"testing"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/codes"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/sdk/trace/tracetest"
	"go.opentelemetry.io/otel/trace"
)

// TestStartNodeThreeLevelTreeParentageAndDuration is the issue's own "Done
// when" criterion for #784: a 3-level tree produces 3 spans with correct
// parentage AND non-zero measured durations. The duration assertion is what
// pins the live design against a future post-hoc/buffered regression — only
// a span started while the node is actually running (not reconstructed
// afterward from buffered records) can have a real elapsed time between
// StartNode and span.End(). A naive buffered implementation that fabricates
// or omits timestamps would produce zero (or identical, or unset) durations
// here, which is exactly what this test would catch.
func TestStartNodeThreeLevelTreeParentageAndDuration(t *testing.T) {
	exporter := tracetest.NewInMemoryExporter()
	provider := sdktrace.NewTracerProvider(
		sdktrace.WithSpanProcessor(sdktrace.NewSimpleSpanProcessor(exporter)),
	)
	prevProvider := otel.GetTracerProvider()
	otel.SetTracerProvider(provider)
	defer func() {
		otel.SetTracerProvider(prevProvider)
		_ = provider.Shutdown(context.Background())
	}()

	ctx := context.Background()

	// Root node (depth 0), no parent.
	rootCtx, rootSpan := StartNode(ctx, trace.SpanContext{}, "root", NodeOptions{
		Depth: 0,
		State: "running",
	})
	rootSpanCtx := rootSpan.SpanContext()
	time.Sleep(5 * time.Millisecond)
	rootSpan.End()

	// Child node (depth 1), parented explicitly to root's span context —
	// not derived from rootCtx, to exercise the "parent taken explicitly"
	// contract that lets inverted completion order still work.
	childCtx, childSpan := StartNode(ctx, rootSpanCtx, "child", NodeOptions{
		ParentID: "root",
		Depth:    1,
		State:    "running",
	})
	childSpanCtx := childSpan.SpanContext()
	time.Sleep(5 * time.Millisecond)
	childSpan.End()

	// Grandchild node (depth 2), parented to child. Also exercises the Gap
	// attribute + Error status path.
	_, grandchildSpan := StartNode(ctx, childSpanCtx, "grandchild", NodeOptions{
		ParentID: "child",
		Depth:    2,
		State:    "terminal",
		Gap:      "unreturnable: truncated by depth limit",
	})
	time.Sleep(5 * time.Millisecond)
	grandchildSpan.End()

	_ = rootCtx
	_ = childCtx

	if err := provider.ForceFlush(context.Background()); err != nil {
		t.Fatalf("force flush failed: %v", err)
	}

	spans := exporter.GetSpans()
	if len(spans) != 3 {
		t.Fatalf("expected 3 spans, got %d", len(spans))
	}

	byNodeID := make(map[string]tracetest.SpanStub)
	for _, s := range spans {
		for _, attr := range s.Attributes {
			if string(attr.Key) == "agenkit.node.id" {
				byNodeID[attr.Value.AsString()] = s
			}
		}
	}

	root, ok := byNodeID["root"]
	if !ok {
		t.Fatal("no span found for node 'root'")
	}
	child, ok := byNodeID["child"]
	if !ok {
		t.Fatal("no span found for node 'child'")
	}
	grandchild, ok := byNodeID["grandchild"]
	if !ok {
		t.Fatal("no span found for node 'grandchild'")
	}

	// Correct parentage: span parent/child linkage, not just an attribute.
	if child.Parent.SpanID() != root.SpanContext.SpanID() {
		t.Errorf("child span parent = %s, want root span id %s", child.Parent.SpanID(), root.SpanContext.SpanID())
	}
	if grandchild.Parent.SpanID() != child.SpanContext.SpanID() {
		t.Errorf("grandchild span parent = %s, want child span id %s", grandchild.Parent.SpanID(), child.SpanContext.SpanID())
	}
	// All three share one trace.
	if root.SpanContext.TraceID() != child.SpanContext.TraceID() || child.SpanContext.TraceID() != grandchild.SpanContext.TraceID() {
		t.Error("expected all three spans to share one trace ID")
	}

	// Non-zero *measured* durations: each node sleeps 5ms between StartNode
	// and span.End(), so a live implementation must report a duration close
	// to that. This threshold (not just ">0") is deliberate: a naive
	// implementation that calls span.End() immediately inside StartNode
	// (e.g. to fabricate a span post-hoc without holding it open across the
	// node's real work) still produces a technically-positive duration of a
	// few microseconds from clock-read overhead alone — ">0" alone would not
	// catch that bug. Requiring the measured duration to be within the same
	// order of magnitude as the real 5ms of work is what pins the live
	// design against that regression.
	const minExpectedDuration = 3 * time.Millisecond
	for name, s := range map[string]tracetest.SpanStub{"root": root, "child": child, "grandchild": grandchild} {
		d := s.EndTime.Sub(s.StartTime)
		if d < minExpectedDuration {
			t.Errorf("span %s duration = %v, want >= %v (the node's real work); a buffered/post-hoc implementation that ends the span immediately would fail this", name, d, minExpectedDuration)
		}
	}

	// agenkit.node.parent_id attribute set on child/grandchild, absent on root.
	assertAttr := func(s tracetest.SpanStub, key, want string) {
		for _, attr := range s.Attributes {
			if string(attr.Key) == key {
				if attr.Value.AsString() != want {
					t.Errorf("span attribute %s = %q, want %q", key, attr.Value.AsString(), want)
				}
				return
			}
		}
		t.Errorf("span missing attribute %s", key)
	}
	assertAttr(child, "agenkit.node.parent_id", "root")
	assertAttr(grandchild, "agenkit.node.parent_id", "child")
	for _, attr := range root.Attributes {
		if string(attr.Key) == "agenkit.node.parent_id" {
			t.Error("root span should not have agenkit.node.parent_id")
		}
	}

	// depth attributes
	assertIntAttr := func(s tracetest.SpanStub, key string, want int64) {
		for _, attr := range s.Attributes {
			if string(attr.Key) == key {
				if attr.Value.AsInt64() != want {
					t.Errorf("span attribute %s = %d, want %d", key, attr.Value.AsInt64(), want)
				}
				return
			}
		}
		t.Errorf("span missing attribute %s", key)
	}
	assertIntAttr(root, "agenkit.node.depth", 0)
	assertIntAttr(child, "agenkit.node.depth", 1)
	assertIntAttr(grandchild, "agenkit.node.depth", 2)

	// base_case_reason absent on non-terminal nodes.
	for _, attr := range root.Attributes {
		if string(attr.Key) == "agenkit.node.base_case_reason" {
			t.Error("root span should not have agenkit.node.base_case_reason (non-terminal)")
		}
	}

	// Gap sets Error status; nodes without a gap stay Ok/Unset (not Error).
	if grandchild.Status.Code != codes.Error {
		t.Errorf("grandchild span status = %v, want Error (has gap)", grandchild.Status.Code)
	}
	if root.Status.Code == codes.Error {
		t.Error("root span status should not be Error (no gap)")
	}
	if child.Status.Code == codes.Error {
		t.Error("child span status should not be Error (no gap)")
	}
}

// TestStartNodeSurfaceToVolumeNotEmitted confirms the deliberate omission
// from #784: surface_to_volume must never appear on a node span, since it is
// derivable from other attributes and a stored derived value can disagree
// with its inputs later.
func TestStartNodeSurfaceToVolumeNotEmitted(t *testing.T) {
	exporter := tracetest.NewInMemoryExporter()
	provider := sdktrace.NewTracerProvider(
		sdktrace.WithSpanProcessor(sdktrace.NewSimpleSpanProcessor(exporter)),
	)
	prevProvider := otel.GetTracerProvider()
	otel.SetTracerProvider(provider)
	defer func() {
		otel.SetTracerProvider(prevProvider)
		_ = provider.Shutdown(context.Background())
	}()

	_, span := StartNode(context.Background(), trace.SpanContext{}, "n", NodeOptions{Depth: 0, State: "running"})
	span.End()
	if err := provider.ForceFlush(context.Background()); err != nil {
		t.Fatalf("force flush failed: %v", err)
	}

	spans := exporter.GetSpans()
	if len(spans) != 1 {
		t.Fatalf("expected 1 span, got %d", len(spans))
	}
	for _, attr := range spans[0].Attributes {
		if string(attr.Key) == "agenkit.node.surface_to_volume" || string(attr.Key) == "surface_to_volume" {
			t.Error("surface_to_volume must not be emitted (deliberately excluded, derivable from other attributes)")
		}
	}
}
