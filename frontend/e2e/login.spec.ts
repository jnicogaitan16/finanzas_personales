import { test, expect } from "@playwright/test";

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
      page.getByText("Usuario o contrasena incorrectos"),
    ).toBeVisible();
  });

  test("login exitoso redirige al dashboard", async ({ page }) => {
    const user = process.env.TEST_ADMIN_USER || process.env.ADMIN_USER || "Nico";
    const pass = process.env.TEST_ADMIN_PASSWORD || process.env.ADMIN_PASSWORD || "testpass123";

    await page.goto("/login");
    await page.locator('input[name="username"]').fill(user);
    await page.locator('input[name="password"]').fill(pass);
    await page.getByRole("button", { name: "Entrar" }).click();

    await page.waitForURL("/");
    await expect(page.getByText("Dashboard")).toBeVisible();
  });

  test("pagina protegida redirige a login sin sesion", async ({ page }) => {
    await page.goto("/movimientos");
    await expect(page).toHaveURL(/login/);
  });
});
