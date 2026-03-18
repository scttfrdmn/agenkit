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

    @Test
    void sizeReflectsStoredMessages() {
        MemoryHierarchy hierarchy = new MemoryHierarchy();
        hierarchy.store(Message.of("user", "msg one"));
        hierarchy.store(Message.of("user", "msg two"));
        // size() counts across tiers; at minimum both stores are present
        assertThat(hierarchy.size()).isGreaterThanOrEqualTo(2);
    }

    @Test
    void retrieveWithTopKLimit() {
        MemoryHierarchy hierarchy = new MemoryHierarchy();
        for (int i = 0; i < 10; i++) {
            hierarchy.store(Message.of("user", "topic " + i));
        }
        var results = hierarchy.retrieve("topic", 3);
        assertThat(results).hasSizeLessThanOrEqualTo(3);
    }

    @Test
    void clearThenStorePersistsNewData() {
        MemoryHierarchy hierarchy = new MemoryHierarchy();
        hierarchy.store(Message.of("user", "old data"));
        hierarchy.clear();
        hierarchy.store(Message.of("user", "fresh data"));
        assertThat(hierarchy.size()).isGreaterThanOrEqualTo(1);
        var results = hierarchy.retrieve("fresh", 5);
        assertThat(results).isNotEmpty();
    }
}
