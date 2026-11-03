# Análisis de algoritmos en el contexto de la bibliometría

Proyecto final de **Análisis de Algoritmos (2026-2)** — Universidad del Quindío, Ingeniería de Sistemas y Computación.
Profesor: Sergio Augusto Cardona Torres.

**Autores:** Mariana Muñoz Rodriguez · Andres Felipe Correa Valencia · Ivan Alexander Cardona · Milton Cesar Gomez Roso

La aplicación procesa los **20 artículos científicos en PDF** entregados por el docente: extrae automáticamente título,
autores y abstract (más palabras clave, año, revista y DOI) y sobre los abstracts implementa:

| Requerimiento | Qué se implementó (desde cero) |
|---|---|
| **R1 — Similitud textual** | Levenshtein y Needleman-Wunsch (programación dinámica), Jaccard (conjuntos), coseno sobre TF-IDF (espacio vectorial) y dos modelos de IA: **GloVe** (promedio de embeddings de palabras) y **Sentence-BERT** (`all-MiniLM-L6-v2`), comparados con coseno y distancia euclidiana propias. |
| **R2 — Agrupamiento jerárquico** | Algoritmo aglomerativo con la fórmula de Lance-Williams: **single, complete y average linkage** (+ Ward como adicional), dendrogramas propios y evaluación con **correlación cofenética** y **coeficiente de silueta**. |
| **R3 — Búsqueda de patrones** | **KMP**, **Boyer-Moore** (carácter malo + sufijo bueno) y **Rabin-Karp** (rolling hash), sin `find()`, `index()` ni expresiones regulares; trazas paso a paso y benchmark empírico. |
| **R4 — Despliegue** | API REST (FastAPI), interfaz web (React + shadcn/ui + Recharts), menú por consola y Docker Compose con HTTPS automático (Caddy) para el servidor de OVHcloud. |

El informe técnico final es **`Informe_Final_Analisis_Algoritmos.pdf`**; la aplicación lo ofrece para descarga en `/informe.pdf`.

---

## Estructura

```
AnalisisAlgProyect/
├── bibliometria/                 # Paquete Python (núcleo del proyecto)
│   ├── extraction/               # Lectura de los PDF y construcción del corpus
│   ├── preprocessing/            # Tokenizador, stopwords y stemmer de Porter propio
│   ├── similarity/               # R1: levenshtein, needleman_wunsch, jaccard, tfidf, embeddings
│   ├── clustering/               # R2: agglomerative, evaluation, dendrogram
│   ├── string_matching/          # R3: kmp, boyer_moore, rabin_karp, benchmark
│   ├── api/main.py               # R4: API REST + servidor de la interfaz
│   ├── corpus.py · config.py
├── data/
│   ├── raw/articulos/            # Los 20 PDF del docente
│   ├── processed/                # corpus.json, embeddings_sbert.json, benchmark
│   └── models/                   # subconjunto de GloVe con el vocabulario del corpus
├── frontend/                     # Interfaz web (React + Vite + TypeScript + shadcn/ui)
├── scripts/                      # build_embeddings.py (regenera los embeddings de IA)
├── tests/                        # pytest (unitarias, oráculo, propiedades, API, flujo)
├── outputs/                      # Dendrogramas PNG y métricas CSV generadas por consola
├── main.py                       # Menú por consola
├── Dockerfile · docker-compose.yml · deploy/Caddyfile · .env.example
└── requirements*.txt
```

## Instalación

Requisitos: Python 3.11+ (y Node 20+ sólo si se va a recompilar la interfaz).

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

### Menú por consola

```bash
python main.py
```

Opciones: extraer el corpus desde los PDF, listar artículos, comparar artículos (R1), agrupamiento y dendrogramas (R2),
buscar patrones y benchmark (R3) e iniciar la aplicación web (R4).

### Aplicación web

```bash
cd frontend && npm install && npm run build && cd ..
uvicorn bibliometria.api.main:app --port 8000
```

Abrir <http://localhost:8000>. La documentación interactiva de la API está en <http://localhost:8000/docs>.

Para desarrollar la interfaz con recarga en caliente: `uvicorn bibliometria.api.main:app --reload` y, en otra terminal,
`cd frontend && npm run dev` (Vite redirige `/api` al puerto 8000).

### Regenerar datos derivados

```bash
python -m bibliometria.extraction.build_corpus     # PDF -> data/processed/corpus.json
pip install -r requirements-ai.txt
python scripts/build_embeddings.py                 # GloVe (subconjunto) + Sentence-BERT
python -m bibliometria.string_matching.benchmark   # benchmark de R3
```

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest                                   # 177 pruebas: unitarias, oráculo, propiedades, API y flujo
cd frontend && npx playwright test       # pruebas de extremo a extremo de la interfaz
```

SciPy, scikit-learn, NLTK y RapidFuzz **sólo se usan en las pruebas**, como oráculos para comprobar que las
implementaciones propias producen exactamente los mismos resultados.

## Despliegue

### Local con Docker

```bash
docker compose up -d --build        # http://localhost:8000
```

### Servidor de OVHcloud con dominio propio

La imagen sirve la API y la interfaz por el puerto 8000; Caddy actúa como proxy inverso y obtiene
automáticamente el certificado HTTPS (Let's Encrypt) para el dominio.

1. Crear el servidor (VPS con Ubuntu) e instalar Docker Engine con el plugin `compose`.
2. En el DNS del dominio, crear un registro **A** (y **AAAA** si hay IPv6) que apunte a la IP pública del servidor.
3. Abrir los puertos 80 y 443 en el firewall del servidor.
4. Clonar el repositorio en el servidor y configurar el dominio:
   ```bash
   cp .env.example .env      # editar DOMAIN=midominio.com
   docker compose --profile produccion up -d --build
   ```
5. Verificar: `https://midominio.com` (interfaz), `https://midominio.com/docs` (API) y
   `docker compose ps` (el servicio `app` debe aparecer *healthy*).

Para actualizar después de cambios: `git pull && docker compose --profile produccion up -d --build`.

## Uso de IA generativa

El informe incluye la declaración explícita del uso de herramientas de IA generativa como apoyo al desarrollo.
