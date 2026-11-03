"""
Servicio del Requerimiento 3: búsqueda de un patrón en los abstracts (y, como
cruce de información, en títulos, autores y palabras clave) con KMP,
Boyer-Moore y Rabin-Karp.
"""

from __future__ import annotations

from ..corpus import Article, Corpus, load_corpus
from .base import MatchResult
from .boyer_moore import boyer_moore_search
from .kmp import kmp_search
from .naive import naive_search
from .rabin_karp import DEFAULT_BASE, DEFAULT_MODULUS, rabin_karp_search

ALGORITHMS = {
    "kmp": {
        "label": "Knuth-Morris-Pratt",
        "preprocessing": "Θ(m)",
        "search_best": "Θ(n)",
        "search_worst": "Θ(n)",
        "space": "O(m)",
        "idea": "Función de prefijos π: nunca retrocede sobre el texto.",
    },
    "boyer_moore": {
        "label": "Boyer-Moore",
        "preprocessing": "O(m + σ)",
        "search_best": "Θ(n/m)",
        "search_worst": "O(n·m)",
        "space": "O(m + σ)",
        "idea": "Compara de derecha a izquierda; saltos por carácter malo y sufijo bueno.",
    },
    "rabin_karp": {
        "label": "Rabin-Karp",
        "preprocessing": "Θ(m)",
        "search_best": "Θ(n + m)",
        "search_worst": "O(n·m)",
        "space": "O(1)",
        "idea": "Rolling hash con aritmética modular; verifica sólo si coinciden los hashes.",
    },
}
REFERENCE = {"naive": {"label": "Fuerza bruta (referencia)", "preprocessing": "—", "search_best": "Θ(n)", "search_worst": "O(n·m)", "space": "O(1)"}}

FIELDS = {
    "abstract": "Abstract",
    "title": "Título",
    "authors": "Autores",
    "keywords": "Palabras clave",
}


def fold_case(text: str) -> str:
    """Minúsculas carácter por carácter conservando la longitud (posiciones estables)."""
    out = []
    for ch in text:
        low = ch.lower()
        out.append(low if len(low) == 1 else ch)
    return "".join(out)


def field_text(article: Article, field: str) -> str:
    if field == "abstract":
        return article.abstract
    if field == "title":
        return article.title
    if field == "authors":
        return "; ".join(article.authors)
    if field == "keywords":
        return "; ".join(article.keywords)
    raise ValueError(f"Campo desconocido: {field}")


def run_algorithm(
    algorithm: str,
    text: str,
    pattern: str,
    trace: bool = False,
    base: int = DEFAULT_BASE,
    modulus: int = DEFAULT_MODULUS,
    max_trace: int = 5000,
) -> MatchResult:
    if algorithm == "kmp":
        return kmp_search(text, pattern, trace=trace, max_trace=max_trace)
    if algorithm == "boyer_moore":
        return boyer_moore_search(text, pattern, trace=trace, max_trace=max_trace)
    if algorithm == "rabin_karp":
        return rabin_karp_search(text, pattern, base=base, modulus=modulus, trace=trace, max_trace=max_trace)
    if algorithm == "naive":
        return naive_search(text, pattern, trace=trace, max_trace=max_trace)
    raise ValueError(f"Algoritmo desconocido: {algorithm}")


def search_corpus(
    pattern: str,
    algorithms: list[str] | None = None,
    fields: list[str] | None = None,
    case_sensitive: bool = False,
    context: int = 60,
    base: int = DEFAULT_BASE,
    modulus: int = DEFAULT_MODULUS,
    corpus: Corpus | None = None,
) -> dict:
    """Busca ``pattern`` en los campos indicados de los 20 artículos."""
    if not pattern or not pattern.strip():
        raise ValueError("Ingrese un patrón de búsqueda no vacío")
    corpus = corpus or load_corpus()
    algorithms = algorithms or list(ALGORITHMS)
    fields = fields or ["abstract"]
    for f in fields:
        if f not in FIELDS:
            raise ValueError(f"Campo desconocido: {f}")
    for a in algorithms:
        if a not in ALGORITHMS and a not in REFERENCE:
            raise ValueError(f"Algoritmo desconocido: {a}")

    needle = pattern if case_sensitive else fold_case(pattern)
    m = len(needle)
    totals = {
        a: {
            "occurrences": 0,
            "comparisons": 0,
            "alignments": 0,
            "preprocessing_ns": 0,
            "search_ns": 0,
            "total_ns": 0,
            "spurious_hits": 0,
            "documents": 0,
        }
        for a in algorithms
    }
    results = []
    consistent = True
    scanned_chars = 0
    for art in corpus:
        for f in fields:
            raw = field_text(art, f)
            haystack = raw if case_sensitive else fold_case(raw)
            scanned_chars += len(haystack)
            reference_positions = None
            for a in algorithms:
                r = run_algorithm(a, haystack, needle, base=base, modulus=modulus)
                t = totals[a]
                t["occurrences"] += len(r.positions)
                t["comparisons"] += r.comparisons
                t["alignments"] += r.alignments
                t["preprocessing_ns"] += r.preprocessing_ns
                t["search_ns"] += r.search_ns
                t["total_ns"] += r.total_ns
                t["spurious_hits"] += r.extra.get("spurious_hits", 0)
                if r.positions:
                    t["documents"] += 1
                if reference_positions is None:
                    reference_positions = r.positions
                elif r.positions != reference_positions:
                    consistent = False
            if reference_positions:
                occurrences = []
                for pos in reference_positions:
                    occurrences.append(
                        {
                            "position": pos,
                            "before": raw[max(0, pos - context) : pos],
                            "match": raw[pos : pos + m],
                            "after": raw[pos + m : pos + m + context],
                        }
                    )
                results.append(
                    {
                        "id": art.id,
                        "code": art.code,
                        "title": art.title,
                        "authors": list(art.authors),
                        "year": art.year,
                        "field": f,
                        "field_label": FIELDS[f],
                        "count": len(reference_positions),
                        "occurrences": occurrences,
                    }
                )
    results.sort(key=lambda r: (-r["count"], r["id"]))
    return {
        "pattern": pattern,
        "case_sensitive": case_sensitive,
        "fields": fields,
        "algorithms": [{"key": a, **(ALGORITHMS.get(a) or REFERENCE[a])} for a in algorithms],
        "rabin_karp": {"base": base, "modulus": modulus},
        "totals": totals,
        "results": results,
        "total_occurrences": sum(r["count"] for r in results),
        "documents_with_matches": len({r["id"] for r in results}),
        "scanned_chars": scanned_chars,
        "consistent": consistent,
    }


def trace_search(
    pattern: str,
    text: str,
    algorithm: str,
    case_sensitive: bool = False,
    base: int = DEFAULT_BASE,
    modulus: int = DEFAULT_MODULUS,
    max_trace: int = 3000,
) -> dict:
    """Ejecución instrumentada (paso a paso) sobre un texto corto."""
    if not text:
        raise ValueError("El texto no puede estar vacío")
    needle = pattern if case_sensitive else fold_case(pattern)
    haystack = text if case_sensitive else fold_case(text)
    r = run_algorithm(algorithm, haystack, needle, trace=True, base=base, modulus=modulus, max_trace=max_trace)
    d = r.to_dict(include_trace=True)
    d["text"] = haystack
    d["info"] = ALGORITHMS.get(algorithm) or REFERENCE.get(algorithm)
    return d
