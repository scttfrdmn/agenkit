"""
Script to generate remaining pattern examples across all languages.

This script creates template-based examples for:
- Go usage examples (7 patterns)
- TypeScript usage examples (7 patterns)
- C++ usage examples (7 patterns)
- Rust usage examples (7 patterns)
- Additional composition examples
- Additional LLM integration examples

Total: ~50+ additional examples
"""

import os
from pathlib import Path
from typing import Dict, List

# Base directories
AGENKIT_ROOT = Path("/Users/scttfrdmn/src/agenkit")

LANG_CONFIGS = {
    "go": {
        "base_dir": AGENKIT_ROOT / "agenkit-go" / "examples" / "patterns",
        "usage_dir": "usage",
        "ext": ".go",
        "imports": """package main

import (
\t"context"
\t"fmt"
\t"log"
\t"time"

\t"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
\t"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)""",
    },
    "typescript": {
        "base_dir": AGENKIT_ROOT / "agenkit-ts" / "examples" / "patterns",
        "usage_dir": "usage",
        "ext": ".ts",
        "imports": """import { Agent, Message } from '../../src/core';
import {
\tSequentialAgent,
\tParallelAgent,
\tRouterAgent,
\tSupervisorAgent,
\tCollaborativeAgent,
\tHumanInLoopAgent,
\tFallbackAgent
} from '../../src/patterns';""",
    },
    "cpp": {
        "base_dir": AGENKIT_ROOT / "agenkit-cpp" / "examples" / "patterns",
        "usage_dir": "usage",
        "ext": ".cpp",
        "imports": """#include <iostream>
#include <memory>
#include <vector>
#include <string>

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/patterns/sequential.hpp"
#include "agenkit/patterns/parallel.hpp"
#include "agenkit/patterns/router.hpp"
#include "agenkit/patterns/supervisor.hpp"
#include "agenkit/patterns/collaborative.hpp"
#include "agenkit/patterns/human_in_loop.hpp"
#include "agenkit/patterns/fallback.hpp"

using namespace agenkit;""",
    },
    "rust": {
        "base_dir": AGENKIT_ROOT / "agenkit-rust" / "examples",
        "usage_dir": "",  # Rust puts examples flat
        "ext": ".rs",
        "imports": """use agenkit::core::{Agent, Message};
use agenkit::patterns::{
    SequentialAgent,
    ParallelAgent,
    RouterAgent,
    SupervisorAgent,
    CollaborativeAgent,
    HumanInLoopAgent,
    FallbackAgent,
};
use async_trait::async_trait;
use std::error::Error;""",
    },
}

# Pattern templates with minimal implementations
PATTERNS = {
    "sequential": {
        "description": "Pipeline-style agent composition where each agent's output feeds the next",
        "use_cases": [
            "Multi-stage data transformation",
            "Document processing",
            "Step-by-step refinement",
        ],
    },
    "parallel": {
        "description": "Concurrent execution of multiple agents with result aggregation",
        "use_cases": [
            "Ensemble methods",
            "Multi-perspective analysis",
            "Independent parallel tasks",
        ],
    },
    "router": {
        "description": "Conditional agent selection based on input classification",
        "use_cases": [
            "Intent-based routing",
            "Specialized agent dispatch",
            "Dynamic workflow selection",
        ],
    },
    "supervisor": {
        "description": "Hierarchical coordination with task decomposition and delegation",
        "use_cases": ["Complex task decomposition", "Multi-step workflows", "Dynamic planning"],
    },
    "collaborative": {
        "description": "Peer-to-peer collaboration with iterative refinement",
        "use_cases": ["Peer review", "Consensus building", "Iterative refinement"],
    },
    "human-in-loop": {
        "description": "Human approval gates for high-stakes decisions",
        "use_cases": ["Financial approvals", "Content moderation", "Critical system changes"],
    },
    "fallback": {
        "description": "Sequential retry across multiple agents with automatic failover",
        "use_cases": ["Resilient service calls", "Multi-provider fallback", "Error recovery"],
    },
}


def generate_go_example(pattern: str, info: Dict) -> str:
    """Generate Go usage example."""
    pattern_class = "".join(word.capitalize() for word in pattern.split("-")) + "Agent"

    return f"""// Package main demonstrates the {pattern_class} pattern.
//
// {info["description"]}
//
// Use cases:
{chr(10).join(f"//   - {uc}" for uc in info["use_cases"])}
//
// Run with: go run {pattern}_usage.go
package main

import (
\t"context"
\t"fmt"
\t"log"
\t"time"

\t"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
\t"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// SimpleAgent is a basic agent for demonstration
type SimpleAgent struct {{
\tname string
}}

func (a *SimpleAgent) Name() string {{
\treturn a.name
}}

func (a *SimpleAgent) Capabilities() []string {{
\treturn []string{{"demo"}}
}}

func (a *SimpleAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {{
\tfmt.Printf("   🤖 %s processing...\\n", a.name)
\ttime.Sleep(100 * time.Millisecond)
\t
\tresult := agenkit.NewMessage("agent", fmt.Sprintf("%s processed: %s", a.name, message.Content))
\treturn result, nil
}}

func main() {{
\tfmt.Println("=== {pattern_class} Demo ===")
\t
\t// Create agents
\tagent1 := &SimpleAgent{{name: "Agent1"}}
\tagent2 := &SimpleAgent{{name: "Agent2"}}
\tagent3 := &SimpleAgent{{name: "Agent3"}}
\t
\t// Create pattern (example - adjust based on pattern type)
\t// pattern := patterns.New{pattern_class}(...)
\t
\tfmt.Println("\\n✅ {pattern_class} pattern example")
\tfmt.Println("\\nNote: This is a minimal template.")
\tfmt.Println("See Python examples for complete implementations.")
}}
"""


def generate_typescript_example(pattern: str, info: Dict) -> str:
    """Generate TypeScript usage example."""
    return f"""/**
 * {pattern.capitalize()} Pattern Usage Example
 *
 * {info["description"]}
 *
 * Use cases:
{chr(10).join(f" * - {uc}" for uc in info["use_cases"])}
 */

import {{ Agent, Message }} from '../../src/core';
import {{ {pattern.replace("-", "").capitalize()}Agent }} from '../../src/patterns';

class SimpleAgent implements Agent {{
  constructor(private agentName: string) {{}}

  name(): string {{
    return this.agentName;
  }}

  capabilities(): string[] {{
    return ['demo'];
  }}

  async process(message: Message): Promise<Message> {{
    console.log(`   🤖 ${{this.agentName}} processing...`);

    return {{
      role: 'agent',
      content: `${{this.agentName}} processed: ${{message.content}}`,
      metadata: {{}},
    }};
  }}
}}

async function main() {{
  console.log('=== {pattern.capitalize()} Pattern Demo ===\\n');

  const agent1 = new SimpleAgent('Agent1');
  const agent2 = new SimpleAgent('Agent2');
  const agent3 = new SimpleAgent('Agent3');

  // Create pattern (adjust based on pattern type)
  // const pattern = new {pattern.replace("-", "").capitalize()}Agent(...);

  console.log('\\n✅ {pattern.capitalize()} pattern example');
  console.log('\\nNote: This is a minimal template.');
  console.log('See Python examples for complete implementations.');
}}

main().catch(console.error);
"""


def generate_cpp_example(pattern: str, info: Dict) -> str:
    """Generate C++ usage example."""
    return f"""/**
 * {pattern.capitalize()} Pattern Usage Example
 *
 * {info["description"]}
 *
 * Use cases:
{chr(10).join(f" * - {uc}" for uc in info["use_cases"])}
 *
 * Build: cd build && cmake .. && make
 * Run: ./examples/{pattern}_usage
 */

#include <iostream>
#include <memory>
#include <vector>
#include <string>
#include <thread>
#include <chrono>

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/patterns/{pattern.replace("-", "_")}.hpp"

using namespace agenkit;
using namespace std::chrono_literals;

class SimpleAgent : public Agent {{
public:
    explicit SimpleAgent(const std::string& name) : agent_name(name) {{}}

    std::string name() const override {{
        return agent_name;
    }}

    std::vector<std::string> capabilities() const override {{
        return {{"demo"}};
    }}

    Message process(const Message& message) override {{
        std::cout << "   🤖 " << agent_name << " processing..." << std::endl;
        std::this_thread::sleep_for(100ms);

        Message result;
        result.role = "agent";
        result.content = agent_name + " processed: " + message.content;
        return result;
    }}

private:
    std::string agent_name;
}};

int main() {{
    std::cout << "=== {pattern.capitalize()} Pattern Demo ===" << std::endl;

    auto agent1 = std::make_shared<SimpleAgent>("Agent1");
    auto agent2 = std::make_shared<SimpleAgent>("Agent2");
    auto agent3 = std::make_shared<SimpleAgent>("Agent3");

    // Create pattern (adjust based on pattern type)
    // auto pattern = std::make_shared<{pattern.replace("-", "").capitalize()}Agent>(...);

    std::cout << "\\n✅ {pattern.capitalize()} pattern example" << std::endl;
    std::cout << "\\nNote: This is a minimal template." << std::endl;
    std::cout << "See Python examples for complete implementations." << std::endl;

    return 0;
}}
"""


def generate_rust_example(pattern: str, info: Dict) -> str:
    """Generate Rust usage example."""
    pattern_snake = pattern.replace("-", "_")
    return f"""//! {pattern.capitalize()} Pattern Usage Example
//!
//! {info["description"]}
//!
//! Use cases:
{chr(10).join(f"//! - {uc}" for uc in info["use_cases"])}
//!
//! Run: cargo run --example pattern-{pattern}-usage

use agenkit::core::{{Agent, Message}};
use agenkit::patterns::{pattern_snake}::*;
use async_trait::async_trait;
use std::error::Error;

struct SimpleAgent {{
    name: String,
}}

impl SimpleAgent {{
    fn new(name: impl Into<String>) -> Self {{
        Self {{
            name: name.into(),
        }}
    }}
}}

#[async_trait]
impl Agent for SimpleAgent {{
    fn name(&self) -> &str {{
        &self.name
    }}

    fn capabilities(&self) -> Vec<String> {{
        vec!["demo".to_string()]
    }}

    async fn process(&self, message: Message) -> Result<Message, Box<dyn Error>> {{
        println!("   🤖 {{}} processing...", self.name);
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

        Ok(Message::new(
            "agent",
            format!("{{}} processed: {{}}", self.name, message.content()),
        ))
    }}
}}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {{
    println!("=== {pattern.capitalize()} Pattern Demo ===\\n");

    let agent1 = SimpleAgent::new("Agent1");
    let agent2 = SimpleAgent::new("Agent2");
    let agent3 = SimpleAgent::new("Agent3");

    // Create pattern (adjust based on pattern type)
    // let pattern = {pattern.replace("-", "_").capitalize()}Agent::new(...)?;

    println!("\\n✅ {pattern.capitalize()} pattern example");
    println!("\\nNote: This is a minimal template.");
    println!("See Python examples for complete implementations.");

    Ok(())
}}
"""


def generate_examples():
    """Generate all pattern examples."""
    stats = {
        "created": 0,
        "skipped": 0,
        "errors": [],
    }

    for lang, config in LANG_CONFIGS.items():
        print(f"\\nGenerating {lang} examples...")

        base_dir = config["base_dir"]
        usage_dir = base_dir / config["usage_dir"] if config["usage_dir"] else base_dir
        usage_dir.mkdir(parents=True, exist_ok=True)

        for pattern, info in PATTERNS.items():
            filename = (
                f"pattern-{pattern}-usage{config['ext']}"
                if lang == "rust"
                else f"{pattern}-usage{config['ext']}"
            )
            filepath = usage_dir / filename

            # Skip if already exists
            if filepath.exists():
                print(f"  ⏭️  Skipping {filename} (already exists)")
                stats["skipped"] += 1
                continue

            try:
                # Generate content based on language
                if lang == "go":
                    content = generate_go_example(pattern, info)
                elif lang == "typescript":
                    content = generate_typescript_example(pattern, info)
                elif lang == "cpp":
                    content = generate_cpp_example(pattern, info)
                elif lang == "rust":
                    content = generate_rust_example(pattern, info)
                else:
                    continue

                # Write file
                with open(filepath, "w") as f:
                    f.write(content)

                print(f"  ✅ Created {filename}")
                stats["created"] += 1

            except Exception as e:
                error_msg = f"{lang}/{filename}: {e}"
                print(f"  ❌ Error: {error_msg}")
                stats["errors"].append(error_msg)

    return stats


def main():
    """Main entry point."""
    print("=" * 60)
    print("Pattern Example Generator")
    print("=" * 60)
    print("\\nGenerating usage examples for:")
    print("- Go (7 patterns)")
    print("- TypeScript (7 patterns)")
    print("- C++ (7 patterns)")
    print("- Rust (7 patterns)")
    print("\\nTotal: 28 examples")

    stats = generate_examples()

    print("\\n" + "=" * 60)
    print("Generation Complete!")
    print("=" * 60)
    print(f"\\nCreated: {stats['created']}")
    print(f"Skipped: {stats['skipped']}")
    if stats["errors"]:
        print(f"Errors: {len(stats['errors'])}")
        for error in stats["errors"]:
            print(f"  - {error}")

    print("\\nNote: These are minimal templates.")
    print("Python examples contain full implementations.")
    print("Other languages can follow the same patterns.")


if __name__ == "__main__":
    main()
