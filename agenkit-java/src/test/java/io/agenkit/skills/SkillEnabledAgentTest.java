package io.agenkit.skills;

import static org.assertj.core.api.Assertions.assertThat;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class SkillEnabledAgentTest {

    private static Path makeSkillDir(Path base, String name, String description) throws IOException {
        Path skillDir = base.resolve(name);
        Files.createDirectories(skillDir);
        String content = "---\nname: " + name + "\ndescription: " + description
                + "\n---\nInstructions here.";
        Files.writeString(skillDir.resolve("SKILL.md"), content, StandardCharsets.UTF_8);
        return skillDir;
    }

    /** Agent that echoes its input content back. */
    private static final class EchoAgent implements Agent {
        @Override
        public String getName() {
            return "echo";
        }

        @Override
        public List<String> getCapabilities() {
            return List.of();
        }

        @Override
        public CompletableFuture<Message> process(Message message) {
            return CompletableFuture.completedFuture(
                    new Message("agent", message.getContent(),
                            new HashMap<>(message.getMetadata()), message.getTimestamp()));
        }

        @Override
        public IntrospectionResult introspect() {
            return new IntrospectionResult("echo", List.of(), null, null, null);
        }
    }

    @Test
    void skillAgentAugmentsMessage(@TempDir Path tmp) throws IOException, ExecutionException, InterruptedException {
        makeSkillDir(tmp, "pdf-processing", "Extract text from PDF documents.");
        SkillRegistry registry = new SkillRegistry(List.of(tmp));
        SkillEnabledAgent agent = new SkillEnabledAgent(new EchoAgent(), registry, 3, true);

        Message msg = Message.of("user", "How do I parse pdf files?");
        Message response = agent.process(msg).get();

        assertThat(response.contentString()).contains("<available_skills>");
        assertThat(response.contentString()).contains("pdf-processing");
    }

    @Test
    void skillAgentNoSkillsPassthrough(@TempDir Path tmp) throws IOException, ExecutionException, InterruptedException {
        makeSkillDir(tmp, "email-compose", "Compose professional emails.");
        SkillRegistry registry = new SkillRegistry(List.of(tmp));
        SkillEnabledAgent agent = new SkillEnabledAgent(new EchoAgent(), registry, 3, true);

        Message msg = Message.of("user", "tell me a joke");
        Message response = agent.process(msg).get();

        assertThat(response.contentString()).doesNotContain("<available_skills>");
        assertThat(response.contentString()).isEqualTo("tell me a joke");
    }

    @Test
    void skillAgentActiveSkillsMetadata(@TempDir Path tmp) throws IOException, ExecutionException, InterruptedException {
        makeSkillDir(tmp, "csv-tools", "Handle and transform CSV spreadsheets.");
        SkillRegistry registry = new SkillRegistry(List.of(tmp));
        SkillEnabledAgent agent = new SkillEnabledAgent(new EchoAgent(), registry, 3, true);

        Message msg = Message.of("user", "parse this csv spreadsheet data");
        Message response = agent.process(msg).get();

        assertThat(response.getMetadata()).containsKey("active_skills");
        @SuppressWarnings("unchecked")
        List<String> active = (List<String>) response.getMetadata().get("active_skills");
        assertThat(active).contains("csv-tools");
    }

    @Test
    void skillAgentCapabilities(@TempDir Path tmp) {
        SkillRegistry registry = new SkillRegistry(List.of(tmp));
        SkillEnabledAgent agent = new SkillEnabledAgent(new EchoAgent(), registry, 3, false);

        assertThat(agent.getCapabilities()).contains("skill_injection");
    }

    @Test
    void skillAgentNameDelegates(@TempDir Path tmp) {
        SkillRegistry registry = new SkillRegistry(List.of(tmp));
        SkillEnabledAgent agent = new SkillEnabledAgent(new EchoAgent(), registry, 3, false);

        assertThat(agent.getName()).isEqualTo("echo");
    }
}
