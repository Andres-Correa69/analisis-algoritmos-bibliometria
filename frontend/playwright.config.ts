import { defineConfig, devices } from "@playwright/test"

/**
 * Pruebas de extremo a extremo de la interfaz.
 *
 * Levanta (o reutiliza) el servidor FastAPI, que sirve la API y el build de
 * producción (`npm run build`). Usa el Chrome instalado en el equipo; para usar
 * el Chromium de Playwright ejecute `npx playwright install chromium` y defina
 * E2E_BROWSER_CHANNEL="".
 */
const channel = process.env.E2E_BROWSER_CHANNEL ?? "chrome"
const serverCmd = process.env.E2E_SERVER_CMD ?? "cd .. && .venv/bin/uvicorn bibliometria.api.main:app --port 8000"

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:8000",
    trace: "retain-on-failure",
    // Sin animaciones de Recharts (respeta prefers-reduced-motion).
    contextOptions: { reducedMotion: "reduce" },
  },
  projects: [
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], channel: channel || undefined, viewport: { width: 1440, height: 1000 } },
      testIgnore: /mobile\.spec\.ts/,
    },
    {
      name: "mobile",
      use: { ...devices["Pixel 7"], channel: channel || undefined },
      testMatch: /mobile\.spec\.ts/,
    },
  ],
  webServer: {
    command: serverCmd,
    url: "http://localhost:8000/api/health",
    reuseExistingServer: true,
    timeout: 60_000,
  },
})
