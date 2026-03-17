package io.agenkit.composition;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.*;

class ParallelAgentTest {

    @Test
    void fanOutAndAggregate() throws Exception {
        MockAgent a = new MockAgent("a", "result_a");
        MockAgent b = new MockAgent("b", "result_b");
        MockAgent c = new MockAgent("c", "result_c");

        ParallelAgent parallel = new ParallelAgent("parallel", List.of(a, b, c));
        Message response = parallel.process(Message.of("user", "question")).get();

        assertThat(response.contentString())
                .contains("result_a").contains("result_b").contains("result_c");
        assertThat(response.getMetadata()).containsEntry("parallel_count", 3);
    }

    @Test
    void singleAgentReturnsItsResponse() throws Exception {
        MockAgent only = new MockAgent("only", "solo");
        ParallelAgent parallel = new ParallelAgent("parallel", List.of(only));
        Message response = parallel.process(Message.of("user", "hi")).get();
        assertThat(response.contentString()).isEqualTo("solo");
    }
}
