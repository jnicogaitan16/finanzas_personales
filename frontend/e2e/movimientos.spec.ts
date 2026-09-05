import { test, expect, Page } from "@playwright/test";

const TS = () => Date.now().toString(36);

async function crearMovimiento(page: Page, datos: { monto: string; descripcion: string }) {
  // Navigate to movimientos and open create dialog
  await page.goto("/movimientos");
  await page.waitForTimeout(1000);

  // Use FAB or direct URL with ?new=1
  await page.goto("/movimientos?new=1");
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible({ timeout: 5000 });

  // Fill monto (inputMode numeric, formatted as COP)
  const montoInput = dialog.locator("input").first();
  await montoInput.fill(datos.monto);

  // Fill descripcion
  await dialog.getByPlaceholder("Uber, Mercado, Netflix...").fill(datos.descripcion);

  await dialog.getByRole("button", { name: "Crear" }).click();
  await expect(dialog).not.toBeVisible({ timeout: 5000 });
}

test.describe("Movimientos", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/movimientos");
    await expect(page.getByRole("heading", { name: "Gastos" })).toBeVisible();
  });

  test("muestra lista de movimientos", async ({ page }) => {
    // Should show the expandable list (not a table)
    await page.waitForTimeout(2000);
    // Either shows items or "Sin movimientos"
    const hasItems = await page.locator("[class*='rounded-2xl']").count();
    expect(hasItems).toBeGreaterThan(0);
  });

  test("crear y eliminar movimiento", async ({ page }) => {
    const desc = `Test ${TS()}`;
    await crearMovimiento(page, { monto: "15000", descripcion: desc });

    await page.goto("/movimientos");
    await expect(page.getByText(desc)).toBeVisible({ timeout: 10000 });

    // Tap to expand
    await page.getByText(desc).click();

    // Click Eliminar
    page.on("dialog", (d) => d.accept());
    await page.getByRole("button", { name: "Eliminar" }).click();
    await expect(page.getByText(desc)).not.toBeVisible({ timeout: 10000 });
  });
});
