package io.agenkit.safety;

import io.agenkit.core.Message;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.*;

class SafetyFilterTest {

    @Test
    void inputValidatorAcceptsNormalContent() {
        InputValidator validator = new InputValidator();
        InputValidator.ValidationResult result = validator.validate(Message.of("user", "hello world"));
        assertThat(result.valid()).isTrue();
        assertThat(result.violations()).isEmpty();
    }

    @Test
    void inputValidatorRejectsExceedingMaxLength() {
        InputValidator validator = new InputValidator(10, List.of());
        String longContent = "x".repeat(11);
        InputValidator.ValidationResult result = validator.validate(Message.of("user", longContent));
        assertThat(result.valid()).isFalse();
        assertThat(result.violations()).anyMatch(v -> v.contains("max length"));
    }

    @Test
    void inputValidatorBlocksPatterns() {
        InputValidator validator = new InputValidator(1000, List.of("badword", "forbidden"));
        InputValidator.ValidationResult result =
                validator.validate(Message.of("user", "this contains badword"));
        assertThat(result.valid()).isFalse();
        assertThat(result.violations()).anyMatch(v -> v.contains("badword"));
    }

    @Test
    void inputValidatorCustomRuleTriggered() {
        InputValidator validator = new InputValidator();
        validator.addRule(msg -> !msg.contentString().contains("STOP"));

        InputValidator.ValidationResult result =
                validator.validate(Message.of("user", "please STOP now"));
        assertThat(result.valid()).isFalse();
    }

    @Test
    void outputValidatorRejectsEmptyResponse() {
        OutputValidator validator = new OutputValidator();
        InputValidator.ValidationResult result = validator.validate(Message.of("assistant", ""));
        assertThat(result.valid()).isFalse();
        assertThat(result.violations()).anyMatch(v -> v.contains("empty"));
    }

    @Test
    void outputValidatorAcceptsValidResponse() {
        OutputValidator validator = new OutputValidator();
        InputValidator.ValidationResult result =
                validator.validate(Message.of("assistant", "Here is my answer."));
        assertThat(result.valid()).isTrue();
    }

    @Test
    void permissionCheckerAllowsDefaultPermissions() {
        PermissionChecker checker = new PermissionChecker(Set.of("read", "write"));
        Message msg = Message.of("user", "request");
        assertThat(checker.hasPermission(msg, "read")).isTrue();
        assertThat(checker.hasPermission(msg, "write")).isTrue();
    }

    @Test
    void permissionCheckerDeniesUnknownPermission() {
        PermissionChecker checker = new PermissionChecker(Set.of("read"));
        Message msg = Message.of("user", "request");
        assertThat(checker.hasPermission(msg, "admin")).isFalse();
    }

    @Test
    void permissionCheckerGrantAndRevoke() {
        PermissionChecker checker = new PermissionChecker(Set.of());
        Message msg = Message.of("user", "request").withMetadata("user_id", "alice");
        checker.grantPermission("alice", "special");
        assertThat(checker.check(msg, "special")).isTrue();
        checker.revokePermission("alice", "special");
        assertThat(checker.check(msg, "special")).isFalse();
    }

    @Test
    void auditLoggerRecordsInteractions() {
        AuditLogger logger = new AuditLogger();
        Message input = Message.of("user", "request").withMetadata("user_id", "bob");
        Message output = Message.of("assistant", "response");
        logger.log("my-agent", input, output, true);

        assertThat(logger.getEntries()).hasSize(1);
        assertThat(logger.getEntries().get(0).agentName()).isEqualTo("my-agent");
        assertThat(logger.getEntries().get(0).success()).isTrue();
    }
}
