import { test, expect } from "@playwright/test";

test.describe("Dashboard", () => {
  test("muestra balance y modulos", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByText("Balance del mes")).toBeVisible();
    await expect(page.getByText("Ingresos")).toBeVisible();
    await expect(page.getByText("Gastos")).toBeVisible();
  });

  test("navegacion de meses cambia datos", async ({ page }) => {
    await page.goto("/");
    const monthLabel = page.locator("span.text-sm.font-semibold").first();
    const initialMonth = await monthLabel.textContent();

    const prevButton = page
      .locator("button")
      .filter({ has: page.locator("svg.lucide-chevron-left") });
    await prevButton.click();

    const newMonth = await monthLabel.textContent();
    expect(newMonth).not.toBe(initialMonth);
  });
});
