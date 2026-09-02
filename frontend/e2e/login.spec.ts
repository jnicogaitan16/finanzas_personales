import { test, expect } from "@playwright/test";
import * as OTPAuth from "otpauth";

// These tests don't use the authenticated session
test.use({ storageState: { cookies: [], origins: [] } });

test.describe("Login", () => {
  test("credenciales invalidas muestra error", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByText("Ingresa tus credenciales")).toBeVisible();

    await page.locator('input[name="username"]').fill("wrong");
    await page.locator('input[name="password"]').fill("wrong");
    await page.getByRole("button", { name: "Entrar" }).click();

    await expect(
      page.getByText("Usuario, contrasena o codigo 2FA incorrectos"),
    ).toBeVisible();
  });

  test("login exitoso redirige al dashboard", async ({ page }) => {
    const user = process.env.TEST_ADMIN_USER || process.env.ADMIN_USER || "admin";
    const pass = process.env.TEST_ADMIN_PASSWORD || process.env.ADMIN_PASSWORD || "admin";
    const totpSecret = process.env.ADMIN_TOTP_SECRET || "";

    await page.goto("/login");
    await page.locator('input[name="username"]').fill(user);
    await page.locator('input[name="password"]').fill(pass);

    const totpInput = page.locator('input[name="totp_code"]');
    if (totpSecret && await totpInput.isVisible({ timeout: 1000 }).catch(() => false)) {
      const totp = new OTPAuth.TOTP({ secret: totpSecret });
      await totpInput.fill(totp.generate());
    }

    await page.getByRole("button", { name: "Entrar" }).click();

    await page.waitForURL("/");
    await expect(page.getByText("Dashboard")).toBeVisible();
  });

  test("pagina protegida redirige a login sin sesion", async ({ page }) => {
    await page.goto("/movimientos");
    await expect(page).toHaveURL(/login/);
  });
});
