"""
API REST del proyecto (Requerimiento 4: despliegue).

Ejecutar en desarrollo:   uvicorn bibliometria.api.main:app --reload --port 8000
Documentación interactiva: http://localhost:8000/docs

Además de los endpoints ``/api/*`` sirve la interfaz web compilada
(``frontend/dist``) y el informe final en PDF (``/informe.pdf``) si el archivo existe.
"""

from __future__ import annotations

import time
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .. import AUTHORS, __version__
from ..clustering.service import REPRESENTATIONS, get_clustering_engine
from ..config import FRONTEND_DIST_DIR, REPORT_PDF
from ..corpus import load_corpus
from ..preprocessing import default_preprocessor
from ..similarity.service import ALGORITHMS as SIM_ALGORITHMS
from ..similarity.service import get_engine
from ..string_matching.benchmark import load_benchmark, run_benchmark
from ..string_matching.rabin_karp import DEFAULT_BASE, DEFAULT_MODULUS
from ..string_matching.service import ALGORITHMS as SM_ALGORITHMS
from ..string_matching.service import FIELDS, REFERENCE, search_corpus, trace_search

app = FastAPI(
    title="Análisis de algoritmos en el contexto de la bibliometría",
    description=(
        "Proyecto final de Análisis de Algoritmos 2026-2 (Universidad del Quindío). "
        "Similitud textual (R1), agrupamiento jerárquico (R2) y búsqueda de patrones (R3) "
        "sobre los abstracts de 20 artículos científicos."
    ),
    version=__version__,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _bad_request(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


# --------------------------------------------------------------------------- #
# Generales
# --------------------------------------------------------------------------- #


@app.get("/api/health", tags=["general"])
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/api/meta", tags=["general"])
def meta() -> dict:
    engine = get_engine()
    return {
        "title": app.title,
        "version": __version__,
        "authors": AUTHORS,
        "course": "Análisis de Algoritmos — Universidad del Quindío, 2026-2",
        "corpus_size": len(engine.corpus),
        "similarity_algorithms": [{"key": k, **SIM_ALGORITHMS[k]} for k in engine.available_algorithms()],
        "clustering_representations": REPRESENTATIONS,
        "string_matching_algorithms": [{"key": k, **v} for k, v in SM_ALGORITHMS.items()],
        "search_fields": FIELDS,
        "report_available": REPORT_PDF.exists(),
    }


# --------------------------------------------------------------------------- #
# Corpus
# --------------------------------------------------------------------------- #


@app.get("/api/corpus", tags=["corpus"])
def corpus_list() -> dict:
    corpus = load_corpus()
    return {"count": len(corpus), "articles": [a.to_dict() for a in corpus]}


@app.get("/api/corpus/{article_id}", tags=["corpus"])
def corpus_item(article_id: int) -> dict:
    try:
        return load_corpus().get(article_id).to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/corpus/{article_id}/preprocessing", tags=["corpus"])
def corpus_preprocessing(article_id: int) -> dict:
    try:
        art = load_corpus().get(article_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": art.id, "code": art.code, **default_preprocessor().process(art.abstract).to_dict()}


# --------------------------------------------------------------------------- #
# Requerimiento 1 — Similitud textual
# --------------------------------------------------------------------------- #


class CompareRequest(BaseModel):
    ids: list[int] = Field(..., min_length=2, description="Ids de los artículos a comparar (2 o más)")
    algorithms: list[str] | None = Field(None, description="Subconjunto de algoritmos (por defecto, todos)")
    granularity: str = Field("words", pattern="^(words|chars)$", description="Levenshtein por palabras o caracteres")


@app.post("/api/similarity/compare", tags=["R1 similitud"])
def similarity_compare(req: CompareRequest) -> dict:
    try:
        return get_engine().compare(req.ids, req.algorithms, req.granularity)
    except (ValueError, KeyError, RuntimeError) as exc:
        raise _bad_request(exc) from exc


@app.get("/api/similarity/explain", tags=["R1 similitud"])
def similarity_explain(
    a: int = Query(..., description="Id del primer artículo"),
    b: int = Query(..., description="Id del segundo artículo"),
    window: int = Query(10, ge=3, le=25, description="Tokens mostrados en las matrices de programación dinámica"),
    match: int = Query(1),
    mismatch: int = Query(-1),
    gap: int = Query(-1),
) -> dict:
    if a == b:
        raise HTTPException(status_code=400, detail="Seleccione dos artículos distintos")
    try:
        return get_engine().explain(a, b, window=window, nw_params=(match, mismatch, gap))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@lru_cache(maxsize=16)
def _matrix(algorithm: str) -> dict:
    engine = get_engine()
    t0 = time.perf_counter()
    M = engine.full_matrix(algorithm)
    return {
        "algorithm": algorithm,
        "ids": engine.corpus.ids,
        "codes": [a.code for a in engine.corpus],
        "matrix": [[round(v, 6) for v in row] for row in M],
        "seconds": round(time.perf_counter() - t0, 3),
    }


@app.get("/api/similarity/matrix", tags=["R1 similitud"])
def similarity_matrix(algorithm: str = Query("tfidf_cosine")) -> dict:
    if algorithm not in get_engine().available_algorithms():
        raise HTTPException(status_code=400, detail=f"Algoritmo no disponible: {algorithm}")
    return _matrix(algorithm)


# --------------------------------------------------------------------------- #
# Requerimiento 2 — Agrupamiento jerárquico
# --------------------------------------------------------------------------- #


@app.get("/api/clustering", tags=["R2 clustering"])
def clustering(
    representation: str = Query("tfidf", pattern="^(tfidf|sbert)$"),
    display_k: int = Query(4, ge=1, le=20),
) -> dict:
    try:
        return get_clustering_engine().run(representation, display_k=display_k)
    except RuntimeError as exc:
        raise _bad_request(exc) from exc


# --------------------------------------------------------------------------- #
# Requerimiento 3 — Búsqueda de patrones
# --------------------------------------------------------------------------- #


class SearchRequest(BaseModel):
    pattern: str = Field(..., min_length=1, max_length=200)
    algorithms: list[str] | None = None
    fields: list[str] | None = Field(None, description="abstract, title, authors, keywords")
    case_sensitive: bool = False
    base: int = Field(DEFAULT_BASE, ge=2, le=1_000_003)
    modulus: int = Field(DEFAULT_MODULUS, ge=2, le=10**12)


@app.post("/api/search", tags=["R3 búsqueda de patrones"])
def search(req: SearchRequest) -> dict:
    try:
        return search_corpus(req.pattern, req.algorithms, req.fields, req.case_sensitive, base=req.base, modulus=req.modulus)
    except ValueError as exc:
        raise _bad_request(exc) from exc


class TraceRequest(BaseModel):
    pattern: str = Field(..., min_length=1, max_length=60)
    algorithm: str = Field("kmp")
    text: str | None = Field(None, max_length=3000, description="Texto a recorrer (si no se envía article_id)")
    article_id: int | None = None
    case_sensitive: bool = False
    base: int = Field(DEFAULT_BASE, ge=2, le=1_000_003)
    modulus: int = Field(DEFAULT_MODULUS, ge=2, le=10**12)


@app.post("/api/search/trace", tags=["R3 búsqueda de patrones"])
def search_trace(req: TraceRequest) -> dict:
    if req.algorithm not in SM_ALGORITHMS and req.algorithm not in REFERENCE:
        raise HTTPException(status_code=400, detail=f"Algoritmo desconocido: {req.algorithm}")
    text = req.text
    if not text and req.article_id is not None:
        try:
            text = load_corpus().get(req.article_id).abstract
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not text:
        raise HTTPException(status_code=400, detail="Envíe un texto o un article_id")
    try:
        return trace_search(req.pattern, text[:3000], req.algorithm, req.case_sensitive, req.base, req.modulus)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.get("/api/search/benchmark", tags=["R3 búsqueda de patrones"])
def search_benchmark(refresh: bool = Query(False, description="Recalcular un benchmark rápido")) -> dict:
    if refresh:
        return run_benchmark(repeats=3, quick=True)
    data = load_benchmark()
    if data is None:
        data = run_benchmark(repeats=3, quick=True)
    return data


# --------------------------------------------------------------------------- #
# Informe y frontend
# --------------------------------------------------------------------------- #


@app.get("/informe.pdf", include_in_schema=False)
def report_pdf():
    if not REPORT_PDF.exists():
        raise HTTPException(status_code=404, detail="El informe aún no ha sido generado")
    return FileResponse(REPORT_PDF, media_type="application/pdf", filename=REPORT_PDF.name)


if FRONTEND_DIST_DIR.exists():
    assets = FRONTEND_DIST_DIR / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        candidate = (FRONTEND_DIST_DIR / full_path).resolve()
        if full_path and candidate.is_file() and FRONTEND_DIST_DIR.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST_DIR / "index.html")
