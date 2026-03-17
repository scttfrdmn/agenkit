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
}
