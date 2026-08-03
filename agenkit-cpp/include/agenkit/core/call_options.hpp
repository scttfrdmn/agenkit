/**
 * @file call_options.hpp
 * @brief Per-call LLM options and the optional OptionsAgent capability
 *
 * Mirrors Python's `agenkit.CallOptions`, Go's `agenkit.CallOptions`,
 * TypeScript's `CallOptions` and Rust's `agenkit::core::CallOptions`.
 *
 * The core Agent contract stays `name()` plus `process(message)`. Agents that
 * can honour per-call options additionally derive from OptionsAgent; the check
 * is a `dynamic_cast`, so the capability is a real property of the type rather
 * than something an agent declares about itself.
 */

#ifndef AGENKIT_CORE_CALL_OPTIONS_HPP
#define AGENKIT_CORE_CALL_OPTIONS_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/errors.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include <future>
#include <memory>
#include <nlohmann/json.hpp>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace agenkit {
namespace core {

/**
 * @brief Per-call LLM sampling options
 *
 * Every field is optional. `std::nullopt` means "unset", never a default: an
 * option the caller never set must not override the agent's or the provider's
 * own configuration. In particular `temperature = 0.0` (greedy decoding) is a
 * real request and is forwarded, while an unset temperature is omitted rather
 * than sent as 0.
 *
 * Field names and bounds match agenkit::adapters::LLMParameterValidator, so
 * options reach an adapter without translation.
 *
 * @example
 * @code
 * auto options = CallOptions{}.with_temperature(0.8).with_max_tokens(512);
 * auto result = process_with_options(agent, message, options).get();
 * @endcode
 */
struct CallOptions {
    /** Sampling temperature, 0.0-2.0 */
    std::optional<double> temperature;

    /** Maximum tokens to generate, must be positive */
    std::optional<int> max_tokens;

    /** Nucleus sampling threshold, 0.0-1.0 */
    std::optional<double> top_p;

    /** Random seed for reproducible sampling */
    std::optional<uint64_t> seed;

    /** Stop sequences */
    std::optional<std::vector<std::string>> stop;

    /** Provider-specific options that have no first-class field */
    nlohmann::json extra = nlohmann::json::object();

    /**
     * @brief Validate every set field
     *
     * The fields are public and the struct is aggregate-initializable, so the
     * builders below can be bypassed entirely. This is therefore the only
     * guard on that path, and callers that accept a CallOptions from outside
     * should invoke it.
     *
     * @throws std::invalid_argument if any set field is out of range
     */
    void validate() const;

    /**
     * @brief Whether no option is set
     *
     * Used to keep an agent that only implements `process` off a path that
     * would hand it an empty option set for no reason.
     */
    bool empty() const;

    /**
     * @brief Set fields as a JSON object, using the provider wire names
     *
     * Unset fields are omitted rather than emitted as null, so a provider
     * cannot mistake "not requested" for "requested as zero".
     */
    nlohmann::json to_params() const;

    /**
     * @brief Overlay `overrides` on a copy of this, field by field
     *
     * Merged field by field rather than by replacing the struct: an unset
     * field in `overrides` means "did not ask", not "clear it". A caller
     * forwarding an optional variable produces exactly that shape, and
     * wholesale replacement would silently erase the base value.
     */
    CallOptions merge(const CallOptions& overrides) const;

    /** @brief Copy with temperature set. @throws std::invalid_argument if out of range */
    CallOptions with_temperature(double value) const;

    /** @brief Copy with max_tokens set. @throws std::invalid_argument if not positive */
    CallOptions with_max_tokens(int value) const;

    /** @brief Copy with top_p set. @throws std::invalid_argument if out of range */
    CallOptions with_top_p(double value) const;

    /** @brief Copy with seed set */
    CallOptions with_seed(uint64_t value) const;

    /** @brief Copy with stop sequences set */
    CallOptions with_stop(std::vector<std::string> value) const;

    /** @brief Copy with one provider-specific key set */
    CallOptions with_extra(const std::string& key, nlohmann::json value) const;
};

/**
 * @brief Optional capability: an Agent that honours per-call options
 *
 * Additive to Agent. Existing agents keep working untouched — the required
 * contract is still `name()` plus `process()`. An agent that can pass options
 * down to an LLM derives from this as well, the same way the streaming
 * capability extends the base interface.
 *
 * `process_with` defaults to ignoring the options and delegating to
 * `process()`, so a partial implementation degrades to current behaviour
 * rather than failing.
 *
 * @example
 * @code
 * class MyAgent : public core::Agent, public core::OptionsAgent {
 * public:
 *     std::future<core::Result<core::Message, core::AgentError>>
 *     process(core::Message m) override { return process_with(std::move(m), {}); }
 *
 *     std::future<core::Result<core::Message, core::AgentError>>
 *     process_with(core::Message m, const core::CallOptions& options) override {
 *         // forward options to the LLM
 *     }
 * };
 * @endcode
 */
class OptionsAgent {
public:
    virtual ~OptionsAgent() = default;

    /**
     * @brief Process a message, honouring the given per-call options
     * @param message Input message
     * @param options Per-call options; may be empty
     * @return Future containing Result<Message, AgentError>
     */
    virtual std::future<Result<Message, AgentError>>
    process_with(Message message, const CallOptions& options) = 0;
};

/**
 * @brief Whether this agent honours per-call options
 *
 * A `dynamic_cast`, so this reports what the type actually implements. An
 * agent cannot advertise the capability without providing it, and cannot
 * provide it without being detected — which a hand-maintained boolean flag
 * could not guarantee in either direction.
 *
 * @param agent Agent to check (may be null)
 * @return true if the agent derives from OptionsAgent
 */
bool supports_options(Agent* agent);

/**
 * @brief Process a message with options, falling back to plain process()
 *
 * The capability check is spelled once here rather than re-derived at each
 * wrapper call site. An empty option set takes the plain `process` path, so an
 * OptionsAgent is never handed an empty CallOptions just because this helper
 * was used.
 *
 * @param agent Agent to call
 * @param message Input message
 * @param options Per-call options; if empty, `process()` is called
 * @return Future containing Result<Message, AgentError>
 */
std::future<Result<Message, AgentError>>
process_with_options(Agent* agent, Message message, const CallOptions& options);

/**
 * @brief shared_ptr convenience overload of process_with_options
 */
std::future<Result<Message, AgentError>>
process_with_options(
    const std::shared_ptr<Agent>& agent,
    Message message,
    const CallOptions& options
);

} // namespace core
} // namespace agenkit

#endif // AGENKIT_CORE_CALL_OPTIONS_HPP
