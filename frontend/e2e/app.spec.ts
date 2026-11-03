import { expect, test, type Page } from "@playwright/test"

function trackErrors(page: Page) {
  const errors: string[] = []
  page.on("pageerror", (e) => errors.push(String(e)))
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text())
  })
  return errors
}

test.describe("Corpus", () => {
  test("lista los 20 artículos y abre el detalle con el abstract", async ({ page }) => {
    const errors = trackErrors(page)
    await page.goto("/")
    await expect(page.getByRole("heading", { name: /20 artículos/ })).toBeVisible()
    await expect(page.locator("[data-testid^=row-]")).toHaveCount(20)
    await page.getByPlaceholder("Filtrar por título, autor, revista…").fill("ChatGPT")
    await expect(page.getByTestId("row-19")).toBeVisible()
    await page.getByTestId("row-19").click()
    await expect(page.getByRole("dialog")).toContainText("An artificial intelligence-based chatbot, ChatGPT")
    await expect(page.getByRole("dialog")).toContainText("Chung Kwan Lo")
    expect(errors).toEqual([])
  })
})

test.describe("Requerimiento 1 — similitud", () => {
  test("compara artículos y muestra la demostración paso a paso", async ({ page }) => {
    const errors = trackErrors(page)
    await page.goto("/similitud")
    const table = page.getByTestId("results-table")
    await expect(table.locator("tbody tr")).toHaveCount(6) // 4 artículos -> 6 pares
    await page.getByRole("button", { name: "IA generativa" }).click()
    await page.getByTestId("compare-button").click()
    await expect(table.locator("tbody tr")).toHaveCount(10) // 5 artículos -> 10 pares
    await expect(table).toContainText("A15 – A19")

    await page.getByRole("tab", { name: "Paso a paso" }).click()
    const explain = page.getByTestId("explain-view")
    await expect(explain).toContainText("Levenshtein (programación dinámica)")
    await expect(explain).toContainText("Needleman-Wunsch")
    await expect(explain).toContainText("Coseno sobre TF-IDF")
    await expect(explain).toContainText("Sentence-BERT")
    await expect(explain.locator("table").first()).toBeVisible()

    await page.getByRole("tab", { name: "Matrices" }).click()
    await expect(page.getByRole("img", { name: "Mapa de calor de similitudes" })).toBeVisible()
    expect(errors).toEqual([])
  })

  test("permite agregar artículos con el selector y usar Levenshtein por caracteres", async ({ page }) => {
    await page.goto("/similitud")
    await expect(page.getByTestId("results-table").locator("tbody tr")).toHaveCount(6)
    await page.getByTestId("article-select").click()
    await page.getByTestId("option-1").click()
    await page.keyboard.press("Escape")
    await page.getByRole("radio", { name: "caracteres" }).click()
    await page.getByTestId("compare-button").click()
    await expect(page.getByTestId("results-table").locator("tbody tr")).toHaveCount(10)
  })
})

test.describe("Requerimiento 2 — agrupamiento", () => {
  test("muestra dendrogramas, métricas y el método más coherente", async ({ page }) => {
    const errors = trackErrors(page)
    await page.goto("/clustering")
    const metrics = page.getByTestId("metrics-table")
    await expect(metrics.locator("tbody tr")).toHaveCount(4)
    await expect(metrics).toContainText("más coherente")
    const dendro = page.getByRole("img", { name: /Dendrograma/ })
    await expect(dendro.locator("circle")).toHaveCount(20)

    await page.getByTestId("method-ward").click()
    await expect(page.getByRole("img", { name: /Dendrograma Ward/ })).toBeVisible()
    await page.getByRole("radio", { name: "SBERT (IA)" }).click()
    await expect(page.getByText(/Sentence-BERT all-MiniLM-L6-v2/).first()).toBeVisible()
    await page.getByRole("slider", { name: "Número de grupos" }).focus()
    await page.keyboard.press("ArrowRight")
    await expect(page.getByText("Grupos al cortar en k = 5")).toBeVisible()
    expect(errors).toEqual([])
  })
})

test.describe("Requerimiento 3 — búsqueda de patrones", () => {
  test("busca en abstracts y cruza con autores", async ({ page }) => {
    const errors = trackErrors(page)
    await page.goto("/patrones")
    await expect(page.getByTestId("occurrences-badge")).toContainText("8 ocurrencias")
    await page.getByTestId("pattern-input").fill("learning analytics")
    await page.getByTestId("search-button").click()
    await expect(page.getByTestId("search-results")).toContainText("A07")
    await expect(page.getByText("los 3 algoritmos coinciden")).toBeVisible()

    await page.getByRole("checkbox").nth(0).click() // quita abstracts
    await page.getByRole("checkbox").nth(1).click() // quita títulos
    await page.getByRole("checkbox").nth(2).click() // agrega autores
    await page.getByTestId("pattern-input").fill("Melissa Bond")
    await page.getByTestId("search-button").click()
    const results = page.getByTestId("search-results")
    await expect(results).toContainText("A12")
    await expect(results).toContainText("A20")
    expect(errors).toEqual([])
  })

  test("reproduce paso a paso KMP, Boyer-Moore y Rabin-Karp", async ({ page }) => {
    await page.goto("/patrones")
    await page.getByRole("tab", { name: "Paso a paso" }).click()
    const counter = page.getByTestId("step-counter")
    await expect(counter).toContainText("Paso 1 de")
    await page.getByRole("button", { name: "Paso siguiente" }).click()
    await expect(counter).toContainText("Paso 2 de")
    await expect(page.getByText("Sufijo bueno (gs)")).toBeVisible()

    await page.getByTestId("trace-algorithm").click()
    await page.getByRole("option", { name: "Knuth-Morris-Pratt" }).click()
    await expect(page.getByText("π[q]").first()).toBeVisible()

    await page.getByTestId("trace-algorithm").click()
    await page.getByRole("option", { name: "Rabin-Karp" }).click()
    await expect(page.getByText("colisión").first()).toBeVisible()
    await page.getByRole("button", { name: "Último paso" }).click()
    await expect(counter).toContainText(/Paso (\d+) de \1/)
  })

  test("muestra el benchmark empírico", async ({ page }) => {
    await page.goto("/patrones")
    await page.getByRole("tab", { name: "Rendimiento empírico" }).click()
    await expect(page.getByText("Peor caso teórico")).toBeVisible()
    await expect(page.getByText("Rabin-Karp: colisiones según el módulo q")).toBeVisible()
  })
})

test.describe("Requerimiento 4 — despliegue", () => {
  test("presenta arquitectura, equipo y enlaces a la documentación", async ({ page }) => {
    await page.goto("/acerca")
    await expect(page.getByText("Arquitectura por capas")).toBeVisible()
    for (const name of ["Mariana Muñoz Rodriguez", "Andres Felipe Correa Valencia", "Ivan Alexander Cardona", "Milton Cesar Gomez Roso"]) {
      await expect(page.getByText(name)).toBeVisible()
    }
    const docs = await page.request.get("/docs")
    expect(docs.ok()).toBeTruthy()
    const openapi = await page.request.get("/openapi.json")
    expect((await openapi.json()).paths["/api/search"]).toBeTruthy()
  })

  test("navega con el menú lateral y cambia a modo oscuro", async ({ page }) => {
    await page.goto("/")
    await page.getByRole("link", { name: /Agrupamiento/ }).click()
    await expect(page).toHaveURL(/\/clustering$/)
    await page.getByRole("button", { name: /modo oscuro|modo claro/ }).click()
    await expect(page.locator("html")).toHaveClass(/dark|light/)
  })
})
