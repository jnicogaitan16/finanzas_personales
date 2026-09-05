import { test, expect } from "@playwright/test";

test.describe("Navegacion", () => {
  test("dashboard carga y muestra modulos", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByText("Ingresos")).toBeVisible();
    await expect(page.getByText("Gastos")).toBeVisible();
    await expect(page.getByText("Tarjetas")).toBeVisible();
  });

  test("navegar a gastos desde dashboard", async ({ page }) => {
    await page.goto("/");
    await page.getByText("Gastos").first().click();
    await expect(page).toHaveURL("/movimientos");
    await expect(page.getByRole("heading", { name: "Gastos" })).toBeVisible();
  });

  test("volver al dashboard con back", async ({ page }) => {
    await page.goto("/movimientos");
    await page.getByRole("link", { name: "Finanzas app" }).click();
    await expect(page).toHaveURL("/");
  });
});
