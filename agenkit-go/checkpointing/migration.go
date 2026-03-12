package checkpointing

import (
	"context"
	"encoding/json"
	"time"
)

// migrationMetaKey is the metadata key used to embed a MigrationContext in a Checkpoint.
const migrationMetaKey = "_migration_context"

// contextKey is a private type for context value keys in this package.
type contextKey string

// MigrationContextKey is the context key under which ResumeMigrated injects the
// MigrationContext into the returned context.
var MigrationContextKey = contextKey("migration_context")

// MigrationContext carries the provenance of a migrated agent session.
//
// It is embedded into the checkpoint metadata when an agent is interrupted (spot
// eviction, drain, crash, or user-initiated) so that the receiving host can
// reconstruct the full execution context and resume cleanly.
type MigrationContext struct {
	// SourceHost is the hostname of the machine that was evicted.
	SourceHost string `json:"source_host"`
	// SourceVMSlot is the Firecracker VM slot index on the source host.
	SourceVMSlot int `json:"source_vm_slot"`
	// InterruptedBy describes what caused the migration.
	// Valid values: "spot_warning" | "drain" | "crash" | "user"
	InterruptedBy string `json:"interrupted_by"`
	// MigrationID is a unique identifier for this migration event.
	MigrationID string `json:"migration_id"`
	// ExecutionElapsedMS is how long the session had been running on the source host
	// at the time of interruption, in milliseconds.
	ExecutionElapsedMS int64 `json:"execution_elapsed_ms"`
	// OriginalMessageID is the ID of the message that triggered the in-flight execution.
	OriginalMessageID string `json:"original_message_id"`
	// Deadline is the hard deadline by which the session must be resumed, if any.
	Deadline time.Time `json:"deadline,omitempty"`
}

// AttachMigrationContext embeds mc into cp's Metadata so that downstream consumers
// can detect and handle migrated sessions.
func AttachMigrationContext(cp *Checkpoint, mc MigrationContext) {
	if cp.Metadata == nil {
		cp.Metadata = make(map[string]interface{})
	}
	data, err := json.Marshal(mc)
	if err != nil {
		return
	}
	var raw map[string]interface{}
	if err := json.Unmarshal(data, &raw); err != nil {
		return
	}
	cp.Metadata[migrationMetaKey] = raw
}

// ExtractMigrationContext retrieves the MigrationContext from cp's Metadata.
// Returns (context, true) if a migration context is present, (zero, false) otherwise.
func ExtractMigrationContext(cp *Checkpoint) (MigrationContext, bool) {
	if cp.Metadata == nil {
		return MigrationContext{}, false
	}
	raw, ok := cp.Metadata[migrationMetaKey]
	if !ok {
		return MigrationContext{}, false
	}
	data, err := json.Marshal(raw)
	if err != nil {
		return MigrationContext{}, false
	}
	var mc MigrationContext
	if err := json.Unmarshal(data, &mc); err != nil {
		return MigrationContext{}, false
	}
	return mc, true
}

// IsMigrationCheckpoint reports whether cp was created as part of a spot/drain migration.
func IsMigrationCheckpoint(cp *Checkpoint) bool {
	_, ok := ExtractMigrationContext(cp)
	return ok
}

// withMigrationContext returns a copy of ctx with mc stored under MigrationContextKey.
func withMigrationContext(ctx context.Context, mc MigrationContext) context.Context {
	return context.WithValue(ctx, MigrationContextKey, mc)
}
