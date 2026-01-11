/**
 * Implementation of input and output validation for agent security.
 */

#include "agenkit/infrastructure/validation.hpp"

#include <algorithm>
#include <cctype>
#include <iostream>
#include <sstream>

namespace agenkit {
namespace infrastructure {

// ============================================================================
// PromptInjectionDetector
// ============================================================================

std::vector<std::string> PromptInjectionDetector::default_patterns() {
  return {
      "ignore\\s+.*?(previous|all|above|prior).*?instructions?",
      "disregard\\s+.*?(previous|all|above|prior)",
      "forget\\s+.*?(everything|all|previous)",
      "new\\s+instructions?:",
      "system\\s*(prompt|message)?:",
      "you\\s+are\\s+now",
      "act\\s+as\\s+(if|though)",
      "pretend\\s+(you|to)\\s+(are|be)",
      "roleplay\\s+as",
      "^sudo\\s+",
      "admin\\s+mode",
      "developer\\s+mode",
      "god\\s+mode",
      "jailbreak",
      "</?\\s*system\\s*>",
      "<\\|.*?\\|>",  // Special tokens
      "\\[INST\\]",   // Llama-style tokens
      "\\{system\\}",
  };
}

std::unordered_map<std::string, int>
PromptInjectionDetector::default_keywords() {
  return {{"ignore", 3},      {"disregard", 3}, {"override", 2},
          {"bypass", 3},      {"jailbreak", 5}, {"prompt", 2},
          {"injection", 4},   {"system", 2},    {"admin", 2},
          {"root", 2},        {"sudo", 3},      {"privilege", 2},
          {"instructions", 2}};
}

PromptInjectionDetector::PromptInjectionDetector()
    : PromptInjectionDetector(Config{}) {}

PromptInjectionDetector::PromptInjectionDetector(const Config& config)
    : threshold_(config.threshold), suspicious_keywords_(config.keywords) {
  // Use custom patterns if provided, otherwise use defaults
  auto patterns =
      config.patterns.empty() ? default_patterns() : config.patterns;

  // Use custom keywords if provided, otherwise use defaults
  if (suspicious_keywords_.empty()) {
    suspicious_keywords_ = default_keywords();
  }

  // Compile regex patterns
  for (const auto& pattern : patterns) {
    try {
      dangerous_patterns_.emplace_back(
          pattern, std::regex::icase | std::regex::optimize);
    } catch (const std::regex_error& e) {
      std::cerr << "Failed to compile pattern: " << pattern << std::endl;
    }
  }
}

std::tuple<bool, double, std::vector<std::string>>
PromptInjectionDetector::detect(const std::string& text) const {
  std::string text_lower = text;
  std::transform(text_lower.begin(), text_lower.end(), text_lower.begin(),
                 [](unsigned char c) { return std::tolower(c); });

  double score = 0.0;
  std::vector<std::string> matched;

  // Check dangerous patterns
  for (const auto& pattern : dangerous_patterns_) {
    if (std::regex_search(text_lower, pattern)) {
      score += 10.0;
      // Store pattern string (note: can't easily get original pattern string
      // from regex)
      matched.push_back("pattern_match");
    }
  }

  // Check suspicious keywords
  std::istringstream iss(text_lower);
  std::string word;
  while (iss >> word) {
    // Remove punctuation
    word.erase(std::remove_if(word.begin(), word.end(), ::ispunct),
               word.end());
    auto it = suspicious_keywords_.find(word);
    if (it != suspicious_keywords_.end()) {
      score += it->second;
    }
  }

  // Heuristics
  // Multiple special characters (possible encoding/obfuscation)
  size_t special_chars =
      std::count_if(text.begin(), text.end(), [](char c) {
        return c == '<' || c == '>' || c == '{' || c == '}' || c == '[' ||
               c == ']' || c == '|';
      });
  if (special_chars > 5) {
    score += 2.0;
  }

  // Very long prompts (possible payload)
  if (text.length() > 5000) {
    score += 1.0;
  }

  // Repeated instructions
  std::regex instruction_pattern(
      "(please|must|you (should|will|must))", std::regex::icase);
  auto instructions_begin =
      std::sregex_iterator(text.begin(), text.end(), instruction_pattern);
  auto instructions_end = std::sregex_iterator();
  size_t instruction_matches = std::distance(instructions_begin, instructions_end);
  if (instruction_matches > 5) {
    score += 2.0;
  }

  bool is_injection = score >= threshold_;

  return {is_injection, score, matched};
}

bool PromptInjectionDetector::is_safe(const std::string& text) const {
  auto [is_injection, score, matched] = detect(text);
  return !is_injection;
}

// ============================================================================
// ContentFilter
// ============================================================================

ContentFilter::ContentFilter()
    : ContentFilter(Config{}) {}

ContentFilter::ContentFilter(const Config& config)
    : banned_words_(config.banned_words),
      max_size_(config.max_size),
      min_size_(config.min_size) {}

std::pair<bool, std::string> ContentFilter::validate(
    const std::string& content) const {
  // Size checks
  if (content.length() > max_size_) {
    return {false, "Content exceeds maximum size (" +
                       std::to_string(max_size_) + " chars)"};
  }

  if (content.length() < min_size_) {
    return {false, "Content below minimum size (" + std::to_string(min_size_) +
                       " chars)"};
  }

  // Banned words
  std::string content_lower = content;
  std::transform(content_lower.begin(), content_lower.end(),
                 content_lower.begin(),
                 [](unsigned char c) { return std::tolower(c); });

  for (const auto& word : banned_words_) {
    std::string word_lower = word;
    std::transform(word_lower.begin(), word_lower.end(), word_lower.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    if (content_lower.find(word_lower) != std::string::npos) {
      return {false, "Content contains banned word: " + word};
    }
  }

  // Basic PII detection
  if (contains_pii(content)) {
    return {false, "Content may contain PII"};
  }

  return {true, ""};
}

bool ContentFilter::is_safe(const std::string& content) const {
  auto [is_valid, error_msg] = validate(content);
  return is_valid;
}

bool ContentFilter::contains_pii(const std::string& content) const {
  // SSN pattern
  std::regex ssn_pattern(R"(\b\d{3}-\d{2}-\d{4}\b)");
  if (std::regex_search(content, ssn_pattern)) {
    return true;
  }

  // Credit card pattern (16 contiguous digits)
  std::regex cc_pattern(R"(\b\d{16}\b)");
  if (std::regex_search(content, cc_pattern)) {
    return true;
  }

  // Email pattern
  std::regex email_pattern(R"(\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b)",
                           std::regex::icase);
  if (std::regex_search(content, email_pattern)) {
    return true;
  }

  return false;
}

// ============================================================================
// SensitiveDataRedactor
// ============================================================================

std::vector<std::pair<std::regex, std::string>>
SensitiveDataRedactor::default_patterns() {
  return {
      // API keys (common formats)
      {std::regex(R"(sk-[a-zA-Z0-9]{32,})", std::regex::optimize),
       "API_KEY"},
      {std::regex(R"([a-zA-Z0-9_-]{32,})", std::regex::optimize),
       "API_KEY"},
      // AWS credentials
      {std::regex(R"(AKIA[0-9A-Z]{16})", std::regex::optimize),
       "AWS_ACCESS_KEY"},
      // GitHub tokens
      {std::regex(R"(ghp_[a-zA-Z0-9]{36})", std::regex::optimize),
       "GITHUB_TOKEN"},
      // Email addresses
      {std::regex(
           R"(\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b)",
           std::regex::icase | std::regex::optimize),
       "EMAIL"},
      // Phone numbers (US format)
      {std::regex(R"(\b\d{3}[-.]?\d{3}[-.]?\d{4}\b)", std::regex::optimize),
       "PHONE"},
      // SSN
      {std::regex(R"(\b\d{3}-\d{2}-\d{4}\b)", std::regex::optimize),
       "SSN"},
      // Credit card numbers
      {std::regex(R"(\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b)",
                  std::regex::optimize),
       "CREDIT_CARD"},
      // JWT tokens
      {std::regex(R"(eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)",
                  std::regex::optimize),
       "JWT"},
  };
}

SensitiveDataRedactor::SensitiveDataRedactor()
    : SensitiveDataRedactor(Config{}) {}

SensitiveDataRedactor::SensitiveDataRedactor(const Config& config)
    : sensitive_fields_(config.sensitive_fields.empty()
                            ? std::set<std::string>{"password", "api_key",
                                                     "apikey", "token", "secret",
                                                     "auth", "credential",
                                                     "private_key", "access_key"}
                            : config.sensitive_fields),
      redaction_text_(config.redaction_text),
      sensitive_patterns_(default_patterns()) {}

std::string SensitiveDataRedactor::redact(const std::string& text) const {
  std::string redacted = text;

  // Apply pattern-based redaction
  for (const auto& [pattern, data_type] : sensitive_patterns_) {
    redacted = std::regex_replace(redacted, pattern,
                                   redaction_text_ + "_" + data_type);
  }

  return redacted;
}

bool SensitiveDataRedactor::has_sensitive_data(const std::string& text) const {
  // Check patterns
  for (const auto& [pattern, data_type] : sensitive_patterns_) {
    if (std::regex_search(text, pattern)) {
      return true;
    }
  }

  return false;
}

// ============================================================================
// InputValidationMiddleware
// ============================================================================

InputValidationMiddleware::InputValidationMiddleware(
    std::shared_ptr<core::Agent> agent,
    std::shared_ptr<PromptInjectionDetector> detector,
    std::shared_ptr<ContentFilter> filter, bool strict)
    : agent_(agent),
      detector_(detector ? detector
                         : std::make_shared<PromptInjectionDetector>()),
      filter_(filter ? filter : std::make_shared<ContentFilter>()),
      strict_(strict) {}

std::string InputValidationMiddleware::name() const { return agent_->name(); }

std::future<core::Result<core::Message, core::AgentError>>
InputValidationMiddleware::process(core::Message message) {
  return std::async(std::launch::async, [this, message]() mutable {
    // Validate message content
    std::string content_str = message.content();

    // 1. Check for prompt injection
    auto [is_injection, score, matched] = detector_->detect(content_str);
    if (is_injection) {
      std::string error_msg = "Potential prompt injection detected (score: " +
                              std::to_string(score) +
                              ", patterns: " + std::to_string(matched.size()) +
                              ")";

      if (strict_) {
        return core::Result<core::Message, core::AgentError>::err(
            core::AgentError(core::AgentErrorType::InvalidInput, error_msg));
      }

      std::cerr << "WARNING: " << error_msg << std::endl;
    }

    // 2. Check content filter
    auto [is_valid, error_msg] = filter_->validate(content_str);
    if (!is_valid) {
      if (strict_) {
        return core::Result<core::Message, core::AgentError>::err(
            core::AgentError(core::AgentErrorType::InvalidInput,
                             "Content validation failed: " + error_msg));
      }
      std::cerr << "WARNING: Content validation failed: " << error_msg
                << std::endl;
    }

    // 3. Process with wrapped agent
    return agent_->process(std::move(message)).get();
  });
}

// ============================================================================
// OutputValidationMiddleware
// ============================================================================

OutputValidationMiddleware::OutputValidationMiddleware(
    std::shared_ptr<core::Agent> agent,
    std::shared_ptr<SensitiveDataRedactor> redactor, bool auto_redact,
    size_t max_size)
    : agent_(agent),
      redactor_(redactor ? redactor
                         : std::make_shared<SensitiveDataRedactor>()),
      auto_redact_(auto_redact),
      max_size_(max_size) {}

std::string OutputValidationMiddleware::name() const { return agent_->name(); }

std::future<core::Result<core::Message, core::AgentError>>
OutputValidationMiddleware::process(core::Message message) {
  return std::async(std::launch::async, [this, message]() mutable {
    // Process with wrapped agent
    auto result = agent_->process(std::move(message)).get();

    if (result.is_err()) {
      return result;
    }

    auto response = result.unwrap();

    // 1. Check output size
    std::string content_str = response.content();
    if (content_str.length() > max_size_) {
      return core::Result<core::Message, core::AgentError>::err(
          core::AgentError(core::AgentErrorType::ProcessingError,
                           "Output exceeds maximum size (" +
                               std::to_string(max_size_) + " chars)"));
    }

    // 2. Auto-redact sensitive data
    if (auto_redact_) {
      std::string redacted_content = redactor_->redact(content_str);

      if (redacted_content != content_str) {
        std::cerr
            << "WARNING: Output may contain sensitive data (has been redacted)"
            << std::endl;

        // Create new message with redacted content
        core::Message redacted_message(response.role(), redacted_content);

        // Copy metadata from original message
        for (auto& [key, value] : response.metadata().items()) {
          redacted_message.with_metadata(key, value);
        }

        response = std::move(redacted_message);
      }
    }

    return core::Result<core::Message, core::AgentError>::ok(response);
  });
}

}  // namespace infrastructure
}  // namespace agenkit
