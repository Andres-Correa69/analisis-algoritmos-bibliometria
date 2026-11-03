import { expect, test } from "@playwright/test"

test("la interfaz es usable en un teléfono (menú lateral y sin desbordes)", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByRole("heading", { name: /20 artículos/ })).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  expect(overflow).toBeLessThanOrEqual(1)
  await page.getByRole("button", { name: "Abrir menú" }).click()
  await page.getByRole("link", { name: /Búsqueda de patrones/ }).click()
  await expect(page).toHaveURL(/\/patrones$/)
  await expect(page.getByTestId("occurrences-badge")).toBeVisible()
})
