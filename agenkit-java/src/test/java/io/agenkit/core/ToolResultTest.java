package io.agenkit.core;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.*;

class ToolResultTest {

    @Test
    void okCreatesSuccessResult() {
        ToolResult result = ToolResult.ok("some data");
        assertThat(result.isSuccess()).isTrue();
        assertThat(result.getData()).isEqualTo("some data");
        assertThat(result.getError()).isNull();
    }

    @Test
    void failCreatesFailureResult() {
        ToolResult result = ToolResult.fail("something went wrong");
        assertThat(result.isSuccess()).isFalse();
        assertThat(result.getData()).isNull();
        assertThat(result.getError()).isEqualTo("something went wrong");
    }

    @Test
    void withMetadataReturnsCopy() {
        ToolResult original = ToolResult.ok("data");
        ToolResult withMeta = original.withMetadata("duration_ms", 42L);
        assertThat(withMeta.getMetadata()).containsEntry("duration_ms", 42L);
        assertThat(original.getMetadata()).doesNotContainKey("duration_ms");
    }

    @Test
    void toStringShowsContent() {
        assertThat(ToolResult.ok("hello").toString()).contains("success=true");
        assertThat(ToolResult.fail("oops").toString()).contains("success=false").contains("oops");
    }

    @Test
    void okWithNullDataIsValid() {
        ToolResult result = ToolResult.ok(null);
        assertThat(result.isSuccess()).isTrue();
        assertThat(result.getData()).isNull();
        assertThat(result.getError()).isNull();
    }

    @Test
    void metadataAccumulatesAcrossMultipleCalls() {
        ToolResult r = ToolResult.ok("payload")
                .withMetadata("k1", "v1")
                .withMetadata("k2", 99);
        assertThat(r.getMetadata()).containsEntry("k1", "v1").containsEntry("k2", 99);
        assertThat(r.getData()).isEqualTo("payload");
    }
}
