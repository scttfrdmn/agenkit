package io.agenkit.core;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.*;

class MessageTest {

    @Test
    void factoryCreatesValidMessage() {
        Message msg = Message.of("user", "hello");
        assertThat(msg.getRole()).isEqualTo("user");
        assertThat(msg.contentString()).isEqualTo("hello");
        assertThat(msg.getTimestamp()).isNotNull();
    }

    @Test
    void contentStringHandlesNull() {
        Message msg = new Message("assistant", null, null, null);
        assertThat(msg.contentString()).isEmpty();
    }

    @Test
    void withMetadataReturnsCopy() {
        Message original = Message.of("user", "hello");
        Message withMeta = original.withMetadata("key", "value");
        assertThat(withMeta.getMetadata()).containsEntry("key", "value");
        assertThat(original.getMetadata()).doesNotContainKey("key");
    }

    @Test
    void validateAcceptsValidRoles() {
        for (String role : new String[]{"user", "assistant", "system", "tool", "agent"}) {
            Message msg = Message.of(role, "content");
            assertThatCode(msg::validate).doesNotThrowAnyException();
        }
    }

    @Test
    void validateRejectsInvalidRole() {
        Message msg = Message.of("invalid_role", "content");
        // Note: Message.of doesn't validate - must call validate() explicitly
        assertThatThrownBy(msg::validate)
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("invalid message role");
    }

    @Test
    void validateRejectsEmptyRole() {
        Message msg = new Message("", "content", null, null);
        assertThatThrownBy(msg::validate)
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("cannot be empty");
    }

    @Test
    void metadataIsImmutable() {
        Message msg = Message.of("user", "hello");
        assertThatThrownBy(() -> msg.getMetadata().put("key", "value"))
                .isInstanceOf(UnsupportedOperationException.class);
    }
}
