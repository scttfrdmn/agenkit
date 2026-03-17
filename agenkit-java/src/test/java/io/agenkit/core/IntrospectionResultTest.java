package io.agenkit.core;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.*;

class IntrospectionResultTest {

    @Test
    void constructorSetsFields() {
        IntrospectionResult result = new IntrospectionResult(
                "my-agent",
                List.of("cap1", "cap2"),
                Map.of("key", "val"),
                Map.of("status", "active"),
                List.of("tool1"));

        assertThat(result.getAgentName()).isEqualTo("my-agent");
        assertThat(result.getCapabilities()).containsExactly("cap1", "cap2");
        assertThat(result.getMemory()).containsEntry("key", "val");
        assertThat(result.getState()).containsEntry("status", "active");
        assertThat(result.getTools()).containsExactly("tool1");
    }

    @Test
    void nullsBecomEmptyCollections() {
        IntrospectionResult result = new IntrospectionResult("agent", null, null, null, null);
        assertThat(result.getCapabilities()).isEmpty();
        assertThat(result.getMemory()).isEmpty();
        assertThat(result.getState()).isEmpty();
        assertThat(result.getTools()).isEmpty();
    }
}
