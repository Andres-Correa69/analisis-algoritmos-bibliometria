"""
Genera los artefactos de los dos modelos de IA del Requerimiento 1.

1. GloVe (glove-wiki-gigaword-100): lee el archivo original (400 000 palabras x
   100 dimensiones, ~128 MB comprimido) y conserva sólo los vectores de las
   palabras que aparecen en los abstracts y títulos del corpus.
2. Sentence-BERT (all-MiniLM-L6-v2): codifica cada abstract completo en un
   vector de 384 dimensiones normalizado (L2).

Requiere las dependencias de ``requirements-ai.txt``. Uso:

    python scripts/build_embeddings.py --glove /ruta/glove-wiki-gigaword-100.gz

Si no se indica ``--glove`` el archivo se descarga del repositorio público de
gensim-data (RaRe Technologies).
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bibliometria.config import (  # noqa: E402
    GLOVE_MODEL_NAME,
    GLOVE_SUBSET_JSON,
    SBERT_EMBEDDINGS_JSON,
    SBERT_MODEL_NAME,
    ensure_dirs,
)
from bibliometria.corpus import Corpus  # noqa: E402
from bibliometria.similarity.embeddings import content_words  # noqa: E402

GLOVE_URL = (
    "https://github.com/RaRe-Technologies/gensim-data/releases/download/"
    "glove-wiki-gigaword-100/glove-wiki-gigaword-100.gz"
)


def build_glove_subset(corpus: Corpus, glove_path: Path | None) -> dict:
    vocab: dict[str, int] = {}
    for art in corpus:
        for w in content_words(art.abstract + " " + art.title):
            vocab[w] = vocab.get(w, 0) + 1
    if glove_path is None:
        glove_path = ROOT / "data" / "models" / "glove-wiki-gigaword-100.gz"
        if not glove_path.exists():
            print(f"Descargando {GLOVE_URL} ...")
            urllib.request.urlretrieve(GLOVE_URL, glove_path)
    vectors: dict[str, list[float]] = {}
    dim = 0
    total_words = 0
    with gzip.open(glove_path, "rt", encoding="utf-8") as fh:
        header = fh.readline().split()
        if len(header) != 2:  # archivo sin cabecera (formato GloVe original)
            fh.seek(0)
        for line in fh:
            total_words += 1
            parts = line.rstrip().split(" ")
            word = parts[0]
            if word in vocab:
                vec = [round(float(x), 5) for x in parts[1:]]
                dim = len(vec)
                vectors[word] = vec
    oov = sorted(w for w in vocab if w not in vectors)
    payload = {
        "model": GLOVE_MODEL_NAME,
        "source": GLOVE_URL,
        "description": "Subconjunto de GloVe 6B (Wikipedia 2014 + Gigaword 5) con las palabras del corpus",
        "dim": dim,
        "original_vocabulary_size": total_words,
        "corpus_vocabulary_size": len(vocab),
        "covered": len(vectors),
        "oov": oov,
        "vectors": vectors,
    }
    with open(GLOVE_SUBSET_JSON, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"GloVe: {len(vectors)}/{len(vocab)} palabras del corpus con vector ({dim} dim). OOV={len(oov)}")
    return payload


def build_sbert(corpus: Corpus, max_seq_length: int = 512) -> dict:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(SBERT_MODEL_NAME, device="cpu")
    model.max_seq_length = max_seq_length
    texts = [a.abstract for a in corpus]
    token_counts = {}
    for art in corpus:
        ids = model.tokenizer(art.abstract, add_special_tokens=True)["input_ids"]
        token_counts[art.id] = len(ids)
    t0 = time.perf_counter()
    emb = model.encode(texts, normalize_embeddings=True, batch_size=8, show_progress_bar=False)
    elapsed = time.perf_counter() - t0
    payload = {
        "model": SBERT_MODEL_NAME,
        "dim": int(emb.shape[1]),
        "max_seq_length": max_seq_length,
        "normalized": True,
        "pooling": "mean",
        "encode_seconds": round(elapsed, 3),
        "token_counts": {str(k): v for k, v in token_counts.items()},
        "vectors": {str(a.id): [round(float(x), 6) for x in emb[i]] for i, a in enumerate(corpus)},
    }
    with open(SBERT_EMBEDDINGS_JSON, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"))
    mx = max(token_counts.values())
    print(f"SBERT: {len(texts)} abstracts codificados en {elapsed:.2f}s (dim={emb.shape[1]}, máx. tokens={mx})")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--glove", type=Path, default=None, help="Ruta al archivo glove-wiki-gigaword-100.gz")
    parser.add_argument("--skip-glove", action="store_true")
    parser.add_argument("--skip-sbert", action="store_true")
    args = parser.parse_args()
    ensure_dirs()
    corpus = Corpus.from_json()
    if not args.skip_glove:
        build_glove_subset(corpus, args.glove)
    if not args.skip_sbert:
        build_sbert(corpus)


if __name__ == "__main__":
    main()
