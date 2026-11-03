# Interfaz web — Bibliometría · Análisis de Algoritmos

React 19 + TypeScript + Vite, con componentes de shadcn/ui, Tailwind CSS, Recharts y KaTeX.

```bash
npm install
npm run dev          # desarrollo (requiere la API en el puerto 8000)
npm run build        # genera dist/, que sirve FastAPI en producción
npx playwright test  # pruebas de extremo a extremo (usa el servidor de la raíz del proyecto)
```

Estructura: `src/pages/` (una página por requerimiento), `src/components/` (dendrograma, mapa de calor,
matriz de programación dinámica, reproductor paso a paso), `src/lib/` (cliente de la API, tipos, paleta).
