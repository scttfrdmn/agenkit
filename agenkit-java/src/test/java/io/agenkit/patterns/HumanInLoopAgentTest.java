package io.agenkit.patterns;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockLlmClient;
import org.junit.jupiter.api.Test;

import java.util.concurrent.CompletableFuture;

import static org.assertj.core.api.Assertions.*;

class HumanInLoopAgentTest {

    @Test
    void approvesAndExecutes() throws Exception {
        MockLlmClient llm = new MockLlmClient(messages -> {
            String last = messages.get(messages.size() - 1).contentString();
            if (last.contains("Propose")) return "Action: query the database";
            return "Database query completed successfully";
        });

        HumanInLoopAgent agent = HumanInLoopAgent.autoApprove("hil", llm);
        Message response = agent.process(Message.of("user", "get some data")).get();

        assertThat(response.getMetadata()).containsEntry("approved", true);
    }

    @Test
    void rejectsUnapprovedAction() throws Exception {
        MockLlmClient llm = new MockLlmClient("Action: delete all records");
        HumanInLoopAgent agent = new HumanInLoopAgent("hil", llm,
                action -> CompletableFuture.completedFuture(false));

        Message response = agent.process(Message.of("user", "delete data")).get();

        assertThat(response.getMetadata()).containsEntry("approved", false);
        assertThat(response.contentString()).contains("rejected");
    }

    @Test
    void autoApproveFactoryWorks() {
        HumanInLoopAgent agent = HumanInLoopAgent.autoApprove("test", new MockLlmClient());
        assertThat(agent.getName()).isEqualTo("test");
        assertThat(agent.getCapabilities()).contains("human_in_loop");
    }
}
