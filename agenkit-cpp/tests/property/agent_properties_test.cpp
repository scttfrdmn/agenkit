/**
 * @file agent_properties_test.cpp
 * @brief Property-based tests for Agent behavior invariants using RapidCheck
 *
 * Verifies that Agent and composition patterns uphold their contracts:
 * response format, name stability, error handling, and independence of calls.
 */

#include <gtest/gtest.h>
#include <rapidcheck.h>
#include <rapidcheck/gtest.h>
#include "../patterns/test_pattern_helpers.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include <string>
#include <memory>

using namespace agenkit;

// 1. An echo-style mock always returns non-empty content
RC_GTEST_PROP(AgentProperties, EchoAgentResponseNonEmpty, (std::string text)) {
    RC_PRE(!text.empty());
    auto agent = test::make_mock_agent("echo", text);
    auto msg = core::Message::with_text("user", text);
    auto result = agent->process(msg).get();
    RC_ASSERT(result.is_ok());
    RC_ASSERT(!result.unwrap().content_as_str().empty());
}

// 2. A successful mock always returns is_ok() == true
RC_GTEST_PROP(AgentProperties, ProcessResultAlwaysOk, (std::string text)) {
    auto agent = test::make_mock_agent("success", "ok response");
    auto msg = core::Message::with_text("user", text);
    auto result = agent->process(msg).get();
    RC_ASSERT(result.is_ok());
}

// 3. Agent name() returns the same value on every call
RC_GTEST_PROP(AgentProperties, AgentNameStable, (std::string name)) {
    RC_PRE(!name.empty());
    auto agent = test::make_mock_agent(name, "response");
    RC_ASSERT(agent->name() == name);
    RC_ASSERT(agent->name() == agent->name());
}

// 4. Mock agent always returns a message with "assistant" role
RC_GTEST_PROP(AgentProperties, ResponseRoleIsAssistant, (std::string text)) {
    auto agent = test::make_mock_agent("responder", "reply");
    auto msg = core::Message::with_text("user", text);
    auto result = agent->process(msg).get();
    RC_ASSERT(result.is_ok());
    RC_ASSERT(result.unwrap().role() == "assistant");
}

// 5. Two appending agents in sequence produce content containing both contributions
RC_GTEST_PROP(AgentProperties, SequentialCompositionLength, (std::string base)) {
    auto agent1 = test::make_appending_mock_agent("first", "_A");
    auto agent2 = test::make_appending_mock_agent("second", "_B");
    auto input = core::Message::with_text("user", base);
    auto r1 = agent1->process(input).get();
    RC_ASSERT(r1.is_ok());
    auto r2 = agent2->process(r1.unwrap()).get();
    RC_ASSERT(r2.is_ok());
    // Result should contain both suffixes from the chain
    auto content = r2.unwrap().content_as_str();
    RC_ASSERT(content.find("_A") != std::string::npos);
    RC_ASSERT(content.find("_B") != std::string::npos);
}

// 6. Processing an empty-content message always succeeds (no crash/error)
RC_GTEST_PROP(AgentProperties, ProcessEmptyMessageSucceeds, ()) {
    auto agent = test::make_mock_agent("agent", "response");
    auto msg = core::Message::with_text("user", "");
    auto result = agent->process(msg).get();
    RC_ASSERT(result.is_ok());
}

// 7. A failing mock always returns is_err() == true
RC_GTEST_PROP(AgentProperties, FailingAgentAlwaysErrors, (std::string text)) {
    auto agent = test::make_failing_mock_agent("failing", "deliberate error");
    auto msg = core::Message::with_text("user", text);
    auto result = agent->process(msg).get();
    RC_ASSERT(result.is_err());
}

// 8. Error result contains a non-empty error message
RC_GTEST_PROP(AgentProperties, ErrorPreservesMessage, (std::string text)) {
    auto agent = test::make_failing_mock_agent("failing", "some error");
    auto msg = core::Message::with_text("user", text);
    auto result = agent->process(msg).get();
    RC_ASSERT(result.is_err());
    RC_ASSERT(!result.unwrap_err().message().empty());
}

// 9. Two separate process() calls on the same agent do not share state
RC_GTEST_PROP(AgentProperties, MultipleCallsIndependent, (std::string text)) {
    auto agent = test::make_mock_agent("stateless", "constant response");
    auto msg = core::Message::with_text("user", text);
    auto r1 = agent->process(msg).get();
    auto r2 = agent->process(msg).get();
    RC_ASSERT(r1.is_ok());
    RC_ASSERT(r2.is_ok());
    RC_ASSERT(r1.unwrap().content_as_str() == r2.unwrap().content_as_str());
}

// 10. Agent name() never returns an empty string when constructed with non-empty name
RC_GTEST_PROP(AgentProperties, AgentNameNeverEmpty, (std::string name)) {
    RC_PRE(!name.empty());
    auto agent = test::make_mock_agent(name, "response");
    RC_ASSERT(!agent->name().empty());
}

// 11. A successful agent result always has non-empty content when given a fixed response
RC_GTEST_PROP(AgentProperties, SuccessResultHasContent, (std::string text)) {
    RC_PRE(!text.empty());
    auto agent = test::make_mock_agent("agent", text);
    auto msg = core::Message::with_text("user", "prompt");
    auto result = agent->process(msg).get();
    RC_ASSERT(result.is_ok());
    RC_ASSERT(!result.unwrap().content_as_str().empty());
}

// 12. process() returns a valid future — calling .get() does not throw
RC_GTEST_PROP(AgentProperties, ProcessReturnsFuture, (std::string text)) {
    auto agent = test::make_mock_agent("agent", "response");
    auto msg = core::Message::with_text("user", text);
    // If the future is broken or throws, the test will fail with an exception
    auto future = agent->process(msg);
    auto result = future.get();
    RC_ASSERT(result.is_ok() || result.is_err()); // either state is valid
}
