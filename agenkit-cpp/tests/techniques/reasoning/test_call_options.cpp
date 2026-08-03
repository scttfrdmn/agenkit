/**
 * @file test_call_options.cpp
 * @brief Tests that per-call options reach the LLM from every reasoning technique
 *
 * These tests assert on the path each call *arrived by* and on the temperature
 * the wrapped agent actually received — not on the returned message. A phase
 * that drops its options still produces a perfectly good response, so the entry
 * path is the only thing that distinguishes a working forward from a broken one.
 *
 * Each gated phase additionally asserts that it actually ran. Without that,
 * "every call carried the temperature" is trivially true for a phase that never
 * executes, and the test passes against a deliberately broken forward.
 */

#include <gtest/gtest.h>

#include "agenkit/core/agent.hpp"
#include "agenkit/core/call_options.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/techniques/reasoning/chain_of_thought.hpp"
#include "agenkit/techniques/reasoning/graph_of_thought.hpp"
#include "agenkit/techniques/reasoning/least_to_most.hpp"
#include "agenkit/techniques/reasoning/plan_and_solve.hpp"
#include "agenkit/techniques/reasoning/self_consistency.hpp"
#include "agenkit/techniques/reasoning/tree_of_thought.hpp"

#include <functional>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <vector>

using namespace agenkit::core;
using namespace agenkit::techniques::reasoning;

namespace {

/** Chooses a canned reply based on the prompt it is given. */
using Responder = std::function<std::string(const std::string&)>;

/**
 * @brief Agent that records how it was called
 *
 * Implements both Agent and OptionsAgent, and records which of the two paths
 * each call arrived by, plus the options it received. A technique that forgets
 * to forward its options still gets a response — it just lands on the plain
 * path, which is what these tests detect.
 */
class RecordingAgent : public Agent, public OptionsAgent {
public:
    explicit RecordingAgent(Responder responder)
        : responder_(std::move(responder)) {}

    std::string name() const override { return "recording"; }

    std::future<Result<Message, AgentError>> process(Message message) override {
        return record(std::move(message), std::nullopt);
    }

    std::future<Result<Message, AgentError>>
    process_with(Message message, const CallOptions& options) override {
        return record(std::move(message), options);
    }

    size_t plain_calls() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return plain_calls_;
    }

    size_t option_calls() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return option_calls_;
    }

    std::vector<std::string> prompts() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return prompts_;
    }

    /** The temperature seen on each call, in arrival order. */
    std::vector<std::optional<double>> temperatures() const {
        std::lock_guard<std::mutex> lock(mutex_);
        std::vector<std::optional<double>> result;
        result.reserve(seen_.size());
        for (const auto& options : seen_) {
            result.push_back(options.has_value() ? options->temperature : std::nullopt);
        }
        return result;
    }

    std::vector<std::optional<CallOptions>> seen() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return seen_;
    }

    /**
     * @brief Assert every call carried exactly this temperature
     *
     * The "was ever called" check is the point: a phase that never runs makes
     * an all-calls assertion vacuously true.
     */
    void assert_every_call_carried_temperature(double want) const {
        auto seen_temperatures = temperatures();
        ASSERT_FALSE(seen_temperatures.empty())
            << "the agent was never called; the test proves nothing";
        EXPECT_EQ(plain_calls(), 0u)
            << "some call took the plain path and dropped its options";
        for (size_t i = 0; i < seen_temperatures.size(); ++i) {
            ASSERT_TRUE(seen_temperatures[i].has_value())
                << "call " << i << " carried no temperature";
            EXPECT_DOUBLE_EQ(seen_temperatures[i].value(), want)
                << "call " << i << " carried the wrong temperature";
        }
    }

private:
    std::future<Result<Message, AgentError>>
    record(Message message, std::optional<CallOptions> options) {
        std::string prompt = message.content_as_str();
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (options.has_value()) {
                ++option_calls_;
            } else {
                ++plain_calls_;
            }
            prompts_.push_back(prompt);
            seen_.push_back(std::move(options));
        }
        return make_ready_future(Result<Message, AgentError>::ok(
            Message::with_text("assistant", responder_(prompt))
        ));
    }

    Responder responder_;
    mutable std::mutex mutex_;
    size_t plain_calls_ = 0;
    size_t option_calls_ = 0;
    std::vector<std::string> prompts_;
    std::vector<std::optional<CallOptions>> seen_;
};

/**
 * @brief Agent with no options capability
 *
 * Deliberately does NOT derive from OptionsAgent, so it stands in for the
 * majority of agents that will never honour per-call options.
 */
class PlainAgent : public Agent {
public:
    explicit PlainAgent(std::string reply = "Therefore, 42")
        : reply_(std::move(reply)) {}

    std::string name() const override { return "plain"; }

    std::future<Result<Message, AgentError>> process(Message message) override {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            ++calls_;
        }
        (void)message;
        return make_ready_future(Result<Message, AgentError>::ok(
            Message::with_text("assistant", reply_)
        ));
    }

    size_t calls() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return calls_;
    }

private:
    std::string reply_;
    mutable std::mutex mutex_;
    size_t calls_ = 0;
};

bool contains(const std::string& haystack, const std::string& needle) {
    return haystack.find(needle) != std::string::npos;
}

/** Responds to whatever any technique asks, so one double serves all six. */
Responder everything_responder() {
    // Mutable state is intentional: Graph-of-Thought's thought-expansion loop
    // only stops when a round yields nothing, and Plan-and-Solve's replanning
    // branch needs the second plan to differ from the first.
    auto thought_rounds = std::make_shared<int>(0);

    return [thought_rounds](const std::string& prompt) -> std::string {
        if (contains(prompt, "Premises:")) {
            return "Fact one\nFact two";
        }
        if (contains(prompt, "thoughts (one per line)")
            || contains(prompt, "Thoughts (one per line)")) {
            // Second round returns nothing usable, which ends the expansion loop
            // below the node cap — the only way the conclusion phase runs at all.
            if ((*thought_rounds)++ == 0) {
                return "Insight one\nInsight two";
            }
            return "#";
        }
        if (contains(prompt, "SUPPORT, DEPEND")) {
            return "NO_RELATION";
        }
        if (contains(prompt, "Final conclusion:")) {
            return "Therefore, 42";
        }
        if (contains(prompt, "Subproblems (from simplest")) {
            return "1. Sub one\n2. Sub two";
        }
        if (contains(prompt, "Solution Plan:")) {
            return "1. First step\n2. Second step";
        }
        if (contains(prompt, "Validation (answer")) {
            return "INVALID: the plan omits verification";
        }
        return "1. Decompose the problem into independent parts.\n"
               "2. Recombine the partial results. Therefore, 42";
    };
}

Message user(const std::string& text) {
    return Message::with_text("user", text);
}

/**
 * The branch text has to survive Tree-of-Thought's 0.3 prune threshold. Length
 * alone does not get there — 137 characters scores 137/500 = 0.274 — so the text
 * also needs the +0.2 structure bonus, which requires two numbered markers each
 * at the START OF A LINE, because default_evaluator's regex is multiline
 * anchored. A single-line "1. ... 2. ..." matches once, scores below the
 * threshold, and every depth-1 branch is pruned — leaving only the root expanded
 * and the recursive expansion, where a dropped forward would actually hide,
 * untested.
 */
const char* const kSurvivesPruning =
    "1. Decompose the problem into independent parts.\n"
    "2. Recombine the partial results. Therefore, 42";

} // namespace

// ---------------------------------------------------------------------------
// Capability advertisement
// ---------------------------------------------------------------------------

TEST(CallOptionsCapability, EveryReasoningTechniqueAdvertisesTheCapability) {
    auto base = std::make_shared<RecordingAgent>(everything_responder());

    ChainOfThoughtAgent cot(base);
    LeastToMostAgent ltm(base);
    TreeOfThoughtAgent tot(base);
    PlanAndSolveAgent pas(base);
    GraphOfThoughtAgent got(base, GraphOfThoughtConfig{});
    SelfConsistencyAgent sc(base);

    EXPECT_TRUE(supports_options(&cot));
    EXPECT_TRUE(supports_options(&ltm));
    EXPECT_TRUE(supports_options(&tot));
    EXPECT_TRUE(supports_options(&pas));
    EXPECT_TRUE(supports_options(&got));
    EXPECT_TRUE(supports_options(&sc));
}

TEST(CallOptionsCapability, APlainAgentDoesNotAdvertiseTheCapability) {
    PlainAgent plain;
    EXPECT_FALSE(supports_options(&plain));
}

TEST(CallOptionsCapability, ANullAgentDoesNotAdvertiseTheCapability) {
    EXPECT_FALSE(supports_options(nullptr));
}

// ---------------------------------------------------------------------------
// Self-Consistency: the technique the issue is about
// ---------------------------------------------------------------------------

TEST(SelfConsistencyOptions, ForwardsConfiguredTemperatureToEverySample) {
    auto base = std::make_shared<RecordingAgent>(everything_responder());
    SelfConsistencyConfig config;
    config.num_samples = 4;
    config.temperature = 0.9;

    SelfConsistencyAgent sc(base, config);
    auto result = sc.process(user("What is 6 * 7?")).get();
    ASSERT_TRUE(result.is_ok());

    EXPECT_EQ(base->option_calls(), 4u);
    base->assert_every_call_carried_temperature(0.9);
}

TEST(SelfConsistencyOptions, TreatsATemperatureOfZeroAsSet) {
    auto base = std::make_shared<RecordingAgent>(everything_responder());
    SelfConsistencyConfig config;
    config.num_samples = 2;
    config.temperature = 0.0;

    SelfConsistencyAgent sc(base, config);
    auto result = sc.process(user("Question")).get();
    ASSERT_TRUE(result.is_ok());

    // 0.0 is greedy decoding — a real request, not an absent one.
    base->assert_every_call_carried_temperature(0.0);
    EXPECT_EQ(result.unwrap().metadata()["temperature"], 0.0);
    EXPECT_TRUE(result.unwrap().metadata()["temperature_applied"].get<bool>());
}

TEST(SelfConsistencyOptions, SendsNoOptionsWhenNoTemperatureIsConfigured) {
    auto base = std::make_shared<RecordingAgent>(everything_responder());
    SelfConsistencyConfig config;
    config.num_samples = 3;

    SelfConsistencyAgent sc(base, config);
    auto result = sc.process(user("Question")).get();
    ASSERT_TRUE(result.is_ok());

    // An unset temperature must be omitted, not sent as 0: forwarding 0 would
    // pin every sample to greedy decoding and defeat the technique.
    EXPECT_EQ(base->option_calls(), 0u);
    EXPECT_EQ(base->plain_calls(), 3u);
    EXPECT_TRUE(result.unwrap().metadata()["temperature"].is_null());
    EXPECT_TRUE(result.unwrap().metadata()["temperature_applied"].get<bool>());
}

TEST(SelfConsistencyOptions, ReportsTemperatureNotAppliedForAPlainAgent) {
    auto plain = std::make_shared<PlainAgent>();
    SelfConsistencyConfig config;
    config.num_samples = 2;
    config.temperature = 0.8;

    SelfConsistencyAgent sc(plain, config);
    EXPECT_FALSE(sc.temperature_applied());

    auto result = sc.process(user("Question")).get();
    ASSERT_TRUE(result.is_ok());
    auto metadata = result.unwrap().metadata();

    // The temperature is still reported, so "asked for 0.8 and did not get it"
    // stays distinguishable from "never asked".
    EXPECT_DOUBLE_EQ(metadata["temperature"].get<double>(), 0.8);
    EXPECT_FALSE(metadata["temperature_applied"].get<bool>());
    EXPECT_EQ(plain->calls(), 2u);
}

TEST(SelfConsistencyOptions, ReportsTemperatureAppliedWhenNoneIsConfigured) {
    auto plain = std::make_shared<PlainAgent>();
    SelfConsistencyAgent sc(plain);

    // Nothing was requested, so nothing was dropped.
    EXPECT_TRUE(sc.temperature_applied());
}

TEST(SelfConsistencyOptions, RejectsANegativeTemperature) {
    auto base = std::make_shared<RecordingAgent>(everything_responder());
    SelfConsistencyConfig config;
    config.temperature = -0.1;

    EXPECT_THROW(SelfConsistencyAgent(base, config), std::invalid_argument);
}

TEST(SelfConsistencyOptions, RejectsATemperatureAboveTheRange) {
    auto base = std::make_shared<RecordingAgent>(everything_responder());
    SelfConsistencyConfig config;
    config.temperature = 2.5;

    EXPECT_THROW(SelfConsistencyAgent(base, config), std::invalid_argument);
}

TEST(SelfConsistencyOptions, ItsOwnTemperatureOverridesTheCallers) {
    auto base = std::make_shared<RecordingAgent>(everything_responder());
    SelfConsistencyConfig config;
    config.num_samples = 2;
    config.temperature = 0.9;

    SelfConsistencyAgent sc(base, config);
    auto options = CallOptions{}.with_temperature(0.1).with_max_tokens(256);
    auto result = sc.process_with(user("Question"), options).get();
    ASSERT_TRUE(result.is_ok());

    // Sampling diversity is what makes the technique correct, so the caller
    // cannot flatten it — but every other option the caller set survives.
    base->assert_every_call_carried_temperature(0.9);
    for (const auto& seen : base->seen()) {
        ASSERT_TRUE(seen.has_value());
        ASSERT_TRUE(seen->max_tokens.has_value());
        EXPECT_EQ(seen->max_tokens.value(), 256);
    }
}

TEST(SelfConsistencyOptions, KeepsItsOwnTemperatureWhenTheCallerSetsNone) {
    auto base = std::make_shared<RecordingAgent>(everything_responder());
    SelfConsistencyConfig config;
    config.num_samples = 2;
    config.temperature = 0.7;

    SelfConsistencyAgent sc(base, config);
    auto options = CallOptions{}.with_max_tokens(128);
    auto result = sc.process_with(user("Question"), options).get();
    ASSERT_TRUE(result.is_ok());

    // An unset temperature in the caller's options means "did not ask", not
    // "clear it" — a merge by replacement would erase the configured value.
    base->assert_every_call_carried_temperature(0.7);
    for (const auto& seen : base->seen()) {
        ASSERT_TRUE(seen.has_value());
        ASSERT_TRUE(seen->max_tokens.has_value());
        EXPECT_EQ(seen->max_tokens.value(), 128);
    }
}

TEST(SelfConsistencyOptions, ForwardsThroughAChainOfThought) {
    auto base = std::make_shared<RecordingAgent>(everything_responder());
    auto cot = std::make_shared<ChainOfThoughtAgent>(base);

    SelfConsistencyConfig config;
    config.num_samples = 3;
    config.temperature = 0.6;

    SelfConsistencyAgent sc(cot, config);
    EXPECT_TRUE(sc.temperature_applied());

    auto result = sc.process(user("What is 6 * 7?")).get();
    ASSERT_TRUE(result.is_ok());

    // Self-Consistency wrapping Chain-of-Thought is the canonical composition
    // and the one where temperature matters most; a technique that consumes
    // options but does not offer them breaks the chain at the wrapper above it.
    EXPECT_EQ(base->option_calls(), 3u);
    base->assert_every_call_carried_temperature(0.6);
}

TEST(SelfConsistencyOptions, VotingIsUnaffectedByTemperature) {
    auto base = std::make_shared<RecordingAgent>(
        [](const std::string&) { return "Therefore, 42"; });
    SelfConsistencyConfig config;
    config.num_samples = 5;
    config.temperature = 1.2;

    SelfConsistencyAgent sc(base, config);
    auto result = sc.process(user("Question")).get();
    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "42");
    EXPECT_DOUBLE_EQ(response.metadata()["consistency_score"].get<double>(), 1.0);
}

// ---------------------------------------------------------------------------
// process() must not manufacture options
// ---------------------------------------------------------------------------

TEST(CallOptionsPlainPath, ProcessLeavesChainOfThoughtOnThePlainPath) {
    auto base = std::make_shared<RecordingAgent>(everything_responder());
    ChainOfThoughtAgent cot(base);

    auto result = cot.process(user("Question")).get();
    ASSERT_TRUE(result.is_ok());

    // process() means "no per-call options", which must not become "an empty
    // set of options" or, worse, a default temperature invented on the way past.
    EXPECT_EQ(base->plain_calls(), 1u);
    EXPECT_EQ(base->option_calls(), 0u);
}

TEST(CallOptionsPlainPath, EmptyOptionsTakeThePlainPath) {
    auto base = std::make_shared<RecordingAgent>(everything_responder());

    auto result = process_with_options(base, user("Question"), CallOptions{}).get();
    ASSERT_TRUE(result.is_ok());

    EXPECT_EQ(base->plain_calls(), 1u);
    EXPECT_EQ(base->option_calls(), 0u);
}

TEST(CallOptionsPlainPath, AnAgentWithoutTheCapabilityStillGetsCalled) {
    auto plain = std::make_shared<PlainAgent>();

    auto result = process_with_options(
        plain, user("Question"), CallOptions{}.with_temperature(0.5)).get();
    ASSERT_TRUE(result.is_ok());

    // Options are dropped, not fatal: an agent that cannot honour them still
    // has to answer.
    EXPECT_EQ(plain->calls(), 1u);
}

// ---------------------------------------------------------------------------
// Chain-of-Thought
// ---------------------------------------------------------------------------

TEST(ChainOfThoughtOptions, ForwardsOptionsToTheWrappedAgent) {
    auto base = std::make_shared<RecordingAgent>(everything_responder());
    ChainOfThoughtAgent cot(base);

    auto result = cot.process_with(
        user("Question"), CallOptions{}.with_temperature(0.4)).get();
    ASSERT_TRUE(result.is_ok());

    EXPECT_EQ(base->option_calls(), 1u);
    base->assert_every_call_carried_temperature(0.4);
}

// ---------------------------------------------------------------------------
// Least-to-Most: decomposition AND every subproblem
// ---------------------------------------------------------------------------

TEST(LeastToMostOptions, ForwardsOptionsToDecompositionAndEverySubproblem) {
    auto base = std::make_shared<RecordingAgent>(everything_responder());
    LeastToMostAgent ltm(base);

    auto result = ltm.process_with(
        user("Calculate 3*4 + 2*5"), CallOptions{}.with_temperature(0.55)).get();
    ASSERT_TRUE(result.is_ok());

    // 1 decomposition + 2 subproblems. Asserting the count matters: solving
    // zero subproblems would satisfy "every subproblem forwarded" vacuously.
    EXPECT_EQ(base->option_calls(), 3u);
    base->assert_every_call_carried_temperature(0.55);
}

// ---------------------------------------------------------------------------
// Plan-and-Solve: happy path AND the replanning branch
// ---------------------------------------------------------------------------

TEST(PlanAndSolveOptions, ForwardsOptionsToPlanningValidationAndEveryStep) {
    auto base = std::make_shared<RecordingAgent>(
        [](const std::string& prompt) -> std::string {
            if (contains(prompt, "Solution Plan:")) {
                return "1. First step\n2. Second step";
            }
            if (contains(prompt, "Validation (answer")) {
                return "VALID";
            }
            return "Step result";
        });

    PlanAndSolveConfig config;
    config.validate_plan = true;
    config.allow_replanning = false;

    PlanAndSolveAgent pas(base, config);
    auto result = pas.process_with(
        user("Problem"), CallOptions{}.with_temperature(0.35)).get();
    ASSERT_TRUE(result.is_ok());

    // 1 plan + 1 validation + 2 steps.
    EXPECT_EQ(base->option_calls(), 4u);
    base->assert_every_call_carried_temperature(0.35);
}

TEST(PlanAndSolveOptions, ForwardsOptionsThroughTheReplanningBranch) {
    auto base = std::make_shared<RecordingAgent>(everything_responder());

    PlanAndSolveConfig config;
    config.validate_plan = true;
    config.allow_replanning = true;

    PlanAndSolveAgent pas(base, config);
    auto result = pas.process_with(
        user("Problem"), CallOptions{}.with_temperature(0.45)).get();
    ASSERT_TRUE(result.is_ok());

    // The replanning branch runs only when validation REJECTS the plan, which
    // the responder above forces. It adds three more LLM calls that the happy
    // path never touches: 1 plan + 1 validation + 1 improved-plan prompt +
    // 1 replan + 1 revalidation + 2 steps.
    EXPECT_EQ(base->option_calls(), 7u)
        << "the replanning branch did not run; the test proves nothing";
    base->assert_every_call_carried_temperature(0.45);

    bool saw_replanning_prompt = false;
    for (const auto& prompt : base->prompts()) {
        if (contains(prompt, "The previous plan had issues")) {
            saw_replanning_prompt = true;
        }
    }
    EXPECT_TRUE(saw_replanning_prompt);
}

// ---------------------------------------------------------------------------
// Tree-of-Thought: recursive expansion under each search strategy
// ---------------------------------------------------------------------------

namespace {

void assert_tree_of_thought_forwards(SearchStrategy strategy) {
    auto base = std::make_shared<RecordingAgent>(
        [](const std::string&) { return kSurvivesPruning; });

    TreeOfThoughtConfig config;
    config.strategy = strategy;
    config.branching_factor = 2;
    config.max_depth = 2;

    TreeOfThoughtAgent tot(base, config);
    auto result = tot.process_with(
        user("Design a system"), CallOptions{}.with_temperature(0.65)).get();
    ASSERT_TRUE(result.is_ok());

    // 2 branches from the root, then 2 from each of those. The count is the
    // assertion that matters: if the branch text were pruned, only the root
    // would expand (2 calls) and the recursive expansion — where a dropped
    // forward would actually hide — would go untested.
    EXPECT_EQ(base->option_calls(), 6u)
        << "the tree did not expand past the root; the test proves nothing";
    base->assert_every_call_carried_temperature(0.65);
}

} // namespace

TEST(TreeOfThoughtOptions, ForwardsOptionsUnderBfs) {
    assert_tree_of_thought_forwards(SearchStrategy::BFS);
}

TEST(TreeOfThoughtOptions, ForwardsOptionsUnderDfs) {
    assert_tree_of_thought_forwards(SearchStrategy::DFS);
}

TEST(TreeOfThoughtOptions, ForwardsOptionsUnderBestFirst) {
    assert_tree_of_thought_forwards(SearchStrategy::BestFirst);
}

// ---------------------------------------------------------------------------
// Graph-of-Thought: all four phases, including the node-cap-gated conclusion
// ---------------------------------------------------------------------------

TEST(GraphOfThoughtOptions, ForwardsOptionsToEveryPhaseOfTheGraphBuild) {
    auto base = std::make_shared<RecordingAgent>(everything_responder());
    GraphOfThoughtAgent got(base, GraphOfThoughtConfig{});

    auto result = got.process_with(
        user("Problem"), CallOptions{}.with_temperature(0.75)).get();
    ASSERT_TRUE(result.is_ok());

    base->assert_every_call_carried_temperature(0.75);

    // The conclusion call is gated on the node count staying under the cap. If
    // the expansion loop filled the graph to max_nodes, that phase would never
    // run and its forward would never be exercised — so assert it happened.
    bool saw_premises = false;
    bool saw_thoughts = false;
    bool saw_connection = false;
    bool saw_conclusion = false;
    for (const auto& prompt : base->prompts()) {
        if (contains(prompt, "Premises:")) saw_premises = true;
        if (contains(prompt, "houghts (one per line)")) saw_thoughts = true;
        if (contains(prompt, "SUPPORT, DEPEND")) saw_connection = true;
        if (contains(prompt, "Final conclusion:")) saw_conclusion = true;
    }
    EXPECT_TRUE(saw_premises) << "premise generation never ran";
    EXPECT_TRUE(saw_thoughts) << "thought expansion never ran";
    EXPECT_TRUE(saw_connection) << "edge identification never ran";
    EXPECT_TRUE(saw_conclusion) << "the gated conclusion phase never ran";
}

// ---------------------------------------------------------------------------
// CallOptions itself
// ---------------------------------------------------------------------------

TEST(CallOptionsTest, EmptyByDefault) {
    EXPECT_TRUE(CallOptions{}.empty());
}

TEST(CallOptionsTest, ATemperatureOfZeroIsNotEmpty) {
    // 0.0 is a set value, and `empty()` gates whether options are forwarded at
    // all — treating it as empty would silently drop a greedy-decoding request.
    EXPECT_FALSE(CallOptions{}.with_temperature(0.0).empty());
}

TEST(CallOptionsTest, ExtraKeysCountAsSet) {
    EXPECT_FALSE(CallOptions{}.with_extra("presence_penalty", 0.5).empty());
}

TEST(CallOptionsTest, ToParamsOmitsUnsetFields) {
    auto params = CallOptions{}.with_temperature(0.7).to_params();
    EXPECT_TRUE(params.contains("temperature"));
    EXPECT_FALSE(params.contains("max_tokens"));
    EXPECT_FALSE(params.contains("top_p"));
    EXPECT_FALSE(params.contains("seed"));
    EXPECT_FALSE(params.contains("stop"));
}

TEST(CallOptionsTest, ToParamsKeepsATemperatureOfZero) {
    auto params = CallOptions{}.with_temperature(0.0).to_params();
    ASSERT_TRUE(params.contains("temperature"));
    EXPECT_DOUBLE_EQ(params["temperature"].get<double>(), 0.0);
}

TEST(CallOptionsTest, ToParamsUsesWireNames) {
    auto params = CallOptions{}
        .with_max_tokens(100)
        .with_top_p(0.9)
        .with_seed(42)
        .with_stop({"STOP"})
        .with_extra("presence_penalty", 0.25)
        .to_params();

    EXPECT_EQ(params["max_tokens"].get<int>(), 100);
    EXPECT_DOUBLE_EQ(params["top_p"].get<double>(), 0.9);
    EXPECT_EQ(params["seed"].get<uint64_t>(), 42u);
    EXPECT_EQ(params["stop"][0].get<std::string>(), "STOP");
    EXPECT_DOUBLE_EQ(params["presence_penalty"].get<double>(), 0.25);
}

TEST(CallOptionsTest, MergeOverridesSetFields) {
    auto base = CallOptions{}.with_temperature(0.2).with_max_tokens(100);
    auto merged = base.merge(CallOptions{}.with_temperature(0.9));

    ASSERT_TRUE(merged.temperature.has_value());
    EXPECT_DOUBLE_EQ(merged.temperature.value(), 0.9);
    ASSERT_TRUE(merged.max_tokens.has_value());
    EXPECT_EQ(merged.max_tokens.value(), 100);
}

TEST(CallOptionsTest, MergeDoesNotLetAnUnsetOverrideEraseTheBase) {
    auto base = CallOptions{}.with_temperature(0.2).with_max_tokens(100);
    auto merged = base.merge(CallOptions{});

    // An unset field means "did not ask", not "clear it". A caller forwarding an
    // unset optional produces exactly this shape.
    ASSERT_TRUE(merged.temperature.has_value());
    EXPECT_DOUBLE_EQ(merged.temperature.value(), 0.2);
    ASSERT_TRUE(merged.max_tokens.has_value());
    EXPECT_EQ(merged.max_tokens.value(), 100);
}

TEST(CallOptionsTest, MergeCanOverrideWithATemperatureOfZero) {
    auto merged = CallOptions{}.with_temperature(0.8)
        .merge(CallOptions{}.with_temperature(0.0));

    ASSERT_TRUE(merged.temperature.has_value());
    EXPECT_DOUBLE_EQ(merged.temperature.value(), 0.0);
}

TEST(CallOptionsTest, MergeCombinesExtraKeys) {
    auto merged = CallOptions{}.with_extra("a", 1)
        .merge(CallOptions{}.with_extra("b", 2));

    EXPECT_EQ(merged.extra["a"].get<int>(), 1);
    EXPECT_EQ(merged.extra["b"].get<int>(), 2);
}

TEST(CallOptionsTest, MergeLeavesTheOperandsUntouched) {
    auto base = CallOptions{}.with_temperature(0.2);
    auto overrides = CallOptions{}.with_temperature(0.9);
    (void)base.merge(overrides);

    EXPECT_DOUBLE_EQ(base.temperature.value(), 0.2);
    EXPECT_DOUBLE_EQ(overrides.temperature.value(), 0.9);
}

TEST(CallOptionsTest, BuildersRejectOutOfRangeValues) {
    EXPECT_THROW(CallOptions{}.with_temperature(-0.1), std::invalid_argument);
    EXPECT_THROW(CallOptions{}.with_temperature(2.1), std::invalid_argument);
    EXPECT_THROW(CallOptions{}.with_max_tokens(0), std::invalid_argument);
    EXPECT_THROW(CallOptions{}.with_top_p(1.5), std::invalid_argument);
}

TEST(CallOptionsTest, BuildersAcceptTheRangeBoundaries) {
    EXPECT_NO_THROW(CallOptions{}.with_temperature(0.0));
    EXPECT_NO_THROW(CallOptions{}.with_temperature(2.0));
    EXPECT_NO_THROW(CallOptions{}.with_top_p(0.0));
    EXPECT_NO_THROW(CallOptions{}.with_top_p(1.0));
}

TEST(CallOptionsTest, ValidateCatchesWhatTheBuildersWereBypassedFor) {
    // The fields are public and the struct is aggregate-initializable, so the
    // builders can be skipped entirely. validate() is the only guard there.
    CallOptions options;
    options.temperature = 3.0;
    EXPECT_THROW(options.validate(), std::invalid_argument);

    CallOptions ok;
    ok.temperature = 1.0;
    EXPECT_NO_THROW(ok.validate());
}

TEST(CallOptionsTest, ValidateAcceptsUnsetFields) {
    EXPECT_NO_THROW(CallOptions{}.validate());
}
