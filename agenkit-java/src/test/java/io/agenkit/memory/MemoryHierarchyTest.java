package io.agenkit.memory;

import io.agenkit.core.Message;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.*;

class MemoryHierarchyTest {

    @Test
    void storesPropagatesAllTiers() {
        MemoryHierarchy hierarchy = new MemoryHierarchy();
        hierarchy.store(Message.of("user", "important fact"));

        assertThat(hierarchy.getWorking().size()).isEqualTo(1);
        assertThat(hierarchy.getEpisodic().size()).isEqualTo(1);
        assertThat(hierarchy.getSemantic().size()).isEqualTo(1);
    }

    @Test
    void retrieveReturnsMessages() {
        MemoryHierarchy hierarchy = new MemoryHierarchy();
        hierarchy.store(Message.of("user", "sky is blue"));
        hierarchy.store(Message.of("assistant", "grass is green"));

        var results = hierarchy.retrieve("sky", 5);
        assertThat(results).isNotEmpty();
    }

    @Test
    void clearErasesAll() {
        MemoryHierarchy hierarchy = new MemoryHierarchy();
        hierarchy.store(Message.of("user", "test"));
        hierarchy.clear();
        assertThat(hierarchy.size()).isEqualTo(0);
    }
}
