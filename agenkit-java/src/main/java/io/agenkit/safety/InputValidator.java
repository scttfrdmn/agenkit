package io.agenkit.safety;

import io.agenkit.core.Message;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Predicate;

/**
 * Validates messages before they are processed by an agent.
 */
public final class InputValidator {

    public record ValidationResult(boolean valid, List<String> violations) {
        public static ValidationResult ok() {
            return new ValidationResult(true, List.of());
        }
        public static ValidationResult fail(List<String> violations) {
            return new ValidationResult(false, violations);
        }
    }

    private final int maxContentLength;
    private final List<String> blockedPatterns;
    private final List<Predicate<Message>> customRules;

    public InputValidator(int maxContentLength, List<String> blockedPatterns) {
        this.maxContentLength = maxContentLength;
        this.blockedPatterns = List.copyOf(blockedPatterns);
        this.customRules = new ArrayList<>();
    }

    public InputValidator() {
        this(10000, List.of());
    }

    public InputValidator addRule(Predicate<Message> rule) {
        customRules.add(rule);
        return this;
    }

    public ValidationResult validate(Message message) {
        List<String> violations = new ArrayList<>();

        if (message.contentString().length() > maxContentLength) {
            violations.add("content exceeds max length of " + maxContentLength);
        }

        String lower = message.contentString().toLowerCase();
        for (String pattern : blockedPatterns) {
            if (lower.contains(pattern.toLowerCase())) {
                violations.add("blocked pattern found: " + pattern);
            }
        }

        for (Predicate<Message> rule : customRules) {
            if (!rule.test(message)) {
                violations.add("custom rule failed");
            }
        }

        return violations.isEmpty()
                ? ValidationResult.ok()
                : ValidationResult.fail(violations);
    }
}
