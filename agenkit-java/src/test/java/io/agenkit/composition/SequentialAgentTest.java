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

    @Test
    void singleAgentWorks() throws Exception {
        MockAgent only = new MockAgent("only", msg -> "processed: " + msg.contentString());
        SequentialAgent seq = new SequentialAgent("single", List.of(only));
        Message response = seq.process(Message.of("user", "input")).get();
        assertThat(response.contentString()).isEqualTo("processed: input");
    }

    @Test
    void getNameReturnsName() {
        SequentialAgent seq = new SequentialAgent("my-pipeline", List.of());
        assertThat(seq.getName()).isEqualTo("my-pipeline");
    }

    @Test
    void introspectReturnsAgentCount() {
        MockAgent a = new MockAgent("a", "ra");
        MockAgent b = new MockAgent("b", "rb");
        SequentialAgent seq = new SequentialAgent("pipe", List.of(a, b));
        assertThat(seq.introspect().getAgentName()).isEqualTo("pipe");
    }

    @Test
    void pipelineMetadataPresent() throws Exception {
        MockAgent step = new MockAgent("s1", msg -> msg.contentString() + "_done");
        SequentialAgent seq = new SequentialAgent("pl", List.of(step, step));
        Message response = seq.process(Message.of("user", "x")).get();
        assertThat(response.getMetadata()).containsKey("pipeline_length");
        assertThat(response.getMetadata().get("pipeline_length")).isEqualTo(2);
    }
}
