/**
 * @file sse_parser.hpp
 * @brief Header-only SSE (Server-Sent Events) and NDJSON stream parser
 *
 * Shared utility for parsing streaming responses from LLM provider APIs.
 * Supports both SSE format (Claude/Anthropic) and NDJSON format (OpenAI,
 * Gemini, Ollama).
 *
 * Usage (SSE / Claude):
 * @code
 * SseParser parser;
 * // content_receiver callback feeds raw bytes from httplib
 * auto fire = [&](const char* data, size_t len) -> bool {
 *     return parser.feed(data, len, SseParser::Mode::SSE, [&](const std::string& json_str) {
 *         // process one complete JSON payload
 *         return true; // return false to abort
 *     });
 * };
 * @endcode
 *
 * Usage (NDJSON / OpenAI, Ollama, Gemini):
 * @code
 * SseParser parser;
 * auto fire = [&](const char* data, size_t len) -> bool {
 *     return parser.feed(data, len, SseParser::Mode::NDJSON, [&](const std::string& json_str) {
 *         // process one complete JSON line
 *         return true;
 *     });
 * };
 * @endcode
 */

#ifndef AGENKIT_CORE_SSE_PARSER_HPP
#define AGENKIT_CORE_SSE_PARSER_HPP

#include <string>
#include <functional>

namespace agenkit {
namespace core {

/**
 * @brief Streaming parser for SSE and NDJSON response bodies
 *
 * Buffers partial data and fires EventCallback once per complete JSON payload.
 * Thread-safe to use from a single httplib content-receiver callback.
 */
class SseParser {
public:
    /**
     * @brief Parsing mode selector
     */
    enum class Mode {
        /// SSE: extract JSON from "data: <payload>" lines; stop on "[DONE]"
        SSE,
        /// NDJSON: each non-empty line is a complete JSON object
        NDJSON
    };

    /**
     * @brief Callback fired for each complete JSON payload.
     * @return true to continue streaming; false to abort.
     */
    using EventCallback = std::function<bool(const std::string& json_payload)>;

    SseParser() = default;

    /**
     * @brief Feed a raw chunk of bytes into the parser.
     *
     * Accumulates bytes in an internal buffer, splits on newlines, and fires
     * @p on_event for each complete payload.  The "[DONE]" SSE sentinel
     * terminates the stream (returns false).
     *
     * @param data  Pointer to the incoming byte buffer.
     * @param len   Number of bytes in @p data.
     * @param mode  Parsing mode (SSE or NDJSON).
     * @param on_event Callback invoked per complete JSON payload.
     * @return true to continue receiving data; false to stop.
     */
    bool feed(const char* data, size_t len, Mode mode, EventCallback on_event) {
        buffer_.append(data, len);

        std::string::size_type pos = 0;
        while (true) {
            auto nl = buffer_.find('\n', pos);
            if (nl == std::string::npos) {
                break;
            }

            // Extract the line (strip trailing \r if present)
            std::string line = buffer_.substr(pos, nl - pos);
            if (!line.empty() && line.back() == '\r') {
                line.pop_back();
            }
            pos = nl + 1;

            if (line.empty()) {
                continue; // blank line — SSE event separator, skip
            }

            std::string json_str;

            if (mode == Mode::SSE) {
                // SSE format: lines begin with "data: "
                if (line.rfind("data: ", 0) != 0) {
                    continue; // skip comment / event / id lines
                }
                json_str = line.substr(6); // strip "data: "
                if (json_str == "[DONE]") {
                    buffer_.erase(0, pos);
                    return false; // stream ended
                }
            } else {
                // NDJSON: the line itself is the JSON payload
                json_str = line;
            }

            if (!json_str.empty()) {
                if (!on_event(json_str)) {
                    buffer_.erase(0, pos);
                    return false; // caller requested abort
                }
            }
        }

        // Keep only the unprocessed tail
        buffer_.erase(0, pos);
        return true;
    }

    /// Reset the internal buffer (call between requests if reusing the parser).
    void reset() { buffer_.clear(); }

private:
    std::string buffer_;
};

} // namespace core
} // namespace agenkit

#endif // AGENKIT_CORE_SSE_PARSER_HPP
