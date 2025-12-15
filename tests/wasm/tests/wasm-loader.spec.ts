import { test, expect } from '@playwright/test';

/**
 * Test WASM module loading across browsers
 */
test.describe('WASM Module Loading', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display page title', async ({ page }) => {
    await expect(page).toHaveTitle(/Agenkit WASM/);
  });

  test('should load echo agent by default', async ({ page }) => {
    // Wait for agent to load
    await expect(page.locator('text=Agent Loaded')).toBeVisible({ timeout: 10000 });

    // Check agent name is displayed
    await expect(page.locator('text=/Name: react-echo_example/')).toBeVisible();

    // Check capabilities are displayed
    await expect(page.locator('text=/Capabilities:/')).toBeVisible();
  });

  test('should show loading state while initializing', async ({ page }) => {
    // Check for loading indicator (may be brief)
    const loadingText = page.locator('text=Loading agent');
    const isVisible = await loadingText.isVisible().catch(() => false);

    // Either loading is visible or already loaded (fast connection)
    if (!isVisible) {
      await expect(page.locator('text=Agent Loaded')).toBeVisible();
    }
  });

  test('should have module selector with 5 options', async ({ page }) => {
    await expect(page.locator('select#module, select')).toBeVisible();

    // Count options
    const options = await page.locator('select option').count();
    expect(options).toBe(5);
  });

  test('should switch between WASM modules', async ({ page }) => {
    // Wait for initial agent
    await expect(page.locator('text=Agent Loaded')).toBeVisible({ timeout: 10000 });

    // Switch to reflection module
    await page.selectOption('select', 'reflection_example');

    // Wait for new agent to load
    await expect(page.locator('text=/Name: react-reflection_example/')).toBeVisible({ timeout: 10000 });
  });

  test('should load all 5 WASM modules successfully', async ({ page }) => {
    const modules = [
      'echo_example',
      'reflection_example',
      'sequential_example',
      'parallel_example',
      'react_example',
    ];

    for (const module of modules) {
      await page.selectOption('select', module);
      await expect(page.locator(`text=/Name: react-${module}/`)).toBeVisible({ timeout: 10000 });
    }
  });
});
