# Emscripten toolchain file for CMake
# Usage: cmake -DCMAKE_TOOLCHAIN_FILE=cmake/Emscripten.cmake ..

# Emscripten settings
set(CMAKE_SYSTEM_NAME Emscripten)
set(CMAKE_SYSTEM_VERSION 1)

# Find emcc compiler
find_program(CMAKE_C_COMPILER emcc)
find_program(CMAKE_CXX_COMPILER em++)
find_program(CMAKE_AR emar)
find_program(CMAKE_RANLIB emranlib)

if(NOT CMAKE_C_COMPILER)
    message(FATAL_ERROR "emcc not found. Install Emscripten: brew install emscripten")
endif()

# Emscripten compile flags
set(EMSCRIPTEN_COMPILE_FLAGS "-s USE_PTHREADS=0 -s ALLOW_MEMORY_GROWTH=1")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${EMSCRIPTEN_COMPILE_FLAGS}")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${EMSCRIPTEN_COMPILE_FLAGS}")

# Emscripten link flags
set(EMSCRIPTEN_LINK_FLAGS
    "-s WASM=1"
    "-s ALLOW_MEMORY_GROWTH=1"
    "-s NO_EXIT_RUNTIME=1"
    "-s EXPORTED_RUNTIME_METHODS=['ccall','cwrap']"
    "-s EXPORT_ES6=1"
    "-s MODULARIZE=1"
    "-s EXPORT_NAME='createAgenkitModule'"
)

string(REPLACE ";" " " EMSCRIPTEN_LINK_FLAGS_STR "${EMSCRIPTEN_LINK_FLAGS}")
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} ${EMSCRIPTEN_LINK_FLAGS_STR}")
set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} ${EMSCRIPTEN_LINK_FLAGS_STR}")
set(CMAKE_MODULE_LINKER_FLAGS "${CMAKE_MODULE_LINKER_FLAGS} ${EMSCRIPTEN_LINK_FLAGS_STR}")

# Set the target architecture
set(CMAKE_C_COMPILER_TARGET wasm32-unknown-emscripten)
set(CMAKE_CXX_COMPILER_TARGET wasm32-unknown-emscripten)

# Skip compiler tests (Emscripten handles this differently)
set(CMAKE_C_COMPILER_WORKS TRUE)
set(CMAKE_CXX_COMPILER_WORKS TRUE)

message(STATUS "Emscripten toolchain configured")
message(STATUS "Emscripten compiler: ${CMAKE_CXX_COMPILER}")
