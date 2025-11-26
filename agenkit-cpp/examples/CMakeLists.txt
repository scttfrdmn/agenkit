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

# Set output directory
set_target_properties(echo_agent http_transport agent_chain
    PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/examples"
)
