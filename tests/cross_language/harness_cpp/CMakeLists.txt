cmake_minimum_required(VERSION 3.16)
project(harness_cpp VERSION 1.0.0 LANGUAGES CXX)

# C++17 standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Find or fetch nlohmann_json
find_package(nlohmann_json 3.11.0 QUIET)

if(NOT nlohmann_json_FOUND)
    message(STATUS "nlohmann_json not found, fetching from GitHub")
    include(FetchContent)
    FetchContent_Declare(
        nlohmann_json
        GIT_REPOSITORY https://github.com/nlohmann/json.git
        GIT_TAG v3.11.3
    )
    FetchContent_MakeAvailable(nlohmann_json)
endif()

# Include agenkit-cpp
set(AGENKIT_CPP_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../../agenkit-cpp")

# Check if agenkit library exists
if(EXISTS "${AGENKIT_CPP_DIR}/build/libagenkit.a" OR
   EXISTS "${AGENKIT_CPP_DIR}/build/libagenkit.so" OR
   EXISTS "${AGENKIT_CPP_DIR}/build/libagenkit.dylib")
    # Use pre-built agenkit library
    message(STATUS "Using pre-built agenkit library from ${AGENKIT_CPP_DIR}/build")
    add_library(agenkit STATIC IMPORTED)

    # Find the library file
    if(EXISTS "${AGENKIT_CPP_DIR}/build/libagenkit.a")
        set_target_properties(agenkit PROPERTIES
            IMPORTED_LOCATION "${AGENKIT_CPP_DIR}/build/libagenkit.a"
        )
    elseif(EXISTS "${AGENKIT_CPP_DIR}/build/libagenkit.dylib")
        set_target_properties(agenkit PROPERTIES
            IMPORTED_LOCATION "${AGENKIT_CPP_DIR}/build/libagenkit.dylib"
        )
    elseif(EXISTS "${AGENKIT_CPP_DIR}/build/libagenkit.so")
        set_target_properties(agenkit PROPERTIES
            IMPORTED_LOCATION "${AGENKIT_CPP_DIR}/build/libagenkit.so"
        )
    endif()
else()
    # Build agenkit from source as part of this project
    message(STATUS "Building agenkit from source: ${AGENKIT_CPP_DIR}")
    add_subdirectory("${AGENKIT_CPP_DIR}" agenkit-build)
endif()

# Harness executable
add_executable(harness_cpp main.cpp)

# Include directories
target_include_directories(harness_cpp PRIVATE
    "${AGENKIT_CPP_DIR}/include"
)

# Link libraries
target_link_libraries(harness_cpp PRIVATE
    agenkit
    nlohmann_json::nlohmann_json
)

# Find threads library (required by agenkit)
find_package(Threads REQUIRED)
target_link_libraries(harness_cpp PRIVATE Threads::Threads)

# Compiler warnings
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(harness_cpp PRIVATE
        -Wall -Wextra -Wpedantic
        -Wno-unused-parameter
    )
elseif(CMAKE_CXX_COMPILER_ID MATCHES "MSVC")
    target_compile_options(harness_cpp PRIVATE /W4)
endif()

# Installation
install(TARGETS harness_cpp DESTINATION bin)
