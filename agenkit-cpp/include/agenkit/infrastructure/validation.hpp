/**
 * Input and output validation for agent security.
 *
 * Provides protection against:
 * - Prompt injection attacks
 * - Malicious inputs
 * - Sensitive data leakage
 * - Content policy violations
 */

#pragma once

#include <algorithm>
#include <future>
#include <memory>
#include <regex>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

#include "agenkit/core/agent.hpp"
#include "agenkit/core/errors.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"

namespace agenkit {
namespace infrastructure {

/**
 * Detects potential prompt injection attempts.
 *
 * Uses pattern matching and heuristics to identify common prompt injection
 * techniques like instruction overrides, jailbreaks, and system prompts.
 */
class PromptInjectionDetector {
 public:
  /**
   * Configuration for prompt injection detection.
   */
  struct Config {
    double threshold = 8.0;  // Score threshold for blocking (0-100)
    std::vector<std::string> patterns;
    std::unordered_map<std::string, int> keywords;
  };

  PromptInjectionDetector();
  explicit PromptInjectionDetector(const Config& config);

  /**
   * Detect prompt injection attempts.
   *
   * @param text Input text to analyze
   * @return tuple of (is_injection, score, matched_patterns)
   */
  std::tuple<bool, double, std::vector<std::string>> detect(
      const std::string& text) const;

  /**
   * Check if text is safe (no injection detected).
   */
  bool is_safe(const std::string& text) const;

 private:
  double threshold_;
  std::vector<std::regex> dangerous_patterns_;
  std::unordered_map<std::string, int> suspicious_keywords_;

  static std::vector<std::string> default_patterns();
  static std::unordered_map<std::string, int> default_keywords();
};

/**
 * Filters content based on policies.
 *
 * Supports:
 * - Banned words/phrases
 * - PII detection (basic)
 * - Size limits
 */
class ContentFilter {
 public:
  /**
   * Configuration for content filtering.
   */
  struct Config {
    std::set<std::string> banned_words;
    size_t max_size = 10000;
    size_t min_size = 1;
  };

  ContentFilter();
  explicit ContentFilter(const Config& config);

  /**
   * Validate content against policies.
   *
   * @param content Content to validate
   * @return tuple of (is_valid, error_message)
   */
  std::pair<bool, std::string> validate(const std::string& content) const;

  /**
   * Check if content is safe.
   */
  bool is_safe(const std::string& content) const;

 private:
  std::set<std::string> banned_words_;
  size_t max_size_;
  size_t min_size_;

  bool contains_pii(const std::string& content) const;
};

/**
 * Redacts sensitive data from outputs.
 *
 * Detects and redacts:
 * - API keys
 * - Passwords
 * - Tokens
 * - PII (email, phone, SSN, credit cards)
 */
class SensitiveDataRedactor {
 public:
  /**
   * Configuration for data redaction.
   */
  struct Config {
    std::set<std::string> sensitive_fields;
    std::string redaction_text = "[REDACTED]";
  };

  SensitiveDataRedactor();
  explicit SensitiveDataRedactor(const Config& config);

  /**
   * Redact sensitive data from text.
   */
  std::string redact(const std::string& text) const;

  /**
   * Check if text contains sensitive data.
   */
  bool has_sensitive_data(const std::string& text) const;

 private:
  std::set<std::string> sensitive_fields_;
  std::string redaction_text_;
  std::vector<std::pair<std::regex, std::string>> sensitive_patterns_;

  static std::vector<std::pair<std::regex, std::string>>
  default_patterns();
};

/**
 * Middleware for input validation and prompt injection defense.
 *
 * Wraps an agent to validate inputs before processing.
 */
class InputValidationMiddleware : public core::Agent {
 public:
  /**
   * Create input validation middleware.
   *
   * @param agent Agent to wrap
   * @param detector Prompt injection detector (optional)
   * @param filter Content filter (optional)
   * @param strict Strict mode (throws on violation)
   */
  InputValidationMiddleware(
      std::shared_ptr<core::Agent> agent,
      std::shared_ptr<PromptInjectionDetector> detector = nullptr,
      std::shared_ptr<ContentFilter> filter = nullptr, bool strict = true);

  std::string name() const override;
  std::future<core::Result<core::Message, core::AgentError>> process(
      core::Message message) override;

 private:
  std::shared_ptr<core::Agent> agent_;
  std::shared_ptr<PromptInjectionDetector> detector_;
  std::shared_ptr<ContentFilter> filter_;
  bool strict_;
};

/**
 * Middleware for output validation and sensitive data redaction.
 *
 * Wraps an agent to validate and redact outputs after processing.
 */
class OutputValidationMiddleware : public core::Agent {
 public:
  /**
   * Create output validation middleware.
   *
   * @param agent Agent to wrap
   * @param redactor Sensitive data redactor (optional)
   * @param auto_redact Automatically redact sensitive data
   * @param max_size Maximum output size
   */
  OutputValidationMiddleware(
      std::shared_ptr<core::Agent> agent,
      std::shared_ptr<SensitiveDataRedactor> redactor = nullptr,
      bool auto_redact = true, size_t max_size = 100000);

  std::string name() const override;
  std::future<core::Result<core::Message, core::AgentError>> process(
      core::Message message) override;

 private:
  std::shared_ptr<core::Agent> agent_;
  std::shared_ptr<SensitiveDataRedactor> redactor_;
  bool auto_redact_;
  size_t max_size_;
};

}  // namespace infrastructure
}  // namespace agenkit
