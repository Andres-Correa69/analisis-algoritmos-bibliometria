"""
Construye el corpus procesado (``data/processed/corpus.json``) a partir de los
20 PDF entregados por el docente.

Uso:  python -m bibliometria.extraction.build_corpus
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..config import CORPUS_JSON, EXTRACTION_REPORT_JSON, RAW_PDF_DIR, ensure_dirs
from .pdf_extractor import extract_pdf


def _pdf_sort_key(path: Path) -> tuple[int, str]:
    head = path.name.split(".")[0]
    return (int(head) if head.isdigit() else 10**6, path.name)


def short_title(title: str, max_words: int = 7) -> str:
    words = title.replace(":", " :").split()
    out = []
    for w in words:
        if w == ":":
            break
        out.append(w)
        if len(out) == max_words:
            break
    text = " ".join(out)
    return text + ("…" if len(out) < len(title.split()) else "")


def build_corpus(pdf_dir: Path = RAW_PDF_DIR, out_path: Path = CORPUS_JSON) -> list[dict]:
    """Extrae los metadatos de todos los PDF y guarda el corpus en JSON."""
    ensure_dirs()
    pdfs = sorted(Path(pdf_dir).glob("*.pdf"), key=_pdf_sort_key)
    if not pdfs:
        raise FileNotFoundError(f"No se encontraron PDF en {pdf_dir}")
    articles: list[dict] = []
    report: list[dict] = []
    for pdf in pdfs:
        t0 = time.perf_counter()
        art = extract_pdf(pdf)
        elapsed = (time.perf_counter() - t0) * 1000
        record = art.to_dict()
        warnings = record.pop("warnings")
        record["code"] = f"A{art.id:02d}"
        record["short_title"] = short_title(art.title)
        record["abstract_words"] = len(art.abstract.split())
        record["abstract_chars"] = len(art.abstract)
        articles.append(record)
        report.append({"id": art.id, "file": pdf.name, "ms": round(elapsed, 1), "warnings": warnings})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(articles, fh, ensure_ascii=False, indent=2)
    with open(EXTRACTION_REPORT_JSON, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    return articles


if __name__ == "__main__":
    arts = build_corpus()
    print(f"Corpus generado con {len(arts)} artículos -> {CORPUS_JSON}")
    for a in arts:
        print(f"  {a['code']}  {a['year']}  {a['abstract_words']:>3} palabras  {a['short_title']}")
