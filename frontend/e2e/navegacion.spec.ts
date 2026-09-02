import { test, expect } from "@playwright/test";

test.describe("Navegacion", () => {
  test("navegar entre todas las paginas desde el header", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

    const pages = [
      { link: "Movimientos", url: "/movimientos", heading: "Movimientos" },
      { link: "Categorias", url: "/categorias", heading: "Categorias" },
      { link: "Cuotas", url: "/cuotas", heading: "Compras en cuotas" },
      { link: "Presupuestos", url: "/presupuestos", heading: "Presupuestos" },
      { link: "Compartido", url: "/compartido", heading: "Gastos Compartidos" },
      { link: "Dashboard", url: "/", heading: "Dashboard" },
    ];

    for (const p of pages) {
      await page.getByRole("link", { name: p.link }).click();
      await expect(page).toHaveURL(p.url);
      await expect(page.getByRole("heading", { name: p.heading })).toBeVisible();
    }
  });
});
