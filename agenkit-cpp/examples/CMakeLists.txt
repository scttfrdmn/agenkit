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

# Set output directory
set_target_properties(echo_agent http_transport agent_chain reflection_example react_example agents_as_tools_example
    PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/examples"
)
