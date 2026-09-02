import { test, expect } from "@playwright/test";

test.describe("Gastos Compartidos", () => {
  test("muestra balance neto y navegacion de meses", async ({ page }) => {
    await page.goto("/compartido");
    await expect(page.getByRole("heading", { name: "Gastos Compartidos" })).toBeVisible();
    await expect(page.getByText("Balance neto")).toBeVisible();

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
