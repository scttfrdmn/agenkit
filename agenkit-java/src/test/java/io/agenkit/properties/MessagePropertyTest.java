package io.agenkit.properties;

import io.agenkit.core.Message;
import net.jqwik.api.*;
import net.jqwik.api.constraints.StringLength;

import static org.assertj.core.api.Assertions.*;

class MessagePropertyTest {

    @Property
    void roleRoundTrips(@ForAll @StringLength(min = 1, max = 20) String role) {
        Message msg = Message.of(role, "content");
        assertThat(msg.getRole()).isEqualTo(role);
    }

    @Property
    void contentRoundTrips(@ForAll String content) {
        Message msg = Message.of("user", content);
        assertThat(msg.contentString()).isEqualTo(content);
    }

    @Property
    void emptyContentValid(@ForAll @StringLength(min = 1, max = 10) String role) {
        Message msg = Message.of(role, "");
        assertThat(msg.contentString()).isEmpty();
    }

    @Property
    void timestampAlwaysSet(@ForAll @StringLength(min = 1, max = 10) String role,
                            @ForAll @StringLength(min = 0, max = 50) String content) {
        Message msg = Message.of(role, content);
        assertThat(msg.getTimestamp()).isNotNull();
    }

    @Property
    void withMetadataPreservesRole(@ForAll @StringLength(min = 1, max = 10) String role,
                                   @ForAll @StringLength(min = 1, max = 10) String key,
                                   @ForAll @StringLength(min = 1, max = 10) String value) {
        Message msg = Message.of(role, "text").withMetadata(key, value);
        assertThat(msg.getRole()).isEqualTo(role);
    }

    @Property
    void withMetadataPreservesContent(@ForAll @StringLength(min = 0, max = 50) String content,
                                      @ForAll @StringLength(min = 1, max = 10) String key) {
        Message msg = Message.of("user", content).withMetadata(key, "value");
        assertThat(msg.contentString()).isEqualTo(content);
    }

    @Property
    void withMetadataDoesNotMutateOriginal(@ForAll @StringLength(min = 1, max = 10) String key) {
        Message original = Message.of("user", "original");
        original.withMetadata(key, "added");
        assertThat(original.getMetadata()).doesNotContainKey(key);
    }

    @Property
    void withMetadataNewCopyContainsEntry(@ForAll @StringLength(min = 1, max = 10) String key,
                                          @ForAll @StringLength(min = 1, max = 20) String value) {
        Message original = Message.of("user", "text");
        Message withMeta = original.withMetadata(key, value);
        assertThat(withMeta.getMetadata()).containsEntry(key, value);
    }

    @Property
    void defaultMetadataIsEmpty(@ForAll @StringLength(min = 1, max = 10) String role) {
        Message msg = Message.of(role, "text");
        assertThat(msg.getMetadata()).isEmpty();
    }

    @Property
    void metadataImmutableAfterCreation(@ForAll @StringLength(min = 1, max = 10) String role) {
        Message msg = Message.of(role, "text");
        assertThatThrownBy(() -> msg.getMetadata().put("k", "v"))
                .isInstanceOf(UnsupportedOperationException.class);
    }

    @Property
    void contentStringNeverNullForFactoryMethod(@ForAll @StringLength(min = 0, max = 100) String content) {
        Message msg = Message.of("user", content);
        assertThat(msg.contentString()).isNotNull();
    }

    @Property
    void roleNeverChangedByMetadataOp(@ForAll @StringLength(min = 1, max = 8) String role,
                                      @ForAll @StringLength(min = 1, max = 8) String k1,
                                      @ForAll @StringLength(min = 1, max = 8) String k2) {
        Message msg = Message.of(role, "content")
                .withMetadata(k1, "v1")
                .withMetadata(k2, "v2");
        assertThat(msg.getRole()).isEqualTo(role);
    }
}
