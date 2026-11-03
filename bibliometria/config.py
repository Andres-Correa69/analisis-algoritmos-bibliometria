"""Rutas y constantes globales del proyecto."""

from __future__ import annotations

import os
from pathlib import Path

# Raíz del proyecto (carpeta que contiene a ``bibliometria/``).
ROOT_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT_DIR / "data"
RAW_PDF_DIR = Path(os.environ.get("BIBLIO_PDF_DIR", DATA_DIR / "raw" / "articulos"))
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = DATA_DIR / "models"
OUTPUTS_DIR = ROOT_DIR / "outputs"
FRONTEND_DIST_DIR = ROOT_DIR / "frontend" / "dist"
REPORT_PDF = ROOT_DIR / "Informe_Final_Analisis_Algoritmos.pdf"

# Archivos derivados
CORPUS_JSON = PROCESSED_DIR / "corpus.json"
EXTRACTION_REPORT_JSON = PROCESSED_DIR / "extraction_report.json"
SBERT_EMBEDDINGS_JSON = PROCESSED_DIR / "embeddings_sbert.json"
GLOVE_SUBSET_JSON = MODELS_DIR / "glove-wiki-gigaword-100.subset.json"
BENCHMARK_JSON = PROCESSED_DIR / "benchmark_string_matching.json"

# Modelos de IA
SBERT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
GLOVE_MODEL_NAME = "glove-wiki-gigaword-100"


def ensure_dirs() -> None:
    """Crea las carpetas de datos y salidas si no existen."""
    for d in (PROCESSED_DIR, MODELS_DIR, OUTPUTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
