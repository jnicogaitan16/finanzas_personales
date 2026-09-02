import { test, expect } from "@playwright/test";

const TS = () => Date.now().toString(36);
const TODAY = new Date().toISOString().split("T")[0]; // YYYY-MM-DD

/** Find input inside the div that contains a label with the given text */
function fieldByLabel(
  parent: ReturnType<typeof import("@playwright/test").Page.prototype.locator>,
  label: string,
) {
  return parent.locator(`div:has(> label:text-is("${label}")) input`);
}

test.describe("Cuotas TDC", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/cuotas");
    await expect(
      page.getByRole("heading", { name: "Compras en cuotas" }),
    ).toBeVisible();
  });

  test("muestra cards de resumen", async ({ page }) => {
    await expect(page.getByText("Cuota mensual total")).toBeVisible();
    await expect(page.getByText("Deuda total")).toBeVisible();
    await expect(page.getByText("Compras activas")).toBeVisible();
  });

  test("crear compra en cuotas", async ({ page }) => {
    const establecimiento = `Test Cuota ${TS()}`;

    await page.getByRole("button", { name: "Nueva compra" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    await dialog.locator("select").first().selectOption({ index: 1 });
    await dialog.getByPlaceholder("Nombre del comercio").fill(establecimiento);
    await fieldByLabel(dialog, "Fecha compra").fill(TODAY);
    await fieldByLabel(dialog, "Valor total").fill("600000");
    await fieldByLabel(dialog, "No. cuotas total").fill("12");

    await dialog.getByRole("button", { name: "Crear" }).click();
    await expect(dialog).not.toBeVisible({ timeout: 10000 });

    await expect(page.getByText(establecimiento)).toBeVisible({
      timeout: 10000,
    });

    // Cleanup
    const row = page.locator("tr").filter({ hasText: establecimiento });
    page.on("dialog", (d) => d.accept());
    await row.getByText("Eliminar").click();
    await expect(row).not.toBeVisible({ timeout: 10000 });
  });

  test("editar cuota existente", async ({ page }) => {
    const nombre = `Test Edit Cuota ${TS()}`;

    // Create
    await page.getByRole("button", { name: "Nueva compra" }).click();
    let dialog = page.getByRole("dialog");
    await dialog.locator("select").first().selectOption({ index: 1 });
    await dialog.getByPlaceholder("Nombre del comercio").fill(nombre);
    await fieldByLabel(dialog, "Fecha compra").fill(TODAY);
    await fieldByLabel(dialog, "Valor total").fill("300000");
    await fieldByLabel(dialog, "No. cuotas total").fill("6");
    await dialog.getByRole("button", { name: "Crear" }).click();
    await expect(dialog).not.toBeVisible({ timeout: 10000 });
    await expect(page.getByText(nombre)).toBeVisible({ timeout: 10000 });

    // Edit
    const row = page.locator("tr").filter({ hasText: nombre });
    await row.getByText("Editar").click();
    dialog = page.getByRole("dialog");
    await expect(dialog.getByText("Editar compra en cuotas")).toBeVisible();
    await fieldByLabel(dialog, "Cuotas pagadas").fill("2");
    await dialog.getByRole("button", { name: "Guardar cambios" }).click();
    await expect(dialog).not.toBeVisible({ timeout: 10000 });

    await expect(row.getByText("2/6")).toBeVisible({ timeout: 10000 });

    // Cleanup
    page.on("dialog", (d) => d.accept());
    await row.getByText("Eliminar").click();
  });
});
