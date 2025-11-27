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

# Set output directory
set_target_properties(echo_agent http_transport agent_chain reflection_example react_example agents_as_tools_example orchestration_example reasoning_with_tools_example conversational_example task_example multiagent_example
    PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/examples"
)
