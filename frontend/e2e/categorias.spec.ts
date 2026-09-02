import { test, expect } from "@playwright/test";

const TS = () => Date.now().toString(36);

test.describe("Categorias CRUD", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/categorias");
    await expect(page.getByRole("heading", { name: "Categorias" })).toBeVisible();
  });

  test("muestra tabla con categorias existentes", async ({ page }) => {
    await expect(page.getByRole("table")).toBeVisible();
    await expect(page.getByRole("cell", { name: "Mercado" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "Transporte" })).toBeVisible();
  });

  test("crear y eliminar categoria", async ({ page }) => {
    const nombre = `Cat Test ${TS()}`;

    await page.getByRole("button", { name: "Nueva categoria" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByPlaceholder("Nombre de la categoria").fill(nombre);

    await dialog.getByRole("combobox").click();
    await page.getByRole("option", { name: "gasto" }).click();

    await dialog.getByRole("button", { name: "Crear" }).click();
    await expect(dialog).not.toBeVisible({ timeout: 5000 });

    await expect(page.getByRole("cell", { name: nombre })).toBeVisible({
      timeout: 10000,
    });

    // Delete
    const row = page.locator("tr").filter({ hasText: nombre });
    page.on("dialog", (d) => d.accept());
    await row.getByRole("button", { name: "Borrar" }).click();
    await expect(row).not.toBeVisible({ timeout: 10000 });
  });

  test("editar nombre de categoria", async ({ page }) => {
    const nombre = `Cat Edit ${TS()}`;
    const nombreNuevo = `Cat Edited ${TS()}`;

    // Create
    await page.getByRole("button", { name: "Nueva categoria" }).click();
    let dialog = page.getByRole("dialog");
    await dialog.getByPlaceholder("Nombre de la categoria").fill(nombre);
    await dialog.getByRole("combobox").click();
    await page.getByRole("option", { name: "gasto" }).click();
    await dialog.getByRole("button", { name: "Crear" }).click();
    await expect(dialog).not.toBeVisible({ timeout: 5000 });
    await expect(page.getByRole("cell", { name: nombre })).toBeVisible({
      timeout: 10000,
    });

    // Edit
    const row = page.locator("tr").filter({ hasText: nombre });
    await row.getByRole("button", { name: "Editar" }).click();
    dialog = page.getByRole("dialog");
    await expect(dialog.getByText("Editar categoria")).toBeVisible();
    await dialog.getByPlaceholder("Nombre de la categoria").fill(nombreNuevo);
    await dialog.getByRole("button", { name: "Actualizar" }).click();
    await expect(dialog).not.toBeVisible({ timeout: 5000 });

    await expect(page.getByRole("cell", { name: nombreNuevo })).toBeVisible({
      timeout: 10000,
    });

    // Cleanup
    const editedRow = page.locator("tr").filter({ hasText: nombreNuevo });
    page.on("dialog", (d) => d.accept());
    await editedRow.getByRole("button", { name: "Borrar" }).click();
  });
});
