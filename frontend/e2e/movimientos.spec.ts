import { test, expect, Page } from "@playwright/test";

const TS = () => Date.now().toString(36);

async function crearMovimiento(
  page: Page,
  datos: {
    monto: string;
    descripcion: string;
    medio_pago?: string;
    compartido?: boolean;
  },
) {
  await page.getByRole("button", { name: "Nuevo movimiento" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();

  // Select first user (native select, first option is "Seleccionar")
  const userSelect = dialog.locator("select").first();
  await userSelect.selectOption({ index: 1 });

  // Fill monto (input type=number with placeholder "0")
  await dialog.locator('input[type="number"]').first().fill(datos.monto);

  // Fill descripcion
  await dialog.getByPlaceholder("Descripcion").fill(datos.descripcion);

  if (datos.medio_pago) {
    const medioPagoSelect = dialog
      .locator("select")
      .filter({ has: page.locator(`option[value="${datos.medio_pago}"]`) });
    await medioPagoSelect.selectOption(datos.medio_pago);
  }

  if (datos.compartido) {
    await dialog.getByText("Compartido").click();
  }

  await dialog.getByRole("button", { name: "Crear" }).click();
  await expect(dialog).not.toBeVisible({ timeout: 5000 });
}

test.describe("Movimientos CRUD", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/movimientos");
    await expect(page.getByRole("heading", { name: "Movimientos" })).toBeVisible();
  });

  test("muestra tabla de movimientos", async ({ page }) => {
    await expect(page.getByRole("table")).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Fecha" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Monto" })).toBeVisible();
  });

  test("crear movimiento basico", async ({ page }) => {
    const desc = `Test mov ${TS()}`;
    await crearMovimiento(page, { monto: "25000", descripcion: desc });

    await expect(page.getByText(desc)).toBeVisible({ timeout: 10000 });

    // Cleanup
    const row = page.locator("tr").filter({ hasText: desc });
    page.on("dialog", (d) => d.accept());
    await row.getByText("Borrar").click();
    await expect(row).not.toBeVisible({ timeout: 10000 });
  });

  test("editar movimiento cambia el monto", async ({ page }) => {
    const desc = `Test edit ${TS()}`;
    await crearMovimiento(page, { monto: "10000", descripcion: desc });
    await expect(page.getByText(desc)).toBeVisible({ timeout: 10000 });

    // Click edit
    const row = page.locator("tr").filter({ hasText: desc });
    await row.getByText("Editar").click();

    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText("Editar movimiento")).toBeVisible();
    // Monto is the first number input
    await dialog.locator('input[type="number"]').first().fill("99000");
    await dialog.getByRole("button", { name: "Actualizar" }).click();
    await expect(dialog).not.toBeVisible({ timeout: 5000 });

    await expect(page.getByText("$99.000")).toBeVisible({ timeout: 10000 });

    // Cleanup
    page.on("dialog", (d) => d.accept());
    const updatedRow = page.locator("tr").filter({ hasText: desc });
    await updatedRow.getByText("Borrar").click();
  });

  test("eliminar movimiento con confirmacion", async ({ page }) => {
    const desc = `Test del ${TS()}`;
    await crearMovimiento(page, { monto: "5000", descripcion: desc });
    await expect(page.getByText(desc)).toBeVisible({ timeout: 10000 });

    // Dismiss confirm — movimiento persists
    page.once("dialog", (d) => d.dismiss());
    const row = page.locator("tr").filter({ hasText: desc });
    await row.getByText("Borrar").click();
    await expect(page.getByText(desc)).toBeVisible();

    // Accept confirm — movimiento disappears
    page.on("dialog", (d) => d.accept());
    await row.getByText("Borrar").click();
    await expect(row).not.toBeVisible({ timeout: 10000 });
  });

  test("filtrar movimientos por usuario", async ({ page }) => {
    // Shadcn Select trigger
    const trigger = page.locator("button").filter({ hasText: "Todos" });
    if (await trigger.isVisible()) {
      await trigger.click();
      const options = page.getByRole("option");
      const count = await options.count();
      if (count > 1) {
        const userName = await options.nth(1).textContent();
        await options.nth(1).click();
        await page.waitForTimeout(500);
        const rows = page.locator("table tbody tr");
        const rowCount = await rows.count();
        for (let i = 0; i < Math.min(rowCount, 5); i++) {
          const userCell = await rows.nth(i).locator("td").nth(1).textContent();
          expect(userCell?.toLowerCase()).toBe(userName?.toLowerCase());
        }
      }
    }
  });

  test("validacion: boton deshabilitado y TC muestra cuotas", async ({ page }) => {
    await page.getByRole("button", { name: "Nuevo movimiento" }).click();
    const dialog = page.getByRole("dialog");

    // Button disabled without user and monto
    await expect(dialog.getByRole("button", { name: "Crear" })).toBeDisabled();

    // Select TC → shows cuotas field
    const medioPagoSelect = dialog
      .locator("select")
      .filter({ has: page.locator('option[value="tarjeta_credito"]') });
    await medioPagoSelect.selectOption("tarjeta_credito");
    await expect(dialog.locator('input[type="number"][min="1"]')).toBeVisible();

    await dialog.getByRole("button", { name: "Cancelar" }).click();
  });
});
