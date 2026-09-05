import { test, expect } from "@playwright/test";

test.describe("Compartido", () => {
  test("muestra pagina de compartido", async ({ page }) => {
    await page.goto("/compartido");
    await expect(page.getByRole("heading", { name: "Compartido" })).toBeVisible();
  });
});
