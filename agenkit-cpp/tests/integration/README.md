# C++ Integration Tests

Comprehensive integration tests for agenkit-cpp covering adapters, patterns, evaluation framework, core functionality, and cross-language compatibility.

## Overview

These integration tests verify real functionality, not just mocks. They test:

- **Adapters**: OpenAI, Anthropic/Claude, Ollama, and error handling
- **Patterns**: Sequential, Parallel, Supervisor, Router, Collaborative, HumanInLoop, Fallback
- **Evaluation**: Metrics collection, session recording, regression detection, quality metrics, A/B testing, monitoring
- **Core**: Message serialization, agent interface, Result type, error propagation, metadata handling
- **Cross-Language**: HTTP transport, JSON format, message size handling, unicode support

## Test Coverage

Total: **29 integration tests** across 5 test suites

### Adapter Tests (10 tests)
- `test_integration_adapters`
  - EchoAdapter
  - OpenAIAdapter (requires OPENAI_API_KEY)
  - AnthropicAdapter (requires ANTHROPIC_API_KEY)
  - OllamaAdapter (requires Ollama service)
  - InvalidAPIKeyHandling
  - TimeoutHandling
  - MetadataPreservation
  - ComplexMessageContent
  - ConcurrentRequests
  - AdapterErrorHandling

### Pattern Tests (12 tests)
- `test_integration_patterns`
  - SequentialPattern
  - ParallelPattern
  - SupervisorPattern
  - RouterPattern
  - CollaborativePattern
  - HumanInLoopPattern
  - FallbackPattern
  - PatternComposition
  - PatternErrorHandling
  - PatternMetadataFlow
  - PatternConcurrentExecution
  - PatternInteroperability

### Evaluation Tests (8 tests)
- `test_integration_evaluation`
  - MetricsCollection
  - SessionRecording
  - RegressionDetection
  - QualityMetrics
  - ABTestingWorkflow
  - ProductionMonitoringWorkflow
  - MetricsLifecycle
  - QualityMetricsEdgeCases

### Core Tests (10 tests)
- `test_integration_core`
  - MessageCreationAndSerialization
  - AgentInterfaceCompliance
  - ResultTypeHandling
  - ErrorPropagation
  - MetadataHandling
  - MessageTimestampHandling
  - ConcurrentMessageProcessing
  - MessageContentTypeFlexibility
  - ErrorTypeCoverage
  - CoreFunctionalityConsistency

### Cross-Language Tests (8 tests)
- `test_integration_cross_language`
  - HTTPTransportCompatibility
  - JSONMessageFormatCompatibility
  - HTTPErrorHandlingCompatibility
  - MessageSizeHandlingCompatibility
  - StreamingCompatibility
  - UnicodeCompatibility
  - MetadataTypeConsistency
  - ConcurrentCrossLanguageRequests

## Building Integration Tests

Integration tests are **disabled by default** since they may require external services or API keys.

### Enable Integration Tests

```bash
cd agenkit-cpp
mkdir -p build && cd build

# Enable integration tests
cmake -DAGENKIT_BUILD_INTEGRATION_TESTS=ON ..
cmake --build .
```

### Build Options

```bash
# Build with all test types
cmake -DAGENKIT_BUILD_TESTS=ON -DAGENKIT_BUILD_INTEGRATION_TESTS=ON ..

# Build only integration tests (skip unit tests)
cmake -DAGENKIT_BUILD_TESTS=OFF -DAGENKIT_BUILD_INTEGRATION_TESTS=ON ..

# Build with specific build type
cmake -DAGENKIT_BUILD_INTEGRATION_TESTS=ON -DCMAKE_BUILD_TYPE=Release ..
```

## Running Integration Tests

### Run All Integration Tests

```bash
cd build
ctest -L integration --output-on-failure
```

### Run Specific Test Suite

```bash
# Adapter tests
./tests/integration/test_integration_adapters

# Pattern tests
./tests/integration/test_integration_patterns

# Evaluation tests
./tests/integration/test_integration_evaluation

# Core tests
./tests/integration/test_integration_core

# Cross-language tests
./tests/integration/test_integration_cross_language
```

### Run Specific Test

```bash
# Run only OpenAI adapter test
./tests/integration/test_integration_adapters --gtest_filter="AdapterIntegrationTest.OpenAIAdapter"

# Run all pattern composition tests
./tests/integration/test_integration_patterns --gtest_filter="*Composition*"
```

### Run with Verbose Output

```bash
./tests/integration/test_integration_adapters --gtest_verbose
```

## Required Environment Variables

Some tests require API keys or external services to be available.

### API Keys

```bash
# For OpenAI adapter tests
export OPENAI_API_KEY="sk-..."

# For Claude/Anthropic adapter tests
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Service Configuration

```bash
# Skip Ollama tests if service not available
export SKIP_OLLAMA_TESTS=1

# Custom Ollama endpoint (default: http://localhost:11434)
# Note: Configure in test code if needed
```

## Running Tests Without External Services

### Skip Optional Tests

Tests automatically skip when required services aren't available:

```bash
# Run all tests, skipping those that need unavailable services
./tests/integration/test_integration_adapters
# Output: [  SKIPPED ] AdapterIntegrationTest.OpenAIAdapter (OPENAI_API_KEY not set)
```

### Run Only Local Tests

Tests that don't require external services:
- All Core tests
- All Cross-Language tests (use local HTTP server)
- Echo adapter tests
- Most Pattern tests
- Most Evaluation tests (use temp directories)

```bash
# Run tests that don't need API keys
./tests/integration/test_integration_core
./tests/integration/test_integration_cross_language
./tests/integration/test_integration_evaluation
```

## Troubleshooting

### Tests Fail to Compile

**Issue**: Missing headers or linker errors

**Solution**: Ensure all dependencies are installed:
```bash
# Install nlohmann_json
brew install nlohmann-json  # macOS
apt-get install nlohmann-json3-dev  # Ubuntu

# Rebuild
rm -rf build
mkdir build && cd build
cmake -DAGENKIT_BUILD_INTEGRATION_TESTS=ON ..
cmake --build .
```

### API Tests Fail with Authentication Error

**Issue**: `Authentication` or `InvalidAPIKey` errors

**Solution**: Verify API keys are set correctly:
```bash
echo $OPENAI_API_KEY  # Should print your key
echo $ANTHROPIC_API_KEY  # Should print your key

# If empty, set them:
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Ollama Tests Fail

**Issue**: `Transport` error or connection refused

**Solution**: Start Ollama service:
```bash
# Install Ollama (if not installed)
# Download from https://ollama.ai

# Start Ollama
ollama serve

# Pull a model
ollama pull llama3.2:1b

# Or skip Ollama tests
export SKIP_OLLAMA_TESTS=1
```

### Port Already in Use

**Issue**: Tests fail with "Address already in use" error

**Solution**: Check for processes using test ports:
```bash
# Check ports 18090-18094
lsof -i :18090
lsof -i :18091
# etc.

# Kill process if needed
kill <PID>

# Or wait a few seconds for ports to be released
```

### Cross-Language Tests Timeout

**Issue**: HTTP transport tests timeout

**Solution**:
1. Check firewall settings (tests use localhost)
2. Verify no other service is using test ports (18090-18094)
3. Increase timeout in test code if needed

### Memory or Resource Errors

**Issue**: Tests crash or run out of memory

**Solution**:
1. Run tests individually instead of all at once:
```bash
./tests/integration/test_integration_core
./tests/integration/test_integration_patterns
# etc.
```

2. Close other applications
3. Check for resource leaks in test output

## Test Development Guidelines

### Adding New Integration Tests

1. Choose appropriate test file:
   - `test_adapters.cpp` - New adapter implementations
   - `test_patterns.cpp` - New pattern implementations
   - `test_evaluation.cpp` - Evaluation framework features
   - `test_core.cpp` - Core functionality
   - `test_cross_language.cpp` - Cross-language compatibility

2. Follow existing test patterns:
```cpp
TEST(CategoryTest, FeatureDescription) {
    // Arrange
    auto agent = std::make_shared<adapters::EchoAgent>();
    auto msg = core::Message::with_text("user", "Test");

    // Act
    auto future = agent.process(std::move(msg));
    auto result = future.get();

    // Assert
    ASSERT_TRUE(result.is_ok());
    auto response = result.unwrap();
    EXPECT_EQ(response.role(), "assistant");
}
```

3. Handle optional dependencies:
```cpp
TEST(AdapterTest, ExternalService) {
    const char* api_key = std::getenv("API_KEY");
    if (!api_key || std::string(api_key).empty()) {
        GTEST_SKIP() << "API_KEY not set, skipping test";
    }
    // Test implementation...
}
```

4. Clean up resources:
```cpp
TEST_F(TestFixture, ResourceTest) {
    // Use RAII or explicit cleanup
    std::unique_ptr<Resource> resource = create_resource();
    // Test...
    // Resource automatically cleaned up
}
```

### Best Practices

- **Use RAII**: Ensure resources are cleaned up automatically
- **Test real functionality**: Avoid mocks where possible
- **Handle failures gracefully**: Skip tests when dependencies unavailable
- **Use descriptive names**: Test names should explain what they verify
- **Add documentation**: Comment complex test setups
- **Verify metadata**: Always check metadata preservation
- **Test error paths**: Verify error handling, not just success
- **Clean up ports/files**: Don't leave resources allocated
- **Keep tests independent**: Tests should not depend on each other
- **Use appropriate timeouts**: Balance speed vs. reliability

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y nlohmann-json3-dev

      - name: Build with integration tests
        run: |
          mkdir build && cd build
          cmake -DAGENKIT_BUILD_INTEGRATION_TESTS=ON ..
          cmake --build .

      - name: Run integration tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SKIP_OLLAMA_TESTS: 1
        run: |
          cd build
          ctest -L integration --output-on-failure
```

## Performance Considerations

### Test Duration

- **Core tests**: ~5-10 seconds
- **Cross-language tests**: ~10-20 seconds (starts local servers)
- **Pattern tests**: ~5-15 seconds
- **Evaluation tests**: ~10-20 seconds
- **Adapter tests**: ~30-60 seconds (API calls)

**Total**: ~60-120 seconds for all integration tests

### Parallel Execution

Run tests in parallel for faster execution:

```bash
# Run 4 tests in parallel
ctest -L integration -j4 --output-on-failure
```

## Comparison with Other Languages

This C++ integration test suite achieves **test parity** with:

### Python Integration Tests
- Location: `tests/integration/`
- Coverage: HTTP, gRPC, WebSocket, basic integration, middleware, observability

### Go Integration Tests
- Location: `agenkit-go/tests/integration/`
- Coverage: Basic integration, HTTP server, gRPC server, test helpers

### TypeScript Integration Tests
- Location: `agenkit-ts/tests/integration/`
- Coverage: HTTP transport, agent patterns, cross-language compatibility

The C++ tests provide **equivalent or better coverage** with 29 integration tests covering all major functionality.

## Contributing

When adding integration tests:

1. Follow the test structure in existing files
2. Update this README with new test descriptions
3. Add environment variable requirements
4. Update CMakeLists.txt if adding new test files
5. Ensure tests pass locally before submitting PR
6. Document any new dependencies or requirements

## Support

For issues or questions about integration tests:

1. Check troubleshooting section above
2. Review test output for specific error messages
3. Verify all dependencies are installed
4. Check that required services are running
5. Open an issue with full error output and environment details
