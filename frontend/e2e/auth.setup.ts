import { test as setup, expect } from "@playwright/test";
import * as OTPAuth from "otpauth";
import { existsSync, unlinkSync } from "fs";

const AUTH_FILE = "e2e/.auth/session.json";

setup("authenticate", async ({ page }) => {
  // Always regenerate session to avoid stale tokens
  if (existsSync(AUTH_FILE)) unlinkSync(AUTH_FILE);

  const user = process.env.TEST_ADMIN_USER || process.env.ADMIN_USER || "admin";
  const pass = process.env.TEST_ADMIN_PASSWORD || process.env.ADMIN_PASSWORD || "admin";
  const totpSecret = process.env.ADMIN_TOTP_SECRET || "";

  await page.goto("/login");
  await page.locator('input[name="username"]').fill(user);
  await page.locator('input[name="password"]').fill(pass);

  if (totpSecret) {
    const totpInput = page.locator('input[name="totp_code"]');
    await totpInput.waitFor({ state: "visible", timeout: 3000 });
    const totp = new OTPAuth.TOTP({ secret: totpSecret });
    await totpInput.fill(totp.generate());
  }

  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL("/", { timeout: 15000 });
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

  await page.context().storageState({ path: AUTH_FILE });
});
