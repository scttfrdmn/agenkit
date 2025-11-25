package patterns

import (
	"context"
	"fmt"
	"strings"
	"testing"
	"time"
)

// ============================================================================
// MemoryEntry Tests
// ============================================================================

func TestCreateMemoryEntry(t *testing.T) {
	entry := CreateMemoryEntry("Test content", map[string]interface{}{"key": "value"}, 0.8, "session1")

	if entry.Content != "Test content" {
		t.Errorf("expected content 'Test content', got %s", entry.Content)
	}

	if entry.Importance != 0.8 {
		t.Errorf("expected importance 0.8, got %f", entry.Importance)
	}

	if entry.SessionID != "session1" {
		t.Errorf("expected session ID 'session1', got %s", entry.SessionID)
	}

	if entry.AccessCount != 0 {
		t.Errorf("expected access count 0, got %d", entry.AccessCount)
	}

	if entry.ID == "" {
		t.Error("expected non-empty ID")
	}
}

// ============================================================================
// WorkingMemory Tests
// ============================================================================

func TestNewWorkingMemory(t *testing.T) {
	wm, err := NewWorkingMemory(10)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if wm.Length() != 0 {
		t.Errorf("expected length 0, got %d", wm.Length())
	}
}

func TestNewWorkingMemory_InvalidMaxMessages(t *testing.T) {
	_, err := NewWorkingMemory(0)
	if err == nil {
		t.Fatal("expected error for maxMessages < 1")
	}
}

func TestWorkingMemory_Store(t *testing.T) {
	wm, _ := NewWorkingMemory(10)
	entry := CreateMemoryEntry("Test", nil, 0.5, "")

	err := wm.Store(context.Background(), entry)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if wm.Length() != 1 {
		t.Errorf("expected length 1, got %d", wm.Length())
	}
}

func TestWorkingMemory_FIFOEviction(t *testing.T) {
	wm, _ := NewWorkingMemory(3)

	// Add 5 entries
	for i := 0; i < 5; i++ {
		entry := CreateMemoryEntry(fmt.Sprintf("Entry %d", i), nil, 0.5, "")
		_ = wm.Store(context.Background(), entry)
	}

	// Should only keep last 3
	if wm.Length() != 3 {
		t.Errorf("expected length 3, got %d", wm.Length())
	}

	all := wm.GetAll()
	if !strings.Contains(all[0].Content, "Entry 2") {
		t.Errorf("expected oldest entry to be 'Entry 2', got %s", all[0].Content)
	}
}

func TestWorkingMemory_Retrieve(t *testing.T) {
	wm, _ := NewWorkingMemory(10)

	// Add entries
	for i := 0; i < 5; i++ {
		entry := CreateMemoryEntry(fmt.Sprintf("Entry %d", i), nil, 0.5, "")
		_ = wm.Store(context.Background(), entry)
	}

	// Retrieve with limit
	results, err := wm.Retrieve(context.Background(), "", 3)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(results) != 3 {
		t.Errorf("expected 3 results, got %d", len(results))
	}
}

func TestWorkingMemory_Delete(t *testing.T) {
	wm, _ := NewWorkingMemory(10)
	entry := CreateMemoryEntry("Test", nil, 0.5, "")
	_ = wm.Store(context.Background(), entry)

	err := wm.Delete(context.Background(), entry.ID)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if wm.Length() != 0 {
		t.Errorf("expected length 0 after delete, got %d", wm.Length())
	}
}

func TestWorkingMemory_Clear(t *testing.T) {
	wm, _ := NewWorkingMemory(10)

	for i := 0; i < 5; i++ {
		entry := CreateMemoryEntry(fmt.Sprintf("Entry %d", i), nil, 0.5, "")
		_ = wm.Store(context.Background(), entry)
	}

	wm.Clear()

	if wm.Length() != 0 {
		t.Errorf("expected length 0 after clear, got %d", wm.Length())
	}
}

// ============================================================================
// ShortTermMemory Tests
// ============================================================================

func TestNewShortTermMemory(t *testing.T) {
	stm, err := NewShortTermMemory(100, 3600)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if stm.Length() != 0 {
		t.Errorf("expected length 0, got %d", stm.Length())
	}
}

func TestNewShortTermMemory_InvalidParams(t *testing.T) {
	_, err := NewShortTermMemory(0, 3600)
	if err == nil {
		t.Error("expected error for maxMessages < 1")
	}

	_, err = NewShortTermMemory(100, 0)
	if err == nil {
		t.Error("expected error for ttlSeconds < 1")
	}
}

func TestShortTermMemory_Store(t *testing.T) {
	stm, _ := NewShortTermMemory(100, 3600)
	entry := CreateMemoryEntry("Test", nil, 0.5, "")

	err := stm.Store(context.Background(), entry)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if stm.Length() != 1 {
		t.Errorf("expected length 1, got %d", stm.Length())
	}
}

func TestShortTermMemory_TTLExpiration(t *testing.T) {
	stm, _ := NewShortTermMemory(100, 1) // 1 second TTL

	entry := CreateMemoryEntry("Test", nil, 0.5, "")
	_ = stm.Store(context.Background(), entry)

	// Wait for expiration
	time.Sleep(1100 * time.Millisecond)

	// Retrieve should trigger cleanup
	results, _ := stm.Retrieve(context.Background(), "", 10)

	if len(results) != 0 {
		t.Errorf("expected 0 results after TTL expiration, got %d", len(results))
	}
}

func TestShortTermMemory_LRUEviction(t *testing.T) {
	stm, _ := NewShortTermMemory(3, 3600)

	// Add 5 entries
	for i := 0; i < 5; i++ {
		entry := CreateMemoryEntry(fmt.Sprintf("Entry %d", i), nil, 0.5, "")
		_ = stm.Store(context.Background(), entry)
		time.Sleep(10 * time.Millisecond) // Ensure different timestamps
	}

	// Should only keep 3 (most recently used)
	if stm.Length() != 3 {
		t.Errorf("expected length 3 after LRU eviction, got %d", stm.Length())
	}
}

func TestShortTermMemory_Retrieve_RecencyOrder(t *testing.T) {
	stm, _ := NewShortTermMemory(100, 3600)

	// Add entries with delays
	for i := 0; i < 3; i++ {
		entry := CreateMemoryEntry(fmt.Sprintf("Entry %d", i), nil, 0.5, "")
		_ = stm.Store(context.Background(), entry)
		time.Sleep(10 * time.Millisecond)
	}

	results, _ := stm.Retrieve(context.Background(), "", 10)

	// Should be in reverse order (most recent first)
	if !strings.Contains(results[0].Content, "Entry 2") {
		t.Errorf("expected most recent entry first, got %s", results[0].Content)
	}
}

// ============================================================================
// LongTermMemory Tests
// ============================================================================

func TestNewLongTermMemory(t *testing.T) {
	ltm, err := NewLongTermMemory(nil, nil, 0.7)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if ltm.Length() != 0 {
		t.Errorf("expected length 0, got %d", ltm.Length())
	}
}

func TestNewLongTermMemory_InvalidMinImportance(t *testing.T) {
	_, err := NewLongTermMemory(nil, nil, -0.1)
	if err == nil {
		t.Error("expected error for minImportance < 0")
	}

	_, err = NewLongTermMemory(nil, nil, 1.5)
	if err == nil {
		t.Error("expected error for minImportance > 1")
	}
}

func TestLongTermMemory_Store_ImportanceThreshold(t *testing.T) {
	ltm, _ := NewLongTermMemory(nil, nil, 0.7)

	// High importance - should store
	highEntry := CreateMemoryEntry("Important", nil, 0.8, "")
	err := ltm.Store(context.Background(), highEntry)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if ltm.Length() != 1 {
		t.Errorf("expected 1 entry stored, got %d", ltm.Length())
	}

	// Low importance - should not store
	lowEntry := CreateMemoryEntry("Not important", nil, 0.5, "")
	_ = ltm.Store(context.Background(), lowEntry)

	if ltm.Length() != 1 {
		t.Errorf("expected still 1 entry (low importance not stored), got %d", ltm.Length())
	}
}

func TestLongTermMemory_Retrieve_KeywordMatch(t *testing.T) {
	ltm, _ := NewLongTermMemory(nil, nil, 0.5)

	entry1 := CreateMemoryEntry("User prefers Python", nil, 0.8, "")
	entry2 := CreateMemoryEntry("User likes Java", nil, 0.7, "")

	_ = ltm.Store(context.Background(), entry1)
	_ = ltm.Store(context.Background(), entry2)

	results, _ := ltm.Retrieve(context.Background(), "Python", 10)

	// Should prioritize entry1 (keyword match)
	if len(results) == 0 || !strings.Contains(results[0].Content, "Python") {
		t.Error("expected Python entry to be retrieved first")
	}
}

func TestLongTermMemory_Retrieve_ImportanceRanking(t *testing.T) {
	ltm, _ := NewLongTermMemory(nil, nil, 0.5)

	entry1 := CreateMemoryEntry("Low importance", nil, 0.6, "")
	entry2 := CreateMemoryEntry("High importance", nil, 0.9, "")

	_ = ltm.Store(context.Background(), entry1)
	_ = ltm.Store(context.Background(), entry2)

	results, _ := ltm.Retrieve(context.Background(), "", 10)

	// Should prioritize by importance
	if !strings.Contains(results[0].Content, "High importance") {
		t.Error("expected high importance entry first")
	}
}

// ============================================================================
// MemoryHierarchy Tests
// ============================================================================

func TestNewMemoryHierarchy(t *testing.T) {
	wm, _ := NewWorkingMemory(10)
	stm, _ := NewShortTermMemory(100, 3600)
	ltm, _ := NewLongTermMemory(nil, nil, 0.7)

	hierarchy := NewMemoryHierarchy(wm, stm, ltm)

	if hierarchy.working == nil {
		t.Error("expected working memory to be set")
	}
}

func TestMemoryHierarchy_Store_AllTiers(t *testing.T) {
	wm, _ := NewWorkingMemory(10)
	stm, _ := NewShortTermMemory(100, 3600)
	ltm, _ := NewLongTermMemory(nil, nil, 0.7)

	hierarchy := NewMemoryHierarchy(wm, stm, ltm)

	id, err := hierarchy.Store(context.Background(), "Important fact", nil, 0.8, "")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if id == "" {
		t.Error("expected non-empty ID")
	}

	// Should be in all tiers
	if wm.Length() != 1 {
		t.Errorf("expected 1 entry in working memory, got %d", wm.Length())
	}

	if stm.Length() != 1 {
		t.Errorf("expected 1 entry in short-term memory, got %d", stm.Length())
	}

	if ltm.Length() != 1 {
		t.Errorf("expected 1 entry in long-term memory, got %d", ltm.Length())
	}
}

func TestMemoryHierarchy_Store_LowImportance(t *testing.T) {
	wm, _ := NewWorkingMemory(10)
	stm, _ := NewShortTermMemory(100, 3600)
	ltm, _ := NewLongTermMemory(nil, nil, 0.7)

	hierarchy := NewMemoryHierarchy(wm, stm, ltm)

	_, err := hierarchy.Store(context.Background(), "Low importance fact", nil, 0.5, "")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should be in working and short-term, but not long-term
	if wm.Length() != 1 {
		t.Error("expected entry in working memory")
	}

	if stm.Length() != 1 {
		t.Error("expected entry in short-term memory")
	}

	if ltm.Length() != 0 {
		t.Error("expected no entry in long-term memory (below threshold)")
	}
}

func TestMemoryHierarchy_Retrieve_AllTiers(t *testing.T) {
	wm, _ := NewWorkingMemory(10)
	stm, _ := NewShortTermMemory(100, 3600)
	ltm, _ := NewLongTermMemory(nil, nil, 0.7)

	hierarchy := NewMemoryHierarchy(wm, stm, ltm)

	_, _ = hierarchy.Store(context.Background(), "Test content", nil, 0.8, "")

	results, err := hierarchy.Retrieve(context.Background(), "", 10, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should deduplicate (same entry across tiers)
	if len(results) != 1 {
		t.Errorf("expected 1 deduplicated result, got %d", len(results))
	}
}

func TestMemoryHierarchy_Retrieve_SpecificTiers(t *testing.T) {
	wm, _ := NewWorkingMemory(10)
	stm, _ := NewShortTermMemory(100, 3600)
	ltm, _ := NewLongTermMemory(nil, nil, 0.7)

	hierarchy := NewMemoryHierarchy(wm, stm, ltm)

	_, _ = hierarchy.Store(context.Background(), "Test", nil, 0.8, "")

	// Search only working memory
	results, _ := hierarchy.Retrieve(context.Background(), "", 10, []string{"working"})

	if len(results) != 1 {
		t.Errorf("expected 1 result from working memory only, got %d", len(results))
	}
}

func TestMemoryHierarchy_Delete_AllTiers(t *testing.T) {
	wm, _ := NewWorkingMemory(10)
	stm, _ := NewShortTermMemory(100, 3600)
	ltm, _ := NewLongTermMemory(nil, nil, 0.7)

	hierarchy := NewMemoryHierarchy(wm, stm, ltm)

	id, _ := hierarchy.Store(context.Background(), "Test", nil, 0.8, "")

	err := hierarchy.Delete(context.Background(), id)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Should be deleted from all tiers
	if wm.Length() != 0 {
		t.Error("expected entry deleted from working memory")
	}

	if stm.Length() != 0 {
		t.Error("expected entry deleted from short-term memory")
	}

	if ltm.Length() != 0 {
		t.Error("expected entry deleted from long-term memory")
	}
}

func TestMemoryHierarchy_ClearWorking(t *testing.T) {
	wm, _ := NewWorkingMemory(10)
	hierarchy := NewMemoryHierarchy(wm, nil, nil)

	_, _ = hierarchy.Store(context.Background(), "Test", nil, 0.5, "")

	hierarchy.ClearWorking()

	if len(hierarchy.GetWorking()) != 0 {
		t.Error("expected working memory to be cleared")
	}
}

func TestMemoryHierarchy_InvalidImportance(t *testing.T) {
	wm, _ := NewWorkingMemory(10)
	hierarchy := NewMemoryHierarchy(wm, nil, nil)

	_, err := hierarchy.Store(context.Background(), "Test", nil, -0.1, "")
	if err == nil {
		t.Error("expected error for importance < 0")
	}

	_, err = hierarchy.Store(context.Background(), "Test", nil, 1.5, "")
	if err == nil {
		t.Error("expected error for importance > 1")
	}
}

// ============================================================================
// Integration Tests
// ============================================================================

func TestMemoryHierarchy_RealWorldScenario(t *testing.T) {
	// Create memory hierarchy
	wm, _ := NewWorkingMemory(5)
	stm, _ := NewShortTermMemory(20, 3600)
	ltm, _ := NewLongTermMemory(nil, nil, 0.7)

	hierarchy := NewMemoryHierarchy(wm, stm, ltm)

	// Store conversation with varying importance
	_, _ = hierarchy.Store(context.Background(), "User's name is Alice", map[string]interface{}{"type": "identity"}, 0.9, "session1")
	_, _ = hierarchy.Store(context.Background(), "User prefers dark mode", map[string]interface{}{"type": "preference"}, 0.8, "session1")
	_, _ = hierarchy.Store(context.Background(), "Weather is sunny today", map[string]interface{}{"type": "ephemeral"}, 0.3, "session1")

	// Retrieve preferences
	results, _ := hierarchy.Retrieve(context.Background(), "preferences", 5, nil)

	// Should find the preference entry
	found := false
	for _, r := range results {
		if strings.Contains(r.Content, "dark mode") {
			found = true
			break
		}
	}

	if !found {
		t.Error("expected to retrieve preference memory")
	}

	// Long-term memory should only have high importance items
	if ltm.Length() != 2 {
		t.Errorf("expected 2 entries in long-term (>= 0.7), got %d", ltm.Length())
	}
}
