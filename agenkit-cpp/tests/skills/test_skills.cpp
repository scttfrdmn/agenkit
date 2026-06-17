/**
 * @file test_skills.cpp
 * @brief Tests for AgentSkill, SkillRegistry, and SkillEnabledAgent.
 *
 * Ported from the Python reference suites:
 *   tests/skills/test_skill_loader.py
 *   tests/skills/test_skill_agent.py
 */

#include <gtest/gtest.h>

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include "agenkit/skills/skill.hpp"
#include "agenkit/skills/skill_enabled_agent.hpp"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <future>
#include <memory>
#include <random>
#include <string>
#include <vector>

using agenkit::core::Agent;
using agenkit::core::AgentError;
using agenkit::core::Message;
using agenkit::core::Result;
using agenkit::skills::AgentSkill;
using agenkit::skills::SkillEnabledAgent;
using agenkit::skills::SkillRegistry;

namespace fs = std::filesystem;

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------

/** Create a unique temporary directory for a test and clean it up after. */
class TempDir {
public:
    TempDir() {
        std::random_device rd;
        std::mt19937_64 gen(rd());
        path_ = fs::temp_directory_path() /
                ("agenkit_skills_" + std::to_string(gen()));
        fs::create_directories(path_);
    }

    ~TempDir() {
        std::error_code ec;
        fs::remove_all(path_, ec);
    }

    const fs::path& path() const { return path_; }

private:
    fs::path path_;
};

/** Create a minimal valid skill directory inside base. */
static fs::path make_skill_dir(const fs::path& base, const std::string& name,
                               const std::string& description,
                               const std::string& body = "Instructions here.") {
    const fs::path skill_dir = base / name;
    fs::create_directories(skill_dir);
    const std::string content =
        "---\nname: " + name + "\ndescription: " + description + "\n---\n" + body;
    std::ofstream out(skill_dir / "SKILL.md", std::ios::binary);
    out << content;
    return skill_dir;
}

/** Agent that echoes its input content back. */
class EchoAgent : public Agent {
public:
    std::string name() const override { return "echo"; }

    std::future<Result<Message, AgentError>> process(Message message) override {
        // EchoAgent uses role "agent" in the Python reference; mirror that and
        // echo content + metadata back unchanged.
        Message echoed("agent", message.content());
        const auto& metadata = message.metadata();
        if (metadata.is_object()) {
            for (auto it = metadata.begin(); it != metadata.end(); ++it) {
                echoed.with_metadata(it.key(), it.value());
            }
        }
        return agenkit::core::make_ready_future(
            Result<Message, AgentError>::ok(std::move(echoed)));
    }
};

// ---------------------------------------------------------------------------
// AgentSkill::from_directory
// ---------------------------------------------------------------------------

TEST(SkillLoaderTest, LoadSkillValid) {
    TempDir tmp;
    const fs::path dir =
        make_skill_dir(tmp.path(), "pdf-processing", "Extract text from PDFs.",
                       "# PDF\nDo stuff.");
    const AgentSkill skill = AgentSkill::from_directory(dir);

    EXPECT_EQ(skill.name, "pdf-processing");
    EXPECT_EQ(skill.description, "Extract text from PDFs.");
    EXPECT_NE(skill.instructions.find("Do stuff."), std::string::npos);
    ASSERT_TRUE(skill.skill_dir.has_value());
    EXPECT_EQ(*skill.skill_dir, dir);
}

TEST(SkillLoaderTest, LoadSkillWithLicenseAndMetadata) {
    TempDir tmp;
    const fs::path dir = tmp.path() / "advanced";
    fs::create_directories(dir);
    const std::string content =
        "---\n"
        "name: advanced\n"
        "description: Advanced skill.\n"
        "license: Apache-2.0\n"
        "metadata:\n"
        "  version: '1.0'\n"
        "---\n"
        "Advanced instructions.";
    {
        std::ofstream out(dir / "SKILL.md", std::ios::binary);
        out << content;
    }

    const AgentSkill skill = AgentSkill::from_directory(dir);
    ASSERT_TRUE(skill.license.has_value());
    EXPECT_EQ(*skill.license, "Apache-2.0");
    ASSERT_EQ(skill.metadata.size(), 1u);
    EXPECT_EQ(skill.metadata.at("version"), "1.0");
}

TEST(SkillLoaderTest, LoadSkillMissingSkillMd) {
    TempDir tmp;
    const fs::path empty_dir = tmp.path() / "empty";
    fs::create_directories(empty_dir);

    try {
        AgentSkill::from_directory(empty_dir);
        FAIL() << "expected std::invalid_argument";
    } catch (const std::invalid_argument& e) {
        EXPECT_NE(std::string(e.what()).find("No SKILL.md found"),
                  std::string::npos);
    }
}

TEST(SkillLoaderTest, LoadSkillInvalidFrontmatter) {
    TempDir tmp;
    const fs::path dir = tmp.path() / "bad";
    fs::create_directories(dir);
    {
        // Missing second "---" delimiter.
        std::ofstream out(dir / "SKILL.md", std::ios::binary);
        out << "name: foo\ndescription: bar\n";
    }

    try {
        AgentSkill::from_directory(dir);
        FAIL() << "expected std::invalid_argument";
    } catch (const std::invalid_argument& e) {
        EXPECT_NE(std::string(e.what()).find("missing frontmatter delimiters"),
                  std::string::npos);
    }
}

TEST(SkillLoaderTest, LoadSkillMissingName) {
    TempDir tmp;
    const fs::path dir = tmp.path() / "noname";
    fs::create_directories(dir);
    {
        std::ofstream out(dir / "SKILL.md", std::ios::binary);
        out << "---\ndescription: A skill without a name.\n---\nInstructions.";
    }

    try {
        AgentSkill::from_directory(dir);
        FAIL() << "expected std::invalid_argument";
    } catch (const std::invalid_argument& e) {
        EXPECT_NE(std::string(e.what()).find("Missing required field 'name'"),
                  std::string::npos);
    }
}

TEST(SkillLoaderTest, LoadSkillMissingDescription) {
    TempDir tmp;
    const fs::path dir = tmp.path() / "nodesc";
    fs::create_directories(dir);
    {
        std::ofstream out(dir / "SKILL.md", std::ios::binary);
        out << "---\nname: nodesc\n---\nInstructions.";
    }

    try {
        AgentSkill::from_directory(dir);
        FAIL() << "expected std::invalid_argument";
    } catch (const std::invalid_argument& e) {
        EXPECT_NE(
            std::string(e.what()).find("Missing required field 'description'"),
            std::string::npos);
    }
}

TEST(SkillLoaderTest, SkillToPrompt) {
    TempDir tmp;
    const fs::path dir = make_skill_dir(tmp.path(), "csv-tools",
                                        "Handle CSV files.", "Parse and write CSV.");
    const AgentSkill skill = AgentSkill::from_directory(dir);
    const std::string prompt = skill.to_prompt();

    EXPECT_NE(prompt.find("# Skill: csv-tools"), std::string::npos);
    EXPECT_NE(prompt.find("## Description"), std::string::npos);
    EXPECT_NE(prompt.find("Handle CSV files."), std::string::npos);
    EXPECT_NE(prompt.find("## Instructions"), std::string::npos);
    EXPECT_NE(prompt.find("Parse and write CSV."), std::string::npos);
}

// ---------------------------------------------------------------------------
// SkillRegistry
// ---------------------------------------------------------------------------

TEST(SkillRegistryTest, DiscoverSkipsNonDirs) {
    TempDir tmp;
    {
        std::ofstream out(tmp.path() / "not_a_dir.md", std::ios::binary);
        out << "ignored";
    }
    SkillRegistry registry({tmp.path()});
    registry.discover_skills();
    EXPECT_EQ(registry.skills().size(), 0u);
}

TEST(SkillRegistryTest, DiscoversValidSkills) {
    TempDir tmp;
    make_skill_dir(tmp.path(), "skill-a", "Skill A description.");
    make_skill_dir(tmp.path(), "skill-b", "Skill B description.");
    SkillRegistry registry({tmp.path()});
    registry.discover_skills();

    const auto skills = registry.skills();
    EXPECT_TRUE(skills.count("skill-a") > 0);
    EXPECT_TRUE(skills.count("skill-b") > 0);
}

TEST(SkillRegistryTest, DiscoverSkipsInvalidSkill) {
    TempDir tmp;
    make_skill_dir(tmp.path(), "good", "A good skill.");
    // An invalid skill directory (SKILL.md present but missing required name).
    const fs::path bad = tmp.path() / "bad";
    fs::create_directories(bad);
    {
        std::ofstream out(bad / "SKILL.md", std::ios::binary);
        out << "---\ndescription: no name here.\n---\nbody";
    }

    SkillRegistry registry({tmp.path()});
    registry.discover_skills();

    const auto skills = registry.skills();
    EXPECT_TRUE(skills.count("good") > 0);
    EXPECT_EQ(skills.size(), 1u);
}

TEST(SkillRegistryTest, FindRelevantNameMatch) {
    TempDir tmp;
    make_skill_dir(tmp.path(), "pdf-processing", "Work with PDF documents.");
    make_skill_dir(tmp.path(), "csv-tools", "Handle CSV spreadsheets.");
    SkillRegistry registry({tmp.path()});
    registry.discover_skills();

    const auto results = registry.find_relevant_skills("pdf");
    ASSERT_GE(results.size(), 1u);
    EXPECT_EQ(results[0].name, "pdf-processing");
}

TEST(SkillRegistryTest, FindRelevantMaxResults) {
    TempDir tmp;
    for (int i = 0; i < 6; ++i) {
        make_skill_dir(tmp.path(), "skill-" + std::to_string(i),
                       "A skill about document processing number " +
                           std::to_string(i) + ".");
    }
    SkillRegistry registry({tmp.path()});
    registry.discover_skills();

    const auto results = registry.find_relevant_skills("document", 3);
    EXPECT_LE(results.size(), 3u);
}

TEST(SkillRegistryTest, GetSkill) {
    TempDir tmp;
    make_skill_dir(tmp.path(), "email-compose", "Compose professional emails.");
    SkillRegistry registry({tmp.path()});
    registry.discover_skills();

    const auto skill = registry.get_skill("email-compose");
    ASSERT_TRUE(skill.has_value());
    EXPECT_EQ(skill->name, "email-compose");

    const auto missing = registry.get_skill("nonexistent");
    EXPECT_FALSE(missing.has_value());
}

// ---------------------------------------------------------------------------
// SkillEnabledAgent
// ---------------------------------------------------------------------------

TEST(SkillEnabledAgentTest, AugmentsMessage) {
    TempDir tmp;
    make_skill_dir(tmp.path(), "pdf-processing", "Extract text from PDF documents.");
    auto registry = std::make_shared<SkillRegistry>(
        std::vector<fs::path>{tmp.path()});
    SkillEnabledAgent agent(std::make_shared<EchoAgent>(), registry, 3, true);

    Message msg = Message::with_text("user", "How do I parse pdf files?");
    auto result = agent.process(std::move(msg)).get();
    ASSERT_TRUE(result.is_ok());

    const std::string content = result.unwrap().content_as_str();
    EXPECT_NE(content.find("<available_skills>"), std::string::npos);
    EXPECT_NE(content.find("pdf-processing"), std::string::npos);
}

TEST(SkillEnabledAgentTest, NoSkillsPassthrough) {
    TempDir tmp;
    make_skill_dir(tmp.path(), "email-compose", "Compose professional emails.");
    auto registry = std::make_shared<SkillRegistry>(
        std::vector<fs::path>{tmp.path()});
    SkillEnabledAgent agent(std::make_shared<EchoAgent>(), registry, 3, true);

    Message msg = Message::with_text("user", "tell me a joke");
    auto result = agent.process(std::move(msg)).get();
    ASSERT_TRUE(result.is_ok());

    const std::string content = result.unwrap().content_as_str();
    EXPECT_EQ(content.find("<available_skills>"), std::string::npos);
    EXPECT_EQ(content, "tell me a joke");
}

TEST(SkillEnabledAgentTest, ActiveSkillsMetadata) {
    TempDir tmp;
    make_skill_dir(tmp.path(), "csv-tools",
                   "Handle and transform CSV spreadsheets.");
    auto registry = std::make_shared<SkillRegistry>(
        std::vector<fs::path>{tmp.path()});
    SkillEnabledAgent agent(std::make_shared<EchoAgent>(), registry, 3, true);

    Message msg = Message::with_text("user", "parse this csv spreadsheet data");
    auto result = agent.process(std::move(msg)).get();
    ASSERT_TRUE(result.is_ok());

    const auto& metadata = result.unwrap().metadata();
    ASSERT_TRUE(metadata.contains("active_skills"));
    const auto active = metadata["active_skills"];
    ASSERT_TRUE(active.is_array());
    bool found = false;
    for (const auto& name : active) {
        if (name.get<std::string>() == "csv-tools") {
            found = true;
        }
    }
    EXPECT_TRUE(found);
}

TEST(SkillEnabledAgentTest, Capabilities) {
    TempDir tmp;
    auto registry = std::make_shared<SkillRegistry>(
        std::vector<fs::path>{tmp.path()});
    SkillEnabledAgent agent(std::make_shared<EchoAgent>(), registry, 3, false);

    const auto caps = agent.capabilities();
    EXPECT_NE(std::find(caps.begin(), caps.end(), "skill_injection"), caps.end());
}

TEST(SkillEnabledAgentTest, NameDelegates) {
    TempDir tmp;
    auto registry = std::make_shared<SkillRegistry>(
        std::vector<fs::path>{tmp.path()});
    SkillEnabledAgent agent(std::make_shared<EchoAgent>(), registry, 3, false);
    EXPECT_EQ(agent.name(), "echo");
}
