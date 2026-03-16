//go:build ignore

// resume_migrated demonstrates DurableAgent.ResumeMigrated — the recovery path
// taken by `agenkit-runtime recover` after a spot eviction.
//
// This example runs without a real Firecracker VM or network. All persistence
// is done with MemoryStorage to keep the demo self-contained.
//
// Production flow (what agenkit-runtime does):
//
//  1. SpotMonitor detects an IMDS termination notice on the source host.
//  2. Migrator.MigrateAll sends a "checkpoint_now" command over vsock to each
//     guest agent.
//  3. The guest checkpoints its state, attaches a MigrationContext (source host,
//     VM slot, reason, migration ID) to the checkpoint metadata, and replies
//     with the resulting checkpointID.
//  4. A MigrationManifest is written to a shared checkpoint store (S3 or NFS).
//  5. A replacement host comes up; `agenkit-runtime recover` is invoked.
//  6. recover reads the MigrationManifest, and for each SessionMigration with
//     status == "pending" it calls DurableAgent.ResumeMigrated(ctx, checkpointID).
//
// This example demonstrates step 6. Steps 1–5 are replaced by:
//   - directly creating a checkpoint via durable.Checkpoint()
//   - optionally attaching a MigrationContext via checkpointing.AttachMigrationContext
//     (shown in the "production path" section below)
//
// Run with:
//
//	go run main.go
package main

import (
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/checkpointing"
)

// ---------------------------------------------------------------------------
// mockAgent — minimal agenkit.Agent used as a stand-in for a real agent
// ---------------------------------------------------------------------------

// mockAgent satisfies the agenkit.Agent interface. In production this would be
// an LLM-backed agent, a tool-using agent, or any other Agenkit agent type.
type mockAgent struct{}

func (a *mockAgent) Name() string { return "mock-agent" }

func (a *mockAgent) Process(_ context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	return agenkit.NewMessage("assistant", "mock response to: "+msg.ContentString()), nil
}

func (a *mockAgent) Capabilities() []string { return nil }

func (a *mockAgent) Introspect() *agenkit.IntrospectionResult { return nil }

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

func printSection(title string) {
	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println(title)
	fmt.Println(strings.Repeat("=", 60))
}

func printState(label string, state map[string]interface{}) {
	if len(state) == 0 {
		fmt.Printf("  %s: (empty)\n", label)
		return
	}
	fmt.Printf("  %s:\n", label)
	for k, v := range state {
		fmt.Printf("    %-20s = %v\n", k, v)
	}
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

func main() {
	ctx := context.Background()

	fmt.Println("resume_migrated — DurableAgent.ResumeMigrated spot-eviction recovery")
	fmt.Println("All persistence is in-memory; no Firecracker VM or network required.")

	// ------------------------------------------------------------------
	// 1. Set up a DurableAgent backed by in-memory storage.
	// ------------------------------------------------------------------
	printSection("1. Create DurableAgent with MemoryStorage")

	storage := checkpointing.NewMemoryStorage()
	agent := &mockAgent{}

	// checkpointInterval=1 means a checkpoint is created on every Process call.
	// autoResume=false because we are demonstrating explicit ResumeMigrated.
	durable := checkpointing.NewDurableAgent(agent, storage, 1, false, "")
	fmt.Printf("  agent name : %s\n", durable.Name())
	fmt.Printf("  storage    : MemoryStorage (in-process)\n")

	// ------------------------------------------------------------------
	// 2. Process a message to build up session state.
	// ------------------------------------------------------------------
	printSection("2. Process messages to build session state")

	const sessionID = "session-1"

	resp, err := durable.Process(ctx, agenkit.NewMessage("user", "Hello, start the task."), sessionID)
	if err != nil {
		fmt.Fprintf(os.Stderr, "process error: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("  turn 1 response: %s\n", resp.ContentString())

	resp, err = durable.Process(ctx, agenkit.NewMessage("user", "Continue the task."), sessionID)
	if err != nil {
		fmt.Fprintf(os.Stderr, "process error: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("  turn 2 response: %s\n", resp.ContentString())

	printState("state after 2 turns", durable.GetState(sessionID))

	// ------------------------------------------------------------------
	// 3. Simulate spot eviction: take an on-demand checkpoint.
	//    In production, agenkit-runtime sends "checkpoint_now" over vsock.
	// ------------------------------------------------------------------
	printSection("3. Checkpoint at eviction time (simulated)")

	checkpointID, err := durable.Checkpoint(ctx, sessionID, map[string]interface{}{
		"triggered_by": "spot_warning",
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "checkpoint error: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("  checkpoint ID : %s\n", checkpointID)

	// NOTE: In the full production path, agenkit-runtime would also call
	// checkpointing.AttachMigrationContext on the saved Checkpoint before
	// writing the MigrationManifest.  We demonstrate that separately below.

	// ------------------------------------------------------------------
	// 4. Simulate "new host" by creating a fresh DurableAgent against the
	//    same storage (represents agenkit-runtime recover on the replacement
	//    host loading checkpoints from S3/NFS).
	// ------------------------------------------------------------------
	printSection("4. ResumeMigrated on the replacement host")

	newDurable := checkpointing.NewDurableAgent(agent, storage, 1, false, "")

	resumeCtx, restoredState, err := newDurable.ResumeMigrated(ctx, checkpointID)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ResumeMigrated error: %v\n", err)
		os.Exit(1)
	}

	printState("restored state", restoredState)

	// Check whether a MigrationContext is present in the returned context.
	// ResumeMigrated injects one only when the checkpoint was created via
	// AttachMigrationContext (the agenkit-runtime production path).
	if mc, ok := resumeCtx.Value(checkpointing.MigrationContextKey).(checkpointing.MigrationContext); ok {
		fmt.Printf("\n  MigrationContext present:\n")
		fmt.Printf("    SourceHost    : %s\n", mc.SourceHost)
		fmt.Printf("    SourceVMSlot  : %d\n", mc.SourceVMSlot)
		fmt.Printf("    InterruptedBy : %s\n", mc.InterruptedBy)
		fmt.Printf("    MigrationID   : %s\n", mc.MigrationID)
	} else {
		fmt.Println("\n  No MigrationContext in context.")
		fmt.Println("  (Expected — this checkpoint was created locally, not via agenkit-runtime.)")
		fmt.Println("  In production, agenkit-runtime calls AttachMigrationContext before saving.")
	}

	// ------------------------------------------------------------------
	// 5. Show what AttachMigrationContext does in the production path.
	// ------------------------------------------------------------------
	printSection("5. Production path: AttachMigrationContext (informational)")

	fmt.Println("  In production, agenkit-runtime calls:")
	fmt.Println()
	fmt.Println(`    cp, _ := storage.Load(ctx, checkpointID)`)
	fmt.Println(`    checkpointing.AttachMigrationContext(cp, checkpointing.MigrationContext{`)
	fmt.Println(`        SourceHost    : "i-0abc1234.us-east-1.compute.internal",`)
	fmt.Println(`        SourceVMSlot  : 3,`)
	fmt.Println(`        InterruptedBy : "spot_warning",`)
	fmt.Println(`        MigrationID   : "mig-20260315-001",`)
	fmt.Println(`    })`)
	fmt.Println(`    _ = storage.Save(ctx, cp)  // overwrite with migration metadata`)
	fmt.Println()
	fmt.Println("  After that, ResumeMigrated will inject MigrationContext into ctx,")
	fmt.Println("  and resumeCtx.Value(checkpointing.MigrationContextKey) will be non-nil.")

	// Demonstrate it with an explicit AttachMigrationContext call.
	loadedCP, err := storage.Load(ctx, checkpointID)
	if err != nil || loadedCP == nil {
		fmt.Fprintf(os.Stderr, "failed to load checkpoint for demonstration: %v\n", err)
		os.Exit(1)
	}

	checkpointing.AttachMigrationContext(loadedCP, checkpointing.MigrationContext{
		SourceHost:    "i-0abc1234.us-east-1.compute.internal",
		SourceVMSlot:  3,
		InterruptedBy: "spot_warning",
		MigrationID:   "mig-20260315-001",
	})
	if err := storage.Save(ctx, loadedCP); err != nil {
		fmt.Fprintf(os.Stderr, "failed to re-save checkpoint: %v\n", err)
		os.Exit(1)
	}

	// Now ResumeMigrated will see the MigrationContext.
	printSection("6. ResumeMigrated after AttachMigrationContext")

	newDurable2 := checkpointing.NewDurableAgent(agent, storage, 1, false, "")
	resumeCtx2, restoredState2, err := newDurable2.ResumeMigrated(ctx, checkpointID)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ResumeMigrated (2) error: %v\n", err)
		os.Exit(1)
	}

	printState("restored state (2)", restoredState2)

	if mc, ok := resumeCtx2.Value(checkpointing.MigrationContextKey).(checkpointing.MigrationContext); ok {
		fmt.Printf("\n  MigrationContext present:\n")
		fmt.Printf("    SourceHost    : %s\n", mc.SourceHost)
		fmt.Printf("    SourceVMSlot  : %d\n", mc.SourceVMSlot)
		fmt.Printf("    InterruptedBy : %s\n", mc.InterruptedBy)
		fmt.Printf("    MigrationID   : %s\n", mc.MigrationID)
	} else {
		fmt.Println("  (no MigrationContext — unexpected)")
	}

	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("resume_migrated demo complete.")
	fmt.Println()
	fmt.Println("Summary:")
	fmt.Println("  durable.Checkpoint()        → snapshot session state")
	fmt.Println("  AttachMigrationContext()     → embed eviction provenance in metadata")
	fmt.Println("  newDurable.ResumeMigrated() → restore state + inject MigrationContext")
	fmt.Println("  ctx.Value(MigrationContextKey) → detect migration in downstream code")
}
