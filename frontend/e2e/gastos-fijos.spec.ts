import { test, expect } from "@playwright/test";

const TS = () => Date.now().toString(36);

test.describe("Gastos Fijos", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/gastos-fijos");
    await expect(page.getByRole("heading", { name: "Gastos Fijos" })).toBeVisible();
  });

  test("crear gasto fijo y verificar en tabla", async ({ page }) => {
    const nombre = `Test GF ${TS()}`;

    await page.getByRole("button", { name: "Nuevo gasto fijo" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    // Shadcn Select combos
    const userCombo = dialog.locator('[role="combobox"]').first();
    await userCombo.click();
    await page.getByRole("option").first().click();

    const catCombo = dialog.locator('[role="combobox"]').nth(1);
    await catCombo.click();
    await page.getByRole("option").first().click();

    await dialog.getByPlaceholder("Arriendo, Internet, etc.").fill(nombre);
    await dialog.getByPlaceholder("0").first().fill("150000");

    await dialog.getByRole("button", { name: "Crear" }).click();
    await expect(dialog).not.toBeVisible({ timeout: 5000 });

    await expect(page.getByText(nombre)).toBeVisible({ timeout: 10000 });

    // Cleanup
    const row = page.locator("tr").filter({ hasText: nombre });
    page.on("dialog", (d) => d.accept());
    await row.getByRole("button", { name: "Borrar" }).click();
    await expect(row).not.toBeVisible({ timeout: 10000 });
  });

  test("toggle activar/desactivar gasto fijo", async ({ page }) => {
    const nombre = `Test Toggle ${TS()}`;

    // Create
    await page.getByRole("button", { name: "Nuevo gasto fijo" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.locator('[role="combobox"]').first().click();
    await page.getByRole("option").first().click();
    await dialog.locator('[role="combobox"]').nth(1).click();
    await page.getByRole("option").first().click();
    await dialog.getByPlaceholder("Arriendo, Internet, etc.").fill(nombre);
    await dialog.getByPlaceholder("0").first().fill("100000");
    await dialog.getByRole("button", { name: "Crear" }).click();
    await expect(dialog).not.toBeVisible({ timeout: 5000 });

    const row = page.locator("tr").filter({ hasText: nombre });
    await expect(row).toBeVisible({ timeout: 10000 });

    // Deactivate
    await row.getByRole("button", { name: "Desactivar" }).click();
    await expect(row.getByRole("button", { name: "Activar" })).toBeVisible({
      timeout: 10000,
    });

    // Reactivate
    await row.getByRole("button", { name: "Activar" }).click();
    await expect(
      row.getByRole("button", { name: "Desactivar" }),
    ).toBeVisible({ timeout: 10000 });

    // Cleanup — wait for stability after toggle re-render, then delete
    page.on("dialog", (d) => d.accept());
    const deleteBtn = page
      .locator("tr")
      .filter({ hasText: nombre })
      .getByRole("button", { name: "Borrar" });
    await deleteBtn.waitFor({ state: "visible" });
    await deleteBtn.click({ force: true });
  });

  test("crear gasto fijo compartido con porcentaje", async ({ page }) => {
    const nombre = `Test Comp ${TS()}`;

    await page.getByRole("button", { name: "Nuevo gasto fijo" }).click();
    const dialog = page.getByRole("dialog");

    await dialog.locator('[role="combobox"]').first().click();
    await page.getByRole("option").first().click();
    await dialog.locator('[role="combobox"]').nth(1).click();
    await page.getByRole("option").first().click();

    await dialog.getByPlaceholder("Arriendo, Internet, etc.").fill(nombre);
    await dialog.getByPlaceholder("0").first().fill("200000");

    // Mark as shared
    await dialog.getByText("Compartido").click();
    const pctInput = dialog.getByPlaceholder("50");
    await expect(pctInput).toBeVisible();
    await pctInput.fill("60");

    await dialog.getByRole("button", { name: "Crear" }).click();
    await expect(dialog).not.toBeVisible({ timeout: 5000 });

    const row = page.locator("tr").filter({ hasText: nombre });
    await expect(row).toBeVisible({ timeout: 10000 });

    // Cleanup
    page.on("dialog", (d) => d.accept());
    await row.getByRole("button", { name: "Borrar" }).click();
  });
});
