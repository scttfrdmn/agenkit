package io.agenkit.composition;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.*;

class ConditionalAgentTest {

    @Test
    void routesToMatchingBranch() throws Exception {
        MockAgent greet = new MockAgent("greet", "hello!");
        MockAgent farewell = new MockAgent("farewell", "goodbye!");

        ConditionalAgent cond = new ConditionalAgent("cond", List.of(
                new ConditionalAgent.Branch("greeting",
                        msg -> msg.contentString().contains("hello"), greet),
                new ConditionalAgent.Branch("farewell",
                        msg -> msg.contentString().contains("bye"), farewell)
        ), null);

        Message response = cond.process(Message.of("user", "hello there")).get();
        assertThat(response.contentString()).isEqualTo("hello!");
        assertThat(response.getMetadata()).containsEntry("matched_branch", "greeting");
    }

    @Test
    void usesFallbackWhenNoBranchMatches() throws Exception {
        MockAgent fallback = new MockAgent("fallback", "default");

        ConditionalAgent cond = new ConditionalAgent("cond", List.of(
                new ConditionalAgent.Branch("never", msg -> false, new MockAgent())
        ), fallback);

        Message response = cond.process(Message.of("user", "something")).get();
        assertThat(response.contentString()).isEqualTo("default");
        assertThat(response.getMetadata()).containsEntry("matched_branch", "fallback");
    }
}
