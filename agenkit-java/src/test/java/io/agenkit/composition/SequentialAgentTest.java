package io.agenkit.composition;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.*;

class SequentialAgentTest {

    @Test
    void chainsAgentsInOrder() throws Exception {
        MockAgent step1 = new MockAgent("step1", msg -> msg.contentString() + "_step1");
        MockAgent step2 = new MockAgent("step2", msg -> msg.contentString() + "_step2");
        MockAgent step3 = new MockAgent("step3", msg -> msg.contentString() + "_step3");

        SequentialAgent seq = new SequentialAgent("pipeline", List.of(step1, step2, step3));
        Message response = seq.process(Message.of("user", "start")).get();

        assertThat(response.contentString()).isEqualTo("start_step1_step2_step3");
        assertThat(response.getMetadata()).containsEntry("pipeline_length", 3);
    }

    @Test
    void emptyPipelineReturnsInput() throws Exception {
        SequentialAgent seq = new SequentialAgent("empty", List.of());
        Message input = Message.of("user", "hello");
        Message response = seq.process(input).get();
        assertThat(response.contentString()).isEqualTo("hello");
    }
}
