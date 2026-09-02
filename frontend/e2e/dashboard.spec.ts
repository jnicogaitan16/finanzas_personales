import { test, expect } from "@playwright/test";

test.describe("Dashboard", () => {
  test("muestra KPIs y filtro de usuario", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByText("Gasto del mes")).toBeVisible();
    await expect(page.getByText("Ingreso del mes")).toBeVisible();

    // User filter exists and works
    const select = page.locator("select").first();
    await expect(select).toBeVisible();
    const options = select.locator("option");
    const count = await options.count();
    if (count > 1) {
      await select.selectOption({ index: 1 });
      await expect(page.getByText("Gasto del mes")).toBeVisible();
    }
  });

  test("navegacion de meses cambia datos", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

    // Find month label and prev button
    const header = page.locator("div").filter({ hasText: /Dashboard/ }).first();
    const monthLabel = page.locator("span.text-sm.font-medium").first();
    const initialMonth = await monthLabel.textContent();

    // Click previous month
    const prevButton = page
      .locator("button")
      .filter({ has: page.locator("svg.lucide-chevron-left") });
    await prevButton.click();

    const newMonth = await monthLabel.textContent();
    expect(newMonth).not.toBe(initialMonth);
  });
});
