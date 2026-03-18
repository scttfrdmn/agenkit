package io.agenkit.memory;

import io.agenkit.core.Message;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.*;

class EphemeralMemoryTest {

    @Test
    void storeAndRetrieve() {
        EphemeralMemory memory = new EphemeralMemory();
        memory.store(Message.of("user", "hello world"));

        assertThat(memory.size()).isEqualTo(1);
        assertThat(memory.retrieve("hello", 5)).hasSize(1);
    }

    @Test
    void retrieveReturnsTopK() {
        EphemeralMemory memory = new EphemeralMemory();
        for (int i = 0; i < 10; i++) {
            memory.store(Message.of("user", "message " + i));
        }

        assertThat(memory.retrieve("message", 3)).hasSize(3);
    }

    @Test
    void clearRemovesAll() {
        EphemeralMemory memory = new EphemeralMemory();
        memory.store(Message.of("user", "test"));
        memory.clear();
        assertThat(memory.size()).isEqualTo(0);
    }

    @Test
    void maxSizeEvictsOldest() {
        EphemeralMemory memory = new EphemeralMemory(3);
        for (int i = 0; i < 5; i++) {
            memory.store(Message.of("user", "msg" + i));
        }
        assertThat(memory.size()).isEqualTo(3);
    }

    @Test
    void storeMultipleMessages() {
        EphemeralMemory memory = new EphemeralMemory();
        memory.store(Message.of("user", "first message"));
        memory.store(Message.of("assistant", "second message"));
        memory.store(Message.of("user", "third message"));
        assertThat(memory.size()).isEqualTo(3);
    }

    @Test
    void retrieveWithEmptyQuery() {
        EphemeralMemory memory = new EphemeralMemory();
        memory.store(Message.of("user", "some content"));
        memory.store(Message.of("assistant", "other content"));
        var results = memory.retrieve("", 10);
        assertThat(results).isNotNull();
    }

    @Test
    void sizeAfterMultipleStores() {
        EphemeralMemory memory = new EphemeralMemory(100);
        for (int i = 0; i < 20; i++) {
            memory.store(Message.of("user", "item " + i));
        }
        assertThat(memory.size()).isEqualTo(20);
    }

    @Test
    void storeAndRetrieveSameMessage() {
        EphemeralMemory memory = new EphemeralMemory();
        memory.store(Message.of("user", "unique content xyz"));
        var results = memory.retrieve("unique content xyz", 5);
        assertThat(results).hasSize(1);
        assertThat(results.get(0).contentString()).isEqualTo("unique content xyz");
    }
}
