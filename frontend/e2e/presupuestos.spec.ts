import { test, expect } from "@playwright/test";

test.describe("Presupuestos", () => {
  test("muestra pagina y boton de crear", async ({ page }) => {
    await page.goto("/presupuestos");
    await expect(page.getByRole("heading", { name: "Presupuestos" })).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Nuevo presupuesto" }),
    ).toBeVisible();
  });

  test.skip("crear presupuesto y navegacion de meses", async ({ page }) => {
    await page.goto("/presupuestos");
    await expect(page.getByRole("heading", { name: "Presupuestos" })).toBeVisible();
    const mes = new Date().toISOString().slice(0, 7);

    await page.getByRole("button", { name: "Nuevo presupuesto" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    // Select user (first combobox)
    await dialog.getByRole("combobox").first().click();
    await page.getByRole("option").first().click();
    // Wait for dropdown to close
    await expect(page.getByRole("option").first()).not.toBeVisible({ timeout: 2000 }).catch(() => {});

    // Select category (second combobox)
    await dialog.getByRole("combobox").nth(1).click();
    await page.getByRole("option").first().click();
    await expect(page.getByRole("option").first()).not.toBeVisible({ timeout: 2000 }).catch(() => {});

    // Fill monto (input type=number) and mes (text input)
    await dialog.locator('input[type="number"]').fill("500000");
    await dialog.getByPlaceholder("2026-09").fill(mes);
    await dialog.getByRole("button", { name: "Crear" }).click();
    await expect(dialog).not.toBeVisible({ timeout: 10000 });
    await expect(page.getByText("$500.000")).toBeVisible({ timeout: 10000 });

    // Month navigation
    const monthLabel = page.locator("span.text-sm.font-medium").first();
    const initialMonth = await monthLabel.textContent();
    const prevButton = page
      .locator("button")
      .filter({ has: page.locator("svg.lucide-chevron-left") });
    await prevButton.click();
    const newMonth = await monthLabel.textContent();
    expect(newMonth).not.toBe(initialMonth);
  });
});
