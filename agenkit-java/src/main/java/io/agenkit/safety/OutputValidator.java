package io.agenkit.safety;

import io.agenkit.core.Message;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Predicate;

/**
 * Validates agent responses before they are returned to callers.
 */
public final class OutputValidator {

    private final int maxContentLength;
    private final List<String> requiredPatterns;
    private final List<Predicate<Message>> customRules;

    public OutputValidator(int maxContentLength, List<String> requiredPatterns) {
        this.maxContentLength = maxContentLength;
        this.requiredPatterns = List.copyOf(requiredPatterns);
        this.customRules = new ArrayList<>();
    }

    public OutputValidator() {
        this(50000, List.of());
    }

    public OutputValidator addRule(Predicate<Message> rule) {
        customRules.add(rule);
        return this;
    }

    public InputValidator.ValidationResult validate(Message message) {
        List<String> violations = new ArrayList<>();

        if (message.contentString().isEmpty()) {
            violations.add("empty response");
        }

        if (message.contentString().length() > maxContentLength) {
            violations.add("response exceeds max length of " + maxContentLength);
        }

        for (String pattern : requiredPatterns) {
            if (!message.contentString().toLowerCase().contains(pattern.toLowerCase())) {
                violations.add("required pattern missing: " + pattern);
            }
        }

        for (Predicate<Message> rule : customRules) {
            if (!rule.test(message)) {
                violations.add("custom rule failed");
            }
        }

        return violations.isEmpty()
                ? InputValidator.ValidationResult.ok()
                : InputValidator.ValidationResult.fail(violations);
    }
}
