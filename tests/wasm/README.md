# Agenkit WASM Testing

Automated testing infrastructure for @agenkit/wasm across multiple browsers using Playwright.

## Overview

This test suite verifies that WASM modules:
- Load correctly in all major browsers
- Process messages accurately
- Perform consistently across platforms
- Meet performance benchmarks

## Test Coverage

### 1. WASM Module Loading (`wasm-loader.spec.ts`)
- ✅ Page title and initial render
- ✅ Default agent loading (echo)
- ✅ Loading state indicators
- ✅ Module selector functionality
- ✅ Switching between 5 WASM patterns
- ✅ All modules load successfully

### 2. Message Processing (`message-processing.spec.ts`)
- ✅ Input field availability
- ✅ Send button states (enabled/disabled)
- ✅ Message submission and response
- ✅ Processing state indicators
- ✅ Sequential message handling
- ✅ Keyboard shortcuts (Enter, Shift+Enter)
- ✅ Multiline input support

### 3. Cross-Browser Compatibility (`cross-browser.spec.ts`)
- ✅ WebAssembly API detection
- ✅ WASM compilation success
- ✅ Consistent message processing
- ✅ Load time measurements
- ✅ Large message handling
- ✅ Concurrent module switches
- ✅ Browser capability reporting

## Browsers Tested

| Browser | Platform | Status |
|---------|----------|--------|
| **Chromium** | Desktop | ✅ Tested |
| **Firefox** | Desktop | ✅ Tested |
| **WebKit** | Desktop | ✅ Tested |
| **Mobile Chrome** | Android | ✅ Tested |
| **Mobile Safari** | iOS | ✅ Tested |

## Quick Start

### Prerequisites

- Node.js ≥18.0.0
- npm or pnpm

### Installation

```bash
cd tests/wasm
npm install
npm run install:browsers
```

### Running Tests

```bash
# Run all tests (all browsers)
npm test

# Run tests with visible browser
npm run test:headed

# Run specific browser
npm run test:chromium
npm run test:firefox
npm run test:webkit

# Debug mode
npm run test:debug

# View test report
npm run test:report
```

## CI/CD Pipeline

### GitHub Actions Workflow

The `.github/workflows/wasm-ci.yml` workflow runs on:
- **Push to main** (WASM-related files)
- **Pull requests** (WASM-related files)
- **Manual trigger**

### Pipeline Stages

```
1. Build Zig WASM
   ↓
2. Build @agenkit/wasm NPM Package
   ↓
3. Test in Parallel:
   - Chromium tests
   - Firefox tests
   - WebKit tests
   ↓
4. Integration Test (verify all passed)
   ↓
5. Performance Benchmarks
```

### Artifacts

The CI pipeline generates:
- **zig-wasm-modules** - Compiled WASM binaries
- **agenkit-wasm-package** - Built NPM package
- **playwright-report-{browser}** - Test results per browser
- **benchmark-report** - Performance metrics

## Test Configuration

### playwright.config.ts

Key settings:
- **Retries**: 2 in CI, 0 locally
- **Workers**: 1 in CI, unlimited locally
- **Timeouts**: 30s default
- **Screenshots**: Only on failure
- **Video**: Retain on failure
- **Trace**: On first retry

### Project Settings

Each browser project includes:
- Desktop viewport (1280x720)
- Mobile viewport (device-specific)
- WebAssembly enabled
- Performance metrics collection

## Build Verification

Before running tests, verify WASM builds:

```bash
./scripts/verify-wasm-build.sh
```

This checks:
- ✅ Zig WASM files exist and are valid
- ✅ Package WASM files copied correctly
- ✅ @agenkit/wasm package built
- ✅ All artifacts present

## Writing Tests

### Test Structure

```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Setup
  });

  test('should do something', async ({ page }) => {
    // Arrange
    const element = page.locator('selector');

    // Act
    await element.click();

    // Assert
    await expect(page.locator('result')).toBeVisible();
  });
});
```

### Best Practices

1. **Wait for agent loading**:
   ```typescript
   await expect(page.locator('text=Agent Loaded')).toBeVisible({ timeout: 10000 });
   ```

2. **Handle timing**:
   ```typescript
   // Check for fast-disappearing states
   const loading = page.locator('text=Loading');
   const isVisible = await loading.isVisible().catch(() => false);
   if (!isVisible) {
     // Already loaded
   }
   ```

3. **Cross-browser logging**:
   ```typescript
   test('feature', async ({ page, browserName }) => {
     console.log(`${browserName}: Feature test`);
   });
   ```

4. **Timeouts**:
   ```typescript
   // WASM loading can be slow
   await expect(locator).toBeVisible({ timeout: 15000 });
   ```

## Performance Benchmarks

### Expected Load Times

| Module | Size | Expected Load Time |
|--------|------|--------------------|
| echo | 19KB | <3ms |
| reflection | 66KB | <7ms |
| sequential | 23KB | <4ms |
| parallel | 31KB | <4ms |
| react | 33KB | <4ms |

### Performance Tests

```typescript
test('should measure load time', async ({ page, browserName }) => {
  const startTime = Date.now();
  await page.goto('/');
  await expect(page.locator('text=Agent Loaded')).toBeVisible();
  const loadTime = Date.now() - startTime;

  console.log(`${browserName}: Load time = ${loadTime}ms`);
  expect(loadTime).toBeLessThan(5000);
});
```

## Debugging

### Local Debugging

```bash
# Run with visible browser
npm run test:headed

# Debug mode with inspector
npm run test:debug

# Run specific test file
npx playwright test tests/wasm-loader.spec.ts --headed

# Run specific test
npx playwright test -g "should load echo agent"
```

### CI Debugging

1. Check workflow logs in GitHub Actions
2. Download artifacts (test reports, screenshots, videos)
3. Review browser console logs
4. Analyze timing issues

### Common Issues

**WASM module not found:**
```
Error: Failed to fetch WASM file
```
**Solution:** Run build verification script

**Timeout errors:**
```
Error: Timeout 30000ms exceeded
```
**Solution:** Increase timeout or check dev server

**Browser not installed:**
```
Error: Browser executable not found
```
**Solution:** Run `npm run install:browsers`

## Local Development

### Running Tests Locally

```bash
# Terminal 1: Start dev server
cd ../../examples/browser/react-example
npm install
npm run dev

# Terminal 2: Run tests
cd tests/wasm
SKIP_DEV_SERVER=true npm test
```

### Watch Mode

Playwright doesn't have built-in watch mode, but you can use:

```bash
# Install nodemon
npm install -g nodemon

# Watch and rerun
nodemon --watch tests --exec "npm test"
```

## Test Reports

### HTML Report

```bash
npm run test:report
```

Opens browser with:
- Test results by browser
- Screenshots on failure
- Video recordings
- Timing information
- Flaky test detection

### CI Reports

GitHub Actions automatically:
- Uploads HTML reports as artifacts
- Shows summary in workflow
- Flags failures
- Retains artifacts for 7 days

## Maintenance

### Updating Tests

When adding new features:
1. Add test cases to appropriate spec file
2. Update expected behaviors
3. Run tests locally
4. Verify CI passes

### Updating Browsers

```bash
# Update Playwright
npm install @playwright/test@latest

# Reinstall browsers
npm run install:browsers
```

### Performance Regression

If load times increase:
1. Check module sizes: `du -h packages/wasm/wasm/*.wasm`
2. Profile with browser DevTools
3. Compare with benchmarks
4. Investigate compilation settings

## Integration with Other Tests

This test suite focuses on browser WASM functionality. See also:
- **agenkit-zig/tests/** - Zig native tests
- **agenkit-rust/tests/** - Rust native tests
- **agenkit-cpp/tests/** - C++ native tests
- **packages/wasm/examples/** - Manual testing examples

## Contributing

When contributing tests:
1. Follow existing patterns
2. Add descriptive test names
3. Include browser logging
4. Handle timing appropriately
5. Update this README
6. Ensure CI passes

## Resources

- [Playwright Documentation](https://playwright.dev/)
- [WebAssembly MDN](https://developer.mozilla.org/en-US/docs/WebAssembly)
- [@agenkit/wasm Package](../../packages/wasm/README.md)
- [Browser Examples](../../examples/browser/README.md)

## License

MIT

## Links

- [Issue #289](https://github.com/agenkit/agenkit/issues/289)
- [Agenkit Repository](https://github.com/agenkit/agenkit)
- [CI/CD Workflow](../../.github/workflows/wasm-ci.yml)
