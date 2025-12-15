import { test, expect } from '@playwright/test';

/**
 * Test WASM compatibility across different browsers
 * These tests verify that WASM modules work consistently across
 * Chromium, Firefox, and WebKit
 */
test.describe('Cross-Browser WASM Compatibility', () => {
  test('should detect WebAssembly support', async ({ page, browserName }) => {
    await page.goto('/');

    // Check if WebAssembly is supported
    const wasmSupported = await page.evaluate(() => {
      return typeof WebAssembly !== 'undefined';
    });

    expect(wasmSupported).toBe(true);
    console.log(`${browserName}: WebAssembly supported = ${wasmSupported}`);
  });

  test('should successfully compile WASM module', async ({ page, browserName }) => {
    await page.goto('/');

    // Wait for agent to load successfully
    await expect(page.locator('text=Agent Loaded')).toBeVisible({ timeout: 15000 });

    console.log(`${browserName}: WASM module compiled and loaded successfully`);
  });

  test('should process messages consistently', async ({ page, browserName }) => {
    await page.goto('/');
    await expect(page.locator('text=Agent Loaded')).toBeVisible({ timeout: 15000 });

    const textarea = page.locator('textarea');
    const sendButton = page.locator('button', { hasText: /Send to Agent/i });

    // Send test message
    const testMessage = `Cross-browser test from ${browserName}`;
    await textarea.fill(testMessage);
    await sendButton.click();

    // Verify response
    await expect(page.locator('text=/Agent Response/')).toBeVisible({ timeout: 5000 });
    await expect(page.locator(`text=/${testMessage}/`)).toBeVisible();

    console.log(`${browserName}: Message processed successfully`);
  });

  test('should measure WASM load time', async ({ page, browserName }) => {
    const startTime = Date.now();

    await page.goto('/');
    await expect(page.locator('text=Agent Loaded')).toBeVisible({ timeout: 15000 });

    const loadTime = Date.now() - startTime;

    console.log(`${browserName}: WASM load time = ${loadTime}ms`);

    // Reasonable load time threshold (should be under 5 seconds)
    expect(loadTime).toBeLessThan(5000);
  });

  test('should handle large messages', async ({ page, browserName }) => {
    await page.goto('/');
    await expect(page.locator('text=Agent Loaded')).toBeVisible({ timeout: 15000 });

    const textarea = page.locator('textarea');
    const sendButton = page.locator('button', { hasText: /Send to Agent/i });

    // Create a large message (1KB)
    const largeMessage = 'A'.repeat(1024);
    await textarea.fill(largeMessage);
    await sendButton.click();

    // Verify response
    await expect(page.locator('text=/Agent Response/')).toBeVisible({ timeout: 10000 });

    console.log(`${browserName}: Large message processed successfully`);
  });

  test('should support concurrent module switches', async ({ page, browserName }) => {
    await page.goto('/');
    await expect(page.locator('text=Agent Loaded')).toBeVisible({ timeout: 15000 });

    // Quickly switch between modules
    await page.selectOption('select', 'reflection_example');
    await page.waitForTimeout(100);
    await page.selectOption('select', 'sequential_example');
    await page.waitForTimeout(100);
    await page.selectOption('select', 'echo_example');

    // Wait for final module to load
    await expect(page.locator('text=/Name: react-echo_example/')).toBeVisible({ timeout: 10000 });

    console.log(`${browserName}: Concurrent module switches handled successfully`);
  });

  test('should report browser and WASM capabilities', async ({ page, browserName }) => {
    await page.goto('/');

    const capabilities = await page.evaluate(() => {
      return {
        wasm: typeof WebAssembly !== 'undefined',
        wasmCompile: typeof WebAssembly.compile === 'function',
        wasmInstantiate: typeof WebAssembly.instantiate === 'function',
        wasmMemory: typeof WebAssembly.Memory === 'function',
        wasmTable: typeof WebAssembly.Table === 'function',
        bigInt64Array: typeof BigInt64Array !== 'undefined',
        sharedArrayBuffer: typeof SharedArrayBuffer !== 'undefined',
      };
    });

    console.log(`${browserName} capabilities:`, capabilities);

    // All modern browsers should support these core WASM features
    expect(capabilities.wasm).toBe(true);
    expect(capabilities.wasmCompile).toBe(true);
    expect(capabilities.wasmInstantiate).toBe(true);
    expect(capabilities.wasmMemory).toBe(true);
  });
});
