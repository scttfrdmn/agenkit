# Examples configuration

# Echo agent example
add_executable(echo_agent echo_agent.cpp)
target_link_libraries(echo_agent agenkit)

# HTTP transport example
add_executable(http_transport http_transport.cpp)
target_link_libraries(http_transport agenkit)

# Agent chain example
add_executable(agent_chain agent_chain.cpp)
target_link_libraries(agent_chain agenkit)

# Claude Reflection example
add_executable(claude_reflection claude_reflection.cpp)
target_link_libraries(claude_reflection agenkit)

# Ollama example
add_executable(ollama_example ollama_example.cpp)
target_link_libraries(ollama_example agenkit)

# ReAct with tools example (uses Ollama)
add_executable(react_tools_example react_tools_example.cpp)
target_link_libraries(react_tools_example agenkit)

# OpenAI examples
add_executable(openai_basic openai_basic.cpp)
target_link_libraries(openai_basic agenkit)

add_executable(multiagent_openai multiagent_openai.cpp)
target_link_libraries(multiagent_openai agenkit)

# Adapter examples
add_executable(litellm_basic adapters/litellm-basic.cpp)
target_link_libraries(litellm_basic agenkit)

add_executable(gemini_basic adapters/gemini-basic.cpp)
target_link_libraries(gemini_basic agenkit)

add_executable(bedrock_basic adapters/bedrock-basic.cpp)
target_link_libraries(bedrock_basic agenkit)

add_executable(conversation_memory conversation_memory.cpp)
target_link_libraries(conversation_memory agenkit)

add_executable(react_openai react_openai.cpp)
target_link_libraries(react_openai agenkit)

add_executable(reflection_openai reflection_openai.cpp)
target_link_libraries(reflection_openai agenkit)

# Pattern examples - Reflection
add_executable(reflection_example patterns/reflection_example.cpp)
target_link_libraries(reflection_example agenkit)

# Pattern examples - ReAct
add_executable(react_example patterns/react_example.cpp)
target_link_libraries(react_example agenkit)

# Pattern examples - Agents-as-Tools
add_executable(agents_as_tools_example patterns/agents_as_tools_example.cpp)
target_link_libraries(agents_as_tools_example agenkit)

# Pattern examples - Orchestration
add_executable(orchestration_example patterns/orchestration_example.cpp)
target_link_libraries(orchestration_example agenkit)

# Pattern examples - Reasoning with Tools
add_executable(reasoning_with_tools_example patterns/reasoning_with_tools_example.cpp)
target_link_libraries(reasoning_with_tools_example agenkit)

# Pattern examples - Conversational
add_executable(conversational_example patterns/conversational_example.cpp)
target_link_libraries(conversational_example agenkit)

# Pattern examples - Task
add_executable(task_example patterns/task_example.cpp)
target_link_libraries(task_example agenkit)

# Pattern examples - Multiagent
add_executable(multiagent_example patterns/multiagent_example.cpp)
target_link_libraries(multiagent_example agenkit)

# Pattern examples - Planning
add_executable(planning_example patterns/planning_example.cpp)
target_link_libraries(planning_example agenkit)

# Pattern examples - Autonomous
add_executable(autonomous_example patterns/autonomous_example.cpp)
target_link_libraries(autonomous_example agenkit)

# Pattern examples - Memory
add_executable(memory_example patterns/memory_example.cpp)
target_link_libraries(memory_example agenkit)

# Set output directory
set_target_properties(echo_agent http_transport agent_chain claude_reflection ollama_example react_tools_example openai_basic multiagent_openai litellm_basic gemini_basic bedrock_basic conversation_memory react_openai reflection_openai reflection_example react_example agents_as_tools_example orchestration_example reasoning_with_tools_example conversational_example task_example multiagent_example planning_example autonomous_example memory_example
    PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/examples"
)

# Evaluation examples
add_executable(basic_metrics evaluation/basic_metrics.cpp)
target_link_libraries(basic_metrics agenkit)

add_executable(session_recording evaluation/session_recording.cpp)
target_link_libraries(session_recording agenkit)

add_executable(quality_scoring evaluation/quality_scoring.cpp)
target_link_libraries(quality_scoring agenkit)

add_executable(regression_detection evaluation/regression_detection.cpp)
target_link_libraries(regression_detection agenkit)

add_executable(production_monitoring evaluation/production_monitoring.cpp)
target_link_libraries(production_monitoring agenkit)

add_executable(ab_testing evaluation/ab_testing.cpp)
target_link_libraries(ab_testing agenkit)
