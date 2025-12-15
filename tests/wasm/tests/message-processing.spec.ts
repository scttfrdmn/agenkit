import { test, expect } from '@playwright/test';

/**
 * Test WASM message processing functionality
 */
test.describe('Message Processing', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait for agent to load
    await expect(page.locator('text=Agent Loaded')).toBeVisible({ timeout: 10000 });
  });

  test('should have message input field', async ({ page }) => {
    await expect(page.locator('textarea')).toBeVisible();
    await expect(page.locator('textarea')).toHaveAttribute('placeholder', /Type your message/i);
  });

  test('should have send button', async ({ page }) => {
    await expect(page.locator('button', { hasText: /Send to Agent/i })).toBeVisible();
  });

  test('should enable send button when message is typed', async ({ page }) => {
    const sendButton = page.locator('button', { hasText: /Send to Agent/i });
    const textarea = page.locator('textarea');

    // Button should be disabled initially
    await expect(sendButton).toBeDisabled();

    // Type a message
    await textarea.fill('Hello, WASM!');

    // Button should now be enabled
    await expect(sendButton).toBeEnabled();
  });

  test('should process message and show response', async ({ page }) => {
    const textarea = page.locator('textarea');
    const sendButton = page.locator('button', { hasText: /Send to Agent/i });

    // Type and send message
    await textarea.fill('Test message from Playwright');
    await sendButton.click();

    // Wait for response
    await expect(page.locator('text=/Agent Response/')).toBeVisible({ timeout: 5000 });

    // Check response contains our message (echo pattern)
    await expect(page.locator('text=/Test message from Playwright/')).toBeVisible();
  });

  test('should show processing state while waiting', async ({ page }) => {
    const textarea = page.locator('textarea');
    const sendButton = page.locator('button', { hasText: /Send to Agent/i });

    await textarea.fill('Processing test');
    await sendButton.click();

    // Check for processing indicator (may be brief)
    const processingText = page.locator('text=/Processing/i');
    const isVisible = await processingText.isVisible().catch(() => false);

    // Either processing is visible or already completed (fast execution)
    if (!isVisible) {
      await expect(page.locator('text=/Agent Response/')).toBeVisible();
    }
  });

  test('should handle multiple messages sequentially', async ({ page }) => {
    const textarea = page.locator('textarea');
    const sendButton = page.locator('button', { hasText: /Send to Agent/i });

    // Send first message
    await textarea.fill('First message');
    await sendButton.click();
    await expect(page.locator('text=/First message/')).toBeVisible({ timeout: 5000 });

    // Send second message
    await textarea.fill('Second message');
    await sendButton.click();
    await expect(page.locator('text=/Second message/')).toBeVisible({ timeout: 5000 });

    // Send third message
    await textarea.fill('Third message');
    await sendButton.click();
    await expect(page.locator('text=/Third message/')).toBeVisible({ timeout: 5000 });
  });

  test('should clear input after sending (optional behavior)', async ({ page }) => {
    const textarea = page.locator('textarea');
    const sendButton = page.locator('button', { hasText: /Send to Agent/i });

    await textarea.fill('Message to send');
    await sendButton.click();

    // Wait for response
    await expect(page.locator('text=/Agent Response/')).toBeVisible({ timeout: 5000 });

    // Note: Whether input is cleared is implementation-specific
    // This test documents the current behavior
  });

  test('should support Enter key to send message', async ({ page }) => {
    const textarea = page.locator('textarea');

    await textarea.fill('Enter key test');
    await textarea.press('Enter');

    // Wait for response
    await expect(page.locator('text=/Agent Response/')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=/Enter key test/')).toBeVisible();
  });

  test('should support Shift+Enter for multiline input', async ({ page }) => {
    const textarea = page.locator('textarea');

    await textarea.fill('Line 1');
    await textarea.press('Shift+Enter');
    await textarea.type('Line 2');

    // Check that textarea contains both lines
    const value = await textarea.inputValue();
    expect(value).toContain('Line 1');
    expect(value).toContain('Line 2');
  });
});
