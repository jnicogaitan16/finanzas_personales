import { test as setup, expect } from "@playwright/test";
import { existsSync, unlinkSync } from "fs";

const AUTH_FILE = "e2e/.auth/session.json";

setup("authenticate", async ({ page }) => {
  if (existsSync(AUTH_FILE)) unlinkSync(AUTH_FILE);

  const user = process.env.TEST_ADMIN_USER || process.env.ADMIN_USER || "Nico";
  const pass = process.env.TEST_ADMIN_PASSWORD || process.env.ADMIN_PASSWORD || "testpass123";

  await page.goto("/login");
  await page.locator('input[name="username"]').fill(user);
  await page.locator('input[name="password"]').fill(pass);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL("/", { timeout: 15000 });

  await page.context().storageState({ path: AUTH_FILE });
});
